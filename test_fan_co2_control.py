import unittest

from app.control.climate_controller import evaluate_co2_ventilation
from app.hardware.gpio_controller import (
    calculate_fan_speed_percent,
    normalize_fan_control_mode,
    should_disable_fan_for_nebulizer,
)


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


class FanCO2ControlTests(unittest.TestCase):
    def fan_speed(self, co2_value, co2_enabled=True):
        sensor_data = {
            'temperature': {'value': '--'},
            'humidity': {'value': '--'},
            'co2': {'value': str(co2_value) if co2_value is not None else '--'},
        }
        return calculate_fan_speed_percent(
            effective_sliders={'sld2': 65, 'sld3': 25, 'sld12': 0},
            sensor_data=sensor_data,
            gpio_output_states={'b4': False, 'b5': False, 'b9': False},
            button_states={'b9': False},
            humidity_purge_active=False,
            fan_pwm_heater_min_duty=35,
            clamp=clamp,
            co2_ventilation_enabled=co2_enabled,
        )

    def test_co2_ventilation_uses_hysteresis(self):
        active, event = evaluate_co2_ventilation(
            enabled=True,
            co2_value=1000,
            previous_state=False,
            on_ppm=1000,
            off_ppm=800,
        )
        self.assertTrue(active)
        self.assertEqual(event, 'started')

        active, event = evaluate_co2_ventilation(
            enabled=True,
            co2_value=850,
            previous_state=True,
            on_ppm=1000,
            off_ppm=800,
        )
        self.assertTrue(active)
        self.assertIsNone(event)

        active, event = evaluate_co2_ventilation(
            enabled=True,
            co2_value=790,
            previous_state=True,
            on_ppm=1000,
            off_ppm=800,
        )
        self.assertFalse(active)
        self.assertEqual(event, 'stopped')

    def test_co2_increases_pwm_duty(self):
        self.assertEqual(self.fan_speed(None), 25.0)
        self.assertEqual(self.fan_speed(999), 25.0)
        self.assertEqual(self.fan_speed(1000), 45.0)
        self.assertEqual(self.fan_speed(1500), 65.0)
        self.assertEqual(self.fan_speed(2000), 85.0)
        self.assertEqual(self.fan_speed(2400), 100.0)

    def test_disabled_co2_does_not_change_pwm_duty(self):
        self.assertEqual(self.fan_speed(2000, co2_enabled=False), 25.0)

    def test_nebulizer_disables_fan_only_during_duty_phase(self):
        self.assertFalse(should_disable_fan_for_nebulizer({'b2': False}, nebulizer_in_duty=True))
        self.assertFalse(should_disable_fan_for_nebulizer({'b2': True}, nebulizer_in_duty=False))
        self.assertTrue(should_disable_fan_for_nebulizer({'b2': True}, nebulizer_in_duty=True))

    def test_fan_control_mode_normalization(self):
        self.assertEqual(normalize_fan_control_mode('manual'), 'manual')
        self.assertEqual(normalize_fan_control_mode('MANUAL'), 'manual')
        self.assertEqual(normalize_fan_control_mode('auto'), 'auto')
        self.assertEqual(normalize_fan_control_mode('bad-value'), 'auto')


if __name__ == "__main__":
    unittest.main()
