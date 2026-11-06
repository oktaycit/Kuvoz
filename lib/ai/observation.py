"""Conservative camera observations; no physiological or sleep inference."""
import math
import threading
import time
from collections import deque


class CameraObservation:
    def __init__(self):
        self.lock = threading.RLock()
        self.samples = deque(maxlen=7200)
        self.events = deque(maxlen=100)
        self.anchor = None
        self.pending_since = None
        self.last_change = None
        self.last_ts = None
        self.latest = {}
        self.previous_usable = False
        self.last_brightness = None

    def update(self, *, now, activity, brightness, sharpness, box, confidence, tracking, frame_aspect=1.0):
        with self.lock:
            lighting_changed = (self.last_ts is not None and 0 < now - self.last_ts <= 10
                                and self.last_brightness is not None
                                and abs(brightness - self.last_brightness) > 20)
            self.last_brightness = brightness
            reason = ('dark' if brightness < 25 else 'overexposed' if brightness > 240
                      else 'blurred' if sharpness < 8 else 'lighting_changed' if lighting_changed else 'tracking_lost'
                      if not tracking or box is None or confidence < .6 else 'usable')
            usable = reason == 'usable'
            moving = activity > 1 if usable else None
            posture = 'unknown'
            if usable:
                x, y, w, h = box
                # This is orientation of the tracked region, never anatomical pose.
                ratio = w * frame_aspect / max(h, .001)
                posture = 'horizontal' if ratio >= 1.7 else 'vertical' if ratio <= .65 else 'unknown'
                if self.anchor is None:
                    self.anchor = box
                ax, ay, aw, ah = self.anchor
                displacement = math.hypot(x + w/2 - ax - aw/2, y + h/2 - ay - ah/2)
                changed = displacement > .10
                if changed:
                    if self.pending_since is None:
                        self.pending_since = now
                    elif now - self.pending_since >= 5:
                        self.last_change = now
                        self.events.append({'timestamp': now, 'type': 'position_change'})
                        self.anchor = box
                        self.pending_since = None
                else:
                    self.pending_since = None
            else:
                # Never bridge tracking gaps as a movement or a stationary interval.
                self.anchor = None
                self.pending_since = None
            start = self.last_ts if self.last_ts is not None else now
            if now - start > 10:
                start = now
            self.samples.append((start, now, moving if usable and self.previous_usable else None))
            self.previous_usable = usable
            self.last_ts = now
            while self.samples and self.samples[0][1] < now - 3600:
                self.samples.popleft()
            self.latest = dict(timestamp=now, activity=round(activity, 2) if usable else None,
                               movement='active' if moving else 'low_motion' if usable else 'unknown',
                               posture=posture, posture_method='tracked_region_orientation',
                               quality=reason, tracking_confidence=round(confidence, 3),
                               last_position_change=self.last_change)

    def snapshot(self, now=None):
        now = time.time() if now is None else now
        with self.lock:
            result = dict(self.latest)
            if not result or now - result.get('timestamp', 0) > 10:
                result.update(quality='unavailable', movement='unknown', activity=None, posture='unknown')
            active = low = observed = 0.0
            for start, end, moving in self.samples:
                duration = max(0, min(end, now) - max(start, now - 3600))
                if moving is not None:
                    observed += duration
                    if moving: active += duration
                    else: low += duration
            window_start = now - 3600
            buckets = [{'timestamp': window_start + minute * 60,
                        'observed_seconds': 0.0, 'active_seconds': 0.0} for minute in range(60)]
            for start, stop, moving in self.samples:
                if moving is None or stop <= window_start:
                    continue
                first = max(0, min(59, int((start - window_start) // 60)))
                last = max(0, min(59, int((stop - window_start) // 60)))
                for minute in range(first, last + 1):
                    begin = buckets[minute]['timestamp']
                    overlap = max(0, min(stop, begin + 60) - max(start, begin))
                    buckets[minute]['observed_seconds'] += overlap
                    if moving:
                        buckets[minute]['active_seconds'] += overlap
            for bucket in buckets:
                for key in ('observed_seconds', 'active_seconds'):
                    bucket[key] = round(bucket[key], 1)
            result['timeline'] = buckets
            result['summary'] = {'window_seconds': 3600, 'observed_seconds': round(observed),
                                 'active_seconds': round(active), 'low_motion_seconds': round(low)}
            result['events'] = [dict(e) for e in self.events if e['timestamp'] >= now - 3600]
            result['position_changes'] = len(result['events'])
            return result
