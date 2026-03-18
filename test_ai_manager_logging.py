import unittest
import sys
from types import SimpleNamespace
from unittest.mock import patch

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
        self.assertIn("vital_durum=TOO_MUCH_MOTION", mock_logger.info.call_args_list[0].args[1])
        self.assertEqual(mock_logger.info.call_args_list[1].args[0], "AI analiz normale dondu")


if __name__ == "__main__":
    unittest.main()
