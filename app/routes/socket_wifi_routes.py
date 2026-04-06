"""Socket.IO Wi-Fi route registration."""

from __future__ import annotations

import os
import subprocess
import time

from flask_socketio import emit


def register_wifi_socket_routes(
    socketio,
    *,
    logger,
    get_all_ips,
    start_wps_pairing,
):
    """Register Wi-Fi socket handlers."""

    @socketio.on('wifi_scan')
    def handle_wifi_scan():
        try:
            logger.info("Wi-Fi scanning initiated...")
            result = subprocess.run(
                ['nmcli', '-t', '-f', 'SSID,SIGNAL,BARS,SECURITY', 'dev', 'wifi'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                networks = []
                seen_ssids = set()
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    parts = line.split(':')
                    if len(parts) >= 4:
                        ssid = parts[0]
                        if ssid and ssid not in seen_ssids:
                            networks.append({
                                'ssid': ssid,
                                'signal': parts[1],
                                'bars': parts[2],
                                'security': parts[3]
                            })
                            seen_ssids.add(ssid)

                emit('wifi_scan_response', {'success': True, 'networks': networks})
            else:
                emit('wifi_scan_response', {'success': False, 'message': 'Tarama başarısız (nmcli hatası)'})

        except subprocess.TimeoutExpired:
            emit('wifi_scan_response', {'success': False, 'message': 'Tarama zaman aşımına uğradı'})
        except Exception as exc:
            logger.error(f"Wi-Fi scan error: {exc}")
            emit('wifi_scan_response', {'success': False, 'message': str(exc)})

    @socketio.on('wifi_connect')
    def handle_wifi_connect(data):
        try:
            ssid = data.get('ssid')
            password = data.get('password')

            if not ssid:
                emit('wifi_connect_response', {'success': False, 'message': 'SSID gerekli'})
                return

            logger.info(f"Attempting to connect to Wi-Fi: {ssid}")
            emit('wifi_connect_progress', {'message': f'{ssid} ağına bağlanılıyor...'})

            cmd = ['sudo', 'nmcli', 'dev', 'wifi', 'connect', ssid]
            if password:
                cmd.extend(['password', password])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                subprocess.run(['sudo', 'nmcli', 'connection', 'modify', ssid, 'ipv4.route-metric', '50'], capture_output=True)
                subprocess.run(['sudo', 'nmcli', 'connection', 'up', ssid], capture_output=True)

                wifi_device = None
                try:
                    status_result = subprocess.run(
                        ['nmcli', '-t', '-f', 'ACTIVE,SSID,DEVICE', 'dev', 'wifi'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if status_result.returncode == 0:
                        for line in status_result.stdout.strip().split('\n'):
                            if line.startswith('yes:'):
                                parts = line.split(':')
                                if len(parts) >= 3:
                                    wifi_device = parts[2]
                                break
                except Exception:
                    wifi_device = None

                if not wifi_device:
                    wifi_device = 'wlan0'

                wifi_ip = None
                for _ in range(10):
                    ips = get_all_ips()
                    wifi_ip = ips.get(wifi_device) or ips.get('wlan0')
                    if wifi_ip:
                        break
                    time.sleep(1)

                if wifi_ip:
                    message = f'{ssid} ağına başarıyla bağlandı. IP: {wifi_ip}'
                else:
                    message = f'{ssid} ağına bağlandı ancak IP alınamadı (DHCP bekleniyor).'

                emit('wifi_connect_response', {
                    'success': True,
                    'message': message,
                    'ip': wifi_ip
                })
                logger.info(f"Successfully connected to {ssid} (Wi-Fi device: {wifi_device}, IP: {wifi_ip})")
            else:
                emit('wifi_connect_response', {
                    'success': False,
                    'message': f'Bağlantı hatası: {result.stderr or result.stdout}'
                })
                logger.error(f"Wi-Fi connect failed for {ssid}: {result.stderr}")

        except Exception as exc:
            logger.error(f"Wi-Fi connect error: {exc}")
            emit('wifi_connect_response', {'success': False, 'message': str(exc)})

    @socketio.on('wifi_wps_pbc')
    def handle_wifi_wps_pbc():
        try:
            logger.info("Starting WPS PBC pairing...")
            emit('wifi_wps_progress', {'message': 'WPS Eşleşmesi başlatılıyor... Lütfen modemdeki butona basın.'})
            ok, msg, stage = start_wps_pairing('wlan0')
            if ok:
                emit('wifi_wps_response', {
                    'success': True,
                    'stage': stage or 'started',
                    'message': msg
                })
            else:
                emit('wifi_wps_response', {
                    'success': False,
                    'stage': 'final',
                    'message': msg
                })
        except Exception as exc:
            logger.error(f"WPS error: {exc}")
            emit('wifi_wps_response', {'success': False, 'stage': 'final', 'message': str(exc)})

    @socketio.on('wifi_status')
    def handle_wifi_status():
        try:
            result = subprocess.run(
                ['nmcli', '-t', '-f', 'active,ssid,device', 'dev', 'wifi'],
                capture_output=True,
                text=True,
                timeout=10
            )

            status = {'connected': False, 'ssid': None, 'ip': None}

            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.startswith('yes:'):
                        parts = line.split(':')
                        if len(parts) >= 2:
                            device = parts[2] if len(parts) > 2 else 'wlan0'
                            status = {
                                'connected': True,
                                'ssid': parts[1],
                                'ip': None
                            }
                            ips = get_all_ips()
                            status['ip'] = ips.get(device) or ips.get('wlan0')
                            break

            if not status['connected']:
                try:
                    wpa_cli = '/usr/sbin/wpa_cli' if os.path.exists('/usr/sbin/wpa_cli') else '/sbin/wpa_cli'
                    if os.path.exists(wpa_cli):
                        cmd = [wpa_cli, '-i', 'wlan0']
                        if os.path.exists('/run/wpa_supplicant/wlan0'):
                            cmd.extend(['-p', '/run/wpa_supplicant'])
                        cmd.append('status')

                        wpa_result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                        if wpa_result.returncode == 0:
                            wpa_state = None
                            wpa_ssid = None
                            for line in wpa_result.stdout.split('\n'):
                                if line.startswith('wpa_state='):
                                    wpa_state = line.split('=', 1)[1].strip()
                                elif line.startswith('ssid='):
                                    wpa_ssid = line.split('=', 1)[1].strip()
                            if wpa_state == 'COMPLETED' and wpa_ssid:
                                ips = get_all_ips()
                                status = {
                                    'connected': True,
                                    'ssid': wpa_ssid,
                                    'ip': ips.get('wlan0')
                                }
                except Exception:
                    pass

            emit('wifi_status_response', status)
        except Exception as exc:
            logger.error(f"Wi-Fi status error: {exc}")
            emit('wifi_status_response', {'connected': False, 'message': str(exc)})

    @socketio.on('wifi_disconnect')
    def handle_wifi_disconnect():
        try:
            quick_state = subprocess.run(
                ['nmcli', '-t', '-f', 'DEVICE,TYPE,STATE', 'dev'],
                capture_output=True,
                text=True,
                timeout=4
            )
            if quick_state.returncode == 0:
                wifi_connected = False
                for line in quick_state.stdout.strip().split('\n'):
                    parts = line.split(':')
                    if len(parts) >= 3 and parts[1] == 'wifi' and parts[2] == 'connected':
                        wifi_connected = True
                        break
                if not wifi_connected:
                    emit('wifi_disconnect_response', {'success': True, 'message': 'Wi-Fi zaten bağlı değil'})
                    return

            active_result = subprocess.run(
                ['nmcli', '-t', '-f', 'DEVICE,TYPE,STATE,CONNECTION', 'dev'],
                capture_output=True,
                text=True,
                timeout=5
            )

            connection_name = None
            if active_result.returncode == 0:
                for line in active_result.stdout.strip().split('\n'):
                    parts = line.split(':')
                    if len(parts) >= 4 and parts[1] == 'wifi' and parts[2] == 'connected':
                        connection_name = parts[3]
                        break

            nm_success = False
            nm_err = None
            if connection_name:
                nm_result = subprocess.run(
                    ['sudo', 'nmcli', 'con', 'down', connection_name],
                    capture_output=True,
                    text=True,
                    timeout=8
                )
                if nm_result.returncode == 0:
                    nm_success = True
                else:
                    nm_err = (nm_result.stderr or nm_result.stdout or '').strip()

            if not nm_success:
                nm_result = subprocess.run(
                    ['sudo', 'nmcli', 'dev', 'disconnect', 'wlan0'],
                    capture_output=True,
                    text=True,
                    timeout=8
                )
                if nm_result.returncode == 0:
                    nm_success = True
                else:
                    nm_err = nm_err or (nm_result.stderr or nm_result.stdout or '').strip()

            wpa_success = False
            wpa_err = None
            try:
                wpa_cli = '/usr/sbin/wpa_cli' if os.path.exists('/usr/sbin/wpa_cli') else '/sbin/wpa_cli'
                if not os.path.exists(wpa_cli):
                    wpa_cli = None
                if wpa_cli:
                    cmd = ['sudo', wpa_cli, '-i', 'wlan0']
                    if os.path.exists('/run/wpa_supplicant/wlan0'):
                        cmd.extend(['-p', '/run/wpa_supplicant'])
                    cmd.append('disconnect')
                    wpa_result = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
                    if wpa_result.returncode == 0 and 'OK' in wpa_result.stdout:
                        wpa_success = True
                    else:
                        wpa_err = (wpa_result.stderr or wpa_result.stdout or '').strip()
            except Exception as exc:
                wpa_err = str(exc)

            if nm_success or wpa_success:
                subprocess.run(['sudo', 'ip', 'route', 'del', 'default', 'dev', 'wlan0'], timeout=5)
                subprocess.run(['sudo', 'ip', 'addr', 'flush', 'dev', 'wlan0'], timeout=5)
                emit('wifi_disconnect_response', {'success': True, 'message': 'Bağlantı kesildi'})
            else:
                detail = nm_err or wpa_err
                msg = 'Bağlantı kesilemedi'
                if detail:
                    msg = f'{msg}: {detail}'
                emit('wifi_disconnect_response', {'success': False, 'message': msg})

        except Exception as exc:
            logger.error(f"Wi-Fi disconnect error: {exc}")
            emit('wifi_disconnect_response', {'success': False, 'message': str(exc)})
