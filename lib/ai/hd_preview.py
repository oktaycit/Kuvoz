"""Low-cost HD viewing stream; never used as input to tracking or vitals."""
import threading
import time
from .ip_camera import fit_preview_frame
from .camera_discovery import CameraResolver

try:
    import av
except ImportError:
    av = None


class KeyframePreview:
    def __init__(self, cv, url, resolution, mac=""):
        self.cv, self.url, self.resolution = cv, url, resolution
        self._stop = threading.Event()
        self.resolver = CameraResolver(url, mac, self._stop)
        self._lock = threading.Lock()
        self._frame = None
        self._timestamp = 0.0
        self.thread = None
        if av is not None:
            self.thread = threading.Thread(target=self._run, name='hd-preview', daemon=True)
            self.thread.start()

    def _run(self):
        self.cv.ocl.setUseOpenCL(False)
        # Native codec logs can include credentials; report availability via status.
        av.logging.set_level(av.logging.PANIC)
        while not self._stop.is_set():
            try:
                resolved = self.resolver.resolve()
                if not resolved:
                    self._stop.wait(2.0)
                    continue
                self.url = resolved
                with av.open(self.url, options={'rtsp_transport': 'tcp'}, timeout=(3, 3)) as container:
                    stream = container.streams.video[0]
                    stream.codec_context.skip_frame = 'NONKEY'
                    stream.codec_context.thread_count = 1
                    for frame in container.decode(stream):
                        if self._stop.is_set():
                            break
                        if not frame.key_frame or getattr(frame, 'is_corrupt', False):
                            continue
                        image = fit_preview_frame(self.cv, frame.to_ndarray(format='bgr24'), self.resolution)
                        with self._lock:
                            self._frame = image
                            self._timestamp = time.monotonic()
            except Exception:
                pass
            finally:
                with self._lock:
                    self._frame = None
                    self._timestamp = 0.0
            self._stop.wait(2.0)

    def read(self):
        with self._lock:
            if self._frame is None or time.monotonic() - self._timestamp >= 4.0:
                return None
            return self._frame

    def release(self):
        self._stop.set()
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(timeout=4.0)
        with self._lock:
            self._frame = None
            self._timestamp = 0.0
