"""Fan PWM must release its worker while idle and restart on demand."""
import ast
import logging
from pathlib import Path
from threading import RLock
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from app.hardware.gpio_controller import GPIOController, reserved_gpio_pins


def load_initializer():
    # Exercise the actual server method without starting Flask or hardware.
    tree = ast.parse(Path(__file__).with_name('web_server.py').read_text())
    server = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'KuvozServer')
    method = next(n for n in server.body if isinstance(n, ast.FunctionDef) and n.name == 'initialize_fan_pwm')
    scope = {'GPIO_AVAILABLE': True, 'reserved_gpio_pins': reserved_gpio_pins,
             'logger': logging.getLogger(__name__)}
    exec(compile(ast.Module(body=[method], type_ignores=[]), 'web_server.py', 'exec'), scope)
    return scope


class FanPWMLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.scope = load_initializer()
        self.gpio = Mock(HIGH=1, LOW=0, OUT=1)
        self.scope['GPIO'] = self.gpio
        self.server = SimpleNamespace(
            fan_pwm=None, fan_pwm_available=False, fan_pwm_duty=0., fan_pwm_pin=18,
            fan_pwm_frequency=25000, fan_pwm_lock=RLock(), outChannels=[5, 6, 13, 16, 19, 20, 21, 26, 12],
            pinDht=15, pinWps=4, is_fan_pwm_mode=lambda: True,
        )
        s = self.server
        def initialize(**kwargs):
            return self.scope['initialize_fan_pwm'](s, **kwargs)
        self.controller = GPIOController(
            gpio=self.gpio, gpio_available_getter=lambda: True, check_gpio_status=lambda: True,
            logger=logging.getLogger(__name__), button_states={}, gpio_output_states={},
            get_fan_speed_percent=lambda: 40., initialize_fan_pwm=initialize, stop_fan_pwm=Mock(),
            is_fan_pwm_mode=s.is_fan_pwm_mode, fan_pwm_lock=s.fan_pwm_lock,
            fan_pwm_pin_getter=lambda: s.fan_pwm_pin, fan_pwm_getter=lambda: s.fan_pwm,
            fan_pwm_setter=lambda v: setattr(s, 'fan_pwm', v),
            fan_pwm_available_getter=lambda: s.fan_pwm_available,
            fan_pwm_available_setter=lambda v: setattr(s, 'fan_pwm_available', v),
            fan_pwm_duty_getter=lambda: s.fan_pwm_duty,
            fan_pwm_duty_setter=lambda v: setattr(s, 'fan_pwm_duty', v),
            get_fan_output_mode=lambda: 'pwm', set_fan_output_mode=Mock(), state_lock=RLock(),
        )
        s.safe_gpio_output = self.controller.safe_gpio_output
        self.initialize = initialize

    def test_initialization_does_not_start_idle_worker(self):
        self.assertTrue(self.initialize())
        self.gpio.PWM.return_value.start.assert_not_called()
        self.gpio.output.assert_called_with(18, 0)
        self.assertTrue(self.server.fan_pwm_available)

    def test_idle_start_speed_change_stop_and_restart(self):
        first, second = Mock(), Mock()
        self.gpio.PWM.side_effect = [first, second]
        c = self.controller
        self.assertTrue(c.apply_fan_output(False))
        first.start.assert_not_called()
        self.assertIsNone(self.server.fan_pwm)
        for _ in range(3):
            self.assertTrue(c.apply_fan_output(False))
        self.assertEqual(self.gpio.PWM.call_count, 1)
        self.assertTrue(c.apply_fan_output(True, duty=35))
        second.start.assert_called_once_with(35.)
        self.assertTrue(c.apply_fan_output(True, duty=70))
        second.ChangeDutyCycle.assert_called_once_with(70.)
        self.assertTrue(c.apply_fan_output(False))
        second.stop.assert_called_once()
        self.assertEqual(self.server.fan_pwm_duty, 0.)
        self.assertFalse(c.gpio_output_states['b6'])
        third = Mock()
        self.gpio.PWM.side_effect = None
        self.gpio.PWM.return_value = third
        self.assertTrue(c.apply_fan_output(True, duty=100))
        third.start.assert_called_once_with(100.)
        self.assertTrue(c.gpio_output_states['b6'])

    def test_relay_mode_preserves_active_low_output(self):
        self.controller.is_fan_pwm_mode = lambda: False
        self.assertTrue(self.controller.apply_fan_output(True))
        self.gpio.output.assert_called_with(20, 0)
        self.assertTrue(self.controller.apply_fan_output(False))
        self.gpio.output.assert_called_with(20, 1)
        self.gpio.PWM.assert_not_called()

    def test_failed_start_reports_unknown_output(self):
        self.gpio.PWM.return_value.start.side_effect = RuntimeError('start failed')
        self.assertFalse(self.controller.apply_fan_output(True, duty=50))
        self.assertIsNone(self.controller.gpio_output_states['b6'])

    def test_missing_gpio_keeps_fan_unavailable(self):
        self.scope['GPIO_AVAILABLE'] = False
        self.assertFalse(self.initialize())
        self.gpio.PWM.assert_not_called()
        self.assertFalse(self.server.fan_pwm_available)


if __name__ == '__main__':
    unittest.main()
