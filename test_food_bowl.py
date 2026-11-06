import unittest
import numpy as np
import cv2
from lib.ai.food_bowl import FoodBowlMonitor, validate_bowl_reference


class FoodBowlTests(unittest.TestCase):
    def setUp(self):
        self.monitor = FoodBowlMonitor()
        self.settings = dict(feeding_roi_enabled=True,
            feeding_roi=dict(x=0, y=0, width=1, height=1),
            food_bowl_empty_reference=[100]*192, food_bowl_full_reference=[160]*192,
            food_bowl_camera_signature=['raspberry_pi', '', 'normal', 'off'])

    def update(self, now, color=100, animal=None):
        return self.monitor.update(np.full((64,64,3),color,dtype=np.uint8),
            self.settings, now, cv2, np, animal)

    def test_requires_continuous_confirmation_and_clears_on_full(self):
        for t in (100,105,110):
            self.assertEqual(self.update(t)['state'], 'empty_candidate')
        self.assertEqual(self.update(115)['state'], 'empty')
        self.assertEqual(self.update(116,160)['state'], 'full')
        self.assertEqual(self.update(117)['state'], 'empty_candidate')

    def test_unknown_occlusion_camera_change_and_stale(self):
        self.assertEqual(self.update(100,130)['state'], 'unknown')
        self.assertEqual(self.update(101,animal=(0,0,1,1))['reason'], 'occluded')
        self.settings['camera_transform']='rotate_180'
        self.assertEqual(self.update(102)['state'], 'unknown')
        self.assertEqual(self.monitor.snapshot(120)['reason'], 'unavailable')

    def test_gaps_and_reference_changes_reset_confirmation(self):
        self.update(100)
        self.assertEqual(self.update(120)['state'], 'empty_candidate')
        self.update(125)
        self.settings['food_bowl_full_reference']=[170]*192
        self.assertEqual(self.update(136)['state'], 'empty_candidate')

    def test_bad_references_rejected(self):
        for value in ([0], [float('nan')]*192, [True]*192):
            with self.assertRaises(ValueError): validate_bowl_reference(value)


if __name__ == '__main__': unittest.main()
