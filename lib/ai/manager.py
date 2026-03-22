import logging
import threading
import time
import re
from collections import deque
from datetime import datetime, timezone
from .vision import VisionEngine
from .analytics import AnalyticsEngine

logger = logging.getLogger(__name__)
DEGRADED_VITAL_STATUSES = {"LOW_CONF", "NOT_ENOUGH_DATA", "UNAVAILABLE", "TOO_MUCH_MOTION"}
ANALYSIS_DEGRADED_CLEAR_DELAY_SECONDS = 20.0
MEANINGFUL_VITAL_CONFIDENCE_MIN = 0.65
STABLE_VITAL_REPORT_COOLDOWN_SECONDS = 60.0

class AIManager:
    def __init__(self):
        self.vision = VisionEngine()
        self.analytics = AnalyticsEngine()
        self.running = False
        self.started = False  # Track if AI has been started
        self.thread = None
        self.vital_change_reports = deque(maxlen=30)
        self.last_vitals_snapshot = None
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

    def start(self):
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

    def stop(self):
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

    def _loop(self):
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
            "frame": self.vision.get_frame() # Base64 encoded JPEG
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

        if not previous:
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

        if previous_bucket != current_bucket:
            if current_bucket == "degraded":
                changes.append(f"takip guvenilmez: {current_snapshot['status'] or 'UNKNOWN'}")
                stress_indicators.append("tracking_degraded")
            elif previous_bucket == "degraded" and current_bucket == "stable":
                changes.append("takip yeniden guvenilir")

        prev_bpm = previous["respiration_bpm"]
        curr_bpm = current_snapshot["respiration_bpm"]
        if previous_bucket == "stable" and current_bucket == "stable" and prev_bpm is not None and curr_bpm is not None:
            bpm_delta = curr_bpm - prev_bpm
            if bpm_delta >= thresholds["bpm_delta"]:
                changes.append(f"solunum {prev_bpm:.1f} -> {curr_bpm:.1f} BPM")
                stress_indicators.append("respiration_increase")

        prev_conf = previous["confidence"]
        curr_conf = current_snapshot["confidence"]
        if previous_bucket == "stable" and current_bucket == "stable" and prev_conf is not None and curr_conf is not None:
            conf_delta = curr_conf - prev_conf
            if conf_delta <= (-1 * thresholds["confidence_delta"]):
                changes.append(f"guven {prev_conf:.2f} -> {curr_conf:.2f}")
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
        anomalies = tuple(dict.fromkeys((analytics_status or {}).get("anomalies") or []))
        significant_vital_state = self._get_analysis_vital_state(vitals)
        signature = (anomalies, significant_vital_state)

        if self.last_analysis_log_signature is None:
            self.last_analysis_log_signature = signature
            if self._is_normal_analysis_signature(signature):
                return
            self._emit_analysis_log(signature, vitals=vitals)
            return

        if signature == self.last_analysis_log_signature:
            return

        previous_signature = self.last_analysis_log_signature
        self.last_analysis_log_signature = signature

        if self._is_normal_analysis_signature(signature):
            if not self._is_normal_analysis_signature(previous_signature):
                logger.info("AI analiz normale dondu")
            return

        self._emit_analysis_log(signature, vitals=vitals)

    def _emit_analysis_log(self, signature, vitals=None):
        anomalies, significant_vital_state = signature
        parts = []

        if anomalies:
            parts.append(f"anomali={len(anomalies)}")
            parts.extend(anomalies)

        if significant_vital_state:
            detail = str((vitals or {}).get("status") or "").strip()
            if detail:
                parts.append(f"vital_izleme={significant_vital_state}({detail})")
            else:
                parts.append(f"vital_izleme={significant_vital_state}")

        logger.info("AI analiz degisimi: %s", " | ".join(parts))

    def _is_normal_analysis_signature(self, signature):
        anomalies, significant_vital_state = signature
        return not anomalies and not significant_vital_state

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
