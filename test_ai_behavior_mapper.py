import unittest
from datetime import datetime, timedelta

from lib.data.ai_behavior_mapper import AIBehaviorMapper


class AIBehaviorMapperTests(unittest.TestCase):
    def setUp(self):
        self.mapper = AIBehaviorMapper(heartbeat_interval=300)
        self.patient = {"id": "2026-03-23_Morbius", "name": "Morbius"}

    def _make_ai_data(
        self,
        *,
        vision_status="DURGUN",
        activity=0.0,
        vital_status="OK",
        respiration_bpm=18.0,
        confidence=0.72,
    ):
        return {
            "vision": {
                "status": vision_status,
                "activity": activity,
            },
            "vitals": {
                "status": vital_status,
                "respiration_bpm": respiration_bpm,
                "confidence": confidence,
            },
        }

    def test_activity_logs_on_state_change(self):
        now = datetime(2026, 3, 26, 12, 0, 0)
        event = self.mapper.consume(
            self._make_ai_data(vision_status="HAREKETLI", activity=42.0, vital_status="TOO_MUCH_MOTION", respiration_bpm=None, confidence=0.0),
            patient_context=self.patient,
            now=now,
        )

        self.assertIsNotNone(event)
        self.assertEqual(event["behavior_type"], "activity")
        self.assertEqual(event["behavior_subtype"], "ai_derived")
        self.assertEqual(event["metadata"]["event_reason"], "state_change")

    def test_same_state_waits_for_heartbeat(self):
        now = datetime(2026, 3, 26, 12, 0, 0)
        self.mapper.consume(
            self._make_ai_data(vision_status="HAREKETLI", activity=32.0, vital_status="TOO_MUCH_MOTION", respiration_bpm=None, confidence=0.0),
            patient_context=self.patient,
            now=now,
        )

        event = self.mapper.consume(
            self._make_ai_data(vision_status="HAREKETLI", activity=38.0, vital_status="TOO_MUCH_MOTION", respiration_bpm=None, confidence=0.0),
            patient_context=self.patient,
            now=now + timedelta(seconds=120),
        )

        self.assertIsNone(event)

    def test_heartbeat_relogs_same_state(self):
        now = datetime(2026, 3, 26, 12, 0, 0)
        self.mapper.consume(
            self._make_ai_data(vision_status="HAREKETLI", activity=24.0, vital_status="TOO_MUCH_MOTION", respiration_bpm=None, confidence=0.0),
            patient_context=self.patient,
            now=now,
        )

        event = self.mapper.consume(
            self._make_ai_data(vision_status="HAREKETLI", activity=28.0, vital_status="TOO_MUCH_MOTION", respiration_bpm=None, confidence=0.0),
            patient_context=self.patient,
            now=now + timedelta(seconds=301),
        )

        self.assertIsNotNone(event)
        self.assertEqual(event["metadata"]["event_reason"], "heartbeat")
        self.assertGreaterEqual(event["duration"], 301)

    def test_resting_requires_reliable_low_motion_vitals(self):
        now = datetime(2026, 3, 26, 12, 0, 0)
        event = self.mapper.consume(
            self._make_ai_data(vision_status="DURGUN", activity=0.4, vital_status="OK", respiration_bpm=16.8, confidence=0.71),
            patient_context=self.patient,
            now=now,
        )

        self.assertIsNotNone(event)
        self.assertEqual(event["behavior_type"], "resting")

    def test_uncertain_snapshot_resets_state(self):
        now = datetime(2026, 3, 26, 12, 0, 0)
        first = self.mapper.consume(
            self._make_ai_data(vision_status="HAREKETLI", activity=18.0, vital_status="TOO_MUCH_MOTION", respiration_bpm=None, confidence=0.0),
            patient_context=self.patient,
            now=now,
        )
        self.assertIsNotNone(first)

        second = self.mapper.consume(
            self._make_ai_data(vision_status="DURGUN", activity=0.3, vital_status="LOW_CONF", respiration_bpm=None, confidence=0.2),
            patient_context=self.patient,
            now=now + timedelta(seconds=30),
        )
        self.assertIsNone(second)

        third = self.mapper.consume(
            self._make_ai_data(vision_status="HAREKETLI", activity=20.0, vital_status="TOO_MUCH_MOTION", respiration_bpm=None, confidence=0.0),
            patient_context=self.patient,
            now=now + timedelta(seconds=40),
        )
        self.assertIsNotNone(third)
        self.assertEqual(third["metadata"]["event_reason"], "state_change")


if __name__ == "__main__":
    unittest.main()
