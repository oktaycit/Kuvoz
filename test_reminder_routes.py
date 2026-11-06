import logging
import tempfile
import time
import unittest
from pathlib import Path
from flask import Flask
from app.routes.reminder_routes import register_reminder_routes


class ReminderRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'reminders.json'
        app = Flask(__name__)
        register_reminder_routes(app, path=self.path, get_patient=lambda: {'name': 'Mavi'}, logger=logging.getLogger('test'))
        self.client = app.test_client()

    def test_create_list_cancel_and_validation(self):
        response = self.client.post('/api/reminders', json={'kind': 'treatment', 'title': 'Kontrol', 'due_at': time.time()+120})
        self.assertEqual(response.status_code, 201)
        row = response.json['reminder']
        self.assertEqual(row['patient_name'], 'Mavi')
        self.assertEqual(len(self.client.get('/api/reminders').json['reminders']), 1)
        self.assertEqual(self.client.patch('/api/reminders/'+row['id'], json={'action':'cancel'}).status_code, 200)
        self.assertEqual(self.client.patch('/api/reminders/missing', json={'action':'cancel'}).status_code, 404)
        self.assertEqual(self.client.post('/api/reminders', json=[]).status_code, 400)
        self.assertEqual(self.client.patch('/api/reminders/'+row['id'], json=[]).status_code, 400)

    def test_corrupt_file_does_not_break_app_or_reset_data(self):
        self.path.write_text('broken')
        logging.disable(logging.CRITICAL)
        try:
            self.assertEqual(self.client.get('/api/reminders').status_code, 503)
        finally:
            logging.disable(logging.NOTSET)
        self.assertEqual(self.path.read_text(), 'broken')
