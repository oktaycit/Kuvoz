import unittest
import sys
from types import SimpleNamespace
from unittest.mock import patch

try:
    import numpy  # noqa: F401
except Exception:
    sys.modules.setdefault(
        "numpy",
        SimpleNamespace(
            polyfit=lambda *args, **kwargs: [0.0],
            var=lambda *args, **kwargs: 0.0,
        ),
    )

import lib.ai.manager as manager_module


class AIManagerLoggingTests(unittest.TestCase):
    def setUp(self):
        self.manager = manager_module.AIManager()

    def test_initial_normal_state_is_not_logged(self):
        with patch.object(manager_module, "logger") as mock_logger:
            self.manager._log_analysis_state_if_changed(
                {"anomalies": []},
                {"status": "OK"},
            )

        mock_logger.info.assert_not_called()

    def test_logs_only_on_meaningful_analysis_changes(self):
        with patch.object(manager_module, "logger") as mock_logger:
            self.manager._log_analysis_state_if_changed(
                {"anomalies": ["sicaklik yuksek"]},
                {"status": "OK"},
            )
            self.manager._log_analysis_state_if_changed(
                {"anomalies": ["sicaklik yuksek"]},
                {"status": "OK"},
            )
            self.manager._log_analysis_state_if_changed(
                {"anomalies": []},
                {"status": "OK"},
            )

        self.assertEqual(mock_logger.info.call_count, 2)
        self.assertIn("AI analiz degisimi", mock_logger.info.call_args_list[0].args[0])
        self.assertEqual(mock_logger.info.call_args_list[1].args[0], "AI analiz normale dondu")

    def test_logs_too_much_motion_once_until_state_clears(self):
        with patch.object(manager_module, "logger") as mock_logger:
            with patch("lib.ai.manager.time.time", side_effect=[100.0, 101.0, 122.0]):
                self.manager._log_analysis_state_if_changed(
                    {"anomalies": []},
                    {"status": "TOO_MUCH_MOTION"},
                )
                self.manager._log_analysis_state_if_changed(
                    {"anomalies": []},
                    {"status": "TOO_MUCH_MOTION"},
                )
                self.manager._log_analysis_state_if_changed(
                    {"anomalies": []},
                    {"status": "OK"},
                )

        self.assertEqual(mock_logger.info.call_count, 2)
        self.assertIn("vital_izleme=DEGRADED(TOO_MUCH_MOTION)", mock_logger.info.call_args_list[0].args[1])
        self.assertEqual(mock_logger.info.call_args_list[1].args[0], "AI analiz normale dondu")

    def test_low_conf_and_motion_share_same_degraded_analysis_state(self):
        with patch.object(manager_module, "logger") as mock_logger:
            with patch("lib.ai.manager.time.time", side_effect=[100.0, 105.0, 110.0, 135.0]):
                self.manager._log_analysis_state_if_changed(
                    {"anomalies": []},
                    {"status": "TOO_MUCH_MOTION"},
                )
                self.manager._log_analysis_state_if_changed(
                    {"anomalies": []},
                    {"status": "LOW_CONF"},
                )
                self.manager._log_analysis_state_if_changed(
                    {"anomalies": []},
                    {"status": "TOO_MUCH_MOTION"},
                )
                self.manager._log_analysis_state_if_changed(
                    {"anomalies": []},
                    {"status": "OK"},
                )

        self.assertEqual(mock_logger.info.call_count, 2)
        self.assertEqual(mock_logger.info.call_args_list[1].args[0], "AI analiz normale dondu")

    def test_brief_ok_does_not_clear_degraded_analysis_state(self):
        with patch.object(manager_module, "logger") as mock_logger:
            with patch("lib.ai.manager.time.time", side_effect=[100.0, 105.0, 130.0]):
                self.manager._log_analysis_state_if_changed(
                    {"anomalies": []},
                    {"status": "LOW_CONF"},
                )
                self.manager._log_analysis_state_if_changed(
                    {"anomalies": []},
                    {"status": "OK"},
                )
                self.manager._log_analysis_state_if_changed(
                    {"anomalies": []},
                    {"status": "OK"},
                )

        self.assertEqual(mock_logger.info.call_count, 2)
        self.assertEqual(mock_logger.info.call_args_list[1].args[0], "AI analiz normale dondu")

    def test_track_vitals_logs_only_first_degraded_event_inside_unstable_episode(self):
        self.manager.last_vitals_snapshot = {
            "status": "OK",
            "respiration_bpm": 18.0,
            "confidence": 0.82,
        }

        vision = {"status": "HAREKETLI", "activity": 1.0}
        with patch.object(manager_module, "logger") as mock_logger:
            with patch("lib.ai.manager.time.time", side_effect=[100.0, 140.0]):
                self.manager._track_vital_changes(
                    vision,
                    {"status": "TOO_MUCH_MOTION", "respiration_bpm": None, "confidence": 0.0},
                )
                self.manager._track_vital_changes(
                    vision,
                    {"status": "LOW_CONF", "respiration_bpm": 27.0, "confidence": 0.41},
                )

        self.assertEqual(len(self.manager.vital_change_reports), 1)
        self.assertEqual(self.manager.vital_change_reports[0]["kind"], "tracking_degraded")
        self.assertEqual(mock_logger.info.call_count, 1)

    def test_track_vitals_ignores_ok_below_confidence_threshold(self):
        self.manager.last_vitals_snapshot = {
            "status": "OK",
            "respiration_bpm": 18.0,
            "confidence": 0.82,
        }

        vision = {"status": "HAREKETLI", "activity": 1.0}
        with patch.object(manager_module, "logger") as mock_logger:
            with patch("lib.ai.manager.time.time", return_value=100.0):
                self.manager._track_vital_changes(
                    vision,
                    {"status": "OK", "respiration_bpm": 27.0, "confidence": 0.58},
                )

        self.assertEqual(len(self.manager.vital_change_reports), 0)
        mock_logger.info.assert_not_called()

    def test_stable_stress_logs_use_slower_cooldown(self):
        self.manager.last_vitals_snapshot = {
            "status": "OK",
            "respiration_bpm": 18.0,
            "confidence": 0.78,
        }

        vision = {"status": "HAREKETLI", "activity": 1.0}
        with patch.object(manager_module, "logger") as mock_logger:
            with patch("lib.ai.manager.time.time", side_effect=[100.0, 130.0, 170.0]):
                self.manager._track_vital_changes(
                    vision,
                    {"status": "OK", "respiration_bpm": 26.0, "confidence": 0.80},
                )
                self.manager._track_vital_changes(
                    vision,
                    {"status": "OK", "respiration_bpm": 34.0, "confidence": 0.82},
                )
                self.manager._track_vital_changes(
                    vision,
                    {"status": "OK", "respiration_bpm": 42.0, "confidence": 0.84},
                )

        self.assertEqual(len(self.manager.vital_change_reports), 2)
        self.assertEqual(mock_logger.info.call_count, 2)

    def test_clear_sensor_history_resets_oxygen_alert_state(self):
        for value in [20.8, 20.6, 20.4, 20.1, 19.0, 17.8]:
            self.manager.update_sensors({"oxygen": value}, {"heater_on": False})

        self.assertTrue(self.manager.analytics.get_status()["anomalies"])

        self.manager.clear_sensor_history("oxygen")

        status = self.manager.analytics.get_status()
        self.assertEqual(status["anomalies"], [])
        self.assertEqual(status["data_points"]["oxygen"], 0)


if __name__ == "__main__":
    unittest.main()
