import unittest
from lib.ai.observation import CameraObservation


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.observation = CameraObservation()

    def sample(self, now, **kwargs):
        values = dict(now=now, activity=0, brightness=100, sharpness=30,
                      box=(.1, .1, .3, .2), confidence=.9, tracking=True)
        values.update(kwargs)
        self.observation.update(**values)
        return self.observation.snapshot(now)

    def test_invalid_image_is_not_counted_as_rest(self):
        self.sample(0)
        self.sample(5, brightness=5)
        result = self.sample(10, brightness=5)
        self.assertEqual(result['summary']['low_motion_seconds'], 0)
        self.assertEqual(result['movement'], 'unknown')
        self.assertEqual(result['quality'], 'dark')

    def test_first_bad_frame_excludes_entire_interval(self):
        self.sample(0)
        result = self.sample(5, brightness=5)
        self.assertEqual(result['summary']['observed_seconds'], 0)

    def test_lighting_transition_is_unknown_and_recovers(self):
        self.sample(0)
        result = self.sample(1, brightness=150, activity=90)
        self.assertEqual(result['quality'], 'lighting_changed')
        self.assertEqual(result['movement'], 'unknown')
        result = self.sample(2, brightness=150)
        self.assertEqual(result['summary']['observed_seconds'], 0)
        self.assertEqual(self.sample(3, brightness=150)['summary']['observed_seconds'], 1)

    def test_short_movement_is_not_position_change(self):
        self.sample(0)
        self.sample(1, box=(.4, .1, .3, .2))
        self.sample(4)
        self.assertEqual(self.sample(10)['position_changes'], 0)

    def test_sustained_translation_counted_once(self):
        self.sample(0)
        self.sample(1, box=(.4, .1, .3, .2))
        self.assertEqual(self.sample(6, box=(.4, .1, .3, .2))['position_changes'], 1)
        self.assertEqual(self.sample(12, box=(.4, .1, .3, .2))['position_changes'], 1)

    def test_reacquisition_does_not_count_as_translation(self):
        self.sample(0)
        self.sample(1, tracking=False)
        self.sample(2, box=(.7, .1, .2, .2))
        self.assertEqual(self.sample(8, box=(.7, .1, .2, .2))['position_changes'], 0)

    def test_long_gap_excluded_and_stale_snapshot_unavailable(self):
        self.sample(0)
        result = self.sample(100)
        self.assertEqual(result['summary']['observed_seconds'], 0)
        self.assertEqual(self.observation.snapshot(111)['quality'], 'unavailable')

    def test_motion_duration_and_timeline(self):
        self.sample(0, activity=10)
        result = self.sample(5, activity=10)
        self.assertEqual(result['summary']['active_seconds'], 5)
        self.assertEqual(sum(m['active_seconds'] for m in result['timeline']), 5)

    def test_low_tracking_confidence_unknown(self):
        self.assertEqual(self.sample(0, confidence=.3)['posture'], 'unknown')

    def test_orientation_uses_frame_aspect(self):
        result = self.sample(0, box=(.1, .1, .3, .2), frame_aspect=4/3)
        self.assertEqual(result['posture'], 'horizontal')
