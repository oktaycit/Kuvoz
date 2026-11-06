"""Preview labels can be hidden without changing the tracked region."""
import unittest
from unittest.mock import Mock, patch
from lib.ai.vision import VisionEngine, OPENCV_AVAILABLE

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

    @unittest.skipUnless(OPENCV_AVAILABLE, 'OpenCV gerekli')
    def test_quality_uses_patient_not_bright_background(self):
        import numpy as np
        engine = VisionEngine.__new__(VisionEngine)
        frame = np.full((100, 100, 3), 255, dtype=np.uint8)
        frame[25:75, 25:75] = 10
        gray = engine._observation_quality_gray(frame, (.25, .25, .5, .5))
        self.assertEqual(gray.shape, (50, 50))
        self.assertEqual(float(gray.mean()), 10)

if __name__ == '__main__':
    unittest.main()
