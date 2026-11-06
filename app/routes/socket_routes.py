"""Socket.IO route registration for Kuvoz web server."""

from __future__ import annotations

import time
import math

from flask import request
from flask_socketio import emit


def register_basic_socket_routes(
    socketio,
    *,
    kuvoz_server,
    logger,
    ai_available: bool,
):
    """Register the first extracted set of high-traffic socket handlers."""

    def _build_status_payload(include_disinfection: bool = False):
        return kuvoz_server.build_status_payload(
            ai_available=ai_available,
            include_disinfection=include_disinfection,
        )

    def _broadcast_active_connections(current_time: float | None = None):
        socketio.emit(
            'active_connections_update',
            kuvoz_server.get_active_connections_payload(current_time),
            namespace='/',
        )

    @socketio.on('connect')
    def handle_connect():
        try:
            sid = request.sid
            ip = request.headers.get('X-Forwarded-For', request.remote_addr) or ''
            if ',' in ip:
                ip = ip.split(',')[0].strip()

            current_time = time.time()
            kuvoz_server.register_active_connection(sid, ip, current_time=current_time)
            kuvoz_server.note_local_kiosk_connect(ip, sid)
            logger.info(f'✅ WebSocket connected: {sid} from {ip}')
            _broadcast_active_connections(current_time)
        except Exception as exc:
            logger.error(f'Connect error: {exc}')

        logger.info('Client connected')
        logger.info(f"📤 Sending status_response on connect. Sliders: {kuvoz_server.slider_values}")
        emit('status_response', _build_status_payload(include_disinfection=False))

    @socketio.on('get_status')
    def handle_get_status(data=None):
        logger.debug('DEBUG: Client requested status')
        logger.debug(f'DEBUG: Current sensor data: {kuvoz_server.sensor_data}')
        page = data.get('page', 'index') if data else 'index'
        logger.debug(f'DEBUG: get_status from page: {page}')
        status_data = _build_status_payload(include_disinfection=True)
        logger.debug(
            "DEBUG (get_status): oxygen_available=%s, co2_available=%s",
            status_data['system'].get('oxygen_available'),
            status_data['system'].get('co2_available'),
        )
        logger.debug(f"DEBUG (get_status): sensor_data keys={list(kuvoz_server.sensor_data.keys())}")
        emit('status_response', status_data)

    def _disinfection_broadcast():
        socketio.emit('disinfection_mode', kuvoz_server.disinfection_status())
        snapshot = kuvoz_server.snapshot_runtime_state()
        socketio.emit('button_update', kuvoz_server.build_button_update_payload(snapshot))

    @socketio.on('stop_disinfection')
    def handle_stop_disinfection(data=None):
        try:
            success = kuvoz_server.stop_disinfection()
            _disinfection_broadcast()
            return {'success': success, 'disinfection': kuvoz_server.disinfection_status()}
        except Exception:
            logger.exception('Disinfection stop failed')
            return {'success': False}

    @socketio.on('disinfection_heartbeat')
    def handle_disinfection_heartbeat(data=None):
        with kuvoz_server.state_lock:
            if kuvoz_server.disinfection_owner == request.sid:
                kuvoz_server.disinfection_heartbeat = time.monotonic()

    @socketio.on('toggle_button')
    def handle_toggle_button(data):
        try:
            if not isinstance(data, dict):
                return {'success': False}
            name, state = data.get('name'), data.get('state')
            channels = {f'b{i+1}': pin for i, pin in enumerate(kuvoz_server.outChannels)}
            if name not in channels or type(state) is not bool:
                return {'success': False}
            if data.get('pin') != channels[name]:
                return {'success': False}
            with kuvoz_server.state_lock:
                if name in ('b7', 'b8') and state:
                    if name == 'b8':
                        duration = float(kuvoz_server.slider_values.get('sld10', 0))
                        if not math.isfinite(duration) or duration <= 0:
                            return {'success': False}
                    if data.get('page') != 'cleaning' or data.get('empty_confirmed') is not True:
                        emit('error', {'type': 'warning', 'message': 'Önce hayvanın kuvöz dışında olduğunu onaylayın.'})
                        return {'success': False}
                    if not kuvoz_server.start_disinfection(request.sid):
                        emit('error', {'type': 'warning', 'message': 'Dezenfeksiyon başlatılamadı; çıkışları ve bağlantıyı kontrol edin.'})
                        return {'success': False}
                if kuvoz_server.disinfection_mode and state and name not in ('b6', 'b7', 'b8'):
                    return {'success': False}
                success = kuvoz_server.toggle_button(name, channels[name], state)
                if name in ('b7', 'b8'):
                    if not success or not any(kuvoz_server.button_states.get(k) for k in ('b7', 'b8')):
                        success = kuvoz_server.stop_disinfection() and success
                    _disinfection_broadcast()
                else:
                    snapshot = kuvoz_server.snapshot_runtime_state()
                    socketio.emit('button_update', kuvoz_server.build_button_update_payload(snapshot))
                return {'success': bool(success)}
        except Exception:
            logger.exception('Toggle button failed')
            return {'success': False}

    def handle_update_slider_logic(data):
        try:
            slider_id = data.get('id')
            value = data.get('value')
            logger.info(f'Slider update: {slider_id} -> {value}')
            if slider_id and value is not None:
                kuvoz_server.update_slider(slider_id, value)
                socketio.emit('slider_update', {
                    'type': 'slider_update',
                    'sliders': kuvoz_server.get_effective_slider_values()
                })
                if slider_id in ['sld8', 'sld9', 'sld10', 'sld11']:
                    socketio.emit('timer_update', kuvoz_server.get_timer_data())
                return True
            return False
        except Exception as exc:
            logger.error(f"Slider logic error: {exc}")
            return False

    @socketio.on('update_slider')
    def handle_update_slider_event(data):
        handle_update_slider_logic(data)

    @socketio.on('disconnect')
    def handle_disconnect():
        try:
            sid = request.sid
            if kuvoz_server.disinfection_owner == sid:
                kuvoz_server.stop_disinfection()
                _disinfection_broadcast()
            connection = kuvoz_server.pop_active_connection(sid)
            if connection is not None:
                ip = connection['ip']
                duration = connection['duration']
                kuvoz_server.note_local_kiosk_disconnect(ip, sid)
                logger.info(f'❌ WebSocket disconnected: {sid} ({ip}) - Duration: {duration}s')
                _broadcast_active_connections()
        except Exception as exc:
            logger.error(f'Disconnect error: {exc}')
        logger.info('Client disconnected')

    return {
        'handle_update_slider_logic': handle_update_slider_logic,
    }
