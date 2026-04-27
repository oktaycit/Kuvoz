from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


def _to_float(value: Any) -> Optional[float]:
    try:
        if value in (None, "", "--"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _clamp01(value: Any) -> float:
    numeric = _to_float(value) or 0.0
    return max(0.0, min(1.0, float(numeric)))


def _normalize_box(box: Any) -> Optional[Dict[str, float]]:
    if not isinstance(box, dict):
        return None

    x = box.get("x_norm", box.get("x"))
    y = box.get("y_norm", box.get("y"))
    width = box.get("width_norm", box.get("width"))
    height = box.get("height_norm", box.get("height"))

    x = _to_float(x)
    y = _to_float(y)
    width = _to_float(width)
    height = _to_float(height)
    if None in (x, y, width, height):
        return None

    x = _clamp01(x)
    y = _clamp01(y)
    width = max(0.0, min(float(width), 1.0 - x))
    height = max(0.0, min(float(height), 1.0 - y))
    if width <= 0.0 or height <= 0.0:
        return None

    return {
        "x": x,
        "y": y,
        "width": width,
        "height": height,
    }


def _intersection_area(box_a: Dict[str, float], box_b: Dict[str, float]) -> float:
    ax1 = box_a["x"]
    ay1 = box_a["y"]
    ax2 = ax1 + box_a["width"]
    ay2 = ay1 + box_a["height"]
    bx1 = box_b["x"]
    by1 = box_b["y"]
    bx2 = bx1 + box_b["width"]
    by2 = by1 + box_b["height"]
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_width = max(0.0, inter_x2 - inter_x1)
    inter_height = max(0.0, inter_y2 - inter_y1)
    return inter_width * inter_height


def _point_in_box(point: Optional[Dict[str, float]], box: Optional[Dict[str, float]]) -> bool:
    if not point or not box:
        return False

    return (
        box["x"] <= point["x"] <= (box["x"] + box["width"])
        and box["y"] <= point["y"] <= (box["y"] + box["height"])
    )


def _point_box_center_distance(
    point: Optional[Dict[str, float]],
    box: Optional[Dict[str, float]],
) -> Optional[float]:
    if not point or not box:
        return None

    box_center_x = box["x"] + (box["width"] * 0.5)
    box_center_y = box["y"] + (box["height"] * 0.5)
    return (((point["x"] - box_center_x) ** 2) + ((point["y"] - box_center_y) ** 2)) ** 0.5


def _subject_contact_point(
    subject_box: Optional[Dict[str, float]],
    roi: Optional[Dict[str, float]] = None,
) -> Optional[Dict[str, float]]:
    if not subject_box:
        return None

    # Bias the contact point toward the ROI side so feeding/drinking can follow
    # the animal's head direction instead of the torso center.
    x_ratio = 0.5
    y_ratio = 0.72
    if roi:
        subject_center_x = subject_box["x"] + (subject_box["width"] * 0.5)
        subject_center_y = subject_box["y"] + (subject_box["height"] * 0.5)
        roi_center_x = roi["x"] + (roi["width"] * 0.5)
        roi_center_y = roi["y"] + (roi["height"] * 0.5)

        if roi_center_x < (subject_center_x - 0.02):
            x_ratio = 0.2
        elif roi_center_x > (subject_center_x + 0.02):
            x_ratio = 0.8

        if roi_center_y < (subject_center_y - 0.02):
            y_ratio = 0.58
        elif roi_center_y > (subject_center_y + 0.02):
            y_ratio = 1.0

    return {
        "x": _clamp01(subject_box["x"] + (subject_box["width"] * x_ratio)),
        "y": _clamp01(subject_box["y"] + (subject_box["height"] * y_ratio)),
    }


@dataclass(frozen=True)
class BehaviorDecision:
    behavior_type: str
    intensity: float
    notes: str
    metadata: Dict[str, Any]
    signature: str
    requires_confirmation: bool = False
    confirmation_seconds: int = 0


class AIBehaviorMapper:
    """Derive conservative life-cycle behaviors from AI motion and vital data."""

    def __init__(
        self,
        *,
        heartbeat_interval: int = 300,
        activity_trigger_level: float = 10.0,
        activity_ignore_level: float = 8.0,
        activity_confirmation_seconds: int = 5,
        resting_max_activity: float = 1.0,
        reliable_confidence: float = 0.60,
        drinking_max_activity: float = 18.0,
        drinking_confirmation_seconds: int = 4,
        drinking_min_tracking_confidence: float = 0.35,
        feeding_max_activity: float = 24.0,
        feeding_confirmation_seconds: int = 5,
        feeding_min_tracking_confidence: float = 0.35,
    ):
        self.heartbeat_interval = max(30, int(heartbeat_interval))
        self.activity_trigger_level = max(0.0, float(activity_trigger_level))
        self.activity_ignore_level = max(0.0, min(float(activity_ignore_level), self.activity_trigger_level))
        self.activity_confirmation_seconds = max(1, int(activity_confirmation_seconds))
        self.resting_max_activity = max(0.0, float(resting_max_activity))
        self.reliable_confidence = max(0.0, min(1.0, float(reliable_confidence)))
        self.drinking_max_activity = max(0.0, float(drinking_max_activity))
        self.drinking_confirmation_seconds = max(1, int(drinking_confirmation_seconds))
        self.drinking_min_tracking_confidence = max(
            0.0, min(1.0, float(drinking_min_tracking_confidence))
        )
        self.feeding_max_activity = max(0.0, float(feeding_max_activity))
        self.feeding_confirmation_seconds = max(1, int(feeding_confirmation_seconds))
        self.feeding_min_tracking_confidence = max(
            0.0, min(1.0, float(feeding_min_tracking_confidence))
        )
        self.current_signature: Optional[str] = None
        self.state_started_at: Optional[datetime] = None
        self.last_logged_at: Optional[datetime] = None
        self.pending_signature: Optional[str] = None
        self.pending_started_at: Optional[datetime] = None

    def reset(self) -> None:
        self.current_signature = None
        self.state_started_at = None
        self.last_logged_at = None
        self.pending_signature = None
        self.pending_started_at = None

    def _clear_pending_behavior(self) -> None:
        self.pending_signature = None
        self.pending_started_at = None

    def _resolve_roi(
        self,
        system_settings: Optional[Dict[str, Any]],
        *,
        enabled_key: str,
        roi_key: str,
    ) -> Optional[Dict[str, float]]:
        if not isinstance(system_settings, dict):
            return None
        if system_settings.get(enabled_key) is not True:
            return None
        return _normalize_box(system_settings.get(roi_key))

    def _resolve_roi_contact(
        self,
        vision: Dict[str, Any],
        system_settings: Optional[Dict[str, Any]],
        *,
        enabled_key: str,
        roi_key: str,
    ) -> tuple[bool, Optional[Dict[str, float]], Optional[Dict[str, float]]]:
        roi = self._resolve_roi(
            system_settings,
            enabled_key=enabled_key,
            roi_key=roi_key,
        )
        subject_box = _normalize_box(vision.get("subject_box"))
        contact_point = _subject_contact_point(subject_box, roi)
        return _point_in_box(contact_point, roi), roi, contact_point

    def _resolve_bowl_preference(
        self,
        *,
        drinking_contact: bool,
        drinking_roi: Optional[Dict[str, float]],
        drinking_contact_point: Optional[Dict[str, float]],
        feeding_contact: bool,
        feeding_roi: Optional[Dict[str, float]],
        feeding_contact_point: Optional[Dict[str, float]],
    ) -> Optional[str]:
        if not (drinking_contact and feeding_contact):
            return None

        drinking_distance = _point_box_center_distance(drinking_contact_point, drinking_roi)
        feeding_distance = _point_box_center_distance(feeding_contact_point, feeding_roi)
        if drinking_distance is None or feeding_distance is None:
            return None

        if abs(drinking_distance - feeding_distance) < 0.025:
            return None

        return "drinking" if drinking_distance < feeding_distance else "feeding"

    def derive_behavior(
        self,
        ai_data: Dict[str, Any],
        *,
        system_settings: Optional[Dict[str, Any]] = None,
    ) -> Optional[BehaviorDecision]:
        if not isinstance(ai_data, dict):
            return None

        vision = ai_data.get("vision") if isinstance(ai_data.get("vision"), dict) else {}
        vitals = ai_data.get("vitals") if isinstance(ai_data.get("vitals"), dict) else {}

        vision_status = _clean_text(vision.get("status")).upper()
        vital_status = _clean_text(vitals.get("status")).upper()
        activity = _to_float(vision.get("activity")) or 0.0
        confidence = _to_float(vitals.get("confidence")) or 0.0
        respiration_bpm = _to_float(vitals.get("respiration_bpm"))
        tracking_confidence = _to_float(vision.get("subject_tracking_confidence")) or 0.0
        subject_box = _normalize_box(vision.get("subject_box"))
        default_contact_point = _subject_contact_point(subject_box)
        drinking_contact, drinking_roi, drinking_contact_point = self._resolve_roi_contact(
            vision,
            system_settings,
            enabled_key="drinking_roi_enabled",
            roi_key="drinking_roi",
        )
        feeding_contact, feeding_roi, feeding_contact_point = self._resolve_roi_contact(
            vision,
            system_settings,
            enabled_key="feeding_roi_enabled",
            roi_key="feeding_roi",
        )

        metadata = {
            "source": "ai_derived",
            "vision_status": vision_status or None,
            "vital_status": vital_status or None,
            "activity": round(activity, 2),
            "confidence": round(confidence, 2),
            "respiration_bpm": respiration_bpm,
            "subject_tracking_confidence": round(tracking_confidence, 2),
            "subject_contact_point": default_contact_point,
            "drinking_contact_point": drinking_contact_point,
            "feeding_contact_point": feeding_contact_point,
        }

        bowl_preference = self._resolve_bowl_preference(
            drinking_contact=drinking_contact,
            drinking_roi=drinking_roi,
            drinking_contact_point=drinking_contact_point,
            feeding_contact=feeding_contact,
            feeding_roi=feeding_roi,
            feeding_contact_point=feeding_contact_point,
        )
        metadata["bowl_contact_preference"] = bowl_preference

        if bowl_preference == "drinking":
            feeding_contact = False
        elif bowl_preference == "feeding":
            drinking_contact = False

        if (
            drinking_contact
            and feeding_contact
            and activity < self.activity_trigger_level
            and vital_status != "TOO_MUCH_MOTION"
        ):
            return None

        if (
            drinking_contact
            and not feeding_contact
            and activity <= self.drinking_max_activity
            and vital_status != "TOO_MUCH_MOTION"
            and bool(vision.get("subject_tracking_locked"))
            and tracking_confidence >= self.drinking_min_tracking_confidence
        ):
            return BehaviorDecision(
                behavior_type="drinking",
                intensity=round(max(0.5, min(10.0, max(activity, 1.0) / 4.0)), 2),
                notes="AI derived drinking behavior from sustained water-bowl ROI contact",
                metadata=metadata,
                signature="drinking",
                requires_confirmation=True,
                confirmation_seconds=self.drinking_confirmation_seconds,
            )

        if (
            feeding_contact
            and not drinking_contact
            and activity <= self.feeding_max_activity
            and vital_status != "TOO_MUCH_MOTION"
            and bool(vision.get("subject_tracking_locked"))
            and tracking_confidence >= self.feeding_min_tracking_confidence
        ):
            return BehaviorDecision(
                behavior_type="feeding",
                intensity=round(max(0.5, min(10.0, max(activity, 1.0) / 3.5)), 2),
                notes="AI derived feeding behavior from sustained food-bowl ROI contact",
                metadata=metadata,
                signature="feeding",
                requires_confirmation=True,
                confirmation_seconds=self.feeding_confirmation_seconds,
            )

        low_motion_activity = (
            vision_status == "HAREKETLI"
            and not drinking_contact
            and not feeding_contact
            and vital_status != "TOO_MUCH_MOTION"
            and activity >= self.activity_ignore_level
            and activity < self.activity_trigger_level
        )

        if low_motion_activity:
            return BehaviorDecision(
                behavior_type="activity",
                intensity=round(max(0.0, min(10.0, activity / 10.0)), 2),
                notes="AI derived activity from sustained low-level motion",
                metadata=metadata,
                signature="activity",
                requires_confirmation=True,
                confirmation_seconds=self.activity_confirmation_seconds,
            )

        if (
            activity >= self.activity_trigger_level
            or vital_status == "TOO_MUCH_MOTION"
        ):
            return BehaviorDecision(
                behavior_type="activity",
                intensity=round(max(0.0, min(10.0, activity / 10.0)), 2),
                notes="AI derived active behavior from motion or unstable tracking",
                metadata=metadata,
                signature="activity",
            )

        if (
            vital_status == "OK"
            and respiration_bpm is not None
            and confidence >= self.reliable_confidence
            and activity <= self.resting_max_activity
            and vision_status != "HAREKETLI"
        ):
            return BehaviorDecision(
                behavior_type="resting",
                intensity=round(max(0.0, min(10.0, activity / 10.0)), 2),
                notes="AI derived resting behavior from reliable low-motion vitals",
                metadata=metadata,
                signature="resting",
            )

        return None

    def consume(
        self,
        ai_data: Dict[str, Any],
        *,
        patient_context: Optional[Dict[str, Any]] = None,
        system_settings: Optional[Dict[str, Any]] = None,
        now: Optional[datetime] = None,
    ) -> Optional[Dict[str, Any]]:
        observed_at = now or datetime.now()
        decision = self.derive_behavior(ai_data, system_settings=system_settings)
        if not decision:
            self.reset()
            return None

        patient = patient_context if isinstance(patient_context, dict) else {}
        patient_marker = _clean_text(patient.get("id") or patient.get("name"))
        signature = f"{patient_marker}|{decision.signature}" if patient_marker else decision.signature

        if decision.requires_confirmation:
            if signature != self.pending_signature:
                self.pending_signature = signature
                self.pending_started_at = observed_at
                return None

            pending_started_at = self.pending_started_at or observed_at
            pending_elapsed = (observed_at - pending_started_at).total_seconds()
            if pending_elapsed < max(1, int(decision.confirmation_seconds or 0)):
                return None
        else:
            self._clear_pending_behavior()

        should_log = False
        event_reason = "heartbeat"

        if signature != self.current_signature:
            self.current_signature = signature
            self.state_started_at = (
                self.pending_started_at
                if decision.requires_confirmation and self.pending_started_at is not None
                else observed_at
            )
            should_log = True
            event_reason = "state_change"
        elif self.last_logged_at is None:
            should_log = True
            event_reason = "state_change"
        else:
            elapsed = (observed_at - self.last_logged_at).total_seconds()
            should_log = elapsed >= self.heartbeat_interval

        if not should_log:
            return None

        self.last_logged_at = observed_at
        state_started_at = self.state_started_at or observed_at
        duration_seconds = max(1, int((observed_at - state_started_at).total_seconds()))

        metadata = dict(decision.metadata)
        metadata["event_reason"] = event_reason

        return {
            "behavior_type": decision.behavior_type,
            "duration": duration_seconds,
            "intensity": decision.intensity,
            "notes": decision.notes,
            "metadata": metadata,
            "behavior_subtype": "ai_derived",
        }
