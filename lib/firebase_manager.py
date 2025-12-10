import firebase_admin
from firebase_admin import credentials, db
import threading
import logging
import os
import json

logger = logging.getLogger(__name__)

class FirebaseManager:
    def __init__(self, cred_path='config/serviceAccountKey.json', db_url=None):
        self.connected = False
        self.user_id = 'USER_DEFAULT'  # Should be configurable
        
        # If db_url is not provided, try to find it in the credentials file or env
        # usually db_url is passed or configured in the app options
        if not db_url:
            # Placeholder default or error
            # Ideally user should provide this. I'll use a placeholder that needs update.
            self.db_url = 'https://YOUR_PROJECT_ID.firebaseio.com/' 
        else:
            self.db_url = db_url

        try:
            if not os.path.exists(cred_path):
                logger.warning(f"⚠️  Firebase credentials not found at {cred_path}")
                logger.warning("   Please ask user to provide serviceAccountKey.json")
                return

            cred = credentials.Certificate(cred_path)
            
            # Check if app is already initialized to avoid errors on reload
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred, {
                    'databaseURL': self.db_url
                })
            
            self.connected = True
            logger.info("✅ Firebase initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Firebase init error: {e}")
            self.connected = False

    def update_sensor_data(self, sensor_data):
        """
        Push sensor data to Firebase
        path: users/{user_id}/device/sensors
        """
        if not self.connected:
            return

        try:
            # Simplify structure for firebase
            clean_data = {}
            for key, val in sensor_data.items():
                if isinstance(val, dict) and 'value' in val:
                    clean_data[key] = val['value']
                else:
                    clean_data[key] = val
                    
            # Add timestamp
            clean_data['timestamp'] = {'.sv': 'timestamp'}
            
            ref = db.reference(f'users/{self.user_id}/device/sensors')
            ref.update(clean_data)
            
        except Exception as e:
            logger.error(f"Firebase update error: {e}")

    def update_status(self, status_data):
        """
        Push device status (online, ip, etc)
        """
        if not self.connected:
            return
        try:
            ref = db.reference(f'users/{self.user_id}/device/status')
            ref.update(status_data)
        except Exception as e:
            logger.error(f"Firebase status update error: {e}")

    def listen_for_controls(self, callback):
        """
        Listen for changes in controls
        path: users/{user_id}/device/controls
        """
        if not self.connected:
            return

        def listener(event):
            try:
                # event.path is something like "/" or "/b1"
                # event.data is the value
                if event.data is None:
                    return
                
                logger.info(f"🔥 Firebase Control: {event.path} = {event.data}")
                callback(event.path, event.data)
            except Exception as e:
                logger.error(f"Firebase listener error: {e}")

        try:
            ref = db.reference(f'users/{self.user_id}/device/controls')
            ref.listen(listener)
            logger.info("✅ Firebase control listener started")
        except Exception as e:
            logger.error(f"Failed to start Firebase listener: {e}")
