import unittest
from unittest.mock import Mock, patch
try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = np = None
from lib.ai.semantic_tracker import SemanticBodyTracker
from lib.ai.semantic_detector import AnimalModel


class Worker:
    result = None
    closed = False
    def submit(self, frame, now):
        return True
    def latest(self):
        return self.result
    def close(self):
        self.closed = True


@unittest.skipUnless(cv2 is not None, 'OpenCV gerekli')
class SemanticTrackerTests(unittest.TestCase):
    def setUp(self):
        self.worker = Worker()
        self.tracker = SemanticBodyTracker(cv2, np, self.worker)
        self.gray = np.zeros((240, 320), np.uint8)
        self.color = np.zeros((480, 640, 3), np.uint8)
        self.tracker.initialize(self.gray, {'animal': dict(x=.1, y=.1, width=.3, height=.4)}, 0)
        self.sequence = 0

    def detect(self, captured, now, boxes=((.6, .3, .2, .4),), error=None):
        self.sequence += 1
        self.tracker.frames.append((captured, self.gray.copy()))
        self.worker.result = dict(sequence=self.sequence, captured=captured, milliseconds=3000,
                                  detections=[dict(box=b, confidence=.5, label='cat') for b in boxes], error=error)
        self.tracker.update_color(self.color, self.gray, now)

    def lock(self):
        self.detect(1, 4)
        self.assertEqual(self.tracker.state, 'acquiring')
        self.assertEqual(self.tracker.boxes, {})
        self.detect(5, 8)
        self.assertEqual(self.tracker.state, 'locked')

    def test_uses_recognized_body_instead_of_saved_coordinates(self):
        self.lock()
        self.assertEqual(self.tracker.boxes['animal'], (192, 72, 64, 96))
        self.assertGreaterEqual(self.tracker.confidence, .6)
        self.assertEqual(self.tracker.detection_confidence, .5)
        self.assertFalse(self.tracker.respiration_ready)

    def test_no_animal_and_multiple_animals_remove_old_box(self):
        self.lock()
        self.detect(9, 12, ())
        self.assertEqual(self.tracker.state, 'lost')
        self.assertEqual(self.tracker.boxes, {})
        self.detect(13, 16, ((.1, .1, .2, .2), (.6, .5, .2, .2)))
        self.assertEqual(self.tracker.reason, 'multiple_animals')
        self.assertEqual(self.tracker.boxes, {})

    def test_old_results_expire_even_when_no_new_detection_arrives(self):
        self.lock()
        self.tracker.update_color(self.color, self.gray, 18)
        self.assertEqual(self.tracker.state, 'lost')
        self.assertEqual(self.tracker.reason, 'recognition_expired')
        self.assertEqual(self.tracker.boxes, {})

    def test_pose_change_requires_fresh_confirmation(self):
        self.lock()
        self.detect(9, 12, ((.2, .1, .4, .2),))
        self.assertEqual(self.tracker.state, 'acquiring')
        self.assertEqual(self.tracker.boxes, {})
        self.detect(13, 16, ((.2, .1, .4, .2),))
        self.assertEqual(self.tracker.state, 'locked')

    def test_inflight_result_from_before_camera_loss_cannot_relock(self):
        self.lock()
        self.tracker.lose('camera_disconnected')
        self.detect(8, 12)
        self.assertEqual(self.tracker.state, 'lost')
        self.assertEqual(self.tracker.boxes, {})
        self.detect(13, 16)
        self.assertEqual(self.tracker.state, 'acquiring')
        self.detect(17, 20)
        self.assertEqual(self.tracker.state, 'locked')

    def test_delayed_recognition_box_moves_to_current_frame(self):
        before = np.full((240, 320), 210, np.uint8)
        before[72:168, 192:256] = np.random.default_rng(4).integers(30, 130, (96, 64), dtype=np.uint8)
        current = cv2.warpAffine(before, np.float32([[1, 0, -15], [0, 1, 8]]), (320, 240), borderValue=210)
        self.tracker.frames.append((1, before))
        self.worker.result = dict(sequence=1, captured=1, milliseconds=3000,
                                  detections=[dict(box=(.6, .3, .2, .4), confidence=.5)], error=None)
        self.tracker.update_color(self.color, current, 4)
        self.assertAlmostEqual(self.tracker.pending_box[0], 177, delta=2)
        self.assertAlmostEqual(self.tracker.pending_box[1], 80, delta=2)

    def test_confirmation_follows_walking_body_between_recognitions(self):
        original = np.full((240, 320), 210, np.uint8)
        original[72:168, 192:256] = np.random.default_rng(4).integers(30, 130, (96, 64), dtype=np.uint8)
        frames = [cv2.warpAffine(original, np.float32([[1, 0, 10*k], [0, 1, 0]]),
                                (320, 240), borderValue=210) for k in range(4)]
        self.tracker.frames.append((0, frames[0]))
        self.worker.result = dict(sequence=1, captured=0, milliseconds=1000,
                                  detections=[dict(box=(.6, .3, .2, .4), confidence=.8)], error=None)
        self.tracker.update_color(self.color, frames[1], 1)
        self.tracker.update_color(self.color, frames[2], 2)
        self.worker.result = dict(sequence=2, captured=2, milliseconds=1000,
                                  detections=[dict(box=(212/320, .3, .2, .4), confidence=.8)], error=None)
        self.tracker.update_color(self.color, frames[3], 3)
        self.assertEqual(self.tracker.state, 'locked')
        self.assertAlmostEqual(self.tracker.boxes['animal'][0], 222, delta=2)

    def test_motion_validation_rejects_a_disappearing_body(self):
        before = np.full((240, 320), 210, np.uint8)
        before[72:168, 192:256] = np.random.default_rng(4).integers(30, 130, (96, 64), dtype=np.uint8)
        self.assertIsNone(self.tracker._transport_box(before, np.full_like(before, 210), (192, 72, 64, 96)))

    def stable_lock(self):
        self.detect(0, 0)
        self.detect(2, 2)
        self.worker.result['milliseconds'] = 900
        self.tracker.detector_ms = 900
        self.worker.submit = Mock(return_value=True)
        for now in (2.5, 3, 3.5, 4):
            self.tracker.update_color(self.color, self.gray, now)

    def test_stationary_body_uses_flow_between_five_second_recognitions(self):
        self.stable_lock()
        self.worker.submit.assert_not_called()
        for now in (4.5, 5, 5.5, 6, 6.5):
            self.tracker.update_color(self.color, self.gray, now)
        self.worker.submit.assert_not_called()
        self.tracker.update_color(self.color, self.gray, 7)
        self.worker.submit.assert_called_once()
        self.assertEqual(self.tracker.state, 'locked')
        self.assertEqual(self.tracker.verified_at, 2)

    def test_motion_requests_recognition_without_waiting_for_stable_interval(self):
        self.stable_lock()
        self.tracker.last_submit = 4
        with patch.object(self.tracker, '_transport_box', return_value=(212, 72, 64, 96)):
            self.tracker.update_color(self.color, self.gray, 4.5)
        self.worker.submit.assert_called_once()
        self.assertEqual(self.tracker.state, 'moving')
        self.assertEqual(self.tracker._recognition_interval(), 2)

    def test_smooth_motion_keeps_light_tracking_between_recognitions(self):
        self.stable_lock()
        with patch.object(self.tracker, '_transport_box', return_value=(197, 72, 64, 96)):
            self.tracker.update_color(self.color, self.gray, 4.5)
        self.worker.submit.assert_not_called()
        self.assertEqual(self.tracker.state, 'moving')
        self.assertEqual(self.tracker.boxes['animal'], (197, 72, 64, 96))
        self.assertEqual(self.tracker._recognition_interval(), 5)

    def test_failed_flow_clears_box_and_immediately_requests_recognition(self):
        self.stable_lock()
        self.tracker.last_submit = 4
        with patch.object(self.tracker, '_transport_box', return_value=None):
            self.tracker.update_color(self.color, self.gray, 4.5)
        self.worker.submit.assert_called_once()
        self.assertEqual(self.tracker.boxes, {})
        self.assertEqual(self.tracker.state, 'lost')

    def test_busy_worker_does_not_consume_urgent_retry(self):
        self.stable_lock()
        self.worker.submit.return_value = False
        self.tracker.lose('body_motion_unverified')
        self.tracker.update_color(self.color, self.gray, 4.5)
        self.assertTrue(self.tracker.recognition_urgent)
        self.worker.submit.return_value = True
        self.tracker.update_color(self.color, self.gray, 5)
        self.assertFalse(self.tracker.recognition_urgent)

    def test_negative_recognition_does_not_run_model_continuously(self):
        self.stable_lock()
        self.detect(4, 5, ())
        self.assertEqual(self.tracker.state, 'lost')
        self.assertFalse(self.tracker.recognition_urgent)
        self.worker.submit.reset_mock()
        self.tracker.last_submit = 5
        self.tracker.update_color(self.color, self.gray, 5.5)
        self.worker.submit.assert_not_called()

    def test_slow_or_low_confidence_recognition_keeps_fast_cadence(self):
        self.stable_lock()
        self.tracker.detector_ms = 3000
        self.assertEqual(self.tracker._recognition_interval(), 2)
        self.tracker.detector_ms = 900
        self.tracker.confidence = .7
        self.assertEqual(self.tracker._recognition_interval(), 2)

    def test_flow_cannot_extend_semantic_expiry(self):
        self.stable_lock()
        self.tracker.update_color(self.color, self.gray, 10.1)
        self.assertEqual(self.tracker.state, 'lost')
        self.assertEqual(self.tracker.reason, 'recognition_expired')
        self.assertEqual(self.tracker.boxes, {})

    def test_rotations_map_boxes_back_to_camera_coordinates(self):
        box = (.1, .2, .3, .4)
        expected = [box, (.4, .1, .4, .3), (.6, .4, .3, .4), (.2, .6, .4, .3)]
        for rotation, target in enumerate(expected):
            np.testing.assert_allclose(AnimalModel.unrotate(box, rotation), target)


@unittest.skipUnless(cv2 is not None, 'OpenCV gerekli')
class SemanticIntegrationTests(unittest.TestCase):
    def test_recognition_keeps_frame_rate_during_motion_and_search(self):
        from lib.ai.vision import VisionEngine
        engine = VisionEngine()
        engine.camera_source = 'ip'
        engine.base_fps = 5
        engine.thermal_fps_cap = 5
        engine.region_tracker = SemanticBodyTracker(cv2, np, Worker())
        for state in ('lost', 'acquiring', 'moving', 'locked'):
            engine.region_tracker.state = state
            engine._update_load_profile(now=100)
            self.assertEqual(engine.target_fps, 2)
            self.assertEqual(engine.load_reason, 'semantic_tracking')
        engine.stop()

    def test_display_and_analysis_share_capture_instead_of_stale_hd_keyframe(self):
        from unittest.mock import patch, Mock
        from lib.ai.vision import VisionEngine
        engine = VisionEngine(resolution=(320, 240))
        engine.camera_type = 'ip'
        engine.preview_camera = Mock()
        engine.preview_camera.read.return_value = np.full((960, 967, 3), 255, np.uint8)
        capture = np.full((480, 640, 3), 64, np.uint8)
        with patch.dict('os.environ', {'KUVOZ_AI_SEMANTIC_TRACKING': '1'}):
            analysis, preview = engine._prepare_capture_frames(capture)
        self.assertEqual(float(analysis.mean()), 64)
        self.assertEqual(float(preview.mean()), 64)
        self.assertFalse(engine.hd_preview_active)
        engine.preview_camera.read.assert_not_called()
        engine.stop()

    def test_engine_uses_preview_geometry_and_never_loads_old_body_cache(self):
        from unittest.mock import patch, Mock
        from lib.ai.vision import VisionEngine
        worker = Worker()
        with patch.dict('os.environ', {'KUVOZ_AI_SEMANTIC_TRACKING': '1'}), \
             patch('lib.ai.semantic_tracker.AnimalDetectionWorker', return_value=worker), \
             patch('lib.ai.vision.ReferenceCache') as cache:
            engine = VisionEngine()
            engine.set_system_settings({'animal_roi_enabled': True,
                                        'animal_roi': dict(x=.2, y=.2, width=.4, height=.4)})
            engine.reference_cache_dir = '/tmp/unused-semantic-cache'
            frame = np.zeros((240, 320, 3), np.uint8)
            preview = np.zeros((960, 967, 3), np.uint8)
            engine._update_region_tracking(frame, preview)
            self.assertIsInstance(engine.region_tracker, SemanticBodyTracker)
            cache.return_value.load.assert_not_called()
            crop, box = engine._apply_analysis_focus(frame)
            self.assertIs(crop, frame)
            self.assertIsNone(box)
            worker.submit = Mock(return_value=True)
            engine._update_region_tracking(frame, preview)
            self.assertIs(worker.submit.call_args.args[0], preview)
            engine.stop()
            self.assertTrue(worker.closed)

if __name__ == '__main__':
    unittest.main()
