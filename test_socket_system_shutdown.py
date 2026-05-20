import unittest
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import patch


def load_socket_system_routes():
    fake_flask_socketio = types.ModuleType('flask_socketio')
    fake_flask_socketio.emit = lambda *args, **kwargs: None
    sys.modules.setdefault('flask_socketio', fake_flask_socketio)

    module_path = Path(__file__).parent / 'app' / 'routes' / 'socket_system_routes.py'
    spec = importlib.util.spec_from_file_location('socket_system_routes_under_test', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


socket_system_routes = load_socket_system_routes()


class FakeSocketIO:
    def __init__(self):
        self.handlers = {}

    def on(self, event):
        def decorator(func):
            self.handlers[event] = func
            return func

        return decorator


class FakeThread:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.started = False

    def start(self):
        self.started = True


class FakeTimer(FakeThread):
    pass


class FakeLogger:
    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass

    def debug(self, *args, **kwargs):
        pass


class FakeKuvozServer:
    def __init__(self):
        self.save_calls = 0
        self.reset_calls = 0
        self.sensor_data = {}
        self.button_states = {}
        self.gpio_output_states = {}
        self.system_settings = {}
        self.ai_enabled = False

    def save_settings(self):
        self.save_calls += 1
        return True

    def reset_to_safe_state(self):
        self.reset_calls += 1

    def get_effective_slider_values(self):
        return {}

    def get_timer_data(self):
        return {}

    def get_effective_system_status(self):
        return {}

    def get_ai_health_status(self):
        return {}

    def get_care_status(self):
        return {}


def register_handlers(server):
    socketio = FakeSocketIO()
    socket_system_routes.register_system_socket_routes(
        socketio,
        kuvoz_server=server,
        logger=FakeLogger(),
        ai_available=False,
        gpio_available=False,
        script_dir='.',
        task_manager=None,
        perform_disk_cleanup=lambda **kwargs: {'success': True, 'message': 'ok'},
        get_git_version_info=lambda: {'hash': 'test'},
        get_git_update_diagnostics=lambda: {},
        classify_git_update_error=lambda *args, **kwargs: 'unknown',
        handle_update_slider_logic=lambda data: True,
        handle_save_settings_logic=lambda data: True,
    )
    return socketio.handlers


class SystemShutdownTests(unittest.TestCase):
    def test_shutdown_resets_to_safe_state(self):
        server = FakeKuvozServer()
        handlers = register_handlers(server)

        with patch.object(socket_system_routes, 'emit'), patch.object(socket_system_routes.threading, 'Thread', FakeThread):
            handlers['shutdown']()

        self.assertEqual(server.reset_calls, 1)
        self.assertEqual(server.save_calls, 0)

    def test_restart_preserves_current_state(self):
        server = FakeKuvozServer()
        handlers = register_handlers(server)

        with patch.object(socket_system_routes, 'emit'), patch.object(socket_system_routes.threading, 'Thread', FakeThread):
            handlers['restart']()

        self.assertEqual(server.save_calls, 1)
        self.assertEqual(server.reset_calls, 0)

    def test_legacy_shutdown_command_resets_to_safe_state(self):
        server = FakeKuvozServer()
        handlers = register_handlers(server)

        with patch.object(socket_system_routes, 'emit'), patch.object(socket_system_routes.threading, 'Timer', FakeTimer):
            handlers['message']({'command': 'shutdown', 'data': {}})

        self.assertEqual(server.reset_calls, 1)
        self.assertEqual(server.save_calls, 0)

    def test_legacy_restart_command_preserves_current_state(self):
        server = FakeKuvozServer()
        handlers = register_handlers(server)

        with patch.object(socket_system_routes, 'emit'), patch.object(socket_system_routes.threading, 'Timer', FakeTimer):
            handlers['message']({'command': 'restart', 'data': {}})

        self.assertEqual(server.save_calls, 1)
        self.assertEqual(server.reset_calls, 0)


if __name__ == '__main__':
    unittest.main()
