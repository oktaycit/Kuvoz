"""HTTP route registration for Kuvoz web server."""

from __future__ import annotations

import datetime
import os
import time
from typing import Any, Callable

from flask import jsonify, request

from app.services.field_diagnostics import collect_field_diagnostics
from app.services.support_reports import (
    append_support_report,
    load_support_reports,
    update_support_report,
)


def register_http_routes(
    app,
    *,
    socketio,
    kuvoz_server,
    logger,
    docs_dir: str,
    get_help_docs_index: Callable[..., list[dict[str, Any]]],
    load_patient_records: Callable[[], list[dict[str, Any]]],
    save_patient_records: Callable[[list[dict[str, Any]]], None],
    merge_current_patient_record: Callable[[list[dict[str, Any]], dict[str, Any]], list[dict[str, Any]]],
    annotate_patient_activity: Callable[[list[dict[str, Any]], dict[str, Any]], tuple[list[dict[str, Any]], dict[str, Any]]],
    build_patient_id: Callable[[dict[str, Any]], str],
    build_readmission_patient_id: Callable[[dict[str, Any], list[dict[str, Any]]], str],
    support_reports_file: str,
) -> None:
    """Register the first extracted set of HTTP routes."""

    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    @app.route('/logs')
    def logs_page():
        return app.send_static_file('logs.html')

    @app.route('/ai-vitals')
    def ai_vitals_page():
        return app.send_static_file('ai_vitals.html')

    @app.route('/help')
    def help_page():
        return app.send_static_file('help.html')

    @app.route('/support')
    def support_page():
        return app.send_static_file('support.html')

    @app.route('/field-setup')
    def field_setup_page():
        return app.send_static_file('field_setup.html')

    def _build_support_report_context(page=None):
        try:
            runtime = kuvoz_server.snapshot_runtime_state()
        except Exception as exc:
            logger.debug(f"Support report snapshot failed: {exc}")
            runtime = {}

        try:
            system_status = kuvoz_server.get_effective_system_status()
        except Exception as exc:
            logger.debug(f"Support report system status failed: {exc}")
            system_status = {}

        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip and ',' in ip:
            ip = ip.split(',')[0].strip()

        device_context = {}
        try:
            device_context = dict(kuvoz_server.user_profile.get('device', {}))
        except Exception:
            device_context = {}

        return {
            "ip": ip,
            "user_agent": request.headers.get('User-Agent', ''),
            "page": page,
            "patient": getattr(kuvoz_server, "current_patient", {}) or {},
            "device": device_context,
            "snapshot": {
                "sensors": runtime.get("sensor_data", {}),
                "buttons": runtime.get("button_states", {}),
                "gpio_outputs": runtime.get("gpio_output_states", {}),
                "system": system_status,
            },
        }

    @app.route('/api/field-setup/status', methods=['GET'])
    def api_field_setup_status():
        try:
            return jsonify(collect_field_diagnostics())
        except Exception as exc:
            logger.error(f"Field setup diagnostics error: {exc}")
            return jsonify({
                "overall_status": "fail",
                "summary": f"Saha kontrolu calistirilamadi: {exc}",
                "checks": [],
            }), 500

    @app.route('/api/support-reports', methods=['GET', 'POST'])
    def api_support_reports():
        if request.method == 'POST':
            try:
                payload = request.get_json(silent=True) or {}
                context = _build_support_report_context(payload.get("page"))
                report = append_support_report(support_reports_file, payload, context=context)
                logger.info(
                    "Support report created: %s type=%s priority=%s",
                    report.get("id"),
                    report.get("type"),
                    report.get("priority"),
                )
                return jsonify({"success": True, "report": report}), 201
            except ValueError as exc:
                return jsonify({"success": False, "error": str(exc)}), 400
            except Exception as exc:
                logger.error(f"Support report create error: {exc}")
                return jsonify({"success": False, "error": "Bildirim kaydedilemedi"}), 500

        try:
            reports = load_support_reports(support_reports_file)
            status_filter = str(request.args.get("status") or "").strip().lower()
            type_filter = str(request.args.get("type") or "").strip().lower()
            if status_filter and status_filter != "all":
                reports = [report for report in reports if report.get("status") == status_filter]
            if type_filter and type_filter != "all":
                reports = [report for report in reports if report.get("type") == type_filter]

            try:
                limit = min(500, max(1, int(request.args.get("limit", 100))))
            except (TypeError, ValueError):
                limit = 100

            return jsonify({
                "success": True,
                "reports": reports[:limit],
                "count": len(reports),
            })
        except Exception as exc:
            logger.error(f"Support reports read error: {exc}")
            return jsonify({"success": False, "error": "Bildirimler okunamadı"}), 500

    @app.route('/api/support-reports/<report_id>', methods=['PATCH'])
    def api_update_support_report(report_id):
        try:
            payload = request.get_json(silent=True) or {}
            report = update_support_report(support_reports_file, report_id, payload)
            logger.info("Support report updated: %s status=%s", report_id, report.get("status"))
            return jsonify({"success": True, "report": report})
        except ValueError as exc:
            return jsonify({"success": False, "error": str(exc)}), 400
        except KeyError:
            return jsonify({"success": False, "error": "Bildirim bulunamadı"}), 404
        except Exception as exc:
            logger.error(f"Support report update error ({report_id}): {exc}")
            return jsonify({"success": False, "error": "Bildirim güncellenemedi"}), 500

    @app.route('/api/help/docs', methods=['GET'])
    def api_help_docs():
        help_lang = request.args.get('lang')
        return jsonify({"docs": get_help_docs_index(help_lang)})

    @app.route('/api/help/docs/<doc_id>', methods=['GET'])
    def api_help_doc_content(doc_id):
        help_lang = request.args.get('lang')
        docs = {d["id"]: d for d in get_help_docs_index(help_lang)}
        item = docs.get(doc_id)
        if not item:
            return jsonify({"error": "Document not found"}), 404

        safe_filename = item["filename"]
        docs_root = os.path.realpath(docs_dir)
        full_path = os.path.realpath(os.path.join(docs_dir, safe_filename))
        if not full_path.startswith(docs_root + os.sep):
            return jsonify({"error": "Invalid document path"}), 400
        if not os.path.isfile(full_path):
            return jsonify({"error": "Document file missing"}), 404

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            return jsonify({
                "id": item["id"],
                "title": item["title"],
                "content": content
            })
        except Exception as exc:
            logger.error(f"Help doc read error ({safe_filename}): {exc}")
            return jsonify({"error": "Document read error"}), 500

    @app.route('/api/status')
    def get_status():
        ai_health = {}
        if hasattr(kuvoz_server, 'get_ai_health_status'):
            try:
                ai_health = kuvoz_server.get_ai_health_status() or {}
            except Exception as exc:
                logger.debug(f"AI health read failed for /api/status: {exc}")

        current_patient = kuvoz_server.current_patient
        if isinstance(current_patient, dict) and current_patient.get('discharged', False):
            current_patient = {}

        return jsonify({
            'sensors': kuvoz_server.sensor_data,
            'buttons': kuvoz_server.button_states,
            'sliders': kuvoz_server.get_effective_slider_values(),
            'gpio_outputs': kuvoz_server.gpio_output_states,
            'timers': kuvoz_server.get_timer_data(),
            'system': kuvoz_server.get_effective_system_status(),
            'ai_health': ai_health,
            'system_settings': kuvoz_server.system_settings,
            'care_settings': kuvoz_server.get_care_status(),
            'current_patient': current_patient,
            'timestamp': time.time()
        })

    @app.route('/api/patients', methods=['GET'])
    def get_patients():
        try:
            patients = load_patient_records()
            patients = merge_current_patient_record(patients, kuvoz_server.current_patient)
            patients, activity = annotate_patient_activity(patients, kuvoz_server.current_patient)
            return jsonify({'success': True, 'patients': patients, **activity})
        except Exception as exc:
            logger.error(f"Error loading patients: {exc}")
            return jsonify({'success': False, 'error': str(exc)}), 500

    @app.route('/api/patients', methods=['POST'])
    def save_patient_api():
        try:
            data = request.json
            if not data:
                return jsonify({'success': False, 'error': 'Geçersiz veri'}), 400

            patients = load_patient_records()
            readmission_of = str(data.get('readmissionOf') or '').strip()
            if readmission_of:
                patient_id = build_readmission_patient_id(data, patients)
                data['readmissionOf'] = readmission_of
                data['readmissionAt'] = datetime.datetime.now().isoformat()
            else:
                patient_id = build_patient_id(data)
            data['id'] = patient_id
            data['savedAt'] = datetime.datetime.now().isoformat()

            existing_index = None
            existing_patient = None
            for i, patient in enumerate(patients):
                if patient.get('id') == patient_id:
                    existing_index = i
                    existing_patient = patient
                    break

            existing_is_discharged = bool(existing_patient and existing_patient.get('discharged', False))
            if existing_is_discharged and not data.get('reactivate', False):
                data = {**existing_patient, **data}
                data['discharged'] = True
            else:
                data['discharged'] = bool(data.get('discharged', False))

            if existing_index is not None:
                patients[existing_index] = data
                logger.info(f"Patient updated: {data.get('name')}")
            else:
                patients.insert(0, data)
                logger.info(f"New patient saved: {data.get('name')}")

            patients = merge_current_patient_record(patients, data)[:50]
            save_patient_records(patients)

            if not data.get('discharged', False):
                kuvoz_server.current_patient = dict(data)
                kuvoz_server.update_patient_context(data)
                kuvoz_server.save_settings()
            else:
                logger.info(f"Discharged patient record updated without changing active patient: {data.get('name')}")
            return jsonify({'success': True, 'patient': data})
        except Exception as exc:
            logger.error(f"Error saving patient: {exc}")
            return jsonify({'success': False, 'error': str(exc)}), 500

    @app.route('/api/patients/<patient_id>', methods=['DELETE'])
    def delete_patient_api(patient_id):
        try:
            patients = load_patient_records()
            new_patients = [patient for patient in patients if patient.get('id') != patient_id]

            current_matches = kuvoz_server.current_patient.get('id') == patient_id
            if len(new_patients) == len(patients) and not current_matches:
                return jsonify({'success': False, 'error': 'Hasta bulunamadı'}), 404

            save_patient_records(new_patients)

            if current_matches:
                kuvoz_server.current_patient = {}
                kuvoz_server.patient_context = {
                    'name': '',
                    'species': '',
                    'breed': '',
                    'age': '',
                    'weight': ''
                }
                kuvoz_server.care_settings['mode'] = 'manual'
                kuvoz_server.save_settings()

            return jsonify({'success': True})
        except Exception as exc:
            logger.error(f"Error deleting patient: {exc}")
            return jsonify({'success': False, 'error': str(exc)}), 500

    @app.route('/api/patients/<patient_id>/discharge', methods=['POST'])
    def discharge_patient_api(patient_id):
        try:
            data = request.json
            patients = merge_current_patient_record(load_patient_records(), kuvoz_server.current_patient)

            patient_index = None
            for i, patient in enumerate(patients):
                if patient.get('id') == patient_id:
                    patient_index = i
                    break

            if patient_index is None:
                return jsonify({'success': False, 'error': 'Hasta bulunamadı'}), 404

            patients[patient_index]['discharged'] = True
            patients[patient_index]['dischargeDate'] = data.get('dischargeDate')
            patients[patient_index]['dischargeTime'] = data.get('dischargeTime')
            patients[patient_index]['dischargeNotes'] = data.get('dischargeNotes')
            patients[patient_index]['dischargeStatus'] = data.get('dischargeStatus')
            patients[patient_index]['dischargedAt'] = datetime.datetime.now().isoformat()

            save_patient_records(patients)
            logger.info(f"Patient discharged: {patients[patient_index].get('name')}")

            discharged_current_patient = False
            if kuvoz_server.current_patient.get('id') == patient_id:
                discharged_current_patient = True

            active_patients = [patient for patient in patients if not patient.get('discharged', False)]
            if discharged_current_patient or len(active_patients) == 0:
                with kuvoz_server.state_lock:
                    kuvoz_server.care_settings['mode'] = 'manual'
                    kuvoz_server.patient_context = {
                        'name': '',
                        'species': '',
                        'breed': '',
                        'age': '',
                        'weight': ''
                    }
                    kuvoz_server.current_patient = {}
                    kuvoz_server.slider_values['sld3'] = 25.0
                    kuvoz_server.slider_values['sld2'] = 65
                    kuvoz_server.slider_values['sld12'] = 25.0
                kuvoz_server.save_settings()
                logger.info("🩺 Active patient discharged - switched to manual care mode, sliders reset to defaults")
                socketio.emit('care_settings_update', {
                    'care_settings': kuvoz_server.get_care_status(),
                    'sliders': kuvoz_server.get_effective_slider_values()
                })
            else:
                kuvoz_server.save_settings()

            return jsonify({'success': True, 'patient': patients[patient_index]})
        except Exception as exc:
            logger.error(f"Error discharging patient: {exc}")
            return jsonify({'success': False, 'error': str(exc)}), 500
