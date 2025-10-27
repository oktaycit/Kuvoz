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
socketio = SocketIO(app, cors_allowed_origins="*", 
                   max_http_buffer_size=1000000,  # 1MB
                   ping_timeout=60000,           # 60 seconds 
                   ping_interval=25000)          # 25 seconds

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
    logger.info("🎯 DHT11 Pin 22: Real sensor readings enabled (NO simulation)")

class KuvozServer:
    def __init__(self):
        # GPIO konfigürasyonu
        self.outChannels = [5, 6, 13, 16, 19, 20, 21, 26]
        self.touch_bt = [5, 20, 21]
        self.pinDht = 15  # GPIO 15 (Physical Pin 10)
        self.sensorDht = 11  # DHT11 (was 22 for DHT22)
        
        # Durum değişkenleri
        self.sensor_data = {
            'temperature': {'value': '--', 'status': 'Initializing...'},
            'humidity': {'value': '--', 'status': 'Initializing...'}
        }
        # Oksijen sensörü başlangıçta eklenmez - init_hardware'dan sonra eklenecek
        
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
        self.oxygen_sensor_available = False
        
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
        
        # Oxygen sensor - İlk açılışta test et
        if OXYGEN_AVAILABLE:
            try:
                from DFRobot_Oxygen import DFRobot_Oxygen_IIC, IIC_MODE, ADDRESS_3, COLLECT_NUMBER
                self.oxygen_sensor = DFRobot_Oxygen_IIC(IIC_MODE, ADDRESS_3)
                
                # İlk okuma testi - eğer başarısızsa sensörü devre dışı bırak
                test_reading = self.oxygen_sensor.get_oxygen_data(5)  # 5 sample ile hızlı test
                if test_reading is not None and 0 <= test_reading <= 100:
                    self.oxygen_sensor_available = True
                    logger.info(f"✅ Oxygen sensor initialized and tested: {test_reading:.1f}%")
                else:
                    self.oxygen_sensor_available = False
                    self.oxygen_sensor = None
                    logger.warning("⚠️  Oxygen sensor test failed - sensor disabled")
                    
            except Exception as e:
                logger.error(f"❌ Oxygen sensor init/test error: {e}")
                self.oxygen_sensor = None
                self.oxygen_sensor_available = False
                logger.info("🔧 System will continue without oxygen sensor")
        else:
            self.oxygen_sensor_available = False
            logger.info("ℹ️  Oxygen sensor library not available")
        
        # Oksijen sensörü varsa sensor_data'ya ekle
        if self.oxygen_sensor_available:
            self.sensor_data['oxygen'] = {'value': '--', 'status': 'Initializing...'}
            logger.info("📊 Oxygen sensor added to dashboard")
            logger.info("💨 Ozone mode: OXYGEN-BASED (intelligent control)")
        else:
            logger.info("📊 Oxygen sensor excluded from dashboard")
            logger.info("💨 Ozone mode: TIMED (fixed interval control)")
    
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
            # GPIO mode kontrolü - daha az aggressive
            current_mode = GPIO.getmode()
            if current_mode is None:
                logger.warning("🔧 GPIO mode lost, reinitializing...")
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                
                # Output pinlerini yeniden setup et
                for pin in self.outChannels:
                    GPIO.setup(pin, GPIO.OUT)
                    GPIO.output(pin, GPIO.HIGH)
            elif current_mode != GPIO.BCM:
                logger.warning(f"🔧 GPIO mode changed to {current_mode}, setting to BCM...")
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                
                logger.info("✅ GPIO reinitialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"GPIO status check failed: {e}")
            GPIO_AVAILABLE = False
            return False
    
    def read_sensors(self):
        """Sensörleri oku"""
        try:
            # DHT sensor - Auto-detection DHT11/DHT22
            if DHT_AVAILABLE:
                logger.debug(f"🌡️  Reading DHT sensor (auto-detect) from GPIO {self.pinDht}...")
                try:
                    # Otomatik algılama ile okuma (sensör tipi belirtilmez)
                    hum, temp = read_retry(pin=self.pinDht)
                    if hum is not None and temp is not None:
                        # Algılanan sensör tipini kontrol et
                        from lib.DHT_Native import dht_native
                        detected_type = dht_native.detected_sensor_type or self.sensorDht
                        logger.info(f"✅ DHT{detected_type} (GPIO {self.pinDht}): {temp:.1f}°C, {hum:.0f}%rH")
                        self.sensor_data['temperature'] = {
                            'value': f"{temp:.1f}",
                            'status': f'DHT{detected_type} GPIO{self.pinDht}'
                        }
                        self.sensor_data['humidity'] = {
                            'value': f"{hum:.0f}",
                            'status': f'DHT{detected_type} GPIO{self.pinDht}'
                        }
                        self.sensor_error_count = 0
                    else:
                        logger.warning(f"⚠️  DHT sensor read failed (GPIO {self.pinDht})")
                        self.sensor_error_count += 1
                        # Use last known values or defaults
                        if 'temperature' not in self.sensor_data or self.sensor_error_count > 5:
                            self.sensor_data['temperature'] = {
                                'value': "25.0",
                                'status': f'DHT{self.sensorDht} ERROR'
                            }
                            self.sensor_data['humidity'] = {
                                'value': "50",
                                'status': f'DHT{self.sensorDht} ERROR'
                            }
                        logger.debug(f"DHT error count: {self.sensor_error_count}")
                except Exception as dht_error:
                    logger.error(f"❌ DHT{self.sensorDht} read error: {dht_error}")
                    raise Exception(f"DHT sensor read failed: {dht_error}")
            else:
                # DHT not available - sensor error
                logger.error("❌ DHT library not available - hardware connection issue")
                raise Exception("DHT sensor hardware not available")
            
            # Oxygen sensor - sadece mevcut ve test edilmişse oku
            if self.oxygen_sensor_available and self.oxygen_sensor:
                try:
                    oxygen_data = self.oxygen_sensor.get_oxygen_data(20)  # 20 samples
                    if oxygen_data is not None and 0 <= oxygen_data <= 100:
                        self.sensor_data['oxygen'] = {
                            'value': f"{oxygen_data:.1f}",
                            'status': 'OK'
                        }
                    else:
                        logger.warning(f"⚠️  Invalid oxygen reading: {oxygen_data}")
                        # Geçersiz okuma - sensörü devre dışı bırak
                        self.oxygen_sensor_available = False
                        self.oxygen_sensor = None
                        if 'oxygen' in self.sensor_data:
                            del self.sensor_data['oxygen']
                        logger.info("🔧 Oxygen sensor disabled due to invalid readings")
                        
                except Exception as e:
                    logger.error(f"❌ Oxygen sensor read error: {e}")
                    # Okuma hatası - sensörü devre dışı bırak
                    self.oxygen_sensor_available = False
                    self.oxygen_sensor = None
                    if 'oxygen' in self.sensor_data:
                        del self.sensor_data['oxygen']
                    logger.info("🔧 Oxygen sensor disabled due to read errors")
            
            # Oksijen sensörü yoksa hiçbir şey yapmayız (simülasyon da yok)
        
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
            
            # Ozone intelligent control (b8 - pin 26)
            ozone_interval = self.slider_values['sld7'] * 3600  # hours to seconds
            
            # Oksijen sensörü varsa daha akıllı kontrol
            if self.oxygen_sensor_available and 'oxygen' in self.sensor_data:
                # Oksijen bazlı ozon kontrolü - dinamik aralık
                if current_time - self.last_ozone_time > ozone_interval:
                    self.ozone_control()
                    self.last_ozone_time = current_time
                elif current_time - self.last_ozone_time > (ozone_interval // 2):
                    # Oksijen çok yüksekse ara kontrol
                    try:
                        current_oxygen = float(self.sensor_data['oxygen']['value'])
                        if current_oxygen > 24.0:  # Çok yüksek oksijen
                            logger.info(f"🚨 Yüksek oksijen tespit edildi ({current_oxygen:.1f}%) - Ara ozon kontrolü")
                            self.ozone_control()
                            self.last_ozone_time = current_time
                    except (ValueError, KeyError):
                        pass  # Oksijen değeri okunamazsa normal döngüye devam
            else:
                # Oksijen sensörü yoksa standart zamanlı kontrol
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
        """Ozone timing control - Oksijen sensörü varlığına göre akıllı kontrol"""
        try:
            ozone_duration = self.slider_values['sld5'] * 60  # minutes to seconds
            
            # Oksijen sensörü varsa önce oksijen seviyesini kontrol et
            if self.oxygen_sensor_available and 'oxygen' in self.sensor_data:
                try:
                    current_oxygen = float(self.sensor_data['oxygen']['value'])
                    
                    # Oksijen seviyesi yüksekse (>22%) ozon çalıştır
                    if current_oxygen > 22.0:
                        logger.info(f"🌟 Oksijen seviyesi yüksek ({current_oxygen:.1f}%) - Ozon başlatılıyor")
                        self.start_ozone_cycle(ozone_duration, f"O2-based ({current_oxygen:.1f}%)")
                    # Oksijen seviyesi normalse (18-22%) kısa süreli ozon
                    elif 18.0 <= current_oxygen <= 22.0:
                        short_duration = ozone_duration // 2  # Yarı süre
                        logger.info(f"⚡ Oksijen seviyesi normal ({current_oxygen:.1f}%) - Kısa ozon ({short_duration//60} dk)")
                        self.start_ozone_cycle(short_duration, f"O2-short ({current_oxygen:.1f}%)")
                    # Oksijen seviyesi düşükse (<18%) ozon yapma
                    else:
                        logger.warning(f"⚠️  Oksijen seviyesi düşük ({current_oxygen:.1f}%) - Ozon atlandı")
                        self.button_states['b8'] = False
                        return
                        
                except (ValueError, KeyError) as e:
                    logger.warning(f"⚠️  Oksijen değeri okunamadı, standart ozon: {e}")
                    self.start_ozone_cycle(ozone_duration, "O2-error fallback")
            else:
                # Oksijen sensörü yoksa zamanlı ozon kontrolü (otomatik/güvenli mod)
                logger.info("🔄 Oksijen sensörü yok - Otomatik zamanlı ozon başlatılıyor")
                self.start_ozone_cycle(ozone_duration, "Timed (no O2 sensor)")
        
        except Exception as e:
            logger.error(f"Ozone control error: {e}")
    
    def start_ozone_cycle(self, duration, reason):
        """Ozon döngüsünü başlat"""
        try:
            # Turn ON
            self.safe_gpio_output(26, GPIO.LOW)
            self.button_states['b8'] = True
            logger.info(f"💨 Ozone ON for {duration//60} minutes - Reason: {reason}")
            
            # Schedule turn OFF
            def turn_off_ozone():
                time.sleep(duration)
                self.safe_gpio_output(26, GPIO.HIGH)
                self.button_states['b8'] = False
                logger.info(f"💨 Ozone OFF - Completed {duration//60} min cycle")
            
            threading.Thread(target=turn_off_ozone, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Ozone cycle start error: {e}")
    
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
        """Ayarları JSON formatından yükle"""
        try:
            if os.path.exists("Failure.dat"):
                with open("Failure.dat", "r") as f:
                    file_content = f.read().strip()

                    # JSON formatı mı kontrol et
                    if file_content.startswith("{"):
                        # JSON format
                        data = json.loads(file_content)
                        if "slider_values" in data:
                            self.slider_values.update(data["slider_values"])
                        if "button_states" in data:
                            self.button_states.update(data["button_states"])
                        logger.info("✅ Settings loaded from JSON format")
                    else:
                        # Eski format
                        parts = file_content.split()
                        if len(parts) >= 8:
                            # Button states
                            button_state = int(parts[0])
                            for i in range(8):
                                self.button_states[f"b{i+1}"] = bool(button_state & (1 << i))

                            # Slider values
                            slider_keys = ["sld1", "sld2", "sld3", "sld4", "sld5", "sld6", "sld7"]
                            for i, key in enumerate(slider_keys):
                                if i + 1 < len(parts):
                                    self.slider_values[key] = float(parts[i + 1])
                        logger.info("✅ Settings loaded from old format")
        except Exception as e:
            logger.error(f"Load settings error: {e}")
    
    def save_settings(self):
        """Ayarları JSON formatında dosyaya kaydet"""
        try:
            settings_data = {
                "slider_values": self.slider_values,
                "button_states": self.button_states
            }

            with open("Failure.dat", "w") as f:
                json.dump(settings_data, f, indent=4)

            logger.info("✅ Settings saved to Failure.dat (JSON format)")
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
                # WebSocket ile sensor verilerini gönder (rate limiting)
                try:
                    logger.info(f"DEBUG: Emitting sensor_update: {self.sensor_data}")
                    socketio.emit('sensor_update', {
                        'type': 'sensor_update',
                        'sensors': self.sensor_data
                    })
                    logger.info("DEBUG: Sensor update emitted successfully")
                except Exception as e:
                    logger.error(f"Socket.IO emit error: {e}")
                time.sleep(5)  # 5 saniyede bir (debug için daha hızlı)
        
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
            'oxygen_available': kuvoz_server.oxygen_sensor_available,
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

@socketio.on('get_status')
def handle_get_status():
    """Get initial status"""
    logger.info('DEBUG: Client requested status')
    logger.info(f'DEBUG: Current sensor data: {kuvoz_server.sensor_data}')
    
    status_data = {
        'type': 'status_response',
        'sensors': kuvoz_server.sensor_data,
        'buttons': kuvoz_server.button_states,
        'sliders': kuvoz_server.slider_values
    }
    
    logger.info(f'DEBUG: Emitting status_response: {status_data}')
    emit('status_response', status_data)

@socketio.on('toggle_button')
def handle_toggle_button(data):
    """Handle button toggle"""
    try:
        name = data.get('name')
        pin = data.get('pin')
        state = data.get('state')
        logger.info(f'Button toggle: {name} (pin {pin}) -> {state}')
        
        if name and pin is not None:
            kuvoz_server.toggle_button(name, int(pin), state if state is not None else None)
            # Emit update to all clients
            socketio.emit('button_update', {
                'name': name,
                'state': kuvoz_server.button_states.get(name, False)
            })
    except Exception as e:
        logger.error(f'Toggle button error: {e}')

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