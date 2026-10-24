"""Bounded, reconnecting RTSP reader; retain only the newest frame."""
import threading
import time
import math
from urllib.parse import urlsplit
from .camera_discovery import CameraResolver, normalize_mac

try:
    import av
except ImportError:
    av = None


def validate_camera_settings(settings):
    normalize_mac(settings.get('ip_camera_mac', ''))
    source = settings.get('camera_source', 'raspberry_pi')
    if source not in ('raspberry_pi', 'ip'):
        raise ValueError('Geçersiz kamera kaynağı')
    url = str(settings.get('ip_camera_url', '') or '').strip()
    if len(url) > 2048:
        raise ValueError('Kamera adresi çok uzun')
    if url:
        try:
            parsed = urlsplit(url)
            valid = parsed.scheme == 'rtsp' and parsed.hostname and parsed.port != 0
        except ValueError:
            valid = False
        if not valid or any(c.isspace() for c in url):
            raise ValueError('Geçerli bir rtsp:// kamera adresi girin')
    if source == 'ip' and not url:
        raise ValueError('IP kamera için yayın adresi gerekli')
    validate_preview_url(settings, url)
    return source, url


def validate_preview_url(settings, primary_url):
    url = str(settings.get('ip_camera_preview_url', '') or '').strip()
    if not url or not primary_url:
        return ''
    try:
        primary, preview = urlsplit(primary_url), urlsplit(url)
        valid = (len(url) <= 2048 and preview.scheme == 'rtsp' and preview.hostname
                 and preview.port != 0
                 and not any(c.isspace() for c in url))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('HD önizleme aynı kameranın geçerli RTSP yayını olmalı')
    # A later camera replacement must not retain the previous camera's HD feed.
    return url if preview.hostname == primary.hostname else ''


def fit_preview_frame(cv, frame, resolution):
    """Bound preview memory without stretching the image or inventing pixels."""
    height, width = frame.shape[:2]
    scale = min(1.0, resolution[0] / width, resolution[1] / height)
    if scale >= 1.0:
        return frame
    size = (max(1, round(width * scale)), max(1, round(height * scale)))
    return cv.resize(frame, size, interpolation=cv.INTER_AREA)


class IPCamera:
    """Capture ownership stays in the worker, including release on shutdown."""
    def __init__(self, cv2, url, resolution=(320, 240), fps=5.0, mac=""):
        self.cv2 = cv2
        self.url = url
        self._stop = threading.Event()
        self.resolver = CameraResolver(url, mac, self._stop)
        self._lock = threading.Lock()
        self._frame = None
        self._timestamp = 0.0
        self._sequence = 0
        self._consumed = 0
        self.resolution = resolution
        self._warmup_seconds = 10.0
        self.set_analysis_fps(fps)
        self.thread = threading.Thread(target=self._run_av if av is not None else self._run,
                                       name='ip-camera', daemon=True)
        self.thread.start()

    def _run_av(self):
        """Decode the complete low-resolution stream over TCP on one thread.

        Convert only the newest requested samples; dependent codec frames must
        still be decoded. Never publish corrupt or pre-keyframe images.
        """
        self.cv2.ocl.setUseOpenCL(False)
        av.logging.set_level(av.logging.PANIC)
        while not self._stop.is_set():
            try:
                resolved = self.resolver.resolve()
                if not resolved:
                    self._stop.wait(2.0)
                    continue
                self.url = resolved
                with av.open(self.url, options={'rtsp_transport': 'tcp'}, timeout=(3, 5)) as container:
                    stream = container.streams.video[0]
                    stream.codec_context.thread_count = 1
                    next_output = 0.0
                    ready = False
                    for decoded in container.decode(stream):
                        if self._stop.is_set():break
                        if getattr(decoded, 'is_corrupt', False):continue
                        ready = ready or decoded.key_frame
                        now = time.monotonic()
                        if not ready or now < next_output:continue
                        frame = fit_preview_frame(self.cv2, decoded.to_ndarray(format='bgr24'), self.resolution)
                        next_output = now + 1.0/self._output_fps
                        with self._lock:
                            self._frame = frame
                            self._timestamp = time.monotonic()
                            self._sequence += 1
            except Exception:
                # Codec exceptions can contain camera credentials.
                pass
            finally:
                with self._lock:
                    self._frame = None
                    self._timestamp = 0.0
            self._stop.wait(2.0)

    def set_analysis_fps(self, fps):
        # Slight oversupply keeps the independent analysis loop fed with fresh
        # frames. Inter-frame codecs still need every grab to decode correctly.
        fps = float(fps)
        self._output_fps = max(.5, min(16.0, fps*1.5)) if math.isfinite(fps) else 7.5

    def _run(self):
        cv = self.cv2
        cv.ocl.setUseOpenCL(False)
        while not self._stop.is_set():
            cap = None
            try:
                resolved = self.resolver.resolve()
                if not resolved:
                    self._stop.wait(2.0)
                    continue
                self.url = resolved
                cap = cv.VideoCapture(self.url, cv.CAP_FFMPEG, [
                    cv.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000,
                    cv.CAP_PROP_READ_TIMEOUT_MSEC, 3000,
                ])
                next_output = 0.0
                ready_after = time.monotonic() + getattr(self, '_warmup_seconds', 0.0)
                while not self._stop.is_set() and cap.isOpened():
                    if not cap.grab():
                        break
                    now = time.monotonic()
                    # A connection can begin between H.265 keyframes. Decode
                    # through startup corruption before creating tracking anchors.
                    if now < ready_after:
                        continue
                    if now < next_output:
                        continue
                    ok, frame = cap.retrieve()
                    if not ok:
                        break
                    interval = 1.0/self._output_fps
                    next_output = max(next_output+interval, now)
                    frame = fit_preview_frame(cv, frame, self.resolution)
                    with self._lock:
                        self._frame = frame
                        self._timestamp = time.monotonic()
                        self._sequence += 1
            except Exception:
                # Never log capture exceptions: they can contain URL credentials.
                pass
            finally:
                if cap is not None:
                    cap.release()
                with self._lock:
                    self._frame = None
                    self._timestamp = 0.0
            self._stop.wait(2.0)

    def is_fresh(self):
        with self._lock:
            return self._frame is not None and time.monotonic() - self._timestamp < 3.0

    def read(self):
        with self._lock:
            if (self._frame is None or time.monotonic() - self._timestamp >= 3.0
                    or self._sequence == self._consumed):
                return False, None
            self._consumed = self._sequence
            return True, self._frame

    def release(self):
        self._stop.set()
        self.thread.join(timeout=4.0)
