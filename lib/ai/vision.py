import logging
import time
import threading
import base64
import os
from collections import deque

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


# Thermal throttling constants
THERMAL_THROTTLE_TEMP = 75.0   # °C - throttle FPS above this
THERMAL_RESTORE_TEMP  = 70.0   # °C - restore FPS below this
THERMAL_NORMAL_FPS    = 5       # FPS when cool
THERMAL_THROTTLED_FPS = 2       # FPS when hot

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

LOAD_PROFILE_SETTINGS = {
    "normal": {"fps": float(THERMAL_NORMAL_FPS), "jpeg_quality": 50},
    "idle": {"fps": 1.5, "jpeg_quality": 35},
    "motion_limited": {"fps": 2.0, "jpeg_quality": 40},
}


class VisionEngine:
    def __init__(self, resolution=(640, 480), fps=5):
        self.resolution = resolution
        self.base_fps = min(float(fps), float(THERMAL_NORMAL_FPS))
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
        self.latest_jpeg = None
        self.lock = threading.Lock()
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
        self.analysis_started_ts = None
        self.analysis_observation_until_ts = None
        self.subject_box = None
        self.subject_tracking_state = "searching"
        self.subject_tracking_confidence = 0.0
        self.subject_box_updated_ts = None

        self.vitals = VitalSignsEstimator() if VITALS_AVAILABLE else None

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
        temp = self._read_cpu_temp()
        if temp is None:
            return
        if not self._throttled and temp >= THERMAL_THROTTLE_TEMP:
            self.thermal_fps_cap = float(THERMAL_THROTTLED_FPS)
            self._throttled = True
            self._refresh_target_fps()
            logger.warning(f"🌡️  CPU temp {temp:.1f}°C ≥ {THERMAL_THROTTLE_TEMP}°C — throttled to {self.target_fps:.1f} FPS")
        elif self._throttled and temp < THERMAL_RESTORE_TEMP:
            self.thermal_fps_cap = float(THERMAL_NORMAL_FPS)
            self._throttled = False
            self._refresh_target_fps()
            logger.info(f"🌡️  CPU temp {temp:.1f}°C < {THERMAL_RESTORE_TEMP}°C — restored to {self.target_fps:.1f} FPS")

    def _refresh_target_fps(self):
        effective_fps = max(1.0, min(self.base_fps, self.profile_fps, self.thermal_fps_cap))
        if abs(effective_fps - self.target_fps) < 1e-6:
            return

        self.target_fps = effective_fps
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
        if self._tracking_lock_active():
            return True
        if self.status == "HAREKETLI" or self.activity_level >= ACTIVE_SUBJECT_ACTIVITY_THRESHOLD:
            return True
        return self._has_reliable_vitals(vitals)

    def _too_much_motion(self, vitals):
        if isinstance(vitals, dict) and vitals.get("status") == "TOO_MUCH_MOTION":
            return True
        return self.activity_level >= HIGH_MOTION_ACTIVITY_THRESHOLD

    def _set_load_profile(self, profile, reason):
        settings = LOAD_PROFILE_SETTINGS[profile]
        profile_changed = profile != self.load_profile

        self.load_profile = profile
        self.load_reason = reason
        self.profile_fps = min(self.base_fps, float(settings["fps"]))
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
            self.subject_box = selected_box
            self.subject_box_updated_ts = float(now)
            self.subject_tracking_state = "locked"
            self.subject_tracking_confidence = round(max(0.35, selected_score), 2)
            return self.subject_box

        if self.subject_box is not None and self.subject_box_updated_ts is not None:
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

        non_zero_pts = cv2.findNonZero(motion_mask)
        if non_zero_pts is None:
            return 0.0

        x, y, w, h = cv2.boundingRect(non_zero_pts)
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

    def _apply_analysis_focus(self, frame):
        if frame is None or getattr(frame, "size", 0) == 0:
            self.safe_focus_box = None
            self.analysis_focus_box = None
            self.analysis_focus_source = "unavailable"
            self.analysis_focus_coverage = 1.0
            return frame, None

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

    def _draw_analysis_focus_overlay(self, frame, focus_box, safe_focus_box=None):
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
        elif self.analysis_focus_source == "center_fallback":
            color = (243, 156, 18)
            label = "MERKEZ TARAMA"
        cv2.rectangle(frame, (x1, y1), (x2 - 1, y2 - 1), color, 2)

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

    def _update_load_profile(self, vitals=None, now=None):
        if now is None:
            now = time.time()
        self._ensure_observation_window(now)

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
        if not OPENCV_AVAILABLE:
            return False
        
        # Strategy 1: Try picamera2 (Raspberry Pi native, modern approach)
        if PICAMERA2_AVAILABLE:
            try:
                logger.info("Attempting to initialize camera with picamera2...")
                picam = Picamera2()
                
                # Configure camera: main stream for capture
                # Use a standard buffer count and explicit format
                config = picam.create_still_configuration(
                    main={"size": self.resolution, "format": "BGR888"},
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

    def stop(self):
        self.running = False
        if self.camera:
            if self.camera_type == 'picamera2':
                try:
                    self.camera.stop()
                    self.camera.close()
                except:
                    pass
            else:  # opencv
                self.camera.release()
        logger.info("Vision Engine stopped.")

    def get_frame(self):
        with self.lock:
            return self.latest_jpeg

    def get_status(self):
        temp = self._read_cpu_temp()
        return {
            "status": self.status,
            "activity": round(self.activity_level, 2),
            "respiration_signal": round(self.respiration_signal_level, 3),
            "available": OPENCV_AVAILABLE and self.running,
            "vitals_available": bool(self.vitals),
            "cpu_temp": round(temp, 1) if temp is not None else None,
            "throttled": self._throttled,
            "target_fps": round(self.target_fps, 2),
            "load_profile": self.load_profile,
            "load_reason": self.load_reason,
            "jpeg_quality": self.jpeg_quality,
            "analysis_focus_source": self.analysis_focus_source,
            "analysis_focus_coverage": round(self.analysis_focus_coverage, 3),
            "analysis_focus_box": self._serialize_focus_box(),
            "subject_tracking_state": self.subject_tracking_state,
            "subject_tracking_confidence": self.subject_tracking_confidence,
            "subject_tracking_locked": self._tracking_lock_active(),
            "startup_collection_active": bool(
                self.analysis_observation_until_ts
                and time.time() < self.analysis_observation_until_ts
            ),
        }

    def get_vitals(self):
        if not self.vitals:
            return {"status": "UNAVAILABLE"}
        return self.latest_vitals

    def process_frame(self):
        if not self.running or not self.camera:
            logger.debug("process_frame skipped: running={}, camera={}".format(self.running, self.camera is not None))
            return

        # Capture frame based on camera type
        try:
            if self.camera_type == 'picamera2':
                frame = self.camera.capture_array()
                if frame is None or frame.shape[0] == 0:
                    logger.warning("Failed to capture frame from picamera2")
                    return
            else:  # opencv
                ret, frame = self.camera.read()
                if not ret:
                    logger.warning("Failed to grab frame from OpenCV")
                    return
        except Exception as e:
            logger.error(f"Error capturing frame: {e}")
            return

        # Resize for consistent processing speed
        frame = cv2.resize(frame, self.resolution)
        
        # Fix Blue Tint: Swap channels (input seems to be RGB, we need BGR for imencode)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        analysis_frame, safe_focus_box = self._apply_analysis_focus(frame)

        # Convert to grayscale for motion detection inside the live-being focus window.
        gray = cv2.cvtColor(analysis_frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.last_frame is None:
            self.last_frame = gray
            logger.info("🎥 First frame captured and processed successfully")
            return

        # Thermal throttle check (every frame, lightweight)
        self._check_thermal_throttle()

        # Compute difference with lowered threshold for subtle breathing
        frame_delta = cv2.absdiff(self.last_frame, gray)
        thresh = cv2.threshold(frame_delta, 12, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        now = time.time()
        candidate_boxes = self._find_motion_candidate_boxes(thresh)
        tracked_subject_box = self._update_subject_tracking(candidate_boxes, gray.shape, now)
        if tracked_subject_box is not None:
            roi_x1, roi_y1, roi_x2, roi_y2 = tracked_subject_box
            motion_mask = thresh[roi_y1:roi_y2, roi_x1:roi_x2]
            frame_box = self._subject_box_to_frame_box(tracked_subject_box)
            focus_source = "tracked_subject_hold" if self.subject_tracking_state == "holding" else "tracked_subject"
            self._set_active_analysis_focus(frame_box, frame.shape, focus_source)
        else:
            motion_mask = thresh
            self._set_active_analysis_focus(safe_focus_box, frame.shape, "center_fallback")

        movement_ratio = self._calculate_motion_ratio(motion_mask)
        vital_signal = self._calculate_vital_signal(frame_delta, tracked_subject_box)

        # Temporal smoothing: 3-frame moving average
        self.activity_history.append(movement_ratio)
        smoothed = sum(self.activity_history) / len(self.activity_history)

        # Update status based on smoothed movement
        self.activity_level = smoothed
        self.respiration_signal_level = vital_signal
        self.status = "HAREKETLI" if smoothed > 1.0 else "DURGUN"

        if self.vitals:
            self.vitals.add_sample(self.respiration_signal_level)
            self.latest_vitals = self.vitals.get_estimate()
        else:
            self.latest_vitals = {"status": "UNAVAILABLE"}

        self._update_load_profile(self.latest_vitals)

        self.last_frame = gray

        # Encode frame for web streaming (low quality for speed)
        display_frame = frame.copy()
        self._draw_analysis_focus_overlay(display_frame, self.analysis_focus_box, safe_focus_box=safe_focus_box)
        _, buffer = cv2.imencode(
            '.jpg',
            display_frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality],
        )
        with self.lock:
            self.latest_jpeg = base64.b64encode(buffer).decode('utf-8')
