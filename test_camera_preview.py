"""Preview retains capture detail while analysis and region coordinates stay small."""
import base64
import unittest
from unittest.mock import patch, Mock
from lib.ai.vision import VisionEngine, OPENCV_AVAILABLE
from lib.ai.ip_camera import fit_preview_frame

if OPENCV_AVAILABLE:
    import cv2
    import numpy as np

@unittest.skipUnless(OPENCV_AVAILABLE, 'OpenCV/Numpy required for image checks')
class CameraPreviewTests(unittest.TestCase):
    def engine(self):
        e = VisionEngine(resolution=(320, 240))
        e.camera_type = 'ip'
        e.frame_dimensions = {'width':320, 'height':240}
        return e

    def test_ip_preview_retains_pixels_and_native_aspect(self):
        e = self.engine()
        capture = np.zeros((1080, 1920, 3), np.uint8)
        analysis, preview = e._prepare_capture_frames(capture)
        self.assertEqual(analysis.shape[:2], (240,320))
        self.assertEqual(preview.shape[:2], (720,1280))

    def test_smaller_sources_are_not_upscaled(self):
        capture = np.zeros((240,320,3), np.uint8)
        self.assertIs(fit_preview_frame(cv2,capture,(1280,960)),capture)

    def test_rotated_frames_share_normalized_coordinates(self):
        e = self.engine()
        with patch.object(e,'_apply_camera_transform',side_effect=lambda f: cv2.rotate(f,cv2.ROTATE_90_CLOCKWISE)):
            analysis,preview=e._prepare_capture_frames(np.zeros((960,1280,3),np.uint8))
        self.assertEqual(analysis.shape[:2],(320,240))
        self.assertEqual(preview.shape[:2],(1280,960))

    def test_tracking_boxes_scale_to_preview_without_changing_analysis(self):
        e=self.engine(); e.analysis_focus_box=(32,24,160,120)
        with patch.object(e,'_draw_analysis_focus_overlay') as overlay:
            e._publish_preview(np.zeros((960,1280,3),np.uint8))
        self.assertEqual(overlay.call_args.args[1],(128,96,640,480))
        self.assertEqual(e.frame_dimensions,{'width':320,'height':240})
        decoded=cv2.imdecode(np.frombuffer(base64.b64decode(e.latest_jpeg),np.uint8),cv2.IMREAD_COLOR)
        self.assertEqual(decoded.shape[:2],(960,1280))
        self.assertEqual(e.preview_jpeg_quality,82)

    def test_noisy_preview_stays_within_transport_budget(self):
        e=self.engine()
        image=np.random.default_rng(1).integers(0,256,(960,1280,3),dtype=np.uint8)
        e._publish_preview(image)
        self.assertLessEqual(len(base64.b64decode(e.latest_jpeg)),384*1024)

    def test_local_camera_keeps_existing_color_conversion(self):
        e=self.engine();e.camera_type='picamera2'
        capture=np.zeros((480,640,3),np.uint8); capture[:,:,0]=200
        analysis,preview=e._prepare_capture_frames(capture)
        self.assertEqual(int(analysis[0,0,2]),200)
        self.assertEqual(int(preview[0,0,2]),200)

    def test_hd_preview_is_never_used_for_analysis(self):
        e=self.engine()
        e.preview_camera=Mock()
        e.preview_camera.read.return_value=np.full((1080,1088,3),180,np.uint8)
        analysis,preview=e._prepare_capture_frames(np.full((480,480,3),20,np.uint8))
        self.assertEqual(analysis.shape[:2],(240,320))
        self.assertEqual(preview.shape[:2],(960,967))
        self.assertEqual(int(analysis[0,0,0]),20)
        self.assertEqual(int(preview[0,0,0]),180)
        self.assertTrue(e.hd_preview_active)
