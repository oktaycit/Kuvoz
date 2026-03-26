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


@dataclass(frozen=True)
class BehaviorDecision:
    behavior_type: str
    intensity: float
    notes: str
    metadata: Dict[str, Any]
    signature: str


class AIBehaviorMapper:
    """Derive conservative life-cycle behaviors from AI motion and vital data."""

    def __init__(
        self,
        *,
        heartbeat_interval: int = 300,
        activity_trigger_level: float = 10.0,
        resting_max_activity: float = 1.0,
        reliable_confidence: float = 0.60,
    ):
        self.heartbeat_interval = max(30, int(heartbeat_interval))
        self.activity_trigger_level = max(0.0, float(activity_trigger_level))
        self.resting_max_activity = max(0.0, float(resting_max_activity))
        self.reliable_confidence = max(0.0, min(1.0, float(reliable_confidence)))
        self.current_signature: Optional[str] = None
        self.state_started_at: Optional[datetime] = None
        self.last_logged_at: Optional[datetime] = None

    def reset(self) -> None:
        self.current_signature = None
        self.state_started_at = None
        self.last_logged_at = None

    def derive_behavior(self, ai_data: Dict[str, Any]) -> Optional[BehaviorDecision]:
        if not isinstance(ai_data, dict):
            return None

        vision = ai_data.get("vision") if isinstance(ai_data.get("vision"), dict) else {}
        vitals = ai_data.get("vitals") if isinstance(ai_data.get("vitals"), dict) else {}

        vision_status = _clean_text(vision.get("status")).upper()
        vital_status = _clean_text(vitals.get("status")).upper()
        activity = _to_float(vision.get("activity")) or 0.0
        confidence = _to_float(vitals.get("confidence")) or 0.0
        respiration_bpm = _to_float(vitals.get("respiration_bpm"))

        metadata = {
            "source": "ai_derived",
            "vision_status": vision_status or None,
            "vital_status": vital_status or None,
            "activity": round(activity, 2),
            "confidence": round(confidence, 2),
            "respiration_bpm": respiration_bpm,
        }

        if (
            vision_status == "HAREKETLI"
            or activity >= self.activity_trigger_level
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
        now: Optional[datetime] = None,
    ) -> Optional[Dict[str, Any]]:
        observed_at = now or datetime.now()
        decision = self.derive_behavior(ai_data)
        if not decision:
            self.reset()
            return None

        patient = patient_context if isinstance(patient_context, dict) else {}
        patient_marker = _clean_text(patient.get("id") or patient.get("name"))
        signature = f"{patient_marker}|{decision.signature}" if patient_marker else decision.signature

        should_log = False
        event_reason = "heartbeat"

        if signature != self.current_signature:
            self.current_signature = signature
            self.state_started_at = observed_at
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
