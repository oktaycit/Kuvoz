import unittest
from datetime import datetime

from app.services.patient_report import (
    build_report_model,
    safe_report_filename,
)


class PatientReportTests(unittest.TestCase):
    def test_build_report_model_summarizes_sensor_and_behavior_data(self):
        model = build_report_model(
            sensor_rows=[
                {
                    "timestamp": "2026-05-18T10:00:00",
                    "temperature": 25.0,
                    "humidity": 75.0,
                    "oxygen": 20.2,
                    "co2": 700,
                    "target_temperature": 25.0,
                    "target_humidity": 50.0,
                    "fan_state": 1,
                    "fan_manual": 1,
                },
                {
                    "timestamp": "2026-05-18T10:15:00",
                    "temperature": 26.0,
                    "humidity": 80.0,
                    "oxygen": 19.8,
                    "co2": 1300,
                    "target_temperature": 25.0,
                    "target_humidity": 50.0,
                    "fan_state": 1,
                    "fan_manual": 1,
                },
                {
                    "timestamp": "2026-05-18T10:30:00",
                    "temperature": 26.5,
                    "humidity": 82.0,
                    "oxygen": 19.5,
                    "co2": 900,
                    "target_temperature": 25.0,
                    "target_humidity": 50.0,
                    "fan_state": 1,
                    "fan_manual": 1,
                },
            ],
            ai_rows=[
                {
                    "timestamp": "2026-05-18T10:05:00",
                    "respiration_bpm": 22.0,
                    "confidence": 0.80,
                    "status": "OK",
                },
                {
                    "timestamp": "2026-05-18T10:20:00",
                    "confidence": 0.20,
                    "status": "LOW_CONF",
                },
            ],
            behavior_rows=[
                {"timestamp": "2026-05-18T10:00:00", "behavior_type": "activity"},
                {"timestamp": "2026-05-18T10:05:00", "behavior_type": "activity"},
                {"timestamp": "2026-05-18T10:12:00", "behavior_type": "resting"},
            ],
            patient={"id": "2026-05-18_Test", "name": "Test"},
            days=1,
            generated_at=datetime(2026, 5, 18, 12, 0),
        )

        self.assertEqual(model["coverage"]["sensor"]["count"], 3)
        self.assertEqual(model["coverage"]["behavior"]["count"], 3)
        self.assertAlmostEqual(model["sensors"]["stats"]["humidity"]["avg"], 79.0)
        self.assertEqual(model["ai"]["status_counts"]["OK"], 1)
        self.assertEqual(model["ai"]["respiration"]["median"], 22.0)
        self.assertEqual(model["behavior"]["episode_counts"]["activity"], 1)
        self.assertEqual(model["sensors"]["humidity_bands"][0]["label"], ">70%")
        self.assertAlmostEqual(model["sensors"]["co2_context"]["high_with_manual_fan_hours"], 0.25)
        self.assertGreater(model["sensors"]["co2_context"]["high_percent"], 0)

    def test_safe_report_filename_normalizes_turkish_patient_name(self):
        filename = safe_report_filename(
            {"name": "Şeker Özel"},
            generated_at=datetime(2026, 5, 18, 9, 0),
        )
        self.assertEqual(filename, "seker_ozel_kuvoz_izlem_raporu_2026-05-18.pdf")


if __name__ == "__main__":
    unittest.main()
