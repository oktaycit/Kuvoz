import sys
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

try:
    import numpy  # noqa: F401
except Exception:
    sys.modules.setdefault(
        "numpy",
        SimpleNamespace(
            array=lambda *args, **kwargs: [],
            polyfit=lambda *args, **kwargs: [0.0],
            var=lambda *args, **kwargs: 0.0,
        ),
    )

sys.modules.setdefault(
    "picamera2",
    SimpleNamespace(Picamera2=type("Picamera2", (), {})),
)

import lib.ai.manager as manager_module


class AnalyticsStub:
    def add_reading(self, *args, **kwargs):
        return None

    def analyze(self, *args, **kwargs):
        return None

    def clear_history(self, *args, **kwargs):
        return None

    def get_status(self):
        return {"anomalies": [], "data_points": {}}


class VisionStub:
    def __init__(self, *args, **kwargs):
        self.start_result = True
        self.raise_on_process = None
        self.start_calls = 0
        self.stop_calls = 0
        self.process_calls = 0
        self.target_fps = 50.0
        self.latest_jpeg = None
        self.last_frame = None
        self.status = "IDLE"
        self.activity_level = 0.0
        self.latest_vitals = {"status": "UNAVAILABLE"}
        self.vitals = None

    def start(self):
        self.start_calls += 1
        return self.start_result

    def stop(self):
        self.stop_calls += 1

    def process_frame(self):
        self.process_calls += 1
        if self.raise_on_process is not None:
            raise self.raise_on_process
        self.last_frame = b"frame"
        self.latest_jpeg = b"jpeg"

    def get_frame(self):
        return self.latest_jpeg

    def get_status(self):
        return {"status": self.status, "activity": self.activity_level}

    def get_vitals(self):
        return self.latest_vitals


def wait_until(predicate, timeout=1.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


class AIManagerLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.vision_patcher = patch.object(manager_module, "VisionEngine", VisionStub)
        self.analytics_patcher = patch.object(manager_module, "AnalyticsEngine", AnalyticsStub)
        self.vision_patcher.start()
        self.analytics_patcher.start()
        self.manager = manager_module.AIManager()

    def tearDown(self):
        try:
            self.manager.stop()
        except Exception:
            pass
        self.analytics_patcher.stop()
        self.vision_patcher.stop()

    def test_repeated_start_is_idempotent(self):
        self.assertTrue(self.manager.start())
        self.assertTrue(wait_until(lambda: self.manager.vision.process_calls > 0))

        self.assertTrue(self.manager.start())

        status = self.manager.get_lifecycle_status()
        self.assertEqual(status["state"], manager_module.LIFECYCLE_RUNNING)
        self.assertTrue(status["thread_alive"])
        self.assertEqual(self.manager.vision.start_calls, 1)

    def test_get_update_includes_lifecycle_snapshot(self):
        self.assertTrue(self.manager.start())
        self.assertTrue(wait_until(lambda: self.manager.vision.process_calls > 0))

        update = self.manager.get_update()

        self.assertIn("lifecycle", update)
        self.assertEqual(update["lifecycle"]["state"], manager_module.LIFECYCLE_RUNNING)
        self.assertTrue(update["lifecycle"]["thread_alive"])

    def test_start_failure_sets_failed_state(self):
        self.manager.vision.start_result = False

        self.assertFalse(self.manager.start())

        status = self.manager.get_lifecycle_status()
        self.assertEqual(status["state"], manager_module.LIFECYCLE_FAILED)
        self.assertFalse(status["running"])
        self.assertFalse(status["started"])
        self.assertFalse(status["thread_alive"])
        self.assertEqual(status["last_error"], "camera_not_available")

    def test_loop_exception_marks_manager_failed(self):
        self.manager.vision.raise_on_process = RuntimeError("loop exploded")

        self.assertTrue(self.manager.start())
        self.assertTrue(
            wait_until(
                lambda: self.manager.get_lifecycle_status()["state"] == manager_module.LIFECYCLE_FAILED
            )
        )

        status = self.manager.get_lifecycle_status()
        self.assertEqual(status["state"], manager_module.LIFECYCLE_FAILED)
        self.assertFalse(status["running"])
        self.assertFalse(status["started"])
        self.assertIn("loop exploded", status["last_error"])
        self.assertGreaterEqual(self.manager.vision.stop_calls, 1)

    def test_vision_runtime_config_uses_low_power_defaults(self):
        with patch.dict(manager_module.os.environ, {}, clear=True):
            resolution, fps = manager_module._vision_runtime_config()

        self.assertEqual(resolution, (320, 240))
        self.assertEqual(fps, 1.0)

    def test_vision_runtime_config_accepts_bounded_env_overrides(self):
        with patch.dict(
            manager_module.os.environ,
            {
                "KUVOZ_AI_WIDTH": "999",
                "KUVOZ_AI_HEIGHT": "90",
                "KUVOZ_AI_FPS": "4",
            },
            clear=True,
        ):
            resolution, fps = manager_module._vision_runtime_config()

        self.assertEqual(resolution, (640, 120))
        self.assertEqual(fps, 4.0)

    def test_stop_clears_runtime_state_for_next_start(self):
        self.assertTrue(self.manager.start())
        self.assertTrue(wait_until(lambda: self.manager.vision.process_calls > 0))

        self.manager.last_vitals_snapshot = {
            "status": "OK",
            "respiration_bpm": 22.0,
            "confidence": 0.82,
        }
        self.manager.stable_vital_history.append(
            {"timestamp": 100.0, "respiration_bpm": 22.0, "confidence": 0.82}
        )
        self.manager.last_analysis_log_signature = (("anomali",), "DEGRADED")
        self.manager.last_analysis_degraded_ts = 123.0
        self.manager.vital_change_reports.append({"message": "test"})
        self.manager.vision.latest_jpeg = b"stale"
        self.manager.vision.last_frame = b"stale"
        self.manager.vision.status = "HAREKETLI"
        self.manager.vision.activity_level = 8.0
        self.manager.vision.latest_vitals = {"status": "OK"}

        self.manager.stop()

        status = self.manager.get_lifecycle_status()
        self.assertEqual(status["state"], manager_module.LIFECYCLE_STOPPED)
        self.assertFalse(status["thread_alive"])
        self.assertEqual(len(self.manager.vital_change_reports), 0)
        self.assertIsNone(self.manager.last_vitals_snapshot)
        self.assertEqual(len(self.manager.stable_vital_history), 0)
        self.assertIsNone(self.manager.last_analysis_log_signature)
        self.assertEqual(self.manager.last_analysis_degraded_ts, 0.0)
        self.assertIsNone(self.manager.vision.latest_jpeg)
        self.assertIsNone(self.manager.vision.last_frame)
        self.assertEqual(self.manager.vision.status, "IDLE")
        self.assertEqual(self.manager.vision.activity_level, 0.0)
        self.assertEqual(self.manager.vision.latest_vitals, {"status": "UNAVAILABLE"})

    def test_repeated_stop_is_idempotent(self):
        self.assertTrue(self.manager.start())
        self.assertTrue(wait_until(lambda: self.manager.vision.process_calls > 0))

        self.manager.stop()
        self.manager.stop()

        status = self.manager.get_lifecycle_status()
        self.assertEqual(status["state"], manager_module.LIFECYCLE_STOPPED)
        self.assertFalse(status["thread_alive"])


if __name__ == "__main__":
    unittest.main()
