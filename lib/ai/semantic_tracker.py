"""Observation follows independently recognized animals, never learned furniture."""
import math
from collections import deque
from .region_tracker import RegionTracker
from .semantic_detector import AnimalDetectionWorker


class SemanticBodyTracker(RegionTracker):
    SEARCH_INTERVAL = 2.0
    STABLE_INTERVAL = 5.0
    RECOGNITION_MAX_AGE = 8.0

    def __init__(self, cv, np, worker=None):
        super().__init__(cv, np, observation_only=True)
        self.worker = worker or AnimalDetectionWorker(cv, np)
        self.last_submit = None
        self.last_result = 0
        self.verified_at = None
        self.pending_box = None
        self.hits = 0
        self.detector_ms = 0
        self.detector_calls = 0
        self.detection_confidence = 0
        self.frames = deque(maxlen=32)
        self.flow_gray = None
        self.recognition_urgent = False

    def initialize(self, gray, boxes, now):
        # The explicit selection enables observation; its old coordinates do
        # not establish animal identity after a restart or camera reconnection.
        self.initial_boxes = {k: dict(v) for k, v in boxes.items() if k == 'animal'}
        self.generation += 1
        self.lose('recognition_pending')

    def close(self):
        self.worker.close()

    def lose(self, reason):
        had_body = bool(self.boxes) or self.pending_box is not None
        super().lose(reason)
        self.boxes = {}
        self.flow_gray = None
        self.verified_at = None
        self.pending_box = None
        self.hits = 0
        self.recognition_urgent = had_body and reason in {
            'body_motion_unverified', 'recognition_motion_unverified',
            'camera_disconnected', 'empty_frame', 'capture_error',
            'recognition_expired',
        }
        # Only a capture interruption invalidates in-flight scene evidence.
        # Flow uncertainty must still allow an independently recognized box.
        if reason in ('camera_disconnected', 'empty_frame', 'capture_error'):
            result = self.worker.latest()
            if result:
                self.last_result = result['sequence']
            self.invalid_before = self.last_submit
        elif not hasattr(self, 'invalid_before'):
            self.invalid_before = None

    def _recognition_interval(self):
        # Sparse flow still validates every frame. Only a confidently recognized,
        # consistently tracked body earns fewer model calls. Smooth motion is
        # handled by flow too; a lost/abruptly moving body needs recognition.
        if (self.state not in ('locked', 'moving') or self.stable_frames < 4
                or self.confidence < .75 or self.verified_at is None):
            return self.SEARCH_INTERVAL
        # Leave time for a slow inference and frame delivery before the existing
        # semantic expiry. Never extend the lifetime of an old recognition.
        latency = max(.5, self.detector_ms / 1000)
        return min(self.STABLE_INTERVAL,
                   max(self.SEARCH_INTERVAL, self.RECOGNITION_MAX_AGE - 2*latency - .5))

    def _transport_box(self, before, gray, box):
        if before.shape != gray.shape:
            return None
        cv, np = self.cv, self.np
        if np.array_equal(before, gray):
            return box
        points = self._features(before, box)
        if points is None or len(points) < 8:
            return None
        nxt, valid, _ = cv.calcOpticalFlowPyrLK(before, gray, points, None,
                                              winSize=(31, 31), maxLevel=3)
        if nxt is None:
            return None
        back, backward, _ = cv.calcOpticalFlowPyrLK(gray, before, nxt, None,
                                                   winSize=(31, 31), maxLevel=3)
        if back is None:
            return None
        good = ((valid.ravel() == 1) & (backward.ravel() == 1) &
                (np.linalg.norm(back-points, axis=2).ravel() < 1.5))
        if good.sum() < 8 or good.mean() < .35:
            return None
        source = points.reshape(-1, 2)[good]
        destination = nxt.reshape(-1, 2)[good]
        matrix, inliers = cv.estimateAffinePartial2D(source, destination,
                                                     method=cv.RANSAC, ransacReprojThreshold=2.5)
        if matrix is None or inliers is None or inliers.sum() < 8 or inliers.mean() < .5:
            return None
        scale = math.hypot(matrix[0, 0], matrix[1, 0])
        if not .8 <= scale <= 1.25:
            return None
        x, y, w, h = box
        # Transport the center under rotation; resizing every flow step would
        # accumulate box inflation. Fresh semantic results determine dimensions.
        center = matrix @ np.array([x+w/2, y+h/2, 1])
        x, y = float(center[0]-w/2), float(center[1]-h/2)
        height, width = gray.shape
        x, y = max(0., min(width-w, x)), max(0., min(height-h, y))
        return (x, y, w, h)

    def update_color(self, frame, gray, now):
        self.frames.append((now, gray.copy()))
        if self.flow_gray is not None and self.boxes.get('animal'):
            prior = self.boxes['animal']
            moved = self._transport_box(self.flow_gray, gray, prior)
            if moved is None:
                self.lose('body_motion_unverified')
            else:
                self.boxes['animal'] = moved
                distance = math.hypot(moved[0]-prior[0], moved[1]-prior[1])
                if distance > 2:
                    if distance > max(8, .15*min(prior[2:])):
                        self.recognition_urgent = True
                        self.stable_frames = 0
                    else:
                        self.stable_frames += 1
                    self.state = 'moving'
                else:
                    self.stable_frames += 1
        elif self.flow_gray is not None and self.pending_box is not None:
            moved = self._transport_box(self.flow_gray, gray, self.pending_box)
            self.pending_box = moved
            if moved is None:
                self.hits = 0
                self.state = 'lost'
                self.reason = 'candidate_motion_unverified'
                self.recognition_urgent = True
        self.flow_gray = gray.copy()
        if (self.recognition_urgent or self.last_submit is None
                or now-self.last_submit >= self._recognition_interval()):
            if self.worker.submit(frame, now):
                self.last_submit = now
                self.recognition_urgent = False
        result = self.worker.latest()
        if result and result['sequence'] != self.last_result:
            self.last_result = result['sequence']
            self.detector_ms = result['milliseconds']
            self.detector_calls += 1
            captured = result['captured']
            if (now-captured > self.RECOGNITION_MAX_AGE or (self.invalid_before is not None and captured <= self.invalid_before)):
                return
            detections = result['detections']
            if len(detections) != 1:
                self.lose('recognition_error' if result['error'] else
                          'multiple_animals' if detections else 'animal_not_detected')
                return
            detection = detections[0]
            height, width = gray.shape
            x, y, w, h = detection['box']
            box = (x*width, y*height, w*width, h*height)
            # A model result describes its captured frame, not today's pixels.
            # Carry its box through the intervening frames before displaying it.
            history = [(stamp, image) for stamp, image in self.frames if stamp >= captured-1e-6]
            if not history or abs(history[0][0]-captured) > .01:
                self.lose('recognition_frame_missing')
                return
            for (_, before), (_, after) in zip(history, history[1:]):
                box = self._transport_box(before, after, box)
                if box is None:
                    self.lose('recognition_motion_unverified')
                    return
            x, y, w, h = box[0]/width, box[1]/height, box[2]/width, box[3]/height
            old = self.boxes.get('animal')
            candidate = self.boxes.get('animal', self.pending_box)
            if candidate is None or self._overlap(candidate, box) < .35:
                self.hits = 0
                self.stable_frames = 0
            self.pending_box = box
            self.hits += 1
            self.detection_confidence = detection['confidence']
            if self.hits < 2:
                self.state = 'acquiring'
                self.confidence = 0
                self.boxes = {}
                self.reason = 'confirming_recognized_animal'
                return
            self.boxes = {'animal': box}
            self.verified_at = captured
            self.state = 'locked'
            self.reason = 'animal_recognized'
            # Tracking confidence includes repeated semantic/spatial agreement;
            # expose the model score separately rather than calling it identity.
            self.confidence = min(.95, .55+.4*detection['confidence'])
            self.recovery_kind = 'semantic_cat_dog'
            if old is None:
                self.generation += 1
            elif math.hypot(x+w/2-(old[0]+old[2]/2)/width,
                            y+h/2-(old[1]+old[3]/2)/height) > .03:
                self.state = 'moving'
        if self.verified_at is not None and now-self.verified_at > self.RECOGNITION_MAX_AGE:
            self.lose('recognition_expired')
