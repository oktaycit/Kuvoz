"""GPIO and fan control helpers for Kuvoz hardware flows."""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, Optional, Tuple


OUTPUT_CHANNELS: Tuple[int, ...] = (5, 6, 13, 16, 19, 20, 21, 26, 12)
TOUCH_BUTTON_PINS: Tuple[int, ...] = (5, 20, 21)
DEFAULT_DHT_PIN = 15
DEFAULT_WPS_PIN = 4

PIN_TO_BUTTON = {
    5: 'b1',
    6: 'b2',
    13: 'b3',
    16: 'b4',
    19: 'b5',
    20: 'b6',
    21: 'b7',
    26: 'b8',
    12: 'b9',
}


def button_name_by_pin(pin: int) -> Optional[str]:
    """Return button name for a configured GPIO output pin."""
    return PIN_TO_BUTTON.get(pin)


def heater_output_active(gpio_output_states: Dict[str, Optional[bool]]) -> bool:
    """Return True when any heating relay output is currently active."""
    return (
        gpio_output_states.get('b4') is True or
        gpio_output_states.get('b5') is True
    )


def should_disable_fan_for_nebulizer(button_states: Dict[str, Any], nebulizer_in_duty: bool) -> bool:
    """Return True while nebulizer output is actively running."""
    return bool(button_states.get('b2')) and bool(nebulizer_in_duty)


def reserved_gpio_pins(
    output_channels: Iterable[int],
    dht_pin: int,
    wps_pin: int,
    extra_pins: Iterable[int] = (2, 3),
) -> set[int]:
    """Build the set of GPIO pins reserved by relay, sensor, and bus usage."""
    return set(output_channels) | {dht_pin, wps_pin} | set(extra_pins)


def normalize_fan_output_mode(mode: Any) -> str:
    """Normalize persisted/user-provided fan output mode."""
    if isinstance(mode, str):
        normalized = mode.strip().lower()
        if normalized in ('pwm', 'mosfet', 'gpio18', 'p18'):
            return 'pwm'
    return 'relay'


def normalize_fan_control_mode(mode: Any) -> str:
    """Normalize fan control strategy."""
    if isinstance(mode, str) and mode.strip().lower() == 'manual':
        return 'manual'
    return 'auto'


def get_sensor_numeric_value(sensor_data: Dict[str, Dict[str, Any]], sensor_name: str) -> Optional[float]:
    """Return a numeric sensor value when available."""
    sensor = sensor_data.get(sensor_name) or {}
    value = sensor.get('value')
    if value in (None, '--', ''):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def calculate_fan_speed_percent(
    *,
    effective_sliders: Dict[str, Any],
    sensor_data: Dict[str, Dict[str, Any]],
    gpio_output_states: Dict[str, Any],
    button_states: Dict[str, Any],
    humidity_purge_active: bool,
    fan_pwm_heater_min_duty: float,
    clamp: Callable[[float, float, float], float],
    co2_ventilation_enabled: bool = True,
) -> float:
    """Return automatic fan PWM duty cycle derived from climate demand."""
    base_duty = clamp(fan_pwm_heater_min_duty - 10.0, 20.0, 100.0)
    duty = base_duty

    heater_active = heater_output_active(gpio_output_states)
    cooling_active = gpio_output_states.get('b9') is True
    cooling_requested = bool(button_states.get('b9')) or cooling_active

    if heater_active:
        duty = max(duty, fan_pwm_heater_min_duty)

    temp = get_sensor_numeric_value(sensor_data, 'temperature')
    hum = get_sensor_numeric_value(sensor_data, 'humidity')
    co2 = get_sensor_numeric_value(sensor_data, 'co2')

    try:
        temp_target = float(effective_sliders.get('sld3'))
    except (TypeError, ValueError):
        temp_target = None

    try:
        hum_target = float(effective_sliders.get('sld2'))
    except (TypeError, ValueError):
        hum_target = None

    try:
        cooling_target = float(effective_sliders.get('sld12', 0))
    except (TypeError, ValueError):
        cooling_target = 0.0

    if temp is not None and temp_target is not None and temp > temp_target:
        duty = max(
            duty,
            clamp(fan_pwm_heater_min_duty + ((temp - temp_target) * 18.0), fan_pwm_heater_min_duty, 95.0)
        )

    if temp is not None and cooling_requested and cooling_target > 0:
        if temp > cooling_target:
            duty = max(duty, clamp(45.0 + ((temp - cooling_target) * 18.0), 45.0, 100.0))
        elif cooling_active:
            duty = max(duty, 45.0)

    if hum is not None and hum_target is not None and hum > hum_target:
        duty = max(duty, clamp(base_duty + ((hum - hum_target) * 2.5), base_duty, 90.0))

    if humidity_purge_active:
        duty = max(duty, 45.0)

    if co2_ventilation_enabled and co2 is not None and co2 >= 1000.0:
        duty = max(duty, clamp(45.0 + ((co2 - 1000.0) / 500.0 * 20.0), 45.0, 100.0))

    return round(clamp(duty, 20.0, 100.0), 1)


class GPIOController:
    """Low-level GPIO and fan output coordinator bound to a running server."""

    def __init__(
        self,
        *,
        gpio: Any,
        gpio_available_getter: Callable[[], bool],
        check_gpio_status: Callable[[], bool],
        logger: Any,
        button_states: Dict[str, Any],
        gpio_output_states: Dict[str, Any],
        get_fan_speed_percent: Callable[[], float],
        initialize_fan_pwm: Callable[..., bool],
        stop_fan_pwm: Callable[[], None],
        is_fan_pwm_mode: Callable[[], bool],
        fan_pwm_lock: Any,
        fan_pwm_pin_getter: Callable[[], Any],
        fan_pwm_getter: Callable[[], Any],
        fan_pwm_setter: Callable[[Any], None],
        fan_pwm_available_getter: Callable[[], bool],
        fan_pwm_available_setter: Callable[[bool], None],
        fan_pwm_duty_getter: Callable[[], float],
        fan_pwm_duty_setter: Callable[[float], None],
        get_fan_output_mode: Callable[[], str],
        set_fan_output_mode: Callable[[str], None],
        state_lock: Any,
    ) -> None:
        self.gpio = gpio
        self.gpio_available_getter = gpio_available_getter
        self.check_gpio_status = check_gpio_status
        self.logger = logger
        self.button_states = button_states
        self.gpio_output_states = gpio_output_states
        self.get_fan_speed_percent = get_fan_speed_percent
        self.initialize_fan_pwm = initialize_fan_pwm
        self.stop_fan_pwm = stop_fan_pwm
        self.is_fan_pwm_mode = is_fan_pwm_mode
        self.fan_pwm_lock = fan_pwm_lock
        self.fan_pwm_pin_getter = fan_pwm_pin_getter
        self.fan_pwm_getter = fan_pwm_getter
        self.fan_pwm_setter = fan_pwm_setter
        self.fan_pwm_available_getter = fan_pwm_available_getter
        self.fan_pwm_available_setter = fan_pwm_available_setter
        self.fan_pwm_duty_getter = fan_pwm_duty_getter
        self.fan_pwm_duty_setter = fan_pwm_duty_setter
        self.get_fan_output_mode = get_fan_output_mode
        self.set_fan_output_mode = set_fan_output_mode
        self.state_lock = state_lock
        self._gpio_low_sim = 0
        self._gpio_high_sim = 1

    def refresh_fan_output_mode(self, reapply_current_output: bool = True) -> None:
        """Apply selected fan output mode immediately."""
        mode = self.get_fan_output_mode()
        self.set_fan_output_mode(mode)

        if mode == 'pwm':
            self.initialize_fan_pwm(force_recreate=True)
            self.safe_gpio_output(20, self.gpio.HIGH)
        else:
            self.stop_fan_pwm()

        if reapply_current_output:
            fan_enabled = bool(self.button_states.get('b6'))
            if fan_enabled:
                self.apply_fan_output(True, duty=self.get_fan_speed_percent(), source='mode_refresh')
            else:
                self.apply_fan_output(False, source='mode_refresh')

    def apply_fan_output(self, enabled: bool, duty: Optional[float] = None, source: str = 'manual') -> bool:
        """Drive fan output using the selected output mode."""
        if not self.is_fan_pwm_mode():
            relay_state = self.gpio.LOW if enabled else self.gpio.HIGH
            return self.safe_gpio_output(20, relay_state)

        if not self.fan_pwm_available_getter() and not self.initialize_fan_pwm(force_recreate=True):
            self.safe_gpio_output(20, self.gpio.HIGH)
            with self.state_lock:
                self.gpio_output_states['b6'] = None if enabled else False
            return False

        if enabled:
            if duty is None:
                applied_duty = self.get_fan_speed_percent()
            else:
                try:
                    applied_duty = max(20.0, min(100.0, float(duty)))
                except (TypeError, ValueError):
                    applied_duty = self.get_fan_speed_percent()
        else:
            applied_duty = 0.0

        if not self.check_gpio_status():
            self.safe_gpio_output(20, self.gpio.HIGH)
            with self.state_lock:
                self.gpio_output_states['b6'] = None
            return False

        if self.fan_pwm_getter() is None and not self.initialize_fan_pwm(force_recreate=True):
            self.safe_gpio_output(20, self.gpio.HIGH)
            with self.state_lock:
                self.gpio_output_states['b6'] = None if enabled else False
            return False

        try:
            self.safe_gpio_output(20, self.gpio.HIGH)
            with self.fan_pwm_lock:
                self.fan_pwm_getter().ChangeDutyCycle(applied_duty)
            self.fan_pwm_duty_setter(applied_duty)
            with self.state_lock:
                self.gpio_output_states['b6'] = enabled and applied_duty > 0
            self.logger.debug(
                "🌬️ Fan PWM updated: enabled=%s duty=%.1f source=%s",
                enabled,
                applied_duty,
                source,
            )
            return True
        except Exception as exc:
            self.logger.error(f"Fan PWM output error: {exc}")
            with self.state_lock:
                self.gpio_output_states['b6'] = None
            return False

    def safe_gpio_output(self, pin: int, state: Any) -> bool:
        """Thread-safe GPIO output with state tracking."""
        button_name = button_name_by_pin(pin)

        if not self.gpio_available_getter():
            if button_name:
                with self.state_lock:
                    is_on = (state == self._gpio_low_sim)
                    self.gpio_output_states[button_name] = is_on
            return False

        if button_name:
            with self.state_lock:
                self.gpio_output_states[button_name] = (state == self.gpio.LOW)

        if not self.check_gpio_status():
            if button_name:
                with self.state_lock:
                    self.gpio_output_states[button_name] = None
            return False

        try:
            self.gpio.output(pin, state)
            return True
        except Exception as exc:
            self.logger.error(f"GPIO output error on pin {pin}: {exc}")
            if self.check_gpio_status():
                try:
                    self.gpio.output(pin, state)
                    self.logger.info(f"🔧 GPIO recovered for pin {pin}")
                    return True
                except Exception as recovery_exc:
                    self.logger.error(f"GPIO recovery failed for pin {pin}: {recovery_exc}")
            if button_name:
                with self.state_lock:
                    self.gpio_output_states[button_name] = None
            return False
