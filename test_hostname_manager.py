import sys
import subprocess
import unittest
from types import SimpleNamespace

from app.services.hostname_manager import (
    set_tailscale_hostname,
    set_device_hostname,
    validate_hostname,
)


class HostnameManagerTests(unittest.TestCase):
    def test_validate_hostname_normalizes_safe_name(self):
        valid, hostname, error = validate_hostname("Kuvoz-Furkan")

        self.assertTrue(valid)
        self.assertEqual(hostname, "kuvoz-furkan")
        self.assertIsNone(error)

    def test_validate_hostname_rejects_unsafe_names(self):
        for value in ["", "kuvoz_furkan", "-kuvoz", "kuvoz-", "kuvoz.furkan", "123"]:
            with self.subTest(value=value):
                valid, hostname, error = validate_hostname(value)
                self.assertFalse(valid)
                self.assertTrue(error)

    def test_set_device_hostname_updates_os_hosts_and_tailscale(self):
        commands = []

        def command_exists(name):
            if name in {"hostnamectl", "tailscale"}:
                return f"/usr/bin/{name}"
            return None

        def runner(command, capture_output, text, stdin, timeout):
            commands.append(command)
            if command == ["hostnamectl", "--static"]:
                return SimpleNamespace(returncode=0, stdout="kuvoz\n", stderr="")
            if command == ["hostnamectl", "set-hostname", "kuvoz-furkan"]:
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            if len(command) >= 4 and command[0] == sys.executable and command[1] == "-c":
                self.assertEqual(command[-1], "kuvoz-furkan")
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            if command == ["tailscale", "set", "--hostname=kuvoz-furkan"]:
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            raise AssertionError(command)

        result = set_device_hostname(
            "kuvoz-furkan",
            runner=runner,
            command_exists=command_exists,
            use_sudo=False,
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["changed"])
        self.assertEqual(result["hostname"], "kuvoz-furkan")
        self.assertIn(["hostnamectl", "set-hostname", "kuvoz-furkan"], commands)
        self.assertIn(["tailscale", "set", "--hostname=kuvoz-furkan"], commands)

    def test_set_device_hostname_can_resync_tailscale_without_os_change(self):
        commands = []

        def command_exists(name):
            if name in {"hostnamectl", "tailscale"}:
                return f"/usr/bin/{name}"
            return None

        def runner(command, capture_output, text, stdin, timeout):
            commands.append(command)
            if command == ["hostnamectl", "--static"]:
                return SimpleNamespace(returncode=0, stdout="kuvoz\n", stderr="")
            if command == ["tailscale", "set", "--hostname=kuvoz"]:
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            raise AssertionError(command)

        result = set_device_hostname(
            "kuvoz",
            runner=runner,
            command_exists=command_exists,
            use_sudo=False,
        )

        self.assertTrue(result["success"])
        self.assertFalse(result["changed"])
        self.assertNotIn(["hostnamectl", "set-hostname", "kuvoz"], commands)
        self.assertIn(["tailscale", "set", "--hostname=kuvoz"], commands)

    def test_set_device_hostname_reports_tailscale_failure_after_os_change(self):
        def command_exists(name):
            if name in {"hostnamectl", "tailscale"}:
                return f"/usr/bin/{name}"
            return None

        def runner(command, capture_output, text, stdin, timeout):
            if command == ["hostnamectl", "--static"]:
                return SimpleNamespace(returncode=0, stdout="kuvoz\n", stderr="")
            if command == ["hostnamectl", "set-hostname", "vetmarketi"]:
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            if len(command) >= 4 and command[0] == sys.executable and command[1] == "-c":
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            if command == ["tailscale", "set", "--hostname=vetmarketi"]:
                return SimpleNamespace(returncode=1, stdout="", stderr="permission denied")
            raise AssertionError(command)

        result = set_device_hostname(
            "vetmarketi",
            runner=runner,
            command_exists=command_exists,
            use_sudo=False,
        )

        self.assertFalse(result["success"])
        self.assertTrue(result["partial_success"])
        self.assertIn("Tailscale adı güncellenemedi", result["message"])

    def test_sudo_uses_non_interactive_mode_for_tailscale(self):
        commands = []

        def runner(command, capture_output, text, stdin, timeout):
            commands.append(command)
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        result = set_tailscale_hostname(
            "kuvoz-baysal",
            runner=runner,
            command_exists=lambda name: f"/usr/bin/{name}" if name == "tailscale" else None,
            use_sudo=True,
        )

        self.assertTrue(result["success"])
        self.assertEqual(commands[0], ["sudo", "-n", "tailscale", "set", "--hostname=kuvoz-baysal"])

    def test_timeout_returns_error_instead_of_raising(self):
        def runner(command, capture_output, text, stdin, timeout):
            raise subprocess.TimeoutExpired(command, timeout)

        result = set_tailscale_hostname(
            "kuvoz-baysal",
            runner=runner,
            command_exists=lambda name: f"/usr/bin/{name}" if name == "tailscale" else None,
            use_sudo=False,
        )

        self.assertFalse(result["success"])
        self.assertIn("zaman aşımına uğradı", result["message"])


if __name__ == "__main__":
    unittest.main()
