import firebase_admin
from firebase_admin import credentials, db
import threading
import logging
import os
import socket
import time

logger = logging.getLogger(__name__)

class FirebaseManager:
    def __init__(self, cred_path=None, db_url=None, device_id=None, device_name=None):
        self.connected = False
        self.device_id = device_id or os.getenv('KUVOZ_DEVICE_ID', 'kuvoz1')
        self.device_name = device_name or os.getenv('KUVOZ_DEVICE_NAME', 'Kuvoz Incubator')
        self.db_url = db_url or os.getenv('KUVOZ_FIREBASE_URL', 'https://kuvoz-vet-system-default-rtdb.europe-west1.firebasedatabase.app/')
        self.cred_path = cred_path or os.getenv('KUVOZ_FIREBASE_CRED', 'config/kuvoz-firebase-key.json')
        
        # Fallback paths
        possible_creds = [
            self.cred_path,
            '/home/oktay/kuvoz/config/kuvoz-firebase-key.json',
            '/home/vet/kuvoz/config/kuvoz-firebase-key.json',
            'config/serviceAccountKey.json'
        ]

        cred_found = None
        for p in possible_creds:
            if os.path.exists(p):
                cred_found = p
                break
        
        if not cred_found:
            logger.warning("⚠️  Firebase credentials not found in any standard location.")
            return

        try:
            cred = credentials.Certificate(cred_found)
            
            # Avoid re-initialization error
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred, {
                    'databaseURL': self.db_url
                })
            
            self.connected = True
            
            # Standard paths (consistent with bridge/mobile app)
            base_path = f'devices/{self.device_id}'
            self.device_ref = db.reference(base_path)
            self.sensors_ref = db.reference(f'{base_path}/sensors')
            self.controls_ref = db.reference(f'{base_path}/controls')
            self.commands_ref = db.reference(f'{base_path}/commands/pending')
            self.status_ref = db.reference(f'{base_path}/status')
            
            logger.info(f"✅ Firebase initialized: {self.db_url} ({self.device_id})")
            
        except Exception as e:
            logger.error(f"❌ Firebase init error: {e}")
            self.connected = False

    def register_device(self, version='3.0'):
        if not self.connected: return
        try:
            info = {
                'name': self.device_name,
                'deviceId': self.device_id,
                'version': version,
                'ipAddress': self._get_ip(),
                'lastSeen': {'.sv': 'timestamp'}
            }
            self.device_ref.child('info').set(info)
            self.status_ref.update({
                'online': True, 
                'lastUpdate': {'.sv': 'timestamp'},
                'embedded': True
            })
            logger.info(f"✅ Device registered in Firebase: {self.device_name}")
        except Exception as e:
            logger.error(f"Firebase registration error: {e}")

    def _get_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return 'unknown'

    def update_sensor_data(self, sensor_data):
        """Standard sensor update (dict of dicts with 'value')"""
        if not self.connected: return
        try:
            fb_data = {}
            for key, data in sensor_data.items():
                if isinstance(data, dict):
                    fb_data[key] = {
                        'value': data.get('value'),
                        'unit': data.get('unit', ''),
                        'status': data.get('status', ''),
                        'timestamp': {'.sv': 'timestamp'}
                    }
                else:
                    fb_data[key] = {
                        'value': data,
                        'timestamp': {'.sv': 'timestamp'}
                    }
            self.sensors_ref.update(fb_data)
            # Update heart beat
            self.status_ref.update({'lastUpdate': {'.sv': 'timestamp'}, 'online': True})
        except Exception as e:
            logger.error(f"Firebase data update error: {e}")

    def sync_controls(self, button_states, slider_values):
        """Sync full state of controls to Firebase"""
        if not self.connected: return
        try:
            data = {
                'buttons': button_states,
                'sliders': slider_values,
                'lastSync': {'.sv': 'timestamp'}
            }
            self.controls_ref.set(data)
        except Exception as e:
            logger.error(f"Firebase sync error: {e}")

    def update_button_state(self, button_id, state):
        if not self.connected: return
        try:
            self.controls_ref.child(f'buttons/{button_id}').update({
                'state': state,
                'timestamp': {'.sv': 'timestamp'}
            })
        except Exception as e:
            logger.error(f"Firebase button update error: {e}")

    def update_slider_value(self, slider_id, value):
        if not self.connected: return
        try:
            self.controls_ref.child(f'sliders/{slider_id}').update({
                'value': value,
                'timestamp': {'.sv': 'timestamp'}
            })
        except Exception as e:
            logger.error(f"Firebase slider update error: {e}")

    def listen_for_commands(self, callback):
        """Robust command listener (uses commands/pending queue)"""
        if not self.connected: return
        
        def listener(event):
            try:
                if event.event_type == 'put' and event.data:
                    if isinstance(event.data, dict):
                        for cmd_id, cmd_data in event.data.items():
                            if isinstance(cmd_data, dict) and not cmd_data.get('processed'):
                                self._process_cmd(cmd_id, cmd_data, callback)
                    elif event.path != '/':
                        # Single child added/changed
                        cmd_id = event.path.strip('/')
                        if isinstance(event.data, dict) and not event.data.get('processed'):
                             self._process_cmd(cmd_id, event.data, callback)
            except Exception as e:
                logger.error(f"Command listener internal error: {e}")

        try:
            self.commands_ref.listen(listener)
            logger.info("✅ Firebase command listener started (devices/{}/commands/pending)".format(self.device_id))
        except Exception as e:
            logger.error(f"Firebase listener failed to start: {e}")

    def _process_cmd(self, cmd_id, cmd_data, callback):
        try:
            cmd_type = cmd_data.get('type')
            data = cmd_data.get('data', {})
            
            logger.info(f"📨 FB Command [{cmd_id}]: {cmd_type}")
            
            # Map type/data to path/value for backward compatibility with handle_firebase_control
            # type: toggle_button -> data: {button: 'b1', state: True}
            # type: update_slider -> data: {slider: 'sld1', value: 30}
            
            if cmd_type == 'toggle_button':
                path = f"/{data.get('button')}"
                val = data.get('state')
                callback(path, val)
            elif cmd_type == 'update_slider':
                path = f"/{data.get('slider')}"
                val = data.get('value')
                callback(path, val)
            else:
                # Direct callback for other types
                callback(cmd_type, data)
            
            # Mark as processed
            self.commands_ref.child(cmd_id).update({
                'processed': True,
                'processedAt': {'.sv': 'timestamp'}
            })
        except Exception as e:
             logger.error(f"FB Command execution error: {e}")
             self.commands_ref.child(cmd_id).update({
                'processed': True,
                'error': str(e),
                'processedAt': {'.sv': 'timestamp'}
            })
