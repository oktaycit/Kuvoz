"""Wi-Fi WPS helper service."""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time


class WifiWPSService:
    """Encapsulate WPS flow state and helper logic."""

    def __init__(self, *, logger, socketio, udhcpc_script: str, get_all_ips):
        self.logger = logger
        self.socketio = socketio
        self.udhcpc_script = udhcpc_script
        self.get_all_ips = get_all_ips
        self._wps_lock = threading.Lock()
        self._wps_in_progress = False
        self._wps_last_start_ts = 0.0
        self._wps_min_interval_sec = 35
        self._wifi_dhcp_lock = threading.Lock()
        self._wifi_dhcp_in_progress = False

    def _begin_wps_session(self):
        now = time.time()
        with self._wps_lock:
            if self._wps_in_progress:
                return False, 'WPS işlemi zaten devam ediyor. Lütfen 30-40 saniye bekleyin.'
            if now - self._wps_last_start_ts < self._wps_min_interval_sec:
                remain = int(max(1, self._wps_min_interval_sec - (now - self._wps_last_start_ts)))
                return False, f'WPS çok sık tetiklendi. {remain}s sonra tekrar deneyin.'
            self._wps_in_progress = True
            self._wps_last_start_ts = now
        return True, None

    def _end_wps_session(self):
        with self._wps_lock:
            self._wps_in_progress = False

    def _get_wpa_status(self, interface='wlan0'):
        wpa_cli = '/usr/sbin/wpa_cli' if os.path.exists('/usr/sbin/wpa_cli') else '/sbin/wpa_cli'
        if not os.path.exists(wpa_cli):
            wpa_cli = 'wpa_cli'
        cmd = ['sudo', wpa_cli, '-i', interface]
        if os.path.exists(f'/run/wpa_supplicant/{interface}'):
            cmd.extend(['-p', '/run/wpa_supplicant'])
        cmd.append('status')
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return ''
        return result.stdout or ''

    @staticmethod
    def _get_wpa_field(status_text, field):
        prefix = f"{field}="
        for line in (status_text or '').splitlines():
            if line.startswith(prefix):
                return line.split('=', 1)[1].strip()
        return None

    def _wait_for_wpa_completed(self, interface='wlan0', timeout=30, interval=2, previous_bssid=None, previous_ssid=None):
        seen_non_completed = False
        start = time.time()
        while time.time() - start < timeout:
            status = self._get_wpa_status(interface)
            wpa_state = self._get_wpa_field(status, 'wpa_state')
            if wpa_state == 'COMPLETED':
                if not previous_bssid and not previous_ssid:
                    return True

                bssid = self._get_wpa_field(status, 'bssid')
                ssid = self._get_wpa_field(status, 'ssid')
                bssid_changed = bool(previous_bssid and bssid and bssid != previous_bssid)
                ssid_changed = bool(previous_ssid and ssid and ssid != previous_ssid)
                if seen_non_completed or bssid_changed or ssid_changed:
                    return True
            else:
                seen_non_completed = True
            time.sleep(interval)
        return False

    def _sync_nm_with_wpa(self, interface='wlan0'):
        try:
            status = self._get_wpa_status(interface)
            if 'wpa_state=COMPLETED' not in status:
                return False

            wpa_ssid = self._get_wpa_field(status, 'ssid')
            if not wpa_ssid:
                return False

            prof = subprocess.run(
                ['nmcli', '-t', '-f', 'NAME,TYPE', 'connection', 'show'],
                capture_output=True,
                text=True,
                timeout=10
            )
            candidate = None
            if prof.returncode == 0:
                for line in (prof.stdout or '').splitlines():
                    parts = line.split(':', 1)
                    if len(parts) < 2:
                        continue
                    name, ctype = parts[0], parts[1]
                    if ctype not in ('wifi', '802-11-wireless'):
                        continue
                    ssid_res = subprocess.run(
                        ['nmcli', '-g', '802-11-wireless.ssid', 'connection', 'show', name],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if ssid_res.returncode != 0:
                        continue
                    ssid = (ssid_res.stdout or '').strip()
                    if ssid != wpa_ssid:
                        continue
                    candidate = name
                    if name != 'preconfigured':
                        break

            if not candidate:
                self.logger.warning(f"WPS NM sync: no matching Wi-Fi profile for SSID '{wpa_ssid}'")
                return False

            up = subprocess.run(
                ['sudo', 'nmcli', 'connection', 'up', candidate, 'ifname', interface],
                capture_output=True,
                text=True,
                timeout=25
            )
            if up.returncode == 0:
                self.logger.info(f"WPS NM sync successful on {interface} via profile '{candidate}'")
                return True

            err = (up.stderr or up.stdout or '').strip()
            self.logger.warning(f"WPS NM sync failed on {interface}: {err}")
            return False
        except Exception as exc:
            self.logger.warning(f"WPS NM sync error on {interface}: {exc}")
            return False

    def _build_udhcpc_command(self, interface='wlan0'):
        if not os.path.exists(self.udhcpc_script):
            self.logger.warning(f"UDHCPC script not found: {self.udhcpc_script}")
            return None
        udhcpc = shutil.which('udhcpc')
        if udhcpc:
            cmd = [udhcpc]
        else:
            busybox = shutil.which('busybox')
            if not busybox:
                self.logger.warning("udhcpc/busybox not found for DHCP")
                return None
            cmd = [busybox, 'udhcpc']
        cmd.extend(['-i', interface, '-q', '-n', '-t', '10', '-T', '3', '-A', '20', '-s', self.udhcpc_script])
        return ['sudo', '-n'] + cmd

    def _current_wifi_status(self, interface='wlan0'):
        status = {'connected': False, 'ssid': None, 'ip': None}
        try:
            result = subprocess.run(
                ['nmcli', '-t', '-f', 'active,ssid,device', 'dev', 'wifi'],
                capture_output=True,
                text=True,
                timeout=8
            )
            if result.returncode == 0:
                for line in (result.stdout or '').splitlines():
                    if not line.startswith('yes:'):
                        continue
                    parts = line.split(':')
                    if len(parts) >= 2:
                        dev = parts[2] if len(parts) > 2 and parts[2] else interface
                        ips = self.get_all_ips()
                        status = {
                            'connected': True,
                            'ssid': parts[1],
                            'ip': ips.get(dev) or ips.get(interface)
                        }
                    break
        except Exception:
            pass
        return status

    def _emit_wps_final(self, success, message):
        payload = {'success': success, 'message': message, 'stage': 'final'}
        payload.update(self._current_wifi_status('wlan0'))
        self.socketio.emit('wifi_wps_response', payload, namespace='/')

    def _wifi_dhcp_worker(self, interface='wlan0', previous_bssid=None, previous_ssid=None, monitor_only=False):
        try:
            self.logger.info(f"WPS Worker: Attempting nmcli WPS on {interface}...")
            nm_success = False
            try:
                check = subprocess.run(['nmcli', 'dev', 'wifi', 'wps', 'help'], capture_output=True, timeout=5)
                if check.returncode == 0:
                    nm_wps = subprocess.run(
                        ['sudo', 'nmcli', 'dev', 'wifi', 'wps', 'ifname', interface],
                        capture_output=True,
                        text=True,
                        timeout=125
                    )
                    if nm_wps.returncode == 0:
                        self.logger.info("WPS Worker: nmcli WPS successful.")
                        nm_success = True
                    else:
                        self.logger.warning(f"WPS Worker: nmcli WPS failed: {nm_wps.stderr}")
                else:
                    self.logger.warning("WPS Worker: nmcli WPS command not supported.")
            except Exception as exc:
                self.logger.warning(f"WPS Worker: nmcli exception: {exc}")

            if not nm_success:
                self.logger.info(f"WPS Worker: Falling back to wpa_cli for {interface}...")
                wpa_cli = '/usr/sbin/wpa_cli' if os.path.exists('/usr/sbin/wpa_cli') else '/sbin/wpa_cli'
                if not os.path.exists(wpa_cli):
                    wpa_cli = 'wpa_cli'
                path = '/run/wpa_supplicant' if os.path.exists(f'/run/wpa_supplicant/{interface}') else None
                wpa_cmd = ['sudo', wpa_cli, '-i', interface]
                if path:
                    wpa_cmd.extend(['-p', path])

                for subcommand in ('wps_cancel', 'disconnect'):
                    subprocess.run(wpa_cmd + [subcommand], capture_output=True, timeout=5)

                pbc = subprocess.run(wpa_cmd + ['wps_pbc'], capture_output=True, text=True, timeout=10)
                if pbc.returncode != 0 or 'OK' not in pbc.stdout:
                    self.logger.error(f"WPS Worker: wpa_cli wps_pbc failed: {pbc.stderr or pbc.stdout}")
                    self._emit_wps_final(False, 'WPS başlatılamadı (wpa_cli hatası).')
                    return

            if not self._wait_for_wpa_completed(
                interface,
                timeout=120,
                interval=3,
                previous_bssid=previous_bssid,
                previous_ssid=previous_ssid
            ):
                self.logger.warning(f"WPS: wpa_state not completed for {interface} within timeout.")
                self._emit_wps_final(False, 'WPS tamamlanamadı: modem ile eşleşme kurulamadı veya zaman aşımı.')
                return

            self.logger.info(f"WPS: Connection state completed on {interface}. Syncing...")
            self.socketio.emit('wifi_wps_progress', {'message': 'Bağlantı kuruldu, IP adresi bekleniyor...'}, namespace='/')

            if self._sync_nm_with_wpa(interface):
                for _ in range(15):
                    status = self._current_wifi_status(interface)
                    if status.get('connected') and status.get('ip'):
                        self._emit_wps_final(True, f"WPS tamamlandı. Bağlandı: {status.get('ssid')} (IP: {status.get('ip')})")
                        return
                    time.sleep(2)

                status = self._current_wifi_status(interface)
                if status.get('connected'):
                    self._emit_wps_final(True, f"WPS tamamlandı. Bağlandı: {status.get('ssid')} (Ağ kaydedildi, IP bekleniyor...)")
                else:
                    self._emit_wps_final(True, 'WPS tamamlandı. Wi-Fi bağlantısı kaydedildi.')
                return

            cmd = self._build_udhcpc_command(interface)
            if not cmd:
                self._emit_wps_final(False, 'WPS sonrası DHCP başlatılamadı (udhcpc eksik).')
                return

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            if result.returncode != 0:
                err = (result.stderr or result.stdout or '').strip()
                self.logger.warning(f"WPS DHCP failed: {err}")
                self._emit_wps_final(False, f'WPS tamamlandı ancak IP alınamadı: {err}')
            else:
                status = self._current_wifi_status(interface)
                self._emit_wps_final(True, f"WPS tamamlandı. Bağlandı: {status.get('ssid') or interface} (IP: {status.get('ip') or 'bilinmiyor'})")
        except Exception as exc:
            self.logger.warning(f"WPS worker error: {exc}")
            self._emit_wps_final(False, f'WPS işlem hatası: {exc}')
        finally:
            with self._wifi_dhcp_lock:
                self._wifi_dhcp_in_progress = False
            self._end_wps_session()

    def start_wifi_dhcp_async(self, interface='wlan0', previous_bssid=None, previous_ssid=None, monitor_only=False):
        with self._wifi_dhcp_lock:
            if self._wifi_dhcp_in_progress:
                self.logger.info(f"WPS/DHCP worker already running for {interface}, skipping duplicate start")
                return False
            self._wifi_dhcp_in_progress = True
        threading.Thread(
            target=self._wifi_dhcp_worker,
            args=(interface, previous_bssid, previous_ssid, monitor_only),
            daemon=True
        ).start()
        return True

    def start_pairing(self, interface='wlan0'):
        started, message = self._begin_wps_session()
        if not started:
            return False, message, None

        pre_status = self._get_wpa_status(interface)
        previous_bssid = self._get_wpa_field(pre_status, 'bssid')
        previous_ssid = self._get_wpa_field(pre_status, 'ssid')

        if self.start_wifi_dhcp_async(interface, previous_bssid, previous_ssid):
            return True, 'WPS Eşleşmesi başlatıldı. Modemdeki butona basın.', 'started'

        self._end_wps_session()
        return False, 'WPS işlemi başlatılamadı.', None
