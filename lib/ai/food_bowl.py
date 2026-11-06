"""Calibrated, conservative bowl appearance comparison (no cloud dependency)."""
import json
import math


def validate_bowl_reference(value):
    if value is None:
        return
    if (not isinstance(value, list) or len(value) != 192
            or any(isinstance(v, bool) or not isinstance(v, (int, float))
                   or not math.isfinite(v) or not 0 <= v <= 255 for v in value)):
        raise ValueError('Mama kabı referansı geçersiz; yeniden kaydedin')


class FoodBowlMonitor:
    def __init__(self):
        self.signature = None
        self.since = None
        self.last_time = None
        self.latest = {}

    def update(self, frame, settings, now, cv2, np, animal_box=None):
        identity = {k: settings.get(k) for k in (
            'feeding_roi_enabled', 'feeding_roi', 'food_bowl_empty_reference',
            'food_bowl_full_reference', 'food_bowl_camera_signature')}
        signature = json.dumps(identity, sort_keys=True)
        if signature != self.signature:
            self.signature, self.since = signature, None
        result = dict(state='unknown', reason='not_configured', timestamp=now)
        try:
            roi = settings.get('feeding_roi')
            empty = settings.get('food_bowl_empty_reference')
            full = settings.get('food_bowl_full_reference')
            camera = [settings.get('camera_source') or 'raspberry_pi', settings.get('ip_camera_url') or '',
                      settings.get('camera_transform') or 'normal', settings.get('camera_lens_correction') or 'off']
            if settings.get('feeding_roi_enabled') and roi and empty and full and settings.get('food_bowl_camera_signature') == camera:
                validate_bowl_reference(empty)
                validate_bowl_reference(full)
                x, y, w, h = (float(roi[k]) for k in ('x', 'y', 'width', 'height'))
                height, width = frame.shape[:2]
                crop = frame[int(y*height):int((y+h)*height), int(x*width):int((x+w)*width)]
                result['reason'] = 'unrecognized'
                occluded = False
                if animal_box:
                    ax, ay, aw, ah = animal_box
                    overlap = max(0, min(x+w, ax+aw)-max(x, ax))*max(0, min(y+h, ay+ah)-max(y, ay))
                    occluded = overlap / (w*h) > .1
                if crop.size and min(crop.shape[:2]) >= 8:
                    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                    sample = cv2.resize(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB), (8, 8), interpolation=cv2.INTER_AREA).astype(float).reshape(-1)
                    e, f = np.asarray(empty), np.asarray(full)
                    separation = float(np.mean(np.abs(e-f)))
                    de, df = float(np.mean(np.abs(sample-e))), float(np.mean(np.abs(sample-f)))
                    if occluded:
                        result['reason'] = 'occluded'
                    elif gray.mean() < 25 or gray.mean() > 240:
                        result['reason'] = 'lighting'
                    elif separation < 15:
                        result['reason'] = 'references_too_similar'
                    elif de < min(18, separation*.35) and df-de > separation*.4:
                        result.update(state='empty_candidate', reason='confirming')
                    elif df < min(18, separation*.35) and de-df > separation*.4:
                        result.update(state='full', reason='matched_full')
        except (ValueError, TypeError, KeyError, ZeroDivisionError):
            result['reason'] = 'invalid_configuration'
        if result['state'] == 'empty_candidate':
            if self.since is None or self.last_time is None or not 0 <= now-self.last_time <= 10:
                self.since = now
            if now-self.since >= 15:
                result.update(state='empty', reason='matched_empty')
        else:
            self.since = None
        self.last_time = now
        self.latest = result
        return result

    def snapshot(self, now, running=True):
        if not running or now-self.latest.get('timestamp', 0) > 10:
            return dict(state='unknown', reason='unavailable')
        return dict(self.latest)
