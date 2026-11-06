"""Coarse selected-body tracking, with independent appearance/occlusion checks."""
import math
from .region_tracker import RegionTracker


class BodyObservationTracker(RegionTracker):
    def __init__(self, cv, np):
        super().__init__(cv, np, observation_only=True)
        self.visual = None
        self.body_hist = None
        self.appearance_misses = 0

    def _histogram(self, patch):
        hist = self.cv.calcHist([patch], [0], None, [24], [0, 256])
        hist = self.cv.GaussianBlur(hist, (1, 3), 0).ravel()
        return hist / max(float(hist.sum()), 1)

    def _start_visual(self, gray):
        factory = getattr(self.cv, 'TrackerCSRT_create', None)
        if factory is None:
            return
        params = self.cv.TrackerCSRT_Params()
        params.template_size = 100
        params.number_of_scales = 17
        params.admm_iterations = 2
        params.use_color_names = False
        params.psr_threshold = .06
        box = tuple(round(v) for v in self.boxes['animal'])
        tracker = factory(params)
        tracker.init(self.cv.cvtColor(gray, self.cv.COLOR_GRAY2BGR), box)
        self.visual = tracker
        if self.body_hist is None:
            self.body_hist = self._histogram(self._patch(gray, box))
        self.appearance_misses = 0

    def initialize(self, gray, boxes, now):
        # Chest geometry must never determine coarse camera observation.
        self.body_hist = None
        self.visual = None
        super().initialize(gray, {k: v for k, v in boxes.items() if k == 'animal'}, now)
        if self.state != 'lost':
            self._start_visual(gray)

    def lose(self, reason):
        super().lose(reason)
        self.visual = None

    def _recover_body(self, gray, now):
        # Only geometric correspondence to the original selected patient may
        # restart tracking. Never use scene silhouettes, histogram-only matches,
        # or subsequently learned poses to establish identity after a loss.
        if self.search_ts is not None and now - self.search_ts < 1.0:
            return
        if self.search_ts is not None and now - self.search_ts > 2.5:
            self.candidate = None
            self.candidate_hits = 0
            self.candidate_since = None
        self.search_ts = now
        recovery = self.recovery
        if not recovery.references:
            return
        cv, np = self.cv, self.np
        recovery.orb.setMaxFeatures(400)
        mask = np.full_like(gray, 255)
        height, width = gray.shape
        for x, y, w, h in recovery.exclusions:
            mask[round(y*height):round((y+h)*height),
                 round(x*width):round((x+w)*width)] = 0
        keys, descriptors = recovery.orb.detectAndCompute(gray, mask)
        found = None
        if descriptors is not None and len(keys) >= 12:
            points = np.array([key.pt for key in keys], dtype=np.float32)
            ref = recovery.references[0]
            src, dst, _ = recovery._correspondences(ref, descriptors, points)
            if len(src) >= 12:
                found = recovery._geometric(gray, ref, src, dst)
            # Repeated fur patterns alone are common. Reject ambiguity only
            # when a second separated object also has geometric support.
            if found is not None:
                outside = ~recovery._inside(points, found['boxes']['animal'])
                if int(outside.sum()) >= 12:
                    other_src, other_dst, _ = recovery._correspondences(
                        ref, descriptors[outside], points[outside])
                    if len(other_src) >= 12 and recovery._geometric(gray, ref, other_src, other_dst):
                        found = None
        if found is None:
            self.candidate = None
            self.candidate_hits = 0
            self.candidate_since = None
            self.reason = 'searching_verified_body'
            return
        box = found['boxes']['animal']
        if self.candidate is None or self._overlap(box, self.candidate) < .65:
            self.candidate_hits = 0
            self.candidate_since = now
        self.candidate = box
        self.candidate_hits += 1
        self.reason = 'confirming_verified_body'
        if self.candidate_hits < 3 or now - self.candidate_since < 2:
            return
        self.boxes = {'animal': box}
        self.previous = gray.copy()
        self.last_ts = now
        self.stable_frames = 0
        self.confidence = found['confidence']
        self.respiration_ready = False
        self.state = 'acquiring'
        self.reason = 'recovery_stabilizing'
        if self.recovery_kind == 'cached':
            # The current-frame selection histogram predates cache restoration.
            # Replace it only after the persisted patient's identity is verified.
            self.body_hist = None
        self.recovery_kind = 'verified_body_features'
        self.generation += 1
        self._start_visual(gray)
        self.candidate = None
        self.candidate_hits = 0
        self.candidate_since = None

    def update(self, gray, now):
        if self.state == 'lost':
            self._recover_body(gray, now)
            return
        if self.visual is None:
            super().update(gray, now)
            if self.state not in ('lost', 'unselected'):
                self.boxes.pop('respiration', None)
                self.respiration_ready = False
                self._start_visual(gray)
            return
        if self.last_ts is None or not 0 < now - self.last_ts <= 3:
            self.lose('frame_gap')
            return
        old_patch = self._patch(self.previous, self.boxes['animal'])
        current_patch = self._patch(gray, self.boxes['animal'])
        same = (old_patch.shape == current_patch.shape and old_patch.size > 0
                and float(old_patch.std()) >= 8 and float(current_patch.std()) >= 8
                and float(self.cv.matchTemplate(current_patch, old_patch,
                                               self.cv.TM_CCOEFF_NORMED)[0, 0]) >= .98)
        # Avoid correlation-filter drift and unnecessary work on unchanged fur.
        ok, box = ((True, self.boxes['animal']) if same else
                   self.visual.update(self.cv.cvtColor(gray, self.cv.COLOR_GRAY2BGR)))
        x, y, w, h = box
        height, width = gray.shape
        if not ok or min(w, h) < 8 or x < 0 or y < 0 or x+w > width or y+h > height:
            self.lose('body_visual_lost')
            return
        px, py, pw, ph = self.boxes['animal']
        displacement = math.hypot(x+w/2-px-pw/2, y+h/2-py-ph/2)
        if displacement > .6 * math.hypot(pw, ph):
            self.lose('body_position_unverified')
            return
        patch = self._patch(gray, box)
        if not patch.size or float(patch.std()) < 8:
            self.lose('occluded')
            return
        # A tracker returning a rectangle alone is insufficient: disappearing
        # into uniform bedding or a different surface must invalidate the lock.
        histogram = self._histogram(patch)
        score = float(self.np.minimum(self.body_hist, histogram).sum())
        self.appearance_misses = self.appearance_misses + 1 if score < .65 else 0
        if score < .35 or self.appearance_misses >= 3:
            self.lose('body_appearance_changed')
            return
        px, py, pw, ph = self.boxes['animal']
        speed = math.hypot(x+w/2-px-pw/2, y+h/2-py-ph/2) / (now-self.last_ts)
        moving = speed > 5
        self.stable_frames += 1
        self.state = ('acquiring' if self.appearance_misses else 'moving' if moving else
                      'locked' if self.stable_frames >= 3 else 'acquiring')
        self.reason = ('appearance_confirming' if self.appearance_misses else 'animal_moving' if moving
                       else 'stable' if self.state == 'locked' else 'stabilizing')
        self.boxes = {'animal': tuple(float(v) for v in box)}
        self.confidence = min(.95, score)
        self.motion_activity = min(100., 100*speed/max(min(w,h),1)) if moving else 0.
        self.previous = gray.copy()
        self.last_ts = now
        self.recovery_kind = 'selected_body_visual'
        # Keep the operator-selected appearance fixed: gradual drift must not
        # teach the validator to accept the background as the patient.
        self._maintain_reference(gray, now)
