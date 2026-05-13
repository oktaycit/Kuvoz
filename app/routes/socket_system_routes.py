"""Socket.IO system and legacy bridge route registration."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time

from flask_socketio import emit

from app.services.hostname_manager import set_device_hostname, validate_hostname


def register_system_socket_routes(
    socketio,
    *,
    kuvoz_server,
    logger,
    ai_available: bool,
    gpio_available: bool,
    script_dir: str,
    task_manager,
    perform_disk_cleanup,
    get_git_version_info,
    get_git_update_diagnostics,
    classify_git_update_error,
    handle_update_slider_logic,
    handle_save_settings_logic,
):
    """Register system maintenance, AI toggle and legacy socket handlers."""

    def _build_status_payload():
        return {
            'type': 'status_response',
            'sensors': kuvoz_server.sensor_data,
            'buttons': kuvoz_server.button_states,
            'gpio_outputs': kuvoz_server.gpio_output_states,
            'sliders': kuvoz_server.get_effective_slider_values(),
            'timers': kuvoz_server.get_timer_data(),
            'system': kuvoz_server.get_effective_system_status(),
            'ai_available': ai_available,
            'ai_enabled': kuvoz_server.ai_enabled,
            'ai_health': kuvoz_server.get_ai_health_status(),
            'system_settings': kuvoz_server.system_settings,
            'care_settings': kuvoz_server.get_care_status(),
        }

    def _run_system_command(command: str, skipped_message: str):
        time.sleep(2)
        if gpio_available:
            os.system(command)
        else:
            logger.warning(skipped_message)

    @socketio.on('save_settings_old')
    def handle_save_settings_old(data=None):
        try:
            if kuvoz_server.save_settings():
                emit('success', {
                    'type': 'success',
                    'message': 'Ayarlar kaydedildi'
                })
                logger.info('Settings saved successfully')
            else:
                emit('error', {
                    'type': 'error',
                    'message': 'Ayar kaydetme başarısız'
                })
        except Exception as exc:
            logger.error(f'Save settings error: {exc}')
            emit('error', {
                'type': 'error',
                'message': f'Ayar kaydetme hatası: {str(exc)}'
            })

    @socketio.on('toggle_ai')
    def handle_toggle_ai(data):
        try:
            payload = data if isinstance(data, dict) else {}
            enabled = kuvoz_server.normalize_ai_enabled_value(payload.get('enabled', False))

            if not ai_available:
                emit('error', {
                    'type': 'warning',
                    'message': 'AI modülü bu cihazda kullanılamıyor'
                })
                return

            if not kuvoz_server.ai_manager:
                emit('error', {
                    'type': 'warning',
                    'message': 'AI Manager başlatılamadı'
                })
                return

            old_state = kuvoz_server.ai_enabled

            if enabled == old_state and bool(kuvoz_server.ai_manager.started) == bool(enabled):
                emit('ai_status', {
                    'enabled': kuvoz_server.ai_enabled,
                    'message': 'AI durumu zaten aynı',
                    'health': kuvoz_server.get_ai_health_status()
                }, broadcast=True)
                return

            ok, message, health = kuvoz_server._set_ai_runtime_enabled(enabled, source='ui_toggle')
            if ok:
                kuvoz_server.save_settings()
                emit('ai_status', {
                    'enabled': kuvoz_server.ai_enabled,
                    'message': message,
                    'health': health
                }, broadcast=True)
            else:
                kuvoz_server.set_ai_enabled_preference(False, source='ui_toggle_failed')
                emit('error', {
                    'type': 'error' if enabled else 'warning',
                    'message': f'AI durumu güncellenemedi: {message}'
                })
                emit('ai_status', {
                    'enabled': kuvoz_server.ai_enabled,
                    'message': 'AI durumu hatalı',
                    'health': health
                }, broadcast=True)

        except Exception as exc:
            logger.error(f'Toggle AI error: {exc}', exc_info=True)
            emit('error', {
                'type': 'error',
                'message': f'AI toggle hatası: {str(exc)}'
            })

    @socketio.on('shutdown')
    def handle_shutdown(data=None):
        logger.info('🔴 SHUTDOWN EVENT RECEIVED!')
        try:
            logger.info('System shutdown requested')
            kuvoz_server.save_settings()
            emit('success', {
                'type': 'success',
                'message': 'Sistem kapatılıyor...'
            })
            threading.Thread(
                target=_run_system_command,
                args=('sudo shutdown -h now', 'Shutdown skipped - GPIO not available (simulation mode)'),
                daemon=True,
            ).start()
            logger.info('🔴 Shutdown thread launched')
        except Exception as exc:
            logger.error(f'🔴 Shutdown error: {exc}')
            emit('error', {
                'type': 'error',
                'message': f'Kapatma hatası: {str(exc)}'
            })

    @socketio.on('restart')
    def handle_restart(data=None):
        logger.info('🟢 RESTART EVENT RECEIVED!')
        try:
            logger.info('System restart requested')
            kuvoz_server.save_settings()
            emit('success', {
                'type': 'success',
                'message': 'Sistem yeniden başlatılıyor...'
            })
            threading.Thread(
                target=_run_system_command,
                args=('sudo reboot', 'Restart skipped - GPIO not available (simulation mode)'),
                daemon=True,
            ).start()
            logger.info('🟢 Restart thread launched')
        except Exception as exc:
            logger.error(f'🟢 Restart error: {exc}')
            emit('error', {
                'type': 'error',
                'message': f'Yeniden başlatma hatası: {str(exc)}'
            })

    @socketio.on('disk_cleanup')
    def handle_disk_cleanup(data=None):
        try:
            emit('disk_cleanup_progress', {'message': 'Disk temizliği başlatılıyor (sistem, sensör ve AI logları temizleniyor)...'})
            logger.info("🧹 Starting manual disk cleanup via WebSocket...")

            cleanup_result = perform_disk_cleanup(
                sensor_logger=kuvoz_server.sensor_logger,
                ai_vitals_logger=getattr(kuvoz_server, 'ai_vitals_logger', None),
                reason='disk_cleanup',
                trigger='settings_disk_cleanup',
            )

            emit('disk_cleanup_response', {
                'success': cleanup_result['success'],
                'message': cleanup_result['message'],
                'details': cleanup_result,
            })

            if cleanup_result['success']:
                logger.info(f"✅ {cleanup_result['message']}")
            else:
                logger.error(f"❌ {cleanup_result['message']}")

        except Exception as exc:
            logger.error(f"Disk cleanup error: {exc}")
            emit('error', {'message': f'Disk temizleme hatası: {str(exc)}'})

    @socketio.on('set_hostname')
    def handle_set_hostname(data=None):
        payload = data if isinstance(data, dict) else {}
        valid, hostname, validation_error = validate_hostname(payload.get('hostname'))
        if not valid:
            emit('hostname_update_response', {
                'success': False,
                'message': validation_error,
                'hostname': hostname,
            })
            return

        if not task_manager.start_task('set_hostname'):
            emit('hostname_update_response', {
                'success': False,
                'message': f'Şu anda başka bir işlem devam ediyor: {task_manager.current_task}',
            })
            return

        update_tailscale = payload.get('update_tailscale', True) is not False

        def run_hostname_update():
            try:
                socketio.emit(
                    'hostname_update_progress',
                    {'message': f'Hostname güncelleniyor: {hostname}'},
                    namespace='/',
                )
                logger.info(f"🏷️ Hostname update requested: {hostname} (tailscale={update_tailscale})")
                result = set_device_hostname(
                    hostname,
                    update_tailscale=update_tailscale,
                )
                socketio.emit('hostname_update_response', result, namespace='/')
                if result.get('success'):
                    logger.info(f"✅ Hostname update completed: {result.get('message')}")
                else:
                    logger.error(f"❌ Hostname update failed: {result.get('message')}")
            except Exception as exc:
                logger.error(f"Hostname update error: {exc}", exc_info=True)
                socketio.emit(
                    'hostname_update_response',
                    {'success': False, 'message': f'Hostname güncelleme hatası: {str(exc)}'},
                    namespace='/',
                )
            finally:
                task_manager.end_task()

        threading.Thread(target=run_hostname_update, daemon=True).start()

    @socketio.on('system_update')
    def handle_system_update(data=None):
        try:
            emit('system_update_progress', {'message': 'Güncelleme kontrol ediliyor...'})
            logger.info("🆙 Starting robust system update via WebSocket...")

            diagnostics = get_git_update_diagnostics()
            current_branch = diagnostics['branch']
            logger.info(f"📌 Current branch: {current_branch}")

            if diagnostics['dirty_files']:
                emit('system_update_response', {
                    'success': False,
                    'message': '❌ Güncelleme engellendi: yerel değişiklikler var. Önce "Geri Al" ile temizleyin veya commit alın.',
                    'error_type': 'dirty_worktree',
                    'error_details': '\n'.join(diagnostics['dirty_files']),
                    'dirty_files': diagnostics['dirty_files'],
                    'diagnostics': diagnostics
                })
                return

            if current_branch in ('HEAD', 'Unknown', ''):
                emit('system_update_response', {
                    'success': False,
                    'message': '❌ Aktif branch belirlenemedi. Detached HEAD durumunda otomatik güncelleme yapılamaz.',
                    'error_type': 'detached_head',
                    'diagnostics': diagnostics
                })
                return

            emit('system_update_progress', {'message': f'Kodlar kontrol ediliyor ({current_branch})...'})
            git_info_before = get_git_version_info()

            fetch_result = subprocess.run(
                ['git', 'fetch', 'origin', current_branch],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=script_dir
            )

            if fetch_result.returncode != 0:
                error_type, user_message, error_output = classify_git_update_error(
                    fetch_result.stderr or fetch_result.stdout,
                    current_branch
                )
                emit('system_update_response', {
                    'success': False,
                    'message': user_message,
                    'error_type': error_type,
                    'error_details': error_output,
                    'diagnostics': diagnostics
                })
                return

            emit('system_update_progress', {'message': f'Güncelleme uygulanıyor ({current_branch})...'})
            merge_result = subprocess.run(
                ['git', 'merge', '--ff-only', 'FETCH_HEAD'],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=script_dir
            )

            if merge_result.returncode != 0:
                error_type, user_message, error_output = classify_git_update_error(
                    merge_result.stderr or merge_result.stdout,
                    current_branch
                )
                emit('system_update_response', {
                    'success': False,
                    'message': user_message,
                    'error_type': error_type,
                    'error_details': error_output,
                    'diagnostics': diagnostics
                })
                return

            git_info_after = get_git_version_info()

            requirements_changed = False
            if git_info_before['hash'] != 'Unknown' and git_info_after['hash'] != 'Unknown':
                requirements_diff = subprocess.run(
                    ['git', 'diff', '--name-only', git_info_before['hash'], git_info_after['hash'], '--', 'requirements.txt'],
                    capture_output=True,
                    text=True,
                    timeout=20,
                    cwd=script_dir
                )
                requirements_changed = requirements_diff.returncode == 0 and bool(requirements_diff.stdout.strip())

            if requirements_changed:
                emit('system_update_progress', {'message': 'Yeni bağımlılıklar kuruluyor (pip install)...'})
                logger.info("📦 requirements.txt changed, running pip install...")
                pip_cmd = [sys.executable, '-m', 'pip', 'install', '-r', os.path.join(script_dir, 'requirements.txt'), '--break-system-packages']
                pip_result = subprocess.run(
                    pip_cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=script_dir
                )
                if pip_result.returncode != 0:
                    logger.error(f"❌ Pip install failed: {pip_result.stderr}")
                    emit('system_update_progress', {'message': '⚠️ Kütüphaneler güncellenirken hata oluştu.'})

            if git_info_before['hash'] == git_info_after['hash']:
                message = 'Sistem zaten güncel.'
            else:
                message = f'Sistem güncellendi: {git_info_before["hash"]} → {git_info_after["hash"]}. Servis yeniden başlatılmalı.'

            emit('system_update_response', {
                'success': True,
                'message': message,
                'git_hash': git_info_after['hash'],
                'git_branch': git_info_after['branch'],
                'needs_restart': git_info_before['hash'] != git_info_after['hash'],
                'diagnostics': get_git_update_diagnostics()
            })
            logger.info(f"✅ System update completed: {message}")

        except Exception as exc:
            logger.error(f"System update error: {exc}")
            emit('error', {'message': f'Gelişmiş güncelleme hatası: {str(exc)}'})

    @socketio.on('system_reset')
    def handle_system_reset(data=None):
        try:
            emit('system_reset_progress', {'message': 'Değişiklikler temizleniyor ve geri dönülüyor...'})
            logger.info("⏪ Starting robust system reset (git reset --hard)...")

            reset_result = subprocess.run(
                ['git', 'reset', '--hard', 'HEAD@{1}'],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=script_dir
            )

            if reset_result.returncode == 0:
                subprocess.run(['git', 'clean', '-fd'], capture_output=True, cwd=script_dir)
                git_info = get_git_version_info()
                emit('system_reset_response', {
                    'success': True,
                    'message': f'Sistem bir önceki sürüme döndürüldü: {git_info["hash"]}',
                    'git_hash': git_info['hash'],
                    'diagnostics': get_git_update_diagnostics()
                })
                logger.info(f"✅ System reset completed: {git_info['hash']}")
            else:
                subprocess.run(['git', 'reset', '--hard', 'HEAD'], capture_output=True, cwd=script_dir)
                subprocess.run(['git', 'clean', '-fd'], capture_output=True, cwd=script_dir)
                emit('system_reset_response', {
                    'success': False,
                    'message': f'Tam geri dönme başarısız olsa da yerel değişiklikler temizlendi: {reset_result.stderr}',
                    'diagnostics': get_git_update_diagnostics()
                })

        except Exception as exc:
            logger.error(f"System reset error: {exc}")
            emit('error', {'message': f'Geri alma hatası: {str(exc)}'})

    @socketio.on('message')
    def handle_message(data):
        try:
            command = data.get('command')
            command_data = data.get('data', {})
            logger.info(f"📥 Received command: {command} with data: {command_data}")

            if command == 'get_status':
                emit('status_response', _build_status_payload())
            elif command == 'toggle_button':
                name = command_data.get('name')
                pin = command_data.get('pin')
                state = command_data.get('state')
                if kuvoz_server.toggle_button(name, pin, state):
                    emit('success', {
                        'type': 'success',
                        'message': f'Button {name} {"ON" if state else "OFF"}'
                    })
                else:
                    emit('error', {
                        'type': 'error',
                        'message': f'Button {name} control failed'
                    })
            elif command == 'update_slider':
                handle_update_slider_logic(command_data)
            elif command == 'save_settings':
                handle_save_settings_logic(command_data)
            elif command == 'shutdown':
                logger.info("Shutdown requested")
                kuvoz_server.save_settings()
                emit('success', {
                    'type': 'success',
                    'message': 'System shutting down...'
                })
                threading.Timer(2.0, lambda: os.system("sudo shutdown -h now")).start()
            elif command == 'restart':
                logger.info("Restart requested")
                kuvoz_server.save_settings()
                emit('success', {
                    'type': 'success',
                    'message': 'System restarting...'
                })
                threading.Timer(2.0, lambda: os.system("sudo reboot")).start()
            else:
                emit('error', {
                    'type': 'error',
                    'message': f'Unknown command: {command}'
                })

        except Exception as exc:
            logger.error(f"WebSocket message error: {exc}")
            emit('error', {
                'type': 'error',
                'message': f'Command processing error: {str(exc)}'
            })
