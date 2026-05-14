import unittest
import importlib.util
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.services.task_manager import BackgroundTaskManager

sys.modules.setdefault(
    "flask_socketio",
    types.SimpleNamespace(emit=lambda *args, **kwargs: None),
)

ROUTE_PATH = Path(__file__).resolve().parent / "app" / "routes" / "socket_tailscale_routes.py"
spec = importlib.util.spec_from_file_location("socket_tailscale_routes_under_test", ROUTE_PATH)
socket_tailscale_routes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(socket_tailscale_routes)
register_tailscale_socket_routes = socket_tailscale_routes.register_tailscale_socket_routes


class FakeLogger:
    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


class FakeSocketIO:
    def __init__(self):
        self.handlers = {}
        self.emitted = []

    def on(self, event_name):
        def decorator(handler):
            self.handlers[event_name] = handler
            return handler

        return decorator

    def emit(self, event_name, payload, namespace=None):
        self.emitted.append((event_name, payload, namespace))


class ImmediateThread:
    def __init__(self, target, daemon=False):
        self.target = target
        self.daemon = daemon

    def start(self):
        self.target()


class TailscaleRouteTests(unittest.TestCase):
    def test_reauth_emits_auth_url_from_force_reauth_output(self):
        logger = FakeLogger()
        socketio = FakeSocketIO()
        task_manager = BackgroundTaskManager(logger=logger)
        commands = []

        def fake_run(command, **kwargs):
            commands.append(command)
            if command == ["which", "tailscale"]:
                return SimpleNamespace(returncode=0, stdout="/usr/bin/tailscale\n", stderr="")
            if command == ["sudo", "tailscale", "up", "--force-reauth", "--timeout=10s"]:
                return SimpleNamespace(
                    returncode=1,
                    stdout="",
                    stderr="To authenticate, visit:\nhttps://login.tailscale.com/a/abc123\n",
                )
            raise AssertionError(command)

        register_tailscale_socket_routes(
            socketio,
            logger=logger,
            task_manager=task_manager,
            qrcode_available=False,
        )

        with patch.object(socket_tailscale_routes.subprocess, "run", side_effect=fake_run), \
                patch.object(socket_tailscale_routes.threading, "Thread", ImmediateThread):
            socketio.handlers["tailscale_reauth"]()

        self.assertIn(
            ["sudo", "tailscale", "up", "--force-reauth", "--timeout=10s"],
            commands,
        )
        self.assertIn(
            (
                "tailscale_auth_url",
                {
                    "url": "https://login.tailscale.com/a/abc123",
                    "qr_code": None,
                    "mode": "reauth",
                    "message": "Yeniden doğrulama linki hazır.",
                },
                "/",
            ),
            socketio.emitted,
        )
        self.assertFalse(task_manager.is_busy)

    def test_share_page_qr_filters_machines_by_tailscale_ip(self):
        logger = FakeLogger()
        socketio = FakeSocketIO()
        task_manager = BackgroundTaskManager(logger=logger)

        def fake_run(command, **kwargs):
            if command == ["tailscale", "status", "--json"]:
                return SimpleNamespace(
                    returncode=0,
                    stdout=json.dumps({
                        "BackendState": "Running",
                        "Self": {
                            "HostName": "kuvoz-test",
                            "TailscaleIPs": ["100.101.255.55"],
                        },
                    }),
                    stderr="",
                )
            raise AssertionError(command)

        register_tailscale_socket_routes(
            socketio,
            logger=logger,
            task_manager=task_manager,
            qrcode_available=False,
        )

        with patch.object(socket_tailscale_routes.subprocess, "run", side_effect=fake_run), \
                patch.object(socket_tailscale_routes, "emit", socketio.emit):
            socketio.handlers["tailscale_share_page_qr"]()

        self.assertIn(
            (
                "tailscale_share_page_qr_response",
                {
                    "success": True,
                    "url": "https://login.tailscale.com/admin/machines?q=100.101.255.55",
                    "qr_code": None,
                    "hostname": "kuvoz-test",
                    "tailscale_ip": "100.101.255.55",
                    "web_url": "http://100.101.255.55:8000",
                },
                None,
            ),
            socketio.emitted,
        )


if __name__ == "__main__":
    unittest.main()
