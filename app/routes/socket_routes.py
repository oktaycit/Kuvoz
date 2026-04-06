"""Socket.IO route registration for Kuvoz web server."""

from __future__ import annotations

import time

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
        system_status = kuvoz_server.get_effective_system_status()
        payload = {
            'type': 'status_response',
            'sensors': kuvoz_server.sensor_data,
            'buttons': kuvoz_server.button_states,
            'gpio_outputs': kuvoz_server.gpio_output_states,
            'sliders': kuvoz_server.get_effective_slider_values(),
            'timers': kuvoz_server.get_timer_data(),
            'system': system_status,
            'ai_available': ai_available,
            'ai_enabled': kuvoz_server.ai_enabled,
            'ai_health': kuvoz_server.get_ai_health_status(),
            'system_settings': kuvoz_server.system_settings,
            'care_settings': kuvoz_server.get_care_status(),
        }
        if include_disinfection:
            payload['disinfection_mode'] = kuvoz_server.disinfection_mode
        return payload

    def _broadcast_active_connections(current_time: float | None = None):
        if current_time is None:
            current_time = time.time()
        socketio.emit('active_connections_update', {
            'connections': [
                {
                    'ip': conn['ip'],
                    'connected_at': conn['connected_at'],
                    'duration': int(current_time - conn['connected_at'])
                }
                for conn in kuvoz_server.active_connections.values()
            ]
        }, namespace='/')

    @socketio.on('connect')
    def handle_connect():
        try:
            sid = request.sid
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ',' in ip:
                ip = ip.split(',')[0].strip()

            current_time = time.time()
            kuvoz_server.active_connections[sid] = {
                'ip': ip,
                'connected_at': current_time,
                'last_seen': current_time
            }
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

    @socketio.on('toggle_button')
    def handle_toggle_button(data):
        try:
            name = data.get('name')
            pin = data.get('pin')
            state = data.get('state')
            page = data.get('page', 'index')
            logger.info(f'Button toggle: {name} (pin {pin}) -> {state} from page: {page}')

            if name in ['b7', 'b8'] and page != 'cleaning':
                logger.warning(f'Button {name} blocked - only allowed on cleaning page')
                emit('error', {
                    'type': 'warning',
                    'message': 'UV ve Ozon sadece Temizlik sayfasında kullanılabilir'
                })
                return

            if name in ['b7', 'b8'] and state is True and not kuvoz_server.disinfection_mode:
                logger.info('🦠 Activating disinfection safety mode - disabling normal controls')
                kuvoz_server.disinfection_mode = True
                kuvoz_server.disinfection_start_time = time.time()
                for btn_name in ['b1', 'b2', 'b3', 'b4', 'b5', 'b6']:
                    if kuvoz_server.button_states.get(btn_name):
                        pin_index = int(btn_name[1:]) - 1
                        btn_pin = kuvoz_server.outChannels[pin_index]
                        kuvoz_server.toggle_button(btn_name, btn_pin, False)
                        logger.info(f'  → Disabled {btn_name} for safety')
                emit('disinfection_mode', {
                    'active': True,
                    'message': 'Dezenfeksiyon modu aktif - normal kontroller devre dışı'
                }, broadcast=True)

            if name in ['b7', 'b8'] and state is False and kuvoz_server.disinfection_mode:
                uv_off = not kuvoz_server.button_states.get('b7', False)
                ozone_off = not kuvoz_server.button_states.get('b8', False)
                if name == 'b7':
                    uv_off = True
                elif name == 'b8':
                    ozone_off = True
                if uv_off and ozone_off:
                    logger.info('🦠 Deactivating disinfection safety mode - re-enabling normal controls')
                    kuvoz_server.disinfection_mode = False
                    kuvoz_server.disinfection_start_time = 0
                    emit('disinfection_mode', {
                        'active': False,
                        'message': 'Normal kontroller tekrar aktif'
                    }, broadcast=True)

            if name and pin is not None:
                kuvoz_server.toggle_button(name, int(pin), state if state is not None else None)
                emit('button_update', {
                    'type': 'button_update',
                    'buttons': kuvoz_server.button_states,
                    'gpio_outputs': kuvoz_server.gpio_output_states
                }, broadcast=True)
        except Exception as exc:
            logger.error(f'Toggle button error: {exc}')

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
            if sid in kuvoz_server.active_connections:
                ip = kuvoz_server.active_connections[sid]['ip']
                duration = int(time.time() - kuvoz_server.active_connections[sid]['connected_at'])
                del kuvoz_server.active_connections[sid]
                kuvoz_server.note_local_kiosk_disconnect(ip, sid)
                logger.info(f'❌ WebSocket disconnected: {sid} ({ip}) - Duration: {duration}s')
                _broadcast_active_connections()
        except Exception as exc:
            logger.error(f'Disconnect error: {exc}')
        logger.info('Client disconnected')

    return {
        'handle_update_slider_logic': handle_update_slider_logic,
    }
