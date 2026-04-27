"""Pure control-decision helpers for Kuvoz climate logic."""

from __future__ import annotations

from typing import Optional, Tuple


def decide_hysteresis_output(
    *,
    enabled: bool,
    sensor_value: Optional[float],
    target: Optional[float],
    hysteresis: float,
    current_output_active: bool,
) -> Tuple[bool, str]:
    """Return desired output state for a hysteresis-controlled binary actuator."""
    if not enabled:
        return False, 'disabled'

    if sensor_value is None or target is None:
        return False, 'sensor_missing'

    if sensor_value < (target - hysteresis):
        return True, 'on'

    if sensor_value > (target + hysteresis):
        return False, 'off'

    return current_output_active, 'hold'


def evaluate_humidity_purge(
    *,
    enabled: bool,
    humidity_value: Optional[float],
    humidity_target: Optional[float],
    previous_state: bool,
    on_delta: float,
    off_delta: float,
) -> Tuple[bool, Optional[str]]:
    """Return humidity purge state and transition event."""
    if not enabled or humidity_value is None or humidity_target is None:
        next_state = False
    elif previous_state:
        next_state = humidity_value > (humidity_target + off_delta)
    else:
        next_state = humidity_value >= (humidity_target + on_delta)

    if next_state == previous_state:
        return next_state, None

    return next_state, 'started' if next_state else 'stopped'


def evaluate_co2_ventilation(
    *,
    enabled: bool,
    co2_value: Optional[float],
    previous_state: bool,
    on_ppm: float,
    off_ppm: float,
) -> Tuple[bool, Optional[str]]:
    """Return CO2 ventilation state and transition event."""
    if not enabled or co2_value is None:
        next_state = False
    elif previous_state:
        next_state = co2_value > off_ppm
    else:
        next_state = co2_value >= on_ppm

    if next_state == previous_state:
        return next_state, None

    return next_state, 'started' if next_state else 'stopped'


def decide_cooling_output(
    *,
    enabled: bool,
    heater_active: bool,
    temperature_value: Optional[float],
    cooling_target: Optional[float],
    hysteresis: float,
    current_output_active: bool,
) -> Tuple[bool, str]:
    """Return desired cooling output state with safety interlocks."""
    if not enabled:
        return False, 'disabled'

    if heater_active:
        return False, 'blocked_by_heater'

    if cooling_target in (None, 0):
        return False, 'no_target'

    if temperature_value is None:
        return False, 'sensor_missing'

    if temperature_value > (cooling_target + hysteresis):
        return True, 'on'

    if temperature_value < (cooling_target - hysteresis):
        return False, 'off'

    return current_output_active, 'hold'
