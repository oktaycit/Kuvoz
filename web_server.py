#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kuvoz Incubator Control System - Flask Web Server
Kivy yerine web tabanlı interface
WebSocket ile real-time iletişim
"""

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import threading
import time
import json
import os
import sys
import logging

# GPIO ve sensor import'ları
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("⚠️  RPi.GPIO not available - simulation mode")
    GPIO_AVAILABLE = False

# DHT sensor library - DHT_Native ONLY (Adafruit_DHT disabled due to platform issues)
sys.path.append("lib/")
try:
    from DHT_Native import read_retry, read
    DHT_AVAILABLE = True
    DHT_LIBRARY = "DHT_Native"
    print("✅ Using DHT_Native library (Adafruit_DHT disabled)")
except ImportError:
    print("❌ DHT_Native not available - using simulation")
    DHT_AVAILABLE = False
    DHT_LIBRARY = "Simulation"

# Oxygen sensor library
sys.path.append("lib/")
try:
    from DFRobot_Oxygen import *
    OXYGEN_AVAILABLE = True
except ImportError:
    print("⚠️  DFRobot_Oxygen not available - using simulation")
    OXYGEN_AVAILABLE = False

# Flask app setup
app = Flask(__name__, static_folder='web', static_url_path='')
app.config['SECRET_KEY'] = 'kuvoz_secret_key_2025'
socketio = SocketIO(app, cors_allowed_origins="*")

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Startup bilgileri
logger.info("🚀 Kuvoz Web Server initializing...")
logger.info(f"📊 DHT Library: {DHT_LIBRARY} (Adafruit_DHT disabled)")
logger.info(f"🔋 GPIO Available: {GPIO_AVAILABLE}")
logger.info(f"🌡️  DHT Available: {DHT_AVAILABLE}")
logger.info(f"💨 Oxygen Available: {OXYGEN_AVAILABLE}")
if DHT_AVAILABLE:
    logger.info("🎯 DHT11 Pin 15: Real sensor readings enabled (NO simulation)")

class KuvozServer:
    def __init__(self):
        # GPIO konfigürasyonu
        self.outChannels = [5, 6, 13, 16, 19, 20, 21, 26]
        self.touch_bt = [5, 20, 21]
        self.pinDht = 15
        self.sensorDht = 11  # DHT11 (was 22 for DHT22)
        
        # Durum değişkenleri
        self.sensor_data = {
            'temperature': {'value': '--', 'status': 'Initializing...'},
            'humidity': {'value': '--', 'status': 'Initializing...'},
            'oxygen': {'value': '--', 'status': 'Initializing...'}
        }
        
        self.button_states = {f'b{i+1}': False for i in range(8)}
        self.slider_values = {
            'sld1': 30,  # Nebulizer interval
            'sld2': 65,  # Humidity target
            'sld3': 25.0,  # Temperature target
            'sld4': 25.0,  # IR Temperature target
            'sld5': 30,  # Ozone interval
            'sld6': 12,  # Nebulizer hours interval
            'sld7': 8.0   # Ozone hours interval
        }
        
        # Control logic state
        self.control_active = True
        self.sensor_error_count = 0
        self.last_nebulizer_time = 0
        self.last_ozone_time = 0
        
        # Threading
        self.sensor_thread = None
        self.control_thread = None
        self.running = False
        
        # Oxygen sensor
        self.oxygen_sensor = None
        
        self.init_hardware()
        self.load_settings()
    
    def init_hardware(self):
        """GPIO ve sensörleri başlat"""
        global GPIO_AVAILABLE, OXYGEN_AVAILABLE
        
        if GPIO_AVAILABLE:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                
                # Output pinlerini ayarla
                for pin in self.outChannels:
                    GPIO.setup(pin, GPIO.OUT)
                    GPIO.output(pin, GPIO.HIGH)  # Relay başlangıç durumu
                
                logger.info("✅ GPIO initialized successfully")
            except Exception as e:
                logger.error(f"❌ GPIO init error: {e}")
                GPIO_AVAILABLE = False
        
        # Oxygen sensor
        if OXYGEN_AVAILABLE:
            try:
                from DFRobot_Oxygen import DFRobot_Oxygen_IIC, IIC_MODE, ADDRESS_3, COLLECT_NUMBER
                self.oxygen_sensor = DFRobot_Oxygen_IIC(IIC_MODE, ADDRESS_3)
                logger.info("✅ Oxygen sensor initialized")
            except Exception as e:
                logger.error(f"❌ Oxygen sensor init error: {e}")
                self.oxygen_sensor = None
    
    def safe_gpio_output(self, pin, state):
        """Thread-safe GPIO output"""
        global GPIO_AVAILABLE
        
        if GPIO_AVAILABLE:
            # Önce GPIO durumunu kontrol et
            if not self.check_gpio_status():
                return False
                
            try:
                GPIO.output(pin, state)
                return True
            except Exception as e:
                logger.error(f"GPIO output error on pin {pin}: {e}")
                # Bir kez daha GPIO'yu kontrol et ve kurtar
                if self.check_gpio_status():
                    try:
                        GPIO.output(pin, state)
                        logger.info(f"🔧 GPIO recovered for pin {pin}")
                        return True
                    except Exception as e2:
                        logger.error(f"GPIO recovery failed for pin {pin}: {e2}")
                return False
        return False
    
    def check_gpio_status(self):
        """GPIO durumunu kontrol et ve gerekirse yeniden başlat"""
        global GPIO_AVAILABLE
        
        if not GPIO_AVAILABLE:
            return False
            
        try:
            # GPIO mode kontrolü
            if GPIO.getmode() is None:
                logger.warning("🔧 GPIO mode lost, reinitializing...")
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                
                # Output pinlerini yeniden setup et
                for pin in self.outChannels:
                    GPIO.setup(pin, GPIO.OUT)
                    GPIO.output(pin, GPIO.HIGH)
                
                logger.info("✅ GPIO reinitialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"GPIO status check failed: {e}")
            GPIO_AVAILABLE = False
            return False
    
    def read_sensors(self):
        """Sensörleri oku"""
        try:
            # DHT sensor
            if DHT_AVAILABLE:
                logger.debug(f"🌡️  Reading DHT{self.sensorDht} from pin {self.pinDht}...")
                try:
                    hum, temp = read_retry(self.sensorDht, self.pinDht)
                    if hum is not None and temp is not None:
                        logger.info(f"✅ DHT{self.sensorDht}: {temp:.1f}°C, {hum:.0f}%rH")
                        self.sensor_data['temperature'] = {
                            'value': f"{temp:.1f}",
                            'status': f'DHT{self.sensorDht}'
                        }
                        self.sensor_data['humidity'] = {
                            'value': f"{hum:.0f}",
                            'status': f'DHT{self.sensorDht}'
                        }
                        self.sensor_error_count = 0
                    else:
                        logger.warning(f"⚠️  DHT{self.sensorDht} read returned None (pin {self.pinDht})")
                        raise Exception("DHT read returned None")
                except Exception as dht_error:
                    logger.error(f"❌ DHT{self.sensorDht} read error: {dht_error}")
                    raise Exception(f"DHT sensor read failed: {dht_error}")
            else:
                # DHT not available - sensor error
                logger.error("❌ DHT library not available - hardware connection issue")
                raise Exception("DHT sensor hardware not available")
            
            # Oxygen sensor
            if self.oxygen_sensor:
                try:
                    oxygen_data = self.oxygen_sensor.get_oxygen_data(20)  # 20 samples
                    self.sensor_data['oxygen'] = {
                        'value': f"{oxygen_data:.1f}",
                        'status': 'OK'
                    }
                except Exception as e:
                    logger.error(f"Oxygen sensor error: {e}")
                    self.sensor_data['oxygen'] = {
                        'value': '--',
                        'status': 'Error'
                    }
            else:
                # Simulation or nebulizer auto control
                import random
                oxygen_val = 20 + random.random() * 2
                self.sensor_data['oxygen'] = {
                    'value': f"{oxygen_val:.1f}",
                    'status': 'Simulated'
                }
        
        except Exception as e:
            logger.error(f"Sensor read error: {e}")
            self.sensor_error_count += 1
            
            if self.sensor_error_count > 5:
                # Reset to safe state
                self.reset_to_safe_state()
    
    def control_logic(self):
        """Ana kontrol döngüsü"""
        try:
            # GPIO durumunu kontrol et
            if not self.check_gpio_status():
                logger.warning("GPIO not available, skipping control logic")
                return
                
            current_time = time.time()
            
            # Temperature control (b4 - pin 16)
            if self.sensor_data['temperature']['value'] != '--':
                temp = float(self.sensor_data['temperature']['value'])
                temp_target = self.slider_values['sld3']
                
                if temp < temp_target:
                    self.safe_gpio_output(16, GPIO.LOW)  # Heating ON
                    self.button_states['b4'] = True
                else:
                    self.safe_gpio_output(16, GPIO.HIGH)  # Heating OFF
                    self.button_states['b4'] = False
            
            # Humidity control (b3 - pin 13)
            if self.sensor_data['humidity']['value'] != '--':
                hum = float(self.sensor_data['humidity']['value'])
                hum_target = self.slider_values['sld2']
                
                if hum < hum_target:
                    self.safe_gpio_output(13, GPIO.LOW)  # Humidity ON
                    self.button_states['b3'] = True
                else:
                    self.safe_gpio_output(13, GPIO.HIGH)  # Humidity OFF
                    self.button_states['b3'] = False
            
            # Nebulizer timed control (b2 - pin 6)
            nebulizer_interval = self.slider_values['sld6'] * 3600  # hours to seconds
            if current_time - self.last_nebulizer_time > nebulizer_interval:
                self.nebulizer_control()
                self.last_nebulizer_time = current_time
            
            # Ozone timed control (b8 - pin 26)
            ozone_interval = self.slider_values['sld7'] * 3600  # hours to seconds
            if current_time - self.last_ozone_time > ozone_interval:
                self.ozone_control()
                self.last_ozone_time = current_time
        
        except Exception as e:
            logger.error(f"Control logic error: {e}")
    
    def nebulizer_control(self):
        """Nebulizer timing control"""
        try:
            nebulizer_duration = self.slider_values['sld1'] * 60  # minutes to seconds
            
            # Turn ON
            self.safe_gpio_output(6, GPIO.LOW)
            self.button_states['b2'] = True
            logger.info(f"Nebulizer ON for {self.slider_values['sld1']} minutes")
            
            # Schedule turn OFF
            def turn_off_nebulizer():
                time.sleep(nebulizer_duration)
                self.safe_gpio_output(6, GPIO.HIGH)
                self.button_states['b2'] = False
                logger.info("Nebulizer OFF")
            
            threading.Thread(target=turn_off_nebulizer, daemon=True).start()
        
        except Exception as e:
            logger.error(f"Nebulizer control error: {e}")
    
    def ozone_control(self):
        """Ozone timing control"""
        try:
            ozone_duration = self.slider_values['sld5'] * 60  # minutes to seconds
            
            # Turn ON
            self.safe_gpio_output(26, GPIO.LOW)
            self.button_states['b8'] = True
            logger.info(f"Ozone ON for {self.slider_values['sld5']} minutes")
            
            # Schedule turn OFF
            def turn_off_ozone():
                time.sleep(ozone_duration)
                self.safe_gpio_output(26, GPIO.HIGH)
                self.button_states['b8'] = False
                logger.info("Ozone OFF")
            
            threading.Thread(target=turn_off_ozone, daemon=True).start()
        
        except Exception as e:
            logger.error(f"Ozone control error: {e}")
    
    def reset_to_safe_state(self):
        """Güvenli duruma geç"""
        logger.warning("Resetting to safe state")
        for pin in self.outChannels:
            self.safe_gpio_output(pin, GPIO.HIGH)
        
        for key in self.button_states:
            self.button_states[key] = False
    
    def toggle_button(self, name, pin, state):
        """Manuel buton kontrolü"""
        try:
            gpio_state = GPIO.LOW if state else GPIO.HIGH
            self.safe_gpio_output(pin, gpio_state)
            self.button_states[name] = state
            logger.info(f"Button {name} (pin {pin}): {'ON' if state else 'OFF'}")
            return True
        except Exception as e:
            logger.error(f"Button toggle error: {e}")
            return False
    
    def update_slider(self, slider_id, value):
        """Slider değerini güncelle"""
        try:
            self.slider_values[slider_id] = value
            logger.info(f"Slider {slider_id}: {value}")
            return True
        except Exception as e:
            logger.error(f"Slider update error: {e}")
            return False
    
    def load_settings(self):
        """Ayarları dosyadan yükle"""
        try:
            if os.path.exists("Failure.dat"):
                with open("Failure.dat", "r") as f:
                    line = f.read().strip()
                    if line:
                        parts = line.split()
                        if len(parts) >= 8:
                            # Button states
                            button_state = int(parts[0])
                            for i in range(8):
                                self.button_states[f'b{i+1}'] = bool(button_state & (1 << i))
                            
                            # Slider values
                            if len(parts) >= 8:
                                slider_keys = ['sld1', 'sld2', 'sld3', 'sld4', 'sld5', 'sld6', 'sld7']
                                for i, key in enumerate(slider_keys):
                                    if i + 1 < len(parts):
                                        self.slider_values[key] = float(parts[i + 1])
                
                logger.info("✅ Settings loaded from Failure.dat")
        except Exception as e:
            logger.error(f"Load settings error: {e}")
    
    def save_settings(self):
        """Ayarları dosyaya kaydet"""
        try:
            # Button states to bit pattern
            button_state = 0
            for i in range(8):
                if self.button_states[f'b{i+1}']:
                    button_state |= (1 << i)
            
            # Create line
            line_parts = [str(button_state)]
            slider_keys = ['sld1', 'sld2', 'sld3', 'sld4', 'sld5', 'sld6', 'sld7']
            for key in slider_keys:
                line_parts.append(str(self.slider_values[key]))
            
            with open("Failure.dat", "w") as f:
                f.write(" ".join(line_parts))
            
            logger.info("✅ Settings saved to Failure.dat")
            return True
        except Exception as e:
            logger.error(f"Save settings error: {e}")
            return False
    
    def start_threads(self):
        """Background thread'leri başlat"""
        self.running = True
        
        # Sensor thread
        def sensor_loop():
            while self.running:
                self.read_sensors()
                # WebSocket ile sensor verilerini gönder
                socketio.emit('sensor_update', {
                    'type': 'sensor_update',
                    'sensors': self.sensor_data
                })
                time.sleep(15)  # 15 saniyede bir
        
        # Control thread
        def control_loop():
            # İlk çalıştığında GPIO'yu kontrol et
            global GPIO_AVAILABLE
            gpio_initialized = False
            
            while self.running:
                # GPIO'yu thread içinde de kontrol et
                if GPIO_AVAILABLE and not gpio_initialized:
                    try:
                        if GPIO.getmode() is None:
                            GPIO.setmode(GPIO.BCM)
                            GPIO.setwarnings(False)
                            # Output pinlerini yeniden setup et
                            for pin in self.outChannels:
                                GPIO.setup(pin, GPIO.OUT)
                                GPIO.output(pin, GPIO.HIGH)
                            logger.info("🔧 GPIO re-initialized in control thread")
                        gpio_initialized = True
                    except Exception as e:
                        logger.error(f"Control thread GPIO init error: {e}")
                        GPIO_AVAILABLE = False
                
                if self.control_active:
                    self.control_logic()
                    # WebSocket ile button durumlarını gönder
                    socketio.emit('button_update', {
                        'type': 'button_update',
                        'buttons': self.button_states
                    })
                time.sleep(1)  # 1 saniyede bir
        
        self.sensor_thread = threading.Thread(target=sensor_loop, daemon=True)
        self.control_thread = threading.Thread(target=control_loop, daemon=True)
        
        self.sensor_thread.start()
        self.control_thread.start()
        
        logger.info("✅ Background threads started")
    
    def stop_threads(self):
        """Thread'leri durdur"""
        self.running = False
        if self.sensor_thread:
            self.sensor_thread.join(timeout=2)
        if self.control_thread:
            self.control_thread.join(timeout=2)
        logger.info("✅ Background threads stopped")
    
    def cleanup(self):
        """Temizlik işlemleri"""
        global GPIO_AVAILABLE
        
        self.stop_threads()
        self.save_settings()
        if GPIO_AVAILABLE:
            GPIO.cleanup()
        logger.info("✅ Cleanup completed")

# Global server instance
kuvoz_server = KuvozServer()

# Flask routes
@app.route('/')
def index():
    """Ana sayfa"""
    return app.send_static_file('index.html')

@app.route('/api/status')
def get_status():
    """Sistem durumunu al"""
    return jsonify({
        'sensors': kuvoz_server.sensor_data,
        'buttons': kuvoz_server.button_states,
        'sliders': kuvoz_server.slider_values,
        'system': {
            'dht_library': DHT_LIBRARY,
            'gpio_available': GPIO_AVAILABLE,
            'dht_available': DHT_AVAILABLE,
            'oxygen_available': OXYGEN_AVAILABLE,
            'dht_pin': kuvoz_server.pinDht,
            'dht_sensor': f"DHT{kuvoz_server.sensorDht}"
        },
        'timestamp': time.time()
    })

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """WebSocket bağlantısı"""
    logger.info('Client connected')
    emit('status_response', {
        'type': 'status_response',
        'sensors': kuvoz_server.sensor_data,
        'buttons': kuvoz_server.button_states,
        'sliders': kuvoz_server.slider_values
    })

@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket bağlantı kesildi"""
    logger.info('Client disconnected')

@socketio.on('message')
def handle_message(data):
    """WebSocket mesajları"""
    try:
        command = data.get('command')
        command_data = data.get('data', {})
        
        if command == 'get_status':
            emit('status_response', {
                'type': 'status_response',
                'sensors': kuvoz_server.sensor_data,
                'buttons': kuvoz_server.button_states,
                'sliders': kuvoz_server.slider_values
            })
        
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
            slider_id = command_data.get('id')
            value = command_data.get('value')
            
            if kuvoz_server.update_slider(slider_id, value):
                emit('success', {
                    'type': 'success',
                    'message': f'Slider {slider_id} updated'
                })
        
        elif command == 'save_settings':
            if kuvoz_server.save_settings():
                emit('success', {
                    'type': 'success',
                    'message': 'Settings saved successfully'
                })
            else:
                emit('error', {
                    'type': 'error',
                    'message': 'Failed to save settings'
                })
        
        elif command == 'shutdown':
            logger.info("Shutdown requested")
            emit('success', {
                'type': 'success',
                'message': 'System shutting down...'
            })
            # Shutdown işlemi
            threading.Timer(2.0, lambda: os.system("sudo shutdown -h now")).start()
        
        elif command == 'restart':
            logger.info("Restart requested")
            emit('success', {
                'type': 'success',
                'message': 'System restarting...'
            })
            # Restart işlemi
            threading.Timer(2.0, lambda: os.system("sudo reboot")).start()
        
        else:
            emit('error', {
                'type': 'error',
                'message': f'Unknown command: {command}'
            })
    
    except Exception as e:
        logger.error(f"WebSocket message error: {e}")
        emit('error', {
            'type': 'error',
            'message': f'Command processing error: {str(e)}'
        })

if __name__ == '__main__':
    # Simulation mode sadece --sim flag ile
    SIMULATION_MODE = '--sim' in sys.argv
    
    if SIMULATION_MODE:
        logger.info("🔧 SIMULATION MODE: Forced by --sim flag")
    elif not GPIO_AVAILABLE:
        logger.warning("⚠️  GPIO not available - hardware mode with limitations")
    elif not DHT_AVAILABLE:
        logger.error("❌ DHT sensor not available - check hardware connection")
        
    try:
        # Background thread'leri başlat
        kuvoz_server.start_threads()
        
        # Flask server'ı başlat
        logger.info("🚀 Starting Kuvoz Web Server...")
        logger.info("📱 Web interface: http://localhost:5000")
        
        if SIMULATION_MODE:
            logger.info("⚠️  Running in simulation mode - no GPIO control")
        
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
    
    except KeyboardInterrupt:
        logger.info("⏹️  Server stopped by user")
    
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
    
    finally:
        kuvoz_server.cleanup()