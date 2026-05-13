import unittest

from app.services.ai_settings import (
    normalize_ai_enabled_value,
    resolve_ai_enabled_preference,
)


class AISettingsTests(unittest.TestCase):
    def test_normalize_ai_enabled_value_handles_string_false(self):
        self.assertFalse(normalize_ai_enabled_value("false"))
        self.assertFalse(normalize_ai_enabled_value("0"))
        self.assertFalse(normalize_ai_enabled_value("off"))
        self.assertTrue(normalize_ai_enabled_value("true"))
        self.assertTrue(normalize_ai_enabled_value("1"))
        self.assertTrue(normalize_ai_enabled_value("on"))

    def test_root_ai_enabled_is_canonical_when_system_setting_conflicts(self):
        enabled, source, conflict = resolve_ai_enabled_preference(
            {
                "ai_enabled": False,
                "system_settings": {"ai_enabled": True},
            }
        )

        self.assertFalse(enabled)
        self.assertEqual(source, "ai_enabled")
        self.assertTrue(conflict)

    def test_system_ai_enabled_used_for_legacy_files_without_root_key(self):
        enabled, source, conflict = resolve_ai_enabled_preference(
            {
                "system_settings": {"ai_enabled": "true"},
            }
        )

        self.assertTrue(enabled)
        self.assertEqual(source, "system_settings.ai_enabled")
        self.assertFalse(conflict)

    def test_default_used_when_no_ai_key_exists(self):
        enabled, source, conflict = resolve_ai_enabled_preference({}, default=True)

        self.assertTrue(enabled)
        self.assertEqual(source, "default")
        self.assertFalse(conflict)


if __name__ == "__main__":
    unittest.main()
