"""Optional approximate barrel correction, with bounded cached maps.

Presets assume a centered radial lens, not a measured lens calibration.
Both image streams use the same normalized geometry, even at different sizes.
"""
from collections import OrderedDict


def normalize_lens_correction(value):
    return value if isinstance(value, str) and value in ('off', 'wide', 'flat') else 'off'


def lens_settings_update(current, requested):
    updated = dict(requested)
    if 'camera_lens_correction' not in updated:
        return updated
    profile = updated['camera_lens_correction']
    if not isinstance(profile, str) or profile not in ('off', 'wide', 'flat'):
        raise ValueError('Geçerli bir balık gözü düzeltme seçeneği seçin.')
    if profile != normalize_lens_correction(current.get('camera_lens_correction')):
        for region in ('animal', 'respiration', 'feeding', 'drinking'):
            updated[region + '_roi_enabled'] = False
    return updated


class LensCorrection:
    def __init__(self, cv, np):
        self.cv, self.np = cv, np
        self.maps = OrderedDict()

    def apply(self, frame, profile):
        profile = normalize_lens_correction(profile)
        if profile == 'off':
            return frame
        height, width = frame.shape[:2]
        key = (profile, width, height)
        if key not in self.maps:
            np, cv = self.np, self.cv
            # Preserve normalized positions across the substream and HD view.
            cx, cy = width/2, height/2
            camera = np.array([[cx, 0, cx], [0, cy, cy], [0, 0, 1.]])
            k1, k2 = (-.08, .01) if profile == 'wide' else (-.18, .03)
            # Positive k2 keeps the radial map monotonic out to the corners.
            self.maps[key] = cv.initUndistortRectifyMap(
                camera, np.array([k1, k2, 0., 0., 0.]), np.eye(3), camera,
                (width, height), cv.CV_16SC2)
            if len(self.maps) > 4:
                self.maps.popitem(last=False)
        self.maps.move_to_end(key)
        return self.cv.remap(frame, *self.maps[key], interpolation=self.cv.INTER_LINEAR,
                             borderMode=self.cv.BORDER_CONSTANT)
