"""Socket.IO settings/profile/patient route registration."""

from __future__ import annotations

import datetime
import time

from flask import request
from flask_socketio import emit


def register_settings_socket_routes(
    socketio,
    *,
    kuvoz_server,
    logger,
    gpio_available: bool,
    dht_available: bool,
    oxygen_available: bool,
    co2_available: bool,
    ai_available: bool,
    logging_available: bool,
    settings_file: str,
    get_local_ip,
    get_git_version_info,
    get_git_update_diagnostics,
    build_patient_id,
    patient_record_has_content,
):
    """Register settings/profile/patient socket handlers."""

    @socketio.on('get_settings')
    def handle_get_settings(data=None):
        try:
            settings_data = {
                'hardware': {
                    'gpio_available': gpio_available,
                    'cooling_available': gpio_available,
                },
                'sensors': {
                    'dht_available': dht_available,
                    'oxygen_available': kuvoz_server.oxygen_sensor_available,
                    'oxygen_library_available': oxygen_available,
                    'co2_available': kuvoz_server.co2_sensor_available,
                    'co2_library_available': co2_available,
                },
                'features': {
                    'ai_available': ai_available,
                    'logging_available': logging_available,
                },
                'settings': kuvoz_server.snapshot_runtime_state()['system_settings'],
            }
            emit('settings_response', settings_data)
            logger.info("Settings data sent to client")
        except Exception as exc:
            logger.error(f"Get settings error: {exc}")
            emit('error', {'message': f'Ayarlar yüklenemedi: {str(exc)}'})

    def handle_save_settings_logic(data):
        try:
            if data:
                with kuvoz_server.state_lock:
                    if 'sliders' in data:
                        kuvoz_server.slider_values.update(data['sliders'])
                        logger.info("Updated sliders from save_settings")

                    if 'buttons' in data:
                        kuvoz_server.button_states.update(data['buttons'])
                        logger.info("Updated buttons from save_settings")

                    if 'system_settings' in data:
                        sys_sett = data['system_settings'].copy()
                        for key in ['sliders', 'buttons', 'gpio_outputs', 'sensors']:
                            sys_sett.pop(key, None)
                        sys_sett.pop('soothing_audio_enabled', None)
                        sys_sett.pop('soothing_audio_mode', None)
                        if 'fan_output_mode' in sys_sett:
                            sys_sett['fan_output_mode'] = kuvoz_server.normalize_fan_output_mode(sys_sett['fan_output_mode'])
                        if 'fan_control_mode' in sys_sett:
                            sys_sett['fan_control_mode'] = kuvoz_server.normalize_fan_control_mode(sys_sett['fan_control_mode'])
                        if 'camera_transform' in sys_sett:
                            sys_sett['camera_transform'] = kuvoz_server.normalize_camera_transform(sys_sett['camera_transform'])
                        kuvoz_server.system_settings.update(sys_sett)
                        kuvoz_server.refresh_fan_output_mode()
                        kuvoz_server.sync_ai_system_settings()
                        logger.info("Updated system settings (filtered)")

                if 'care_settings' in data and isinstance(data['care_settings'], dict):
                    requested_mode = data['care_settings'].get('mode')
                    if requested_mode is not None:
                        ok, reason = kuvoz_server.set_care_mode(requested_mode)
                        if not ok:
                            logger.warning(f"Care mode change rejected: {reason}")
                            socketio.emit('care_settings_update', {
                                'care_settings': kuvoz_server.get_care_status(),
                                'sliders': kuvoz_server.get_effective_slider_values()
                            })
                            return False
                        logger.info(f"Updated care mode: {kuvoz_server.care_settings['mode']}")

                flat_keys = ['cooling_enabled', 'dht_enabled', 'oxygen_enabled', 'co2_enabled', 'ai_enabled', 'logging_enabled', 'fan_output_mode', 'fan_control_mode', 'screen_orientation', 'camera_transform']
                flat_settings = {key: data[key] for key in flat_keys if key in data}
                if flat_settings:
                    with kuvoz_server.state_lock:
                        if 'fan_output_mode' in flat_settings:
                            flat_settings['fan_output_mode'] = kuvoz_server.normalize_fan_output_mode(flat_settings['fan_output_mode'])
                        if 'fan_control_mode' in flat_settings:
                            flat_settings['fan_control_mode'] = kuvoz_server.normalize_fan_control_mode(flat_settings['fan_control_mode'])
                        if 'camera_transform' in flat_settings:
                            flat_settings['camera_transform'] = kuvoz_server.normalize_camera_transform(flat_settings['camera_transform'])
                        kuvoz_server.system_settings.update(flat_settings)
                        kuvoz_server.refresh_fan_output_mode()
                        kuvoz_server.sync_ai_system_settings()
                    logger.info(f"Updated system settings from flat structure: {list(flat_settings.keys())}")

                requested_ai_enabled = None
                if 'ai_enabled' in data:
                    requested_ai_enabled = bool(data['ai_enabled'])
                elif 'system_settings' in data and 'ai_enabled' in data['system_settings']:
                    requested_ai_enabled = bool(data['system_settings']['ai_enabled'])

                if requested_ai_enabled is not None:
                    if requested_ai_enabled != kuvoz_server.ai_enabled or (
                        requested_ai_enabled and not getattr(kuvoz_server.ai_manager, 'started', False)
                    ):
                        ok, message, health = kuvoz_server._set_ai_runtime_enabled(
                            requested_ai_enabled,
                            source='save_settings',
                        )
                        if not ok:
                            logger.warning(f"AI setting sync failed: {message}")
                            logger.debug("AI setting sync health: %s", health)
                    else:
                        kuvoz_server.ai_enabled = requested_ai_enabled

                kuvoz_server.apply_runtime_sensor_settings()

                if kuvoz_server.save_settings():
                    socketio.emit('settings_saved', {'message': 'Ayarlar başarıyla kaydedildi'})
                    socketio.emit(
                        'status_response',
                        kuvoz_server.build_status_payload(ai_available=ai_available),
                    )
                    socketio.emit('care_settings_update', {
                        'care_settings': kuvoz_server.get_care_status(),
                        'sliders': kuvoz_server.get_effective_slider_values()
                    })
                    logger.info(f"✅ Settings saved to {settings_file}")
                    if kuvoz_server.firebase_manager:
                        kuvoz_server.firebase_manager.sync_controls(kuvoz_server.button_states, kuvoz_server.slider_values)
                        logger.info("✅ Firebase controls synced after save")
                    return True

                socketio.emit('error', {'message': 'Ayarlar dosyaya yazılamadı'})
                return False

            if kuvoz_server.save_settings():
                socketio.emit('settings_saved', {'message': 'Ayarlar kaydedildi'})
                return True

            socketio.emit('error', {'message': 'Ayarlar kaydedilemedi'})
            return False
        except Exception as exc:
            logger.error(f"Save settings logic error: {exc}")
            socketio.emit('error', {'message': f'Hata: {str(exc)}'})
            return False

    @socketio.on('save_settings')
    def handle_save_settings_event(data):
        handle_save_settings_logic(data)

    @socketio.on('client_event')
    def handle_client_event(data):
        try:
            sid = request.sid
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ip and ',' in ip:
                ip = ip.split(',')[0].strip()
            kuvoz_server.touch_active_connection(sid, current_time=time.time())
            event_type = data.get('type') if isinstance(data, dict) else None
            payload = data.get('payload') if isinstance(data, dict) else None
            kuvoz_server.note_local_kiosk_event(ip, event_type or 'client_event', payload=payload, sid=sid)
            logger.info(f"🧭 Client event from {ip}: {data}")
        except Exception as exc:
            logger.error(f"Client event error: {exc}")

    @socketio.on('get_profile')
    def handle_get_profile(data=None):
        try:
            profile_data = {
                'company': dict(kuvoz_server.user_profile.get('company', {})),
                'contact': dict(kuvoz_server.user_profile.get('contact', {})),
                'device': dict(kuvoz_server.user_profile.get('device', {}))
            }
            profile_data['device']['ip'] = get_local_ip()
            profile_data['device']['last_update'] = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
            git_info = get_git_version_info()
            profile_data['device']['git_hash'] = git_info['hash']
            profile_data['device']['git_branch'] = git_info['branch']
            profile_data['update_diagnostics'] = get_git_update_diagnostics()
            emit('profile_response', profile_data)
            logger.info(f"Profile data sent to client (git: {git_info['hash']} on {git_info['branch']})")
        except Exception as exc:
            logger.error(f"Get profile error: {exc}")
            emit('error', {'message': f'Profil bilgileri yüklenemedi: {str(exc)}'})

    @socketio.on('save_profile')
    def handle_save_profile(data):
        try:
            if data:
                if 'company' in data:
                    kuvoz_server.user_profile['company'].update(data['company'])
                if 'contact' in data:
                    kuvoz_server.user_profile['contact'].update(data['contact'])
                if kuvoz_server.save_settings():
                    emit('profile_saved', {'message': 'Profil bilgileri kaydedildi'})
                    logger.info("User profile saved")
                else:
                    emit('error', {'message': 'Profil bilgileri kaydedilemedi'})
            else:
                emit('error', {'message': 'Geçersiz veri'})
        except Exception as exc:
            logger.error(f"Save profile error: {exc}")
            emit('error', {'message': f'Profil bilgileri kaydedilemedi: {str(exc)}'})

    @socketio.on('update_patient_context')
    def handle_update_patient_context(data):
        try:
            if not isinstance(data, dict):
                emit('error', {'message': 'Geçersiz hasta bilgisi'})
                return

            if kuvoz_server.update_patient_context(data):
                merged_patient = dict(kuvoz_server.current_patient) if isinstance(kuvoz_server.current_patient, dict) else {}
                merged_patient.update({
                    key: value for key, value in data.items()
                    if value is not None and str(value).strip() != ''
                })
                if patient_record_has_content(merged_patient):
                    merged_patient.setdefault('id', build_patient_id(merged_patient))
                    merged_patient.setdefault('savedAt', datetime.datetime.now().isoformat())
                    kuvoz_server.current_patient = merged_patient

                kuvoz_server.save_settings()
                care_payload = {
                    'success': True,
                    'care_settings': kuvoz_server.get_care_status(),
                    'sliders': kuvoz_server.get_effective_slider_values()
                }
                emit('patient_context_updated', care_payload)
                socketio.emit('care_settings_update', {
                    'care_settings': kuvoz_server.get_care_status(),
                    'sliders': kuvoz_server.get_effective_slider_values()
                })
                logger.info(
                    f"🐾 Patient context updated: species={kuvoz_server.patient_context.get('species')}, "
                    f"breed={kuvoz_server.patient_context.get('breed')}, "
                    f"age={kuvoz_server.patient_context.get('age')}, "
                    f"weight={kuvoz_server.patient_context.get('weight')}"
                )
            else:
                emit('error', {'message': 'Hasta bağlamı güncellenemedi'})
        except Exception as exc:
            logger.error(f"Update patient context error: {exc}")
            emit('error', {'message': f'Hasta bağlamı güncellenemedi: {str(exc)}'})

    return {
        'handle_save_settings_logic': handle_save_settings_logic,
    }
