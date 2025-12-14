#!/usr/bin/env python3
"""
Kuvoz Firebase Bridge Service
Connects Raspberry Pi GPIO/sensors with Firebase Realtime Database
"""

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import time
import logging
from threading import Thread
from datetime import datetime
import os

# Device configuration
DEVICE_ID = os.getenv('KUVOZ_DEVICE_ID', 'kuvoz1')
DEVICE_NAME = os.getenv('KUVOZ_DEVICE_NAME', 'Kuvoz Cage A')
FIREBASE_CRED_PATH = os.getenv('KUVOZ_FIREBASE_CRED', '/home/oktay/kuvoz/config/kuvoz-firebase-key.json')
FIREBASE_DB_URL = os.getenv('KUVOZ_FIREBASE_URL', 'https://kuvoz-vet-system-default-rtdb.europe-west1.firebasedatabase.app/')

# GPIO imports
try:
    import RPi.GPIO as GPIO
    from lib.DHT_Native import read_dht_sensor
    from lib.DFRobot_Oxygen import DFRobot_Oxygen_IIC
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logging.warning("GPIO not available - running in simulation mode")

# GPIO Pin Configuration
BUTTON_PINS = {
    'b1': 5,   # Therapeutic Lighting
    'b2': 6,   # Nebulizer
    'b3': 13,  # Humidity Control
    'b4': 16,  # Heating Pad
    'b5': 19,  # IR Heater
    'b6': 20,  # Ventilation Fan
    'b7': 21,  # UV Sterilization
    'b8': 26   # Ozone Sterilizer
}

BUTTON_NAMES = {
    'b1': 'Therapeutic Lighting',
    'b2': 'Nebulizer',
    'b3': 'Humidity Control',
    'b4': 'Heating Pad',
    'b5': 'IR Heater',
    'b6': 'Ventilation Fan',
    'b7': 'UV Sterilization',
    'b8': 'Ozone Sterilizer'
}

DHT_PIN = 15


class FirebaseBridge:
    def __init__(self):
        """Initialize Firebase Bridge"""
        self.button_states = {k: False for k in BUTTON_PINS.keys()}
        self.last_sensor_read = 0
        self.sensor_read_interval = 5  # seconds
        
        # Initialize Firebase
        self.init_firebase()
        
        # Initialize GPIO
        if GPIO_AVAILABLE:
            self.init_gpio()
        
        # Register device
        self.register_device()
        
        # Start listening to commands
        self.listen_to_commands()
        
        logging.info(f"✅ Firebase Bridge initialized for {DEVICE_NAME} (ID: {DEVICE_ID})")
    
    def init_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            cred = credentials.Certificate(FIREBASE_CRED_PATH)
            firebase_admin.initialize_app(cred, {
                'databaseURL': FIREBASE_DB_URL
            })
            
            # Create references
            self.devices_ref = db.reference(f'devices/{DEVICE_ID}')
            self.sensors_ref = db.reference(f'devices/{DEVICE_ID}/sensors')
            self.controls_ref = db.reference(f'devices/{DEVICE_ID}/controls')
            self.commands_ref = db.reference(f'devices/{DEVICE_ID}/commands/pending')
            self.status_ref = db.reference(f'devices/{DEVICE_ID}/status')
            
            logging.info(f"✅ Firebase connected to {FIREBASE_DB_URL}")
        except Exception as e:
            logging.error(f"❌ Firebase initialization failed: {e}")
            raise
    
    def init_gpio(self):
        """Initialize GPIO pins"""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Setup all button pins as outputs (HIGH = OFF for active-low relay)
            for button, pin in BUTTON_PINS.items():
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.HIGH)  # Start with all OFF
            
            logging.info("✅ GPIO initialized")
        except Exception as e:
            logging.error(f"❌ GPIO initialization failed: {e}")
    
    def get_serial(self):
        """Get Raspberry Pi serial number"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('Serial'):
                        return line.split(':')[1].strip()
        except:
            pass
        return 'unknown'
    
    def get_ip_address(self):
        """Get local IP address"""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return 'unknown'
    
    def register_device(self):
        """Register device info in Firebase"""
        try:
            device_info = {
                'name': DEVICE_NAME,
                'deviceId': DEVICE_ID,
                'serial': self.get_serial(),
                'ipAddress': self.get_ip_address(),
                'version': '3.0',
                'location': 'Veteriner Kliniği',
                'lastSeen': {'.sv': 'timestamp'}
            }
            
            self.devices_ref.child('info').set(device_info)
            
            # Set initial status
            self.status_ref.set({
                'online': True,
                'gpioAvailable': GPIO_AVAILABLE,
                'errors': [],
                'lastUpdate': {'.sv': 'timestamp'}
            })
            
            # Initialize button states
            for button, pin in BUTTON_PINS.items():
                self.controls_ref.child(f'buttons/{button}').set({
                    'name': BUTTON_NAMES[button],
                    'state': False,
                    'pin': pin,
                    'timestamp': {'.sv': 'timestamp'}
                })
            
            logging.info(f"✅ Device registered: {DEVICE_NAME}")
        except Exception as e:
            logging.error(f"❌ Device registration failed: {e}")
    
    def read_sensors_loop(self):
        """Continuously read sensors and upload to Firebase"""
        logging.info("🌡️ Sensor reading thread started")
        
        while True:
            try:
                current_time = time.time()
                
                # Only read if enough time has passed
                if current_time - self.last_sensor_read < self.sensor_read_interval:
                    time.sleep(0.5)
                    continue
                
                self.last_sensor_read = current_time
                
                if GPIO_AVAILABLE:
                    # Read DHT22 sensor
                    try:
                        dht = read_dht_sensor(DHT_PIN)
                        if dht.get('success'):
                            self.sensors_ref.child('temperature').set({
                                'value': round(dht['temperature'], 1),
                                'unit': '°C',
                                'status': 'DHT22 GPIO15',
                                'timestamp': {'.sv': 'timestamp'}
                            })
                            
                            self.sensors_ref.child('humidity').set({
                                'value': round(dht['humidity'], 1),
                                'unit': '%',
                                'status': 'DHT22 GPIO15',
                                'timestamp': {'.sv': 'timestamp'}
                            })
                            
                            logging.debug(f"Temp: {dht['temperature']}°C, Hum: {dht['humidity']}%")
                    except Exception as e:
                        logging.error(f"DHT read error: {e}")
                    
                    # Read Oxygen sensor
                    try:
                        oxygen_sensor = DFRobot_Oxygen_IIC(1, 0x70)
                        oxy_value = oxygen_sensor.get_oxygen_data(20)
                        
                        self.sensors_ref.child('oxygen').set({
                            'value': round(oxy_value, 1),
                            'unit': '%',
                            'status': 'OK',
                            'timestamp': {'.sv': 'timestamp'}
                        })
                        
                        logging.debug(f"O2: {oxy_value}%")
                    except Exception as e:
                        logging.debug(f"Oxygen sensor not available: {e}")
                else:
                    # Simulation mode
                    import random
                    self.sensors_ref.child('temperature').set({
                        'value': round(20 + random.random() * 10, 1),
                        'unit': '°C',
                        'status': 'Simulation',
                        'timestamp': {'.sv': 'timestamp'}
                    })
                    
                    self.sensors_ref.child('humidity').set({
                        'value': round(50 + random.random() * 30, 1),
                        'unit': '%',
                        'status': 'Simulation',
                        'timestamp': {'.sv': 'timestamp'}
                    })
                
                # Update last seen timestamp
                self.devices_ref.child('info/lastSeen').set({'.sv': 'timestamp'})
                self.status_ref.child('online').set(True)
                self.status_ref.child('lastUpdate').set({'.sv': 'timestamp'})
                
            except Exception as e:
                logging.error(f"❌ Sensor loop error: {e}")
                self.status_ref.child('errors').push({
                    'message': str(e),
                    'timestamp': {'.sv': 'timestamp'}
                })
            
            time.sleep(0.5)
    
    def listen_to_commands(self):
        """Listen to commands from Firebase"""
        def on_command_change(event):
            try:
                if event.event_type == 'put' and event.data:
                    # Handle new commands
                    if isinstance(event.data, dict):
                        for cmd_id, cmd_data in event.data.items():
                            if isinstance(cmd_data, dict) and not cmd_data.get('processed'):
                                self.process_command(cmd_id, cmd_data)
                    
                elif event.event_type == 'child_added':
                    # New command added
                    cmd_id = event.path.split('/')[-1]
                    cmd_data = event.data
                    if isinstance(cmd_data, dict) and not cmd_data.get('processed'):
                        self.process_command(cmd_id, cmd_data)
                        
            except Exception as e:
                logging.error(f"Command listener error: {e}")
        
        # Listen to commands
        self.commands_ref.listen(on_command_change)
        logging.info("✅ Listening to commands from Firebase")
    
    def process_command(self, cmd_id, cmd_data):
        """Process a command from Firebase"""
        try:
            cmd_type = cmd_data.get('type')
            data = cmd_data.get('data', {})
            
            logging.info(f"📨 Processing command [{cmd_id}]: {cmd_type}")
            
            if cmd_type == 'toggle_button':
                button = data.get('button')
                state = data.get('state')
                self.toggle_button(button, state)
            
            elif cmd_type == 'update_slider':
                slider = data.get('slider')
                value = data.get('value')
                self.update_slider(slider, value)
            
            elif cmd_type == 'get_status':
                self.publish_full_status()
            
            # Mark command as processed
            self.commands_ref.child(cmd_id).update({
                'processed': True,
                'processedAt': {'.sv': 'timestamp'}
            })
            
        except Exception as e:
            logging.error(f"❌ Command processing error: {e}")
            self.commands_ref.child(cmd_id).update({
                'processed': True,
                'error': str(e),
                'processedAt': {'.sv': 'timestamp'}
            })
    
    def toggle_button(self, button, state):
        """Toggle a button's GPIO state"""
        if button not in BUTTON_PINS:
            logging.warning(f"Invalid button: {button}")
            return
        
        pin = BUTTON_PINS[button]
        
        if GPIO_AVAILABLE:
            try:
                # Active-low relay: LOW = ON, HIGH = OFF
                gpio_value = GPIO.LOW if state else GPIO.HIGH
                GPIO.output(pin, gpio_value)
                self.button_states[button] = state
                
                logging.info(f"🔘 Button {button} ({BUTTON_NAMES[button]}): {'ON' if state else 'OFF'}")
            except Exception as e:
                logging.error(f"GPIO control error: {e}")
                return
        else:
            self.button_states[button] = state
            logging.info(f"🔘 [SIM] Button {button}: {state}")
        
        # Update Firebase
        self.controls_ref.child(f'buttons/{button}').update({
            'state': state,
            'timestamp': {'.sv': 'timestamp'}
        })
    
    def update_slider(self, slider, value):
        """Update a slider value"""
        logging.info(f"🎚️ Slider {slider}: {value}")
        
        self.controls_ref.child(f'sliders/{slider}').set({
            'value': value,
            'timestamp': {'.sv': 'timestamp'}
        })
    
    def publish_full_status(self):
        """Publish full system status"""
        status = {
            'online': True,
            'gpioAvailable': GPIO_AVAILABLE,
            'buttons': self.button_states,
            'timestamp': {'.sv': 'timestamp'}
        }
        
        self.status_ref.set(status)
        logging.info("📊 Published full status")
    
    def run(self):
        """Start the Firebase bridge service"""
        logging.info(f"🚀 Starting Firebase Bridge for {DEVICE_NAME}")
        
        # Start sensor reading thread
        sensor_thread = Thread(target=self.read_sensors_loop, daemon=True)
        sensor_thread.start()
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("\n⚠️ Shutting down...")
            self.cleanup()
    
    def cleanup(self):
        """Cleanup on exit"""
        try:
            # Mark device as offline
            self.status_ref.update({
                'online': False,
                'lastUpdate': {'.sv': 'timestamp'}
            })
            
            # Cleanup GPIO
            if GPIO_AVAILABLE:
                GPIO.cleanup()
            
            logging.info("✅ Cleanup completed")
        except Exception as e:
            logging.error(f"Cleanup error: {e}")


if __name__ == '__main__':
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [%(levelname)s] - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, 'kuvoz-firebase.log')),
            logging.StreamHandler()
        ]
    )
    
    logging.info("=" * 60)
    logging.info("🚀 Kuvoz Firebase Bridge Service")
    logging.info(f"   Device: {DEVICE_NAME} ({DEVICE_ID})")
    logging.info(f"   Firebase URL: {FIREBASE_DB_URL}")
    logging.info(f"   GPIO Available: {GPIO_AVAILABLE}")
    logging.info("=" * 60)
    
    try:
        bridge = FirebaseBridge()
        bridge.run()
    except Exception as e:
        logging.error(f"❌ Fatal error: {e}")
        raise
