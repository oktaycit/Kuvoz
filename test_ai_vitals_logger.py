import gc
import os
import unittest
from datetime import datetime, timedelta

from lib.data.ai_vitals_logger import AIVitalsLogger


class AIVitalsLoggerMotionTests(unittest.TestCase):
    def _db_path(self) -> str:
        return os.path.join(os.getcwd(), "test_ai_vitals_logger.db")

    def _make_ai_data(
        self,
        *,
        status="TOO_MUCH_MOTION",
        vision_status="HAREKETLI",
        activity=45.0,
        respiration_bpm=None,
        confidence=0.0,
    ):
        return {
            "vitals": {
                "status": status,
                "respiration_bpm": respiration_bpm,
                "confidence": confidence,
                "method": "activity_peaks",
            },
            "vision": {
                "status": vision_status,
                "activity": activity,
            },
        }

    def test_repeated_motion_noise_is_throttled_until_motion_heartbeat(self):
        db_path = self._db_path()
        if os.path.exists(db_path):
            os.remove(db_path)

        logger = None
        try:
            logger = AIVitalsLogger(db_path=db_path, min_interval=15, heartbeat_interval=60)

            first = self._make_ai_data(activity=18.0)
            second = self._make_ai_data(activity=92.0)

            self.assertTrue(logger.log_if_changed(first))
            self.assertEqual(logger.get_record_count(), 1)

            logger.last_log_time = datetime.now() - timedelta(seconds=5)
            self.assertFalse(logger.log_if_changed(second))
            self.assertEqual(logger.get_record_count(), 1)

            logger.last_log_time = datetime.now() - timedelta(seconds=61)
            self.assertTrue(logger.log_if_changed(second))
            self.assertEqual(logger.get_record_count(), 2)
        finally:
            logger = None
            gc.collect()
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_motion_to_reliable_ok_still_logs_after_motion_interval(self):
        db_path = self._db_path()
        if os.path.exists(db_path):
            os.remove(db_path)

        logger = None
        try:
            logger = AIVitalsLogger(db_path=db_path, min_interval=15, heartbeat_interval=60)

            self.assertTrue(
                logger.log_if_changed(
                    self._make_ai_data(status="TOO_MUCH_MOTION", activity=56.0)
                )
            )

            logger.last_log_time = datetime.now() - timedelta(seconds=31)
            self.assertTrue(
                logger.log_if_changed(
                    self._make_ai_data(
                        status="OK",
                        activity=32.0,
                        respiration_bpm=27.5,
                        confidence=0.74,
                    )
                )
            )

            latest = logger.get_latest_reading()
            self.assertIsNotNone(latest)
            self.assertEqual(latest["status"], "OK")
            self.assertEqual(latest["vision_status"], "HAREKETLI")
            self.assertEqual(logger.get_record_count(), 2)
        finally:
            logger = None
            gc.collect()
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_motion_recovery_to_still_low_signal_is_suppressed(self):
        db_path = self._db_path()
        if os.path.exists(db_path):
            os.remove(db_path)

        logger = None
        try:
            logger = AIVitalsLogger(db_path=db_path, min_interval=15, heartbeat_interval=60)

            self.assertTrue(
                logger.log_if_changed(
                    self._make_ai_data(status="LOW_CONF", vision_status="HAREKETLI", activity=28.0, confidence=0.15)
                )
            )

            logger.last_log_time = datetime.now() - timedelta(seconds=5)
            self.assertFalse(
                logger.log_if_changed(
                    self._make_ai_data(status="LOW_CONF", vision_status="DURGUN", activity=0.0, confidence=0.15)
                )
            )
            self.assertEqual(logger.get_record_count(), 1)
        finally:
            logger = None
            gc.collect()
            if os.path.exists(db_path):
                os.remove(db_path)


if __name__ == "__main__":
    unittest.main()

