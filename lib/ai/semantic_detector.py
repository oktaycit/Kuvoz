"""Local cat/dog recognition with Google's EfficientDet-Lite0 int8 model.

The anchor ordering and box decoding follow google/automl efficientdet/tf2.
See models/ for the source and checksum. No frames leave the device.
"""
import logging
import os
from pathlib import Path
import threading
import time

logger = logging.getLogger(__name__)
MODEL_PATH = Path(os.getenv('KUVOZ_AI_ANIMAL_MODEL', str(Path(__file__).parent / 'models/efficientdet_lite0.tflite')))


class AnimalModel:
    def __init__(self, cv, np, path=MODEL_PATH, threshold=.4):
        import sys
        try:
            from tflite_runtime.interpreter import Interpreter
        except ImportError:
            runtime = Path(__file__).resolve().parents[2] / '.runtime/tflite'
            sys.path.insert(0, str(runtime))
            from tflite_runtime.interpreter import Interpreter
        self.cv, self.np, self.threshold = cv, np, threshold
        self.model = Interpreter(str(path), num_threads=1)
        self.model.allocate_tensors()
        self.input = self.model.get_input_details()[0]
        self.outputs = self.model.get_output_details()
        if tuple(self.input['shape']) != (1, 320, 320, 3) or self.input['dtype'] != np.uint8:
            raise ValueError('Unexpected EfficientDet input')
        self.anchors = self.make_anchors(np)

    @staticmethod
    def make_anchors(np):
        # EfficientDet-Lite0: levels 3..7, three octave scales and aspect ratios.
        # Feature strides use actual ceil-divided feature dimensions, including
        # the last 3x3 level. Ordering follows Google's tf2/anchors.py.
        levels = []
        for count in (40, 20, 10, 5, 3):
            stride = 320/count
            xx, yy = np.meshgrid((np.arange(count)+.5)*stride,
                                 (np.arange(count)+.5)*stride)
            configurations = []
            for octave in range(3):
                base = 4*stride*2**(octave/3)
                for ratio in (1., 2., .5):
                    w = base*np.sqrt(ratio)
                    h = base/np.sqrt(ratio)
                    configurations.append(np.column_stack((yy.ravel(), xx.ravel(),
                                                           np.full(count*count, h), np.full(count*count, w))))
            levels.append(np.stack(configurations, axis=1).reshape(-1, 4))
        return np.concatenate(levels).astype(np.float32)

    @staticmethod
    def unrotate(box, rotation):
        x, y, w, h = box
        if rotation == 1:
            return (1-y-h, x, h, w)
        if rotation == 2:
            return (1-x-w, 1-y-h, w, h)
        if rotation == 3:
            return (y, 1-x-w, h, w)
        return box

    def detect(self, frame, rotation=0):
        cv, np = self.cv, self.np
        image = cv.cvtColor(cv.resize(np.rot90(frame, rotation).copy(), (320, 320)), cv.COLOR_BGR2RGB)
        self.model.set_tensor(self.input['index'], image[None])
        self.model.invoke()
        outputs = [self.model.get_tensor(v['index'])[0] for v in self.outputs]
        cls = next(v for v in outputs if v.shape[-1] == 90)
        reg = next(v for v in outputs if v.shape[-1] == 4)
        if len(cls) != len(self.anchors) or len(reg) != len(self.anchors):
            raise ValueError('Unexpected EfficientDet output anchors')
        animal = cls[:, 16:18]  # COCO 90-label map: cat, dog.
        scores = animal.max(axis=1)
        selected = np.flatnonzero(scores >= self.threshold)
        if not len(selected):
            return []
        anchors, offsets = self.anchors[selected], reg[selected]
        center = offsets[:, :2]*anchors[:, 2:] + anchors[:, :2]
        size = np.exp(np.clip(offsets[:, 2:], -10, 10))*anchors[:, 2:]
        lower = np.clip(center-size/2, 0, 320)
        upper = np.clip(center+size/2, 0, 320)
        boxes = np.column_stack((lower[:, 1], lower[:, 0], upper[:, 1]-lower[:, 1], upper[:, 0]-lower[:, 0]))
        valid = np.flatnonzero((boxes[:, 2] >= 8) & (boxes[:, 3] >= 8))
        if not len(valid):
            return []
        boxes, selected = boxes[valid], selected[valid]
        kept = np.asarray(cv.dnn.NMSBoxes(boxes.tolist(), scores[selected].tolist(), self.threshold, .4)).reshape(-1)
        return [dict(box=self.unrotate(tuple(float(v/320) for v in boxes[int(i)]), rotation),
                     confidence=float(scores[selected[int(i)]]),
                     label='cat' if animal[selected[int(i)]].argmax() == 0 else 'dog') for i in kept]


class AnimalDetectionWorker:
    """One bounded background job; old results cannot outlive the tracker."""
    def __init__(self, cv, np):
        self.cv, self.np = cv, np
        self.condition = threading.Condition()
        self.pending = None
        self.result = None
        self.busy = False
        self.closed = False
        self.sequence = 0
        self.thread = threading.Thread(target=self._run, name='animal-recognition', daemon=True)
        self.thread.start()

    def submit(self, frame, timestamp):
        with self.condition:
            if self.closed or self.busy or self.pending is not None:
                return False
            # Bound retained input to a single small color frame.
            self.pending = (self.cv.resize(frame, (320, 320)), timestamp)
            self.condition.notify()
            return True

    def latest(self):
        with self.condition:
            return self.result

    def close(self):
        with self.condition:
            self.closed = True
            self.pending = None
            self.condition.notify()

    def _run(self):
        self.cv.ocl.setUseOpenCL(False)
        try:
            if hasattr(os, 'setpriority'):
                os.setpriority(os.PRIO_PROCESS, threading.get_native_id(), 10)
        except OSError:
            pass
        model = None
        rotation = 0
        while True:
            with self.condition:
                self.condition.wait_for(lambda: self.closed or self.pending is not None)
                if self.closed:
                    return
                frame, captured = self.pending
                self.pending = None
                self.busy = True
            start = time.monotonic()
            error = None
            try:
                if model is None:
                    model = AnimalModel(self.cv, self.np)
                detections = model.detect(frame, rotation)
            except Exception as exc:
                detections = []
                error = str(exc)
                logger.warning('Animal recognition failed: %s', exc)
            elapsed = (time.monotonic()-start)*1000
            if len(detections) != 1:
                rotation = (rotation+1) % 4
            with self.condition:
                self.busy = False
                if self.closed:
                    return
                self.sequence += 1
                self.result = dict(sequence=self.sequence, captured=captured, detections=detections,
                                   error=error, milliseconds=round(elapsed, 1))
