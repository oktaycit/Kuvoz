"""Check complete new dictionaries and runtime interpolation compatibility."""
import json
import re
import unittest
from pathlib import Path


def flatten(data, prefix=''):
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result.update(flatten(value, prefix + key + '.'))
        else:
            result[prefix + key] = value
    return result


class TranslationTests(unittest.TestCase):
    def test_new_languages_have_all_keys_and_placeholders(self):
        root = Path(__file__).parent / 'web' / 'translations'
        base = flatten(json.loads((root / 'en.json').read_text()))
        for lang in ('es', 'pt', 'ru', 'ko', 'zh', 'ja', 'ar'):
            with self.subTest(language=lang):
                data = flatten(json.loads((root / (lang + '.json')).read_text()))
                self.assertEqual(set(base), set(data))
                for key, value in base.items():
                    self.assertIsInstance(data[key], str)
                    self.assertTrue(data[key].strip())
                    self.assertEqual(set(re.findall(r'\{[^{}]+\}', value)),
                                     set(re.findall(r'\{[^{}]+\}', data[key])), key)

    def test_reminders_are_translated_in_every_language(self):
        root = Path(__file__).parent / 'web' / 'translations'
        expected = json.loads((root / 'en.json').read_text())['reminders']
        for lang in ('tr', 'en', 'de', 'es', 'pt', 'ru', 'ko', 'zh', 'ja', 'ar'):
            with self.subTest(language=lang):
                data = json.loads((root / (lang + '.json')).read_text())['reminders']
                self.assertEqual(set(data), set(expected))
