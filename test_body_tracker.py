import unittest
from unittest.mock import patch
try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = np = None
from lib.ai.body_tracker import BodyObservationTracker


@unittest.skipUnless(cv2 is not None and hasattr(cv2, 'TrackerCSRT_create'), 'CSRT gerekli')
class BodyTrackerTests(unittest.TestCase):
    def setUp(self):
        cv2.setNumThreads(1)
        self.frame = np.full((240, 320), 210, np.uint8)
        self.frame[60:160, 100:220] = np.random.default_rng(3).integers(30, 130, (100, 120), dtype=np.uint8)
        self.tracker = BodyObservationTracker(cv2, np)
        self.tracker.initialize(self.frame, {'animal': dict(x=100/320, y=60/240, width=120/320, height=100/240)}, 0)

    def test_tracks_selected_body_and_rejects_empty_bedding(self):
        for now in (1, 2, 3):
            self.tracker.update(self.frame, now)
        self.assertEqual(self.tracker.state, 'locked')
        self.assertGreaterEqual(self.tracker.confidence, .65)
        self.tracker.update(np.full_like(self.frame, 210), 4)
        self.assertEqual(self.tracker.state, 'lost')

    def test_tracks_translation_without_enabling_respiration(self):
        moved = cv2.warpAffine(self.frame, np.float32([[1, 0, 8], [0, 1, 0]]), (320, 240), borderValue=210)
        self.tracker.update(moved, 1)
        self.assertNotEqual(self.tracker.state, 'lost')
        self.assertGreater(self.tracker.boxes['animal'][0], 103)
        self.assertFalse(self.tracker.respiration_ready)
        self.assertNotIn('respiration', self.tracker.boxes)

    def test_transient_appearance_uncertainty_is_not_reported_as_reliable(self):
        seed=np.zeros(24,np.float32);seed[:4]=.25
        changed=np.zeros(24,np.float32);changed[:8]=.125
        self.tracker.body_hist=seed
        with patch.object(self.tracker,'_histogram',return_value=changed):
            self.tracker.update(self.frame,1)
        self.assertEqual(self.tracker.state,'acquiring')
        self.assertLess(self.tracker.confidence,.65)
        self.assertIsNotNone(self.tracker.visual)
        with patch.object(self.tracker,'_histogram',return_value=seed):
            for now in (2,3,4):self.tracker.update(self.frame,now)
        self.assertEqual(self.tracker.state,'locked')

    def test_lost_body_does_not_adopt_unrelated_background(self):
        self.tracker.lose('body_visual_lost')
        with patch.object(self.tracker.recovery, 'find') as find:
            for now in (1, 2, 3, 4):
                self.tracker.update(np.full_like(self.frame, 210), now)
        find.assert_not_called()
        self.assertEqual(self.tracker.state, 'lost')
        self.assertEqual(self.tracker.confidence, 0)
        self.assertIsNone(self.tracker.visual)

    def test_body_histogram_stays_anchored_to_selection(self):
        original = self.tracker.body_hist.copy()
        changed = .85 * original + .15 / len(original)
        with patch.object(self.tracker, '_histogram', return_value=changed):
            for now in range(1, 15):
                self.tracker.update(self.frame, now)
        np.testing.assert_array_equal(self.tracker.body_hist, original)

    def test_visual_tracker_cannot_teleport_to_enclosure(self):
        from unittest.mock import Mock
        self.tracker.visual = Mock()
        self.tracker.visual.update.return_value = (True, (0, 0, 120, 100))
        changed = 255 - self.frame
        self.tracker.update(changed, 1)
        self.assertEqual(self.tracker.state, 'lost')
        self.assertEqual(self.tracker.reason, 'body_position_unverified')

    def test_reconnect_recovers_selected_body_after_repeated_verification(self):
        self.tracker.lose('camera_disconnected')
        for now in (1, 2):
            self.tracker.update(self.frame, now)
            self.assertEqual(self.tracker.state, 'lost')
        self.tracker.update(self.frame, 3)
        self.assertEqual(self.tracker.state, 'acquiring')
        self.assertEqual(self.tracker.recovery_kind, 'verified_body_features')
        for now in (4, 5, 6):
            self.tracker.update(self.frame, now)
        self.assertEqual(self.tracker.state, 'locked')
        self.assertFalse(self.tracker.respiration_ready)

    def test_recovery_finds_translated_patient_without_learning_new_identity(self):
        moved = cv2.warpAffine(self.frame, np.float32([[1, 0, 35], [0, 1, 10]]),
                              (320, 240), borderValue=210)
        original = self.tracker.body_hist.copy()
        self.tracker.lose('frame_gap')
        for now in range(1, 7):
            self.tracker.update(moved, now)
        self.assertEqual(self.tracker.state, 'locked')
        self.assertGreater(self.tracker.boxes['animal'][0], 125)
        np.testing.assert_array_equal(self.tracker.body_hist, original)

    def test_recovery_rejects_unrelated_textured_object(self):
        changed = np.full_like(self.frame, 210)
        changed[15:115, 15:135] = np.random.default_rng(8).integers(30, 130, (100, 120), dtype=np.uint8)
        self.tracker.lose('camera_disconnected')
        for now in range(1, 7):
            self.tracker.update(changed, now)
        self.assertEqual(self.tracker.state, 'lost')
        self.assertEqual(self.tracker.confidence, 0)

    def test_recovery_confirmation_does_not_bridge_another_disconnect(self):
        self.tracker.lose('camera_disconnected')
        self.tracker.update(self.frame, 1)
        self.tracker.update(self.frame, 2)
        self.tracker.update(self.frame, 10)
        self.assertEqual(self.tracker.state, 'lost')
        self.assertEqual(self.tracker.candidate_hits, 1)
        for now in (11, 12, 13, 14, 15):
            self.tracker.update(self.frame, now)
        self.assertEqual(self.tracker.state, 'locked')
