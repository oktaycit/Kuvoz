"""Patient monitoring PDF report generation."""

from __future__ import annotations

import math
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from io import BytesIO
from typing import Any, Iterable


class ReportGenerationUnavailable(RuntimeError):
    """Raised when the PDF backend cannot be imported."""


def parse_timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        try:
            return datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None


def numeric_value(value: Any) -> float | None:
    try:
        if value in (None, "", "--"):
            return None
        result = float(value)
        return None if math.isnan(result) else result
    except (TypeError, ValueError):
        return None


def percentile(values: Iterable[float | None], ratio: float) -> float | None:
    cleaned = sorted(value for value in values if value is not None)
    if not cleaned:
        return None
    if len(cleaned) == 1:
        return cleaned[0]

    k = (len(cleaned) - 1) * ratio
    lo = int(math.floor(k))
    hi = int(math.ceil(k))
    if lo == hi:
        return cleaned[lo]
    return cleaned[lo] * (hi - k) + cleaned[hi] * (k - lo)


def numeric_stats(values: Iterable[float | None]) -> dict[str, Any]:
    cleaned = [value for value in values if value is not None]
    if not cleaned:
        return {
            "n": 0,
            "avg": None,
            "min": None,
            "max": None,
            "median": None,
            "p10": None,
            "p90": None,
        }

    return {
        "n": len(cleaned),
        "avg": sum(cleaned) / len(cleaned),
        "min": min(cleaned),
        "max": max(cleaned),
        "median": percentile(cleaned, 0.5),
        "p10": percentile(cleaned, 0.1),
        "p90": percentile(cleaned, 0.9),
    }


def chronological_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        timestamp = parse_timestamp(row.get("timestamp"))
        if not timestamp:
            continue
        item = dict(row)
        item["_dt"] = timestamp
        normalized.append(item)
    return sorted(normalized, key=lambda item: item["_dt"])


def time_weighted_stats(rows: list[dict[str, Any]], field: str, *, cap_seconds: int = 1800) -> dict[str, Any]:
    total_seconds = 0.0
    weighted_sum = 0.0
    min_value = None
    max_value = None

    for index, row in enumerate(rows[:-1]):
        value = numeric_value(row.get(field))
        if value is None:
            continue
        delta = (rows[index + 1]["_dt"] - row["_dt"]).total_seconds()
        if delta <= 0:
            continue

        weight = min(delta, cap_seconds)
        total_seconds += weight
        weighted_sum += value * weight
        min_value = value if min_value is None else min(min_value, value)
        max_value = value if max_value is None else max(max_value, value)

    return {
        "hours": total_seconds / 3600 if total_seconds else 0,
        "avg": weighted_sum / total_seconds if total_seconds else None,
        "min": min_value,
        "max": max_value,
    }


def weighted_bands(
    rows: list[dict[str, Any]],
    field: str,
    buckets: list[tuple[str, Any]],
    *,
    cap_seconds: int = 1800,
) -> list[dict[str, Any]]:
    counters: Counter[str] = Counter()
    total_seconds = 0.0

    for index, row in enumerate(rows[:-1]):
        value = numeric_value(row.get(field))
        if value is None:
            continue
        delta = (rows[index + 1]["_dt"] - row["_dt"]).total_seconds()
        if delta <= 0:
            continue

        weight = min(delta, cap_seconds)
        total_seconds += weight
        label = "Diğer"
        for bucket_label, predicate in buckets:
            if predicate(value):
                label = bucket_label
                break
        counters[label] += weight

    return [
        {
            "label": label,
            "percent": (seconds / total_seconds * 100) if total_seconds else 0,
            "hours": seconds / 3600,
        }
        for label, seconds in counters.most_common()
    ]


def daily_sensor_series(rows: list[dict[str, Any]]) -> tuple[list[str], dict[str, list[float | None]]]:
    by_day: dict[str, dict[str, list[float | None]]] = defaultdict(lambda: defaultdict(list))
    fields = ("temperature", "humidity", "oxygen", "co2", "target_temperature", "target_humidity")

    for row in rows:
        day = row["_dt"].date().isoformat()
        for field in fields:
            by_day[day][field].append(numeric_value(row.get(field)))

    days = sorted(by_day)
    series = {
        field: [numeric_stats(by_day[day][field])["avg"] for day in days]
        for field in fields
    }
    return days, series


def behavior_seconds(rows: list[dict[str, Any]], *, cap_seconds: int = 300) -> tuple[Counter[str], dict[str, Counter[str]]]:
    counters: Counter[str] = Counter()
    parts: dict[str, Counter[str]] = defaultdict(Counter)

    for index, row in enumerate(rows[:-1]):
        delta = (rows[index + 1]["_dt"] - row["_dt"]).total_seconds()
        if delta <= 0:
            continue
        weight = min(delta, cap_seconds)
        behavior_type = str(row.get("behavior_type") or "unknown")
        counters[behavior_type] += weight
        daypart = "Gündüz 08-20" if 8 <= row["_dt"].hour < 20 else "Gece 20-08"
        parts[daypart][behavior_type] += weight

    return counters, parts


def counter_percentages(counter: Counter[str]) -> list[dict[str, Any]]:
    total = sum(counter.values())
    return [
        {
            "label": label,
            "hours": seconds / 3600,
            "percent": (seconds / total * 100) if total else 0,
        }
        for label, seconds in counter.most_common()
    ]


def collapse_behavior_episodes(rows: list[dict[str, Any]], *, gap_seconds: int = 600) -> list[dict[str, Any]]:
    episodes: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for row in rows:
        behavior_type = str(row.get("behavior_type") or "unknown")
        timestamp = row["_dt"]
        if (
            current
            and current["type"] == behavior_type
            and (timestamp - current["last"]).total_seconds() <= gap_seconds
        ):
            current["last"] = timestamp
            current["events"] += 1
            continue

        if current:
            episodes.append(current)
        current = {"type": behavior_type, "start": timestamp, "last": timestamp, "events": 1}

    if current:
        episodes.append(current)
    return episodes


def build_report_model(
    *,
    sensor_rows: Iterable[dict[str, Any]],
    ai_rows: Iterable[dict[str, Any]],
    behavior_rows: Iterable[dict[str, Any]],
    patient: dict[str, Any] | None = None,
    days: float | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    sensors = chronological_rows(sensor_rows)
    ai = chronological_rows(ai_rows)
    behaviors = chronological_rows(behavior_rows)
    patient = dict(patient or {})
    generated_at = generated_at or datetime.now()

    sensor_stats = {
        field: numeric_stats(numeric_value(row.get(field)) for row in sensors)
        for field in ("temperature", "humidity", "oxygen", "co2")
    }
    sensor_tw = {
        field: time_weighted_stats(sensors, field)
        for field in ("temperature", "humidity", "oxygen", "co2")
    }
    sensor_days, sensor_series = daily_sensor_series(sensors)

    behavior_counter, behavior_dayparts = behavior_seconds(behaviors)
    behavior_distribution = counter_percentages(behavior_counter)
    episodes = collapse_behavior_episodes(behaviors)
    episode_counts = Counter(episode["type"] for episode in episodes)
    episode_daily: dict[str, Counter[str]] = defaultdict(Counter)
    for episode in episodes:
        episode_daily[episode["start"].date().isoformat()][episode["type"]] += 1

    ai_status = Counter(str(row.get("status") or "-").upper() for row in ai)
    reliable_ai = [
        row for row in ai
        if str(row.get("status") or "").upper() == "OK"
        and numeric_value(row.get("respiration_bpm")) is not None
        and (numeric_value(row.get("confidence")) or 0) >= 0.60
    ]
    ai_bpm_stats = numeric_stats(numeric_value(row.get("respiration_bpm")) for row in reliable_ai)
    ai_conf_stats = numeric_stats(numeric_value(row.get("confidence")) for row in ai)

    return {
        "patient": patient,
        "generated_at": generated_at,
        "days": days,
        "coverage": {
            "sensor": {
                "count": len(sensors),
                "first": sensors[0]["_dt"] if sensors else None,
                "last": sensors[-1]["_dt"] if sensors else None,
            },
            "behavior": {
                "count": len(behaviors),
                "first": behaviors[0]["_dt"] if behaviors else None,
                "last": behaviors[-1]["_dt"] if behaviors else None,
            },
            "ai": {
                "count": len(ai),
                "first": ai[0]["_dt"] if ai else None,
                "last": ai[-1]["_dt"] if ai else None,
            },
        },
        "sensors": {
            "stats": sensor_stats,
            "time_weighted": sensor_tw,
            "days": sensor_days,
            "series": sensor_series,
            "humidity_bands": weighted_bands(sensors, "humidity", [
                ("40-60%", lambda value: 40 <= value <= 60),
                ("60-70%", lambda value: 60 < value <= 70),
                (">70%", lambda value: value > 70),
                ("<40%", lambda value: value < 40),
            ]),
            "co2_bands": weighted_bands(sensors, "co2", [
                ("<800 ppm", lambda value: value < 800),
                ("800-1200 ppm", lambda value: 800 <= value <= 1200),
                ("1200-2000 ppm", lambda value: 1200 < value <= 2000),
                (">2000 ppm", lambda value: value > 2000),
            ]),
            "oxygen_bands": weighted_bands(sensors, "oxygen", [
                ("18-21%", lambda value: 18 <= value <= 21),
                ("<18%", lambda value: value < 18),
                (">21%", lambda value: value > 21),
            ]),
        },
        "behavior": {
            "distribution": behavior_distribution,
            "episode_counts": episode_counts,
            "episode_daily": {day: dict(counts) for day, counts in sorted(episode_daily.items())},
            "dayparts": {daypart: counter_percentages(counter) for daypart, counter in behavior_dayparts.items()},
        },
        "ai": {
            "status_counts": ai_status,
            "respiration": ai_bpm_stats,
            "confidence": ai_conf_stats,
        },
    }


def _format_number(value: Any, digits: int = 1, suffix: str = "") -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
        if math.isnan(number):
            return "-"
        if digits == 0:
            return f"{int(round(number))}{suffix}"
        return f"{number:.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return "-"


def _format_dt(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M") if value else "-"


def safe_report_filename(patient: dict[str, Any] | None, generated_at: datetime | None = None) -> str:
    generated_at = generated_at or datetime.now()
    raw_name = str((patient or {}).get("name") or (patient or {}).get("id") or "kuvoz").strip().lower()
    ascii_name = (
        raw_name
        .replace("ı", "i")
        .replace("ğ", "g")
        .replace("ü", "u")
        .replace("ş", "s")
        .replace("ö", "o")
        .replace("ç", "c")
    )
    ascii_name = re.sub(r"[^a-z0-9]+", "_", ascii_name).strip("_") or "kuvoz"
    return f"{ascii_name}_kuvoz_izlem_raporu_{generated_at:%Y-%m-%d}.pdf"


def _find_font_paths() -> tuple[str | None, str | None]:
    regular_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    bold_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
    ]
    regular = next((path for path in regular_candidates if os.path.exists(path)), None)
    bold = next((path for path in bold_candidates if os.path.exists(path)), regular)
    return regular, bold


def generate_patient_report_pdf(
    *,
    sensor_rows: Iterable[dict[str, Any]],
    ai_rows: Iterable[dict[str, Any]],
    behavior_rows: Iterable[dict[str, Any]],
    patient: dict[str, Any] | None = None,
    days: float | None = None,
    generated_at: datetime | None = None,
) -> BytesIO:
    """Generate a patient monitoring PDF and return it as a seeked BytesIO."""

    try:
        from reportlab.lib import colors
        from reportlab.lib.colors import HexColor
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import Flowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:  # pragma: no cover - exercised on devices without dependency
        raise ReportGenerationUnavailable("PDF raporu için reportlab paketi kurulu değil") from exc

    model = build_report_model(
        sensor_rows=sensor_rows,
        ai_rows=ai_rows,
        behavior_rows=behavior_rows,
        patient=patient,
        days=days,
        generated_at=generated_at,
    )
    generated_at = model["generated_at"]

    regular_font, bold_font = _find_font_paths()
    if regular_font:
        pdfmetrics.registerFont(TTFont("KuvozSans", regular_font))
        pdfmetrics.registerFont(TTFont("KuvozSans-Bold", bold_font or regular_font))
        base_font = "KuvozSans"
        bold_base_font = "KuvozSans-Bold"
    else:
        base_font = "Helvetica"
        bold_base_font = "Helvetica-Bold"

    page_w, page_h = A4
    margin = 1.45 * cm
    text = HexColor("#17212b")
    muted = HexColor("#5d6b78")
    blue = HexColor("#1f6feb")
    green = HexColor("#209a62")
    orange = HexColor("#d97706")
    red = HexColor("#c62828")
    teal = HexColor("#008c8c")
    purple = HexColor("#7c3aed")
    grid = HexColor("#d8e0e8")
    header_bg = HexColor("#edf5ff")

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("TitleK", parent=styles["Title"], fontName=bold_base_font, fontSize=23, leading=28, textColor=text, alignment=TA_LEFT, spaceAfter=8))
    styles.add(ParagraphStyle("SubK", parent=styles["Normal"], fontName=base_font, fontSize=10.5, leading=14, textColor=muted, spaceAfter=10))
    styles.add(ParagraphStyle("H1K", parent=styles["Heading1"], fontName=bold_base_font, fontSize=16.5, leading=20, textColor=text, spaceBefore=4, spaceAfter=8))
    styles.add(ParagraphStyle("H2K", parent=styles["Heading2"], fontName=bold_base_font, fontSize=12.2, leading=15, textColor=text, spaceBefore=7, spaceAfter=5))
    styles.add(ParagraphStyle("BodyK", parent=styles["BodyText"], fontName=base_font, fontSize=9, leading=12.5, textColor=text, spaceAfter=5))
    styles.add(ParagraphStyle("SmallK", parent=styles["BodyText"], fontName=base_font, fontSize=7.7, leading=10.2, textColor=muted, spaceAfter=3))
    styles.add(ParagraphStyle("HeadK", parent=styles["BodyText"], fontName=bold_base_font, fontSize=7.8, leading=10.2, textColor=text, spaceAfter=3))
    styles.add(ParagraphStyle("NoteK", parent=styles["BodyText"], fontName=base_font, fontSize=8.2, leading=11.2, textColor=text, backColor=HexColor("#fff7ed"), borderColor=HexColor("#fed7aa"), borderWidth=0.6, borderPadding=7, spaceAfter=7))
    styles.add(ParagraphStyle("CalloutK", parent=styles["BodyText"], fontName=bold_base_font, fontSize=9.1, leading=12.7, textColor=text, backColor=header_bg, borderColor=HexColor("#bad7ff"), borderWidth=0.6, borderPadding=8, spaceAfter=8))

    def escape(value: Any) -> str:
        return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")

    def para(value: Any, style: str = "BodyK") -> Paragraph:
        return Paragraph(escape(value), styles[style])

    def make_table(data: list[list[Any]], widths: list[float] | None = None) -> Table:
        rows = []
        for index, row in enumerate(data):
            style = "HeadK" if index == 0 else "SmallK"
            rows.append([cell if isinstance(cell, Paragraph) else para(cell, style) for cell in row])
        table = Table(rows, colWidths=widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), header_bg),
            ("FONTNAME", (0, 0), (-1, 0), bold_base_font),
            ("FONTNAME", (0, 1), (-1, -1), base_font),
            ("GRID", (0, 0), (-1, -1), 0.35, grid),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HexColor("#f8fafc")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return table

    class KPIBox(Flowable):
        def __init__(self, items: list[dict[str, str]], width: float = 17.0 * cm, height: float = 2.45 * cm):
            super().__init__()
            self.items = items
            self.width = width
            self.height = height

        def draw(self):
            gap = 0.18 * cm
            box_width = (self.width - gap * (len(self.items) - 1)) / len(self.items)
            for index, item in enumerate(self.items):
                x = index * (box_width + gap)
                self.canv.setFillColor(HexColor(item.get("bg", "#f7f9fc")))
                self.canv.setStrokeColor(HexColor("#d8e0e8"))
                self.canv.roundRect(x, 0, box_width, self.height, 6, fill=1, stroke=1)
                self.canv.setFillColor(HexColor(item.get("color", "#17212b")))
                self.canv.setFont(bold_base_font, 12.5)
                self.canv.drawString(x + 0.28 * cm, self.height - 0.73 * cm, item["value"])
                self.canv.setFillColor(muted)
                self.canv.setFont(base_font, 7.5)
                self.canv.drawString(x + 0.28 * cm, self.height - 1.16 * cm, item["label"][:38])
                if item.get("note"):
                    self.canv.setFont(base_font, 6.6)
                    self.canv.drawString(x + 0.28 * cm, 0.34 * cm, item["note"][:42])

    class LineChart(Flowable):
        def __init__(self, title: str, labels: list[str], series: list[dict[str, Any]], width: float = 17.0 * cm, height: float = 6.6 * cm, y_min: float | None = None, y_max: float | None = None):
            super().__init__()
            self.title = title
            self.labels = labels
            self.series = series
            self.width = width
            self.height = height
            self.y_min = y_min
            self.y_max = y_max

        def draw(self):
            canvas = self.canv
            left, right, top, bottom = 1.3 * cm, 0.35 * cm, 0.72 * cm, 1.05 * cm
            plot_w, plot_h = self.width - left - right, self.height - top - bottom
            canvas.setFillColor(text)
            canvas.setFont(bold_base_font, 9.3)
            canvas.drawString(0, self.height - 0.28 * cm, self.title)
            values = [value for item in self.series for value in item["values"] if value is not None]
            if not values:
                canvas.setFont(base_font, 8)
                canvas.drawString(left, bottom + plot_h / 2, "Veri yok")
                return

            vmin = self.y_min if self.y_min is not None else min(values)
            vmax = self.y_max if self.y_max is not None else max(values)
            if vmax == vmin:
                vmax = vmin + 1
            pad = (vmax - vmin) * 0.08
            if self.y_min is None:
                vmin -= pad
            if self.y_max is None:
                vmax += pad

            canvas.setStrokeColor(grid)
            canvas.setLineWidth(0.45)
            for step in range(5):
                y = bottom + plot_h * step / 4
                canvas.line(left, y, left + plot_w, y)
                canvas.setFillColor(muted)
                canvas.setFont(base_font, 6.7)
                canvas.drawRightString(left - 0.15 * cm, y - 2, _format_number(vmin + (vmax - vmin) * step / 4, 0 if vmax > 100 else 1))

            count = len(self.labels)

            def xpos(index: int) -> float:
                return left + plot_w * index / max(count - 1, 1)

            def ypos(value: float) -> float:
                return bottom + (value - vmin) / (vmax - vmin) * plot_h

            for item in self.series:
                color = HexColor(item.get("color", "#1f6feb"))
                points = [(xpos(index), ypos(value)) for index, value in enumerate(item["values"]) if value is not None]
                canvas.setStrokeColor(color)
                canvas.setLineWidth(1.7)
                for first, second in zip(points, points[1:]):
                    canvas.line(first[0], first[1], second[0], second[1])
                canvas.setFillColor(color)
                for x, y in points:
                    canvas.circle(x, y, 2.0, fill=1, stroke=0)

            canvas.setFillColor(muted)
            canvas.setFont(base_font, 6.2)
            for index, label in enumerate(self.labels):
                if count <= 8 or index in (0, count - 1) or index % 2 == 0:
                    canvas.drawCentredString(xpos(index), bottom - 0.34 * cm, label[5:])

            legend_x, legend_y = left, 0.16 * cm
            for item in self.series:
                color = HexColor(item.get("color", "#1f6feb"))
                canvas.setFillColor(color)
                canvas.rect(legend_x, legend_y + 2, 8, 5, fill=1, stroke=0)
                canvas.setFillColor(text)
                canvas.setFont(base_font, 6.7)
                canvas.drawString(legend_x + 12, legend_y, item["name"])
                legend_x += 3.5 * cm

    class HorizontalBars(Flowable):
        def __init__(self, title: str, rows: list[tuple[str, float, Any]], width: float = 17.0 * cm, height: float | None = None, unit: str = "%"):
            super().__init__()
            self.title = title
            self.rows = rows
            self.width = width
            self.unit = unit
            self.height = height or (1.15 * cm + max(1, len(rows)) * 0.56 * cm)

        def draw(self):
            canvas = self.canv
            canvas.setFillColor(text)
            canvas.setFont(bold_base_font, 9.3)
            canvas.drawString(0, self.height - 0.28 * cm, self.title)
            if not self.rows:
                canvas.setFont(base_font, 8)
                canvas.drawString(0, self.height - 0.85 * cm, "Veri yok")
                return
            left = 3.2 * cm
            bar_w = self.width - left - 1.2 * cm
            max_value = max(value for _, value, *_ in self.rows) or 1
            y = self.height - 0.85 * cm
            palette = [blue, green, orange, purple, teal, red]
            for index, row in enumerate(self.rows):
                label, value = row[0], row[1]
                color = row[2] if len(row) > 2 and row[2] else palette[index % len(palette)]
                canvas.setFillColor(text)
                canvas.setFont(base_font, 7.4)
                canvas.drawString(0, y + 2, str(label))
                canvas.setFillColor(HexColor("#eef2f7"))
                canvas.roundRect(left, y, bar_w, 0.26 * cm, 3, fill=1, stroke=0)
                canvas.setFillColor(color)
                canvas.roundRect(left, y, bar_w * value / max_value, 0.26 * cm, 3, fill=1, stroke=0)
                canvas.setFillColor(text)
                canvas.setFont(bold_base_font, 7.0)
                canvas.drawRightString(self.width, y + 2, f"{value:.1f}{self.unit}")
                y -= 0.54 * cm

    patient = model["patient"]
    coverage = model["coverage"]
    sensor = model["sensors"]
    behavior = model["behavior"]
    ai = model["ai"]

    temp = sensor["stats"]["temperature"]
    hum = sensor["stats"]["humidity"]
    oxy = sensor["stats"]["oxygen"]
    co2 = sensor["stats"]["co2"]
    temp_tw = sensor["time_weighted"]["temperature"]
    hum_tw = sensor["time_weighted"]["humidity"]
    oxy_tw = sensor["time_weighted"]["oxygen"]
    co2_tw = sensor["time_weighted"]["co2"]

    story = []
    story.append(Spacer(1, 0.35 * cm))
    story.append(para("Kuvoz İzlem Raporu", "TitleK"))
    story.append(para("Hasta, çevresel sensör, kamera davranışı ve AI vital kayıtlarının özet analizi", "SubK"))
    story.append(make_table([
        ["Alan", "Değer", "Alan", "Değer"],
        ["Hasta", patient.get("name") or "-", "Tür / Irk", f"{patient.get('species') or '-'} / {patient.get('breed') or '-'}"],
        ["Yaş / Kilo", f"{patient.get('age') or '-'} / {patient.get('weight') or '-'} kg", "Tanı", patient.get("diagnosis") or "-"],
        ["Yatış", f"{patient.get('admissionDate') or '-'} {patient.get('admissionTime') or ''}", "Tedavi", patient.get("currentTreatment") or "-"],
        ["Rapor tarihi", generated_at.strftime("%Y-%m-%d %H:%M"), "Dönem", f"Son {days:g} gün" if days else "Seçili kayıtlar"],
    ], widths=[2.7 * cm, 5.7 * cm, 2.5 * cm, 6.1 * cm]))
    story.append(Spacer(1, 0.35 * cm))
    story.append(KPIBox([
        {"value": f"{coverage['behavior']['count']:,}".replace(",", "."), "label": "Davranış kaydı", "note": f"{_format_dt(coverage['behavior']['first'])[:10]} - {_format_dt(coverage['behavior']['last'])[:10]}", "color": "#1f6feb", "bg": "#eef5ff"},
        {"value": f"{coverage['sensor']['count']:,}".replace(",", "."), "label": "Sensör kaydı", "note": f"{_format_dt(coverage['sensor']['first'])[:10]} - {_format_dt(coverage['sensor']['last'])[:10]}", "color": "#209a62", "bg": "#ecfdf5"},
        {"value": f"{coverage['ai']['count']:,}".replace(",", "."), "label": "AI vital kaydı", "note": f"{_format_dt(coverage['ai']['first'])[:10]} - {_format_dt(coverage['ai']['last'])[:10]}", "color": "#7c3aed", "bg": "#f4f0ff"},
        {"value": _format_number(hum_tw["avg"], 1, "%"), "label": "Ortalama nem", "note": "Zaman ağırlıklı", "color": "#d97706", "bg": "#fff7ed"},
    ]))
    story.append(Spacer(1, 0.25 * cm))
    story.append(para("Bu rapor klinik karar desteği amacıyla hazırlanmıştır; veteriner hekimin muayene, tedavi ve laboratuvar bulgularının yerine geçmez. Kamera tabanlı davranış ve AI solunum ölçümleri otomatik sınıflandırmadır.", "NoteK"))
    story.append(para("Yönetici Özeti", "H1K"))
    summary = [
        f"Sıcaklık zaman ağırlıklı ortalama {_format_number(temp_tw['avg'], 1, ' C')}; minimum {_format_number(temp['min'], 1, ' C')}, maksimum {_format_number(temp['max'], 1, ' C')}.",
        f"Nem zaman ağırlıklı ortalama {_format_number(hum_tw['avg'], 1, '%')}; hedef üstü dönemler cihaz/ortam koşullarıyla birlikte izlenmeli.",
        f"CO2 ortalaması {_format_number(co2_tw['avg'], 0, ' ppm')}; en yüksek kayıt {_format_number(co2['max'], 0, ' ppm')}.",
        f"Oksijen ortalaması {_format_number(oxy_tw['avg'], 1, '%')}; minimum {_format_number(oxy['min'], 1, '%')}.",
        "Davranış kayıtları gündüz/gece ritmi ve yeme-içme eğilimi için kullanılabilir.",
        "AI solunum bölümü sadece güvenilir OK kayıtlarıyla yorumlanmalıdır.",
    ]
    story.append(make_table([["Öne çıkan sonuçlar"]] + [[para("- " + item, "SmallK")] for item in summary], widths=[17 * cm]))

    story.append(PageBreak())
    story.append(para("Veri Kapsamı ve Çevresel Özet", "H1K"))
    story.append(make_table([
        ["Kayıt türü", "Kapsam", "Adet", "Kullanım değeri", "Sınırlama"],
        ["Çevresel sensör", f"{_format_dt(coverage['sensor']['first'])} - {_format_dt(coverage['sensor']['last'])}", f"{coverage['sensor']['count']:,}".replace(",", "."), "Sıcaklık, nem, oksijen, CO2 stabilite analizi", "Değişim/heartbeat bazlı kayıt; ham saniyelik veri değildir"],
        ["Davranış", f"{_format_dt(coverage['behavior']['first'])} - {_format_dt(coverage['behavior']['last'])}", f"{coverage['behavior']['count']:,}".replace(",", "."), "Gündüz/gece ritmi, yeme-içme ve aktivite eğilimleri", "Kamera/ROI doğruluğuna bağımlı"],
        ["AI vital", f"{_format_dt(coverage['ai']['first'])} - {_format_dt(coverage['ai']['last'])}", f"{coverage['ai']['count']:,}".replace(",", "."), "Solunum tahmini ve güven skoru takibi", "Düşük güven kayıtları klinik yorumdan ayrılmalı"],
    ], widths=[2.7 * cm, 4.1 * cm, 2.0 * cm, 4.2 * cm, 4.0 * cm]))
    story.append(Spacer(1, 0.25 * cm))
    story.append(make_table([
        ["Metrik", "Ortalama", "Minimum", "Maksimum", "Yorum"],
        ["Sıcaklık", _format_number(temp_tw["avg"], 1, " C"), _format_number(temp["min"], 1, " C"), _format_number(temp["max"], 1, " C"), "Hedef bandına göre izlenmeli"],
        ["Nem", _format_number(hum_tw["avg"], 1, "%"), _format_number(hum["min"], 0, "%"), _format_number(hum["max"], 0, "%"), "Yüksek nem dönemleri dikkat ister"],
        ["Oksijen", _format_number(oxy_tw["avg"], 1, "%"), _format_number(oxy["min"], 1, "%"), _format_number(oxy["max"], 1, "%"), "Düşük epizodlar olay bazlı incelenmeli"],
        ["CO2", _format_number(co2_tw["avg"], 0, " ppm"), _format_number(co2["min"], 0, " ppm"), _format_number(co2["max"], 0, " ppm"), "Havalandırma etkinliğiyle birlikte yorumlanmalı"],
    ], widths=[3.0 * cm, 2.4 * cm, 2.4 * cm, 2.4 * cm, 6.8 * cm]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(para("Kayıtlar anlamlı değişim ve heartbeat mantığıyla yazıldığı için raporda zaman ağırlıklı ortalamalar önceliklendirildi.", "CalloutK"))

    story.append(PageBreak())
    story.append(para("Çevresel Trendler", "H1K"))
    sensor_days = sensor["days"]
    series = sensor["series"]
    story.append(LineChart("Günlük sıcaklık ortalaması ve hedef", sensor_days, [
        {"name": "Sıcaklık", "values": series["temperature"], "color": "#c62828"},
        {"name": "Hedef sıcaklık", "values": series["target_temperature"], "color": "#5d6b78"},
    ], y_min=21.5, y_max=31.0))
    story.append(Spacer(1, 0.15 * cm))
    story.append(LineChart("Günlük nem ortalaması ve hedef", sensor_days, [
        {"name": "Nem", "values": series["humidity"], "color": "#1f6feb"},
        {"name": "Hedef nem", "values": series["target_humidity"], "color": "#5d6b78"},
    ], y_min=35, y_max=90))
    story.append(Spacer(1, 0.1 * cm))
    story.append(HorizontalBars("Nem bandı - zaman payı", [(item["label"], item["percent"], orange if item["label"] == ">70%" else green) for item in sensor["humidity_bands"]], height=3.3 * cm))

    story.append(PageBreak())
    story.append(para("Hava Kalitesi ve Gazlar", "H1K"))
    co2_daily_values = [value for value in series["co2"] if value is not None]
    story.append(LineChart("Günlük CO2 ortalaması", sensor_days, [
        {"name": "CO2 ppm", "values": series["co2"], "color": "#209a62"},
    ], y_min=350, y_max=max(1400, (max(co2_daily_values) if co2_daily_values else 1000) + 120)))
    story.append(Spacer(1, 0.15 * cm))
    story.append(LineChart("Günlük oksijen ortalaması", sensor_days, [
        {"name": "Oksijen %", "values": series["oxygen"], "color": "#008c8c"},
    ], y_min=16, y_max=21.5))
    story.append(Spacer(1, 0.1 * cm))
    story.append(HorizontalBars("CO2 bandı - zaman payı", [(item["label"], item["percent"], red if item["label"] == ">2000 ppm" else orange if "1200" in item["label"] else green) for item in sensor["co2_bands"]], height=3.4 * cm))
    story.append(HorizontalBars("Oksijen bandı - zaman payı", [(item["label"], item["percent"], red if item["label"] == "<18%" else green) for item in sensor["oxygen_bands"]], height=2.6 * cm))

    story.append(PageBreak())
    story.append(para("Davranış ve AI Vital Analizi", "H1K"))
    behavior_dist = behavior["distribution"]
    top_behavior = behavior_dist[0]["label"] if behavior_dist else "-"
    top_behavior_pct = behavior_dist[0]["percent"] if behavior_dist else 0
    story.append(KPIBox([
        {"value": f"{coverage['behavior']['count']:,}".replace(",", "."), "label": "Davranış kaydı", "note": "Kamera tabanlı", "color": "#1f6feb", "bg": "#eef5ff"},
        {"value": str(behavior["episode_counts"].get("feeding", 0)), "label": "Yeme epizodu", "note": "ROI türetilmiş", "color": "#d97706", "bg": "#fff7ed"},
        {"value": str(behavior["episode_counts"].get("drinking", 0)), "label": "İçme epizodu", "note": "ROI türetilmiş", "color": "#008c8c", "bg": "#ecfeff"},
        {"value": f"{top_behavior_pct:.0f}%", "label": f"Baskın durum: {top_behavior}", "note": "Süreye göre", "color": "#209a62", "bg": "#ecfdf5"},
    ]))
    story.append(Spacer(1, 0.15 * cm))
    story.append(HorizontalBars("Davranış süre dağılımı", [(item["label"], item["percent"], {"activity": blue, "resting": green, "drinking": teal, "feeding": orange}.get(item["label"], purple)) for item in behavior_dist], height=3.5 * cm))
    daypart_rows = [["Dönem", "Aktivite", "Dinlenme", "İçme", "Yeme"]]
    for daypart, rows in behavior["dayparts"].items():
        row_map = {item["label"]: item["percent"] for item in rows}
        daypart_rows.append([
            daypart,
            f"{row_map.get('activity', 0):.1f}%",
            f"{row_map.get('resting', 0):.1f}%",
            f"{row_map.get('drinking', 0):.1f}%",
            f"{row_map.get('feeding', 0):.1f}%",
        ])
    story.append(make_table(daypart_rows, widths=[4.0 * cm, 3.2 * cm, 3.2 * cm, 3.2 * cm, 3.2 * cm]))
    story.append(Spacer(1, 0.2 * cm))
    ai_total = sum(ai["status_counts"].values())
    ok_percent = ai["status_counts"].get("OK", 0) / ai_total * 100 if ai_total else 0
    story.append(KPIBox([
        {"value": str(ai_total), "label": "AI vital kaydı", "note": "Kamera vital", "color": "#7c3aed", "bg": "#f4f0ff"},
        {"value": f"{ok_percent:.0f}%", "label": "OK oranı", "note": "Kayıt bazında", "color": "#209a62", "bg": "#ecfdf5"},
        {"value": _format_number(ai["respiration"]["median"], 1, " bpm"), "label": "Medyan solunum", "note": "OK ve güven >= 0.60", "color": "#1f6feb", "bg": "#eef5ff"},
        {"value": _format_number(ai["confidence"]["avg"], 2), "label": "Ortalama güven", "note": "Tüm AI kayıtları", "color": "#d97706", "bg": "#fff7ed"},
    ]))
    story.append(HorizontalBars("AI durum dağılımı", [(label, count / ai_total * 100 if ai_total else 0, green if label == "OK" else orange if label == "LOW_CONF" else red) for label, count in ai["status_counts"].most_common()], height=3.2 * cm))
    story.append(para("Davranış ve AI sonuçları otomatik kamera sınıflandırmasıdır. Klinik yorum için kadraj, ışık, ROI hizası ve canlı gözlemle birlikte değerlendirilmelidir.", "NoteK"))

    story.append(PageBreak())
    story.append(para("Yorum ve Önerilen Takip", "H1K"))
    story.append(make_table([
        ["Öncelik", "Başlık", "Takip"],
        ["1", "Nem ve sıcaklık dengesi", "Hedef değerler ile gerçekleşen ortalamalar karşılaştırılmalı; uzun süreli sapmalar cihaz/ortam koşullarıyla birlikte incelenmeli."],
        ["2", "CO2 ve oksijen epizodları", "Yüksek CO2 veya düşük oksijen kayıtları kapak hareketi, fan durumu ve klinik gözlemle eşleştirilmeli."],
        ["3", "Davranış ROI doğrulaması", "Yeme/içme epizotları raporlanabilir; kap ve kamera hizası doğrulanırsa güvenilirlik artar."],
        ["4", "AI vital sürekliliği", "AI kayıt adedi düşükse kamera, estimator ve servis logları kontrol edilmeli."],
        ["5", "Hasta dosyası arşivi", "Bu PDF hasta dosyasına eklenebilir; sonraki hastada hasta bazlı arşiv ve veri temizleme politikası uygulanmalı."],
    ], widths=[1.5 * cm, 4.2 * cm, 11.3 * cm]))
    story.append(Spacer(1, 0.25 * cm))
    story.append(make_table([
        ["Kontrol", "Sonuç"],
        ["Hasta eşleşmesi", str(patient.get("id") or patient.get("name") or "Hasta seçilmedi")],
        ["Rapor veri kaynağı", "Canlı uygulama veritabanları: sensor_logs.db, behavior_logs.db, ai_vitals.db ve aktif hasta ayarları"],
        ["Klinik not", "Bulgular veteriner hekimin klinik kararıyla birlikte değerlendirilmelidir."],
    ], widths=[5.2 * cm, 11.8 * cm]))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(blue)
        canvas.setLineWidth(1.2)
        canvas.line(margin, page_h - margin + 0.2 * cm, page_w - margin, page_h - margin + 0.2 * cm)
        canvas.setFont(base_font, 7.2)
        canvas.setFillColor(muted)
        canvas.drawString(margin, 0.85 * cm, "Kuvoz izlem raporu - otomatik veri analizi")
        canvas.drawRightString(page_w - margin, 0.85 * cm, f"Sayfa {doc.page}")
        canvas.restoreState()

    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=margin,
        leftMargin=margin,
        topMargin=1.55 * cm,
        bottomMargin=1.35 * cm,
        title="Kuvoz İzlem Raporu",
        author="Kuvoz",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    output.seek(0)
    return output
