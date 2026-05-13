import logging
import os
import threading
import time
import re
from collections import deque
from datetime import datetime, timezone
import statistics
from .vision import VisionEngine
from .analytics import AnalyticsEngine

logger = logging.getLogger(__name__)
DEGRADED_VITAL_STATUSES = {"LOW_CONF", "NOT_ENOUGH_DATA", "UNAVAILABLE", "TOO_MUCH_MOTION"}
ANALYSIS_DEGRADED_CLEAR_DELAY_SECONDS = 20.0
MEANINGFUL_VITAL_CONFIDENCE_MIN = 0.65
STABLE_VITAL_REPORT_COOLDOWN_SECONDS = 60.0
STABLE_VITAL_TREND_SAMPLE_INTERVAL_SECONDS = 10.0
STABLE_VITAL_TREND_HISTORY_SECONDS = 180.0
STABLE_VITAL_TREND_BASELINE_SAMPLES = 2
STABLE_VITAL_TREND_RECENT_SAMPLES = 2
LIFECYCLE_STOPPED = "STOPPED"
LIFECYCLE_STARTING = "STARTING"
LIFECYCLE_RUNNING = "RUNNING"
LIFECYCLE_STOPPING = "STOPPING"
LIFECYCLE_FAILED = "FAILED"


def _env_int(name, default, minimum=None, maximum=None):
    try:
        value = int(os.getenv(name, default))
    except (TypeError, ValueError):
        logger.warning("Invalid %s value; using default %s", name, default)
        value = int(default)
    if minimum is not None:
        value = max(int(minimum), value)
    if maximum is not None:
        value = min(int(maximum), value)
    return value


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


def _vision_runtime_config():
    width = _env_int("KUVOZ_AI_WIDTH", 320, minimum=160, maximum=640)
    height = _env_int("KUVOZ_AI_HEIGHT", 240, minimum=120, maximum=480)
    fps = _env_float("KUVOZ_AI_FPS", 1.0, minimum=0.25, maximum=5.0)
    return (width, height), fps


class AIManager:
    def __init__(self):
        resolution, fps = _vision_runtime_config()
        self.vision = VisionEngine(resolution=resolution, fps=fps)
        self.analytics = AnalyticsEngine()
        self.running = False
        self.started = False  # Track if AI has been started
        self.thread = None
        self.lifecycle_state = LIFECYCLE_STOPPED
        self._state_lock = threading.RLock()
        self._run_token = 0
        self._stop_event = threading.Event()
        self.vital_change_reports = deque(maxlen=30)
        self.last_vitals_snapshot = None
        self.stable_vital_history = deque(maxlen=24)
        self.last_vital_report_ts = 0.0
        self.last_vital_report_ts_by_kind = {}
        self.last_vital_report_signature = None
        self.last_analysis_log_signature = None
        self.last_analysis_degraded_ts = 0.0
        self.last_vital_analysis = {
            "stress_increase_detected": False,
            "indicators": [],
            "changes": [],
            "timestamp": 0.0,
        }
        self.patient_context = {}
        self.last_start_ts = 0.0
        self.last_stop_ts = 0.0
        self.last_loop_started_ts = 0.0
        self.last_loop_completed_ts = 0.0
        self.last_frame_ts = 0.0
        self.last_error = None
        self.last_error_ts = 0.0

    def _legacy_start(self):
        if self.started:
            logger.warning("AI Manager already started, skipping")
            return True
        
        self.running = True
        self.last_analysis_log_signature = None
        # Start vision engine
        vision_started = self.vision.start()
        if vision_started:
            # Start a background thread to process frames periodically
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()
            self.started = True
            logger.info("✅ AI Manager started with camera")
            return True
        else:
            logger.error("❌ AI Manager failed to start - Camera not available")
            self.running = False
            return False

    def _legacy_stop(self):
        if not self.started:
            logger.warning("AI Manager not started, skipping stop")
            return
        
        self.running = False
        self.started = False
        self.vision.stop()
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
        logger.info("✅ AI Manager stopped.")

    def _legacy_loop(self):
        while self.running:
            self.vision.process_frame()
            # Sleep to maintain target FPS (approximate)
            time.sleep(1.0 / self.vision.target_fps)

    def update_sensors(self, sensor_data, actuator_state):
        """
        Feed new sensor data to analytics engine.
        sensor_data: dict {'temperature': 25.0, ...}
        actuator_state: dict {'heater_on': True, ...}
        """
        if 'temperature' in sensor_data:
            self.analytics.add_reading('temperature', sensor_data['temperature'])
        if 'humidity' in sensor_data:
            self.analytics.add_reading('humidity', sensor_data['humidity'])
        if 'oxygen' in sensor_data:
            self.analytics.add_reading('oxygen', sensor_data['oxygen'])

        # Run analysis
        self.analytics.analyze(actuator_state)

    def clear_sensor_history(self, sensor_type):
        self.analytics.clear_history(sensor_type)
        self.last_analysis_log_signature = None

    def get_update(self):
        """
        Get combined status for frontend.
        """
        vision_status = self.vision.get_status()
        analytics_status = self.analytics.get_status()
        vitals = self.vision.get_vitals()

        self._track_vital_changes(vision_status, vitals)
        self._log_analysis_state_if_changed(analytics_status, vitals)

        return {
            "vision": vision_status,
            "analytics": analytics_status,
            "vitals": vitals,
            "vital_reports": list(self.vital_change_reports),
            "frame": self.vision.get_frame(), # Base64 encoded JPEG
            "lifecycle": self.get_lifecycle_status(),
        }

    def set_patient_context(self, patient_context):
        if not isinstance(patient_context, dict):
            return
        self.patient_context = {
            "species": str(patient_context.get("species") or "").strip(),
            "breed": str(patient_context.get("breed") or "").strip(),
            "age": str(patient_context.get("age") or "").strip(),
            "weight": patient_context.get("weight"),
        }

    def set_system_settings(self, system_settings):
        if hasattr(self.vision, "set_system_settings"):
            self.vision.set_system_settings(system_settings if isinstance(system_settings, dict) else {})

    def start(self):
        with self._state_lock:
            if self.lifecycle_state in (LIFECYCLE_RUNNING, LIFECYCLE_STARTING):
                logger.warning("AI Manager already started, skipping")
                return True
            thread_to_join = self.thread if self.lifecycle_state == LIFECYCLE_STOPPING else None

        if thread_to_join:
            thread_to_join.join(timeout=2.0)

        with self._state_lock:
            if self.thread and self.thread.is_alive():
                logger.warning("AI Manager is still stopping, start request rejected")
                return False

            self._prepare_for_start_locked()
            self.lifecycle_state = LIFECYCLE_STARTING
            self._run_token += 1
            run_token = self._run_token
            stop_event = threading.Event()
            self._stop_event = stop_event

        vision_started = False
        try:
            vision_started = self.vision.start()
            if not vision_started:
                self._mark_start_failed("camera_not_available")
                logger.error("AI Manager failed to start - Camera not available")
                return False

            worker = threading.Thread(
                target=self._loop,
                args=(run_token, stop_event),
                daemon=True,
                name=f"AIManagerLoop-{run_token}",
            )

            with self._state_lock:
                self.thread = worker
                self.running = True
                self.started = True
                self.lifecycle_state = LIFECYCLE_RUNNING
                self.last_start_ts = time.time()

            worker.start()
            logger.info("AI Manager started with camera")
            return True
        except Exception as exc:
            if vision_started:
                try:
                    self.vision.stop()
                except Exception:
                    logger.debug("Vision stop failed during AI manager start rollback", exc_info=True)
            self._mark_start_failed(str(exc))
            logger.error("AI Manager failed to start: %s", exc, exc_info=True)
            return False

    def stop(self):
        with self._state_lock:
            if self.lifecycle_state == LIFECYCLE_STOPPED and not self.thread:
                logger.warning("AI Manager not started, skipping stop")
                return

            self.lifecycle_state = LIFECYCLE_STOPPING
            self.running = False
            self.started = False
            stop_event = self._stop_event
            thread_to_join = self.thread
            run_token = self._run_token

        stop_event.set()

        try:
            self.vision.stop()
        except Exception:
            logger.error("Vision Engine stop failed during AI Manager stop", exc_info=True)

        if thread_to_join and thread_to_join is not threading.current_thread():
            thread_to_join.join(timeout=2.0)

        with self._state_lock:
            if run_token != self._run_token:
                return
            if self.thread is thread_to_join:
                self.thread = None
            self.last_stop_ts = time.time()
            self._reset_runtime_state_locked()
            self.lifecycle_state = LIFECYCLE_STOPPED
            self._stop_event = threading.Event()

        logger.info("AI Manager stopped.")

    def _loop(self, run_token, stop_event):
        current_thread = threading.current_thread()
        try:
            while not stop_event.is_set():
                with self._state_lock:
                    if run_token != self._run_token:
                        break
                    self.last_loop_started_ts = time.time()

                try:
                    self.vision.process_frame()
                except Exception as exc:
                    with self._state_lock:
                        if run_token != self._run_token:
                            break
                        self.running = False
                        self.started = False
                        self.lifecycle_state = LIFECYCLE_FAILED
                        self.last_error = str(exc)
                        self.last_error_ts = time.time()
                    stop_event.set()
                    try:
                        self.vision.stop()
                    except Exception:
                        logger.debug("Vision stop failed after loop exception", exc_info=True)
                    logger.error("AI Manager loop failed: %s", exc, exc_info=True)
                    break

                completed_at = time.time()
                with self._state_lock:
                    if run_token != self._run_token:
                        break
                    self.last_loop_completed_ts = completed_at
                    if self.vision.get_frame() is not None:
                        self.last_frame_ts = completed_at

                target_fps = max(float(getattr(self.vision, "target_fps", 1.0) or 1.0), 0.25)
                time.sleep(1.0 / target_fps)
        finally:
            with self._state_lock:
                if self.thread is current_thread:
                    self.thread = None
                if run_token == self._run_token and self.lifecycle_state != LIFECYCLE_STOPPING:
                    self.running = False
                    self.started = False
                    if self.lifecycle_state != LIFECYCLE_FAILED:
                        self.lifecycle_state = LIFECYCLE_STOPPED
                        self.last_stop_ts = time.time()

    def get_lifecycle_status(self):
        with self._state_lock:
            thread_alive = bool(self.thread and self.thread.is_alive())
            return {
                "state": self.lifecycle_state,
                "running": self.running,
                "started": self.started,
                "thread_alive": thread_alive,
                "run_token": self._run_token,
                "last_start_ts": self.last_start_ts,
                "last_stop_ts": self.last_stop_ts,
                "last_loop_started_ts": self.last_loop_started_ts,
                "last_loop_completed_ts": self.last_loop_completed_ts,
                "last_frame_ts": self.last_frame_ts,
                "last_error": self.last_error,
                "last_error_ts": self.last_error_ts,
            }

    def _prepare_for_start_locked(self):
        self.running = False
        self.started = False
        self.thread = None
        self.last_start_ts = 0.0
        self.last_stop_ts = 0.0
        self.last_loop_started_ts = 0.0
        self.last_loop_completed_ts = 0.0
        self.last_frame_ts = 0.0
        self.last_error = None
        self.last_error_ts = 0.0
        self._reset_runtime_state_locked()

    def _mark_start_failed(self, error_message):
        with self._state_lock:
            self.running = False
            self.started = False
            self.thread = None
            self.lifecycle_state = LIFECYCLE_FAILED
            self.last_error = str(error_message)
            self.last_error_ts = time.time()

    def _reset_runtime_state_locked(self):
        self.last_vitals_snapshot = None
        self.stable_vital_history.clear()
        self.last_vital_report_ts = 0.0
        self.last_vital_report_ts_by_kind = {}
        self.last_vital_report_signature = None
        self.last_analysis_log_signature = None
        self.last_analysis_degraded_ts = 0.0
        self.last_vital_analysis = {
            "stress_increase_detected": False,
            "indicators": [],
            "changes": [],
            "timestamp": 0.0,
        }
        self.vital_change_reports.clear()
        self._clear_vision_runtime_state()

    def _clear_vision_runtime_state(self):
        if hasattr(self.vision, "camera"):
            self.vision.camera = None
        if hasattr(self.vision, "camera_type"):
            self.vision.camera_type = None
        if hasattr(self.vision, "last_frame"):
            self.vision.last_frame = None
        if hasattr(self.vision, "latest_jpeg"):
            self.vision.latest_jpeg = None
        if hasattr(self.vision, "status"):
            self.vision.status = "IDLE"
        if hasattr(self.vision, "activity_level"):
            self.vision.activity_level = 0.0
        if hasattr(self.vision, "respiration_signal_level"):
            self.vision.respiration_signal_level = 0.0
        if hasattr(self.vision, "vitals_focus_source"):
            self.vision.vitals_focus_source = "none"
        if hasattr(self.vision, "respiration_roi_frame_box"):
            self.vision.respiration_roi_frame_box = None
        if hasattr(self.vision, "activity_history") and hasattr(self.vision.activity_history, "clear"):
            self.vision.activity_history.clear()
        if hasattr(self.vision, "no_subject_since_ts"):
            self.vision.no_subject_since_ts = None
        if hasattr(self.vision, "high_motion_since_ts"):
            self.vision.high_motion_since_ts = None
        if hasattr(self.vision, "last_subject_seen_ts"):
            self.vision.last_subject_seen_ts = None
        if hasattr(self.vision, "load_profile"):
            self.vision.load_profile = "normal"
        if hasattr(self.vision, "load_reason"):
            self.vision.load_reason = "startup"
        if hasattr(self.vision, "safe_focus_box"):
            self.vision.safe_focus_box = None
        if hasattr(self.vision, "analysis_focus_box"):
            self.vision.analysis_focus_box = None
        if hasattr(self.vision, "analysis_focus_source"):
            self.vision.analysis_focus_source = "pending"
        if hasattr(self.vision, "analysis_focus_coverage"):
            self.vision.analysis_focus_coverage = 1.0
        if hasattr(self.vision, "analysis_started_ts"):
            self.vision.analysis_started_ts = None
        if hasattr(self.vision, "analysis_observation_until_ts"):
            self.vision.analysis_observation_until_ts = None
        if hasattr(self.vision, "subject_box"):
            self.vision.subject_box = None
        if hasattr(self.vision, "subject_tracking_state"):
            self.vision.subject_tracking_state = "searching"
        if hasattr(self.vision, "subject_tracking_confidence"):
            self.vision.subject_tracking_confidence = 0.0
        if hasattr(self.vision, "subject_box_updated_ts"):
            self.vision.subject_box_updated_ts = None
        if hasattr(self.vision, "latest_vitals"):
            unavailable_status = "UNAVAILABLE"
            if getattr(self.vision, "vitals", None) is not None:
                unavailable_status = "NOT_ENOUGH_DATA"
            self.vision.latest_vitals = {"status": unavailable_status}

    def _track_vital_changes(self, vision_status, vitals):
        if not isinstance(vitals, dict):
            self.last_vital_analysis = {
                "stress_increase_detected": False,
                "indicators": [],
                "changes": [],
                "timestamp": 0.0,
            }
            return

        now = time.time()
        current_snapshot = {
            "status": str(vitals.get("status") or ""),
            "respiration_bpm": self._to_float(vitals.get("respiration_bpm")),
            "confidence": self._to_float(vitals.get("confidence")),
        }

        previous = self.last_vitals_snapshot
        self.last_vitals_snapshot = current_snapshot

        self._prune_stable_vital_history(now)

        if not previous:
            self._seed_stable_vital_history(current_snapshot, now)
            self.last_vital_analysis = {
                "stress_increase_detected": False,
                "indicators": [],
                "changes": [],
                "timestamp": now,
            }
            return

        if not self._animal_detected(vision_status, current_snapshot):
            self.last_vital_analysis = {
                "stress_increase_detected": False,
                "indicators": [],
                "changes": [],
                "timestamp": now,
            }
            return

        thresholds = self._get_dynamic_thresholds()
        changes = []
        stress_indicators = []
        previous_bucket = self._get_vital_state_bucket(previous)
        current_bucket = self._get_vital_state_bucket(current_snapshot)

        self._seed_stable_vital_history(previous, now - STABLE_VITAL_TREND_SAMPLE_INTERVAL_SECONDS)
        self._record_stable_vital_snapshot(current_snapshot, now)
        trend = self._get_stable_vital_trend()

        if previous_bucket != current_bucket:
            if current_bucket == "degraded":
                changes.append(f"takip guvenilmez: {current_snapshot['status'] or 'UNKNOWN'}")
                stress_indicators.append("tracking_degraded")
            elif previous_bucket == "degraded" and current_bucket == "stable":
                changes.append("takip yeniden guvenilir")

        prev_bpm = previous["respiration_bpm"]
        curr_bpm = current_snapshot["respiration_bpm"]
        if (
            previous_bucket == "stable"
            and current_bucket == "stable"
            and prev_bpm is not None
            and curr_bpm is not None
            and trend
        ):
            bpm_delta = trend["recent_bpm"] - trend["baseline_bpm"]
            if bpm_delta >= thresholds["bpm_delta"]:
                changes.append(
                    "solunum trendi "
                    f"{trend['baseline_bpm']:.1f} -> {trend['recent_bpm']:.1f} BPM"
                )
                stress_indicators.append("respiration_increase")

        prev_conf = previous["confidence"]
        curr_conf = current_snapshot["confidence"]
        if (
            previous_bucket == "stable"
            and current_bucket == "stable"
            and prev_conf is not None
            and curr_conf is not None
            and trend
        ):
            conf_delta = trend["recent_confidence"] - trend["baseline_confidence"]
            if conf_delta <= (-1 * thresholds["confidence_delta"]):
                changes.append(
                    "guven trendi "
                    f"{trend['baseline_confidence']:.2f} -> {trend['recent_confidence']:.2f}"
                )
                stress_indicators.append("confidence_drop")

        self.last_vital_analysis = {
            "stress_increase_detected": bool(stress_indicators),
            "indicators": stress_indicators,
            "changes": changes,
            "timestamp": now,
        }

        if not changes:
            return

        report_kind = self._select_vital_report_kind(previous_bucket, current_bucket, stress_indicators)
        if report_kind is None:
            return

        report_cooldown = thresholds["cooldown_seconds"]
        if report_kind == "stress_increase":
            report_cooldown = max(report_cooldown, STABLE_VITAL_REPORT_COOLDOWN_SECONDS)

        last_kind_ts = self.last_vital_report_ts_by_kind.get(report_kind, 0.0)
        if last_kind_ts and now - last_kind_ts < report_cooldown:
            return

        report_signature = (report_kind, tuple(changes), tuple(stress_indicators))
        duplicate_window = max(report_cooldown * 2, 30.0)
        if (
            report_signature == self.last_vital_report_signature
            and now - self.last_vital_report_ts < duplicate_window
        ):
            return

        self.last_vital_report_ts = now
        self.last_vital_report_ts_by_kind[report_kind] = now
        self.last_vital_report_signature = report_signature
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "VITAL degisimi: " + ", ".join(changes),
            "severity": "warning" if report_kind != "tracking_recovered" else "info",
            "kind": report_kind,
        }
        self.vital_change_reports.append(report)
        if report["severity"] == "warning":
            logger.info(f"🫀 {report['message']} @ {report['timestamp']}")

    def _log_analysis_state_if_changed(self, analytics_status, vitals):
        """
        Analiz durumu değişimlerini logla.
        Sadece ÖNEMLİ değişiklikleri logla: yeni anomali, kritik vital durum
        """
        anomalies = tuple(dict.fromkeys((analytics_status or {}).get("anomalies") or []))
        significant_vital_state = self._get_analysis_vital_state(vitals)
        signature = (anomalies, significant_vital_state)
        is_normal = self._is_normal_analysis_signature(signature)

        if self.last_analysis_log_signature is None:
            self.last_analysis_log_signature = signature
            if not is_normal:
                logger.info(
                    "AI analiz degisimi: %s",
                    self._format_analysis_signature(signature, vitals),
                )
            return

        if signature == self.last_analysis_log_signature:
            return

        previous_signature = self.last_analysis_log_signature
        self.last_analysis_log_signature = signature
        previous_is_normal = self._is_normal_analysis_signature(previous_signature)

        if is_normal:
            if not previous_is_normal:
                logger.info("AI analiz normale dondu")
            return

        prev_anomalies, prev_vital = previous_signature
        if (
            previous_is_normal
            or anomalies != prev_anomalies
            or significant_vital_state != prev_vital
        ):
            logger.info(
                "AI analiz degisimi: %s",
                self._format_analysis_signature(signature, vitals),
            )

    def _is_normal_analysis_signature(self, signature):
        anomalies, significant_vital_state = signature
        return not anomalies and not significant_vital_state

    def _format_analysis_signature(self, signature, vitals):
        anomalies, significant_vital_state = signature
        details = []

        if anomalies:
            details.append(f"anomali={len(anomalies)}")

        if significant_vital_state:
            status = str((vitals or {}).get("status") or "").strip().upper()
            if status in DEGRADED_VITAL_STATUSES:
                details.append(f"vital_izleme=DEGRADED({status})")
            else:
                details.append(f"vital_izleme={significant_vital_state}")

        return ", ".join(details) if details else "normal"

    def _get_vital_state_bucket(self, vitals_snapshot):
        status = str((vitals_snapshot or {}).get("status") or "").strip().upper()
        respiration = self._to_float((vitals_snapshot or {}).get("respiration_bpm"))
        confidence = self._to_float((vitals_snapshot or {}).get("confidence"))

        if status in DEGRADED_VITAL_STATUSES:
            return "degraded"
        if status == "OK" and respiration is not None and (confidence or 0.0) >= MEANINGFUL_VITAL_CONFIDENCE_MIN:
            return "stable"
        return "other"

    def _select_vital_report_kind(self, previous_bucket, current_bucket, stress_indicators):
        if current_bucket == "degraded" and previous_bucket != "degraded":
            return "tracking_degraded"
        if stress_indicators:
            return "stress_increase"
        if previous_bucket == "degraded" and current_bucket == "stable":
            return "tracking_recovered"
        return None

    def _get_analysis_vital_state(self, vitals):
        status = str((vitals or {}).get("status") or "").strip().upper()
        now = time.time()

        if status in DEGRADED_VITAL_STATUSES:
            self.last_analysis_degraded_ts = now
            return "DEGRADED"

        if (
            self.last_analysis_degraded_ts
            and now - self.last_analysis_degraded_ts < ANALYSIS_DEGRADED_CLEAR_DELAY_SECONDS
        ):
            return "DEGRADED"

        return ""

    def _animal_detected(self, vision_status, vitals_snapshot):
        try:
            status = (vision_status or {}).get("status")
            activity = float((vision_status or {}).get("activity") or 0.0)
        except (TypeError, ValueError):
            status = None
            activity = 0.0

        # Current project has no direct animal classifier; infer presence from
        # sustained motion or reliable respiration estimation.
        if status == "HAREKETLI" or activity >= 0.5:
            return True

        if (
            vitals_snapshot.get("status") == "OK"
            and vitals_snapshot.get("respiration_bpm") is not None
            and (vitals_snapshot.get("confidence") or 0.0) >= 0.5
        ):
            return True

        return False

    def _is_stable_vital_snapshot(self, vitals_snapshot):
        return self._get_vital_state_bucket(vitals_snapshot) == "stable"

    def _prune_stable_vital_history(self, now):
        cutoff = float(now) - STABLE_VITAL_TREND_HISTORY_SECONDS
        while self.stable_vital_history and self.stable_vital_history[0]["timestamp"] < cutoff:
            self.stable_vital_history.popleft()

    def _seed_stable_vital_history(self, vitals_snapshot, timestamp):
        if self.stable_vital_history or not self._is_stable_vital_snapshot(vitals_snapshot):
            return

        self.stable_vital_history.append(
            {
                "timestamp": float(timestamp),
                "respiration_bpm": float(vitals_snapshot["respiration_bpm"]),
                "confidence": float(vitals_snapshot["confidence"]),
            }
        )

    def _record_stable_vital_snapshot(self, vitals_snapshot, now):
        if not self._is_stable_vital_snapshot(vitals_snapshot):
            return

        entry = {
            "timestamp": float(now),
            "respiration_bpm": float(vitals_snapshot["respiration_bpm"]),
            "confidence": float(vitals_snapshot["confidence"]),
        }

        if self.stable_vital_history:
            last_entry = self.stable_vital_history[-1]
            elapsed = entry["timestamp"] - last_entry["timestamp"]
            if elapsed < STABLE_VITAL_TREND_SAMPLE_INTERVAL_SECONDS:
                self.stable_vital_history[-1] = entry
                return

        self.stable_vital_history.append(entry)

    def _get_stable_vital_trend(self):
        required_samples = (
            STABLE_VITAL_TREND_BASELINE_SAMPLES
            + STABLE_VITAL_TREND_RECENT_SAMPLES
        )
        if len(self.stable_vital_history) < required_samples:
            return None

        history = list(self.stable_vital_history)
        recent_entries = history[-STABLE_VITAL_TREND_RECENT_SAMPLES:]
        baseline_entries = history[
            -(required_samples): -STABLE_VITAL_TREND_RECENT_SAMPLES
        ]

        baseline_bpm = statistics.median(
            entry["respiration_bpm"] for entry in baseline_entries
        )
        recent_bpm = statistics.median(
            entry["respiration_bpm"] for entry in recent_entries
        )
        baseline_confidence = statistics.median(
            entry["confidence"] for entry in baseline_entries
        )
        recent_confidence = statistics.median(
            entry["confidence"] for entry in recent_entries
        )

        latest_entry = recent_entries[-1]
        # Keep the trend anchored to the latest stable snapshot so a single
        # transient sample cannot keep the aggregated median elevated.
        if latest_entry["respiration_bpm"] < (baseline_bpm + 0.01):
            recent_bpm = min(recent_bpm, latest_entry["respiration_bpm"])
        if latest_entry["confidence"] > (baseline_confidence - 0.01):
            recent_confidence = max(recent_confidence, latest_entry["confidence"])

        return {
            "baseline_bpm": float(baseline_bpm),
            "recent_bpm": float(recent_bpm),
            "baseline_confidence": float(baseline_confidence),
            "recent_confidence": float(recent_confidence),
        }

    def _to_float(self, value):
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _get_dynamic_thresholds(self):
        # Defaults tuned for current estimator behavior.
        thresholds = {
            "bpm_delta": 4.0,
            "confidence_delta": 0.20,
            "cooldown_seconds": 8.0,
        }

        species = str(self.patient_context.get("species") or "").strip().lower()
        breed = str(self.patient_context.get("breed") or "").strip().lower()
        weight_kg = self._parse_weight_kg(self.patient_context.get("weight"))
        age_years = self._parse_age_years(self.patient_context.get("age"))

        if "kedi" in species or "cat" in species:
            thresholds["bpm_delta"] = 3.0
            thresholds["confidence_delta"] = 0.18
        elif "köpek" in species or "kopek" in species or "dog" in species:
            thresholds["bpm_delta"] = 4.0
            thresholds["confidence_delta"] = 0.20
            if weight_kg is not None:
                if weight_kg <= 10:
                    thresholds["bpm_delta"] = 3.5
                elif weight_kg >= 30:
                    thresholds["bpm_delta"] = 5.0
        elif any(token in species for token in ("kuş", "kus", "bird", "tavşan", "tavsan", "rabbit", "kemirgen", "rodent")):
            thresholds["bpm_delta"] = 2.5
            thresholds["confidence_delta"] = 0.15

        brachycephalic_tokens = (
            "pug", "bulldog", "french bulldog", "boxer", "pekingese", "shih tzu",
            "persian", "british shorthair", "scottish fold"
        )
        if any(token in breed for token in brachycephalic_tokens):
            thresholds["bpm_delta"] = min(thresholds["bpm_delta"], 3.0)
            thresholds["confidence_delta"] = min(thresholds["confidence_delta"], 0.18)

        if age_years is not None:
            if age_years < 1.0:
                thresholds["bpm_delta"] = max(2.0, thresholds["bpm_delta"] - 0.5)
            elif age_years >= 8.0:
                thresholds["bpm_delta"] = min(6.0, thresholds["bpm_delta"] + 0.5)

        return thresholds

    def _parse_weight_kg(self, raw):
        if raw is None:
            return None
        try:
            text = str(raw).strip().replace(",", ".")
            if not text:
                return None
            value = float(text)
            if value <= 0:
                return None
            return value
        except (TypeError, ValueError):
            return None

    def _parse_age_years(self, raw):
        if raw is None:
            return None
        text = str(raw).lower().strip()
        if not text:
            return None

        # Examples: "2 yıl 3 ay", "4 years", "8 months"
        years = 0.0
        months = 0.0

        year_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(y[iı]l|year|years|yr)", text)
        if year_match:
            years = float(year_match.group(1).replace(",", "."))

        month_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(ay|month|months|mo)", text)
        if month_match:
            months = float(month_match.group(1).replace(",", "."))

        if years == 0.0 and months == 0.0:
            try:
                # If only numeric age was entered, interpret as years.
                years = float(text.replace(",", "."))
            except ValueError:
                return None

        return years + (months / 12.0)
