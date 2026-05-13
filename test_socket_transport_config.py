import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class SocketTransportConfigTests(unittest.TestCase):
    def test_websocket_upgrade_path_is_not_used_by_pages(self):
        offenders = []
        for path in (ROOT / "web").glob("*"):
            if path.name == "socket.io.min.js" or path.suffix not in {".html", ".js"}:
                continue

            content = path.read_text(encoding="utf-8", errors="ignore")
            if "/socket.io/socket.io.js" in content:
                offenders.append(str(path.relative_to(ROOT)))
            if "transports: ['websocket'" in content or 'transports: ["websocket"' in content:
                offenders.append(str(path.relative_to(ROOT)))
            if "rememberUpgrade: true" in content or "upgrade: true" in content:
                offenders.append(str(path.relative_to(ROOT)))

        self.assertEqual(offenders, [])

    def test_server_defaults_to_polling_only(self):
        content = (ROOT / "web_server.py").read_text(encoding="utf-8")

        self.assertIn("KUVOZ_SOCKETIO_TRANSPORTS', 'polling'", content)
        self.assertIn("transports=SOCKETIO_TRANSPORTS", content)
        self.assertIn("allow_upgrades=SOCKETIO_ALLOW_UPGRADES", content)

    def test_server_prefers_eventlet_in_production(self):
        content = (ROOT / "web_server.py").read_text(encoding="utf-8")

        self.assertIn("KUVOZ_SOCKETIO_ASYNC_MODE', 'eventlet'", content)
        self.assertIn("async_mode=SOCKETIO_ASYNC_MODE", content)
        self.assertIn("EVENTLET_NO_GREENDNS', 'yes'", content)
        self.assertNotIn("async_mode='threading'", content)

    def test_systemd_requests_eventlet_mode(self):
        content = (ROOT / "systemd" / "kuvoz-web.service").read_text(encoding="utf-8")

        self.assertIn("Environment=EVENTLET_NO_GREENDNS=yes", content)
        self.assertIn("Environment=KUVOZ_SOCKETIO_ASYNC_MODE=eventlet", content)


if __name__ == "__main__":
    unittest.main()
