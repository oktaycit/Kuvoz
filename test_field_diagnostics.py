import unittest

from app.services.field_diagnostics import (
    decode_power_throttled,
    parse_meminfo_snapshot,
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

    def test_split_nmcli_escaped_colons(self):
        parts = split_nmcli_line(r"yes:Clinic\:Main:82:WPA2:wlan0")

        self.assertEqual(parts, ["yes", "Clinic:Main", "82", "WPA2", "wlan0"])

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
