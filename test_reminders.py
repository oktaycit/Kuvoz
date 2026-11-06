import json
import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from app.services.reminders import ReminderStore


class ReminderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'reminders.json'
        self.now = 1000
        self.store = ReminderStore(self.path, lambda: self.now)

    def create(self, **kwargs):
        return self.store.create(dict(kind='medication', title='Test', due_at=1060, **kwargs), {'id': 'p1', 'name': 'Mavi'})

    def test_overdue_survives_restart_and_remains_until_acknowledged(self):
        row = self.create()
        self.now = 1200
        restarted = ReminderStore(self.path, lambda: self.now)
        self.assertTrue(restarted.snapshot()[0]['due'])
        self.assertEqual(restarted.snapshot()[0]['patient_name'], 'Mavi')
        restarted.action(row['id'], 'acknowledge')
        self.assertFalse(ReminderStore(self.path, lambda: self.now).snapshot()[0]['due'])

    def test_repeating_uses_acknowledgement_not_missed_doses(self):
        row = self.create(repeat_minutes=60)
        self.now = 10000
        self.store.action(row['id'], 'acknowledge')
        self.assertEqual(self.store.snapshot()[0]['due_at'], 13600)
        with self.assertRaises(ValueError):
            self.store.action(row['id'], 'acknowledge')
        self.assertEqual(self.store.snapshot()[0]['due_at'], 13600)

    def test_snooze_cancel_and_duplicate_ack(self):
        row = self.create()
        self.now = 1060
        self.store.action(row['id'], 'snooze')
        self.assertEqual(self.store.snapshot()[0]['due_at'], 1360)
        self.store.action(row['id'], 'cancel')
        self.store.action(row['id'], 'acknowledge')
        self.assertEqual(self.store.snapshot()[0]['status'], 'cancelled')

    def test_invalid_input_is_rejected(self):
        for payload in (None, [], {}, {'kind': 'medication', 'title': 'x', 'due_at': float('nan')},
                        {'kind': 'treatment', 'title': 'x', 'due_at': 900},
                        {'kind': 'treatment', 'title': 'x', 'due_at': 1100, 'repeat_minutes': -1}):
            with self.assertRaises(ValueError):
                self.store.create(payload)
        self.assertFalse(self.path.exists())

    def test_concurrent_creates_preserve_all_rows(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda _: self.create(), range(30)))
        self.assertEqual(len(ReminderStore(self.path).snapshot()), 30)

    def test_storage_failure_does_not_commit_in_memory(self):
        row = self.create()
        self.path.unlink()
        self.path.mkdir()
        self.now = 1100
        with self.assertRaises(OSError):
            self.store.action(row['id'], 'acknowledge')
        self.assertTrue(self.store.snapshot()[0]['due'])

    def test_corrupt_storage_is_not_silently_overwritten(self):
        self.path.write_text('broken')
        with self.assertRaises(json.JSONDecodeError):
            ReminderStore(self.path)
        self.assertEqual(self.path.read_text(), 'broken')


if __name__ == '__main__':
    unittest.main()
