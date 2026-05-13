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
        subject_box=None,
        subject_tracking_locked=True,
        subject_tracking_confidence=0.72,
    ):
        return {
            "vision": {
                "status": vision_status,
                "activity": activity,
                "subject_box": subject_box,
                "subject_tracking_locked": subject_tracking_locked,
                "subject_tracking_confidence": subject_tracking_confidence,
            },
            "vitals": {
                "status": vital_status,
                "respiration_bpm": respiration_bpm,
                "confidence": confidence,
            },
        }

    def _make_drinking_settings(self):
        return {
            "drinking_roi_enabled": True,
            "drinking_roi": {
                "x": 0.60,
                "y": 0.55,
                "width": 0.10,
                "height": 0.18,
            },
        }

    def _make_feeding_settings(self):
        return {
            "feeding_roi_enabled": True,
            "feeding_roi": {
                "x": 0.72,
                "y": 0.55,
                "width": 0.10,
                "height": 0.20,
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
        self.assertEqual(event["behavior_subtype"], "camera_lifecycle")
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

    def test_resting_uses_camera_subject_lock_without_vital_requirement(self):
        now = datetime(2026, 3, 26, 12, 0, 0)
        event = self.mapper.consume(
            self._make_ai_data(
                vision_status="DURGUN",
                activity=0.4,
                vital_status="LOW_CONF",
                respiration_bpm=None,
                confidence=0.15,
                subject_box={
                    "x_norm": 0.30,
                    "y_norm": 0.30,
                    "width_norm": 0.40,
                    "height_norm": 0.45,
                },
                subject_tracking_locked=True,
                subject_tracking_confidence=0.44,
            ),
            patient_context=self.patient,
            now=now,
        )

        self.assertIsNotNone(event)
        self.assertEqual(event["behavior_type"], "resting")
        self.assertEqual(event["metadata"]["resting_basis"], "camera_subject_lock")

    def test_small_motion_is_ignored_while_resting(self):
        now = datetime(2026, 3, 26, 12, 0, 0)
        event = self.mapper.consume(
            self._make_ai_data(
                vision_status="HAREKETLI",
                activity=7.4,
                vital_status="NOT_ENOUGH_DATA",
                respiration_bpm=None,
                confidence=0.0,
            ),
            patient_context=self.patient,
            now=now,
        )

        self.assertIsNone(event)

    def test_moderate_motion_requires_confirmation(self):
        now = datetime(2026, 3, 26, 12, 0, 0)
        ai_data = self._make_ai_data(
            vision_status="HAREKETLI",
            activity=8.4,
            vital_status="NOT_ENOUGH_DATA",
            respiration_bpm=None,
            confidence=0.0,
        )

        first = self.mapper.consume(
            ai_data,
            patient_context=self.patient,
            now=now,
        )
        second = self.mapper.consume(
            ai_data,
            patient_context=self.patient,
            now=now + timedelta(seconds=3),
        )
        third = self.mapper.consume(
            ai_data,
            patient_context=self.patient,
            now=now + timedelta(seconds=6),
        )

        self.assertIsNone(first)
        self.assertIsNone(second)
        self.assertIsNotNone(third)
        self.assertEqual(third["behavior_type"], "activity")

    def test_drinking_requires_sustained_roi_contact(self):
        now = datetime(2026, 3, 26, 12, 0, 0)
        ai_data = self._make_ai_data(
            vision_status="DURGUN",
            activity=4.0,
            vital_status="LOW_CONF",
            respiration_bpm=None,
            confidence=0.2,
            subject_box={
                "x_norm": 0.58,
                "y_norm": 0.54,
                "width_norm": 0.18,
                "height_norm": 0.18,
            },
        )
        settings = self._make_drinking_settings()

        first = self.mapper.consume(
            ai_data,
            patient_context=self.patient,
            system_settings=settings,
            now=now,
        )
        second = self.mapper.consume(
            ai_data,
            patient_context=self.patient,
            system_settings=settings,
            now=now + timedelta(seconds=2),
        )
        third = self.mapper.consume(
            ai_data,
            patient_context=self.patient,
            system_settings=settings,
            now=now + timedelta(seconds=5),
        )

        self.assertIsNone(first)
        self.assertIsNone(second)
        self.assertIsNotNone(third)
        self.assertEqual(third["behavior_type"], "drinking")
        self.assertEqual(third["metadata"]["event_reason"], "state_change")
        self.assertGreaterEqual(third["duration"], 5)

    def test_feeding_requires_sustained_roi_contact(self):
        now = datetime(2026, 3, 26, 12, 0, 0)
        ai_data = self._make_ai_data(
            vision_status="DURGUN",
            activity=6.0,
            vital_status="LOW_CONF",
            respiration_bpm=None,
            confidence=0.2,
            subject_box={
                "x_norm": 0.69,
                "y_norm": 0.54,
                "width_norm": 0.16,
                "height_norm": 0.18,
            },
        )
        settings = self._make_feeding_settings()

        first = self.mapper.consume(
            ai_data,
            patient_context=self.patient,
            system_settings=settings,
            now=now,
        )
        second = self.mapper.consume(
            ai_data,
            patient_context=self.patient,
            system_settings=settings,
            now=now + timedelta(seconds=3),
        )
        third = self.mapper.consume(
            ai_data,
            patient_context=self.patient,
            system_settings=settings,
            now=now + timedelta(seconds=6),
        )

        self.assertIsNone(first)
        self.assertIsNone(second)
        self.assertIsNotNone(third)
        self.assertEqual(third["behavior_type"], "feeding")
        self.assertEqual(third["metadata"]["event_reason"], "state_change")
        self.assertGreaterEqual(third["duration"], 6)

    def test_feeding_can_use_roi_side_as_head_direction(self):
        now = datetime(2026, 3, 26, 12, 0, 0)
        settings = {
            "feeding_roi_enabled": True,
            "feeding_roi": {
                "x": 0.16,
                "y": 0.80,
                "width": 0.25,
                "height": 0.16,
            },
        }
        ai_data = self._make_ai_data(
            vision_status="HAREKETLI",
            activity=16.0,
            vital_status="LOW_CONF",
            respiration_bpm=None,
            confidence=0.0,
            subject_box={
                "x_norm": 0.27,
                "y_norm": 0.40,
                "width_norm": 0.51,
                "height_norm": 0.48,
            },
        )

        first = self.mapper.consume(
            ai_data,
            patient_context=self.patient,
            system_settings=settings,
            now=now,
        )
        second = self.mapper.consume(
            ai_data,
            patient_context=self.patient,
            system_settings=settings,
            now=now + timedelta(seconds=5),
        )

        self.assertIsNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(second["behavior_type"], "feeding")
        self.assertTrue(second["metadata"]["feeding_contact_point"]["x"] < 0.45)
        self.assertTrue(second["metadata"]["feeding_contact_point"]["y"] > 0.79)

    def test_feeding_can_win_when_bowl_contacts_overlap_in_time(self):
        now = datetime(2026, 3, 26, 12, 0, 0)
        settings = {
            "drinking_roi_enabled": True,
            "drinking_roi": {
                "x": 0.172,
                "y": 0.50,
                "width": 0.292,
                "height": 0.30,
            },
            "feeding_roi_enabled": True,
            "feeding_roi": {
                "x": 0.172,
                "y": 0.82,
                "width": 0.292,
                "height": 0.18,
            },
        }
        ai_data = self._make_ai_data(
            vision_status="HAREKETLI",
            activity=21.0,
            vital_status="LOW_CONF",
            respiration_bpm=None,
            confidence=0.0,
            subject_box={
                "x_norm": 0.303,
                "y_norm": 0.279,
                "width_norm": 0.473,
                "height_norm": 0.55,
            },
            subject_tracking_confidence=0.52,
        )

        first = self.mapper.consume(
            ai_data,
            patient_context=self.patient,
            system_settings=settings,
            now=now,
        )
        second = self.mapper.consume(
            ai_data,
            patient_context=self.patient,
            system_settings=settings,
            now=now + timedelta(seconds=5),
        )

        self.assertIsNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(second["behavior_type"], "feeding")

    def test_adjacent_rois_can_be_left_ambiguous(self):
        now = datetime(2026, 3, 26, 12, 0, 0)
        settings = {
            "drinking_roi_enabled": True,
            "drinking_roi": {
                "x": 0.60,
                "y": 0.55,
                "width": 0.14,
                "height": 0.18,
            },
            "feeding_roi_enabled": True,
            "feeding_roi": {
                "x": 0.66,
                "y": 0.55,
                "width": 0.14,
                "height": 0.18,
            },
        }
        event = self.mapper.consume(
            self._make_ai_data(
                vision_status="DURGUN",
                activity=5.0,
                vital_status="LOW_CONF",
                respiration_bpm=None,
                confidence=0.2,
                subject_box={
                    "x_norm": 0.60,
                    "y_norm": 0.55,
                    "width_norm": 0.20,
                    "height_norm": 0.18,
                },
            ),
            patient_context=self.patient,
            system_settings=settings,
            now=now,
        )

        self.assertIsNone(event)

    def test_drinking_does_not_override_high_motion_activity(self):
        now = datetime(2026, 3, 26, 12, 0, 0)
        event = self.mapper.consume(
            self._make_ai_data(
                vision_status="HAREKETLI",
                activity=32.0,
                vital_status="TOO_MUCH_MOTION",
                respiration_bpm=None,
                confidence=0.0,
                subject_box={
                    "x_norm": 0.58,
                    "y_norm": 0.54,
                    "width_norm": 0.18,
                    "height_norm": 0.18,
                },
            ),
            patient_context=self.patient,
            system_settings=self._make_drinking_settings(),
            now=now,
        )

        self.assertIsNotNone(event)
        self.assertEqual(event["behavior_type"], "activity")

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
