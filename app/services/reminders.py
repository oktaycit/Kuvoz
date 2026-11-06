"""Persistent clinical reminders; scheduling never operates medical equipment."""
import copy
import json
import math
import os
import tempfile
import threading
import time
import uuid
from pathlib import Path


class ReminderStore:
    def __init__(self, path, clock=time.time):
        self.path = Path(path)
        self.clock = clock
        self.lock = threading.RLock()
        # A corrupt file must remain visible as an error, never silently reset.
        self.rows = json.loads(self.path.read_text()) if self.path.exists() else []
        if not isinstance(self.rows, list) or any(
            not isinstance(row, dict)
            or not {'id', 'kind', 'title', 'status', 'due_at', 'repeat_minutes'} <= row.keys()
            or row['status'] not in ('pending', 'acknowledged', 'cancelled')
            or row['kind'] not in ('treatment', 'medication')
            or not isinstance(row['due_at'], (int, float)) or not math.isfinite(row['due_at'])
            or not isinstance(row['repeat_minutes'], (int, float)) or not math.isfinite(row['repeat_minutes'])
            for row in self.rows
        ):
            raise ValueError('Invalid reminder storage')

    def _save(self, rows):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=self.path.parent, prefix='.reminders-')
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(rows, stream, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        self.rows = rows

    def snapshot(self):
        with self.lock:
            now = self.clock()
            return [dict(copy.deepcopy(row), due=row['status'] == 'pending' and row['due_at'] <= now)
                    for row in self.rows]

    def create(self, payload, patient=None):
        if not isinstance(payload, dict):
            raise ValueError('invalid_request')
        kind = payload.get('kind')
        title = str(payload.get('title') or '').strip()
        if kind not in ('treatment', 'medication') or not title or len(title) > 160:
            raise ValueError('invalid_request')
        try:
            due = float(payload['due_at'])
            repeat = float(payload.get('repeat_minutes', 0))
        except (KeyError, TypeError, ValueError):
            raise ValueError('invalid_request')
        now = self.clock()
        if not math.isfinite(due) or not now < due <= now + 366 * 86400:
            raise ValueError('invalid_time')
        if not math.isfinite(repeat) or (repeat != 0 and not 1 <= repeat <= 525600):
            raise ValueError('invalid_interval')
        patient = patient if isinstance(patient, dict) else {}
        row = dict(id=uuid.uuid4().hex, kind=kind, title=title, due_at=due,
                   repeat_minutes=repeat, status='pending', created_at=now,
                   patient_id=str(patient.get('id') or patient.get('patient_id') or ''),
                   patient_name=str(patient.get('name') or patient.get('patient_name') or '')[:160])
        with self.lock:
            if sum(r['status'] == 'pending' for r in self.rows) >= 100:
                raise ValueError('limit_reached')
            pending = [r for r in self.rows if r['status'] == 'pending']
            history = [r for r in self.rows if r['status'] != 'pending'][-899:]
            self._save(history + pending + [row])
        return copy.deepcopy(row)

    def action(self, reminder_id, action):
        if action not in ('acknowledge', 'cancel', 'snooze'):
            raise ValueError('invalid_request')
        with self.lock:
            rows = copy.deepcopy(self.rows)
            row = next((r for r in rows if r['id'] == reminder_id), None)
            if row is None:
                raise KeyError(reminder_id)
            if row['status'] != 'pending':
                return copy.deepcopy(row)  # Idempotent across multiple clients.
            now = self.clock()
            if action != 'cancel' and row['due_at'] > now:
                raise ValueError('not_due')
            if action == 'snooze':
                row['due_at'] = now + 300
            elif action == 'acknowledge':
                row['acknowledged_at'] = now
                if row['repeat_minutes']:
                    # Schedule from acknowledgement; do not replay missed doses.
                    row['due_at'] = now + row['repeat_minutes'] * 60
                else:
                    row['status'] = 'acknowledged'
            else:
                row['status'] = 'cancelled'
            self._save(rows)
            return copy.deepcopy(row)
