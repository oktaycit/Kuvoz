"""Support report storage helpers for issue/request tracking."""

from __future__ import annotations

import datetime
import json
import os
import re
import threading
import uuid


VALID_REPORT_TYPES = {"issue", "request", "maintenance", "other"}
VALID_PRIORITIES = {"low", "normal", "high", "critical"}
VALID_STATUSES = {"open", "in_progress", "resolved", "closed"}
SUPPORT_REPORTS_LOCK = threading.Lock()


def _now_iso(now=None):
    if now is None:
        now = datetime.datetime.now().astimezone()
    if isinstance(now, datetime.datetime):
        if now.tzinfo is None:
            now = now.astimezone()
        return now.isoformat(timespec="seconds")
    return str(now)


def _clean_text(value, max_length, *, preserve_newlines=False):
    if value is None:
        return ""

    text = str(value).replace("\x00", "").strip()
    if preserve_newlines:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n"))
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
    else:
        text = re.sub(r"\s+", " ", text).strip()

    return text[:max_length].strip()


def _choice(value, valid_values, default):
    normalized = _clean_text(value, 40).lower()
    return normalized if normalized in valid_values else default


def _compact_mapping(value, allowed_keys):
    if not isinstance(value, dict):
        return {}
    compacted = {}
    for key in allowed_keys:
        item = value.get(key)
        if item is None:
            continue
        if isinstance(item, (str, int, float, bool)):
            compacted[key] = item
    return compacted


def _build_report_id(created_at, uuid_factory=uuid.uuid4):
    date_part = str(created_at)[:10].replace("-", "") or datetime.date.today().strftime("%Y%m%d")
    suffix = uuid_factory().hex[:6].upper()
    return f"SR-{date_part}-{suffix}"


def normalize_support_report_payload(payload, *, context=None, now=None, uuid_factory=uuid.uuid4):
    """Validate and normalize a user-submitted support report."""

    if not isinstance(payload, dict):
        raise ValueError("Geçersiz bildirim verisi")

    context = context if isinstance(context, dict) else {}
    created_at = _now_iso(now)
    report_type = _choice(payload.get("type"), VALID_REPORT_TYPES, "issue")
    priority = _choice(payload.get("priority"), VALID_PRIORITIES, "normal")
    title = _clean_text(payload.get("title"), 140)
    message = _clean_text(payload.get("message"), 2400, preserve_newlines=True)

    if not message:
        raise ValueError("Bildirim açıklaması zorunlu")
    if not title:
        first_line = message.splitlines()[0] if message.splitlines() else ""
        title = _clean_text(first_line, 100) or "Kuvoz bildirimi"

    snapshot = context.get("snapshot") if isinstance(context.get("snapshot"), dict) else {}
    system = snapshot.get("system") if isinstance(snapshot.get("system"), dict) else {}

    report = {
        "id": _build_report_id(created_at, uuid_factory=uuid_factory),
        "type": report_type,
        "priority": priority,
        "status": "open",
        "title": title,
        "message": message,
        "reporter": _clean_text(payload.get("reporter"), 80),
        "contact": _clean_text(payload.get("contact"), 120),
        "location": _clean_text(payload.get("location"), 120),
        "page": _clean_text(payload.get("page") or context.get("page"), 80),
        "created_at": created_at,
        "updated_at": created_at,
        "client": {
            "ip": _clean_text(context.get("ip"), 80),
            "user_agent": _clean_text(context.get("user_agent"), 240),
        },
        "patient": _compact_mapping(
            payload.get("patient") or context.get("patient"),
            ("id", "name", "species", "breed", "age", "weight", "ownerName"),
        ),
        "device": _compact_mapping(
            context.get("device"),
            ("hostname", "local_ip", "tailscale_ip", "git_hash", "git_branch"),
        ),
        "snapshot": {
            "sensors": snapshot.get("sensors") if isinstance(snapshot.get("sensors"), dict) else {},
            "buttons": snapshot.get("buttons") if isinstance(snapshot.get("buttons"), dict) else {},
            "gpio_outputs": snapshot.get("gpio_outputs") if isinstance(snapshot.get("gpio_outputs"), dict) else {},
            "system": _compact_mapping(
                system,
                (
                    "gpio_available",
                    "dht_available",
                    "oxygen_available",
                    "co2_available",
                    "ai_available",
                    "simulation_mode",
                ),
            ),
        },
        "notes": [],
    }

    return report


def ensure_support_report_storage(reports_file):
    reports_dir = os.path.dirname(reports_file)
    if reports_dir:
        os.makedirs(reports_dir, exist_ok=True)


def load_support_reports(reports_file):
    if not os.path.exists(reports_file):
        return []

    with open(reports_file, "r", encoding="utf-8") as handle:
        reports = json.load(handle)

    return reports if isinstance(reports, list) else []


def save_support_reports(reports_file, reports):
    ensure_support_report_storage(reports_file)
    tmp_file = f"{reports_file}.tmp"
    with open(tmp_file, "w", encoding="utf-8") as handle:
        json.dump(reports, handle, ensure_ascii=False, indent=2)
    os.replace(tmp_file, reports_file)


def append_support_report(reports_file, payload, *, context=None, max_reports=500, now=None, uuid_factory=uuid.uuid4):
    report = normalize_support_report_payload(
        payload,
        context=context,
        now=now,
        uuid_factory=uuid_factory,
    )
    with SUPPORT_REPORTS_LOCK:
        reports = load_support_reports(reports_file)
        reports.insert(0, report)
        save_support_reports(reports_file, reports[:max_reports])
    return report


def update_support_report(reports_file, report_id, updates, *, now=None):
    if not isinstance(updates, dict):
        raise ValueError("Geçersiz güncelleme verisi")

    report_id = _clean_text(report_id, 80)
    status = updates.get("status")
    note = _clean_text(updates.get("note"), 600, preserve_newlines=True)
    normalized_status = _choice(status, VALID_STATUSES, None) if status is not None else None

    if status is not None and normalized_status is None:
        raise ValueError("Geçersiz bildirim durumu")
    if status is None and not note:
        raise ValueError("Güncellenecek alan bulunamadı")

    with SUPPORT_REPORTS_LOCK:
        reports = load_support_reports(reports_file)
        updated_at = _now_iso(now)
        for report in reports:
            if report.get("id") != report_id:
                continue
            if normalized_status:
                report["status"] = normalized_status
            if note:
                report.setdefault("notes", []).insert(0, {
                    "text": note,
                    "created_at": updated_at,
                })
            report["updated_at"] = updated_at
            save_support_reports(reports_file, reports)
            return report

    raise KeyError(report_id)
