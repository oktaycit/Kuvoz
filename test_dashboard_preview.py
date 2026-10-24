"""Preview labels can be hidden without changing the tracked region."""
import unittest
from unittest.mock import Mock, patch
from lib.ai.vision import VisionEngine

class DashboardPreviewTests(unittest.TestCase):
    def test_clean_preview_keeps_box_without_embedded_text(self):
        engine = VisionEngine.__new__(VisionEngine)
        engine.analysis_focus_source = 'center_fallback'
        engine.region_tracker = None
        frame = Mock()
        frame.shape = (480, 640, 3)
        cv = Mock()
        with patch('lib.ai.vision.cv2', cv, create=True):
            engine._draw_analysis_focus_overlay(frame, (20, 30, 200, 200), show_label=False)
        cv.rectangle.assert_called_once()
        cv.putText.assert_not_called()

if __name__ == '__main__':
    unittest.main()
