import unittest
from unittest.mock import patch

import app.services.field_diagnostics as field_diagnostics
from app.services.field_diagnostics import (
    collect_wifi_status,
    collect_power_status,
    decode_power_throttled,
    parse_meminfo_snapshot,
    parse_route_get_output,
    split_nmcli_line,
)


class FieldDiagnosticsTests(unittest.TestCase):
    def test_decode_clean_throttled_mask(self):
        decoded = decode_power_throttled("throttled=0x0")

        self.assertEqual(decoded["mask"], 0)
        self.assertEqual(decoded["active_flags"], [])
        self.assertEqual(decoded["current_flags"], [])
        self.assertEqual(decoded["historical_flags"], [])

    def test_decode_current_and_historical_undervoltage(self):
        decoded = decode_power_throttled("throttled=0x50005")

        self.assertIn("undervoltage_now", decoded["current_flags"])
        self.assertIn("throttled_now", decoded["current_flags"])
        self.assertIn("undervoltage_occurred", decoded["historical_flags"])
        self.assertIn("throttled_occurred", decoded["historical_flags"])

    def test_decode_soft_temperature_limit_without_undervoltage(self):
        decoded = decode_power_throttled("throttled=0x80008")

        self.assertIn("soft_temperature_limit_now", decoded["current_flags"])
        self.assertIn("soft_temperature_limit_occurred", decoded["historical_flags"])
        self.assertNotIn("undervoltage_now", decoded["current_flags"])
        self.assertNotIn("undervoltage_occurred", decoded["historical_flags"])

    def test_collect_power_status_describes_historical_thermal_limit(self):
        def fake_run_command(args, timeout=5):
            if args == ["vcgencmd", "get_throttled"]:
                return {
                    "available": True,
                    "ok": True,
                    "returncode": 0,
                    "stdout": "throttled=0x80000",
                    "stderr": "",
                    "timeout": False,
                }
            if args == ["vcgencmd", "measure_temp"]:
                return {
                    "available": True,
                    "ok": True,
                    "returncode": 0,
                    "stdout": "temp=59.1'C",
                    "stderr": "",
                    "timeout": False,
                }
            if args == ["vcgencmd", "measure_volts"]:
                return {
                    "available": True,
                    "ok": True,
                    "returncode": 0,
                    "stdout": "volt=1.3450V",
                    "stderr": "",
                    "timeout": False,
                }
            raise AssertionError(args)

        with patch.object(field_diagnostics.shutil, "which", return_value="/usr/bin/vcgencmd"), \
                patch.object(field_diagnostics, "run_command", side_effect=fake_run_command):
            status = collect_power_status()

        self.assertEqual(status["status"], "warn")
        self.assertEqual(status["title"], "Güç ve sıcaklık")
        self.assertIn("sicaklik limitine", status["message"])
        self.assertNotIn("dusuk voltaj", status["message"])
        self.assertTrue(any("Sogutucu" in action for action in status["actions"]))

    def test_split_nmcli_escaped_colons(self):
        parts = split_nmcli_line(r"yes:Clinic\:Main:82:WPA2:wlan0")

        self.assertEqual(parts, ["yes", "Clinic:Main", "82", "WPA2", "wlan0"])

    def test_parse_route_get_output(self):
        parsed = parse_route_get_output("1.1.1.1 via 192.168.1.1 dev eth0 src 192.168.1.42 uid 1000")

        self.assertEqual(parsed["device"], "eth0")
        self.assertEqual(parsed["src"], "192.168.1.42")

    def test_collect_wifi_status_accepts_ethernet_internet(self):
        def fake_run_command(args, timeout=5):
            if args[:4] == ["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL,SECURITY,DEVICE"]:
                return {
                    "available": True,
                    "ok": True,
                    "returncode": 0,
                    "stdout": "no:Clinic:80:WPA2:wlan0",
                    "stderr": "",
                    "timeout": False,
                }
            if args == ["ip", "-4", "-o", "addr", "show", "dev", "wlan0"]:
                return {
                    "available": True,
                    "ok": False,
                    "returncode": 1,
                    "stdout": "",
                    "stderr": "",
                    "timeout": False,
                }
            if args == ["ip", "route", "get", "1.1.1.1"]:
                return {
                    "available": True,
                    "ok": True,
                    "returncode": 0,
                    "stdout": "1.1.1.1 via 192.168.1.1 dev eth0 src 192.168.1.42 uid 1000",
                    "stderr": "",
                    "timeout": False,
                }
            if args[:2] == ["getent", "hosts"]:
                return {
                    "available": True,
                    "ok": True,
                    "returncode": 0,
                    "stdout": "140.82.112.4 github.com",
                    "stderr": "",
                    "timeout": False,
                }
            if args and args[0] == "curl":
                return {
                    "available": True,
                    "ok": True,
                    "returncode": 0,
                    "stdout": "",
                    "stderr": "",
                    "timeout": False,
                }
            raise AssertionError(args)

        with patch.object(field_diagnostics, "run_command", side_effect=fake_run_command):
            status = collect_wifi_status()

        self.assertEqual(status["status"], "ok")
        self.assertEqual(status["details"]["connection_type"], "Ethernet")
        self.assertEqual(status["details"]["ip"], "192.168.1.42")
        self.assertTrue(status["details"]["internet_ok"])

    def test_collect_wifi_status_falls_back_when_tailscale_probe_fails(self):
        def fake_run_command(args, timeout=5):
            if args[:4] == ["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL,SECURITY,DEVICE"]:
                return {
                    "available": True,
                    "ok": True,
                    "returncode": 0,
                    "stdout": "yes:Clinic\\:Main:82:WPA2:wlan0",
                    "stderr": "",
                    "timeout": False,
                }
            if args == ["ip", "-4", "-o", "addr", "show", "dev", "wlan0"]:
                return {
                    "available": True,
                    "ok": True,
                    "returncode": 0,
                    "stdout": "2: wlan0 inet 192.168.1.23/24 brd 192.168.1.255 scope global wlan0",
                    "stderr": "",
                    "timeout": False,
                }
            if args == ["ip", "route", "get", "1.1.1.1"]:
                return {
                    "available": True,
                    "ok": True,
                    "returncode": 0,
                    "stdout": "1.1.1.1 via 192.168.1.1 dev wlan0 src 192.168.1.23 uid 1000",
                    "stderr": "",
                    "timeout": False,
                }
            if args[:2] == ["getent", "hosts"]:
                return {
                    "available": True,
                    "ok": True,
                    "returncode": 0,
                    "stdout": "34.117.59.81 login.tailscale.com",
                    "stderr": "",
                    "timeout": False,
                }
            if args and args[0] == "curl":
                target = args[-1]
                return {
                    "available": True,
                    "ok": target == "https://www.gstatic.com/generate_204",
                    "returncode": 0 if target == "https://www.gstatic.com/generate_204" else 22,
                    "stdout": "",
                    "stderr": "" if target == "https://www.gstatic.com/generate_204" else "HTTP request failed",
                    "timeout": False,
                }
            raise AssertionError(args)

        with patch.object(field_diagnostics, "run_command", side_effect=fake_run_command):
            status = collect_wifi_status()

        self.assertEqual(status["status"], "ok")
        self.assertEqual(status["details"]["ssid"], "Clinic:Main")
        self.assertTrue(status["details"]["internet_ok"])
        self.assertEqual(status["details"]["internet_probe"]["target"], "https://www.gstatic.com/generate_204")

    def test_parse_meminfo_snapshot(self):
        parsed = parse_meminfo_snapshot(
            "\n".join([
                "MemTotal:        1000000 kB",
                "MemAvailable:     250000 kB",
                "SwapTotal:        100000 kB",
                "SwapFree:          40000 kB",
            ])
        )

        self.assertEqual(parsed["MemTotal"], 1000000)
        self.assertEqual(parsed["MemAvailable"], 250000)
        self.assertEqual(parsed["SwapTotal"], 100000)
        self.assertEqual(parsed["SwapFree"], 40000)


if __name__ == "__main__":
    unittest.main()
