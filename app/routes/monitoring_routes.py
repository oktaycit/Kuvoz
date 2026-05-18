"""Monitoring/logging HTTP route registration."""

from __future__ import annotations

import datetime
import os

from flask import jsonify, request, send_file, send_from_directory

from app.services.patient_report import (
    ReportGenerationUnavailable,
    generate_patient_report_pdf,
    safe_report_filename,
)


def register_monitoring_routes(
    app,
    *,
    kuvoz_server,
    logger,
    ai_vitals_logger_cls,
    behavior_logger_cls,
    script_dir: str,
    settings_file: str,
):
    """Register monitoring, logging and asset routes."""

    @app.route('/api/ai-alerts', methods=['GET'])
    def get_ai_alerts():
        try:
            from ai_alert_summary import AIAlertSummary

            hours = max(1, min(int(request.args.get('hours', 24)), 720))
            patient_id = request.args.get('patient_id', None)
            min_confidence = float(request.args.get('min_confidence', 0.5))
            min_confidence = max(0.0, min(1.0, min_confidence))

            analyzer = AIAlertSummary(db_path='data/ai_vitals.db')
            summary = analyzer.get_quick_summary(
                hours=hours,
                patient_id=patient_id,
                min_confidence=min_confidence,
            )
            return jsonify(summary)
        except ImportError as exc:
            logger.error(f"AI Alert Summary import error: {exc}")
            return jsonify({'error': 'AI alert module not available'}), 503
        except Exception as exc:
            logger.error(f"Error fetching AI alerts: {exc}")
            return jsonify({'error': str(exc)}), 500

    @app.route('/api/behaviors', methods=['GET', 'POST', 'DELETE'])
    def get_behaviors():
        behavior_logger = getattr(kuvoz_server, 'behavior_logger', None)
        if not behavior_logger:
            return jsonify({'error': 'Behavior logging not available', 'data': []}), 503

        try:
            if request.method == 'DELETE':
                payload = request.get_json(silent=True) or {}
                clear_reason = str(payload.get('reason') or 'manual').strip() or 'manual'
                success = behavior_logger.clear_all_data(reason=clear_reason, context=payload)
                if success:
                    return jsonify({
                        'success': True,
                        'message': 'All behavior logs cleared',
                        'meta': {'cleared_reason': clear_reason}
                    })
                return jsonify({'success': False, 'error': 'Database error'}), 500

            if request.method == 'POST':
                payload = request.get_json(silent=True) or {}
                behavior_type = str(payload.get('behavior_type') or '').strip()
                if behavior_type not in behavior_logger_cls.BEHAVIOR_TYPES:
                    return jsonify({'success': False, 'message': 'Gecersiz davranis turu'}), 400

                patient_context = kuvoz_server.normalize_patient_record(payload.get('patient_context'))
                if not patient_context:
                    patient_context = kuvoz_server.get_ai_logging_patient_context()

                duration = payload.get('duration')
                intensity = payload.get('intensity')
                behavior_subtype = str(payload.get('behavior_subtype') or '').strip() or None
                notes = str(payload.get('notes') or '').strip() or None
                metadata = payload.get('metadata') if isinstance(payload.get('metadata'), dict) else None

                try:
                    duration_value = int(duration) if duration not in (None, '') else None
                    intensity_value = float(intensity) if intensity not in (None, '') else None
                except (TypeError, ValueError):
                    return jsonify({'success': False, 'message': 'Sure veya yogunluk gecersiz'}), 400

                logged = behavior_logger.log_behavior(
                    behavior_type,
                    patient_context=patient_context,
                    duration=duration_value,
                    intensity=intensity_value,
                    notes=notes,
                    metadata=metadata,
                    behavior_subtype=behavior_subtype,
                )
                if not logged:
                    return jsonify({'success': False, 'message': 'Davranis kaydi sinira takildi veya yazilamadi'}), 409

                latest_behavior = behavior_logger.get_latest_behavior(
                    behavior_type=behavior_type,
                    patient_id=patient_context.get('id') if patient_context else None,
                )
                if latest_behavior:
                    kuvoz_server._emit_behavior_update(latest_behavior)

                return jsonify({'success': True, 'data': latest_behavior})

            try:
                limit = max(1, min(int(request.args.get('limit', 1000)), 5000))
                hours = max(1, min(int(request.args.get('hours', 168)), 720))
            except ValueError:
                return jsonify({'error': 'Gecersiz limit veya zaman araligi', 'data': []}), 400

            patient_id = str(request.args.get('patient_id', 'all') or 'all').strip() or 'all'
            if patient_id == 'current':
                current_pt = kuvoz_server.get_ai_logging_patient_context()
                patient_id = current_pt.get('id') if current_pt else 'all'

            behavior_types = []
            if request.args.get('behavior_type'):
                behavior_types = [
                    str(item).strip()
                    for item in request.args.get('behavior_type', '').split(',')
                    if str(item).strip()
                ]

            start_date = str(request.args.get('start_date') or '').strip()
            end_date = str(request.args.get('end_date') or '').strip()

            end_time = datetime.datetime.now()
            start_time = end_time - datetime.timedelta(hours=hours)

            if start_date:
                try:
                    start_day = datetime.date.fromisoformat(start_date)
                    start_time = datetime.datetime.combine(start_day, datetime.time.min)
                    if end_date:
                        end_day = datetime.date.fromisoformat(end_date)
                        end_time = datetime.datetime.combine(end_day + datetime.timedelta(days=1), datetime.time.min)
                    else:
                        end_time = start_time + datetime.timedelta(days=1)
                except ValueError:
                    return jsonify({'error': 'Gecersiz tarih formati', 'data': []}), 400

            readings = behavior_logger.get_behaviors(
                start_time=start_time,
                end_time=end_time,
                patient_id=None if patient_id == 'all' else patient_id,
                behavior_types=behavior_types or None,
                limit=limit,
            )
            summary = behavior_logger.get_behavior_summary(
                start_time=start_time,
                end_time=end_time,
                patient_id=None if patient_id == 'all' else patient_id,
            )
            stats = behavior_logger.get_behavior_statistics(
                start_time=start_time,
                end_time=end_time,
                patient_id=None if patient_id == 'all' else patient_id,
            )
            latest = behavior_logger.get_latest_behavior(
                patient_id=None if patient_id == 'all' else patient_id
            )
            patients = behavior_logger.get_patient_summaries(
                start_time=start_time,
                end_time=end_time,
            )

            return jsonify({
                'data': readings,
                'meta': {
                    'limit': limit,
                    'hours': hours,
                    'returned_records': len(readings),
                    'total_records': behavior_logger.get_record_count(
                        patient_id=None if patient_id == 'all' else patient_id
                    ),
                    'summary': summary,
                    'statistics': stats,
                    'latest': latest,
                    'patients': patients,
                    'current_patient': kuvoz_server.current_patient,
                    'logging_enabled': bool(kuvoz_server.system_settings.get('logging_enabled', True)),
                }
            })
        except Exception as exc:
            logger.error(f"Error fetching behavior logs: {exc}", exc_info=True)
            return jsonify({'error': str(exc), 'data': []}), 500

    @app.route('/api/ai-vitals', methods=['GET', 'DELETE'])
    def get_ai_vitals():
        try:
            if ai_vitals_logger_cls is None:
                raise ImportError('AI vitals logger unavailable')

            ai_vitals_logger = ai_vitals_logger_cls(db_path='data/ai_vitals.db')

            if request.method == 'DELETE':
                try:
                    payload = request.get_json(silent=True) or {}
                    clear_reason = str(payload.get('reason') or 'manual').strip() or 'manual'
                    success = ai_vitals_logger.clear_all_data(reason=clear_reason, context=payload)
                    if success:
                        return jsonify({
                            'success': True,
                            'message': 'All AI vital logs cleared',
                            'meta': {'cleared_reason': clear_reason}
                        })
                    return jsonify({'success': False, 'error': 'Database error'}), 500
                except Exception as exc:
                    logger.error(f"Error clearing AI vital logs: {exc}")
                    return jsonify({'success': False, 'error': str(exc)}), 500

            limit = max(1, min(int(request.args.get('limit', 2500)), 6000))
            hours = max(1, min(int(request.args.get('hours', 24)), 720))
            patient_id = request.args.get('patient_id', 'all')

            if patient_id == 'current':
                current_pt = kuvoz_server.get_ai_logging_patient_context()
                patient_id = current_pt.get('id') if current_pt else 'all'

            end_time = datetime.datetime.now()
            start_time = end_time - datetime.timedelta(hours=hours)

            readings = ai_vitals_logger.get_readings(
                start_time=start_time,
                end_time=end_time,
                patient_id=None if patient_id == 'all' else patient_id,
                limit=limit
            )
            stats = ai_vitals_logger.get_statistics(
                start_time=start_time,
                end_time=end_time,
                patient_id=None if patient_id == 'all' else patient_id
            )
            status_breakdown = ai_vitals_logger.get_status_breakdown(
                start_time=start_time,
                end_time=end_time,
                patient_id=None if patient_id == 'all' else patient_id
            )
            latest = ai_vitals_logger.get_latest_reading(
                patient_id=None if patient_id == 'all' else patient_id
            )
            patients = ai_vitals_logger.get_patient_summaries(
                start_time=start_time,
                end_time=end_time
            )

            return jsonify({
                'data': readings,
                'meta': {
                    'hours': hours,
                    'limit': limit,
                    'returned_records': len(readings),
                    'total_records': ai_vitals_logger.get_record_count(),
                    'statistics': stats,
                    'status_breakdown': status_breakdown,
                    'latest': latest,
                    'patients': patients,
                    'current_patient': kuvoz_server.current_patient,
                    'logging_enabled': bool(kuvoz_server.system_settings.get('logging_enabled', True)),
                    'ai_enabled': getattr(kuvoz_server, 'ai_enabled', False),
                }
            })
        except ImportError as exc:
            logger.error(f"AI Vitals Logger import error: {exc}")
            return jsonify({'error': 'AI vitals module not available', 'data': []}), 503
        except Exception as exc:
            logger.error(f"Error fetching AI vitals: {exc}", exc_info=True)
            return jsonify({'error': str(exc), 'data': []}), 500

    @app.route('/api/logs', methods=['GET', 'DELETE'])
    def get_logs():
        if not kuvoz_server.sensor_logger:
            return jsonify({'error': 'Logging not available', 'data': []})

        if request.method == 'DELETE':
            try:
                payload = request.get_json(silent=True) or {}
                clear_reason = str(payload.get('reason') or request.args.get('reason') or 'manual').strip() or 'manual'
                success = kuvoz_server.sensor_logger.clear_all_data(reason=clear_reason, context=payload)
                if success:
                    return jsonify({
                        'success': True,
                        'message': 'All logs cleared',
                        'meta': {'cleared_reason': clear_reason}
                    })
                return jsonify({'success': False, 'error': 'Database error'}), 500
            except Exception as exc:
                logger.error(f"Error clearing logs: {exc}")
                return jsonify({'success': False, 'error': str(exc)}), 500

        try:
            limit = max(1, min(int(request.args.get('limit', 100)), 5000))
            days = max((1.0 / 24.0), min(float(request.args.get('days', 1.0)), 365.0))
            start_time = datetime.datetime.now() - datetime.timedelta(days=days)
            readings = kuvoz_server.sensor_logger.get_readings(start_time=start_time, limit=limit)
            stats = kuvoz_server.sensor_logger.get_statistics(hours=max(1, int(days * 24)))

            return jsonify({
                'data': readings,
                'meta': {
                    'days': days,
                    'limit': limit,
                    'returned_records': len(readings),
                    'total_records': kuvoz_server.sensor_logger.get_record_count(),
                    'stats': stats,
                    'current_patient': kuvoz_server.current_patient,
                    'capabilities': kuvoz_server.get_effective_system_status(),
                    'sliders': kuvoz_server.get_effective_slider_values(),
                    'buttons': kuvoz_server.button_states,
                    'care_settings': kuvoz_server.get_care_status(),
                    'system_settings': kuvoz_server.system_settings,
                }
            })
        except Exception as exc:
            logger.error(f"Error fetching logs: {exc}")
            return jsonify({'error': str(exc), 'data': []})

    @app.route('/api/reports/patient.pdf', methods=['GET'])
    def download_patient_report_pdf():
        """Generate a downloadable patient monitoring PDF for the selected log range."""
        try:
            days = max((1.0 / 24.0), min(float(request.args.get('days', 7.0)), 90.0))
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'Geçersiz zaman aralığı'}), 400

        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(days=days)

        patient_id = str(request.args.get('patient_id', 'current') or 'current').strip() or 'current'
        patient_context = getattr(kuvoz_server, 'current_patient', {}) or {}
        if patient_id == 'current':
            patient_id = patient_context.get('id') or 'all'

        query_patient_id = None if patient_id == 'all' else patient_id

        try:
            sensor_rows = []
            if getattr(kuvoz_server, 'sensor_logger', None):
                sensor_rows = kuvoz_server.sensor_logger.get_readings(
                    start_time=start_time,
                    end_time=end_time,
                    limit=12000,
                    patient_id=query_patient_id,
                    order='ASC',
                )

            ai_rows = []
            ai_vitals_logger = getattr(kuvoz_server, 'ai_vitals_logger', None)
            if not ai_vitals_logger and ai_vitals_logger_cls is not None:
                ai_vitals_logger = ai_vitals_logger_cls(db_path='data/ai_vitals.db')
            if ai_vitals_logger:
                ai_rows = ai_vitals_logger.get_readings(
                    start_time=start_time,
                    end_time=end_time,
                    patient_id=query_patient_id,
                    limit=12000,
                    order='ASC',
                )

            behavior_rows = []
            behavior_logger = getattr(kuvoz_server, 'behavior_logger', None)
            if behavior_logger:
                behavior_rows = behavior_logger.get_behaviors(
                    start_time=start_time,
                    end_time=end_time,
                    patient_id=query_patient_id,
                    limit=30000,
                    order='ASC',
                )

            if query_patient_id and not patient_context.get('id') == query_patient_id:
                patient_context = {
                    'id': query_patient_id,
                    'name': query_patient_id,
                }

            pdf_buffer = generate_patient_report_pdf(
                sensor_rows=sensor_rows,
                ai_rows=ai_rows,
                behavior_rows=behavior_rows,
                patient=patient_context,
                days=days,
                generated_at=end_time,
            )
            filename = safe_report_filename(patient_context, generated_at=end_time)
            logger.info(
                "Patient PDF report generated: patient=%s days=%s sensor=%s ai=%s behavior=%s",
                query_patient_id or 'all',
                days,
                len(sensor_rows),
                len(ai_rows),
                len(behavior_rows),
            )
            return send_file(
                pdf_buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename,
            )
        except ReportGenerationUnavailable as exc:
            logger.error(f"PDF report dependency missing: {exc}")
            return jsonify({
                'success': False,
                'error': 'PDF raporu için reportlab paketi kurulu değil. Kurulum: pip3 install reportlab',
            }), 503
        except Exception as exc:
            logger.error(f"Patient PDF report error: {exc}", exc_info=True)
            return jsonify({'success': False, 'error': 'PDF raporu oluşturulamadı'}), 500

    @app.route('/failure.dat')
    def download_settings_file():
        if os.path.exists(settings_file):
            return send_file(settings_file, as_attachment=True)
        return jsonify({'error': 'Settings file not found'}), 404

    @app.route('/resim/<path:filename>')
    def serve_resim(filename):
        return send_from_directory(os.path.join(script_dir, 'resim'), filename)
