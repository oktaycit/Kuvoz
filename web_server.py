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
import datetime
import json
import os
import sys
import logging
import socket
import subprocess
import re
import base64
from io import BytesIO

# Firebase integration (optional - for mobile app)
try:
    from lib.firebase_manager import FirebaseManager
    FIREBASE_AVAILABLE = True
    print("✅ Firebase Manager loaded")
except ImportError as e:
    print(f"⚠️  Firebase not available: {e}")
    print("   Zero 2 W için Firebase gereksiz (RAM tasarrufu)")
    FIREBASE_AVAILABLE = False
    FirebaseManager = None

# QR Code library
try:
    import qrcode
    QRCODE_AVAILABLE = True
    print("✅ QR Code library loaded")
except ImportError:
    print("⚠️  QR Code library not available")
    QRCODE_AVAILABLE = False

# GPIO ve sensor import'ları
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("⚠️  RPi.GPIO not available - simulation mode")
    GPIO_AVAILABLE = False
    # GPIO simulation constants
    class GPIO:
        LOW = 0
        HIGH = 1
        BCM = 11
        OUT = 0

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

# CO2 (SCD30) sensor library
try:
    from sensirion_driver_adapters.i2c_adapter.linux_i2c_channel_provider import LinuxI2cChannelProvider
    from sensirion_i2c_scd30 import Scd30Device
    CO2_AVAILABLE = True
    print("✅ SCD30 libraries loaded")
except ImportError:
    print("⚠️  SCD30 libraries not available - CO2 disabled")
    print("   Install: make deps-scd30")
    print("   Install: make deps-scd30")
    CO2_AVAILABLE = False

# AI Module - DISABLED for Raspberry Pi Zero 2 W (RAM optimization)
sys.path.append("lib/")
AI_AVAILABLE = False
AIManager = None

try:
    from lib.ai.manager import AIManager
    AI_AVAILABLE = True
    print("✅ AI Module available")
except ImportError as e:
    print(f"⚠️  AI Module not available: {e}")
    AI_AVAILABLE = False
    AIManager = None

# Sensor Data Logger
try:
    from lib.data.sensor_logger import SensorLogger
    LOGGING_AVAILABLE = True
    print("✅ Sensor Logger loaded")
except ImportError as e:
    print(f"⚠️  Sensor Logger not available: {e}")
    LOGGING_AVAILABLE = False

# Flask app setup
app = Flask(__name__, static_folder='web', static_url_path='')
app.config['SECRET_KEY'] = 'kuvoz_secret_key_2025'
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   async_mode='threading',       # Explicit threading mode
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
    def _detect_dht_sensor_type(self):
        """
        Detect DHT sensor type from command line or environment variable.
        Priority: 1) Command line arg, 2) Environment variable, 3) Default DHT22

        Usage:
          python3 web_server.py --dht11    # Force DHT11
          python3 web_server.py --dht22    # Force DHT22
          DHT_SENSOR_TYPE=11 python3 web_server.py  # Environment variable
        """
        # 1. Check command line arguments
        if '--dht11' in sys.argv:
            logger.info("🌡️  DHT11 sensor specified via --dht11 flag")
            return 11
        elif '--dht22' in sys.argv:
            logger.info("🌡️  DHT22 sensor specified via --dht22 flag")
            return 22

        # 2. Check environment variable
        env_sensor_type = os.getenv('DHT_SENSOR_TYPE')
        if env_sensor_type:
            try:
                sensor_type = int(env_sensor_type)
                if sensor_type in [11, 22]:
                    logger.info(f"🌡️  DHT{sensor_type} sensor specified via DHT_SENSOR_TYPE environment variable")
                    return sensor_type
                else:
                    logger.warning(f"⚠️  Invalid DHT_SENSOR_TYPE={env_sensor_type}, using default DHT22")
            except ValueError:
                logger.warning(f"⚠️  Invalid DHT_SENSOR_TYPE={env_sensor_type}, using default DHT22")

        # 3. Default: DHT22 (most common for production)
        logger.info("🌡️  Using default DHT22 sensor (override with --dht11 or DHT_SENSOR_TYPE=11)")
        return 22

    def __init__(self):
        # GPIO konfigürasyonu
        self.outChannels = [5, 6, 13, 16, 19, 20, 21, 26]
        self.touch_bt = [5, 20, 21]
        self.pinDht = 15  # GPIO 15 (Physical Pin 10)

        # DHT sensor type - auto-detect from environment or command line
        # Priority: 1) Command line arg, 2) Environment variable, 3) Default DHT22
        self.sensorDht = self._detect_dht_sensor_type()

        # Durum değişkenleri
        self.sensor_data = {
            'temperature': {'value': '--', 'status': 'Initializing...'},
            'humidity': {'value': '--', 'status': 'Initializing...'}
        }
        # Oksijen sensörü başlangıçta eklenmez - init_hardware'dan sonra eklenecek
        # CO2 sensörü (SCD30) de init_hardware'dan sonra eklenecek
        
        self.button_states = {f'b{i+1}': False for i in range(8)}
        self.gpio_output_states = {f'b{i+1}': None for i in range(8)}  # GPIO output states (True=LOW, False=HIGH, None=unknown)
        self.slider_values = {
            'sld1': 30,  # Nebulizer interval
            'sld2': 65,  # Humidity target
            'sld3': 25.0,  # Temperature target
            'sld4': 25.0,  # IR Temperature target
            'sld5': 30,  # Ozone interval
            'sld6': 12,  # Nebulizer hours interval
            'sld7': 8.0,   # Ozone hours interval
            # Duty/Free Time Settings
            'sld8': 5,   # Nebulizer duty time (min)
            'sld9': 25,  # Nebulizer free time (min)
            'sld10': 3,  # Ozone duty time (min)
            'sld11': 60  # Ozone free time (min)
        }
        
        # Control logic state
        self.control_active = True
        self.sensor_error_count = 0
        self.last_nebulizer_time = 0
        self.last_ozone_time = 0
        
        # Disinfection safety mode
        self.disinfection_mode = False
        self.disinfection_start_time = 0
        
        # AI Module state (can be toggled at runtime)
        self.ai_enabled = False  # Default OFF - can be enabled from UI

        # Hysteresis settings (prevent relay chattering)
        self.TEMP_HYSTERESIS = 0.5  # °C - prevents heating on/off cycling
        self.HUM_HYSTERESIS = 2.0   # % - prevents humidifier on/off cycling
        
        # Duty cycle state tracking
        self.nebulizer_duty_start = 0
        self.nebulizer_in_duty = False
        self.ozone_duty_start = 0
        self.ozone_in_duty = False
        
        # Threading
        self.sensor_thread = None
        self.control_thread = None
        self.running = False
        
        # Firebase Integration (optional)
        self.firebase_manager = None
        if FIREBASE_AVAILABLE:
            try:
                self.firebase_manager = FirebaseManager()
                self.firebase_manager.listen_for_controls(self.handle_firebase_control)
                print("✅ Firebase connected")
            except Exception as e:
                print(f"⚠️  Firebase connection failed: {e}")
                self.firebase_manager = None
        
        # Oxygen sensor
        self.oxygen_sensor = None
        self.oxygen_sensor_available = False
        
        # DHT bit-shift anomaly filter - tracks last valid readings
        self.last_valid_temp = None
        self.last_valid_humidity = None

        # CO2 sensor (SCD30)
        self.co2_sensor = None
        self.co2_sensor_available = False
        self._scd30_started = False
        self._scd30_warmup_reads = 0  # İlk birkaç okumayı atla
        
        # AI Manager (initialized but not started by default)
        self.ai_manager = None
        if AI_AVAILABLE:
            try:
                self.ai_manager = AIManager()
                logger.info("AI Manager initialized (not started - toggle from UI)")
            except Exception as e:
                logger.error(f"Failed to initialize AI Manager: {e}")
                self.ai_manager = None
        
        # Sensor Data Logger
        self.sensor_logger = None
        # Sensor Data Logger
        self.sensor_logger = None
        if LOGGING_AVAILABLE:
            self.sensor_logger = SensorLogger(db_path="data/sensor_logs.db", min_interval=60)
        
        self.init_hardware()
        self.load_settings()
        
        # Start AI if it was enabled in saved settings
        if self.ai_enabled and self.ai_manager:
            try:
                self.ai_manager.start()
                logger.info("🤖 AI Manager auto-started (user preference from settings)")
            except Exception as e:
                logger.error(f"Failed to auto-start AI Manager: {e}")
                self.ai_enabled = False
    
    def handle_firebase_control(self, path, value):
        """Handle control updates from Firebase"""
        logger.info(f"Firebase Control: {path} = {value}")
        
        # Path examples: "/controls/b1", "/settings/sld1", "/b1" (depending on how we structure)
        # Assuming path is relative to controls root, e.g. "/b1"
        
        key = path.strip('/')
        
        if key in self.button_states:
            # Button update
            state = bool(value)
            self.button_states[key] = state
            
            # Update Hardware
            pin_map = {
                'b1': 5, 'b2': 6, 'b3': 13, 'b4': 16,
                'b5': 19, 'b6': 20, 'b7': 21, 'b8': 26
            }
            if key in pin_map:
                pin = pin_map[key]
                gpio_val = GPIO.LOW if state else GPIO.HIGH
                self.safe_gpio_output(pin, gpio_val)
                
            # Sync to local Web UI
            socketio.emit('button_update', {'id': key, 'status': state})
            
        elif key in self.slider_values:
            # Slider update
            try:
                val = float(value)
                self.slider_values[key] = val
                # Sync to Web UI
                socketio.emit('slider_update', {'id': key, 'value': val})
            except ValueError:
                pass

    def get_system_status(self):
        """Return backend capability flags for frontend consumption."""
        # Oksijen verisi var mı? (Gerçek sensör VEYA CO2'den tahmin)
        has_oxygen_data = 'oxygen' in self.sensor_data and self.sensor_data['oxygen']['value'] != '--'
        
        # CO2 verisi var mı? (SCD30'dan gerçek okuma)
        has_co2_data = 'co2' in self.sensor_data and self.sensor_data['co2']['value'] != '--'
        
        return {
            'dht_library': DHT_LIBRARY,
            'gpio_available': True,  # Always true - simulation mode works too
            'dht_available': DHT_AVAILABLE,
            'oxygen_available': has_oxygen_data,  # Gerçek sensör VEYA tahmini
            'co2_available': has_co2_data,  # SCD30'dan gerçek okuma varsa
            'dht_pin': self.pinDht,
            'dht_sensor': f"DHT{self.sensorDht}",
            'network_ip': get_local_ip(),
            'port': 8000
        }

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
                    button_name = self.get_button_name_by_pin(pin)
                    if button_name:
                        self.gpio_output_states[button_name] = False
                
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

        # CO2 (SCD30) sensörü başlat
        if CO2_AVAILABLE:
            try:
                self._scd30_provider = LinuxI2cChannelProvider('/dev/i2c-1')
                self._scd30_provider.__enter__()  # Context manager'i başlat
                # SCD30 I2C adresi: 0x61, CRC yok
                self._scd30_channel = self._scd30_provider.get_channel(slave_address=0x61, crc_parameters=None)
                self.co2_sensor = Scd30Device(self._scd30_channel)
                
                # Yeni sensör versiyonu için yapılandırma
                try:
                    # Soft reset (temiz başlangıç)
                    self.co2_sensor.soft_reset()
                    time.sleep(0.5)
                    logger.info("   Soft reset OK")
                except:
                    pass  # Eski versiyonlarda olmayabilir
                
                try:
                    # Measurement interval: 5 saniye (yeni sensör versiyonu için)
                    self.co2_sensor.set_measurement_interval(5)
                    time.sleep(0.2)
                    logger.info("   Measurement interval: 5s")
                except Exception as e:
                    logger.warning(f"   Measurement interval ayarlanamadı: {e}")
                
                try:
                    # Auto-calibration kapat (daha tutarlı okumalar için)
                    self.co2_sensor.deactivate_automatic_self_calibration()
                    time.sleep(0.2)
                    logger.info("   Auto-calibration: OFF")
                except AttributeError:
                    logger.info("   Auto-calibration: Not available (API version)")
                except Exception as e:
                    logger.warning(f"   Auto-calibration kapatılamadı: {e}")
                
                # Periyodik ölçüm başlat (0 = ambient basınç)
                self.co2_sensor.start_periodic_measurement(0)
                self._scd30_started = True
                
                # Dashboard'a CO2 alanını ekle
                self.co2_sensor_available = True
                self.sensor_data['co2'] = {'value': '--', 'status': 'Warming up (20s)...'}
                logger.info("✅ CO2 (SCD30) sensor initialized (5s interval, no auto-cal)")
            except Exception as e:
                logger.error(f"❌ CO2 (SCD30) init error: {e}")
                logger.error(f"   Sensör arızalı olabilir - devre dışı bırakılıyor")
                self.co2_sensor = None
                self.co2_sensor_available = False
                # Arızalı sensör için UI mesajı
                self.sensor_data['co2'] = {'value': '--', 'status': 'Sensör arızalı - değiştirilmeli'}
        else:
            logger.info("ℹ️  CO2 (SCD30) libraries not available")
    
    def safe_gpio_output(self, pin, state):
        """Thread-safe GPIO output with state tracking"""
        global GPIO_AVAILABLE

        button_name = self.get_button_name_by_pin(pin)

        # Simulation mode: track state but don't call GPIO
        if not GPIO_AVAILABLE:
            if button_name:
                # GPIO.LOW simülasyonu
                if hasattr(self, '_GPIO_LOW_SIM'):
                    is_on = (state == self._GPIO_LOW_SIM)
                else:
                    # GPIO constants simulation
                    self._GPIO_LOW_SIM = 0
                    self._GPIO_HIGH_SIM = 1
                    is_on = (state == 0)  # LOW = 0 = ON
                self.gpio_output_states[button_name] = is_on
            return False

        if button_name:
            self.gpio_output_states[button_name] = (state == GPIO.LOW)

        # Önce GPIO durumunu kontrol et
        if not self.check_gpio_status():
            if button_name:
                self.gpio_output_states[button_name] = None
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
            if button_name:
                self.gpio_output_states[button_name] = None
            return False

    def get_button_name_by_pin(self, pin):
        """Get button name (b1-b8) by GPIO pin number"""
        pin_to_button = {
            5: 'b1',   # Therapeutic Lighting
            6: 'b2',   # Nebulizer
            13: 'b3',  # Humidity Control
            16: 'b4',  # Heating Pad
            19: 'b5',  # IR Heater
            20: 'b6',  # Ventilation Fan
            21: 'b7',  # UV Sterilization
            26: 'b8'   # Ozone Sterilizer
        }
        return pin_to_button.get(pin)
    
    def estimate_oxygen_from_co2(self, co2_ppm):
        """
        Oksijen sensörü yoksa CO2 seviyesinden yaklaşık O2 tahmini yapar.
        
        CO2 ve O2 kapalı ortamlarda ters orantılıdır:
        - Normal atmosfer: ~21% O2, ~400-450 ppm CO2
        - İyi havalandırma: <800 ppm CO2 → ~20-21% O2
        - Orta kalite: 800-1200 ppm → ~19-20% O2
        - Zayıf: 1200-1500 ppm → ~18-19% O2
        - Kötü: 1500-2000 ppm → ~17-18% O2
        - Çok kötü: >2000 ppm → <17% O2
        
        Args:
            co2_ppm: CO2 seviyesi (ppm)
            
        Returns:
            float: Tahmini O2 yüzdesi
        """
        try:
            co2_ppm = float(co2_ppm)
            
            # Parçalı lineer interpolasyon kullanarak O2 tahmini
            if co2_ppm < 400:
                # Çok iyi havalandırma (dış mekan havası)
                return 20.9
            elif co2_ppm <= 800:
                # İyi havalandırma: 400-800 ppm → 20.9-20% O2
                return 20.9 - ((co2_ppm - 400) / 400) * 0.9
            elif co2_ppm <= 1200:
                # Orta: 800-1200 ppm → 20-19% O2
                return 20.0 - ((co2_ppm - 800) / 400) * 1.0
            elif co2_ppm <= 1500:
                # Zayıf: 1200-1500 ppm → 19-18% O2
                return 19.0 - ((co2_ppm - 1200) / 300) * 1.0
            elif co2_ppm <= 2000:
                # Kötü: 1500-2000 ppm → 18-17% O2
                return 18.0 - ((co2_ppm - 1500) / 500) * 1.0
            else:
                # Çok kötü: >2000 ppm → <17% O2
                # 2000 ppm üzerinde her 500 ppm için 0.5% O2 azalması
                oxygen = 17.0 - ((co2_ppm - 2000) / 500) * 0.5
                # Minimum %15 O2 (daha düşük değerler tehlikeli)
                return max(15.0, oxygen)
                
        except (ValueError, TypeError) as e:
            logger.warning(f"CO2'den O2 tahmini hatası: {e}")
            return None
    
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
                    button_name = self.get_button_name_by_pin(pin)
                    if button_name:
                        self.gpio_output_states[button_name] = False
            elif current_mode != GPIO.BCM:
                logger.warning(f"🔧 GPIO mode changed to {current_mode}, setting to BCM...")
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                for pin in self.outChannels:
                    GPIO.setup(pin, GPIO.OUT)
                    GPIO.output(pin, GPIO.HIGH)
                    button_name = self.get_button_name_by_pin(pin)
                    if button_name:
                        self.gpio_output_states[button_name] = False
                
                logger.info("✅ GPIO reinitialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"GPIO status check failed: {e}")
            GPIO_AVAILABLE = False
            return False
    
    def filter_dht_bit_shift(self, temp, hum):
        """DHT11 bit kayması anomalilerini filtrele.
        
        DHT11 sensöründe bazen bit kayması oluşabilir ve değerler 2 katına çıkar.
        Bu fonksiyon anormal değerleri tespit edip düzeltir.
        
        Strateji: Son geçerli değerle ORAN karşılaştırması (daha güvenilir)
        - Oran ~2x ise ve yarısı makul ise → kesin bit kayması, düzelt
        - İlk okumada yarısı makul değer aralığında ise → düzelt
        """
        # Güvenlik kontrolü - None değerleri aynen döndür
        if temp is None or hum is None:
            return temp, hum
        
        # Debug: Giriş değerlerini logla
        logger.debug(f"🔍 DHT Filter Input: temp={temp:.1f}°C, hum={hum:.0f}%, last_temp={self.last_valid_temp}, last_hum={self.last_valid_humidity}")
        
        corrected_temp = temp
        corrected_hum = hum
        temp_corrected = False
        hum_corrected = False
        
        # ========== SICAKLIK FİLTRESİ ==========
        half_temp = temp / 2
        
        # Strateji 1: Son geçerli değerle oran kontrolü (EN GÜVENİLİR)
        if self.last_valid_temp is not None:
            # Division by zero koruması
            if self.last_valid_temp > 0:
                ratio = temp / self.last_valid_temp
                logger.debug(f"  Temp ratio: {ratio:.2f}x (current/last: {temp:.1f}/{self.last_valid_temp:.1f})")
                
                # Oran ~2x ise ve yarısı makul aralıkta (15-30°C)
                if 1.8 <= ratio <= 2.2 and 15 <= half_temp <= 30:
                    corrected_temp = half_temp
                    temp_corrected = True
                    logger.warning(f"⚠️  DHT TEMP BIT-SHIFT: {temp:.1f}°C → {corrected_temp:.1f}°C (ratio: {ratio:.2f}x vs last: {self.last_valid_temp:.1f}°C)")
                # Oran ~1x ama mutlak değer çok yüksek (35°C+) ve yarısı son değere yakın
                elif temp > 35 and 15 <= half_temp <= 30 and abs(half_temp - self.last_valid_temp) < 5:
                    corrected_temp = half_temp
                    temp_corrected = True
                    logger.warning(f"⚠️  DHT TEMP HIGH: {temp:.1f}°C → {corrected_temp:.1f}°C (>35°C, half near last: {self.last_valid_temp:.1f}°C)")
        else:
            # Strateji 2: İlk okuma - sadece makul aralık kontrolü
            logger.debug(f"  First temp read, checking if {temp:.1f}°C needs correction (half={half_temp:.1f}°C)")
            if temp > 35 and 15 <= half_temp <= 30:
                corrected_temp = half_temp
                temp_corrected = True
                logger.warning(f"⚠️  DHT TEMP INIT: {temp:.1f}°C → {corrected_temp:.1f}°C (>35°C, no history)")
        
        # ==# Division by zero koruması
            if self.last_valid_humidity > 0:
                ratio = hum / self.last_valid_humidity
                logger.debug(f"  Hum ratio: {ratio:.2f}x (current/last: {hum:.0f}/{self.last_valid_humidity:.0f})")
                
                # Oran ~2x ise ve yarısı makul aralıkta (20-70%)
                if 1.8 <= ratio <= 2.2 and 20 <= half_hum <= 70:
                    corrected_hum = half_hum
                    hum_corrected = True
                    logger.warning(f"⚠️  DHT HUM BIT-SHIFT: {hum:.0f}% → {corrected_hum:.0f}% (ratio: {ratio:.2f}x vs last: {self.last_valid_humidity:.0f}%)")
                # Oran ~1x ama mutlak değer yüksek (70%+) ve yarısı son değere yakın
                elif hum > 60 and 20 <= half_hum <= 70 and abs(half_hum - self.last_valid_humidity) < 10:
                    corrected_hum = half_hum
                    hum_corrected = True
                    logger.warning(f"⚠️  DHT HUM HIGH: {hum:.0f}% → {corrected_hum:.0f}% (>60%, half near last: {self.last_valid_humidity:.0f}%)")
        else:
            # Strateji 2: İlk okuma - sadece makul aralık kontrolü
            logger.debug(f"  First hum read, checking if {hum:.0f}% needs correction (half={half_hum:.0f}%)")
            # 64%'yi de yakalamak için threshold'u 60%'ye düşür
            if hum > 60 and 20 <= half_hum <= 70:
                corrected_hum = half_hum
                hum_corrected = True
                logger.warning(f"⚠️  DHT HUM INIT: {hum:.0f}% → {corrected_hum:.0f}% (>60%, no history)")
        
        # Son geçerli değerleri güncelle (düzeltilmiş değerlerle)
        if 10 <= corrected_temp <= 40 and 15 <= corrected_hum <= 95:
            self.last_valid_temp = corrected_temp
            self.last_valid_humidity = corrected_hum
            logger.debug(f"  Updated last valid: temp={corrected_temp:.1f}°C, hum={corrected_hum:.0f}%")
        else:
            logger.debug(f"  Skipped update (out of range): temp={corrected_temp:.1f}°C, hum={corrected_hum:.0f}%")
        
        if temp_corrected or hum_corrected:
            logger.info(f"🔧 DHT Filter Output: {corrected_temp:.1f}°C, {corrected_hum:.0f}%")hum:.0f}% → {corrected_hum:.0f}% (>70%, no history)")
        
        # Son geçerli değerleri güncelle (düzeltilmiş değerlerle)
        if 10 <= corrected_temp <= 40 and 15 <= corrected_hum <= 95:
            self.last_valid_temp = corrected_temp
            self.last_valid_humidity = corrected_hum
        
        return corrected_temp, corrected_hum
    
    def read_sensors(self):
        """Sensörleri oku"""
        try:
            # DHT sensor - Use configured type (avoid re-detecting on every read)
            if DHT_AVAILABLE:
                logger.debug(f"🌡️  Reading DHT{self.sensorDht} sensor from GPIO {self.pinDht}...")
                try:
                    # Sabit sensör tipi ile okuma (daha kararlı ve log spam'i azaltır)
                    hum, temp = read_retry(sensor_type=self.sensorDht, pin=self.pinDht)
                    if hum is not None and temp is not None:
                        # DHT11 bit kayması filtresi uygula (güvenli)
                        try:
                            temp, hum = self.filter_dht_bit_shift(temp, hum)
                        except Exception as filter_error:
                            logger.error(f"⚠️  DHT filter error (using raw values): {filter_error}")
                            import traceback
                            logger.error(traceback.format_exc())
                            # Filtre hatası durumunda ham değerleri kullan
                        
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
                        # Başarılı okuma - hata sayacını sıfırla
                        self.sensor_error_count = 0
                    else:
                        # Sensör okuma başarısız - hata sayacını artır
                        self.sensor_error_count += 1
                        
                        # İlk 3 hatada son değeri tut (geçici okuma hataları için)
                        if self.sensor_error_count <= 3:
                            logger.debug(f"⚠️  DHT okuma hatası ({self.sensor_error_count}/3) - son değer korunuyor")
                            # sensor_data değerlerini değiştirme, son başarılı değeri göster
                        
                        # 3-10 arası hatada '--' göster
                        elif self.sensor_error_count <= 10:
                            logger.warning(f"⚠️  DHT sensor read failed (GPIO {self.pinDht}) - Deneme {self.sensor_error_count}/10")
                            self.sensor_data['temperature'] = {
                                'value': '--',
                                'status': f'Okuma hatası ({self.sensor_error_count}/10)'
                            }
                            self.sensor_data['humidity'] = {
                                'value': '--',
                                'status': f'Okuma hatası ({self.sensor_error_count}/10)'
                            }
                        
                        # 10 hatadan sonra simülasyon moduna geç (sensör muhtemelen bağlı değil)
                        else:
                            if self.sensor_error_count == 11:
                                logger.warning(f"⚠️  DHT sensör 10 kez okunamadı - simülasyon moduna geçiliyor")
                            
                            # Simülasyon verisi kullan
                            import random
                            base_temp = 24.5
                            base_hum = 60.0
                            temp = base_temp + random.uniform(-2.0, 2.0)
                            hum = base_hum + random.uniform(-5.0, 5.0)
                            
                            self.sensor_data['temperature'] = {
                                'value': f"{temp:.1f}",
                                'status': 'Sensör bağlı değil (simülasyon)'
                            }
                            self.sensor_data['humidity'] = {
                                'value': f"{hum:.0f}",
                                'status': 'Sensör bağlı değil (simülasyon)'
                            }
                            
                            # Her 20 okumada bir sensörü yeniden dene
                            if self.sensor_error_count % 20 == 0:
                                logger.info("🔄 DHT sensör yeniden deneniyor...")
                                self.sensor_error_count = 3  # 3'e sıfırla (direkt '--' gösterme)
                        
                except Exception as dht_error:
                    logger.error(f"❌ DHT{self.sensorDht} read exception: {dht_error}")
                    self.sensor_error_count += 1
                    
                    # Exception durumunda da simülasyona geç
                    if self.sensor_error_count >= 5:
                        import random
                        temp = 24.5 + random.uniform(-2.0, 2.0)
                        hum = 60.0 + random.uniform(-5.0, 5.0)
                        self.sensor_data['temperature'] = {
                            'value': f"{temp:.1f}",
                            'status': 'Sensör bağlı değil (simülasyon)'
                        }
                        self.sensor_data['humidity'] = {
                            'value': f"{hum:.0f}",
                            'status': 'Sensör bağlı değil (simülasyon)'
                        }
                    else:
                        self.sensor_data['temperature'] = {
                            'value': '--',
                            'status': f'Bağlantı hatası ({self.sensor_error_count}/5)'
                        }
                        self.sensor_data['humidity'] = {
                            'value': '--',
                            'status': f'Bağlantı hatası ({self.sensor_error_count}/5)'
                        }
            else:
                # DHT not available - use simulation data
                import random
                # Simulate realistic temperature and humidity values with wider range for testing
                base_temp = 24.5
                base_hum = 60.0
                # Add wider random variations for testing hysteresis control
                temp = base_temp + random.uniform(-2.5, 2.5)  # 22.0 - 27.0°C range
                hum = base_hum + random.uniform(-5.0, 5.0)

                self.sensor_data['temperature'] = {
                    'value': f"{temp:.1f}",
                    'status': 'SIMULATION'
                }
                self.sensor_data['humidity'] = {
                    'value': f"{hum:.0f}",
                    'status': 'SIMULATION'
                }
                logger.info(f"🔧 SIMULATION: {temp:.1f}°C, {hum:.0f}%rH")
            
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

            # CO2 (SCD30) sensör okuması - mevcutsa
            if self.co2_sensor_available and self.co2_sensor:
                try:
                    # Veri hazır mı kontrol et
                    ready = False
                    try:
                        ready = self.co2_sensor.get_data_ready()
                        # Bazı versiyonlarda sürekli 0/False döner ama yine de okuyabilir
                        if self._scd30_warmup_reads >= 2 and not ready:
                            logger.debug("get_data_ready() = False, ama warm-up tamamlandı, zorla okuyoruz")
                            ready = True
                    except Exception as ready_err:
                        # Bazı versiyonlarda get_data_ready() çalışmayabilir
                        logger.debug(f"get_data_ready() hatası: {ready_err}")
                        # Warm-up tamamlandıysa okumayı dene
                        if self._scd30_warmup_reads >= 2:
                            ready = True
                    
                    if ready:
                        # İlk 2 okumayı atla (warm-up period)
                        if self._scd30_warmup_reads < 2:
                            self._scd30_warmup_reads += 1
                            logger.info(f"🔄 SCD30 warm-up read {self._scd30_warmup_reads}/2 (skipping...)")
                            try:
                                # Okumayı yap ama kullanma (buffer'ı temizle)
                                self.co2_sensor.read_measurement_data()
                            except:
                                pass
                            self.sensor_data['co2'] = {
                                'value': '--',
                                'status': f'Warming up ({self._scd30_warmup_reads}/2)...'
                            }
                        else:
                            # Ölçüm verilerini oku (CO2, sıcaklık, nem)
                            co2_ppm, temp_c, humidity = self.co2_sensor.read_measurement_data()
                            
                            # Makul aralıkta mı kontrol et (400-5000 ppm tipik iç mekan)
                            if 0 <= co2_ppm <= 10000:
                                self.sensor_data['co2'] = {
                                    'value': f"{co2_ppm:.0f}",
                                    'status': 'OK'
                                }
                                
                                # DHT sensörü yoksa VEYA arızalıysa SCD30'dan sıcaklık ve nem kullan
                                # Sıcaklık ve nem değerlerinin geçerli olduğunu kontrol et
                                # ÖNEMLĐ: DHT çalışıyorsa (sensor_error_count <= 3) SCD30 değerlerini KULLANMA
                                if (not DHT_AVAILABLE) or (DHT_AVAILABLE and self.sensor_error_count > 3):
                                    # Daha katı validasyon: Negatif ve aşırı büyük değerleri reddet
                                    temp_valid = (temp_c is not None and 
                                                 -40 <= temp_c <= 85 and 
                                                 temp_c != 0.0 and 
                                                 abs(temp_c) < 100)  # Aşırı büyük değerleri reddet
                                    
                                    hum_valid = (humidity is not None and 
                                                0 <= humidity <= 100 and 
                                                humidity >= 0)  # Negatif değerleri reddet
                                    
                                    if temp_valid:
                                        self.sensor_data['temperature'] = {
                                            'value': f"{temp_c:.1f}",
                                            'status': 'SCD30 (CO2 sensörü)'
                                        }
                                    if hum_valid:
                                        self.sensor_data['humidity'] = {
                                            'value': f"{humidity:.0f}",
                                            'status': 'SCD30 (CO2 sensörü)'
                                        }
                                    if not DHT_AVAILABLE and (temp_valid or hum_valid):
                                        logger.info(f"🌡️  SCD30: {temp_c:.1f}°C, {humidity:.0f}%rH (DHT sensörü yok, SCD30 kullanılıyor)")
                                    elif DHT_AVAILABLE and self.sensor_error_count > 3 and (temp_valid or hum_valid):
                                        logger.info(f"🌡️  SCD30: {temp_c:.1f}°C, {humidity:.0f}%rH (DHT arızalı, SCD30 kullanılıyor)")
                                    elif not DHT_AVAILABLE and not (temp_valid or hum_valid):
                                        logger.warning(f"⚠️ SCD30 sıcaklık/nem geçersiz: {temp_c:.1f}°C, {humidity:.0f}%rH (atlandı)")
                                
                                # Oksijen sensörü yoksa CO2'den O2 tahmini yap
                                if not self.oxygen_sensor_available:
                                    estimated_o2 = self.estimate_oxygen_from_co2(co2_ppm)
                                    if estimated_o2 is not None:
                                        self.sensor_data['oxygen'] = {
                                            'value': f"{estimated_o2:.1f}",
                                            'status': f'Tahmini (CO2: {co2_ppm:.0f} ppm)'
                                        }
                                        logger.info(f"💡 O2 tahmini CO2'den: {estimated_o2:.1f}% (CO2: {co2_ppm:.0f} ppm)")
                                        logger.debug(f"DEBUG: sensor_data['oxygen'] = {self.sensor_data['oxygen']}")
                            else:
                                logger.warning(f"⚠️  Invalid CO2 reading: {co2_ppm} ppm")
                    # Hazır değilse önceki değer korunur
                except Exception as e:
                    logger.error(f"❌ CO2 (SCD30) read error: {e}")
                    # Hata durumunda sensörü devre dışı bırakmayalım; geçici olabilir
            
            # Log sensor data if values changed AND system is active
            # Conditional Logging: Don't log if system is in standby (all buttons OFF)
            system_active = any(self.button_states.values())
            
            if self.sensor_logger and system_active:
                self.sensor_logger.log_if_changed(self.sensor_data)
                
            # Firebase Update (optional)
            if self.firebase_manager and hasattr(self.firebase_manager, 'connected') and self.firebase_manager.connected:
                self.firebase_manager.update_sensor_data(self.sensor_data)
        
        except Exception as e:
            logger.error(f"Sensor read error: {e}")
            self.sensor_error_count += 1
            
            if self.sensor_error_count > 5:
                # Reset to safe state
                self.reset_to_safe_state()

            # Feed data to AI Manager
            if self.ai_manager:
                # Prepare data for AI
                sensor_values = {}
                if 'temperature' in self.sensor_data and self.sensor_data['temperature']['value'] != '--':
                    try:
                        sensor_values['temperature'] = float(self.sensor_data['temperature']['value'])
                    except ValueError:
                        pass
                if 'humidity' in self.sensor_data and self.sensor_data['humidity']['value'] != '--':
                    try:
                        sensor_values['humidity'] = float(self.sensor_data['humidity']['value'])
                    except ValueError:
                        pass
                if 'oxygen' in self.sensor_data and self.sensor_data['oxygen']['value'] != '--':
                    try:
                        sensor_values['oxygen'] = float(self.sensor_data['oxygen']['value'])
                    except ValueError:
                        pass
                
                # Actuator states
                actuator_states = {
                    'heater_on': self.gpio_output_states.get('b4', False) == True, # LOW=True=ON
                    'nebulizer_on': self.gpio_output_states.get('b2', False) == True,
                    'ozone_on': self.gpio_output_states.get('b8', False) == True
                }
                
                self.ai_manager.update_sensors(sensor_values, actuator_states)
    
    def control_logic(self):
        """Ana kontrol döngüsü"""
        try:
            # ⚠️ SAFETY: Skip all normal controls when in disinfection mode
            if self.disinfection_mode:
                logger.debug("🦠 Disinfection mode active - normal controls disabled")
                return
            
            # GPIO durumunu kontrol et (simulation mode'da da devam et)
            self.check_gpio_status()

            current_time = time.time()
            
            # Temperature control with hysteresis (b4 - pin 16)
            # Only control if function is enabled by user
            if self.button_states['b4']:
                if self.sensor_data['temperature']['value'] != '--':
                    temp = float(self.sensor_data['temperature']['value'])
                    temp_target = self.slider_values['sld3']

                    # Hysteresis control: prevents relay chattering
                    if temp < (temp_target - self.TEMP_HYSTERESIS):
                        # Below target - hysteresis → Turn heating ON
                        self.safe_gpio_output(16, GPIO.LOW)
                    elif temp > (temp_target + self.TEMP_HYSTERESIS):
                        # Above target + hysteresis → Turn heating OFF
                        self.safe_gpio_output(16, GPIO.HIGH)
                    # else: In hysteresis zone → Maintain current state (no change)
                else:
                    # Sensör okunamıyor - güvenlik için ısıtmayı kapat
                    self.safe_gpio_output(16, GPIO.HIGH)
                    logger.warning("⚠️  Temperature sensor unavailable - heating disabled for safety")
            else:
                # Function disabled - ensure GPIO is OFF
                self.safe_gpio_output(16, GPIO.HIGH)

            # Humidity control with hysteresis (b3 - pin 13)
            # Only control if function is enabled by user
            if self.button_states['b3']:
                if self.sensor_data['humidity']['value'] != '--':
                    hum = float(self.sensor_data['humidity']['value'])
                    hum_target = self.slider_values['sld2']

                    # Hysteresis control: prevents relay chattering
                    if hum < (hum_target - self.HUM_HYSTERESIS):
                        # Below target - hysteresis → Turn humidifier ON
                        self.safe_gpio_output(13, GPIO.LOW)
                    elif hum > (hum_target + self.HUM_HYSTERESIS):
                        # Above target + hysteresis → Turn humidifier OFF
                        self.safe_gpio_output(13, GPIO.HIGH)
                    # else: In hysteresis zone → Maintain current state (no change)
                else:
                    # Sensör okunamıyor - güvenlik için nemlendiriciye kapat
                    self.safe_gpio_output(13, GPIO.HIGH)
                    logger.warning("⚠️  Humidity sensor unavailable - humidifier disabled for safety")
            else:
                # Function disabled - ensure GPIO is OFF
                self.safe_gpio_output(13, GPIO.HIGH)

            # IR Temperature control with hysteresis (b5 - pin 19)
            # Only control if function is enabled by user
            ir_heater_active = False
            if self.button_states['b5']:
                if self.sensor_data['temperature']['value'] != '--':
                    temp = float(self.sensor_data['temperature']['value'])
                    ir_temp_target = self.slider_values['sld3']  # Using sld3 for IR temp target

                    # Hysteresis control: prevents relay chattering
                    if temp < (ir_temp_target - self.TEMP_HYSTERESIS):
                        # Below target - hysteresis → Turn IR heater ON
                        self.safe_gpio_output(19, GPIO.LOW)
                        ir_heater_active = True
                    elif temp > (ir_temp_target + self.TEMP_HYSTERESIS):
                        # Above target + hysteresis → Turn IR heater OFF
                        self.safe_gpio_output(19, GPIO.HIGH)
                        ir_heater_active = False
                    else:
                        # In hysteresis zone → Check current GPIO state
                        ir_heater_active = self.gpio_output_states.get('b5', False) == True
                else:
                    # Sensör okunamıyor - güvenlik için IR heater'ı kapat
                    self.safe_gpio_output(19, GPIO.HIGH)
                    ir_heater_active = False
                    logger.warning("⚠️  Temperature sensor unavailable - IR heater disabled for safety")
            else:
                # Function disabled - ensure GPIO is OFF
                self.safe_gpio_output(19, GPIO.HIGH)
                ir_heater_active = False

            # Carbon heater active state check
            carbon_heater_active = False
            if self.button_states['b4']:
                if self.sensor_data['temperature']['value'] != '--':
                    temp = float(self.sensor_data['temperature']['value'])
                    temp_target = self.slider_values['sld3']
                    # Check if heater is currently on (in hysteresis zone, check GPIO state)
                    if temp < (temp_target + self.TEMP_HYSTERESIS):
                        carbon_heater_active = self.gpio_output_states.get('b4', False) == True

            # Fan control based on heaters (b6 - pin 20)
            # Automatically turn on fan if either Carbon (b4) or IR (b5) heater is ACTUALLY running (GPIO LOW)
            # BUT: If user has manually enabled fan (b6=true and b6_manual=true), keep it ON regardless
            if carbon_heater_active or ir_heater_active:
                # At least one heater is active - turn fan ON
                self.safe_gpio_output(20, GPIO.LOW)
                # Update button state if not already set
                if not self.button_states['b6']:
                    self.button_states['b6'] = True
                    self.button_states['b6_manual'] = True  # Auto-enabled fan is treated as manual
                    logger.info("🌀 Fan otomatik açıldı - ısıtıcılar aktif")
            elif self.button_states.get('b6_manual', False) and self.button_states['b6']:
                # User has MANUALLY enabled the fan - KEEP IT ON even if heaters are off
                # Fan stays on until user manually disables it
                self.safe_gpio_output(20, GPIO.LOW)
                logger.debug("🌀 Fan manuel kontrol - açık kalıyor")
            else:
                # Both heaters are off AND fan was NOT manually enabled - turn fan OFF
                self.safe_gpio_output(20, GPIO.HIGH)
                if self.button_states['b6']:
                    self.button_states['b6'] = False
                self.button_states['b6_manual'] = False
                logger.debug("🌀 Fan otomatik kapatıldı - ısıtıcılar kapandı ve manuel kontrol yoktu")

            # Nebulizer duty cycle control (b2 - pin 6)
            # Only control if function is enabled by user
            if self.button_states['b2']:
                # Note: Initial DUTY start is handled by toggle_button event
                # Here we only update ongoing duty/free cycles
                self.update_nebulizer_duty_cycle()
            else:
                # Function disabled - ensure GPIO is OFF and reset duty cycle state
                self.safe_gpio_output(6, GPIO.HIGH)
                self.nebulizer_in_duty = False
                self.nebulizer_duty_start = 0
            
            # Ozone duty cycle control (b8 - pin 26)
            # Only control if function is enabled by user
            if self.button_states['b8']:
                # Note: Initial DUTY start is handled by toggle_button event
                # Here we only update ongoing duty/free cycles
                self.update_ozone_duty_cycle()
            else:
                # Function disabled - ensure GPIO is OFF and reset duty cycle state
                self.safe_gpio_output(26, GPIO.HIGH)
                self.ozone_in_duty = False
                self.ozone_duty_start = 0

            # Manual buttons - direct ON/OFF control
            # B1: Therapeutic Lighting (pin 5)
            if self.button_states['b1']:
                self.safe_gpio_output(5, GPIO.LOW)  # ON
            else:
                self.safe_gpio_output(5, GPIO.HIGH)  # OFF

            # B7: UV Sterilization (pin 21)
            if self.button_states['b7']:
                self.safe_gpio_output(21, GPIO.LOW)  # ON
            else:
                self.safe_gpio_output(21, GPIO.HIGH)  # OFF

        except Exception as e:
            logger.error(f"Control logic error: {e}")
    
    def nebulizer_control(self):
        """Nebulizer duty cycle control"""
        try:
            current_time = time.time()
            duty_duration = self.slider_values['sld8'] * 60  # duty minutes to seconds
            free_duration = self.slider_values['sld9'] * 60  # free minutes to seconds
            
            if not self.nebulizer_in_duty:
                # Start duty cycle
                self.safe_gpio_output(6, GPIO.LOW)  # Turn ON
                self.nebulizer_duty_start = current_time
                self.nebulizer_in_duty = True
                logger.info(f"Nebulizer DUTY cycle started - ON for {self.slider_values['sld8']} minutes")
            
        except Exception as e:
            logger.error(f"Nebulizer control error: {e}")
    
    def update_nebulizer_duty_cycle(self):
        """Update nebulizer duty cycle state"""
        try:
            # If button is OFF, stop duty cycle completely
            if not self.button_states['b2']:
                if self.nebulizer_in_duty or self.nebulizer_duty_start > 0:
                    self.safe_gpio_output(6, GPIO.HIGH)  # Turn OFF
                    self.nebulizer_in_duty = False
                    self.nebulizer_duty_start = 0  # Reset timer
                    logger.info("Nebulizer stopped - button OFF")
                return
            
            current_time = time.time()
            duty_duration = self.slider_values['sld8'] * 60
            free_duration = self.slider_values['sld9'] * 60
            
            if self.nebulizer_in_duty:
                # Check if duty time is complete
                if current_time - self.nebulizer_duty_start >= duty_duration:
                    self.safe_gpio_output(6, GPIO.HIGH)  # Turn OFF
                    self.nebulizer_in_duty = False
                    self.nebulizer_duty_start = current_time  # Start free time
                    logger.info(f"Nebulizer FREE cycle started - OFF for {self.slider_values['sld9']} minutes")
            else:
                # Check if free time is complete
                if current_time - self.nebulizer_duty_start >= free_duration:
                    # If button still active, start new DUTY cycle
                    if self.button_states['b2']:
                        self.safe_gpio_output(6, GPIO.LOW)  # Turn ON again
                        self.nebulizer_duty_start = current_time
                        self.nebulizer_in_duty = True
                        logger.info(f"Nebulizer new DUTY cycle started - ON for {self.slider_values['sld8']} minutes")
                    else:
                        # Button was turned off, complete cycle
                        self.last_nebulizer_time = current_time
                        self.nebulizer_in_duty = False
                        logger.info("Nebulizer stopped by user")

        except Exception as e:
            logger.error(f"Nebulizer duty cycle update error: {e}")
    
    def ozone_control(self):
        """Ozone duty cycle control with oxygen sensor intelligence (real or estimated)"""
        try:
            current_time = time.time()
            duty_duration = self.slider_values['sld10'] * 60  # duty minutes to seconds
            free_duration = self.slider_values['sld11'] * 60  # free minutes to seconds
            
            # Check oxygen levels if available (real sensor or CO2-estimated)
            # NOTE: Only extend duty for high O2, never reduce for low O2 (user confusion)
            oxygen_multiplier = 1.0
            if 'oxygen' in self.sensor_data:
                try:
                    current_oxygen = float(self.sensor_data['oxygen']['value'])
                    oxygen_source = self.sensor_data['oxygen']['status']
                    if current_oxygen > 24.0:
                        oxygen_multiplier = 1.5  # Longer duty for high oxygen
                        logger.info(f"🌟 High oxygen ({current_oxygen:.1f}%, {oxygen_source}) - Extended ozone duty")
                    # Removed LOW O2 reduction to prevent user confusion
                    # elif current_oxygen < 18.0:
                    #     oxygen_multiplier = 0.5  # Shorter duty for low oxygen
                    #     logger.info(f"⚠️ Low oxygen ({current_oxygen:.1f}%) - Reduced ozone duty")
                except (ValueError, KeyError):
                    pass
            
            adjusted_duty = int(duty_duration * oxygen_multiplier)
            
            if not self.ozone_in_duty:
                # Start duty cycle
                self.safe_gpio_output(26, GPIO.LOW)  # Turn ON
                self.ozone_duty_start = current_time
                self.ozone_in_duty = True
                logger.info(f"💨 Ozone DUTY cycle started - ON for {adjusted_duty//60} minutes")
            
        except Exception as e:
            logger.error(f"Ozone control error: {e}")
    
    def update_ozone_duty_cycle(self):
        """Update ozone duty cycle state"""
        try:
            # If button is OFF, stop duty cycle completely
            if not self.button_states['b8']:
                if self.ozone_in_duty or self.ozone_duty_start > 0:
                    self.safe_gpio_output(26, GPIO.HIGH)  # Turn OFF
                    self.ozone_in_duty = False
                    self.ozone_duty_start = 0  # Reset timer
                    logger.info("💨 Ozone stopped - button OFF")
                return
            
            current_time = time.time()
            duty_duration = self.slider_values['sld10'] * 60
            free_duration = self.slider_values['sld11'] * 60
            
            # Apply oxygen-based adjustment if available (real sensor or CO2-estimated)
            # NOTE: Only extend duty for high O2, never reduce for low O2 (user confusion)
            if 'oxygen' in self.sensor_data:
                try:
                    current_oxygen = float(self.sensor_data['oxygen']['value'])
                    oxygen_source = self.sensor_data['oxygen']['status']
                    if current_oxygen > 24.0:
                        duty_duration = int(duty_duration * 1.5)
                        logger.info(f"🌟 High O2 ({current_oxygen:.1f}%, {oxygen_source}) - Extended ozone duty to {duty_duration//60}min")
                    # Removed LOW O2 reduction to prevent user confusion
                    # elif current_oxygen < 18.0:
                    #     duty_duration = int(duty_duration * 0.5)
                except (ValueError, KeyError):
                    pass
            
            if self.ozone_in_duty:
                # Check if duty time is complete
                if current_time - self.ozone_duty_start >= duty_duration:
                    self.safe_gpio_output(26, GPIO.HIGH)  # Turn OFF
                    self.ozone_in_duty = False
                    self.ozone_duty_start = current_time  # Start free time
                    logger.info(f"💨 Ozone FREE cycle started - OFF for {free_duration//60} minutes")
            else:
                # Check if free time is complete
                if current_time - self.ozone_duty_start >= free_duration:
                    # If button still active, start new DUTY cycle
                    if self.button_states['b8']:
                        self.safe_gpio_output(26, GPIO.LOW)  # Turn ON again
                        self.ozone_duty_start = current_time
                        self.ozone_in_duty = True
                        logger.info(f"💨 Ozone new DUTY cycle started - ON for {self.slider_values['sld10']} minutes")
                    else:
                        # Button was turned off, complete cycle
                        self.last_ozone_time = current_time
                        self.ozone_in_duty = False
                        logger.info("💨 Ozone stopped by user")
                    
        except Exception as e:
            logger.error(f"Ozone duty cycle update error: {e}")
    
    def get_timer_data(self):
        """Get current timer states for frontend"""
        current_time = time.time()
        
        # Nebulizer timer data
        nebulizer_duty_duration = self.slider_values['sld8'] * 60
        nebulizer_free_duration = self.slider_values['sld9'] * 60
        
        # Only show timer if button is active
        if self.button_states['b2']:
            if self.nebulizer_in_duty:
                nebulizer_remaining = max(0, nebulizer_duty_duration - (current_time - self.nebulizer_duty_start))
                nebulizer_phase = "DUTY"
                nebulizer_total = nebulizer_duty_duration
            else:
                nebulizer_remaining = max(0, nebulizer_free_duration - (current_time - self.nebulizer_duty_start))
                nebulizer_phase = "FREE" if self.nebulizer_duty_start > 0 else "READY"
                nebulizer_total = nebulizer_free_duration if self.nebulizer_duty_start > 0 else 0
        else:
            # Button is OFF - show READY state
            nebulizer_remaining = 0
            nebulizer_phase = "READY"
            nebulizer_total = 0
        
        # Ozone timer data
        ozone_duty_duration = self.slider_values['sld10'] * 60
        ozone_free_duration = self.slider_values['sld11'] * 60
        
        # Apply oxygen-based adjustment for display
        # NOTE: Only extend duty for high O2, never reduce for low O2 (user confusion)
        if self.oxygen_sensor_available and 'oxygen' in self.sensor_data:
            try:
                current_oxygen = float(self.sensor_data['oxygen']['value'])
                if current_oxygen > 24.0:
                    ozone_duty_duration = int(ozone_duty_duration * 1.5)
                # Removed LOW O2 reduction to prevent user confusion
                # elif current_oxygen < 18.0:
                #     ozone_duty_duration = int(ozone_duty_duration * 0.5)
            except (ValueError, KeyError):
                pass
        
        # Only show timer if button is active
        if self.button_states['b8']:
            if self.ozone_in_duty:
                ozone_remaining = max(0, ozone_duty_duration - (current_time - self.ozone_duty_start))
                ozone_phase = "DUTY"
                ozone_total = ozone_duty_duration
            else:
                ozone_remaining = max(0, ozone_free_duration - (current_time - self.ozone_duty_start))
                ozone_phase = "FREE" if self.ozone_duty_start > 0 else "READY"
                ozone_total = ozone_free_duration if self.ozone_duty_start > 0 else 0
        else:
            # Button is OFF - show READY state
            ozone_remaining = 0
            ozone_phase = "READY"
            ozone_total = 0
        
        return {
            'nebulizer': {
                'phase': nebulizer_phase,
                'remaining': int(nebulizer_remaining),
                'total': int(nebulizer_total)
            },
            'ozone': {
                'phase': ozone_phase,
                'remaining': int(ozone_remaining),
                'total': int(ozone_total)
            }
        }
    
    def reset_to_safe_state(self):
        """Güvenli duruma geç"""
        logger.warning("Resetting to safe state")
        for pin in self.outChannels:
            self.safe_gpio_output(pin, GPIO.HIGH)
        
        for key in self.button_states:
            self.button_states[key] = False
    
    def toggle_button(self, name, pin, state):
        """Buton kontrolü - button_states ve GPIO'yu anında değiştir"""
        try:
            # Button state'i güncelle
            self.button_states[name] = state
            logger.info(f"Button {name}: {'ENABLED' if state else 'DISABLED'}")

            # GPIO'yu HEMEN ayarla (anında feedback için)
            if state:
                # Buton ENABLED -> GPIO LOW (relay ON)
                self.safe_gpio_output(pin, GPIO.LOW)
                self.gpio_output_states[name] = True  # LOW = aktif = True
                logger.info(f"GPIO {pin} -> LOW (relay ON)")

                # Fan manuel kontrol ediliyorsa, manual flag set et
                if name == 'b6':  # Fan
                    self.button_states['b6_manual'] = True
                    logger.info("🔧 Fan manuel kontrol etkinleştirildi - otomatik kapanmayacak")

                # Start duty cycles immediately for duty-cycle buttons
                if name == 'b2':  # Nebulizer
                    current_time = time.time()
                    self.nebulizer_duty_start = current_time
                    self.nebulizer_in_duty = True
                    self.last_nebulizer_time = current_time - (self.slider_values['sld6'] * 3600)  # Force interval check to pass
                    logger.info(f"💧 Nebulizer DUTY cycle started immediately - ON for {self.slider_values['sld8']} minutes")
                elif name == 'b8':  # Ozone
                    current_time = time.time()
                    self.ozone_duty_start = current_time
                    self.ozone_in_duty = True
                    self.last_ozone_time = current_time - (self.slider_values['sld7'] * 3600)  # Force interval check to pass
                    logger.info(f"💨 Ozone DUTY cycle started immediately - ON for {self.slider_values['sld10']} minutes")
            else:
                # Buton DISABLED -> GPIO HIGH (relay OFF)
                self.safe_gpio_output(pin, GPIO.HIGH)
                self.gpio_output_states[name] = False  # HIGH = pasif = False
                logger.info(f"GPIO {pin} -> HIGH (relay OFF)")

                # Fan manuel olarak kapatılırsa, manual flag'i sıfırla
                if name == 'b6':  # Fan
                    self.button_states['b6_manual'] = False
                    logger.info("🔧 Fan manuel kontrol devre dışı - otomatik kontrole hazır")

                # Reset timers when button is turned OFF
                if name == 'b2':  # Nebulizer
                    self.nebulizer_in_duty = False
                    self.nebulizer_duty_start = 0
                    logger.info("Nebulizer timer reset to READY")
                elif name == 'b8':  # Ozone
                    self.ozone_in_duty = False
                    self.ozone_duty_start = 0
                    logger.info("Ozone timer reset to READY")

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
                        if "ai_enabled" in data and AI_AVAILABLE:
                            self.ai_enabled = data["ai_enabled"]
                            logger.info(f"🤖 AI enabled preference loaded: {self.ai_enabled}")
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

                    # GÜVENLİK: UV ve Ozon butonları dosyada ON olsa bile başlangıçta OFF
                    self.button_states["b7"] = False  # UV Sterilization
                    self.button_states["b8"] = False  # Ozone Sterilization
                    logger.info("🔒 UV/Ozone forced OFF at startup (safety)")
        except Exception as e:
            logger.error(f"Load settings error: {e}")
    
    def save_settings(self):
        """Ayarları JSON formatında dosyaya kaydet"""
        try:
            # UV ve Ozon butonlarını herzaman kapalı kaydet (güvenlik)
            button_states_to_save = self.button_states.copy()
            button_states_to_save["b7"] = False  # UV Sterilization
            button_states_to_save["b8"] = False  # Ozone Sterilization

            settings_data = {
                "slider_values": self.slider_values,
                "button_states": button_states_to_save,
                "ai_enabled": self.ai_enabled
            }

            with open("Failure.dat", "w") as f:
                json.dump(settings_data, f, indent=4)

            logger.info("✅ Settings saved (UV/Ozone forced OFF)")
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
                    logger.debug(f"DEBUG: Emitting sensor_update: {self.sensor_data}")
                    socketio.emit('sensor_update', {
                        'type': 'sensor_update',
                        'sensors': self.sensor_data
                    })
                    
                    # Send timer updates every 5 seconds
                    socketio.emit('timer_update', self.get_timer_data())
                    
                    logger.debug("DEBUG: Sensor and timer updates emitted successfully")
                except Exception as e:
                    logger.error(f"Socket.IO emit error: {e}")
                time.sleep(15)  # 15 saniyede bir (DHT sensör kararlılığı için)

        # AI Update Loop
        def ai_loop():
            if not AI_AVAILABLE or not self.ai_manager:
                logger.info("🤖 AI loop skipped - AI module not available")
                return
            
            logger.info("🤖 AI loop started (waiting for enable signal)")
            frame_count = 0
            last_log_time = time.time()
            
            while self.running and self.ai_manager:
                try:
                    # Skip if AI not enabled
                    if not self.ai_enabled:
                        time.sleep(1)
                        continue
                    
                    ai_data = self.ai_manager.get_update()
                    frame_count += 1
                    
                    # Log status every 10 seconds
                    current_time = time.time()
                    if current_time - last_log_time > 10:
                        has_frame = ai_data and ai_data.get('frame') is not None
                        logger.info(f"🤖 AI Status: frames processed={frame_count}, has_frame={has_frame}, vision_running={self.ai_manager.vision.running}")
                        last_log_time = current_time
                    
                    if ai_data and ai_data.get('frame'):
                        socketio.emit('ai_update', ai_data)
                        logger.debug(f"✅ AI frame emitted (size: {len(ai_data.get('frame', ''))} bytes)")
                    else:
                        # Log level reduced to debug to prevent spam
                        logger.debug("⚠️  AI update skipped - no frame available yet")
                except Exception as e:
                    logger.error(f"AI update error: {e}", exc_info=True)
                time.sleep(1.0) # 1 FPS update rate for UI

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
                    # WebSocket ile button durumlarını VE GPIO output state'lerini gönder
                    socketio.emit('button_update', {
                        'type': 'button_update',
                        'buttons': self.button_states,
                        'gpio_outputs': self.gpio_output_states
                    })
                time.sleep(1)  # 1 saniyede bir
        
        self.sensor_thread = threading.Thread(target=sensor_loop, daemon=True)
        self.control_thread = threading.Thread(target=control_loop, daemon=True)
        
        self.sensor_thread.start()
        self.control_thread.start()

        if self.ai_manager:
            self.ai_manager.start()
            self.ai_thread = threading.Thread(target=ai_loop, daemon=True)
            self.ai_thread.start()
            logger.info("🧠 AI Manager started")
        
        logger.info("✅ Background threads started")
    
    def stop_threads(self):
        """Thread'leri durdur"""
        self.running = False
        if self.sensor_thread:
            self.sensor_thread.join(timeout=2)
        if self.control_thread:
            self.control_thread.join(timeout=2)
        if self.control_thread:
            self.control_thread.join(timeout=2)
        
        if self.ai_manager:
            self.ai_manager.stop()
            if hasattr(self, 'ai_thread'):
                self.ai_thread.join(timeout=2)

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

@app.route('/logs')
def logs_page():
    """Log görüntüleme sayfası"""
    return app.send_static_file('logs.html')

@app.route('/api/status')
def get_status():
    """Sistem durumunu al"""
    return jsonify({
        'sensors': kuvoz_server.sensor_data,
        'buttons': kuvoz_server.button_states,
        'sliders': kuvoz_server.slider_values,
        'gpio_outputs': kuvoz_server.gpio_output_states,
        'timers': kuvoz_server.get_timer_data(),
        'system': kuvoz_server.get_system_status(),
        'timestamp': time.time()
    })

@app.route('/api/logs', methods=['GET', 'DELETE'])
def get_logs():
    """Sensor loglarını getir veya sil"""
    if not kuvoz_server.sensor_logger:
        return jsonify({'error': 'Logging not available', 'data': []})
    
    # Handle DELETE request to clear logs
    if request.method == 'DELETE':
        try:
            success = kuvoz_server.sensor_logger.clear_all_data()
            if success:
                return jsonify({'success': True, 'message': 'All logs cleared'})
            else:
                return jsonify({'success': False, 'error': 'Database error'}), 500
        except Exception as e:
            logger.error(f"Error clearing logs: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # Handle GET request to fetch logs
    try:
        limit = int(request.args.get('limit', 100))
        days = float(request.args.get('days', 1.0))
        
        start_time = datetime.datetime.now() - datetime.timedelta(days=days)
        readings = kuvoz_server.sensor_logger.get_readings(start_time=start_time, limit=limit)
        
        return jsonify({'data': readings})
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        return jsonify({'error': str(e), 'data': []})

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """WebSocket bağlantısı"""
    logger.info('Client connected')
    
    # Get system status dynamically
    system_status = kuvoz_server.get_system_status()
    
    emit('status_response', {
        'type': 'status_response',
        'sensors': kuvoz_server.sensor_data,
        'buttons': kuvoz_server.button_states,
        'gpio_outputs': kuvoz_server.gpio_output_states,
        'sliders': kuvoz_server.slider_values,
        'timers': kuvoz_server.get_timer_data(),
        'system': system_status,
        'ai_available': AI_AVAILABLE
    })
    
    logger.debug(f'DEBUG (connect): oxygen_available={system_status.get("oxygen_available")}, co2_available={system_status.get("co2_available")}')

@socketio.on('get_status')
def handle_get_status(data=None):
    """Get initial status"""
    logger.debug('DEBUG: Client requested status')
    logger.debug(f'DEBUG: Current sensor data: {kuvoz_server.sensor_data}')
    
    # Get page parameter if provided
    page = data.get('page', 'index') if data else 'index'
    logger.debug(f'DEBUG: get_status from page: {page}')

    # Note: UV/Ozone button protection is handled in toggle_button event
    # Do NOT reset button states here - it causes conflict when multiple tabs are open

    # Get system status dynamically (oxygen_available updates with CO2 estimation)
    system_status = kuvoz_server.get_system_status()
    
    status_data = {
        'type': 'status_response',
        'sensors': kuvoz_server.sensor_data,
        'buttons': kuvoz_server.button_states,
        'gpio_outputs': kuvoz_server.gpio_output_states,
        'sliders': kuvoz_server.slider_values,
        'timers': kuvoz_server.get_timer_data(),
        'system': system_status,
        'ai_available': AI_AVAILABLE,
        'ai_enabled': kuvoz_server.ai_enabled,
        'disinfection_mode': kuvoz_server.disinfection_mode
    }
    
    logger.debug(f'DEBUG (get_status): oxygen_available={system_status.get("oxygen_available")}, co2_available={system_status.get("co2_available")}')
    logger.debug(f'DEBUG (get_status): sensor_data keys={list(kuvoz_server.sensor_data.keys())}')
    emit('status_response', status_data)

@socketio.on('toggle_button')
def handle_toggle_button(data):
    """Handle button toggle"""
    try:
        name = data.get('name')
        pin = data.get('pin')
        state = data.get('state')
        page = data.get('page', 'index')  # Get current page, default to 'index'
        
        logger.info(f'Button toggle: {name} (pin {pin}) -> {state} from page: {page}')

        # Block UV (b7) and Ozone (b8) buttons if not on cleaning page
        if name in ['b7', 'b8'] and page != 'cleaning':
            logger.warning(f'Button {name} blocked - only allowed on cleaning page')
            emit('error', {
                'type': 'warning',
                'message': 'UV ve Ozon sadece Temizlik sayfasında kullanılabilir'
            })
            return
        
        # ⚠️ DISINFECTION SAFETY MODE: Activate when UV or Ozone is turned ON
        if name in ['b7', 'b8'] and state == True:
            if not kuvoz_server.disinfection_mode:
                logger.info('🦠 Activating disinfection safety mode - disabling normal controls')
                kuvoz_server.disinfection_mode = True
                kuvoz_server.disinfection_start_time = time.time()
                
                # Turn off all normal functions (b1-b6)
                for btn_name in ['b1', 'b2', 'b3', 'b4', 'b5', 'b6']:
                    if kuvoz_server.button_states.get(btn_name):
                        pin_index = int(btn_name[1:]) - 1
                        btn_pin = kuvoz_server.outChannels[pin_index]
                        kuvoz_server.toggle_button(btn_name, btn_pin, False)
                        logger.info(f'  → Disabled {btn_name} for safety')
                
                # Notify all clients
                emit('disinfection_mode', {
                    'active': True,
                    'message': 'Dezenfeksiyon modu aktif - normal kontroller devre dışı'
                }, broadcast=True)
        
        # ⚠️ DISINFECTION SAFETY MODE: Deactivate when BOTH UV and Ozone are OFF
        if name in ['b7', 'b8'] and state == False:
            if kuvoz_server.disinfection_mode:
                # Check if both UV and Ozone are now OFF
                uv_off = not kuvoz_server.button_states.get('b7', False)
                ozone_off = not kuvoz_server.button_states.get('b8', False)
                
                # Need to account for the button we're about to turn off
                if name == 'b7':
                    uv_off = True
                elif name == 'b8':
                    ozone_off = True
                
                if uv_off and ozone_off:
                    logger.info('🦠 Deactivating disinfection safety mode - re-enabling normal controls')
                    kuvoz_server.disinfection_mode = False
                    kuvoz_server.disinfection_start_time = 0
                    
                    # Notify all clients
                    emit('disinfection_mode', {
                        'active': False,
                        'message': 'Normal kontroller tekrar aktif'
                    }, broadcast=True)

        if name and pin is not None:
            kuvoz_server.toggle_button(name, int(pin), state if state is not None else None)
            # Emit update to all clients with both button states and GPIO outputs
            update_data = {
                'type': 'button_update',
                'buttons': kuvoz_server.button_states,
                'gpio_outputs': kuvoz_server.gpio_output_states
            }
            logger.debug(f'DEBUG: Emitting button_update: {update_data}')
            # Use emit() with broadcast=True within handler context
            emit('button_update', update_data, broadcast=True)
            logger.debug('DEBUG: button_update emitted successfully')
    except Exception as e:
        logger.error(f'Toggle button error: {e}')

@socketio.on('update_slider')
def handle_update_slider(data):
    """Handle slider value update"""
    try:
        slider_id = data.get('id')
        value = data.get('value')
        logger.info(f'Slider update: {slider_id} -> {value}')

        if slider_id and value is not None:
            kuvoz_server.update_slider(slider_id, value)
            # Emit update to all clients
            emit('slider_update', {
                'type': 'slider_update',
                'sliders': kuvoz_server.slider_values
            }, broadcast=True)

            # If duty/free time sliders changed, immediately send timer update
            if slider_id in ['sld8', 'sld9', 'sld10', 'sld11']:
                emit('timer_update', kuvoz_server.get_timer_data(), broadcast=True)
                logger.info(f'Timer update sent immediately due to {slider_id} change')
    except Exception as e:
        logger.error(f'Update slider error: {e}')

@socketio.on('save_settings')
def handle_save_settings(data=None):
    """Handle save settings request"""
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
    except Exception as e:
        logger.error(f'Save settings error: {e}')
        emit('error', {
            'type': 'error',
            'message': f'Ayar kaydetme hatası: {str(e)}'
        })

@socketio.on('toggle_ai')
def handle_toggle_ai(data):
    """Handle AI enable/disable toggle"""
    try:
        enabled = data.get('enabled', False)
        
        if not AI_AVAILABLE:
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
        kuvoz_server.ai_enabled = enabled
        
        if enabled and not old_state:
            # Start AI manager (only if not already running)
            try:
                kuvoz_server.ai_manager.start()
                logger.info('🤖 AI Module enabled by user')
                # Save preference
                kuvoz_server.save_settings()
                emit('ai_status', {
                    'enabled': True,
                    'message': 'AI analizi başlatıldı'
                }, broadcast=True)
            except Exception as e:
                logger.error(f'Failed to start AI: {e}')
                kuvoz_server.ai_enabled = False
                emit('error', {
                    'type': 'error',
                    'message': f'AI başlatma hatası: {str(e)}'
                })
        elif not enabled and old_state:
            # Stop AI manager
            try:
                kuvoz_server.ai_manager.stop()
                logger.info('🤖 AI Module disabled by user')
                # Save preference
                kuvoz_server.save_settings()
                emit('ai_status', {
                    'enabled': False,
                    'message': 'AI analizi durduruldu'
                }, broadcast=True)
            except Exception as e:
                logger.error(f'Failed to stop AI: {e}')
        
    except Exception as e:
        logger.error(f'Toggle AI error: {e}')
        emit('error', {
            'type': 'error',
            'message': f'AI toggle hatası: {str(e)}'
        })


@socketio.on('shutdown')
def handle_shutdown(data=None):
    """Handle system shutdown request"""
    logger.info('🔴 SHUTDOWN EVENT RECEIVED!')  # Debug log
    try:
        logger.info('System shutdown requested')
        emit('success', {
            'type': 'success',
            'message': 'Sistem kapatılıyor...'
        })
        # Delay to allow response to be sent
        def shutdown_system():
            logger.info('🔴 Shutdown thread started')  # Debug log
            time.sleep(2)
            if GPIO_AVAILABLE:
                logger.info('🔴 Executing: sudo shutdown -h now')  # Debug log
                os.system('sudo shutdown -h now')
            else:
                logger.warning('Shutdown skipped - GPIO not available (simulation mode)')

        shutdown_thread = threading.Thread(target=shutdown_system, daemon=True)
        shutdown_thread.start()
        logger.info('🔴 Shutdown thread launched')  # Debug log
    except Exception as e:
        logger.error(f'🔴 Shutdown error: {e}')
        emit('error', {
            'type': 'error',
            'message': f'Kapatma hatası: {str(e)}'
        })

@socketio.on('restart')
def handle_restart(data=None):
    """Handle system restart request"""
    logger.info('🟢 RESTART EVENT RECEIVED!')  # Debug log
    try:
        logger.info('System restart requested')
        emit('success', {
            'type': 'success',
            'message': 'Sistem yeniden başlatılıyor...'
        })
        # Delay to allow response to be sent
        def restart_system():
            logger.info('🟢 Restart thread started')  # Debug log
            time.sleep(2)
            if GPIO_AVAILABLE:
                logger.info('🟢 Executing: sudo reboot')  # Debug log
                os.system('sudo reboot')
            else:
                logger.warning('Restart skipped - GPIO not available (simulation mode)')

        restart_thread = threading.Thread(target=restart_system, daemon=True)
        restart_thread.start()
        logger.info('🟢 Restart thread launched')  # Debug log
    except Exception as e:
        logger.error(f'🟢 Restart error: {e}')
        emit('error', {
            'type': 'error',
            'message': f'Yeniden başlatma hatası: {str(e)}'
        })

@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket bağlantı kesildi"""
    logger.info('Client disconnected')

# ============================================================================
# TAILSCALE YÖNETIMI
# ============================================================================

@socketio.on('tailscale_status')
def handle_tailscale_status():
    """Tailscale durumunu kontrol et"""
    try:
        # Tailscale yüklü mü kontrol et
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
        
        # Tailscaled servisi çalışıyor mu kontrol et
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
        
        # Tailscale durumunu kontrol et
        result = subprocess.run(
            ['tailscale', 'status', '--json'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            status_data = json.loads(result.stdout)
            backend_state = status_data.get('BackendState', 'Unknown')
            
            # BackendState kontrolü - sadece "Running" bağlı demek
            # Diğer durumlar: "Stopped", "NeedsLogin", "NoState"
            is_connected = backend_state == 'Running'
            
            # IP adreslerini al
            ip_addresses = []
            self_info = status_data.get('Self', {})
            if self_info and is_connected:
                tailscale_ips = self_info.get('TailscaleIPs', [])
                ip_addresses = tailscale_ips
            
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
    except Exception as e:
        logger.error(f'Tailscale status error: {e}')
        emit('tailscale_status_response', {
            'installed': True,
            'connected': False,
            'message': f'Durum okunamadı: {str(e)}'
        })

@socketio.on('tailscale_install')
def handle_tailscale_install():
    """Tailscale kurulumunu başlat"""
    try:
        # Tailscale zaten yüklü mü kontrol et
        check_installed = subprocess.run(
            ['which', 'tailscale'],
            capture_output=True,
            text=True
        )
        
        if check_installed.returncode == 0:
            emit('tailscale_install_response', {
                'success': False,
                'message': 'Tailscale zaten kurulu'
            })
            return
        
        # Tailscale kurulum scriptini çalıştır
        emit('tailscale_install_progress', {
            'message': 'Tailscale indiriliyor...'
        })
        
        install_result = subprocess.run(
            ['curl', '-fsSL', 'https://tailscale.com/install.sh'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if install_result.returncode == 0:
            # Scripti çalıştır
            emit('tailscale_install_progress', {
                'message': 'Tailscale kuruluyor...'
            })
            
            install_script = subprocess.run(
                ['sh', '-c', install_result.stdout],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if install_script.returncode == 0:
                emit('tailscale_install_response', {
                    'success': True,
                    'message': 'Tailscale başarıyla kuruldu'
                })
            else:
                emit('tailscale_install_response', {
                    'success': False,
                    'message': f'Kurulum hatası: {install_script.stderr}'
                })
        else:
            emit('tailscale_install_response', {
                'success': False,
                'message': 'Kurulum scripti indirilemedi'
            })
            
    except subprocess.TimeoutExpired:
        emit('error', {'message': 'Kurulum zaman aşımına uğradı'})
    except Exception as e:
        logger.error(f'Tailscale install error: {e}')
        emit('error', {'message': f'Kurulum hatası: {str(e)}'})

@socketio.on('tailscale_connect')
def handle_tailscale_connect():
    """Tailscale bağlantısı başlat ve auth URL oluştur"""
    try:
        logger.info('Tailscale connect requested')
        
        # Önce mevcut durumu kontrol et
        status_check = subprocess.run(
            ['tailscale', 'status', '--json'],
            capture_output=True,
            text=True,
            timeout=20
        )
        
        if status_check.returncode == 0:
            status_data = json.loads(status_check.stdout)
            backend_state = status_data.get('BackendState', 'Unknown')
            
            # Zaten bağlıysa bilgi ver
            if backend_state == 'Running':
                logger.info('Tailscale already connected')
                emit('tailscale_connect_response', {
                    'success': True,
                    'already_connected': True,
                    'message': 'Tailscale zaten bağlı'
                })
                # Durum güncellemesi için emit
                socketio.emit('tailscale_status_response', {
                    'installed': True,
                    'connected': True,
                    'state': backend_state,
                    'ips': status_data.get('TailscaleIPs', []),
                    'hostname': status_data.get('Self', {}).get('HostName', 'Unknown')
                }, namespace='/')
                return
        
        logger.info('Starting tailscale up command...')
        
        # Tailscale up komutu - non-blocking şekilde başlat
        # Önemli: --timeout=0 ile auth URL'den sonra hemen dön
        result = subprocess.run(
            ['sudo', 'tailscale', 'up', '--reset', '--timeout=5s'],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        logger.info(f'Tailscale up completed with return code: {result.returncode}')
        
        # Output'u birleştir
        output = result.stdout + result.stderr
        logger.info(f'Output length: {len(output)} chars')
        logger.debug(f'Output preview: {output[:300]}...')
        
        # Auth URL'yi bul
        url_pattern = r'https://login\.tailscale\.com/a/[a-z0-9]+'
        match = re.search(url_pattern, output)
        
        if match:
            auth_url = match.group(0)
            logger.info(f'Auth URL found: {auth_url}')
            
            # QR kod oluştur
            qr_code_data = None
            if QRCODE_AVAILABLE:
                try:
                    logger.info('Generating QR code...')
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_L,
                        box_size=10,
                        border=4,
                    )
                    qr.add_data(auth_url)
                    qr.make(fit=True)
                    
                    img = qr.make_image(fill_color="black", back_color="white")
                    
                    # Convert to base64
                    buffered = BytesIO()
                    img.save(buffered, format="PNG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    qr_code_data = f"data:image/png;base64,{img_str}"
                    logger.info('QR code generated successfully')
                except Exception as e:
                    logger.error(f'QR code generation error: {e}')
            else:
                logger.warning('QR code library not available')
            
            emit('tailscale_auth_url', {
                'url': auth_url,
                'qr_code': qr_code_data
            })
            return
        
        # Auth URL bulunamadı - durum kontrol et
        logger.warning('No auth URL found in output')
        
        # Tekrar durum kontrol et
        time.sleep(1)
        final_status = subprocess.run(
            ['tailscale', 'status', '--json'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if final_status.returncode == 0:
            status_data = json.loads(final_status.stdout)
            if status_data.get('BackendState') == 'Running':
                emit('tailscale_connect_response', {
                    'success': True,
                    'message': 'Bağlantı başarılı (auth URL gerekmedi)'
                })
            else:
                emit('error', {
                    'message': 'Bağlantı başlatıldı ama durum belirsiz. Sayfayı yenileyin.'
                })
        else:
            emit('error', {
                'message': 'Bağlantı kuruldu ama auth URL bulunamadı. Komut satırından kontrol edin: tailscale status'
            })
            
    except subprocess.TimeoutExpired:
        logger.error('Tailscale connect timeout')
        emit('error', {'message': 'Bağlantı komutu zaman aşımına uğradı. Lütfen tekrar deneyin veya: sudo tailscale up'})
    except Exception as e:
        logger.error(f'Tailscale connect error: {e}')
        emit('error', {'message': f'Bağlantı hatası: {str(e)}'})

@socketio.on('tailscale_disconnect')
def handle_tailscale_disconnect():
    """Tailscale bağlantısını kes"""
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
            emit('error', {
                'message': f'Bağlantı kesilemedi: {result.stderr}'
            })
            
    except Exception as e:
        logger.error(f'Tailscale disconnect error: {e}')
        emit('error', {'message': f'Hata: {str(e)}'})

# ============================================================================
# WEBSOCKET EVENT HANDLERS (DEVAM)
# ============================================================================

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
                'gpio_outputs': kuvoz_server.gpio_output_states,
                'sliders': kuvoz_server.slider_values,
                'timers': kuvoz_server.get_timer_data(),
                'system': kuvoz_server.get_system_status()
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

def get_local_ip():
    """Get local network IP address"""
    try:
        # Create a socket to get the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Connect to Google DNS (doesn't actually send data)
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

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
        PORT = 8000
        local_ip = get_local_ip()

        logger.info("🚀 Starting Kuvoz Web Server...")
        logger.info(f"📱 Local access:   http://localhost:{PORT}")
        logger.info(f"🌐 Network access: http://{local_ip}:{PORT}")

        if SIMULATION_MODE:
            logger.info("⚠️  Running in simulation mode - no GPIO control")

        max_retries = 5
        for attempt in range(max_retries):
            try:
                socketio.run(app, host='0.0.0.0', port=PORT, debug=False, allow_unsafe_werkzeug=True)
                break
            except OSError as e:
                if "Address already in use" in str(e) or e.errno == 98:
                    logger.warning(f"⚠️  Port {PORT} in use, waiting to retry ({attempt+1}/{max_retries})...")
                    time.sleep(2)
                else:
                    raise e
    
    except KeyboardInterrupt:
        logger.info("⏹️  Server stopped by user")
    
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
    
    finally:
        kuvoz_server.cleanup()