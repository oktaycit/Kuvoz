"""Pure helpers for nebulizer/ozone duty-cycle state machines."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def compute_ozone_duty_duration(
    *,
    base_duration: int,
    sensor_data: Dict[str, Dict[str, Any]],
    allow_estimated_oxygen: bool = True,
) -> Tuple[int, Optional[float], Optional[str]]:
    """Return adjusted ozone duty duration using oxygen context when available."""
    if 'oxygen' not in sensor_data:
        return base_duration, None, None

    if not allow_estimated_oxygen:
        return base_duration, None, None

    try:
        oxygen_value = float(sensor_data['oxygen']['value'])
        oxygen_status = sensor_data['oxygen']['status']
    except (TypeError, ValueError, KeyError):
        return base_duration, None, None

    if oxygen_value > 24.0:
        return int(base_duration * 1.5), oxygen_value, oxygen_status

    return base_duration, oxygen_value, oxygen_status


def start_duty_cycle(current_time: float) -> Tuple[bool, float]:
    """Return the canonical state for a newly started duty cycle."""
    return True, current_time


def update_duty_cycle_state(
    *,
    button_enabled: bool,
    in_duty: bool,
    phase_started_at: float,
    current_time: float,
    duty_duration: float,
    free_duration: float,
) -> Tuple[str, bool, float]:
    """Advance a generic duty/free state machine."""
    if not button_enabled:
        if in_duty or phase_started_at > 0:
            return 'stop', False, 0.0
        return 'noop', False, phase_started_at

    if in_duty:
        if current_time - phase_started_at >= duty_duration:
            return 'to_free', False, current_time
        return 'noop', True, phase_started_at

    if current_time - phase_started_at >= free_duration:
        return 'to_duty', True, current_time

    return 'noop', False, phase_started_at


def advance_duty_cycle(
    *,
    enabled: bool,
    in_duty: bool,
    cycle_start: float,
    current_time: float,
    duty_duration: float,
    free_duration: float,
) -> Dict[str, Any]:
    """Compatibility wrapper returning a dict transition payload."""
    action, next_in_duty, next_cycle_start = update_duty_cycle_state(
        button_enabled=enabled,
        in_duty=in_duty,
        phase_started_at=cycle_start,
        current_time=current_time,
        duty_duration=duty_duration,
        free_duration=free_duration,
    )
    mapped_action = {
        'noop': 'noop',
        'stop': 'stop',
        'to_free': 'start_free',
        'to_duty': 'start_duty',
    }[action]
    return {
        'action': mapped_action,
        'in_duty': next_in_duty,
        'cycle_start': next_cycle_start,
    }


def build_timer_state(
    *,
    button_enabled: Optional[bool] = None,
    button_active: Optional[bool] = None,
    in_duty: bool,
    phase_started_at: Optional[float] = None,
    cycle_start: Optional[float] = None,
    current_time: float,
    duty_duration: float,
    free_duration: float,
) -> Dict[str, int | str]:
    """Build frontend timer payload for a generic duty/free state machine."""
    if button_enabled is None:
        button_enabled = bool(button_active)
    if phase_started_at is None:
        phase_started_at = cycle_start or 0.0

    if not button_enabled:
        return {'phase': 'READY', 'remaining': 0, 'total': 0}

    if in_duty:
        remaining = max(0, duty_duration - (current_time - phase_started_at))
        return {'phase': 'DUTY', 'remaining': int(remaining), 'total': int(duty_duration)}

    remaining = max(0, free_duration - (current_time - phase_started_at))
    phase = 'FREE' if phase_started_at > 0 else 'READY'
    total = int(free_duration) if phase_started_at > 0 else 0
    return {'phase': phase, 'remaining': int(remaining), 'total': total}


def resolve_ozone_duty_duration(
    base_duration: int,
    oxygen_sensor: Optional[Dict[str, Any]],
) -> Tuple[int, Optional[Dict[str, Any]]]:
    """Compatibility wrapper returning adjusted duration and log note payload."""
    if not oxygen_sensor:
        return base_duration, None

    adjusted_duration, oxygen_value, oxygen_source = compute_ozone_duty_duration(
        base_duration=base_duration,
        sensor_data={'oxygen': oxygen_sensor},
        allow_estimated_oxygen=True,
    )
    if oxygen_value is None or adjusted_duration == base_duration:
        return adjusted_duration, None

    return adjusted_duration, {
        'oxygen': oxygen_value,
        'source': oxygen_source,
        'duration_minutes': adjusted_duration // 60,
    }
