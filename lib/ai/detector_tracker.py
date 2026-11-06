"""Pose-independent selected animal appearance, with separate verified chest correspondence."""
import math
from .region_tracker import RegionTracker


class DetectorTracker(RegionTracker):
    def __init__(self, cv, np, detector):
        super().__init__(cv, np)
        self.detector = detector
        self.detected_at = None
        self.detected_box = None
        self.detected_score = 0.0
        self.detection_hits = 0
        self.detect_due = 0.0
        self.still_since = None
        self.flow_at = None
        self.chest_template = None
        self.respiration_source = None
        self.chest_probe_at = None
        self.scene_started = False

    def _drop_chest(self):
        if self.respiration_ready:
            self.generation += 1
        self.respiration_ready = False
        self.boxes.pop('respiration', None)
        self.chest_template = None
        self.respiration_source = None
        self._confirm_chest(None, 0)

    def _shift(self, box, dx, dy, shape):
        x, y, w, h = box
        return (max(0., min(shape[1]-w, x+dx)), max(0., min(shape[0]-h, y+dy)), w, h)

    def update_color(self, frame, gray, now):
        cv, np = self.cv, self.np
        if not self.scene_started:
            self._drop_chest(); self.scene_started = True
            self.state = 'lost'; self.points = None
        if now >= self.detect_due:
            # Stable flow needs only one scene check every five seconds.
            self.detect_due = now + (5.0 if self.state == 'locked' else 2.0)
            try:
                self.detector.hint = self.boxes.get('animal') if self.state!='lost' else None
                detections = self.detector.detect(frame)
            except Exception:
                detections = []
            if len(detections) != 1:
                self.detection_hits = 0
                self._drop_chest()
                self.lose('multiple_animals' if detections else 'animal_not_detected')
                self.detected_at = None
                return
            found = detections[0]; box = found['box']
            if self.detected_box is None or self._overlap(self.detected_box, box) < .25:
                self.detection_hits = 0
                self.still_since = None
                self._drop_chest()
            self.detection_hits += 1
            prior = self.boxes.get('animal')
            # Keep crop dimensions steady under small detector jitter.
            if (prior and self.state != 'lost' and self._overlap(prior, box) > .6 and
                    abs(prior[2]/box[2]-1) < .2 and abs(prior[3]/box[3]-1) < .2):
                correction = math.hypot(box[0]-prior[0], box[1]-prior[1])
                if correction > 4:
                    self._drop_chest(); self.still_since = None
                    self.boxes['animal'] = box
            else:
                self.boxes['animal'] = box
                self._drop_chest(); self.still_since = None
            self.detected_box, self.detected_at = box, now
            self.detected_score = found['confidence']
            self.recovery_kind = 'scene_appearance'
            if self.state == 'lost':
                self.state = 'acquiring'
            # Detection must not reset the flow clock on every low-FPS frame:
            # otherwise reacquisition can remain 'acquiring' indefinitely.
            if self.previous is None or self.flow_at is None or prior is None or self._overlap(prior,box)<.25:
                self.points = self._features(gray, self.boxes['animal'])
                self.previous = gray.copy(); self.flow_at = now
        if self.detected_at is None:
            return
        if now-self.detected_at > 8:
            self._drop_chest(); self.lose('detector_expired'); return
        if self.flow_at is not None and now-self.flow_at < .4:
            return
        moving = False
        if self.previous is not None and self.points is not None and len(self.points) >= 8:
            dt = max(now-self.flow_at, .01)
            nxt, valid, _ = cv.calcOpticalFlowPyrLK(self.previous, gray, self.points, None,
                                                   winSize=(21, 21), maxLevel=2)
            dx = dy = 0.0
            if nxt is not None:
                back, backward, _ = cv.calcOpticalFlowPyrLK(gray, self.previous, nxt, None,
                                                          winSize=(21, 21), maxLevel=2)
                if back is not None:
                    good = ((valid.ravel() == 1) & (backward.ravel() == 1) &
                            (np.linalg.norm(back-self.points, axis=2).ravel() < 1.5))
                    if int(good.sum()) >= 6:
                        offsets = (nxt-self.points).reshape(-1, 2)[good]
                        dx, dy = map(float, np.median(offsets, axis=0))
                        moving = math.hypot(dx, dy)/dt > 3.0
                    else:
                        moving = True
            box = self.boxes['animal']; x,y,w,h = map(round, box)
            before = self.previous[y:y+h, x:x+w]; after = gray[y:y+h, x:x+w]
            if before.size and before.shape == after.shape:
                difference = after.astype(np.int16)-before.astype(np.int16)
                change = np.abs(difference-np.median(difference))
                moving = moving or float((change > 18).mean()) > .18
            if abs(dx) + abs(dy) > .3:
                for name in list(self.boxes):
                    self.boxes[name] = self._shift(self.boxes[name], dx, dy, gray.shape)
            self.motion_activity = min(100., math.hypot(dx, dy)/dt*5) if moving else 0.
        else:
            moving = True
            self.detect_due = min(self.detect_due, now + 1.0)
        if moving:
            self.still_since = None; self._drop_chest()
            self.state = 'moving'; self.reason = 'animal_moving'
        else:
            if self.still_since is None:
                self.still_since = now
            stable = now-self.still_since >= 2 and self.detection_hits >= 2
            self.state = 'locked' if stable else 'acquiring'
            self.reason = 'stable' if stable else 'stabilizing'
        self.confidence = min(.99, self.detected_score)
        self.points = self._features(gray, self.boxes['animal'])
        self.previous = gray.copy(); self.flow_at = now; self.last_ts = now
        if self.state != 'locked':
            return
        if self.respiration_ready:
            patch = self._patch(gray, self.boxes['respiration'])
            similarity = (float(cv.matchTemplate(cv.resize(patch,(32,32)), self.chest_template,
                                                cv.TM_CCOEFF_NORMED)[0,0]) if patch.size else 0.)
            if not math.isfinite(similarity) or similarity < .85:
                self._drop_chest()
        if not self.respiration_ready and (self.chest_probe_at is None or now-self.chest_probe_at >= 2):
            self.chest_probe_at = now
            chest = self.recovery.find_chest_features(gray, self.boxes['animal'])
            if chest is None:
                chest = self.recovery.find_local_chest(gray, self.boxes['animal'])
            source = 'reference'
            if chest is None:
                chest = self.recovery.find_surface(gray, self.boxes['animal'])
                source = 'surface'
            if chest is not None and self._inside_body(chest):
                confirmed = self._confirm_chest(chest, now)
                if confirmed and (source!='surface' or (self.chest_hits>=3 and now-self.chest_since>=4)):
                    self.boxes['respiration'] = chest
                    self.respiration_ready = True
                    self.respiration_source = source
                    self.chest_template = cv.resize(self._patch(gray,chest),(32,32))
                    self.generation += 1
            else:
                self._confirm_chest(None, now)
        # Only a verified torso may add an anatomical reference.
        if self.respiration_ready and self.respiration_source=='reference':
            self.recovery.remember(gray, self.boxes, now, verified=True)
        elif self.confidence>=.9:
            self.recovery.remember(gray, {'animal':self.boxes['animal']}, now, verified=True)

    def _inside_body(self, chest):
        x,y,w,h = self.boxes['animal'];cx,cy,cw,ch = chest
        return (x <= cx and y <= cy and cx+cw <= x+w and cy+ch <= y+h and
                120 <= cw*ch <= w*h*.4)
