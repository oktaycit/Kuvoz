from .observation import CameraObservation
import logging
import time
import threading
import base64
import os
import math
from collections import deque
from .ip_camera import IPCamera, validate_camera_settings, fit_preview_frame, validate_preview_url
from .hd_preview import KeyframePreview
from .camera_regions import validate_camera_regions
from .region_tracker import RegionTracker
from .animal_detector import AnimalDetector
from .detector_tracker import DetectorTracker
from .respiration_surface import RespirationSurface
from .reference_cache import ReferenceCache

try:
    from .vital_signs import VitalSignsEstimator
    VITALS_AVAILABLE = True
except Exception:
    VitalSignsEstimator = None
    VITALS_AVAILABLE = False

logger = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np
    # Small CPU images do not benefit from loading a software OpenCL runtime.
    cv2.ocl.setUseOpenCL(False)
    OPENCV_AVAILABLE = True
except ImportError:
    logger.warning("OpenCV/Numpy not found. Vision features disabled.")
    OPENCV_AVAILABLE = False

# Try to import picamera2 for Raspberry Pi native camera support
try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False


def _env_float(name, default, minimum=None, maximum=None):
    try:
        value = float(os.getenv(name, default))
    except (TypeError, ValueError):
        logger.warning("Invalid %s value; using default %s", name, default)
        value = float(default)
    if minimum is not None:
        value = max(float(minimum), value)
    if maximum is not None:
        value = min(float(maximum), value)
    return value


# Thermal throttling constants. Camera analysis now focuses on life-cycle
# tracking, so low FPS is intentional and keeps Raspberry Pi thermals stable.
THERMAL_THROTTLE_TEMP = _env_float("KUVOZ_AI_THERMAL_THROTTLE_TEMP", 62.0, minimum=45.0)
THERMAL_RESTORE_TEMP = _env_float("KUVOZ_AI_THERMAL_RESTORE_TEMP", 58.0, minimum=40.0)
THERMAL_NORMAL_FPS = _env_float("KUVOZ_AI_NORMAL_FPS", 1.0, minimum=0.25, maximum=5.0)
THERMAL_THROTTLED_FPS = _env_float("KUVOZ_AI_THROTTLED_FPS", 0.5, minimum=0.25, maximum=3.0)
if THERMAL_RESTORE_TEMP >= THERMAL_THROTTLE_TEMP:
    THERMAL_RESTORE_TEMP = max(40.0, THERMAL_THROTTLE_TEMP - 4.0)

# Dynamic load profiles
NO_ANIMAL_IDLE_SECONDS = 30.0
HIGH_MOTION_ENTER_SECONDS = 3.0
ACTIVE_SUBJECT_ACTIVITY_THRESHOLD = 0.5
HIGH_MOTION_ACTIVITY_THRESHOLD = 10.0
RELIABLE_VITAL_CONFIDENCE = 0.5
STARTUP_VITAL_COLLECTION_SECONDS = 75.0
ANALYSIS_FOCUS_WIDTH_RATIO = 0.72
ANALYSIS_FOCUS_HEIGHT_RATIO = 0.78
SUBJECT_CANDIDATE_MIN_AREA = 60.0
SUBJECT_TRACK_HOLD_SECONDS = 90.0
SUBJECT_EXPAND_WIDTH_FACTOR = 2.8
SUBJECT_EXPAND_HEIGHT_FACTOR = 3.2
SUBJECT_MIN_WIDTH_RATIO = 0.24
SUBJECT_MIN_HEIGHT_RATIO = 0.28
SUBJECT_MAX_WIDTH_RATIO = 0.92
SUBJECT_MAX_HEIGHT_RATIO = 0.95
SUBJECT_TRACK_BLEND_ALPHA = 0.45
SUBJECT_TRACK_MIN_CONFIDENCE = 0.2
SUBJECT_TRACK_ACCEPT_SCORE = 0.3
SUBJECT_TRACK_CONFIRM_FRAMES = 3
VITALS_LOCK_MIN_CONFIDENCE = 0.3
VITALS_HOLD_MIN_CONFIDENCE = 0.45
VITALS_HOLD_GRACE_SECONDS = 8.0
VITALS_MEASUREMENT_HOLD_MIN_CONFIDENCE = 0.2
VITALS_MEASUREMENT_HOLD_GRACE_SECONDS = 20.0
VITALS_RESET_GRACE_SECONDS = 30.0
VITALS_MIN_SUBJECT_AREA_RATIO = 0.06
VITALS_MIN_EDGE_MARGIN_SCORE = 0.12
VITALS_MAX_CENTER_DISTANCE = 0.42
RESPIRATION_ROI_MIN_WIDTH_RATIO = 0.04
RESPIRATION_ROI_MIN_HEIGHT_RATIO = 0.04
RESPIRATION_ROI_MIN_AREA_PIXELS = 120

LOAD_PROFILE_SETTINGS = {
    "normal": {"fps": float(THERMAL_NORMAL_FPS), "jpeg_quality": 42},
    "idle": {"fps": 0.5, "jpeg_quality": 30},
    "motion_limited": {"fps": min(0.75, float(THERMAL_NORMAL_FPS)), "jpeg_quality": 35},
}


class VisionEngine:
    def __init__(self, resolution=(640, 480), fps=5):
        self.resolution = resolution
        # Capture detail for viewing; tracking still uses the small analysis frame.
        self.preview_resolution = (1280, 960)
        self.preview_dimensions = None
        self.preview_jpeg_quality = 82
        self.base_fps = min(float(fps), float(THERMAL_NORMAL_FPS))
        self.local_camera_fps = self.base_fps
        self.profile_fps = self.base_fps
        self.thermal_fps_cap = float(THERMAL_NORMAL_FPS)
        self.target_fps = self.base_fps
        self._throttled = False  # True when thermally throttled
        logger.info(f"⚡ Vision FPS set to {self.target_fps}")
        self.running = False
        self.camera = None
        self.camera_type = None  # 'picamera2' or 'opencv'
        self.last_frame = None
        self.status = "IDLE"
        self.activity_level = 0.0
        self.respiration_signal_level = 0.0
        self.vitals_focus_source = "subject_tracking"
        self.latest_jpeg = None
        self._processed_frame_times = deque(maxlen=120)
        self._last_preview_ts = 0.0
        self._last_estimate_ts = 0.0
        self._temperature_ts = None
        self._temperature = None
        self.motion_analysis_pixels = 0
        self._compute_thread_id = None
        self.lock = threading.Lock()
        self.settings_lock = threading.RLock()
        self.activity_history = deque(maxlen=3)  # 3-frame moving average
        self.load_profile = "normal"
        self.load_reason = "startup"
        self.jpeg_quality = LOAD_PROFILE_SETTINGS["normal"]["jpeg_quality"]
        self.no_subject_since_ts = None
        self.high_motion_since_ts = None
        self.last_subject_seen_ts = None
        self.latest_vitals = {"status": "UNAVAILABLE" if not VITALS_AVAILABLE else "NOT_ENOUGH_DATA"}
        self.safe_focus_box = None
        self.analysis_focus_box = None
        self.analysis_focus_source = "pending"
        self.analysis_focus_coverage = 1.0
        self.system_settings = {}
        self.camera_source = "raspberry_pi"
        self.ip_camera_url = ""
        self.ip_camera_preview_url = ""
        self.preview_camera = None
        self._preview_restart_pending = False
        self.hd_preview_active = False
        self._camera_restart_pending = False
        self.camera_transform = "normal"
        self._surface_respiration = None
        self._animal_detector = None
        self.region_tracker = None
        self._region_tracker_signature = None
        self._region_tracking_generation = None
        self.reference_cache_dir = os.getenv('KUVOZ_AI_CAMERA_REFERENCE_DIR')
        self._reference_cache = None
        self._reference_cache_last_save = None
        self._reference_restored = False
        self._tracked_regions = {}
        self.animal_roi = None
        self.respiration_roi_enabled = False
        self.respiration_roi = None
        self.respiration_roi_frame_box = None
        self.respiration_roi_revision = 0
        self.active_respiration_roi_revision = 0
        self.frame_dimensions = {
            "width": int(self.resolution[0]),
            "height": int(self.resolution[1]),
        }
        self.analysis_started_ts = None
        self.analysis_observation_until_ts = None
        self.subject_box = None
        self.subject_tracking_state = "searching"
        self.subject_tracking_confidence = 0.0
        self.subject_box_updated_ts = None
        self.pending_subject_box = None
        self.pending_subject_score = 0.0
        self.pending_subject_streak = 0
        self.last_vitals_sample_ts = None

        self.vitals = VitalSignsEstimator() if VITALS_AVAILABLE else None  # Legacy helpers only; sampling disabled.
        self.observation = CameraObservation()

    # ------------------------------------------------------------------
    # Runtime settings
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_camera_transform(transform):
        normalized = str(transform or "normal").strip().lower()
        aliases = {
            "none": "normal",
            "default": "normal",
            "180": "rotate_180",
            "rotate180": "rotate_180",
            "rotated_180": "rotate_180",
            "horizontal": "flip_horizontal",
            "mirror": "flip_horizontal",
            "vertical": "flip_vertical",
        }
        if normalized in aliases:
            normalized = aliases[normalized]
        if normalized in {"normal", "rotate_180", "flip_horizontal", "flip_vertical"}:
            return normalized
        return "normal"

    @staticmethod
    def _normalize_unit_box(box):
        if not isinstance(box, dict):
            return None

        try:
            x = float(box.get("x"))
            y = float(box.get("y"))
            width = float(box.get("width"))
            height = float(box.get("height"))
        except (TypeError, ValueError):
            return None

        values = (x, y, width, height)
        if not all(math.isfinite(value) for value in values):
            return None

        x = max(0.0, min(1.0, x))
        y = max(0.0, min(1.0, y))
        width = max(0.0, min(1.0 - x, width))
        height = max(0.0, min(1.0 - y, height))

        if width < RESPIRATION_ROI_MIN_WIDTH_RATIO or height < RESPIRATION_ROI_MIN_HEIGHT_RATIO:
            return None

        return {
            "x": round(x, 4),
            "y": round(y, 4),
            "width": round(width, 4),
            "height": round(height, 4),
        }

    def set_system_settings(self, settings):
        """Update vision-specific runtime settings without restarting AI."""
        if not isinstance(settings, dict):
            settings = {}

        source, url = validate_camera_settings(settings)
        preview_url = validate_preview_url(settings, url)
        enabled = settings.get("respiration_roi_enabled") is True
        roi = self._normalize_unit_box(settings.get("respiration_roi")) if enabled else None
        # Legacy files with invalid respiration boxes continue to disable that ROI.
        regions = validate_camera_regions(dict(settings, respiration_roi_enabled=bool(roi), respiration_roi=roi))
        animal_roi = regions.get("animal")
        camera_transform = self._normalize_camera_transform(settings.get("camera_transform"))
        roi_signature = (
            bool(enabled and roi),
            tuple(roi.items()) if roi else None,
        )

        with self.settings_lock:
            previous_roi_signature = (
                bool(self.respiration_roi_enabled and self.respiration_roi),
                tuple(self.respiration_roi.items()) if self.respiration_roi else None,
            )
            previous_camera_transform = self.camera_transform
            identity_changed = settings.get("ip_camera_mac", "") != self.system_settings.get("ip_camera_mac", "")
            if source != self.camera_source or identity_changed or (source == "ip" and url != self.ip_camera_url):
                self._camera_restart_pending = True
            if preview_url != self.ip_camera_preview_url or identity_changed:
                self._preview_restart_pending = True
            self.ip_camera_preview_url = preview_url
            self.camera_source, self.ip_camera_url = source, url
            try:
                ip_fps = float(settings.get("ip_camera_analysis_fps", 5.0))
                if not math.isfinite(ip_fps):
                    raise ValueError()
            except (TypeError, ValueError):
                ip_fps = 5.0
            self.base_fps = max(3.0, min(8.0, ip_fps)) if source == "ip" else self.local_camera_fps
            self.thermal_fps_cap = float(THERMAL_THROTTLED_FPS) if self._throttled else self.base_fps
            self._set_load_profile(self.load_profile, self.load_reason)
            self.system_settings = dict(settings)
            self.camera_transform = camera_transform
            self.respiration_roi_enabled = bool(enabled and roi)
            self.respiration_roi = roi
            animal_changed = animal_roi != self.animal_roi
            self.animal_roi = animal_roi
            if animal_changed or roi_signature != previous_roi_signature:
                self.respiration_roi_revision += 1

        if camera_transform != previous_camera_transform:
            self.last_frame = None
            self.safe_focus_box = None
            self.analysis_focus_box = None
            self.subject_box = None
            self.subject_tracking_state = "searching"
            self.subject_tracking_confidence = 0.0
            self.pending_subject_box = None
            self.pending_subject_streak = 0
            self._clear_vitals_measurement(reason="camera_transform_changed")
            logger.info(f"🎥 Camera transform changed to {camera_transform}")

    def _get_camera_transform(self):
        with self.settings_lock:
            return self.camera_transform

    def _apply_camera_transform(self, frame):
        transform = self._get_camera_transform()
        if transform == "rotate_180":
            return cv2.rotate(frame, cv2.ROTATE_180)
        if transform == "flip_horizontal":
            return cv2.flip(frame, 1)
        if transform == "flip_vertical":
            return cv2.flip(frame, 0)
        return frame

    def _get_respiration_roi_settings(self):
        with self.settings_lock:
            roi = dict(self.respiration_roi) if self.respiration_roi else None
            return bool(self.respiration_roi_enabled and roi), roi, self.respiration_roi_revision

    # ------------------------------------------------------------------
    # Thermal management
    # ------------------------------------------------------------------
    @staticmethod
    def _read_cpu_temp():
        """Read Raspberry Pi CPU temperature in °C. Returns None if unavailable."""
        try:
            temp_path = "/sys/class/thermal/thermal_zone0/temp"
            if os.path.exists(temp_path):
                with open(temp_path, "r") as f:
                    return float(f.read().strip()) / 1000.0
        except Exception:
            pass
        # Fallback: vcgencmd measure_temp
        try:
            import subprocess
            out = subprocess.check_output(["vcgencmd", "measure_temp"], text=True)
            # Output: temp=45.0'C
            return float(out.split("=")[1].split("'")[0])
        except Exception:
            return None

    def _check_thermal_throttle(self):
        """Adjust FPS based on CPU temperature."""
        temp = self._cached_cpu_temp()
        if temp is None:
            return
        if not self._throttled and temp >= THERMAL_THROTTLE_TEMP:
            self.thermal_fps_cap = float(THERMAL_THROTTLED_FPS)
            self._throttled = True
            self._refresh_target_fps()
            logger.warning(f"🌡️  CPU temp {temp:.1f}°C ≥ {THERMAL_THROTTLE_TEMP}°C — throttled to {self.target_fps:.1f} FPS")
        elif self._throttled and temp < THERMAL_RESTORE_TEMP:
            self.thermal_fps_cap = self.base_fps
            self._throttled = False
            self._refresh_target_fps()
            logger.info(f"🌡️  CPU temp {temp:.1f}°C < {THERMAL_RESTORE_TEMP}°C — restored to {self.target_fps:.1f} FPS")

    def _cached_cpu_temp(self):
        now = time.monotonic()
        if self._temperature_ts is None or now-self._temperature_ts >= 5.0:
            self._temperature = self._read_cpu_temp()
            self._temperature_ts = now
        return self._temperature

    def _refresh_target_fps(self):
        effective_fps = max(0.25, min(self.base_fps, self.profile_fps, self.thermal_fps_cap))
        if abs(effective_fps - self.target_fps) < 1e-6:
            return

        self.target_fps = effective_fps
        if self.camera_type == 'ip' and self.camera:
            self.camera.set_analysis_fps(self.target_fps)
        if self.camera_type == 'opencv' and self.camera:
            try:
                self.camera.set(cv2.CAP_PROP_FPS, self.target_fps)
            except Exception:
                logger.debug("Could not apply updated FPS to OpenCV capture", exc_info=True)

    @staticmethod
    def _to_float(value):
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _has_reliable_vitals(self, vitals):
        if not isinstance(vitals, dict):
            return False

        confidence = self._to_float(vitals.get("confidence")) or 0.0
        return (
            vitals.get("status") == "OK"
            and self._to_float(vitals.get("respiration_bpm")) is not None
            and confidence >= RELIABLE_VITAL_CONFIDENCE
        )

    def _animal_detected(self, vitals):
        if self.region_tracker:
            return self.region_tracker.state in ('locked', 'acquiring', 'moving')
        if self._subject_present():
            return True
        if self.status == "HAREKETLI" or self.activity_level >= ACTIVE_SUBJECT_ACTIVITY_THRESHOLD:
            return True
        return self._has_reliable_vitals(vitals)

    def _subject_present(self, now=None):
        if self.subject_box is None:
            return False

        if now is None:
            now = time.time()

        if self.subject_tracking_state == "locked":
            return self.subject_tracking_confidence >= SUBJECT_TRACK_MIN_CONFIDENCE

        if self.subject_tracking_state != "holding":
            return False

        if self.subject_box_updated_ts is None:
            return False

        age = float(now) - self.subject_box_updated_ts
        return (
            self.subject_tracking_confidence >= VITALS_HOLD_MIN_CONFIDENCE
            and age <= VITALS_HOLD_GRACE_SECONDS
        )

    def _too_much_motion(self, vitals):
        if isinstance(vitals, dict) and vitals.get("status") == "TOO_MUCH_MOTION":
            return True
        return self.activity_level >= HIGH_MOTION_ACTIVITY_THRESHOLD

    def _set_load_profile(self, profile, reason):
        settings = LOAD_PROFILE_SETTINGS[profile]
        profile_changed = profile != self.load_profile

        self.load_profile = profile
        self.load_reason = reason
        if self.camera_source == "ip":
            # Probe for life at 1 FPS; preserve temporal detail during observation.
            profile_fps = {"normal": self.base_fps, "idle": 1.0, "motion_limited": 2.0}[profile]
        else:
            profile_fps = float(settings["fps"])
        self.profile_fps = min(self.base_fps, profile_fps)
        self.jpeg_quality = int(settings["jpeg_quality"])
        self._refresh_target_fps()

        if profile_changed:
            logger.debug(
                "⚙️ Vision load profile -> %s (reason=%s, fps=%.1f, jpeg_quality=%d)",
                self.load_profile,
                self.load_reason,
                self.target_fps,
                self.jpeg_quality,
            )

    def _ensure_observation_window(self, now):
        if self.analysis_started_ts is None:
            self.analysis_started_ts = float(now)
        if self.analysis_observation_until_ts is None:
            self.analysis_observation_until_ts = float(now) + STARTUP_VITAL_COLLECTION_SECONDS

    @staticmethod
    def _box_area(box):
        if not box:
            return 0.0
        x1, y1, x2, y2 = box
        return float(max(x2 - x1, 0) * max(y2 - y1, 0))

    @staticmethod
    def _box_center(box):
        if not box:
            return 0.0, 0.0
        x1, y1, x2, y2 = box
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    def _clip_box(self, box, width, height):
        if not box:
            return None

        x1, y1, x2, y2 = box
        x1 = int(max(0, min(width - 1, round(x1))))
        y1 = int(max(0, min(height - 1, round(y1))))
        x2 = int(max(x1 + 1, min(width, round(x2))))
        y2 = int(max(y1 + 1, min(height, round(y2))))
        return (x1, y1, x2, y2)

    def _respiration_roi_to_frame_box(self, frame_shape):
        enabled, roi, _ = self._get_respiration_roi_settings()
        if self.region_tracker:
            roi = self._tracked_regions.get('respiration') if self.region_tracker.respiration_ready else None
        if not enabled or not roi or not frame_shape:
            self.respiration_roi_frame_box = None
            return None

        height, width = frame_shape[:2]
        frame_width = max(int(width), 1)
        frame_height = max(int(height), 1)
        frame_box = self._normalized_region_box(roi, frame_width, frame_height)
        if not frame_box:
            self.respiration_roi_frame_box = None
            return None

        if self._box_area(frame_box) < RESPIRATION_ROI_MIN_AREA_PIXELS:
            self.respiration_roi_frame_box = None
            return None

        self.respiration_roi_frame_box = frame_box
        return frame_box

    def _normalized_region_box(self, roi, width, height):
        # Round the size independently of translation. Rounding both edges
        # makes an unchanged 76.8px torso alternate between 76 and 77px,
        # needlessly resetting the respiratory observation window.
        x=round(roi['x']*width);y=round(roi['y']*height)
        w=max(1,round(roi['width']*width));h=max(1,round(roi['height']*height))
        return self._clip_box((x,y,x+w,y+h),width,height)

    def _frame_box_to_analysis_box(self, frame_box, safe_focus_box, analysis_shape):
        if not frame_box or not analysis_shape:
            return None

        analysis_height, analysis_width = analysis_shape[:2]
        if safe_focus_box:
            safe_x1, safe_y1, safe_x2, safe_y2 = safe_focus_box
        else:
            safe_x1, safe_y1 = 0, 0
            safe_x2, safe_y2 = analysis_width, analysis_height

        x1 = max(frame_box[0], safe_x1)
        y1 = max(frame_box[1], safe_y1)
        x2 = min(frame_box[2], safe_x2)
        y2 = min(frame_box[3], safe_y2)
        if x2 <= x1 or y2 <= y1:
            return None

        local_box = (
            x1 - safe_x1,
            y1 - safe_y1,
            x2 - safe_x1,
            y2 - safe_y1,
        )
        clipped = self._clip_box(local_box, analysis_width, analysis_height)
        if not clipped or self._box_area(clipped) < RESPIRATION_ROI_MIN_AREA_PIXELS:
            return None
        return clipped

    def _calculate_analysis_focus_box(self, frame_shape):
        height, width = frame_shape[:2]
        focus_width = max(1, min(width, int(round(width * ANALYSIS_FOCUS_WIDTH_RATIO))))
        focus_height = max(1, min(height, int(round(height * ANALYSIS_FOCUS_HEIGHT_RATIO))))

        x1 = max(0, (width - focus_width) // 2)
        y1 = max(0, (height - focus_height) // 2)
        x2 = min(width, x1 + focus_width)
        y2 = min(height, y1 + focus_height)
        return (x1, y1, x2, y2)

    def _set_active_analysis_focus(self, active_box, frame_shape, source):
        if active_box is None:
            self.analysis_focus_box = None
            self.analysis_focus_source = source
            self.analysis_focus_coverage = 1.0
            return

        height, width = frame_shape[:2]
        clipped_box = self._clip_box(active_box, width, height)
        self.analysis_focus_box = clipped_box
        frame_area = max(width * height, 1)
        self.analysis_focus_source = source
        self.analysis_focus_coverage = self._box_area(clipped_box) / frame_area

    def _expand_subject_box(self, candidate_box, frame_shape):
        height, width = frame_shape[:2]
        x1, y1, x2, y2 = candidate_box
        candidate_width = max(x2 - x1, 1)
        candidate_height = max(y2 - y1, 1)
        center_x, center_y = self._box_center(candidate_box)

        target_width = max(
            candidate_width * SUBJECT_EXPAND_WIDTH_FACTOR,
            width * SUBJECT_MIN_WIDTH_RATIO,
        )
        target_height = max(
            candidate_height * SUBJECT_EXPAND_HEIGHT_FACTOR,
            height * SUBJECT_MIN_HEIGHT_RATIO,
        )
        target_width = min(target_width, width * SUBJECT_MAX_WIDTH_RATIO)
        target_height = min(target_height, height * SUBJECT_MAX_HEIGHT_RATIO)

        expanded = (
            center_x - (target_width / 2.0),
            center_y - (target_height / 2.0),
            center_x + (target_width / 2.0),
            center_y + (target_height / 2.0),
        )
        return self._clip_box(expanded, width, height)

    def _normalized_center_distance(self, box, frame_shape):
        height, width = frame_shape[:2]
        diag = max((width ** 2 + height ** 2) ** 0.5, 1.0)
        center_x, center_y = self._box_center(box)
        frame_center_x = width / 2.0
        frame_center_y = height / 2.0
        return min(
            1.0,
            (((center_x - frame_center_x) ** 2 + (center_y - frame_center_y) ** 2) ** 0.5) / diag,
        )

    def _normalized_box_distance(self, box_a, box_b, frame_shape):
        height, width = frame_shape[:2]
        diag = max((width ** 2 + height ** 2) ** 0.5, 1.0)
        ax, ay = self._box_center(box_a)
        bx, by = self._box_center(box_b)
        return min(1.0, (((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5) / diag)

    def _edge_margin_score(self, box, frame_shape):
        height, width = frame_shape[:2]
        x1, y1, x2, y2 = box
        margin_x = min(x1, max(width - x2, 0))
        margin_y = min(y1, max(height - y2, 0))
        normalized_margin = min(
            margin_x / max(width * 0.18, 1.0),
            margin_y / max(height * 0.18, 1.0),
        )
        return max(0.0, min(normalized_margin, 1.0))

    def _box_iou(self, box_a, box_b):
        if not box_a or not box_b:
            return 0.0

        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b
        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)
        inter_area = self._box_area((inter_x1, inter_y1, inter_x2, inter_y2))
        if inter_area <= 0:
            return 0.0

        union_area = self._box_area(box_a) + self._box_area(box_b) - inter_area
        if union_area <= 0:
            return 0.0
        return inter_area / union_area

    def _blend_boxes(self, current_box, target_box, alpha, frame_shape):
        if not current_box:
            return target_box
        if not target_box:
            return current_box

        blended = tuple(
            (current_value * (1.0 - alpha)) + (target_value * alpha)
            for current_value, target_value in zip(current_box, target_box)
        )
        return self._clip_box(blended, frame_shape[1], frame_shape[0])

    def _select_subject_candidate(self, candidate_boxes, frame_shape):
        if not candidate_boxes:
            return None, 0.0

        height, width = frame_shape[:2]
        frame_area = max(height * width, 1)
        previous_subject_box = self.subject_box
        best_box = None
        best_score = -1.0

        for candidate_box in candidate_boxes:
            expanded_box = self._expand_subject_box(candidate_box, frame_shape)
            raw_area_score = min(
                1.0,
                self._box_area(candidate_box) / max(frame_area * 0.025, 1.0),
            )
            center_score = max(
                0.0,
                1.0 - self._normalized_center_distance(expanded_box, frame_shape),
            )
            edge_score = self._edge_margin_score(expanded_box, frame_shape)

            if previous_subject_box:
                overlap_score = self._box_iou(expanded_box, previous_subject_box)
                proximity_score = max(
                    0.0,
                    1.0 - self._normalized_box_distance(expanded_box, previous_subject_box, frame_shape),
                )
                score = (
                    (0.20 * raw_area_score)
                    + (0.10 * center_score)
                    + (0.10 * edge_score)
                    + (0.35 * overlap_score)
                    + (0.30 * proximity_score)
                )
            else:
                score = (0.35 * center_score) + (0.25 * raw_area_score) + (0.40 * edge_score)

            if score > best_score:
                best_score = score
                best_box = expanded_box

        return best_box, max(0.0, min(best_score, 1.0))

    def _tracking_lock_active(self):
        return (
            self.subject_box is not None
            and self.subject_tracking_state in {"locked", "holding"}
            and self.subject_tracking_confidence >= SUBJECT_TRACK_MIN_CONFIDENCE
        )

    def _reset_pending_subject(self):
        self.pending_subject_box = None
        self.pending_subject_score = 0.0
        self.pending_subject_streak = 0

    def _pending_candidate_matches(self, candidate_box, frame_shape):
        if not self.pending_subject_box:
            return False

        overlap = self._box_iou(candidate_box, self.pending_subject_box)
        proximity = max(
            0.0,
            1.0 - self._normalized_box_distance(candidate_box, self.pending_subject_box, frame_shape),
        )
        return overlap >= 0.2 or proximity >= 0.75

    def _promote_subject_lock(self, selected_box, selected_score, now):
        self.subject_box = selected_box
        self.subject_box_updated_ts = float(now)
        self.subject_tracking_state = "locked"
        self.subject_tracking_confidence = round(max(0.35, selected_score), 2)
        self._reset_pending_subject()
        return self.subject_box

    def _vitals_measurement_allowed(self, tracked_subject_box, now):
        if not self.vitals or tracked_subject_box is None:
            return False

        frame_shape = self.last_frame.shape if self.last_frame is not None else None
        if not self._subject_geometry_valid_for_vitals(tracked_subject_box, frame_shape):
            return False

        if self.subject_tracking_state == "locked":
            return self.subject_tracking_confidence >= VITALS_LOCK_MIN_CONFIDENCE

        if self.subject_tracking_state != "holding":
            return False

        if self.subject_box_updated_ts is None:
            return False

        age = float(now) - self.subject_box_updated_ts
        if (
            self.subject_tracking_confidence >= VITALS_HOLD_MIN_CONFIDENCE
            and age <= VITALS_HOLD_GRACE_SECONDS
        ):
            return True

        return (
            self.subject_tracking_confidence >= VITALS_MEASUREMENT_HOLD_MIN_CONFIDENCE
            and age <= VITALS_MEASUREMENT_HOLD_GRACE_SECONDS
        )

    def _subject_geometry_valid_for_vitals(self, subject_box, frame_shape):
        if not subject_box or not frame_shape:
            return False

        frame_area = max(frame_shape[0] * frame_shape[1], 1)
        area_ratio = self._box_area(subject_box) / frame_area
        if area_ratio < VITALS_MIN_SUBJECT_AREA_RATIO:
            return False

        if self._edge_margin_score(subject_box, frame_shape) < VITALS_MIN_EDGE_MARGIN_SCORE:
            return False

        if self._normalized_center_distance(subject_box, frame_shape) > VITALS_MAX_CENTER_DISTANCE:
            return False

        return True

    def _clear_vitals_measurement(self, reason="no_subject"):
        self.respiration_signal_level = 0.0
        self.vitals_focus_source = "none"
        if self._surface_respiration:self._surface_respiration.reset()
        if self.vitals:
            self.vitals.reset()
        self.last_vitals_sample_ts = None
        self.latest_vitals = {
            "status": "NOT_ENOUGH_DATA",
            "respiration_bpm": None,
            "confidence": 0.0,
            "method": "activity_peaks",
            "reason": reason,
            "focus_source": self.vitals_focus_source,
            "respiration_roi_enabled": False,
        }

    def _should_preserve_vitals_window(self, tracked_subject_box, now):
        if not self.vitals or self.last_vitals_sample_ts is None:
            return False

        if (float(now) - float(self.last_vitals_sample_ts)) > VITALS_RESET_GRACE_SECONDS:
            return False

        if tracked_subject_box is None and self.subject_box is None:
            return False

        if self.subject_tracking_state == "locked":
            return self.subject_tracking_confidence >= SUBJECT_TRACK_MIN_CONFIDENCE

        if self.subject_tracking_state != "holding" or self.subject_box_updated_ts is None:
            return False

        age = float(now) - self.subject_box_updated_ts
        return (
            self.subject_tracking_confidence >= VITALS_MEASUREMENT_HOLD_MIN_CONFIDENCE
            and age <= VITALS_MEASUREMENT_HOLD_GRACE_SECONDS
        )

    def _update_subject_tracking(self, candidate_boxes, frame_shape, now):
        selected_box, selected_score = self._select_subject_candidate(candidate_boxes, frame_shape)
        if selected_box is not None and selected_score >= SUBJECT_TRACK_ACCEPT_SCORE:
            if self.subject_box is not None:
                selected_box = self._blend_boxes(
                    self.subject_box,
                    selected_box,
                    SUBJECT_TRACK_BLEND_ALPHA,
                    frame_shape,
                )
                return self._promote_subject_lock(selected_box, selected_score, now)

            if self._pending_candidate_matches(selected_box, frame_shape):
                self.pending_subject_box = self._blend_boxes(
                    self.pending_subject_box,
                    selected_box,
                    SUBJECT_TRACK_BLEND_ALPHA,
                    frame_shape,
                )
                self.pending_subject_score = max(self.pending_subject_score, selected_score)
                self.pending_subject_streak += 1
            else:
                self.pending_subject_box = selected_box
                self.pending_subject_score = selected_score
                self.pending_subject_streak = 1

            if self.pending_subject_streak >= SUBJECT_TRACK_CONFIRM_FRAMES:
                promoted_box = self.pending_subject_box or selected_box
                promoted_score = max(self.pending_subject_score, selected_score)
                return self._promote_subject_lock(promoted_box, promoted_score, now)

            self.subject_tracking_state = "searching"
            self.subject_tracking_confidence = 0.0
            return None

        if self.subject_box is not None and self.subject_box_updated_ts is not None:
            self._reset_pending_subject()
            age = float(now) - self.subject_box_updated_ts
            if age < SUBJECT_TRACK_HOLD_SECONDS:
                hold_ratio = max(0.0, 1.0 - (age / SUBJECT_TRACK_HOLD_SECONDS))
                base_confidence = max(self.subject_tracking_confidence, 0.35)
                self.subject_tracking_state = "holding"
                self.subject_tracking_confidence = round(
                    max(0.15, hold_ratio * base_confidence),
                    2,
                )
                return self.subject_box

        self._reset_pending_subject()
        self.subject_box = None
        self.subject_box_updated_ts = None
        self.subject_tracking_state = "searching"
        self.subject_tracking_confidence = 0.0
        return None

    def _subject_box_to_frame_box(self, subject_box):
        if not subject_box or not self.safe_focus_box:
            return None

        safe_x1, safe_y1, _, _ = self.safe_focus_box
        x1, y1, x2, y2 = subject_box
        return (
            safe_x1 + x1,
            safe_y1 + y1,
            safe_x1 + x2,
            safe_y1 + y2,
        )

    def _find_motion_candidate_boxes(self, motion_mask):
        contours_result = cv2.findContours(
            motion_mask.copy(),
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )
        contours = contours_result[0] if len(contours_result) == 2 else contours_result[1]
        boxes = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < SUBJECT_CANDIDATE_MIN_AREA:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            boxes.append((x, y, x + w, y + h))
        return boxes

    def _calculate_motion_ratio(self, motion_mask):
        if motion_mask is None or getattr(motion_mask, "size", 0) == 0:
            return 0.0

        # OpenCV accepts the binary mask directly; avoid allocating an Nx2
        # coordinate array for every changed pixel.
        x, y, w, h = cv2.boundingRect(motion_mask)
        if not w or not h:
            return 0.0
        roi_area = max(w * h, 1)
        roi_area = max(roi_area, 400)
        roi_count = cv2.countNonZero(motion_mask[y:y + h, x:x + w])
        return (roi_count / roi_area) * 100.0

    def _calculate_vital_signal(self, frame_delta, subject_box=None):
        if frame_delta is None or getattr(frame_delta, "size", 0) == 0:
            return 0.0

        signal_region = frame_delta
        if subject_box is not None:
            roi_x1, roi_y1, roi_x2, roi_y2 = subject_box
            candidate_region = frame_delta[roi_y1:roi_y2, roi_x1:roi_x2]
            if candidate_region is not None and getattr(candidate_region, "size", 0) > 0:
                signal_region = candidate_region

        # Use the average grayscale delta inside the tracked live-being window.
        # This keeps respiratory estimation sensitive to subtle chest motion
        # without inheriting the coarse UI activity percentage.
        if OPENCV_AVAILABLE:
            mean_delta = cv2.mean(signal_region)[0]
        else:
            mean_delta = float(signal_region.mean())
        return float(mean_delta / 2.55)

    def _prepare_motion_gray(self, frame):
        # Preserve fractional grayscale changes through the spatial filter.
        # Filtering uint8 quantizes subtle chest motion away before differencing.
        gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY).astype('float32')
        return cv2.GaussianBlur(gray,(21,21),0)

    def _apply_analysis_focus(self, frame):
        if frame is None or getattr(frame, "size", 0) == 0:
            self.safe_focus_box = None
            self.analysis_focus_box = None
            self.analysis_focus_source = "unavailable"
            self.analysis_focus_coverage = 1.0
            self.respiration_roi_frame_box = None
            return frame, None

        respiration_roi_box = self._respiration_roi_to_frame_box(frame.shape)
        with self.settings_lock:
            animal_roi = dict(self.animal_roi) if self.animal_roi else None
        animal_roi = self._tracked_regions.get("animal", animal_roi)
        if animal_roi:
            height, width = frame.shape[:2]
            box = self._normalized_region_box(animal_roi,width,height)
            self.safe_focus_box = box
            self._set_active_analysis_focus(box, frame.shape, "animal_roi")
            x1, y1, x2, y2 = box
            return frame[y1:y2, x1:x2], box
        if respiration_roi_box is not None:
            height, width = frame.shape[:2]
            full_frame_box = (0, 0, width, height)
            self.safe_focus_box = full_frame_box
            self._set_active_analysis_focus(respiration_roi_box, frame.shape, "respiration_roi")
            return frame, full_frame_box

        focus_box = self._calculate_analysis_focus_box(frame.shape)
        self.safe_focus_box = focus_box
        x1, y1, x2, y2 = focus_box
        focused = frame[y1:y2, x1:x2]
        if focused is None or getattr(focused, "size", 0) == 0:
            self.safe_focus_box = None
            self.analysis_focus_box = None
            self.analysis_focus_source = "full_frame_fallback"
            self.analysis_focus_coverage = 1.0
            return frame, None

        self._set_active_analysis_focus(focus_box, frame.shape, "center_fallback")
        return focused, focus_box

    def _prepare_capture_frames(self, capture):
        hd = self.preview_camera.read() if self.preview_camera else None
        self.hd_preview_active = hd is not None
        preview = fit_preview_frame(cv2, hd if hd is not None else capture, self.preview_resolution)
        analysis = capture
        if (capture.shape[1], capture.shape[0]) != self.resolution:
            analysis = cv2.resize(capture, self.resolution, interpolation=cv2.INTER_AREA)
        analysis = self._apply_camera_transform(analysis)
        preview = self._apply_camera_transform(preview)
        if self.camera_type != "ip":
            analysis = cv2.cvtColor(analysis, cv2.COLOR_BGR2RGB)
            preview = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
        return analysis, preview

    def _publish_preview(self, preview, safe_focus_box=None):
        display = preview.copy()
        sx = display.shape[1] / self.frame_dimensions['width']
        sy = display.shape[0] / self.frame_dimensions['height']
        def scaled(box):
            if box is None:
                return None
            return tuple(round(v * (sx if i % 2 == 0 else sy)) for i, v in enumerate(box))
        self._draw_analysis_focus_overlay(display, scaled(self.analysis_focus_box),
                                          safe_focus_box=scaled(safe_focus_box), show_label=False)
        # Bound Socket.IO payloads even for unusually noisy images.
        limit = 384 * 1024
        for quality in (82, 70, 58):
            ok, buffer = cv2.imencode('.jpg', display, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
            if not ok:
                return
            if buffer.nbytes <= limit:
                break
        if buffer.nbytes > limit:
            display = fit_preview_frame(cv2, display, (800, 600))
            ok, buffer = cv2.imencode('.jpg', display, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
            if not ok or buffer.nbytes > limit:
                return
        with self.lock:
            self.latest_jpeg = base64.b64encode(buffer).decode('utf-8')
            self.preview_dimensions = {"width": display.shape[1], "height": display.shape[0]}
            self.preview_jpeg_quality = quality

    def _draw_analysis_focus_overlay(self, frame, focus_box, safe_focus_box=None, show_label=True):
        if frame is None or focus_box is None:
            return

        if safe_focus_box and safe_focus_box != focus_box:
            safe_x1, safe_y1, safe_x2, safe_y2 = safe_focus_box
            cv2.rectangle(frame, (safe_x1, safe_y1), (safe_x2 - 1, safe_y2 - 1), (243, 156, 18), 1)

        x1, y1, x2, y2 = focus_box
        color = (46, 204, 113)
        label = "CANLI TAKIP"
        if self.analysis_focus_source == "tracked_subject_hold":
            color = (52, 152, 219)
            label = "CANLI KILIT"
        elif self.analysis_focus_source == "respiration_roi":
            color = (26, 188, 156)
            label = "SOLUNUM ROI"
        elif self.analysis_focus_source == "center_fallback":
            color = (243, 156, 18)
            label = "MERKEZ TARAMA"
        if self.region_tracker and self.region_tracker.state == 'lost':
            color, label = (40, 40, 220), 'TAKIP KAYIP'
        elif self.region_tracker and self.region_tracker.state in ('moving', 'acquiring'):
            color, label = (0, 190, 255), 'SOLUNUM BEKLIYOR'
        cv2.rectangle(frame, (x1, y1), (x2 - 1, y2 - 1), color, 2)

        if not show_label:
            return
        label_y = y1 - 8 if y1 >= 20 else min(frame.shape[0] - 8, y1 + 18)
        cv2.putText(
            frame,
            label,
            (x1 + 6, label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            color,
            1,
            cv2.LINE_AA,
        )

    def _serialize_focus_box(self):
        if not self.analysis_focus_box:
            return None

        x1, y1, x2, y2 = self.analysis_focus_box
        return {
            "x": int(x1),
            "y": int(y1),
            "width": int(max(x2 - x1, 0)),
            "height": int(max(y2 - y1, 0)),
        }

    def _serialize_frame_box(self, box):
        if not box:
            return None

        x1, y1, x2, y2 = box
        frame_width = max(int(self.frame_dimensions.get("width") or 0), 1)
        frame_height = max(int(self.frame_dimensions.get("height") or 0), 1)
        width = int(max(x2 - x1, 0))
        height = int(max(y2 - y1, 0))
        return {
            "x": int(x1),
            "y": int(y1),
            "width": width,
            "height": height,
            "x_norm": round(float(x1) / frame_width, 4),
            "y_norm": round(float(y1) / frame_height, 4),
            "width_norm": round(float(width) / frame_width, 4),
            "height_norm": round(float(height) / frame_height, 4),
        }

    def _decorate_vitals(self, vitals, focus_source, respiration_roi_box=None):
        payload = dict(vitals or {})
        payload["focus_source"] = focus_source
        payload["respiration_roi_enabled"] = bool(respiration_roi_box)
        if respiration_roi_box:
            payload["respiration_roi_box"] = self._serialize_frame_box(respiration_roi_box)
        return payload

    def _serialize_subject_box(self):
        frame_box = self._subject_box_to_frame_box(self.subject_box)
        if not frame_box:
            return None

        x1, y1, x2, y2 = frame_box
        frame_width = max(int(self.frame_dimensions.get("width") or 0), 1)
        frame_height = max(int(self.frame_dimensions.get("height") or 0), 1)
        width = int(max(x2 - x1, 0))
        height = int(max(y2 - y1, 0))
        return {
            "x": int(x1),
            "y": int(y1),
            "width": width,
            "height": height,
            "x_norm": round(float(x1) / frame_width, 4),
            "y_norm": round(float(y1) / frame_height, 4),
            "width_norm": round(float(width) / frame_width, 4),
            "height_norm": round(float(height) / frame_height, 4),
        }

    def _update_load_profile(self, vitals=None, now=None):
        if now is None:
            now = time.time()
        self._ensure_observation_window(now)

        if self.region_tracker and self.region_tracker.state == 'lost':
            self._set_load_profile('idle', 'tracking_lost')
            return
        if (self.region_tracker and self.region_tracker.state == 'locked' and
                (not self.respiration_roi_enabled or not self.region_tracker.respiration_ready)):
            self._set_load_profile('motion_limited', 'lifecycle_only')
            return

        snapshot = vitals if isinstance(vitals, dict) else self.latest_vitals
        subject_detected = self._animal_detected(snapshot)
        too_much_motion = self._too_much_motion(snapshot)

        if subject_detected:
            self.last_subject_seen_ts = now
            self.no_subject_since_ts = None
        elif self.no_subject_since_ts is None:
            self.no_subject_since_ts = now

        if too_much_motion:
            if self.high_motion_since_ts is None:
                self.high_motion_since_ts = now
        else:
            self.high_motion_since_ts = None

        desired_profile = "normal"
        reason = "subject_detected"

        if (
            self.high_motion_since_ts is not None
            and (now - self.high_motion_since_ts) >= HIGH_MOTION_ENTER_SECONDS
        ):
            desired_profile = "motion_limited"
            reason = "too_much_motion"
        elif (
            not subject_detected
            and self.analysis_observation_until_ts is not None
            and now < self.analysis_observation_until_ts
        ):
            reason = "startup_vital_collection"
        elif (
            self.no_subject_since_ts is not None
            and (now - self.no_subject_since_ts) >= NO_ANIMAL_IDLE_SECONDS
        ):
            desired_profile = "idle"
            reason = "no_animal_detected"
        elif not subject_detected:
            reason = "probing_for_subject"

        self._set_load_profile(desired_profile, reason)

    def start(self):
        with self.settings_lock:
            self._camera_restart_pending = False
        if not OPENCV_AVAILABLE:
            return False
        
        if self.camera_source == 'ip':
            cv2.setNumThreads(1)
            self.camera = IPCamera(cv2, self.ip_camera_url, resolution=self.preview_resolution, fps=self.target_fps, mac=self.system_settings.get("ip_camera_mac", ""))
            self.camera_type = 'ip'
            self._restart_preview_camera()
            self.running = True
            self.analysis_started_ts = time.time()
            self.analysis_observation_until_ts = self.analysis_started_ts + STARTUP_VITAL_COLLECTION_SECONDS
            return True

        # Strategy 1: Try picamera2 (Raspberry Pi native, modern approach)
        if PICAMERA2_AVAILABLE:
            try:
                logger.info("Attempting to initialize camera with picamera2...")
                picam = Picamera2()
                
                # Configure camera: main stream for capture
                # Use a standard buffer count and explicit format
                config = picam.create_still_configuration(
                    main={"size": self.preview_resolution, "format": "BGR888"},
                    buffer_count=2
                )
                picam.configure(config)
                picam.start()
                
                # Test capture
                time.sleep(2.0)  # Increased warm-up time
                test_frame = picam.capture_array()
                
                if test_frame is not None and test_frame.shape[0] > 0:
                    logger.info(f"✅ Camera initialized successfully with picamera2")
                    logger.info(f"   Resolution: {self.resolution}, FPS: {self.target_fps}")
                    logger.info(f"   Frame shape: {test_frame.shape}")
                    self.camera = picam
                    self.camera_type = 'picamera2'
                    self.running = True
                    self.analysis_started_ts = time.time()
                    self.analysis_observation_until_ts = (
                        self.analysis_started_ts + STARTUP_VITAL_COLLECTION_SECONDS
                    )
                    self.safe_focus_box = None
                    self.subject_box = None
                    self.subject_tracking_state = "searching"
                    self.subject_tracking_confidence = 0.0
                    self.subject_box_updated_ts = None
                    self.analysis_focus_box = None
                    self.analysis_focus_source = "pending"
                    self.analysis_focus_coverage = 1.0
                    logger.info("🎥 Vision Engine started (picamera2).")
                    return True
                else:
                    logger.error("❌ picamera2 opened but returned empty frame during test")
                    logger.error(f"   Frame info: {test_frame}")
                    picam.stop()
                    picam.close()
                    
            except Exception as e:
                logger.error(f"❌ picamera2 initialization failed: {e}", exc_info=True)
                # ⚠️ CRITICAL: always release the camera fd on failure, or /dev/video0 stays busy
                try:
                    picam.stop()
                except Exception:
                    pass
                try:
                    picam.close()
                except Exception:
                    pass
                logger.info("Falling back to OpenCV VideoCapture...")
        
        # Strategy 2: Fallback to OpenCV VideoCapture (for non-RPi or if picamera2 fails)
        try:
            logger.info("Initializing camera with OpenCV VideoCapture (Fallback)...")
            
            # Camera indices and backends to try
            strategies = [
                # (Name, Index, Backend)
                ("Index 0 with V4L2", 0, cv2.CAP_V4L2),
                ("Index 0 with default backend", 0, cv2.CAP_ANY),
                ("Index 1 with V4L2", 1, cv2.CAP_V4L2),
                ("Index 1 with default backend", 1, cv2.CAP_ANY),
            ]
            
            # Configurations to try: (FourCC, Width, Height)
            configs = [
                ('MJPG', *self.preview_resolution),
                ('MJPG', 640, 480),
                ('YUYV', 640, 480),
                ('MJPG', 320, 240),
                (None, 640, 480) # Default
            ]

            for name, idx, backend in strategies:
                logger.info(f"Attempting: {name}...\"")
                
                try:
                    cap = cv2.VideoCapture(idx, backend)
                    if not cap.isOpened():
                        logger.warning(f"  ❌ Could not open camera {name}")
                        continue
                    
                    # Try different format configurations
                    for fourcc, w, h in configs:
                        config_desc = f"{name} - {fourcc if fourcc else 'Default'} {w}x{h}"
                        logger.info(f"  Testing: {config_desc}")
                        
                        # Set camera properties
                        if fourcc:
                            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
                        cap.set(cv2.CAP_PROP_FPS, self.target_fps)
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer
                        
                        # Test if we can actually read frames
                        if self._test_camera_read(cap):
                            logger.info(f"✅ Camera initialized successfully: {config_desc}")
                            self.camera = cap
                            self.camera_type = 'opencv'
                            self.running = True
                            self.analysis_started_ts = time.time()
                            self.analysis_observation_until_ts = (
                                self.analysis_started_ts + STARTUP_VITAL_COLLECTION_SECONDS
                            )
                            self.safe_focus_box = None
                            self.subject_box = None
                            self.subject_tracking_state = "searching"
                            self.subject_tracking_confidence = 0.0
                            self.subject_box_updated_ts = None
                            self.analysis_focus_box = None
                            self.analysis_focus_source = "pending"
                            self.analysis_focus_coverage = 1.0
                            logger.info("🎥 Vision Engine started (OpenCV).")
                            return True
                        else:
                            logger.debug(f"  ❌ Could not read frames from {config_desc}")
                    
                    # If no config worked, release and try next strategy
                    cap.release()
                    logger.debug(f"  No working configuration for {name}")
                    
                except Exception as e:
                    logger.error(f"  Exception with {name}: {e}")

            logger.error("Could not open any camera after trying all configurations.")
            return False
        except Exception as e:
            logger.error(f"Error starting Vision Engine: {e}")
            return False

    def _test_camera_read(self, cap):
        """Helper to test if camera can actually read frames"""
        for _ in range(5):
            ret, _ = cap.read()
            if ret:
                return True
            time.sleep(0.1)
        return False

    def _restart_preview_camera(self):
        self._preview_restart_pending = False
        if self.preview_camera:
            self.preview_camera.release()
            self.preview_camera = None
        if self.camera_type == 'ip' and self.ip_camera_preview_url:
            self.preview_camera = KeyframePreview(cv2, self.ip_camera_preview_url, self.preview_resolution, mac=self.system_settings.get("ip_camera_mac", ""))

    def stop(self):
        self.running = False
        if self.preview_camera:
            self.preview_camera.release()
            self.preview_camera = None
        self.hd_preview_active = False
        if self.camera:
            if self.camera_type == 'picamera2':
                try:
                    self.camera.stop()
                    self.camera.close()
                except:
                    pass
            else:  # opencv
                self.camera.release()
        self.camera = None
        self.region_tracker = None
        self._region_tracker_signature = None
        self._tracked_regions = {}
        with self.lock:
            self.latest_jpeg = None
        self.last_frame = None
        self._processed_frame_times.clear()
        self._last_preview_ts = 0.0
        self._last_estimate_ts = 0.0
        logger.info("Vision Engine stopped.")

    def get_frame(self):
        with self.lock:
            return self.latest_jpeg

    def get_status(self):
        temp = self._cached_cpu_temp()
        vitals_progress = (
            self.vitals.get_progress()
            if self.vitals and hasattr(self.vitals, "get_progress")
            else {}
        )
        return {
            "observation": self.observation.snapshot() if self.running else {
                **self.observation.snapshot(), "quality": "unavailable",
                "movement": "unknown", "activity": None, "posture": "unknown"},
            "status": self.status,
            "activity": round(self.activity_level, 2),
            "respiration_signal": round(self.respiration_signal_level, 3),
            "available": OPENCV_AVAILABLE and self.running and (
                self.camera_type != "ip" or (self.camera is not None and self.camera.is_fresh())
            ),
            "camera_source": self.camera_source,
            "vitals_available": False,
            "cpu_temp": round(temp, 1) if temp is not None else None,
            "throttled": self._throttled,
            "target_fps": round(self.target_fps, 2),
            "effective_fps": round(self._effective_analysis_fps(), 2),
            "pixel_budget": {
                "frame": self.frame_dimensions['width'] * self.frame_dimensions['height'],
                "motion": self.motion_analysis_pixels,
                "tracking": self.region_tracker.flow_pixels if self.region_tracker else 0,
                "respiration": int(self._box_area(self.respiration_roi_frame_box)),
            },
            "load_profile": self.load_profile,
            "load_reason": self.load_reason,
            "jpeg_quality": self.jpeg_quality,
            "preview_dimensions": self.preview_dimensions,
            "preview_jpeg_quality": self.preview_jpeg_quality,
            "preview_source": "main_keyframes" if self.hd_preview_active else "analysis_stream",
            "analysis_focus_source": self.analysis_focus_source,
            "analysis_focus_coverage": round(self.analysis_focus_coverage, 3),
            "analysis_focus_box": self._serialize_focus_box(),
            "vitals_focus_source": self.vitals_focus_source,
            "region_tracking": self._region_tracking_status(),
            "respiration_roi_enabled": bool(self.respiration_roi_enabled),
            "respiration_roi": dict(self.respiration_roi) if self.respiration_roi else None,
            "respiration_roi_box": self._serialize_frame_box(self.respiration_roi_frame_box),
            "subject_box": self._serialize_subject_box(),
            "subject_tracking_state": self.subject_tracking_state,
            "subject_tracking_confidence": self.subject_tracking_confidence,
            "subject_tracking_locked": self._tracking_lock_active(),
            "frame_dimensions": dict(self.frame_dimensions),
            "vitals_sample_count": vitals_progress.get("sample_count"),
            "vitals_window_duration": vitals_progress.get("window_duration"),
            "vitals_last_sample_age": vitals_progress.get("last_sample_age"),
            "startup_collection_active": bool(
                self.analysis_observation_until_ts
                and time.time() < self.analysis_observation_until_ts
            ),
        }

    def get_vitals(self):
        return {"status": "DISABLED", "respiration_bpm": None, "confidence": 0.0}

    def _update_region_tracking(self, frame):
        with self.settings_lock:
            enabled = bool(self.animal_roi or self.respiration_roi_enabled)
            signature = (self.respiration_roi_revision, self.camera_source,
                         self.system_settings.get("ip_camera_mac") or self.ip_camera_url,
                         self.camera_transform, self.system_settings.get('region_tracking_revision', 0))
            regions = {}
            if self.animal_roi:
                regions['animal'] = dict(self.animal_roi)
            if self.respiration_roi_enabled and self.respiration_roi:
                regions['respiration'] = dict(self.respiration_roi)
            cache_identity=[self.camera_source,self.system_settings.get("ip_camera_mac") or self.ip_camera_url,self.camera_transform,
                            self.resolution,regions,self.system_settings.get('region_tracking_revision',0)]
        if not enabled:
            self.region_tracker = None
            self._region_tracker_signature = None
            self._tracked_regions = {}
            self._reference_cache = None
            self._reference_restored = False
            return
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        now = time.monotonic()
        if signature != self._region_tracker_signature:
            if self._animal_detector is None:
                self._animal_detector = AnimalDetector(cv2, np)
            self.region_tracker = (DetectorTracker(cv2, np, self._animal_detector)
                                   if self._animal_detector.available else RegionTracker(cv2, np))
            self._region_tracking_generation = None
            self.region_tracker.recovery.exclusions = [
                (r['x'],r['y'],r['width'],r['height'])
                for name in ('feeding','drinking')
                if self.system_settings.get(name+'_roi_enabled')
                and (r := self._normalize_unit_box(self.system_settings.get(name+'_roi')))
            ]
            self._region_tracker_signature = signature
            self.region_tracker.initialize(gray, regions, now)
            self._reference_cache = (ReferenceCache(self.reference_cache_dir,cache_identity,gray.shape)
                                     if self.reference_cache_dir else None)
            self._reference_restored = False
            self._reference_cache_last_save = None
            restored=self._reference_cache.load(self.region_tracker.recovery) if self._reference_cache else None
            if restored:
                saved,boxes=restored
                tracker=self.region_tracker
                tracker.previous=saved;tracker.boxes=boxes;tracker.anchor_boxes=dict(boxes)
                tracker.anchor_patch=tracker._patch(saved,boxes['animal']).copy()
                tracker.template=cv2.resize(tracker.anchor_patch,(64,64))
                tracker.recovery.last_remembered=now
                tracker.lose('restoring_reference');tracker.recovery_kind='cached'
                self._reference_restored=True
            if isinstance(self.region_tracker, DetectorTracker):
                recent = bool(restored and self._reference_cache and
                              time.time()-self._reference_cache.path.stat().st_mtime<86400)
                self._animal_detector.attach(self.region_tracker.recovery, saved if restored else gray,
                                             boxes.get('animal') if recent else None)
            self.last_frame = None
            self._clear_vitals_measurement(reason='tracking_initializing')
        else:
            if isinstance(self.region_tracker, DetectorTracker):
                self.region_tracker.update_color(frame, gray, now)
            else:
                self.region_tracker.update(gray, now)
        tracker=self.region_tracker
        if (self._reference_cache and tracker.state=='locked' and
                tracker.confidence >= (.8 if isinstance(tracker, DetectorTracker) else .9) and
                (self._reference_cache_last_save is None or now-self._reference_cache_last_save>=60)):
            self._reference_cache_last_save=now
            boxes={k:v for k,v in tracker.boxes.items() if k!='respiration' or (tracker.respiration_ready and getattr(tracker,'respiration_source',None)!='surface')}
            self._reference_cache.save(tracker.recovery,gray,boxes)
        self._tracked_regions = self.region_tracker.normalized_boxes(gray.shape)
        if self._region_tracking_generation != self.region_tracker.generation:
            self._region_tracking_generation = self.region_tracker.generation
            self.last_frame = None
            self.activity_history.clear()
            if self._surface_respiration:self._surface_respiration.reset()
            self._clear_vitals_measurement(reason='tracking_reference_changed')
        if not self._region_vitals_allowed():
            if self._surface_respiration:self._surface_respiration.reset()
            self._clear_vitals_measurement(reason='tracking_' + self.region_tracker.state)
            self._last_estimate_ts = 0.0

    def _region_vitals_allowed(self):
        if self.animal_roi or self.respiration_roi_enabled:
            return (self.region_tracker is not None and self.region_tracker.state == 'locked'
                    and self.region_tracker.confidence >= .8
                    and (not self.respiration_roi_enabled or self.region_tracker.respiration_ready))
        return self.subject_tracking_state == 'locked' and self._tracking_lock_active()

    def _region_tracking_status(self):
        tracker = self.region_tracker
        return {'state': tracker.state if tracker else 'unselected',
                'confidence': round(tracker.confidence, 3) if tracker else 0.0,
                'reason': tracker.reason if tracker else 'no_selection',
                'boxes': dict(self._tracked_regions) if tracker and tracker.state != 'lost' else {},
                'respiration_ready': bool(tracker and tracker.respiration_ready),
                'respiration_source': getattr(tracker,'respiration_source',None),
                'surface_samples': len(self._surface_respiration.samples) if self._surface_respiration else 0,
                'recovery_kind': tracker.recovery_kind if tracker else None,
                'appearance_reference_bytes': tracker.recovery.memory_bytes() if tracker else 0,
                'reference_restored': self._reference_restored,
                'respiration_allowed': self._region_vitals_allowed(),
                'detector_available': bool(self._animal_detector and self._animal_detector.available),
                'detector_ms': self._animal_detector.last_ms if self._animal_detector else 0.0,
                'detector_calls': self._animal_detector.calls if self._animal_detector else 0}

    def _effective_analysis_fps(self):
        now = time.monotonic()
        recent = [t for t in self._processed_frame_times if now - t <= 5.0]
        if len(recent) < 2:
            return 0.0
        return (len(recent) - 1) / max(now - recent[0], 0.001)

    def process_frame(self):
        # Apply camera changes on the analysis thread, never in a socket handler.
        with self.settings_lock:
            restart = self._camera_restart_pending
            self._camera_restart_pending = False
        if restart:
            self.stop()
            self._clear_vitals_measurement(reason="camera_source_changed")
            self.safe_focus_box = None
            self.analysis_focus_box = None
            self.subject_box = None
            self.subject_tracking_state = "searching"
            self.subject_tracking_confidence = 0.0
            self.subject_box_updated_ts = None
            self.pending_subject_box = None
            self.pending_subject_score = 0.0
            self.pending_subject_streak = 0
            self.no_subject_since_ts = None
            self.high_motion_since_ts = None
            self.last_subject_seen_ts = None
            self.activity_level = 0.0
            self.status = "IDLE"
            self.activity_history.clear()
            self.start()
        if self._preview_restart_pending:
            self._restart_preview_camera()
        if not self.running or not self.camera:
            logger.debug("process_frame skipped: running={}, camera={}".format(self.running, self.camera is not None))
            return

        compute_thread = threading.get_ident()
        if OPENCV_AVAILABLE and self._compute_thread_id != compute_thread:
            # OpenCL preference is thread-local in OpenCV.
            cv2.ocl.setUseOpenCL(False)
            self._compute_thread_id = compute_thread

        # Capture frame based on camera type
        try:
            if self.camera_type == 'picamera2':
                frame = self.camera.capture_array()
                if frame is None or frame.shape[0] == 0:
                    if self.region_tracker:
                        self.region_tracker.lose('empty_frame')
                    self._clear_vitals_measurement(reason='empty_frame')
                    logger.warning("Failed to capture frame from picamera2")
                    return
            else:  # opencv
                ret, frame = self.camera.read()
                if not ret:
                    if self.camera_type == 'ip':
                        if not self.camera.is_fresh():
                            with self.lock:
                                self.latest_jpeg = None
                            self.last_frame = None
                            self.activity_level = 0.0
                            self.status = "DISCONNECTED"
                            if self.region_tracker:
                                self.region_tracker.lose('camera_disconnected')
                            self._clear_vitals_measurement(reason="camera_disconnected")
                    else:
                        if self.region_tracker:
                            self.region_tracker.lose('camera_disconnected')
                        self._clear_vitals_measurement(reason='camera_disconnected')
                        logger.warning("Failed to grab frame from OpenCV")
                    return
        except Exception as e:
            if self.region_tracker:
                self.region_tracker.lose('capture_error')
            self._clear_vitals_measurement(reason='capture_error')
            logger.error(f"Error capturing frame: {e}")
            return

        self._processed_frame_times.append(time.monotonic())

        frame, preview_frame = self._prepare_capture_frames(frame)
        self.frame_dimensions = {"width": int(frame.shape[1]), "height": int(frame.shape[0])}

        self._update_region_tracking(frame)
        analysis_frame, safe_focus_box = self._apply_analysis_focus(frame)

        # Convert to grayscale for motion detection inside the live-being focus window.
        gray = self._prepare_motion_gray(analysis_frame)
        self.motion_analysis_pixels = int(gray.size)

        _, _, roi_revision = self._get_respiration_roi_settings()
        if roi_revision != self.active_respiration_roi_revision:
            self.active_respiration_roi_revision = roi_revision
            self.last_frame = None
            self.subject_box = None
            self.subject_box_updated_ts = None
            self.subject_tracking_state = "searching"
            self.subject_tracking_confidence = 0.0
            self.pending_subject_box = None
            self.pending_subject_streak = 0
            self.activity_history.clear()
            self._clear_vitals_measurement(reason="respiration_roi_changed")

        if self.last_frame is not None and self.last_frame.shape != gray.shape:
            self.last_frame = None
            self._clear_vitals_measurement(reason="analysis_focus_changed")

        if self.last_frame is None:
            self.last_frame = gray
            logger.info("🎥 First frame captured and processed successfully")
            return

        # Thermal throttle check (every frame, lightweight)
        self._check_thermal_throttle()

        # Keep the existing activity threshold; respiration uses the raw delta.
        frame_delta = cv2.absdiff(self.last_frame, gray)
        thresh = cv2.threshold(frame_delta, 12, 255, cv2.THRESH_BINARY)[1].astype('uint8')
        thresh = cv2.dilate(thresh, None, iterations=2)

        now = time.time()
        if self.region_tracker:
            # The selected region already has an optical-flow tracker. A second
            # motion-contour tracker would drift toward the head or bowl.
            state = self.region_tracker.state
            tracked_subject_box = (0, 0, gray.shape[1], gray.shape[0]) if state != 'lost' else None
            self.subject_box = tracked_subject_box
            self.subject_tracking_state = 'locked' if state in ('locked', 'moving') else state
            self.subject_tracking_confidence = self.region_tracker.confidence
            self.subject_box_updated_ts = now if tracked_subject_box else None
        else:
            candidate_boxes = self._find_motion_candidate_boxes(thresh)
            tracked_subject_box = self._update_subject_tracking(candidate_boxes, gray.shape, now)
        manual_respiration_box = self._frame_box_to_analysis_box(
            self.respiration_roi_frame_box,
            safe_focus_box,
            gray.shape,
        )
        if tracked_subject_box is not None:
            roi_x1, roi_y1, roi_x2, roi_y2 = tracked_subject_box
            motion_mask = thresh[roi_y1:roi_y2, roi_x1:roi_x2]
            frame_box = self._subject_box_to_frame_box(tracked_subject_box)
            focus_source = ('animal_roi' if self.region_tracker else
                            "tracked_subject_hold" if self.subject_tracking_state == "holding" else "tracked_subject")
            self._set_active_analysis_focus(frame_box, frame.shape, focus_source)
        else:
            motion_mask = thresh
            self._set_active_analysis_focus(safe_focus_box, frame.shape, "center_fallback")

        if manual_respiration_box is not None and self.respiration_roi_frame_box is not None:
            self._set_active_analysis_focus(self.respiration_roi_frame_box, frame.shape, "respiration_roi")

        movement_ratio = self._calculate_motion_ratio(motion_mask)
        if self.region_tracker and self.region_tracker.state == 'moving':
            # The moving crop stabilizes the body in pixel space; retain its
            # translation as activity so walking cannot look like resting.
            movement_ratio = max(movement_ratio, self.region_tracker.motion_activity, 2.0)
        manual_vitals_allowed = bool(self.vitals and manual_respiration_box is not None)
        tracking_vitals_allowed = self._vitals_measurement_allowed(tracked_subject_box, now)
        vitals_allowed = False  # Physiological sampling replaced by camera observations.
        vital_signal_box = manual_respiration_box if manual_vitals_allowed else tracked_subject_box
        self.vitals_focus_source = "respiration_roi" if manual_vitals_allowed else (
            "tracked_subject" if tracking_vitals_allowed else "none"
        )
        vital_signal = (
            self._calculate_vital_signal(frame_delta, vital_signal_box)
            if vitals_allowed
            else 0.0
        )

        # Temporal smoothing: 3-frame moving average
        self.activity_history.append(movement_ratio)
        smoothed = sum(self.activity_history) / len(self.activity_history)

        # Update status based on smoothed movement
        self.activity_level = smoothed
        self.respiration_signal_level = vital_signal
        self.status = "HAREKETLI" if smoothed > 1.0 else "DURGUN"
        if self.region_tracker and self.region_tracker.state == 'lost':
            self.status = 'TRACKING_LOST'
            # Loss of an anatomical lock invalidates respiration, not observed
            # motion. Keep coarse activity for life-cycle logs at the idle rate;
            # absence of a subject lock prevents resting/feeding claims.
            self.subject_tracking_state = 'lost'
            self.subject_tracking_confidence = 0.0

        if self.vitals and vitals_allowed:
            self.vitals.add_sample(self.respiration_signal_level)
            if self.camera_type == 'ip' and (self.target_fps < 3.0 or self._effective_analysis_fps() < 3.0):
                # Low-rate lifecycle probing must never masquerade as respiration.
                self.vitals.reset()
                if self._surface_respiration:self._surface_respiration.reset()
                self.latest_vitals = {"status": "LOW_SAMPLE_RATE", "respiration_bpm": None,
                                      "confidence": 0.0, "method": "activity_peaks"}
            elif getattr(self.region_tracker, 'respiration_source', None) == 'surface':
                self.vitals_focus_source='auto_surface'
                if self._surface_respiration is None:
                    self._surface_respiration = RespirationSurface(cv2,np)
                self._surface_respiration.add(frame, self.region_tracker.boxes['respiration'],
                                              self.region_tracker.boxes['animal'], time.monotonic())
                if now-self._last_estimate_ts>=1.0:
                    self.latest_vitals=self._decorate_vitals(self._surface_respiration.estimate(),
                                                            'auto_surface',respiration_roi_box=self.respiration_roi_frame_box)
                    self._last_estimate_ts=now
            elif now - self._last_estimate_ts >= 1.0:
                self.latest_vitals = self._decorate_vitals(
                    self.vitals.get_estimate(),
                    self.vitals_focus_source,
                    respiration_roi_box=self.respiration_roi_frame_box if manual_vitals_allowed else None,
                )
                self._last_estimate_ts = now
            self.last_vitals_sample_ts = now
        elif self.vitals:
            self.respiration_signal_level = 0.0
            if not self._region_vitals_allowed() or not self._should_preserve_vitals_window(tracked_subject_box, now):
                reason = ('tracking_' + self.region_tracker.state) if self.region_tracker else (
                    "respiration_roi_invalid" if self.respiration_roi_enabled else "no_subject")
                self._clear_vitals_measurement(reason=reason)
        else:
            self.latest_vitals = {"status": "UNAVAILABLE"}

        observation_box = self._serialize_subject_box()
        box = None
        if observation_box:
            box = tuple(observation_box[k] for k in ('x_norm', 'y_norm', 'width_norm', 'height_norm'))
        # Use the actual animal region rather than the respiration/focus crop.
        animal = self._tracked_regions.get('animal') if self.region_tracker else None
        if animal:
            box = tuple(animal[k] for k in ('x', 'y', 'width', 'height'))
        quality_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.observation.update(
            now=now, activity=smoothed, brightness=float(quality_gray.mean()),
            sharpness=float(cv2.Laplacian(quality_gray, cv2.CV_64F).var()),
            box=box, confidence=float(self.subject_tracking_confidence),
            tracking=self.subject_tracking_state == 'locked',
            frame_aspect=frame.shape[1] / frame.shape[0])

        self._update_load_profile(self.latest_vitals)

        self.last_frame = gray

        # Preview refresh is independent of analysis sampling.
        if self.camera_type == 'ip' and time.monotonic() - self._last_preview_ts < 1.0:
            return
        self._last_preview_ts = time.monotonic()
        self._publish_preview(preview_frame, safe_focus_box)
