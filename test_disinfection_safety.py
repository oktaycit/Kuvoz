"""Exercise production methods with simulated outputs only; no server/hardware imports."""
import ast
import copy
import logging
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from flask import Flask
from flask_socketio import SocketIO
from app.control.disinfection import DisinfectionSafetyMixin
from app.control.duty_cycles import compute_ozone_duty_duration, start_duty_cycle, update_duty_cycle_state
from app.routes.socket_routes import register_basic_socket_routes


def production_methods():
    tree = ast.parse((Path(__file__).parent / 'web_server.py').read_text())
    server = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'KuvozServer')
    methods = [n for n in server.body if isinstance(n, ast.FunctionDef) and n.name in
               ('toggle_button', 'control_logic', 'update_ozone_duty_cycle')]
    scope = dict(logger=logging.getLogger('test'), time=time, GPIO=SimpleNamespace(HIGH=1, LOW=0),
                 compute_ozone_duty_duration=compute_ozone_duty_duration,
                 start_duty_cycle=start_duty_cycle, update_duty_cycle_state=update_duty_cycle_state)
    exec(compile(ast.Module(body=methods, type_ignores=[]), '<production-disinfection>', 'exec'), scope)
    return scope


class FakeServer(DisinfectionSafetyMixin):
    def __init__(self):
        self.init_disinfection_safety()
        self.state_lock = threading.RLock()
        self.outChannels = [5, 6, 13, 16, 19, 20, 21, 26, 12]
        self.button_states = {f'b{i}': False for i in range(1, 10)}
        self.gpio_output_states = self.button_states.copy()
        self.system_settings = {'cooling_enabled': True}
        self.slider_values = {'sld10': 0.01, 'sld11': 1, 'sld7': 8}
        self.sensor_data = {'oxygen': {'value': '30', 'status': 'Tahmini'}}
        self.firebase_manager = None
        self.control_active = True
        self.nebulizer_in_duty = self.ozone_in_duty = False
        self.nebulizer_duty_start = self.ozone_duty_start = 0
        self.fan_auto_active = False
        self.schedule_settings_save = Mock()
        self.save_settings = Mock(return_value=True)
        self.history = []
        self.fail_pin = None
        self.fail_fan = False

    def safe_gpio_output(self, pin, value):
        self.history.append((pin, value))
        name = f'b{self.outChannels.index(pin)+1}'
        if pin == self.fail_pin:
            self.gpio_output_states[name] = None
            return False
        self.gpio_output_states[name] = value == 0
        return True

    def apply_fan_output(self, enable, **kwargs):
        self.gpio_output_states['b6'] = None if self.fail_fan else enable
        return not self.fail_fan

    def snapshot_runtime_state(self):
        return copy.deepcopy({'button_states': self.button_states, 'gpio_output_states': self.gpio_output_states})

    def build_button_update_payload(self, snapshot):
        return {'buttons': snapshot['button_states'], 'gpio_outputs': snapshot['gpio_output_states']}

    def build_status_payload(self, **kwargs):
        return {}

    def register_active_connection(self, *args, **kwargs): pass
    def note_local_kiosk_connect(self, *args): pass
    def get_active_connections_payload(self, *args): return {}
    def pop_active_connection(self, *args): return None


for name, method in production_methods().items():
    if name in ('toggle_button', 'control_logic', 'update_ozone_duty_cycle'):
        setattr(FakeServer, name, method)


class DisinfectionSafetyTests(unittest.TestCase):
    def setUp(self):
        self.server = FakeServer()

    def test_start_physically_removes_normal_loads_before_exposure(self):
        s = self.server
        s.button_states['b4'] = s.gpio_output_states['b4'] = True
        s.button_states['b9'] = s.gpio_output_states['b9'] = True
        self.assertTrue(s.start_disinfection('owner'))
        self.assertFalse(s.gpio_output_states['b4'])
        self.assertFalse(s.gpio_output_states['b9'])
        s.toggle_button('b8', 26, True)
        self.assertLess(s.history.index((16, 1)), s.history.index((26, 0)))
        self.assertTrue(s.disinfection_ventilation_required)
        s.save_settings.assert_called_once()

    def test_controlled_output_off_is_immediate_even_in_disinfection(self):
        s = self.server
        s.disinfection_mode = True
        s.gpio_output_states['b4'] = True
        self.assertTrue(s.toggle_button('b4', 16, False))
        self.assertFalse(s.gpio_output_states['b4'])
        self.assertFalse(s.toggle_button('b4', 16, True))

    def test_cycle_ends_once_and_starts_fan_without_clearance_claim(self):
        s = self.server
        s.start_disinfection('owner'); s.toggle_button('b8', 26, True)
        s.ozone_duty_start = time.time() - 1
        s.control_logic()
        self.assertFalse(s.gpio_output_states['b8'])
        self.assertFalse(s.disinfection_mode)
        self.assertTrue(s.gpio_output_states['b6'])
        self.assertFalse(s.button_states['b8'])
        self.assertTrue(s.disinfection_ventilation_required)

    def test_active_exposure_duration_is_fixed_at_start(self):
        s = self.server
        s.slider_values['sld10'] = 2
        s.start_disinfection('owner'); s.toggle_button('b8', 26, True)
        s.slider_values['sld10'] = 100
        s.ozone_duty_start = time.time() - 121
        s.control_disinfection()
        self.assertFalse(s.gpio_output_states['b8'])
        self.assertFalse(s.disinfection_mode)

    def test_expired_lease_stops_both_outputs(self):
        s = self.server
        s.start_disinfection('owner'); s.toggle_button('b7', 21, True)
        s.disinfection_heartbeat = time.monotonic() - 21
        s.control_disinfection()
        self.assertFalse(s.gpio_output_states['b7'])
        self.assertTrue(s.gpio_output_states['b6'])

    def test_stop_failure_is_not_acknowledged_and_is_retried(self):
        s = self.server
        s.start_disinfection('owner'); s.toggle_button('b7', 21, True)
        s.fail_pin = 21
        self.assertFalse(s.stop_disinfection())
        self.assertTrue(s.disinfection_mode)
        s.fail_pin = None
        s.control_disinfection()
        self.assertFalse(s.disinfection_mode)
        self.assertFalse(s.gpio_output_states['b7'])

    def test_failed_output_or_persistence_prevents_start(self):
        s = self.server
        s.fail_pin = 16
        self.assertFalse(s.start_disinfection('owner'))
        self.assertFalse(s.disinfection_mode)
        s.fail_pin = None; s.save_settings.return_value = False
        self.assertFalse(s.start_disinfection('owner'))
        self.assertFalse(s.disinfection_mode)

    def test_inactive_control_loop_prevents_start(self):
        self.server.control_active = False
        self.assertFalse(self.server.start_disinfection('owner'))

    def test_restart_resumes_fan_without_reenergizing_disinfection(self):
        s = self.server
        s.disinfection_ventilation_required = True
        self.assertTrue(s.resume_disinfection_safety())
        self.assertTrue(s.gpio_output_states['b6'])
        self.assertFalse(s.gpio_output_states['b7'])
        self.assertFalse(s.gpio_output_states['b8'])
        self.assertFalse(s.disinfection_mode)
        self.assertTrue(s.disinfection_ventilation_required)

    def test_direct_calls_cannot_bypass_session_interlock(self):
        self.assertFalse(self.server.toggle_button('b7', 21, True))
        self.assertEqual(self.server.history, [])

    def test_fan_failure_is_not_acknowledged_as_success(self):
        s = self.server
        s.start_disinfection('owner'); s.toggle_button('b7', 21, True)
        s.fail_fan = True
        self.assertFalse(s.stop_disinfection())
        self.assertTrue(s.disinfection_ventilation_required)
        self.assertFalse(s.gpio_output_states['b7'])


class DisinfectionSocketTests(unittest.TestCase):
    def setUp(self):
        self.server = FakeServer()
        app = Flask(__name__); app.config['TESTING'] = True
        self.io = SocketIO(app, async_mode='threading')
        register_basic_socket_routes(self.io, kuvoz_server=self.server,
                                     logger=logging.getLogger('test'), ai_available=False)
        self.client = self.io.test_client(app)
        self.app = app

    def toggle(self, **kwargs):
        data = dict(name='b8', pin=26, state=True, page='cleaning', empty_confirmed=True)
        data.update(kwargs)
        return self.client.emit('toggle_button', data, callback=True)

    def test_requires_empty_confirmation_and_correct_pin_before_side_effects(self):
        self.assertFalse(self.toggle(empty_confirmed=False)['success'])
        self.assertFalse(self.toggle(pin=16)['success'])
        self.assertFalse(self.toggle(page='index')['success'])
        self.assertFalse(self.server.disinfection_mode)
        self.assertEqual(self.server.history, [])

    def test_owner_disconnect_stops_observer_disconnect_does_not(self):
        self.assertTrue(self.toggle()['success'])
        observer = self.io.test_client(self.app); observer.disconnect()
        self.assertTrue(self.server.disinfection_mode)
        self.client.disconnect()
        self.assertFalse(self.server.disinfection_mode)
        self.assertFalse(self.server.gpio_output_states['b8'])

    def test_explicit_stop_is_idempotent_and_returns_confirmation(self):
        self.toggle()
        for _ in range(2):
            reply = self.client.emit('stop_disinfection', {}, callback=True)
            self.assertTrue(reply['success'])
            self.assertFalse(reply['disinfection']['active'])
            self.assertTrue(reply['disinfection']['ventilation_required'])

    def test_rejects_another_owner_and_renews_only_current_owner(self):
        self.toggle()
        observer = self.io.test_client(self.app)
        self.assertFalse(observer.emit('toggle_button', dict(name='b7', pin=21, state=True,
                          page='cleaning', empty_confirmed=True), callback=True)['success'])
        self.server.disinfection_heartbeat = 0
        observer.emit('disinfection_heartbeat', {})
        self.assertEqual(self.server.disinfection_heartbeat, 0)
        self.client.emit('disinfection_heartbeat', {})
        self.assertGreater(self.server.disinfection_heartbeat, 0)

    def test_invalid_ozone_duration_never_starts(self):
        self.server.slider_values['sld10'] = float('nan')
        self.assertFalse(self.toggle()['success'])
        self.assertFalse(self.server.disinfection_mode)
