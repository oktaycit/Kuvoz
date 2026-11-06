import unittest
from unittest.mock import patch
from lib.ai.camera_regions import validate_camera_regions
from lib.ai.vision import VisionEngine
try:
    import numpy as np
except ImportError:
    np = None

A = {'x': .1, 'y': .1, 'width': .8, 'height': .8}
R = {'x': .3, 'y': .3, 'width': .3, 'height': .3}


class CameraRegionTests(unittest.TestCase):
    @unittest.skipUnless(np is not None, 'numpy gerekli')
    def test_scene_detector_cannot_override_selected_observation_body(self):
        from lib.ai.region_tracker import RegionTracker
        from lib.ai.vision import cv2
        engine = VisionEngine()
        engine.reference_cache_dir = None
        engine.set_system_settings({'animal_roi_enabled': True, 'animal_roi': A})
        frame = np.random.default_rng(17).integers(40, 180, (240, 320, 3), dtype=np.uint8)
        with patch.dict('os.environ', {'KUVOZ_AI_SCENE_TRACKING': '1'}):
            for now in (100, 101.34, 102.68, 104.02):
                with patch('lib.ai.vision.time.monotonic', return_value=now):
                    engine._update_region_tracking(frame)
        self.assertIsInstance(engine.region_tracker, RegionTracker)
        self.assertEqual(engine.region_tracker.state, 'locked')
        self.assertGreaterEqual(engine.region_tracker.confidence, .8)
        with patch('lib.ai.vision.time.monotonic', return_value=105.36):
            engine._update_region_tracking(np.zeros_like(frame))
        self.assertNotEqual(engine.region_tracker.state, 'locked')

    def test_old_settings_keep_automatic_focus(self):
        self.assertEqual(validate_camera_regions({}), {})
        engine = VisionEngine()
        engine.set_system_settings({})
        self.assertIsNone(engine.animal_roi)

    def test_two_valid_regions(self):
        self.assertEqual(len(validate_camera_regions({'animal_roi_enabled': True, 'animal_roi': A,
                                                      'respiration_roi_enabled': True, 'respiration_roi': R})), 2)

    def test_respiration_must_be_inside_animal(self):
        with self.assertRaises(ValueError):
            validate_camera_regions({'animal_roi_enabled': True, 'animal_roi': R,
                                     'respiration_roi_enabled': True, 'respiration_roi': A})

    def test_invalid_regions_are_rejected(self):
        for region in [None, {}, dict(A, x=float('nan')), dict(A, width=.01), dict(A, width=2), dict(A, x=-1)]:
            with self.subTest(region=region), self.assertRaises(ValueError):
                validate_camera_regions({'animal_roi_enabled': True, 'animal_roi': region})

    def test_animal_change_invalidates_previous_signal_window(self):
        engine = VisionEngine()
        engine.set_system_settings({'animal_roi_enabled': True, 'animal_roi': A})
        revision = engine.respiration_roi_revision
        engine.set_system_settings({'animal_roi_enabled': True, 'animal_roi': dict(A, x=.15)})
        self.assertGreater(engine.respiration_roi_revision, revision)

    @unittest.skipUnless(np is not None, 'numpy gerekli')
    def test_separate_regions_crop_body_and_map_respiration(self):
        engine = VisionEngine()
        engine.set_system_settings({'animal_roi_enabled': True, 'animal_roi': A,
                                    'respiration_roi_enabled': True, 'respiration_roi': R})
        frame = np.zeros((200, 300, 3), dtype=np.uint8)
        cropped, box = engine._apply_analysis_focus(frame)
        self.assertEqual(box, (30, 20, 270, 180))
        self.assertEqual(cropped.shape[:2], (160, 240))
        mapped = engine._frame_box_to_analysis_box(engine.respiration_roi_frame_box, box, cropped.shape)
        self.assertIsNone(mapped)
        self.assertFalse(engine.respiration_roi_enabled)
        self.assertIsNone(engine.vitals)
        self.assertEqual(engine.get_vitals()["status"], "DISABLED")


if __name__ == '__main__':
    unittest.main()
