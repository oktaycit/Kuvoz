"""Socket.IO Tailscale route registration."""

from __future__ import annotations

import base64
import json
import re
import subprocess
import threading
import time
from io import BytesIO

from flask_socketio import emit


def register_tailscale_socket_routes(
    socketio,
    *,
    logger,
    task_manager,
    qrcode_module=None,
    qrcode_available: bool = False,
):
    """Register Tailscale management socket handlers."""

    def _build_qr_data(url: str):
        if not qrcode_available or qrcode_module is None:
            return None
        qr = qrcode_module.QRCode(version=1, box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode('utf-8')}"

    @socketio.on('tailscale_status')
    def handle_tailscale_status():
        try:
            check_installed = subprocess.run(
                ['which', 'tailscale'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if check_installed.returncode != 0:
                emit('tailscale_status_response', {
                    'installed': False,
                    'connected': False,
                    'message': 'Tailscale kurulu değil'
                })
                return

            service_check = subprocess.run(
                ['systemctl', 'is-active', 'tailscaled'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if service_check.returncode != 0:
                logger.warning('tailscaled service not running')
                emit('tailscale_status_response', {
                    'installed': True,
                    'connected': False,
                    'message': 'Tailscale servisi çalışmıyor. Başlatmak için: sudo systemctl start tailscaled'
                })
                return

            result = subprocess.run(
                ['tailscale', 'status', '--json'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                status_data = json.loads(result.stdout)
                backend_state = status_data.get('BackendState', 'Unknown')
                is_connected = backend_state == 'Running'
                self_info = status_data.get('Self', {})
                ip_addresses = self_info.get('TailscaleIPs', []) if self_info and is_connected else []

                emit('tailscale_status_response', {
                    'installed': True,
                    'connected': is_connected,
                    'state': backend_state,
                    'ips': ip_addresses,
                    'hostname': self_info.get('HostName', 'Unknown') if self_info else 'Unknown'
                })
            else:
                emit('tailscale_status_response', {
                    'installed': True,
                    'connected': False,
                    'message': 'Tailscale durumu alınamadı'
                })

        except subprocess.TimeoutExpired:
            logger.error('Tailscale status timeout')
            emit('tailscale_status_response', {
                'installed': True,
                'connected': False,
                'message': 'Tailscale yanıt vermiyor. Servis çalışıyor mu kontrol edin: sudo systemctl status tailscaled'
            })
        except Exception as exc:
            logger.error(f'Tailscale status error: {exc}')
            emit('tailscale_status_response', {
                'installed': True,
                'connected': False,
                'message': f'Durum okunamadı: {str(exc)}'
            })

    @socketio.on('tailscale_install')
    def handle_tailscale_install():
        if not task_manager.start_task('tailscale_install'):
            emit('error', {'message': f'Şu anda başka bir işlem devam ediyor: {task_manager.current_task}'})
            return

        def run_install():
            try:
                check_installed = subprocess.run(['which', 'tailscale'], capture_output=True, text=True)
                if check_installed.returncode == 0:
                    socketio.emit('tailscale_install_response', {'success': False, 'message': 'Tailscale zaten kurulu'}, namespace='/')
                    return

                socketio.emit('tailscale_install_progress', {'message': 'Tailscale indiriliyor...'}, namespace='/')
                install_result = subprocess.run(
                    ['curl', '-fsSL', 'https://tailscale.com/install.sh'],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if install_result.returncode != 0:
                    socketio.emit('tailscale_install_response', {'success': False, 'message': 'Kurulum scripti indirilemedi'}, namespace='/')
                    return

                socketio.emit('tailscale_install_progress', {'message': 'Tailscale kuruluyor (birkaç dakika sürebilir)...'}, namespace='/')
                install_script = subprocess.run(
                    ['sh', '-c', install_result.stdout],
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                if install_script.returncode == 0:
                    socketio.emit('tailscale_install_response', {'success': True, 'message': 'Tailscale başarıyla kuruldu'}, namespace='/')
                else:
                    combined_output = (install_script.stderr or '') + (install_script.stdout or '')
                    if "No space left on device" in combined_output:
                        error_msg = "❌ Cihazda yeterli yer yok! 'Disk Temizle' butonunu kullanın."
                    else:
                        error_msg = f'Kurulum hatası: {(install_script.stderr or "")[:200]}'
                    socketio.emit('tailscale_install_response', {'success': False, 'message': error_msg}, namespace='/')

            except subprocess.TimeoutExpired:
                socketio.emit('tailscale_install_response', {'success': False, 'message': 'Kurulum zaman aşımına uğradı (5 dk).'}, namespace='/')
            except Exception as exc:
                logger.error(f'Tailscale install error: {exc}')
                socketio.emit('error', {'message': f'Kurulum sırasında kritik hata: {str(exc)}'}, namespace='/')
            finally:
                task_manager.end_task()

        threading.Thread(target=run_install, daemon=True).start()

    @socketio.on('tailscale_connect')
    def handle_tailscale_connect():
        if not task_manager.start_task('tailscale_connect'):
            emit('error', {'message': f'İşlem reddedildi. Şu anda devam eden işlem: {task_manager.current_task}'})
            return

        def run_connect():
            try:
                logger.info('Tailscale connect process started in background...')
                status_check = subprocess.run(['tailscale', 'status', '--json'], capture_output=True, text=True, timeout=20)
                if status_check.returncode == 0:
                    status_data = json.loads(status_check.stdout)
                    if status_data.get('BackendState') == 'Running':
                        socketio.emit('tailscale_connect_response', {'success': True, 'already_connected': True, 'message': 'Tailscale zaten bağlı'}, namespace='/')
                        return

                socketio.emit('tailscale_install_progress', {'message': 'Bağlantı başlatılıyor...'}, namespace='/')
                result = subprocess.run(
                    ['sudo', 'tailscale', 'up', '--reset', '--timeout=10s'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                output = result.stdout + result.stderr
                match = re.search(r'https://login\.tailscale\.com/a/[a-z0-9]+', output)
                if match:
                    auth_url = match.group(0)
                    qr_code_data = None
                    try:
                        qr_code_data = _build_qr_data(auth_url)
                        if qr_code_data:
                            logger.info(f"✅ QR code generated: {len(qr_code_data)} bytes")
                    except Exception as exc:
                        logger.error(f'QR generation error: {exc}', exc_info=True)

                    socketio.emit('tailscale_auth_url', {'url': auth_url, 'qr_code': qr_code_data}, namespace='/')
                    return

                time.sleep(2)
                final_status = subprocess.run(['tailscale', 'status', '--json'], capture_output=True, text=True, timeout=10)
                if final_status.returncode == 0:
                    status_data = json.loads(final_status.stdout)
                    if status_data.get('BackendState') == 'Running':
                        socketio.emit('tailscale_connect_response', {'success': True, 'message': 'Bağlantı başarılı'}, namespace='/')
                    else:
                        socketio.emit('tailscale_connect_response', {
                            'success': False,
                            'message': 'Bağlantı başlatıldı ama henüz aktif değil. Lütfen bekleyin veya QR kodu okutun.'
                        }, namespace='/')
                else:
                    socketio.emit('tailscale_connect_response', {
                        'success': False,
                        'message': 'Bağlantı hatası: Auth URL bulunamadı.'
                    }, namespace='/')

            except subprocess.TimeoutExpired:
                socketio.emit('tailscale_connect_response', {
                    'success': False,
                    'message': 'Bağlantı işlemi zaman aşımına uğradı.'
                }, namespace='/')
            except Exception as exc:
                logger.error(f'Tailscale connect thread error: {exc}')
                socketio.emit('tailscale_connect_response', {
                    'success': False,
                    'message': f'Bağlantı hatası: {str(exc)}'
                }, namespace='/')
            finally:
                task_manager.end_task()

        threading.Thread(target=run_connect, daemon=True).start()

    @socketio.on('tailscale_disconnect')
    def handle_tailscale_disconnect():
        try:
            result = subprocess.run(
                ['sudo', 'tailscale', 'down'],
                capture_output=True,
                text=True,
                timeout=20
            )

            if result.returncode == 0:
                emit('tailscale_disconnect_response', {
                    'success': True,
                    'message': 'Tailscale bağlantısı kesildi'
                })
            else:
                emit('error', {'message': f'Bağlantı kesilemedi: {result.stderr}'})

        except Exception as exc:
            logger.error(f'Tailscale disconnect error: {exc}')
            emit('error', {'message': f'Hata: {str(exc)}'})

    @socketio.on('tailscale_logout')
    def handle_tailscale_logout():
        try:
            result = subprocess.run(
                ['sudo', 'tailscale', 'logout'],
                capture_output=True,
                text=True,
                timeout=20
            )

            backend_state = 'Unknown'
            status_check = subprocess.run(
                ['tailscale', 'status', '--json'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if status_check.returncode == 0:
                try:
                    status_data = json.loads(status_check.stdout)
                    backend_state = status_data.get('BackendState', 'Unknown')
                except Exception:
                    backend_state = 'Unknown'

            if result.returncode == 0 or backend_state in ('NeedsLogin', 'NoState', 'Stopped'):
                emit('tailscale_logout_response', {
                    'success': True,
                    'message': 'Tailscale oturumu kapatıldı. Artık başka bir ağa bağlanabilirsiniz.',
                    'state': backend_state
                })
            else:
                error_text = (result.stderr or result.stdout or '').strip()
                emit('tailscale_logout_response', {
                    'success': False,
                    'message': f'Oturum kapatılamadı: {error_text or "Bilinmeyen hata"}',
                    'state': backend_state
                })

        except Exception as exc:
            logger.error(f'Tailscale logout error: {exc}')
            emit('tailscale_logout_response', {
                'success': False,
                'message': f'Oturum kapatma hatası: {str(exc)}'
            })

    @socketio.on('tailscale_invite_users_qr')
    def handle_tailscale_invite_users_qr(data=None):
        invite_url = 'https://login.tailscale.com/admin/users'
        try:
            emit('tailscale_invite_users_qr_response', {
                'success': True,
                'url': invite_url,
                'qr_code': _build_qr_data(invite_url)
            })
        except Exception as exc:
            logger.error(f'Tailscale invite QR error: {exc}')
            emit('tailscale_invite_users_qr_response', {
                'success': False,
                'message': f'QR oluşturulamadı: {str(exc)}'
            })

    @socketio.on('tailscale_funnel_enable')
    def handle_tailscale_funnel_enable(data=None):
        try:
            logger.info('Enabling Tailscale Funnel for port 8000')
            hostname_result = subprocess.run(
                ['tailscale', 'status', '--json'],
                capture_output=True,
                text=True,
                timeout=5
            )
            status_data = {}
            hostname = 'kuvoz'
            dns_name = 'kuvoz.tailnet.ts.net'

            if hostname_result.returncode == 0:
                status_data = json.loads(hostname_result.stdout)
                hostname = status_data.get('Self', {}).get('HostName', 'kuvoz')
                dns_name_raw = status_data.get('Self', {}).get('DNSName', '')
                dns_name = dns_name_raw.rstrip('.')

            subprocess.run(
                ['sudo', 'tailscale', 'funnel', 'reset'],
                capture_output=True,
                text=True,
                timeout=10
            )
            result = subprocess.run(
                ['sudo', 'tailscale', 'funnel', '--bg', '8000'],
                capture_output=True,
                text=True,
                timeout=15
            )

            logger.info(f'Funnel result: {result.returncode}, stdout: {result.stdout}, stderr: {result.stderr}')
            if 'not enabled' in result.stderr or 'not enabled' in result.stdout:
                enable_url_match = re.search(r'https://login\.tailscale\.com/[^\s]+', result.stderr + result.stdout)
                enable_url = enable_url_match.group(0) if enable_url_match else 'https://login.tailscale.com/admin/machines'
                emit('tailscale_funnel_enable_required', {
                    'success': False,
                    'enable_url': enable_url,
                    'message': 'Funnel tailnet\'te aktif değil. Lütfen enable edin.'
                })
                return

            time.sleep(1)
            status_result = subprocess.run(
                ['tailscale', 'funnel', 'status'],
                capture_output=True,
                text=True,
                timeout=5
            )
            logger.info(f'Funnel status: {status_result.stdout}{status_result.stderr}')

            funnel_url = f'https://{dns_name}'
            tailscale_ip = None
            self_info = status_data.get('Self', {})
            tailscale_ips = self_info.get('TailscaleIPs', [])
            if tailscale_ips:
                tailscale_ip = tailscale_ips[0]
            ssh_command = f'ssh vet@{tailscale_ip}' if tailscale_ip else f'ssh vet@{dns_name}'

            emit('tailscale_funnel_response', {
                'success': True,
                'enabled': True,
                'funnel_url': funnel_url,
                'ssh_command': ssh_command,
                'tailscale_ip': tailscale_ip,
                'message': 'Funnel aktifleştirildi'
            })

        except Exception as exc:
            logger.error(f'Tailscale funnel enable error: {exc}')
            emit('error', {'message': f'Funnel hatası: {str(exc)}'})

    @socketio.on('tailscale_funnel_disable')
    def handle_tailscale_funnel_disable(data=None):
        try:
            logger.info('Disabling Tailscale Funnel')
            result = subprocess.run(
                ['sudo', 'tailscale', 'funnel', 'reset'],
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=10
            )
            logger.info(f'Funnel reset result: {result.returncode}, stdout: {result.stdout}, stderr: {result.stderr}')
            emit('tailscale_funnel_response', {
                'success': True,
                'enabled': False,
                'message': 'Funnel kapatıldı'
            })
        except Exception as exc:
            logger.error(f'Tailscale funnel disable error: {exc}')
            emit('error', {'message': f'Funnel kapatma hatası: {str(exc)}'})

    @socketio.on('tailscale_funnel_status')
    def handle_tailscale_funnel_status(data=None):
        try:
            result = subprocess.run(
                ['tailscale', 'funnel', 'status'],
                capture_output=True,
                text=True,
                timeout=10
            )

            output = result.stdout + result.stderr
            is_enabled = 'https://' in output and result.returncode == 0

            if is_enabled:
                url_match = re.search(r'https://[^\s]+', output)
                funnel_url = url_match.group(0) if url_match else None
                hostname_result = subprocess.run(
                    ['tailscale', 'status', '--json'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                hostname = 'kuvoz'
                if hostname_result.returncode == 0:
                    status_data = json.loads(hostname_result.stdout)
                    hostname = status_data.get('Self', {}).get('HostName', 'kuvoz')

                emit('tailscale_funnel_response', {
                    'success': True,
                    'enabled': True,
                    'funnel_url': funnel_url,
                    'ssh_command': f'ssh vet@{hostname}.tailnet.ts.net'
                })
            else:
                emit('tailscale_funnel_response', {
                    'success': True,
                    'enabled': False
                })

        except Exception as exc:
            logger.error(f'Tailscale funnel status error: {exc}')
            emit('tailscale_funnel_response', {
                'success': True,
                'enabled': False
            })

    @socketio.on('tailscale_create_share')
    def handle_tailscale_create_share(data=None):
        try:
            logger.info('Creating Tailscale share link for remote support')
            status_check = subprocess.run(
                ['tailscale', 'status', '--json'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if status_check.returncode != 0:
                emit('error', {'message': 'Tailscale bağlı değil. Önce bağlantı kurun.'})
                return

            status_data = json.loads(status_check.stdout)
            if status_data.get('BackendState') != 'Running':
                emit('error', {'message': 'Tailscale aktif değil. Önce bağlantı kurun.'})
                return

            self_info = status_data.get('Self', {})
            tailscale_ips = self_info.get('TailscaleIPs', [])
            hostname = self_info.get('HostName', 'kuvoz')
            if not tailscale_ips:
                emit('error', {'message': 'Tailscale IP adresi bulunamadı'})
                return

            tailscale_ip = tailscale_ips[0]
            subprocess.run(
                ['sudo', 'tailscale', 'serve', 'status', '--json'],
                capture_output=True,
                text=True,
                timeout=10
            )

            web_url = f'http://{tailscale_ip}:8000'
            admin_url = f'https://{hostname}.tailnet.ts.net:8000'
            share_info = {
                'web_url': web_url,
                'admin_url': admin_url,
                'tailscale_ip': tailscale_ip,
                'hostname': hostname,
                'instructions': [
                    '1. Tailscale uygulamasını indirin (tailscale.com)',
                    '2. Aynı Tailscale ağına katılın',
                    f'3. Tarayıcıda şu adresi açın: {web_url}',
                    '4. Kuvoz kontrol paneline erişebilirsiniz'
                ]
            }

            logger.info(f'Share link created: {web_url}')
            emit('tailscale_share_response', {
                'success': True,
                'share_info': share_info
            })

        except subprocess.TimeoutExpired:
            logger.error('Tailscale share timeout')
            emit('error', {'message': 'Tailscale yanıt vermiyor'})
        except Exception as exc:
            logger.error(f'Tailscale create share error: {exc}')
            emit('error', {'message': f'Paylaşım linki oluşturulamadı: {str(exc)}'})
