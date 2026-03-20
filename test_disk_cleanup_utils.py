import unittest
from types import SimpleNamespace

from disk_cleanup_utils import perform_disk_cleanup


class FakeLogger:
    def __init__(self, count, clear_ok=True):
        self.count = count
        self.clear_ok = clear_ok
        self.calls = []

    def get_record_count(self):
        return self.count

    def clear_all_data(self, reason=None, context=None):
        self.calls.append((reason, context))
        if self.clear_ok:
            self.count = 0
            return True
        return False


class DiskCleanupUtilsTests(unittest.TestCase):
    def test_perform_disk_cleanup_clears_sensor_and_ai_logs(self):
        sensor_logger = FakeLogger(4)
        ai_logger = FakeLogger(2)

        def runner(command, capture_output, text, timeout):
            self.assertEqual(command, ["make", "disk-clean"])
            self.assertTrue(capture_output)
            self.assertTrue(text)
            self.assertEqual(timeout, 300)
            return SimpleNamespace(returncode=0, stdout="ok", stderr="")

        result = perform_disk_cleanup(
            sensor_logger=sensor_logger,
            ai_vitals_logger=ai_logger,
            runner=runner,
        )

        self.assertTrue(result["success"])
        self.assertEqual(
            result["application_cleanup"]["deleted_records_total"],
            6,
        )
        self.assertIn("4 sensör logu", result["message"])
        self.assertIn("2 AI vital kaydı", result["message"])
        self.assertEqual(
            sensor_logger.calls[0],
            ("disk_cleanup", {"trigger": "settings_disk_cleanup"}),
        )
        self.assertEqual(
            ai_logger.calls[0],
            ("disk_cleanup", {"trigger": "settings_disk_cleanup"}),
        )

    def test_perform_disk_cleanup_reports_partial_failure_when_system_command_fails(self):
        sensor_logger = FakeLogger(3)

        def runner(command, capture_output, text, timeout):
            return SimpleNamespace(returncode=1, stdout="", stderr="sudo denied")

        result = perform_disk_cleanup(
            sensor_logger=sensor_logger,
            ai_vitals_logger=None,
            runner=runner,
        )

        self.assertFalse(result["success"])
        self.assertTrue(result["application_cleanup"]["success"])
        self.assertFalse(result["system_cleanup"]["success"])
        self.assertIn("Uygulama logları temizlendi", result["message"])
        self.assertIn("sistem temizliği başarısız oldu", result["message"])


if __name__ == "__main__":
    unittest.main()
