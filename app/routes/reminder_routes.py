"""Clinical reminder API, independent of sensor and GPIO control."""
import threading
from flask import jsonify, request
from app.services.reminders import ReminderStore


def register_reminder_routes(app, *, path, get_patient, logger):
    # Load lazily so a storage failure cannot prevent incubator control startup.
    store = None
    store_lock = threading.Lock()

    def get_store():
        nonlocal store
        with store_lock:
            if store is None:
                store = ReminderStore(path)
            return store

    @app.route('/api/reminders', methods=['GET', 'POST'])
    def reminders():
        try:
            service = get_store()
            if request.method == 'POST':
                row = service.create(request.get_json(silent=True), get_patient())
                return jsonify(success=True, reminder=row), 201
            return jsonify(success=True, reminders=service.snapshot())
        except ValueError as exc:
            if str(exc) in ('invalid_request', 'invalid_time', 'invalid_interval', 'limit_reached'):
                return jsonify(success=False, error=str(exc)), 400
            logger.exception('Reminder storage error')
            return jsonify(success=False, error='storage_error'), 503
        except Exception:
            logger.exception('Reminder storage error')
            return jsonify(success=False, error='storage_error'), 503

    @app.route('/api/reminders/<reminder_id>', methods=['PATCH'])
    def reminder_action(reminder_id):
        try:
            payload = request.get_json(silent=True)
            if not isinstance(payload, dict):
                raise ValueError('invalid_request')
            row = get_store().action(reminder_id, payload.get('action'))
            return jsonify(success=True, reminder=row)
        except KeyError:
            return jsonify(success=False, error='not_found'), 404
        except ValueError as exc:
            if str(exc) in ('invalid_request', 'not_due'):
                return jsonify(success=False, error=str(exc)), 400
            logger.exception('Reminder storage error')
            return jsonify(success=False, error='storage_error'), 503
        except Exception:
            logger.exception('Reminder update error')
            return jsonify(success=False, error='storage_error'), 503
