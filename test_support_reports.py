import datetime
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from app.services.support_reports import (
    append_support_report,
    load_support_reports,
    normalize_support_report_payload,
    update_support_report,
)


class SupportReportTests(unittest.TestCase):
    def test_normalize_requires_message(self):
        with self.assertRaises(ValueError):
            normalize_support_report_payload({"type": "issue", "message": "   "})

    def test_append_support_report_persists_normalized_record(self):
        now = datetime.datetime(2026, 5, 14, 12, 30, tzinfo=datetime.timezone.utc)
        uuid_factory = Mock(return_value=type("Uuid", (), {"hex": "abcdef123456"})())

        with tempfile.TemporaryDirectory() as tmp_dir:
            reports_file = str(Path(tmp_dir) / "support_reports.json")
            report = append_support_report(
                reports_file,
                {
                    "type": "request",
                    "priority": "high",
                    "title": "Yeni alarm filtresi",
                    "message": "Alarm listesinde sadece kritik olanları görmek istiyoruz.",
                    "reporter": "Klinik",
                },
                context={
                    "ip": "127.0.0.1",
                    "patient": {"name": "Boncuk", "species": "cat"},
                    "snapshot": {
                        "sensors": {"temperature": {"value": 31.5}},
                        "buttons": {"b4": True},
                        "gpio_outputs": {"b4": True},
                        "system": {"gpio_available": True, "simulation_mode": False},
                    },
                },
                now=now,
                uuid_factory=uuid_factory,
            )

            reports = load_support_reports(reports_file)

        self.assertEqual(report["id"], "SR-20260514-ABCDEF")
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["type"], "request")
        self.assertEqual(reports[0]["priority"], "high")
        self.assertEqual(reports[0]["status"], "open")
        self.assertEqual(reports[0]["patient"]["name"], "Boncuk")
        self.assertTrue(reports[0]["snapshot"]["buttons"]["b4"])

    def test_update_support_report_status_and_note(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            reports_file = str(Path(tmp_dir) / "support_reports.json")
            report = append_support_report(
                reports_file,
                {"message": "Nem ekrani bazen gec guncelleniyor."},
                now=datetime.datetime(2026, 5, 14, 10, 0, tzinfo=datetime.timezone.utc),
                uuid_factory=Mock(return_value=type("Uuid", (), {"hex": "111111abcdef"})()),
            )

            updated = update_support_report(
                reports_file,
                report["id"],
                {"status": "in_progress", "note": "Saha dönüşü bekleniyor."},
                now=datetime.datetime(2026, 5, 14, 10, 5, tzinfo=datetime.timezone.utc),
            )
            reports = load_support_reports(reports_file)

        self.assertEqual(updated["status"], "in_progress")
        self.assertEqual(reports[0]["status"], "in_progress")
        self.assertEqual(reports[0]["notes"][0]["text"], "Saha dönüşü bekleniyor.")


if __name__ == "__main__":
    unittest.main()
