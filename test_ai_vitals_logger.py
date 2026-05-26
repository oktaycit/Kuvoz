import gc
import os
import logging
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

    def test_repeated_motion_noise_is_event_based_without_heartbeat(self):
        db_path = self._db_path()
        if os.path.exists(db_path):
            os.remove(db_path)

        logger = None
        try:
            logger = AIVitalsLogger(db_path=db_path, min_interval=15, heartbeat_interval=0)

            first = self._make_ai_data(activity=18.0)
            second = self._make_ai_data(activity=92.0)

            self.assertTrue(logger.log_if_changed(first))
            self.assertEqual(logger.get_record_count(), 1)

            logger.last_log_time = datetime.now() - timedelta(seconds=5)
            self.assertFalse(logger.log_if_changed(second))
            self.assertEqual(logger.get_record_count(), 1)

            logger.last_log_time = datetime.now() - timedelta(seconds=61)
            self.assertFalse(logger.log_if_changed(second))
            self.assertEqual(logger.get_record_count(), 1)
        finally:
            logger = None
            gc.collect()
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_unstable_snapshot_logs_periodic_heartbeat_when_enabled(self):
        db_path = self._db_path()
        if os.path.exists(db_path):
            os.remove(db_path)

        logger = None
        try:
            logger = AIVitalsLogger(db_path=db_path, min_interval=15, heartbeat_interval=30)

            self.assertTrue(
                logger.log_if_changed(
                    self._make_ai_data(status="NOT_ENOUGH_DATA", vision_status="DURGUN", activity=0.0)
                )
            )

            logger.last_log_time = datetime.now() - timedelta(seconds=29)
            self.assertFalse(
                logger.log_if_changed(
                    self._make_ai_data(status="NOT_ENOUGH_DATA", vision_status="DURGUN", activity=0.0)
                )
            )

            logger.last_log_time = datetime.now() - timedelta(seconds=31)
            self.assertTrue(
                logger.log_if_changed(
                    self._make_ai_data(status="NOT_ENOUGH_DATA", vision_status="DURGUN", activity=0.0)
                )
            )
            self.assertEqual(logger.get_record_count(), 2)
        finally:
            logger = None
            gc.collect()
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_motion_vision_status_flap_is_suppressed(self):
        db_path = self._db_path()
        if os.path.exists(db_path):
            os.remove(db_path)

        logger = None
        try:
            logger = AIVitalsLogger(db_path=db_path, min_interval=15, heartbeat_interval=0)

            self.assertTrue(
                logger.log_if_changed(
                    self._make_ai_data(status="TOO_MUCH_MOTION", vision_status="HAREKETLI", activity=28.0)
                )
            )

            logger.last_log_time = datetime.now() - timedelta(seconds=16)
            self.assertFalse(
                logger.log_if_changed(
                    self._make_ai_data(status="TOO_MUCH_MOTION", vision_status="DURGUN", activity=0.0)
                )
            )
            self.assertEqual(logger.get_record_count(), 1)
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
            logger = AIVitalsLogger(db_path=db_path, min_interval=15, heartbeat_interval=0)

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

    def test_significant_reliable_ok_change_waits_for_stable_interval(self):
        db_path = self._db_path()
        if os.path.exists(db_path):
            os.remove(db_path)

        logger = None
        try:
            logger = AIVitalsLogger(db_path=db_path, min_interval=15, heartbeat_interval=0)

            self.assertTrue(
                logger.log_if_changed(
                    self._make_ai_data(
                        status="OK",
                        vision_status="DURGUN",
                        activity=0.0,
                        respiration_bpm=20.0,
                        confidence=0.82,
                    )
                )
            )

            logger.last_log_time = datetime.now() - timedelta(seconds=6)
            self.assertFalse(
                logger.log_if_changed(
                    self._make_ai_data(
                        status="OK",
                        vision_status="DURGUN",
                        activity=0.0,
                        respiration_bpm=26.5,
                        confidence=0.82,
                    )
                )
            )
            self.assertEqual(logger.get_record_count(), 1)

            logger.last_log_time = datetime.now() - timedelta(
                seconds=logger.STABLE_OK_MIN_INTERVAL + 1
            )
            self.assertTrue(
                logger.log_if_changed(
                    self._make_ai_data(
                        status="OK",
                        vision_status="DURGUN",
                        activity=0.0,
                        respiration_bpm=26.5,
                        confidence=0.82,
                    )
                )
            )
            self.assertEqual(logger.get_record_count(), 2)
        finally:
            logger = None
            gc.collect()
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_ok_snapshot_below_confidence_threshold_is_ignored(self):
        db_path = self._db_path()
        if os.path.exists(db_path):
            os.remove(db_path)

        logger = None
        try:
            logger = AIVitalsLogger(db_path=db_path, min_interval=15, heartbeat_interval=0)

            self.assertFalse(
                logger.log_if_changed(
                    self._make_ai_data(
                        status="OK",
                        vision_status="DURGUN",
                        activity=0.0,
                        respiration_bpm=22.0,
                        confidence=0.58,
                    )
                )
            )
            self.assertEqual(logger.get_record_count(), 0)
        finally:
            logger = None
            gc.collect()
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_reliable_ok_snapshots_use_slower_stable_interval(self):
        db_path = self._db_path()
        if os.path.exists(db_path):
            os.remove(db_path)

        logger = None
        try:
            logger = AIVitalsLogger(db_path=db_path, min_interval=15, heartbeat_interval=0)

            self.assertTrue(
                logger.log_if_changed(
                    self._make_ai_data(
                        status="OK",
                        vision_status="DURGUN",
                        activity=0.0,
                        respiration_bpm=18.0,
                        confidence=0.74,
                    )
                )
            )

            logger.last_log_time = datetime.now() - timedelta(seconds=20)
            self.assertFalse(
                logger.log_if_changed(
                    self._make_ai_data(
                        status="OK",
                        vision_status="DURGUN",
                        activity=0.0,
                        respiration_bpm=26.0,
                        confidence=0.78,
                    )
                )
            )
            self.assertEqual(logger.get_record_count(), 1)

            logger.last_log_time = datetime.now() - timedelta(
                seconds=logger.STABLE_OK_MIN_INTERVAL + 1
            )
            self.assertTrue(
                logger.log_if_changed(
                    self._make_ai_data(
                        status="OK",
                        vision_status="DURGUN",
                        activity=0.0,
                        respiration_bpm=26.0,
                        confidence=0.78,
                    )
                )
            )
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
            logger = AIVitalsLogger(db_path=db_path, min_interval=15, heartbeat_interval=0)

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

    def test_low_signal_status_flap_is_event_based_without_heartbeat(self):
        db_path = self._db_path()
        if os.path.exists(db_path):
            os.remove(db_path)

        logger = None
        try:
            logger = AIVitalsLogger(db_path=db_path, min_interval=15, heartbeat_interval=0)

            self.assertTrue(
                logger.log_if_changed(
                    self._make_ai_data(
                        status="LOW_CONF",
                        vision_status="DURGUN",
                        activity=0.0,
                        confidence=0.15,
                    )
                )
            )

            logger.last_log_time = datetime.now() - timedelta(seconds=16)
            self.assertFalse(
                logger.log_if_changed(
                    self._make_ai_data(
                        status="NOT_ENOUGH_DATA",
                        vision_status="DURGUN",
                        activity=0.0,
                        confidence=0.15,
                    )
                )
            )
            self.assertEqual(logger.get_record_count(), 1)

            logger.last_log_time = datetime.now() - timedelta(seconds=16 * 60)
            self.assertTrue(
                logger.log_if_changed(
                    self._make_ai_data(
                        status="OK",
                        vision_status="DURGUN",
                        activity=0.0,
                        respiration_bpm=24.0,
                        confidence=0.78,
                    )
                )
            )
            self.assertEqual(logger.get_record_count(), 2)
        finally:
            logger = None
            gc.collect()
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_low_conf_and_motion_transitions_stay_in_same_unstable_episode(self):
        db_path = self._db_path()
        if os.path.exists(db_path):
            os.remove(db_path)

        logger = None
        try:
            logger = AIVitalsLogger(db_path=db_path, min_interval=15, heartbeat_interval=0)

            self.assertTrue(
                logger.log_if_changed(
                    self._make_ai_data(
                        status="LOW_CONF",
                        vision_status="HAREKETLI",
                        activity=14.0,
                        respiration_bpm=31.5,
                        confidence=0.44,
                    )
                )
            )

            logger.last_log_time = datetime.now() - timedelta(seconds=16)
            self.assertFalse(
                logger.log_if_changed(
                    self._make_ai_data(
                        status="TOO_MUCH_MOTION",
                        vision_status="DURGUN",
                        activity=0.0,
                        respiration_bpm=None,
                        confidence=0.0,
                    )
                )
            )
            self.assertEqual(logger.get_record_count(), 1)
        finally:
            logger = None
            gc.collect()
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_activity_and_vision_changes_do_not_create_new_event(self):
        db_path = self._db_path()
        if os.path.exists(db_path):
            os.remove(db_path)

        logger = None
        try:
            logger = AIVitalsLogger(db_path=db_path, min_interval=15, heartbeat_interval=0)

            self.assertTrue(
                logger.log_if_changed(
                    self._make_ai_data(
                        status="OK",
                        vision_status="DURGUN",
                        activity=2.0,
                        respiration_bpm=24.0,
                        confidence=0.80,
                    )
                )
            )

            logger.last_log_time = datetime.now() - timedelta(seconds=16)
            self.assertFalse(
                logger.log_if_changed(
                    self._make_ai_data(
                        status="OK",
                        vision_status="HAREKETLI",
                        activity=36.0,
                        respiration_bpm=24.0,
                        confidence=0.80,
                    )
                )
            )
            self.assertEqual(logger.get_record_count(), 1)
        finally:
            logger = None
            gc.collect()
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_small_ok_fluctuation_is_ignored_but_large_shift_logs(self):
        db_path = self._db_path()
        if os.path.exists(db_path):
            os.remove(db_path)

        logger = None
        try:
            logger = AIVitalsLogger(db_path=db_path, min_interval=15, heartbeat_interval=0)

            self.assertTrue(
                logger.log_if_changed(
                    self._make_ai_data(
                        status="OK",
                        vision_status="DURGUN",
                        activity=0.0,
                        respiration_bpm=24.0,
                        confidence=0.80,
                    )
                )
            )

            logger.last_log_time = datetime.now() - timedelta(seconds=16)
            self.assertFalse(
                logger.log_if_changed(
                    self._make_ai_data(
                        status="OK",
                        vision_status="DURGUN",
                        activity=0.0,
                        respiration_bpm=27.0,
                        confidence=0.84,
                    )
                )
            )
            self.assertEqual(logger.get_record_count(), 1)

            logger.last_log_time = datetime.now() - timedelta(
                seconds=logger.STABLE_OK_MIN_INTERVAL + 1
            )
            self.assertTrue(
                logger.log_if_changed(
                    self._make_ai_data(
                        status="OK",
                        vision_status="DURGUN",
                        activity=0.0,
                        respiration_bpm=30.0,
                        confidence=0.80,
                    )
                )
            )
            self.assertEqual(logger.get_record_count(), 2)
        finally:
            logger = None
            gc.collect()
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_no_significant_change_skip_is_debug_not_info(self):
        db_path = self._db_path()
        if os.path.exists(db_path):
            os.remove(db_path)

        logger = None
        try:
            logger = AIVitalsLogger(db_path=db_path, min_interval=15, heartbeat_interval=0)

            self.assertTrue(
                logger.log_if_changed(
                    self._make_ai_data(
                        status="OK",
                        vision_status="DURGUN",
                        activity=0.0,
                        respiration_bpm=24.0,
                        confidence=0.80,
                    )
                )
            )

            logger.last_log_time = datetime.now() - timedelta(seconds=20)
            with self.assertLogs("lib.data.ai_vitals_logger", level="DEBUG") as captured:
                self.assertFalse(
                    logger.log_if_changed(
                        self._make_ai_data(
                            status="OK",
                            vision_status="DURGUN",
                            activity=0.0,
                            respiration_bpm=30.0,
                            confidence=0.80,
                        )
                    )
                )

            skip_records = [
                record for record in captured.records
                if "AI vital skip: no significant change" in record.getMessage()
            ]
            self.assertEqual(len(skip_records), 1)
            self.assertEqual(skip_records[0].levelno, logging.DEBUG)
        finally:
            logger = None
            gc.collect()
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_periodic_maintenance_runs_only_after_interval(self):
        db_path = self._db_path()
        if os.path.exists(db_path):
            os.remove(db_path)

        logger = None
        try:
            logger = AIVitalsLogger(db_path=db_path, min_interval=15, heartbeat_interval=0)

            maintenance_calls = []
            logger._auto_cleanup = lambda: maintenance_calls.append("ran")

            baseline = datetime.now()
            logger._last_maintenance_at = baseline

            self.assertFalse(
                logger.maybe_run_maintenance(
                    now=baseline + timedelta(hours=1),
                )
            )
            self.assertEqual(maintenance_calls, [])

            self.assertTrue(
                logger.maybe_run_maintenance(
                    now=baseline + logger.MAINTENANCE_INTERVAL + timedelta(seconds=1),
                )
            )
            self.assertEqual(maintenance_calls, ["ran"])
        finally:
            logger = None
            gc.collect()
            if os.path.exists(db_path):
                os.remove(db_path)


if __name__ == "__main__":
    unittest.main()
