#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kuvoz Incubator Control System - Flask Web Server
Kivy yerine web tabanlı interface
WebSocket ile real-time iletişim
"""

from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from flask_socketio import SocketIO, emit
import threading
import time
import datetime
import json
import copy
import os
import sys
import logging
import subprocess
import shutil
import re
from disk_cleanup_utils import perform_disk_cleanup
from app.care.patient_profiles import (
    build_patient_auto_profile,
    parse_age_weeks,
)
from app.control.climate_controller import (
    decide_cooling_output,
    decide_hysteresis_output,
    evaluate_humidity_purge,
)
from app.control.duty_cycles import (
    build_timer_state,
    compute_ozone_duty_duration,
    resolve_ozone_duty_duration,
    start_duty_cycle,
    update_duty_cycle_state,
)
from app.hardware.gpio_controller import (
    DEFAULT_DHT_PIN,
    DEFAULT_WPS_PIN,
    GPIOController,
    OUTPUT_CHANNELS,
    TOUCH_BUTTON_PINS,
    button_name_by_pin,
    calculate_fan_speed_percent,
    get_sensor_numeric_value,
    heater_output_active,
    normalize_fan_output_mode,
    reserved_gpio_pins,
)
from app.hardware.sensors import (
    apply_moving_average as apply_dht_moving_average,
    filter_dht_bit_shift as filter_dht_bit_shift_helper,
    probe_oxygen_sensor as probe_oxygen_sensor_helper,
)
from app.routes import (
    register_basic_socket_routes,
    register_http_routes,
    register_monitoring_routes,
    register_settings_socket_routes,
    register_system_socket_routes,
    register_tailscale_socket_routes,
    register_wifi_socket_routes,
)
from app.services import (
    BackgroundTaskManager,
    WifiWPSService,
    build_patient_id,
    classify_git_update_error,
    ensure_patient_storage,
    get_all_ips,
    get_git_update_diagnostics,
    get_git_version_info,
    get_local_ip,
    load_patient_records,
    merge_current_patient_record,
    normalize_patient_record,
    patient_record_has_content,
    save_patient_records,
)
from app.settings_store import (
    find_settings_name_ttl,
    load_settings_json,
    resolve_settings_path,
    save_settings_json,
)

# Ayar dosyası için mutlak yol (servis hangi dizinden başlatılırsa başlatılsın çalışır)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = str(resolve_settings_path(SCRIPT_DIR))
PATIENTS_DIR = os.path.join(SCRIPT_DIR, "data")
PATIENTS_FILE = os.path.join(PATIENTS_DIR, "patients.json")
UDHCPC_SCRIPT = os.path.join(SCRIPT_DIR, "scripts", "udhcpc_default.sh")
DOCS_DIR = os.path.join(SCRIPT_DIR, "docs")
PUBLIC_HELP_DOCS = [
    ("KUVOZ_KULLANIM_KLAVUZU.md", "Kullanim Kilavuzu"),
    ("SETTINGS_AND_PROFILE.md", "Ayarlar ve Profil"),
    ("AI_INTEGRATION.md", "Yapay Zeka Ozeti"),
    ("AI_ALERTS.md", "Akilli Uyari Rehberi"),
    ("AI_DYNAMIC_VITAL_THRESHOLDS.md", "Akilli Esik Ayarlari"),
    ("KVKK_AYDINLATMA_VE_ACIK_RIZA_METNI.md", "KVKK Aydinlatma ve Acik Riza"),
]

# Firebase integration disabled in current release.
# Keep FirebaseManager code in repository for next version re-enable.
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

# DHT sensor library - fallback path only when SCD41 is unavailable
sys.path.append("lib/")
try:
    from DHT_Native import read_retry, read
    DHT_AVAILABLE = True
    DHT_LIBRARY = "DHT_Native"
    print("✅ DHT_Native library loaded (fallback climate sensor path)")
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

# CO2 sensor library - SCD41 only
CO2_SENSOR_TYPE = None  # Will be detected: 'SCD41' or None
CO2_AVAILABLE = False

try:
    from lib.SCD41_Sensor import SCD41Sensor, SCD41_AVAILABLE
    if SCD41_AVAILABLE:
        CO2_AVAILABLE = True
        CO2_SENSOR_TYPE = 'SCD41'
        print("✅ SCD41 sensor library loaded")
    else:
        raise ImportError("SCD41 library imported but not available")
except ImportError:
    print("⚠️  SCD41 sensor not available")
    print("   Install: pip3 install --break-system-packages adafruit-circuitpython-scd4x")
    print("   Or use: make deps-scd41")
    CO2_AVAILABLE = False
    CO2_SENSOR_TYPE = None

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

try:
    from lib.data.ai_vitals_logger import AIVitalsLogger
    AI_VITAL_LOGGING_AVAILABLE = True
    print("AI Vitals Logger loaded")
except ImportError as e:
    print(f"AI Vitals Logger not available: {e}")
    AI_VITAL_LOGGING_AVAILABLE = False
    AIVitalsLogger = None

try:
    from lib.data.behavior_logger import BehaviorLogger
    BEHAVIOR_LOGGING_AVAILABLE = True
    print("Behavior Logger loaded")
except ImportError as e:
    print(f"Behavior Logger not available: {e}")
    BEHAVIOR_LOGGING_AVAILABLE = False
    BehaviorLogger = None

try:
    from lib.data.ai_behavior_mapper import AIBehaviorMapper
    AI_BEHAVIOR_MAPPING_AVAILABLE = True
    print("AI Behavior Mapper loaded")
except ImportError as e:
    print(f"AI Behavior Mapper not available: {e}")
    AI_BEHAVIOR_MAPPING_AVAILABLE = False
    AIBehaviorMapper = None

# Flask app setup
app = Flask(__name__, static_folder='web', static_url_path='')
app.config['SECRET_KEY'] = 'kuvoz_secret_key_2025'
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   async_mode='threading',       # Explicit threading mode
                   max_http_buffer_size=1000000,  # 1MB
                   ping_timeout=60,              # Engine.IO expects seconds, not milliseconds
                   ping_interval=25)             # Keep stale client sessions from lingering for hours

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def _env_flag(name, default='0'):
    value = os.getenv(name, default)
    return str(value).strip().lower() not in ('0', 'false', 'no', 'off', '')

def _env_int(name, default):
    try:
        return int(os.getenv(name, str(default)).strip())
    except (TypeError, ValueError, AttributeError):
        return default

def _clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))

POWER_DIAGNOSTIC_INTERVAL_SEC = int(os.getenv('KUVOZ_POWER_DIAG_INTERVAL_SEC', '60'))
POWER_DIAGNOSTIC_HEALTHY_LOG_SEC = int(os.getenv('KUVOZ_POWER_DIAG_HEALTHY_LOG_SEC', '1800'))
POWER_DIAGNOSTIC_WARN_LOG_SEC = int(os.getenv('KUVOZ_POWER_DIAG_WARN_LOG_SEC', '300'))
KIOSK_WATCHDOG_ENABLED = os.getenv('KUVOZ_KIOSK_WATCHDOG_ENABLED', '1').strip().lower() not in ('0', 'false', 'no')
KIOSK_WATCHDOG_INTERVAL_SEC = int(os.getenv('KUVOZ_KIOSK_WATCHDOG_INTERVAL_SEC', '30'))
KIOSK_WATCHDOG_TIMEOUT_SEC = int(os.getenv('KUVOZ_KIOSK_WATCHDOG_TIMEOUT_SEC', '120'))
KIOSK_WATCHDOG_COOLDOWN_SEC = int(os.getenv('KUVOZ_KIOSK_WATCHDOG_COOLDOWN_SEC', '900'))
FAN_PWM_REQUESTED = _env_flag('KUVOZ_FAN_PWM_ENABLED', '0')
FAN_PWM_PIN = _env_int('KUVOZ_FAN_PWM_PIN', 18)
FAN_PWM_FREQUENCY = _env_int('KUVOZ_FAN_PWM_FREQ', 25000)
FAN_PWM_HEATER_MIN_DUTY = _clamp(float(_env_int('KUVOZ_FAN_PWM_HEATER_MIN_DUTY', 35)), 20.0, 100.0)
DEFAULT_FAN_OUTPUT_MODE = 'pwm' if FAN_PWM_REQUESTED else 'relay'
LOCAL_KIOSK_IPS = {'127.0.0.1', '::1', 'localhost'}

POWER_THROTTLED_FLAGS = {
    0: 'under_voltage_now',
    1: 'arm_freq_capped_now',
    2: 'throttled_now',
    3: 'soft_temp_limit_now',
    16: 'under_voltage_occurred',
    17: 'arm_freq_capped_occurred',
    18: 'throttled_occurred',
    19: 'soft_temp_limit_occurred',
}

# Global görev yöneticisi örneği
task_manager = BackgroundTaskManager(logger=logger)

# Startup bilgileri
logger.info("🚀 Kuvoz Web Server initializing...")
logger.info(f"📊 DHT Library: {DHT_LIBRARY} (Adafruit_DHT disabled)")
logger.info(f"🔋 GPIO Available: {GPIO_AVAILABLE}")
logger.info(f"🌡️  DHT Library Available: {DHT_AVAILABLE}")
logger.info(f"💨 Oxygen Library Available: {OXYGEN_AVAILABLE}")
logger.info(f"🌫️  CO2 Sensor Library: {CO2_SENSOR_TYPE if CO2_AVAILABLE else 'Not Available'}")
if DHT_AVAILABLE:
    logger.info("🎯 DHT11 Pin 22: Real sensor readings enabled (NO simulation)")

def _get_help_docs_index():
    docs = []
    if not os.path.isdir(DOCS_DIR):
        return docs
    for filename, title in PUBLIC_HELP_DOCS:
        if not filename.lower().endswith(".md"):
            continue
        full_path = os.path.join(DOCS_DIR, filename)
        if not os.path.isfile(full_path):
            continue
        docs.append({
            "id": filename,
            "title": title,
            "filename": filename
        })
    return docs

class KuvozServer:
    def _detect_dht_sensor_type(self):
        """
        Detect DHT sensor type from command line or environment variable.
        Priority: 1) Command line arg, 2) Environment variable, 3) Fallback DHT22

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
                    logger.warning(f"⚠️  Invalid DHT_SENSOR_TYPE={env_sensor_type}, using fallback DHT22")
            except ValueError:
                logger.warning(f"⚠️  Invalid DHT_SENSOR_TYPE={env_sensor_type}, using fallback DHT22")

        # 3. Fallback default: DHT22
        logger.info("🌡️  Using fallback DHT22 sensor (primary climate sensor is SCD41 when available)")
        return 22

    def preload_boot_system_settings(self):
        """Load persisted system settings needed before hardware init runs."""
        if not os.path.exists(SETTINGS_FILE):
            return

        try:
            with open(SETTINGS_FILE, "r") as f:
                file_content = f.read().strip()
        except OSError as e:
            logger.debug(f"Boot settings preload skipped: {e}")
            return

        if not file_content or not file_content.startswith("{"):
            return

        try:
            data = json.loads(file_content)
        except json.JSONDecodeError as e:
            logger.debug(f"Boot settings preload skipped: {e}")
            return

        boot_settings = data.get("system_settings")
        if not isinstance(boot_settings, dict):
            return

        for key in list(self.system_settings.keys()):
            if key in boot_settings:
                self.system_settings[key] = boot_settings[key]

        self.system_settings.pop('soothing_audio_enabled', None)
        self.system_settings.pop('soothing_audio_mode', None)
        self.system_settings['fan_output_mode'] = self.normalize_fan_output_mode(
            self.system_settings.get('fan_output_mode')
        )

    def is_oxygen_feature_enabled(self):
        return self.system_settings.get('oxygen_enabled', True) is not False

    def get_primary_climate_sensor_name(self):
        if self.co2_sensor_available and self.co2_sensor and self.co2_sensor_type == 'SCD41':
            return 'SCD41'
        if DHT_AVAILABLE:
            return f'DHT{self.sensorDht}'
        return 'None'

    def get_climate_sensor_strategy(self):
        return {
            'primary': 'SCD41',
            'fallback': f'DHT{self.sensorDht}',
            'oxygen_mode': 'optional',
        }

    def apply_runtime_sensor_settings(self):
        """Apply sensor-related feature flags immediately after settings changes."""
        if not self.is_oxygen_feature_enabled():
            self.sensor_data.pop('oxygen', None)
            if self.ai_manager and hasattr(self.ai_manager, 'clear_sensor_history'):
                self.ai_manager.clear_sensor_history('oxygen')
            return

        if self.oxygen_sensor is None and not self.oxygen_sensor_available and OXYGEN_AVAILABLE:
            try:
                sensor, address, test_reading, probe_errors = self.probe_oxygen_sensor(sample_count=5)
                if sensor is not None:
                    self.oxygen_sensor = sensor
                    self.oxygen_sensor_address = address
                    self.oxygen_sensor_available = True
                    logger.info(
                        f"âœ… Oxygen sensor enabled from settings at I2C 0x{address:02X}: {test_reading:.1f}%"
                    )
                elif probe_errors:
                    attempted = ", ".join(probe_errors.keys()) or "none"
                    logger.warning(f"âš ï¸  Oxygen sensor probe failed after enabling setting: {attempted}")
            except Exception as e:
                logger.error(f"âŒ Oxygen sensor probe error after enabling setting: {e}")

        if self.oxygen_sensor_available and 'oxygen' not in self.sensor_data:
            self.sensor_data['oxygen'] = {'value': '--', 'status': 'Initializing...'}

    def __init__(self):
        # GPIO konfigürasyonu
        self.outChannels = list(OUTPUT_CHANNELS)
        self.touch_bt = list(TOUCH_BUTTON_PINS)
        self.pinDht = DEFAULT_DHT_PIN
        self.pinWps = DEFAULT_WPS_PIN

        # DHT sensor type - only used for fallback climate sensing
        # Priority: 1) Command line arg, 2) Environment variable, 3) Fallback DHT22
        self.sensorDht = self._detect_dht_sensor_type()

        # Durum değişkenleri
        self.sensor_data = {
            'temperature': {'value': '--', 'status': 'Initializing...'},
            'humidity': {'value': '--', 'status': 'Initializing...'}
        }
        # Oksijen sensörü başlangıçta eklenmez - init_hardware'dan sonra eklenecek
        # CO2 sensörü (SCD41) de init_hardware'dan sonra eklenecek
        
        self.button_states = {f'b{i+1}': False for i in range(9)}  # b1-b8 + b9 (cooling)
        self.gpio_output_states = {f'b{i+1}': None for i in range(9)}  # GPIO output states (True=LOW, False=HIGH, None=unknown)
        self.slider_values = {
            'sld1': 30,  # Nebulizer interval
            'sld2': 65,  # Humidity target
            'sld3': 25.0,  # Temperature target (heating)
            'sld4': 25.0,  # IR Temperature target
            'sld5': 30,  # Ozone interval
            'sld6': 12,  # Nebulizer hours interval
            'sld7': 8.0,   # Ozone hours interval
            # Duty/Free Time Settings
            'sld8': 5,   # Nebulizer duty time (min)
            'sld9': 25,  # Nebulizer free time (min)
            'sld10': 3,  # Ozone duty time (min)
            'sld11': 60,  # Ozone free time (min)
            # Cooling system (optional feature - slider optional, works as manual ON/OFF too)
            'sld12': 25.0,  # Cooling target temperature (°C) - set to 0 for manual mode
            'sld13': 100  # Legacy fan speed slot kept for UI compatibility
        }

        # Optional PWM fan control. Relay/PWM path is selected from system settings.
        self.fan_pwm_requested = FAN_PWM_REQUESTED
        self.fan_pwm_pin = FAN_PWM_PIN
        self.fan_pwm_frequency = FAN_PWM_FREQUENCY
        self.fan_pwm_heater_min_duty = FAN_PWM_HEATER_MIN_DUTY
        self.fan_pwm = None
        self.fan_pwm_available = False
        self.fan_pwm_duty = 0.0
        self.fan_pwm_lock = threading.Lock()
        self.state_lock = threading.RLock()
        self.connection_lock = threading.RLock()
        self.fan_auto_active = False
        self.output_controller = GPIOController(
            gpio=GPIO,
            gpio_available_getter=lambda: GPIO_AVAILABLE,
            check_gpio_status=self.check_gpio_status,
            logger=logger,
            button_states=self.button_states,
            gpio_output_states=self.gpio_output_states,
            get_fan_speed_percent=self.get_fan_speed_percent,
            initialize_fan_pwm=self.initialize_fan_pwm,
            stop_fan_pwm=self.stop_fan_pwm,
            is_fan_pwm_mode=self.is_fan_pwm_mode,
            fan_pwm_lock=self.fan_pwm_lock,
            fan_pwm_pin_getter=lambda: self.fan_pwm_pin,
            fan_pwm_getter=lambda: self.fan_pwm,
            fan_pwm_setter=lambda value: setattr(self, 'fan_pwm', value),
            fan_pwm_available_getter=lambda: self.fan_pwm_available,
            fan_pwm_available_setter=lambda value: setattr(self, 'fan_pwm_available', value),
            fan_pwm_duty_getter=lambda: self.fan_pwm_duty,
            fan_pwm_duty_setter=lambda value: setattr(self, 'fan_pwm_duty', value),
            get_fan_output_mode=self.get_fan_output_mode,
            set_fan_output_mode=lambda value: self.system_settings.__setitem__('fan_output_mode', value),
            state_lock=self.state_lock,
        )

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
        self.ai_thread = None
        self.ai_lifecycle_lock = threading.RLock()
        self.ai_runtime_state = 'stopped'
        self.ai_runtime_last_change_ts = 0.0
        self.ai_runtime_last_error = None

        # System Settings (features can be toggled)
        self.system_settings = {
            'cooling_enabled': False,
            'dht_enabled': True,
            'oxygen_enabled': True,
            'co2_enabled': True,
            'ai_enabled': False,
            'logging_enabled': True,
            'fan_output_mode': DEFAULT_FAN_OUTPUT_MODE,
            'screen_orientation': 'auto'
        }
        self.preload_boot_system_settings()

        # User Profile Data
        self.user_profile = {
            'company': {
                'name': '',
                'address': '',
                'phone': '',
                'email': '',
                'tax_number': '',
                'website': ''
            },
            'contact': {
                'name': '',
                'title': '',
                'mobile': '',
                'email': ''
            },
            'device': {
                'name': 'Kuvoz Cihazı',
                'ip': '',
                'last_update': ''
            }
        }
        self.patient_context = {
            'name': '',
            'species': '',
            'breed': '',
            'age': '',
            'weight': ''
        }
        self.current_patient = {}
        self.care_settings = {
            'mode': 'manual'  # manual | auto
        }

        # Hysteresis settings (prevent relay chattering)
        self.TEMP_HYSTERESIS = 0.5  # °C - prevents heating on/off cycling
        self.HUM_HYSTERESIS = 2.0   # % - prevents humidifier on/off cycling
        self.COOLING_HYSTERESIS = 0.5  # °C - prevents cooling on/off cycling
        
        # SAFETY: Cooling target temperature limits (°C)
        self.COOLING_TARGET_MIN = 15.0   # Minimum cooling target
        self.COOLING_TARGET_MAX = 35.0   # Maximum cooling target (danger zone above this)
        
        # SAFETY: Critical temperature thresholds for alarms (°C)
        self.TEMP_CRITICAL_HIGH = 40.0   # Critical high temperature - life danger
        self.TEMP_WARNING_HIGH = 38.0    # Warning high temperature
        self.TEMP_CRITICAL_LOW = 10.0    # Critical low temperature - life danger
        self.TEMP_WARNING_LOW = 15.0     # Warning low temperature
        
        # Alarm state tracking
        self.last_alarm_time = 0
        self.alarm_cooldown = 300  # 5 minutes between repeated alarms
        self.critical_alarm_active = False
        self.HUMIDITY_PURGE_ON_DELTA = 4.0   # % - excess humidity required to start ventilation purge
        self.HUMIDITY_PURGE_OFF_DELTA = 1.0  # % - keep purging until nearly back at target
        self.humidity_purge_active = False
        
        # Duty cycle state tracking
        self.nebulizer_duty_start = 0
        self.nebulizer_in_duty = False
        self.ozone_duty_start = 0
        self.ozone_in_duty = False
        
        # Aktif bağlantılar tracking
        self.active_connections = {}  # {sid: {'ip': '...', 'connected_at': timestamp, 'last_seen': timestamp}}

        # Local kiosk watchdog state
        self.local_kiosk_seen_once = False
        self.local_kiosk_last_event_ts = 0.0
        self.local_kiosk_last_event_type = None
        self.local_kiosk_last_connect_ts = 0.0
        self.local_kiosk_last_disconnect_ts = 0.0
        self.local_kiosk_last_origin = None
        self.kiosk_watchdog_last_restart_ts = 0.0
        
        # Threading
        self.sensor_thread = None
        self.control_thread = None
        self.wps_thread = None
        self.power_diag_thread = None
        self.kiosk_watchdog_thread = None
        self.running = False
        self.settings_save_lock = threading.Lock()
        self.settings_save_timer = None
        self.settings_save_delay_sec = 1.0

        # Power diagnostics
        self.last_power_diag = None
        self.last_power_diag_mask = None
        self.last_power_diag_log_ts = 0.0
        self.power_diag_available = shutil.which('vcgencmd') is not None
        self.kiosk_watchdog_available = (
            KIOSK_WATCHDOG_ENABLED and
            sys.platform.startswith('linux') and
            shutil.which('systemctl') is not None
        )
        
        # Firebase Integration (optional)
        self.firebase_manager = None
        if FIREBASE_AVAILABLE:
            try:
                self.firebase_manager = FirebaseManager(device_name=self.user_profile['device'].get('name', 'Kuvoz'))
                self.firebase_manager.register_device(version='3.0-embedded')
                self.firebase_manager.listen_for_commands(self.handle_firebase_control)
                # Sync current state
                if hasattr(self, 'button_states') and hasattr(self, 'slider_values'):
                    self.firebase_manager.sync_controls(self.button_states, self.slider_values)
                logger.info("✅ Firebase initialized and state synced")
            except Exception as e:
                logger.error(f"⚠️  Firebase connection failed: {e}")
                self.firebase_manager = None
        
        # Oxygen sensor
        self.oxygen_sensor = None
        self.oxygen_sensor_available = False
        self.oxygen_sensor_address = None
        
        # DHT bit-shift anomaly filter - tracks last valid readings
        self.last_valid_temp = None
        self.last_valid_humidity = None
        
        # DHT fallback quality filter - moving average for noisy readings
        self.temp_readings = []  # Son N okuma
        self.humidity_readings = []  # Son N okuma
        self.moving_avg_window = 3  # 3 okuma ortalaması (~45 saniye)

        # CO2 sensor (SCD41)
        self.co2_sensor = None
        self.co2_sensor_available = False
        self.co2_sensor_type = None
        self._co2_warmup_reads = 0
        self._co2_startup_blend_reads = 6
        self._startup_sensor_baseline = {}
        
        # AI Manager (initialized but not started by default)
        self.ai_manager = None
        if AI_AVAILABLE:
            try:
                self.ai_manager = AIManager()
                self.ai_manager.set_patient_context(self.patient_context)
                self.ai_runtime_state = 'stopped'
                logger.info("AI Manager initialized (not started - toggle from UI)")
            except Exception as e:
                logger.error(f"Failed to initialize AI Manager: {e}")
                self.ai_manager = None
                self.ai_runtime_state = 'unavailable'
        
        # Sensor Data Logger
        self.sensor_logger = None
        # Sensor Data Logger
        self.sensor_logger = None
        if LOGGING_AVAILABLE:
            self.sensor_logger = SensorLogger(db_path="data/sensor_logs.db", min_interval=60)

        self.ai_vitals_logger = None
        if AI_VITAL_LOGGING_AVAILABLE:
            # AGRESİF AI VITAL LOGGER - Sadece önemli değişiklikleri kaydet
            # min_interval: 30 saniye (önceki: 10s) - Minimum kayıt aralığı
            # heartbeat_interval: 180 saniye (önceki: 60s) - Her 3 dakikada bir heartbeat
            # Bu sayede gereksiz kayıtlar azalır, sadece anlamlı değişiklikler kaydedilir
            self.ai_vitals_logger = AIVitalsLogger(
                db_path="data/ai_vitals.db",
                min_interval=30,  # AGRESİF: Minimum 30 saniye
                heartbeat_interval=180,  # AGRESİF: Her 3 dakikada bir (sadece stabil durumlarda)
            )

        self.behavior_logger = None
        if BEHAVIOR_LOGGING_AVAILABLE:
            self.behavior_logger = BehaviorLogger(
                db_path="data/behavior_logs.db",
                min_interval=60,
            )

        self.ai_behavior_mapper = None
        if AI_BEHAVIOR_MAPPING_AVAILABLE:
            self.ai_behavior_mapper = AIBehaviorMapper(heartbeat_interval=300)
        
        self.init_hardware()
        self.restore_last_sensor_snapshot()
        self.load_settings()
        self.apply_runtime_sensor_settings()
        
        # Start AI if it was enabled in saved settings
        if self.ai_enabled:
            started, message, health = self._set_ai_runtime_enabled(True, source='startup')
            if started:
                logger.info("🤖 AI Manager auto-started (user preference from settings)")
            else:
                logger.warning("⚠️ AI auto-start skipped because the camera could not be initialized")
                logger.debug("🤖 AI startup result: %s / %s", message, health)

        logger.info(
            "🔌 Power diagnostics: %s (interval=%ss, healthy_log=%ss, warn_log=%ss)",
            "enabled" if self.power_diag_available else "vcgencmd unavailable",
            POWER_DIAGNOSTIC_INTERVAL_SEC,
            POWER_DIAGNOSTIC_HEALTHY_LOG_SEC,
            POWER_DIAGNOSTIC_WARN_LOG_SEC,
        )
        logger.info(
            "🖥️ Kiosk watchdog: %s (timeout=%ss, cooldown=%ss)",
            "enabled" if self.kiosk_watchdog_available else "disabled",
            KIOSK_WATCHDOG_TIMEOUT_SEC,
            KIOSK_WATCHDOG_COOLDOWN_SEC,
        )

    def snapshot_runtime_state(self):
        """Return a deep-copied snapshot of mutable runtime state."""
        with self.state_lock:
            return {
                'sensor_data': copy.deepcopy(self.sensor_data),
                'button_states': copy.deepcopy(self.button_states),
                'gpio_output_states': copy.deepcopy(self.gpio_output_states),
                'slider_values': copy.deepcopy(self.slider_values),
                'system_settings': copy.deepcopy(self.system_settings),
                'care_settings': copy.deepcopy(self.care_settings),
            }

    def build_status_payload(self, *, ai_available, include_disinfection=False):
        snapshot = self.snapshot_runtime_state()
        payload = {
            'type': 'status_response',
            'sensors': snapshot['sensor_data'],
            'buttons': snapshot['button_states'],
            'gpio_outputs': snapshot['gpio_output_states'],
            'sliders': self.get_effective_slider_values(),
            'timers': self.get_timer_data(),
            'system': self.get_effective_system_status(),
            'ai_available': ai_available,
            'ai_enabled': self.ai_enabled,
            'ai_health': self.get_ai_health_status(),
            'system_settings': snapshot['system_settings'],
            'care_settings': self.get_care_status(),
        }
        if include_disinfection:
            payload['disinfection_mode'] = self.disinfection_mode
        return payload

    def register_active_connection(self, sid, ip, current_time=None):
        if current_time is None:
            current_time = time.time()
        with self.connection_lock:
            self.active_connections[sid] = {
                'ip': ip,
                'connected_at': current_time,
                'last_seen': current_time,
            }

    def touch_active_connection(self, sid, current_time=None):
        if current_time is None:
            current_time = time.time()
        with self.connection_lock:
            connection = self.active_connections.get(sid)
            if connection is None:
                return False
            connection['last_seen'] = current_time
            return True

    def pop_active_connection(self, sid, current_time=None):
        if current_time is None:
            current_time = time.time()
        with self.connection_lock:
            connection = self.active_connections.pop(sid, None)
        if connection is None:
            return None
        return {
            'ip': connection.get('ip'),
            'connected_at': connection.get('connected_at', current_time),
            'last_seen': connection.get('last_seen', current_time),
            'duration': int(current_time - connection.get('connected_at', current_time)),
        }

    def get_active_connections_payload(self, current_time=None):
        if current_time is None:
            current_time = time.time()
        with self.connection_lock:
            connections = [
                {
                    'ip': conn['ip'],
                    'connected_at': conn['connected_at'],
                    'duration': int(current_time - conn['connected_at']),
                }
                for conn in self.active_connections.values()
            ]
        return {'connections': connections}
    
    def handle_firebase_control(self, path, value):
        """Handle control updates from Firebase"""
        logger.info(f"Firebase Control: {path} = {value}")
        
        # Path examples: "/controls/b1", "/settings/sld1", "/b1" (depending on how we structure)
        # Assuming path is relative to controls root, e.g. "/b1"
        
        key = path.strip('/')
        
        if key in self.button_states:
            # Button update
            state = bool(value)
            with self.state_lock:
                self.button_states[key] = state
            
            # Update Hardware
            # Pin değişiklikleri: b6 (Fan) PWM GPIO18, b9 (Cooling) GPIO20
            pin_map = {
                'b1': 5, 'b2': 6, 'b3': 13, 'b4': 16,
                'b5': 19, 'b6': 18, 'b7': 21, 'b8': 26,  # b6 artık PWM GPIO18
                'b9': 20   # Cooling GPIO20'ye taşındı
            }
            if key in pin_map:
                pin = pin_map[key]
                gpio_val = GPIO.LOW if state else GPIO.HIGH
                self.safe_gpio_output(pin, gpio_val)
                
            # Sync to local Web UI
            snapshot = self.snapshot_runtime_state()
            socketio.emit('button_update', {
                'id': key,
                'status': state,
                'buttons': snapshot['button_states'],
                'gpio_outputs': snapshot['gpio_output_states'],
            })
            
        elif key in self.slider_values:
            # Slider update
            try:
                val = float(value)
                with self.state_lock:
                    self.slider_values[key] = val
                # Sync to all local clients
                snapshot = self.snapshot_runtime_state()
                socketio.emit('slider_update', {'id': key, 'value': val, 'sliders': snapshot['slider_values']})

                # Sync to Firebase
                if self.firebase_manager:
                    self.firebase_manager.update_slider_value(key, val)
            except ValueError:
                pass

    def get_system_status(self):
        """Return backend capability flags for frontend consumption."""
        # Oksijen verisi var mı? (Gerçek sensör VEYA CO2'den tahmin)
        has_oxygen_data = 'oxygen' in self.sensor_data and self.sensor_data['oxygen']['value'] != '--'
        
        # CO2 verisi var mı? (SCD41'den gerçek okuma)
        has_co2_data = 'co2' in self.sensor_data and self.sensor_data['co2']['value'] != '--'
        
        strategy = self.get_climate_sensor_strategy()
        return {
            'dht_library': DHT_LIBRARY,
            'gpio_available': True,  # Always true - simulation mode works too
            'dht_available': DHT_AVAILABLE,
            'oxygen_available': has_oxygen_data,  # Gerçek sensör VEYA tahmini
            'oxygen_sensor_available': self.oxygen_sensor_available,
            'oxygen_estimated': has_oxygen_data and not self.oxygen_sensor_available,
            'co2_available': has_co2_data,  # SCD41'den gerçek okuma varsa
            'co2_sensor_available': self.co2_sensor_available,
            'primary_climate_sensor': self.get_primary_climate_sensor_name(),
            'climate_sensor_primary_expected': strategy['primary'],
            'climate_sensor_fallback': strategy['fallback'],
            'oxygen_sensor_mode': strategy['oxygen_mode'],
            'fan_output_mode': self.get_fan_output_mode(),
            'fan_pwm_available': self.fan_pwm_available,
            'fan_pwm_requested': self.is_fan_pwm_mode(),
            'fan_pwm_pin': self.fan_pwm_pin if self.fan_pwm_available else None,
            'fan_pwm_frequency': self.fan_pwm_frequency if self.fan_pwm_available else None,
            'fan_pwm_duty': self.fan_pwm_duty if self.fan_pwm_available else None,
            'dht_pin': self.pinDht,
            'dht_sensor': f"DHT{self.sensorDht}",
            'network_ip': get_local_ip(),
            'port': 8000
        }

    def get_effective_system_status(self):
        system_status = self.get_system_status()
        if not self.is_oxygen_feature_enabled():
            system_status['oxygen_available'] = False
            system_status['oxygen_estimated'] = False
        return system_status

    def get_ai_logging_patient_context(self):
        """Return the most useful patient snapshot for AI vital logging."""
        patient = normalize_patient_record(self.current_patient)
        if not patient:
            patient = normalize_patient_record(self.patient_context)
        return patient

    def _emit_behavior_update(self, behavior_entry):
        if not isinstance(behavior_entry, dict):
            return
        try:
            socketio.emit('behavior_update', behavior_entry)
        except Exception as exc:
            logger.debug(f"Behavior update emit failed: {exc}")

    def _log_ai_behavior_if_needed(self, ai_data):
        if (
            not self.behavior_logger
            or not self.ai_behavior_mapper
            or not self.system_settings.get('logging_enabled', True)
            or not isinstance(ai_data, dict)
        ):
            return False

        patient_context = self.get_ai_logging_patient_context()
        behavior_event = self.ai_behavior_mapper.consume(
            ai_data,
            patient_context=patient_context,
        )
        if not behavior_event:
            return False

        logged = self.behavior_logger.log_behavior(
            behavior_event['behavior_type'],
            patient_context=patient_context,
            duration=behavior_event.get('duration'),
            intensity=behavior_event.get('intensity'),
            notes=behavior_event.get('notes'),
            metadata=behavior_event.get('metadata'),
            behavior_subtype=behavior_event.get('behavior_subtype'),
        )
        if not logged:
            return False

        latest_behavior = self.behavior_logger.get_latest_behavior(
            behavior_type=behavior_event['behavior_type'],
            patient_id=patient_context.get('id') if patient_context else None,
        )
        if latest_behavior:
            self._emit_behavior_update(latest_behavior)
        logger.info("Behavior logged from AI: %s", behavior_event['behavior_type'])
        return True

    def get_ai_health_status(self):
        """Return a compact AI runtime health snapshot for UI and logs."""
        manager = self.ai_manager
        vision = getattr(manager, 'vision', None) if manager else None
        vision_status = {}
        lifecycle_status = {}

        if vision and hasattr(vision, 'get_status'):
            try:
                vision_status = vision.get_status() or {}
            except Exception as exc:
                logger.debug(f"AI health vision status read failed: {exc}")

        latest_vitals = {}
        if vision and hasattr(vision, 'get_vitals'):
            try:
                latest_vitals = vision.get_vitals() or {}
            except Exception as exc:
                logger.debug(f"AI health vitals read failed: {exc}")

        if manager and hasattr(manager, 'get_lifecycle_status'):
            try:
                lifecycle_status = manager.get_lifecycle_status() or {}
            except Exception as exc:
                logger.debug(f"AI health lifecycle read failed: {exc}")

        manager_state = lifecycle_status.get('state')
        manager_started = bool(lifecycle_status.get('started', getattr(manager, 'started', False)))
        manager_running = bool(lifecycle_status.get('running', getattr(manager, 'running', False)))
        thread_alive = bool(self.ai_thread and self.ai_thread.is_alive())
        manager_last_error = lifecycle_status.get('last_error')

        if not manager:
            health = 'unavailable'
            state = 'unavailable'
        elif manager_state == 'FAILED':
            health = 'degraded'
            state = 'failed'
        elif manager_started and vision_status.get('available', False):
            health = 'healthy'
            state = self.ai_runtime_state if self.ai_runtime_state != 'stopped' else 'running'
        elif self.ai_enabled:
            health = 'degraded'
            state = manager_state.lower() if manager_state else self.ai_runtime_state
        else:
            health = 'idle'
            state = self.ai_runtime_state if self.ai_runtime_state != 'unavailable' else 'stopped'

        return {
            'available': bool(AI_AVAILABLE and manager is not None),
            'enabled': bool(self.ai_enabled),
            'state': state,
            'health': health,
            'manager_started': manager_started,
            'manager_running': manager_running,
            'thread_alive': thread_alive,
            'vision_running': bool(getattr(vision, 'running', False)),
            'vision_available': bool(vision_status.get('available', False)),
            'camera_type': getattr(vision, 'camera_type', None),
            'activity': vision_status.get('activity'),
            'respiration_signal': vision_status.get('respiration_signal'),
            'target_fps': vision_status.get('target_fps'),
            'load_profile': vision_status.get('load_profile'),
            'load_reason': vision_status.get('load_reason'),
            'analysis_focus_source': vision_status.get('analysis_focus_source'),
            'analysis_focus_coverage': vision_status.get('analysis_focus_coverage'),
            'analysis_focus_box': vision_status.get('analysis_focus_box'),
            'subject_tracking_state': vision_status.get('subject_tracking_state'),
            'subject_tracking_confidence': vision_status.get('subject_tracking_confidence'),
            'subject_tracking_locked': vision_status.get('subject_tracking_locked'),
            'startup_collection_active': vision_status.get('startup_collection_active'),
            'vital_status': latest_vitals.get('status'),
            'respiration_bpm': latest_vitals.get('respiration_bpm'),
            'vital_confidence': latest_vitals.get('confidence'),
            'vital_method': latest_vitals.get('method'),
            'last_error': manager_last_error or self.ai_runtime_last_error,
            'last_transition_ts': self.ai_runtime_last_change_ts,
            'manager_lifecycle': lifecycle_status,
        }

    def _set_ai_runtime_enabled(self, enabled, source='unknown'):
        """Centralized AI lifecycle transition helper."""
        desired_enabled = bool(enabled)

        with self.ai_lifecycle_lock:
            if not AI_AVAILABLE or not self.ai_manager:
                self.ai_enabled = False
                self.ai_runtime_state = 'unavailable'
                self.ai_runtime_last_error = 'AI module unavailable'
                self.ai_runtime_last_change_ts = time.time()
                health = self.get_ai_health_status()
                logger.warning("🤖 AI lifecycle skipped (%s): module unavailable", source)
                return False, self.ai_runtime_last_error, health

            if desired_enabled:
                self.ai_enabled = True
                if getattr(self.ai_manager, 'started', False):
                    self.ai_runtime_state = 'running'
                    self.ai_runtime_last_error = None
                    self.ai_runtime_last_change_ts = time.time()
                    health = self.get_ai_health_status()
                    logger.info("🤖 AI lifecycle already running (%s)", source)
                    return True, 'AI zaten çalışıyor', health

                self.ai_runtime_state = 'starting'
                self.ai_runtime_last_error = None
                try:
                    started = self.ai_manager.start()
                except Exception as exc:
                    started = False
                    self.ai_runtime_last_error = str(exc)
                    logger.error("🤖 AI start exception (%s): %s", source, exc, exc_info=True)

                if started:
                    self.ai_runtime_state = 'running'
                    self.ai_runtime_last_error = None
                    self.ai_runtime_last_change_ts = time.time()
                    health = self.get_ai_health_status()
                    logger.info("🤖 AI lifecycle started (%s)", source)
                    return True, 'AI analizi başlatıldı', health

                self.ai_enabled = False
                self.ai_runtime_state = 'failed'
                if not self.ai_runtime_last_error:
                    self.ai_runtime_last_error = 'camera initialization failed'
                self.ai_runtime_last_change_ts = time.time()
                health = self.get_ai_health_status()
                logger.warning("⚠️ AI start failed (%s): %s", source, self.ai_runtime_last_error)
                return False, self.ai_runtime_last_error, health

            self.ai_enabled = False
            if not getattr(self.ai_manager, 'started', False):
                self.ai_runtime_state = 'stopped'
                self.ai_runtime_last_error = None
                self.ai_runtime_last_change_ts = time.time()
                health = self.get_ai_health_status()
                logger.info("🤖 AI lifecycle already stopped (%s)", source)
                return True, 'AI zaten durdurulmuş', health

            self.ai_runtime_state = 'stopping'
            try:
                self.ai_manager.stop()
            except Exception as exc:
                self.ai_runtime_state = 'failed'
                self.ai_runtime_last_error = str(exc)
                self.ai_runtime_last_change_ts = time.time()
                health = self.get_ai_health_status()
                logger.error("🤖 AI stop exception (%s): %s", source, exc, exc_info=True)
                return False, self.ai_runtime_last_error, health

            self.ai_runtime_state = 'stopped'
            self.ai_runtime_last_error = None
            self.ai_runtime_last_change_ts = time.time()
            health = self.get_ai_health_status()
            logger.info("🤖 AI lifecycle stopped (%s)", source)
            return True, 'AI analizi durduruldu', health

    def restore_last_sensor_snapshot(self, max_age_minutes=30):
        """Restore the latest logged sensor snapshot so restart warm-up does not cause visible jumps."""
        if not self.sensor_logger:
            return

        latest = self.sensor_logger.get_latest_reading()
        if not latest:
            return

        timestamp_raw = latest.get('timestamp')
        if not timestamp_raw:
            return

        try:
            timestamp = datetime.datetime.fromisoformat(str(timestamp_raw))
        except ValueError:
            return

        age_seconds = (datetime.datetime.now() - timestamp).total_seconds()
        if age_seconds > max_age_minutes * 60:
            logger.info(
                f"Skipping startup sensor restore because latest snapshot is too old ({int(age_seconds)}s)"
            )
            return

        restored = {}
        formats = {
            'temperature': "{:.1f}",
            'humidity': "{:.0f}",
            'oxygen': "{:.1f}",
            'co2': "{:.0f}",
        }

        for sensor_type, formatter in formats.items():
            if sensor_type == 'oxygen' and not self.is_oxygen_feature_enabled():
                continue
            value = latest.get(sensor_type)
            if value is None:
                continue
            numeric_value = float(value)
            restored[sensor_type] = numeric_value
            self.sensor_data[sensor_type] = {
                'value': formatter.format(numeric_value),
                'status': 'Startup hold'
            }

        if restored:
            self._startup_sensor_baseline = restored
            logger.info(
                f"Restored last sensor snapshot for startup stabilization ({int(age_seconds)}s old)"
            )

    def blend_startup_sensor_value(self, sensor_type, raw_value):
        """Blend the first SCD41 reads with the latest stable snapshot to avoid restart spikes."""
        baseline = self._startup_sensor_baseline.get(sensor_type)
        if baseline is None:
            return raw_value

        if self._co2_warmup_reads >= self._co2_startup_blend_reads:
            return raw_value

        ratio = min(1.0, (self._co2_warmup_reads + 1) / float(self._co2_startup_blend_reads))
        return baseline + ((raw_value - baseline) * ratio)
    
    def normalize_fan_output_mode(self, mode):
        """Normalize persisted/user-provided fan output mode."""
        return normalize_fan_output_mode(mode)

    def get_fan_output_mode(self):
        """Return the currently selected fan output mode."""
        return self.normalize_fan_output_mode(self.system_settings.get('fan_output_mode'))

    def is_fan_pwm_mode(self):
        """True when fan output should use the PWM/MOSFET path."""
        return self.get_fan_output_mode() == 'pwm'

    def refresh_fan_output_mode(self, reapply_current_output=True):
        """Apply selected fan output mode immediately."""
        self.output_controller.refresh_fan_output_mode(reapply_current_output=reapply_current_output)

    def _decode_power_throttled_mask(self, mask):
        active_flags = [
            flag_name for bit, flag_name in POWER_THROTTLED_FLAGS.items()
            if mask & (1 << bit)
        ]
        current_flags = [flag for flag in active_flags if flag.endswith('_now')]
        historical_flags = [flag for flag in active_flags if flag.endswith('_occurred')]
        return active_flags, current_flags, historical_flags

    def _collect_power_diagnostics(self):
        snapshot = {
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'available': self.power_diag_available,
            'raw': None,
            'mask': None,
            'active_flags': [],
            'current_flags': [],
            'historical_flags': [],
            'temperature_c': None,
            'error': None,
        }

        if not self.power_diag_available:
            snapshot['error'] = 'vcgencmd not found'
            return snapshot

        try:
            throttled_result = subprocess.run(
                ['vcgencmd', 'get_throttled'],
                capture_output=True,
                text=True,
                timeout=4,
            )
            raw = throttled_result.stdout.strip()
            snapshot['raw'] = raw

            if throttled_result.returncode != 0:
                snapshot['error'] = throttled_result.stderr.strip() or 'vcgencmd get_throttled failed'
                return snapshot

            if '=' not in raw:
                snapshot['error'] = f'unexpected get_throttled output: {raw}'
                return snapshot

            mask_str = raw.split('=', 1)[1].strip().lower()
            mask = int(mask_str, 16)
            snapshot['mask'] = mask
            active_flags, current_flags, historical_flags = self._decode_power_throttled_mask(mask)
            snapshot['active_flags'] = active_flags
            snapshot['current_flags'] = current_flags
            snapshot['historical_flags'] = historical_flags

            temp_result = subprocess.run(
                ['vcgencmd', 'measure_temp'],
                capture_output=True,
                text=True,
                timeout=4,
            )
            temp_raw = temp_result.stdout.strip()
            temp_match = re.search(r'temp=([0-9.]+)', temp_raw)
            if temp_match:
                snapshot['temperature_c'] = float(temp_match.group(1))

        except subprocess.TimeoutExpired:
            snapshot['error'] = 'vcgencmd timeout'
        except Exception as e:
            snapshot['error'] = str(e)

        return snapshot

    def _log_power_diagnostics_if_needed(self, snapshot, force=False):
        now = time.time()
        mask = snapshot.get('mask')
        raw = snapshot.get('raw') or 'n/a'
        current_flags = snapshot.get('current_flags') or []
        historical_flags = snapshot.get('historical_flags') or []
        temp_c = snapshot.get('temperature_c')
        temp_text = f", temp={temp_c:.1f}C" if isinstance(temp_c, (int, float)) else ""

        if snapshot.get('error'):
            if force or now - self.last_power_diag_log_ts >= POWER_DIAGNOSTIC_WARN_LOG_SEC:
                logger.warning(f"⚡ Power diagnostic unavailable: {snapshot['error']}")
                self.last_power_diag_log_ts = now
            return

        changed = mask != self.last_power_diag_mask

        if current_flags:
            if force or changed or now - self.last_power_diag_log_ts >= POWER_DIAGNOSTIC_WARN_LOG_SEC:
                logger.warning(
                    "⚡ Power issue detected: raw=%s current=%s history=%s%s",
                    raw,
                    current_flags,
                    historical_flags or ['none'],
                    temp_text,
                )
                self.last_power_diag_log_ts = now
        elif historical_flags:
            if force or changed or now - self.last_power_diag_log_ts >= POWER_DIAGNOSTIC_HEALTHY_LOG_SEC:
                logger.warning(
                    "⚠️ Power issue recorded since boot: raw=%s history=%s%s",
                    raw,
                    historical_flags,
                    temp_text,
                )
                self.last_power_diag_log_ts = now
        elif force or changed or now - self.last_power_diag_log_ts >= POWER_DIAGNOSTIC_HEALTHY_LOG_SEC:
            logger.info("🔌 Power diagnostic healthy: raw=%s%s", raw, temp_text)
            self.last_power_diag_log_ts = now

        self.last_power_diag_mask = mask

    def power_diagnostic_loop(self):
        logger.info("🔌 Power diagnostic loop started")
        while self.running:
            snapshot = self._collect_power_diagnostics()
            self.last_power_diag = snapshot
            self._log_power_diagnostics_if_needed(snapshot)
            time.sleep(POWER_DIAGNOSTIC_INTERVAL_SEC)

    def _is_local_kiosk_ip(self, ip):
        if not ip:
            return False
        normalized_ip = str(ip).strip().lower()
        if normalized_ip.startswith('::ffff:'):
            normalized_ip = normalized_ip.split('::ffff:', 1)[1]
        return normalized_ip in LOCAL_KIOSK_IPS

    def note_local_kiosk_connect(self, ip, sid=None):
        if not self._is_local_kiosk_ip(ip):
            return
        now = time.time()
        self.local_kiosk_seen_once = True
        self.local_kiosk_last_event_ts = now
        self.local_kiosk_last_event_type = 'websocket_connect'
        self.local_kiosk_last_connect_ts = now
        logger.info("🖥️ Local kiosk connected: sid=%s ip=%s", sid, ip)

    def note_local_kiosk_disconnect(self, ip, sid=None):
        if not self._is_local_kiosk_ip(ip):
            return
        self.local_kiosk_seen_once = True
        self.local_kiosk_last_disconnect_ts = time.time()
        logger.warning("🖥️ Local kiosk disconnected: sid=%s ip=%s", sid, ip)

    def note_local_kiosk_event(self, ip, event_type, payload=None, sid=None):
        if not self._is_local_kiosk_ip(ip):
            return
        now = time.time()
        self.local_kiosk_seen_once = True
        self.local_kiosk_last_event_ts = now
        self.local_kiosk_last_event_type = event_type
        if isinstance(payload, dict) and payload.get('origin'):
            self.local_kiosk_last_origin = payload.get('origin')
        if sid:
            self.touch_active_connection(sid, current_time=now)

    def restart_kiosk_service_from_watchdog(self, reason, stale_for):
        self.kiosk_watchdog_last_restart_ts = time.time()
        logger.warning(
            "🖥️ Kiosk watchdog restarting kuvoz-kiosk: reason=%s stale_for=%ss last_event=%s origin=%s",
            reason,
            int(stale_for),
            self.local_kiosk_last_event_type or 'unknown',
            self.local_kiosk_last_origin or '-',
        )
        try:
            result = subprocess.run(
                ['sudo', 'systemctl', 'restart', 'kuvoz-kiosk'],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                logger.warning("✅ Kiosk watchdog restart completed")
            else:
                logger.error(
                    "❌ Kiosk watchdog restart failed: %s",
                    result.stderr.strip() or result.stdout.strip() or 'unknown error',
                )
        except subprocess.TimeoutExpired:
            logger.error("❌ Kiosk watchdog restart timed out")
        except Exception as e:
            logger.error(f"❌ Kiosk watchdog restart exception: {e}")

    def kiosk_watchdog_loop(self):
        logger.info("🖥️ Kiosk watchdog loop started")
        while self.running:
            try:
                if not self.local_kiosk_seen_once or not self.local_kiosk_last_event_ts:
                    time.sleep(KIOSK_WATCHDOG_INTERVAL_SEC)
                    continue

                now = time.time()
                if now - self.kiosk_watchdog_last_restart_ts < KIOSK_WATCHDOG_COOLDOWN_SEC:
                    time.sleep(KIOSK_WATCHDOG_INTERVAL_SEC)
                    continue

                stale_for = now - self.local_kiosk_last_event_ts
                if stale_for < KIOSK_WATCHDOG_TIMEOUT_SEC:
                    time.sleep(KIOSK_WATCHDOG_INTERVAL_SEC)
                    continue

                service_active = False
                try:
                    status_result = subprocess.run(
                        ['systemctl', 'is-active', 'kuvoz-kiosk'],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    service_active = status_result.stdout.strip() == 'active'
                except Exception:
                    service_active = False

                reason = 'no_local_kiosk_events'
                if not service_active:
                    reason = 'kiosk_service_inactive'

                self.restart_kiosk_service_from_watchdog(reason, stale_for)
            except Exception as e:
                logger.error(f"Kiosk watchdog loop error: {e}")

            time.sleep(KIOSK_WATCHDOG_INTERVAL_SEC)

    def probe_oxygen_sensor(self, sample_count=5):
        """Probe common DFRobot oxygen sensor I2C addresses and return the first healthy sensor."""
        if not OXYGEN_AVAILABLE:
            return None, None, None, {}

        from DFRobot_Oxygen import (
            ADDRESS_0,
            ADDRESS_1,
            ADDRESS_2,
            ADDRESS_3,
            DFRobot_Oxygen_IIC,
            IIC_MODE,
        )

        candidate_addresses = (ADDRESS_3, ADDRESS_0, ADDRESS_1, ADDRESS_2)

        def oxygen_factory(address):
            return DFRobot_Oxygen_IIC(IIC_MODE, address)

        return probe_oxygen_sensor_helper(
            oxygen_library_available=OXYGEN_AVAILABLE,
            oxygen_factory=oxygen_factory,
            candidate_addresses=candidate_addresses,
            sample_count=sample_count,
        )

    def init_hardware(self):
        """GPIO ve sensörleri başlat"""
        global GPIO_AVAILABLE, OXYGEN_AVAILABLE
        oxygen_enabled = self.is_oxygen_feature_enabled()
        
        if GPIO_AVAILABLE:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                
                # Output pinlerini ayarla
                for pin in self.outChannels:
                    GPIO.setup(pin, GPIO.OUT)
                    GPIO.output(pin, GPIO.HIGH)  # Default OFF (active-low relays)
                    button_name = self.get_button_name_by_pin(pin)
                    if button_name:
                        self.gpio_output_states[button_name] = False
                # WPS Pull-up butonu ayarla
                GPIO.setup(self.pinWps, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                self.initialize_fan_pwm(force_recreate=True)
                
                logger.info("✅ GPIO initialized successfully")
            except Exception as e:
                logger.error(f"❌ GPIO init error: {e}")
                GPIO_AVAILABLE = False
        
        # Oxygen sensor - opsiyonel donanım
        if OXYGEN_AVAILABLE and oxygen_enabled:
            try:
                sensor, address, test_reading, probe_errors = self.probe_oxygen_sensor(sample_count=5)
                if sensor is not None:
                    self.oxygen_sensor = sensor
                    self.oxygen_sensor_address = address
                    self.oxygen_sensor_available = True
                    logger.info(
                        f"✅ Oxygen sensor initialized and tested at I2C 0x{address:02X}: {test_reading:.1f}%"
                    )
                else:
                    self.oxygen_sensor_available = False
                    self.oxygen_sensor = None
                    self.oxygen_sensor_address = None
                    attempted = ", ".join(probe_errors.keys()) or "none"
                    logger.warning(f"⚠️  Oxygen sensor probe failed on I2C addresses: {attempted}")
                    if probe_errors:
                        logger.debug(f"Oxygen sensor probe details: {probe_errors}")
                    logger.info(
                        "🔧 System will continue without oxygen sensor. Check wiring/power/address or run `make fix-i2c`."
                    )
                    
            except Exception as e:
                logger.error(f"❌ Oxygen sensor init/test error: {e}")
                self.oxygen_sensor = None
                self.oxygen_sensor_address = None
                self.oxygen_sensor_available = False
                logger.info("🔧 System will continue without oxygen sensor")
        else:
            self.oxygen_sensor_available = False
            logger.info("ℹ️  Oxygen sensor library not available")
        
        # Oksijen sensörü varsa sensor_data'ya ekle
        if oxygen_enabled and self.oxygen_sensor_available:
            self.sensor_data['oxygen'] = {'value': '--', 'status': 'Initializing...'}
            logger.info("📊 Optional oxygen sensor added to dashboard")
            logger.info("💨 Ozone mode: OXYGEN-BASED (intelligent control)")
        else:
            logger.info("📊 Optional oxygen sensor excluded from dashboard")
            logger.info("💨 Ozone mode: TIMED (fixed interval control)")

        # Primary climate sensor: SCD41
        if CO2_AVAILABLE:
            try:
                logger.info("🔄 Initializing primary climate sensor: SCD41...")
                self.co2_sensor = SCD41Sensor()
                
                # İlk okuma testi - 5 saniye bekle ve test et
                logger.info("⏳ Waiting 5 seconds for SCD41 warm-up...")
                time.sleep(5)
                
                test_data = self.co2_sensor.read_all()
                if (test_data.get('co2') is not None and 
                    test_data.get('temperature') is not None and 
                    test_data.get('humidity') is not None):
                    
                    self.co2_sensor_available = True
                    self.co2_sensor_type = 'SCD41'
                    self.sensor_data['co2'] = {'value': '--', 'status': 'OK'}
                    logger.info(
                        f"✅ Primary climate sensor ready (SCD41): CO2={test_data['co2']:.0f}ppm, "
                        f"Temp={test_data['temperature']:.1f}°C, "
                        f"Hum={test_data['humidity']:.0f}%"
                    )
                else:
                    logger.error("❌ SCD41 test failed - no valid data")
                    self.co2_sensor = None
                    self.co2_sensor_available = False
                    logger.info("🔧 System will continue with fallback climate sensor path (DHT)")
                    
            except Exception as e:
                logger.error(f"❌ SCD41 init/test error: {e}")
                self.co2_sensor = None
                self.co2_sensor_available = False
                logger.info("🔧 System will continue with fallback climate sensor path (DHT)")
        else:
            logger.info("ℹ️  SCD41 library not available, fallback climate sensor path will use DHT")
            self.co2_sensor_available = False
    
    def initialize_fan_pwm(self, force_recreate=False):
        """Initialize optional PWM output for the fan."""
        global GPIO_AVAILABLE

        if not self.is_fan_pwm_mode():
            self.fan_pwm_available = False
            self.fan_pwm_duty = 0.0
            return False

        if not GPIO_AVAILABLE:
            logger.info("ℹ️ Fan PWM requested but GPIO is not available")
            self.fan_pwm_available = False
            self.fan_pwm_duty = 0.0
            return False

        if not hasattr(GPIO, 'PWM'):
            logger.warning("⚠️ RPi.GPIO PWM API bulunamadı - fan röle modunda kalacak")
            self.fan_pwm_available = False
            self.fan_pwm_duty = 0.0
            return False

        reserved_pins = reserved_gpio_pins(self.outChannels, self.pinDht, self.pinWps)
        if self.fan_pwm_pin in reserved_pins:
            logger.error(
                "❌ Fan PWM pin conflict: GPIO %s zaten başka bir iş için kullanılıyor",
                self.fan_pwm_pin,
            )
            self.fan_pwm_available = False
            self.fan_pwm_duty = 0.0
            return False

        try:
            with self.fan_pwm_lock:
                if force_recreate and self.fan_pwm is not None:
                    try:
                        self.fan_pwm.ChangeDutyCycle(0)
                        self.fan_pwm.stop()
                    except Exception as stop_error:
                        logger.warning(f"⚠️ Fan PWM stop warning: {stop_error}")
                    self.fan_pwm = None

                if self.fan_pwm is None:
                    GPIO.setup(self.fan_pwm_pin, GPIO.OUT)
                    self.fan_pwm = GPIO.PWM(self.fan_pwm_pin, self.fan_pwm_frequency)
                    self.fan_pwm.start(0)

            self.fan_pwm_available = True
            self.fan_pwm_duty = 0.0
            logger.info(
                "✅ Fan PWM initialized on GPIO %s @ %sHz",
                self.fan_pwm_pin,
                self.fan_pwm_frequency,
            )
            return True
        except Exception as e:
            logger.error(f"❌ Fan PWM init error: {e}")
            self.fan_pwm = None
            self.fan_pwm_available = False
            self.fan_pwm_duty = 0.0
            return False

    def stop_fan_pwm(self):
        """Stop PWM safely during shutdown/reset flows."""
        if self.fan_pwm is None:
            self.fan_pwm_duty = 0.0
            self.fan_pwm_available = False
            return

        try:
            with self.fan_pwm_lock:
                self.fan_pwm.ChangeDutyCycle(0)
                self.fan_pwm.stop()
        except Exception as e:
            logger.warning(f"⚠️ Fan PWM stop error: {e}")
        finally:
            self.fan_pwm = None
            self.fan_pwm_duty = 0.0
            self.fan_pwm_available = False

    def _get_sensor_numeric_value(self, sensor_name):
        """Return a numeric sensor value when available."""
        return get_sensor_numeric_value(self.sensor_data, sensor_name)

    def is_heater_output_active(self):
        """Return True when any heating output is currently active."""
        return heater_output_active(self.gpio_output_states)

    def should_run_humidity_purge(self, effective_sliders=None):
        """Return True when excess humidity should trigger ventilation."""
        if effective_sliders is None:
            effective_sliders = self.get_effective_slider_values()

        hum = self._get_sensor_numeric_value('humidity')
        try:
            hum_target = float(effective_sliders.get('sld2'))
        except (TypeError, ValueError):
            hum_target = None

        active, event = evaluate_humidity_purge(
            enabled=bool(self.button_states.get('b3')),
            humidity_value=hum,
            humidity_target=hum_target,
            previous_state=self.humidity_purge_active,
            on_delta=self.HUMIDITY_PURGE_ON_DELTA,
            off_delta=self.HUMIDITY_PURGE_OFF_DELTA,
        )

        if event == 'started':
            logger.info(
                "💨 Nem purgesi başladı - Nem %.1f%%, hedef %.1f%%",
                hum,
                hum_target,
            )
        elif event == 'stopped':
            logger.info(
                "💨 Nem purgesi durdu - Nem %.1f%%, hedef %.1f%%",
                hum if hum is not None else -1.0,
                hum_target if hum_target is not None else -1.0,
            )

        self.humidity_purge_active = active
        return active

    def get_fan_speed_percent(self, effective_sliders=None):
        """Return automatic fan PWM duty cycle derived from climate demand."""
        if effective_sliders is None:
            effective_sliders = self.get_effective_slider_values()
        return calculate_fan_speed_percent(
            effective_sliders=effective_sliders,
            sensor_data=self.sensor_data,
            gpio_output_states=self.gpio_output_states,
            button_states=self.button_states,
            humidity_purge_active=self.humidity_purge_active,
            fan_pwm_heater_min_duty=self.fan_pwm_heater_min_duty,
            clamp=_clamp,
        )

    def apply_fan_output(self, enabled, duty=None, source='manual'):
        """Drive fan output using the selected output mode."""
        return self.output_controller.apply_fan_output(enabled, duty=duty, source=source)

    def safe_gpio_output(self, pin, state):
        """Thread-safe GPIO output with state tracking"""
        return self.output_controller.safe_gpio_output(pin, state)

    def get_button_name_by_pin(self, pin):
        """Get button name (b1-b9) by GPIO pin number"""
        return button_name_by_pin(pin)
    
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
                GPIO.setup(self.pinWps, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                self.initialize_fan_pwm(force_recreate=True)
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
                
                GPIO.setup(self.pinWps, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                self.initialize_fan_pwm(force_recreate=True)
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
        corrected_temp, corrected_hum, updated_temp, updated_hum = filter_dht_bit_shift_helper(
            temp,
            hum,
            self.last_valid_temp,
            self.last_valid_humidity,
            debug=logger.debug,
            info=logger.info,
            warning=logger.warning,
        )
        self.last_valid_temp = updated_temp
        self.last_valid_humidity = updated_hum
        return corrected_temp, corrected_hum
    
    def apply_moving_average(self, temp, hum):
        """DHT11 sensör kalitesi filtresi - hareketli ortalama.
        
        DHT11 düşük kaliteli sensördür:
        - Sıcaklık: ±2°C hata payı (4-5°C sıçramalar normal)
        - Nem: ±5% hata payı (2-3% sıçramalar normal)
        
        Çözüm: Son N okumanın ortalamasını al (smoothing filter)
        - Ani sıçramaları yumuşatır
        - Gerçek değişimleri korur
        - 3 okuma penceresi (~45 saniye) optimal
        - Hem sıcaklık hem de nem için uygulanır
        """
        avg_temp, avg_hum, next_temp_readings, next_humidity_readings = apply_dht_moving_average(
            temp,
            hum,
            self.temp_readings,
            self.humidity_readings,
            self.moving_avg_window,
            debug=logger.debug,
        )
        self.temp_readings = next_temp_readings
        self.humidity_readings = next_humidity_readings
        return avg_temp, avg_hum
    
    def read_sensors(self):
        """Sensörleri oku - Öncelik: SCD41 (CO2+Sıcaklık+Nem) → DHT (yedek)"""
        try:
            oxygen_enabled = self.is_oxygen_feature_enabled()
            if not oxygen_enabled:
                self.sensor_data.pop('oxygen', None)

            # Priority 1: SCD41 sensor (CO2, Temperature, Humidity all-in-one)
            scd41_success = False
            
            if self.co2_sensor_available and self.co2_sensor and CO2_SENSOR_TYPE == 'SCD41':
                try:
                    data = self.co2_sensor.read_all()
                    co2_ppm = data.get('co2')
                    temp_c = data.get('temperature')
                    humidity = data.get('humidity')
                    
                    # SCD41'den tüm değerleri oku (CO2, sıcaklık, nem)
                    if co2_ppm is not None and 0 <= co2_ppm <= 10000:
                        startup_blending = bool(self._startup_sensor_baseline) and (
                            self._co2_warmup_reads < self._co2_startup_blend_reads
                        )
                        effective_co2_ppm = self.blend_startup_sensor_value('co2', co2_ppm)

                        # CO2 okuma
                        self.sensor_data['co2'] = {
                            'value': f"{effective_co2_ppm:.0f}",
                            'status': 'SCD41 (stabilizing)' if startup_blending else 'SCD41'
                        }
                        
                        # Sıcaklık ve nem okuma
                        temp_valid = (temp_c is not None and -40 <= temp_c <= 85 and temp_c != 0.0)
                        hum_valid = (humidity is not None and 0 <= humidity <= 100)
                        
                        if temp_valid and hum_valid:
                            effective_temp_c = self.blend_startup_sensor_value('temperature', temp_c)
                            effective_humidity = self.blend_startup_sensor_value('humidity', humidity)
                            climate_status = 'SCD41 (stabilizing)' if startup_blending else 'SCD41'
                            self.sensor_data['temperature'] = {
                                'value': f"{effective_temp_c:.1f}",
                                'status': climate_status
                            }
                            self.sensor_data['humidity'] = {
                                'value': f"{effective_humidity:.0f}",
                                'status': climate_status
                            }
                            scd41_success = True
                            logger.info(
                                f"✅ SCD41: {effective_temp_c:.1f}°C, {effective_humidity:.0f}%rH, CO2: {effective_co2_ppm:.0f}ppm"
                            )

                            if startup_blending:
                                self._co2_warmup_reads += 1
                                if self._co2_warmup_reads == 1:
                                    logger.info(
                                        f"🌡️ SCD41 startup stabilization active - blending first {self._co2_startup_blend_reads} reads"
                                    )
                                if self._co2_warmup_reads >= self._co2_startup_blend_reads:
                                    self._startup_sensor_baseline = {}
                                    logger.info("🌡️ SCD41 startup stabilization completed")
                        else:
                            logger.warning(f"⚠️  SCD41: CO2 OK ama sıcaklık/nem geçersiz (temp={temp_c}, hum={humidity})")
                        
                        # Oksijen sensörü yoksa CO2'den O2 tahmini yap
                        if oxygen_enabled and not self.oxygen_sensor_available:
                            estimated_o2 = self.estimate_oxygen_from_co2(effective_co2_ppm)
                            if estimated_o2 is not None:
                                self.sensor_data['oxygen'] = {
                                    'value': f"{estimated_o2:.1f}",
                                    'status': f"Tahmini (CO2: {effective_co2_ppm:.0f}ppm)"
                                }
                    else:
                        logger.debug(f"SCD41 data not ready or invalid: {co2_ppm}")
                        
                except Exception as e:
                    logger.error(f"❌ SCD41 read error: {e}")
                    # SCD41 başarısız, DHT'ye geç
                    logger.info("🔄 SCD41 okuma hatası - DHT sensörüne geçiliyor...")
            
            # Priority 2: DHT sensor (fallback - sadece SCD41 başarısız olursa)
            if DHT_AVAILABLE and not scd41_success:
                logger.debug(f"🌡️  Reading DHT{self.sensorDht} sensor from GPIO {self.pinDht}...")
                try:
                    # Sabit sensör tipi ile okuma (daha kararlı ve log spam'i azaltır)
                    hum, temp = read_retry(sensor_type=self.sensorDht, pin=self.pinDht)
                    if hum is not None and temp is not None:
                        # 1. Bit kayması filtresi (anomali tespiti)
                        try:
                            temp, hum = self.filter_dht_bit_shift(temp, hum)
                        except Exception as filter_error:
                            logger.error(f"⚠️  DHT bit-shift filter error: {filter_error}")
                            import traceback
                            logger.error(traceback.format_exc())
                        
                        # 2. Hareketli ortalama filtresi (sensör kalitesi düzeltmesi)
                        try:
                            temp, hum = self.apply_moving_average(temp, hum)
                        except Exception as avg_error:
                            logger.error(f"⚠️  DHT moving average error: {avg_error}")
                        
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
                        
                        # 10 hatadan sonra hata mesajı göster (simülasyon YOK)
                        else:
                            if self.sensor_error_count == 11:
                                logger.error(f"❌ DHT sensör 10 kez okunamadı - sensör bağlantısını kontrol edin!")
                            
                            # Simülasyon kullanma - hata göster
                            self.sensor_data['temperature'] = {
                                'value': '--',
                                'status': 'Sensör bağlantı hatası'
                            }
                            self.sensor_data['humidity'] = {
                                'value': '--',
                                'status': 'Sensör bağlantı hatası'
                            }
                        
                        
                except Exception as dht_error:
                    logger.error(f"❌ DHT{self.sensorDht} read exception: {dht_error}")
                    self.sensor_error_count += 1
                    
                    # Exception durumunda hata göster (simülasyon YOK)
                    self.sensor_data['temperature'] = {
                        'value': '--',
                        'status': f'Bağlantı hatası ({self.sensor_error_count})'
                    }
                    self.sensor_data['humidity'] = {
                        'value': '--',
                        'status': f'Bağlantı hatası ({self.sensor_error_count})'
                    }
            
            # SCD41 yoksa ve DHT de yoksa - hata göster (simülasyon YOK)
            if not DHT_AVAILABLE and not scd41_success:
                # Neither SCD41 nor DHT available - show error
                self.sensor_data['temperature'] = {
                    'value': '--',
                    'status': 'Sensör bulunamadı'
                }
                self.sensor_data['humidity'] = {
                    'value': '--',
                    'status': 'Sensör bulunamadı'
                }
                logger.error(f"❌ Sıcaklık/Nem sensörü bulunamadı - DHT veya SCD41 gerekli!")
            
            # Oxygen sensor - sadece mevcut ve test edilmişse oku
            if oxygen_enabled and self.oxygen_sensor_available and self.oxygen_sensor:
                try:
                    oxygen_data = self.oxygen_sensor.get_oxygen_data(20)  # 20 samples
                    if oxygen_data is not None and 0 <= oxygen_data <= 100:
                        self.sensor_data['oxygen'] = {
                            'value': f"{oxygen_data:.1f}",
                            'status': 'OK'
                        }
                    else:
                        logger.warning(f"⚠️  Invalid oxygen reading: {oxygen_data} - skipping")
                        
                except Exception as e:
                    logger.error(f"❌ Oxygen sensor read error: {e} - skipping")

            # Log sensor data if values changed AND system is active
            # Conditional Logging: Don't log if system is in standby (all buttons OFF)
            system_active = any(self.button_states.values())
            
            if self.sensor_logger and system_active:
                self.sensor_logger.log_if_changed(self.sensor_data)
                
            # Firebase Update (optional)
            if self.firebase_manager and hasattr(self.firebase_manager, 'connected') and self.firebase_manager.connected:
                self.firebase_manager.update_sensor_data(self.sensor_data)

            # Feed the latest sensor snapshot into AI analytics on every cycle.
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
                if oxygen_enabled and 'oxygen' in self.sensor_data and self.sensor_data['oxygen']['value'] != '--':
                    try:
                        sensor_values['oxygen'] = float(self.sensor_data['oxygen']['value'])
                    except ValueError:
                        pass

                actuator_states = {
                    'heater_on': self.gpio_output_states.get('b4', False) == True,  # LOW=True=ON
                    'nebulizer_on': self.gpio_output_states.get('b2', False) == True,
                    'ozone_on': self.gpio_output_states.get('b8', False) == True
                }

                self.ai_manager.update_sensors(sensor_values, actuator_states)
        
        except Exception as e:
            logger.error(f"Sensor read error: {e}")
            self.sensor_error_count += 1
            
            if self.sensor_error_count > 5:
                # Reset to safe state
                self.reset_to_safe_state()

    def wps_button_check_loop(self):
        """Fiziksel WPS butonunu takip et (Headless mod için)"""
        if not GPIO_AVAILABLE:
            return

        logger.info(f"🔘 WPS physical button monitor started on GPIO {self.pinWps}")
        press_start_time = 0
        
        while self.running:
            # Buton basılı mı? (Pull-up olduğu için LOW = Basılı)
            if GPIO.input(self.pinWps) == GPIO.LOW:
                if press_start_time == 0:
                    press_start_time = time.time()
                else:
                    duration = time.time() - press_start_time
                    if duration >= 2.0:  # 2 saniye basılı tutulursa
                        logger.info("🔘 WPS button long press detected! Starting pairing...")
                        ok, msg, _ = _start_wps_pairing('wlan0')
                        if not ok:
                            logger.warning(f"WPS button trigger rejected: {msg}")
                        # Görsel/işitsel geri bildirim için (örneğin b1 ışığını yakıp söndür)
                        self.safe_gpio_output(5, GPIO.LOW)  # Işık aç
                        time.sleep(0.5)
                        self.safe_gpio_output(5, GPIO.HIGH) # Işık kapa
                        
                        # Butonun bırakılmasını bekle
                        while GPIO.input(self.pinWps) == GPIO.LOW:
                            time.sleep(0.1)
                        press_start_time = 0
            else:
                press_start_time = 0
                
            time.sleep(0.2)

    def check_and_start_hotspot_fallback(self):
        """Eğer Wi-Fi bağlı değilse ve headless ise AP başlat (Hotspot)"""
        try:
            # Mevcut bağlantıyı kontrol et
            result = subprocess.run(['nmcli', '-t', '-f', 'DEVICE,STATE', 'dev'], capture_output=True, text=True)
            wifi_connected = False
            for line in result.stdout.split('\n'):
                if 'wifi:connected' in line:
                    wifi_connected = True
                    break
            
            if not wifi_connected:
                logger.warning("📶 No Wi-Fi connection detected. Headless units might need Hotspot...")
                # Buraya bir timeout eklenebilir veya kullanıcı konfigürasyonuyla AP başlatılabilir
                # Örnek (opsiyonel): os.system("sudo nmcli con up Kuvoz-Hotspot")
                
        except Exception as e:
            logger.error(f"Hotspot fallback check error: {e}")

    def start_threads(self):
        """Tüm background thread'leri başlat"""
        self.running = True
        
        # Sensor thread
        self.sensor_thread = threading.Thread(target=self.sensor_loop, daemon=True)
        self.sensor_thread.start()
        
        # Control thread
        self.control_thread = threading.Thread(target=self.control_loop, daemon=True)
        self.control_thread.start()

        # WPS button thread
        self.wps_thread = threading.Thread(target=self.wps_button_check_loop, daemon=True)
        self.wps_thread.start()
        
        logger.info("🧵 All background threads started")
        
        # Headless check (opsiyonel/gecikmeli)
        threading.Timer(60, self.check_and_start_hotspot_fallback).start()

    def sensor_loop(self):
        """Sensör okuma döngüsü"""
        while self.running:
            self.read_sensors()
            time.sleep(15)

    def control_loop(self):
        """Kontrol mantığı döngüsü"""
        while self.running:
            # Kontrol mantığı (sıcaklık, nem vb.) buraya gelecek
            time.sleep(1)
    
    def check_temperature_alarms(self, temp, current_time):
        """
        Sıcaklık bazlı hayati risk alarmları
        Critical temperature alarms for life safety
        """
        if temp is None or temp == '--':
            return
        
        try:
            temp = float(temp)
        except (ValueError, TypeError):
            return
        
        # Check if alarm cooldown has passed (5 minutes between repeated alarms)
        alarm_cooldown_passed = (current_time - self.last_alarm_time) >= self.alarm_cooldown
        
        # CRITICAL HIGH: > 40°C - Hayati tehlike!
        if temp >= self.TEMP_CRITICAL_HIGH:
            if alarm_cooldown_passed or not self.critical_alarm_active:
                logger.critical(f"🚨 KRİTİK YÜKSEK SICAKLIK ALARMI: {temp}°C - Hayati tehlike!")
                socketio.emit('critical_alarm', {
                    'type': 'critical_high_temp',
                    'severity': 'critical',
                    'message': f'🚨 KRİTİK SICAKLIK: {temp}°C - Hayati tehlike! Acil müdahale gerekli!',
                    'temperature': temp,
                    'threshold': self.TEMP_CRITICAL_HIGH,
                    'timestamp': datetime.datetime.now().isoformat()
                }, broadcast=True)
                self.last_alarm_time = current_time
                self.critical_alarm_active = True
        
        # WARNING HIGH: > 38°C - Uyarı
        elif temp >= self.TEMP_WARNING_HIGH:
            if alarm_cooldown_passed:
                logger.warning(f"⚠️ YÜKSEK SICAKLIK UYARISI: {temp}°C - Dikkat!")
                socketio.emit('temperature_alarm', {
                    'type': 'warning_high_temp',
                    'severity': 'warning',
                    'message': f'⚠️ YÜKSEK SICAKLIK: {temp}°C - Dikkat!',
                    'temperature': temp,
                    'threshold': self.TEMP_WARNING_HIGH,
                    'timestamp': datetime.datetime.now().isoformat()
                }, broadcast=True)
                self.last_alarm_time = current_time
        
        # CRITICAL LOW: < 10°C - Hayati tehlike!
        elif temp <= self.TEMP_CRITICAL_LOW:
            if alarm_cooldown_passed or not self.critical_alarm_active:
                logger.critical(f"🚨 KRİTİK DÜŞÜK SICAKLIK ALARMI: {temp}°C - Hayati tehlike!")
                socketio.emit('critical_alarm', {
                    'type': 'critical_low_temp',
                    'severity': 'critical',
                    'message': f'🚨 KRİTİK SOĞUK: {temp}°C - Hayati tehlike! Acil müdahale gerekli!',
                    'temperature': temp,
                    'threshold': self.TEMP_CRITICAL_LOW,
                    'timestamp': datetime.datetime.now().isoformat()
                }, broadcast=True)
                self.last_alarm_time = current_time
                self.critical_alarm_active = True
        
        # WARNING LOW: < 15°C - Uyarı
        elif temp <= self.TEMP_WARNING_LOW:
            if alarm_cooldown_passed:
                logger.warning(f"⚠️ DÜŞÜK SICAKLIK UYARISI: {temp}°C - Dikkat!")
                socketio.emit('temperature_alarm', {
                    'type': 'warning_low_temp',
                    'severity': 'warning',
                    'message': f'⚠️ DÜŞÜK SICAKLIK: {temp}°C - Dikkat!',
                    'temperature': temp,
                    'threshold': self.TEMP_WARNING_LOW,
                    'timestamp': datetime.datetime.now().isoformat()
                }, broadcast=True)
                self.last_alarm_time = current_time
        
        # Reset critical alarm flag when temperature is back to normal
        if self.TEMP_WARNING_LOW < temp < self.TEMP_WARNING_HIGH:
            self.critical_alarm_active = False
    
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
            effective_sliders = self.get_effective_slider_values()
            temperature_value = self._get_sensor_numeric_value('temperature')
            humidity_value = self._get_sensor_numeric_value('humidity')
            
            # 🔍 Check temperature alarms (life safety)
            if self.sensor_data['temperature']['value'] != '--':
                self.check_temperature_alarms(
                    self.sensor_data['temperature']['value'],
                    current_time
                )
            
            temp_target = effective_sliders.get('sld3')
            humidity_target = effective_sliders.get('sld2')
            cooling_target = effective_sliders.get('sld12', 0)

            carbon_heater_active, carbon_reason = decide_hysteresis_output(
                enabled=bool(self.button_states['b4']),
                sensor_value=temperature_value,
                target=temp_target,
                hysteresis=self.TEMP_HYSTERESIS,
                current_output_active=bool(self.gpio_output_states.get('b4') is True),
            )
            self.safe_gpio_output(16, GPIO.LOW if carbon_heater_active else GPIO.HIGH)
            if self.button_states['b4'] and carbon_reason == 'sensor_missing':
                logger.warning("⚠️  Temperature sensor unavailable - heating disabled for safety")

            humidifier_active, humidity_reason = decide_hysteresis_output(
                enabled=bool(self.button_states['b3']),
                sensor_value=humidity_value,
                target=humidity_target,
                hysteresis=self.HUM_HYSTERESIS,
                current_output_active=bool(self.gpio_output_states.get('b3') is True),
            )
            self.safe_gpio_output(13, GPIO.LOW if humidifier_active else GPIO.HIGH)
            if self.button_states['b3'] and humidity_reason == 'sensor_missing':
                logger.warning("⚠️  Humidity sensor unavailable - humidifier disabled for safety")

            ir_heater_active, ir_reason = decide_hysteresis_output(
                enabled=bool(self.button_states['b5']),
                sensor_value=temperature_value,
                target=temp_target,
                hysteresis=self.TEMP_HYSTERESIS,
                current_output_active=bool(self.gpio_output_states.get('b5') is True),
            )
            self.safe_gpio_output(19, GPIO.LOW if ir_heater_active else GPIO.HIGH)
            if self.button_states['b5'] and ir_reason == 'sensor_missing':
                logger.warning("⚠️  Temperature sensor unavailable - IR heater disabled for safety")

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

            # Cooling control with hysteresis and heating conflict prevention (b9 - pin 20)
            # SAFETY: Cooling and heating MUST NOT run simultaneously
            # MODE: If sld12 > 0 → Auto mode (hysteresis control), If sld12 = 0 → Manual ON/OFF
            # Only control if function is enabled by user
            
            # Track cooling state changes only (not every iteration)
            # Removed excessive debug logging
            
            # SAFETY: Cooling and heating MUST NOT run simultaneously
            # MODE: If sld12 > 0 → Auto mode (hysteresis control), If sld12 = 0 → Manual ON/OFF
            # Only control if function is enabled by user
            prev_cooling_state = self.gpio_output_states.get('b9', False) == True
            heater_active = carbon_heater_active or ir_heater_active or self.is_heater_output_active()
            cooling_feature_enabled = bool(self.system_settings.get('cooling_enabled', False))
            cooling_requested = cooling_feature_enabled and bool(self.button_states['b9'])
            cooling_active, cooling_reason = decide_cooling_output(
                enabled=cooling_requested,
                heater_active=heater_active,
                temperature_value=temperature_value,
                cooling_target=cooling_target,
                hysteresis=self.COOLING_HYSTERESIS,
                current_output_active=prev_cooling_state,
            )
            self.safe_gpio_output(12, GPIO.LOW if cooling_active else GPIO.HIGH)
            if self.button_states['b9']:
                if not cooling_feature_enabled:
                    logger.warning("❄️  Cooling disabled - feature is turned off in settings")
                elif cooling_reason == 'blocked_by_heater':
                    logger.warning("❄️  Cooling disabled - Heaters are active (safety interlock)")
                elif cooling_reason == 'no_target':
                    logger.warning("❄️  Cooling disabled - No target temperature set (sld12=0)")
                elif cooling_reason == 'sensor_missing':
                    logger.warning("❄️  Cooling disabled - Temperature sensor unavailable")
                elif cooling_reason == 'on' and not prev_cooling_state:
                    logger.info(f"❄️  Cooling ON - Temp {temperature_value}°C > Target+Hyst {cooling_target+self.COOLING_HYSTERESIS}°C")
                elif cooling_reason == 'off' and prev_cooling_state:
                    logger.info(f"❄️  Cooling OFF - Temp {temperature_value}°C < Target-Hyst {cooling_target-self.COOLING_HYSTERESIS}°C")

            # Fan control based on actual climate demand (b6 - pin 20 / PWM P18)
            # Fan ON/OFF behavior stays compatible; PWM duty is now determined automatically.
            humidity_purge_active = self.should_run_humidity_purge(effective_sliders=effective_sliders)
            fan_duty = self.get_fan_speed_percent(effective_sliders=effective_sliders)
            
            if carbon_heater_active or ir_heater_active:
                self.fan_auto_active = True
                self.apply_fan_output(True, duty=fan_duty, source='heater')
                if not self.button_states['b6']:
                    self.button_states['b6'] = True
                    logger.info("🌀 Fan otomatik açıldı - ısıtıcılar aktif")
            elif cooling_active:
                # 🧊 SOĞUTMA AKTİF: Fanı otomatik olarak çalıştır (mosfet üzerinden)
                self.fan_auto_active = True
                self.apply_fan_output(True, duty=fan_duty, source='cooling')
                if not self.button_states['b6']:
                    self.button_states['b6'] = True
                    logger.info("🌀 Fan otomatik açıldı - soğutma aktif")
            elif self.button_states.get('b6_manual', False) and self.button_states['b6']:
                self.fan_auto_active = False
                self.apply_fan_output(True, duty=fan_duty, source='manual_hold')
                logger.debug("🌀 Fan manuel açık, hız sistem tarafından ayarlanıyor")
            elif humidity_purge_active:
                self.fan_auto_active = True
                self.apply_fan_output(True, duty=fan_duty, source='humidity_purge')
                if not self.button_states['b6']:
                    self.button_states['b6'] = True
                    logger.info("🌀 Fan otomatik açıldı - yüksek nem purgesi")
            else:
                self.fan_auto_active = False
                self.apply_fan_output(False, source='auto_off')
                if self.button_states['b6']:
                    self.button_states['b6'] = False
                self.button_states['b6_manual'] = False
                logger.debug("🌀 Fan otomatik kapatıldı - ısıtıcılar kapandı ve manuel kontrol yoktu")

        except Exception as e:
            logger.error(f"Control logic error: {e}")
    
    def nebulizer_control(self):
        """Nebulizer duty cycle control"""
        try:
            current_time = time.time()
            if not self.nebulizer_in_duty:
                # Start duty cycle
                self.safe_gpio_output(6, GPIO.LOW)  # Turn ON
                self.nebulizer_in_duty, self.nebulizer_duty_start = start_duty_cycle(current_time)
                logger.info(f"Nebulizer DUTY cycle started - ON for {self.slider_values['sld8']} minutes")
            
        except Exception as e:
            logger.error(f"Nebulizer control error: {e}")
    
    def update_nebulizer_duty_cycle(self):
        """Update nebulizer duty cycle state"""
        try:
            current_time = time.time()
            duty_duration = int(self.slider_values['sld8'] * 60)
            free_duration = int(self.slider_values['sld9'] * 60)
            action, self.nebulizer_in_duty, self.nebulizer_duty_start = update_duty_cycle_state(
                button_enabled=bool(self.button_states['b2']),
                in_duty=self.nebulizer_in_duty,
                phase_started_at=self.nebulizer_duty_start,
                current_time=current_time,
                duty_duration=duty_duration,
                free_duration=free_duration,
            )

            if action == 'stop':
                self.safe_gpio_output(6, GPIO.HIGH)
                logger.info("Nebulizer stopped - button OFF")
            elif action == 'to_free':
                self.safe_gpio_output(6, GPIO.HIGH)
                logger.info(f"Nebulizer FREE cycle started - OFF for {self.slider_values['sld9']} minutes")
            elif action == 'to_duty':
                self.safe_gpio_output(6, GPIO.LOW)
                logger.info(f"Nebulizer new DUTY cycle started - ON for {self.slider_values['sld8']} minutes")

        except Exception as e:
            logger.error(f"Nebulizer duty cycle update error: {e}")
    
    def ozone_control(self):
        """Ozone duty cycle control with oxygen sensor intelligence (real or estimated)"""
        try:
            current_time = time.time()
            duty_duration = self.slider_values['sld10'] * 60  # duty minutes to seconds
            adjusted_duty, current_oxygen, oxygen_source = compute_ozone_duty_duration(
                base_duration=int(duty_duration),
                sensor_data=self.sensor_data,
                allow_estimated_oxygen=True,
            )
            if current_oxygen is not None and adjusted_duty != int(duty_duration):
                logger.info(f"🌟 High oxygen ({current_oxygen:.1f}%, {oxygen_source}) - Extended ozone duty")
            
            if not self.ozone_in_duty:
                # Start duty cycle
                self.safe_gpio_output(26, GPIO.LOW)  # Turn ON
                self.ozone_in_duty, self.ozone_duty_start = start_duty_cycle(current_time)
                logger.info(f"💨 Ozone DUTY cycle started - ON for {adjusted_duty//60} minutes")
            
        except Exception as e:
            logger.error(f"Ozone control error: {e}")
    
    def update_ozone_duty_cycle(self):
        """Update ozone duty cycle state"""
        try:
            current_time = time.time()
            base_duty_duration = int(self.slider_values['sld10'] * 60)
            free_duration = int(self.slider_values['sld11'] * 60)
            duty_duration, current_oxygen, oxygen_source = compute_ozone_duty_duration(
                base_duration=base_duty_duration,
                sensor_data=self.sensor_data,
                allow_estimated_oxygen=True,
            )
            if current_oxygen is not None and duty_duration != base_duty_duration:
                logger.info(f"🌟 High O2 ({current_oxygen:.1f}%, {oxygen_source}) - Extended ozone duty to {duty_duration//60}min")

            action, self.ozone_in_duty, self.ozone_duty_start = update_duty_cycle_state(
                button_enabled=bool(self.button_states['b8']),
                in_duty=self.ozone_in_duty,
                phase_started_at=self.ozone_duty_start,
                current_time=current_time,
                duty_duration=duty_duration,
                free_duration=free_duration,
            )

            if action == 'stop':
                self.safe_gpio_output(26, GPIO.HIGH)
                logger.info("💨 Ozone stopped - button OFF")
            elif action == 'to_free':
                self.safe_gpio_output(26, GPIO.HIGH)
                logger.info(f"💨 Ozone FREE cycle started - OFF for {free_duration//60} minutes")
            elif action == 'to_duty':
                self.safe_gpio_output(26, GPIO.LOW)
                logger.info(f"💨 Ozone new DUTY cycle started - ON for {self.slider_values['sld10']} minutes")
                    
        except Exception as e:
            logger.error(f"Ozone duty cycle update error: {e}")
    
    def get_timer_data(self):
        """Get current timer states for frontend"""
        with self.state_lock:
            current_time = time.time()
            nebulizer_duty_duration = int(self.slider_values['sld8'] * 60)
            nebulizer_free_duration = int(self.slider_values['sld9'] * 60)
            ozone_duty_duration = int(self.slider_values['sld10'] * 60)
            ozone_free_duration = int(self.slider_values['sld11'] * 60)
            ozone_duty_duration, _ = resolve_ozone_duty_duration(
                ozone_duty_duration,
                self.sensor_data.get('oxygen') if self.oxygen_sensor_available else None,
            )

            nebulizer_timer = build_timer_state(
                button_enabled=bool(self.button_states['b2']),
                in_duty=self.nebulizer_in_duty,
                phase_started_at=self.nebulizer_duty_start,
                current_time=current_time,
                duty_duration=nebulizer_duty_duration,
                free_duration=nebulizer_free_duration,
            )
            ozone_timer = build_timer_state(
                button_enabled=bool(self.button_states['b8']),
                in_duty=self.ozone_in_duty,
                phase_started_at=self.ozone_duty_start,
                current_time=current_time,
                duty_duration=ozone_duty_duration,
                free_duration=ozone_free_duration,
            )

        return {
            'nebulizer': nebulizer_timer,
            'ozone': ozone_timer,
        }
    
    def reset_to_safe_state(self):
        """Güvenli duruma geç"""
        logger.warning("Resetting to safe state")
        with self.state_lock:
            self.fan_auto_active = False
            self.apply_fan_output(False, source='safe_state')
            for pin in self.outChannels:
                if pin == 20:
                    continue
                self.safe_gpio_output(pin, GPIO.HIGH)

            for key in self.button_states:
                self.button_states[key] = False
        
        # Persist forced safe-state so a subsequent restart keeps system consistent
        self.save_settings()
    
    def toggle_button(self, name, pin, state):
        """Buton kontrolü - button_states ve GPIO'yu anında değiştir"""
        try:
            with self.state_lock:
                controlled_buttons = {'b3', 'b4', 'b5', 'b9'}
                direct_buttons = {'b1', 'b7'}
                duty_cycle_buttons = {'b2', 'b8'}

                # DEBUG: Log b9 (cooling) button specifically
                if name == 'b9':
                    logger.info(f"🧊 COOLING BUTTON (b9) triggered - pin:{pin}, state:{state}")
                    if not self.system_settings.get('cooling_enabled', False):
                        self.button_states['b9'] = False
                        logger.warning("❄️  Cooling button ignored because cooling is disabled in settings")
                        self.safe_gpio_output(pin, GPIO.HIGH)
                        return False

                # Button state'i güncelle
                self.button_states[name] = state
                logger.info(f"Button {name}: {'ENABLED' if state else 'DISABLED'}")

                if name == 'b6':
                    self.button_states['b6_manual'] = bool(state)
                    self.fan_auto_active = False
                    self.apply_fan_output(bool(state), duty=self.get_fan_speed_percent(), source='manual_button')
                    logger.info(f"Fan output -> {'PWM/relay ON' if state else 'PWM/relay OFF'}")

                    if self.firebase_manager:
                        self.firebase_manager.update_button_state(name, state)

                    self.schedule_settings_save(reason='fan_manual_toggle')
                    return True

                if name in controlled_buttons:
                    logger.info(
                        "GPIO %s control deferred to control loop for %s",
                        pin,
                        name,
                    )
                elif state:
                    # Buton ENABLED -> GPIO LOW (relay ON)
                    self.safe_gpio_output(pin, GPIO.LOW)
                    self.gpio_output_states[name] = True  # LOW = aktif = True
                    logger.info(f"GPIO {pin} -> LOW (relay ON)")

                    # Start duty cycles immediately for duty-cycle buttons
                    if name == 'b2':
                        current_time = time.time()
                        self.nebulizer_in_duty, self.nebulizer_duty_start = start_duty_cycle(current_time)
                        self.last_nebulizer_time = current_time - (self.slider_values['sld6'] * 3600)  # Force interval check to pass
                        logger.info(f"💧 Nebulizer DUTY cycle started immediately - ON for {self.slider_values['sld8']} minutes")
                    elif name == 'b8':
                        current_time = time.time()
                        self.ozone_in_duty, self.ozone_duty_start = start_duty_cycle(current_time)
                        self.last_ozone_time = current_time - (self.slider_values['sld7'] * 3600)  # Force interval check to pass
                        logger.info(f"💨 Ozone DUTY cycle started immediately - ON for {self.slider_values['sld10']} minutes")
                else:
                    # Buton DISABLED -> GPIO HIGH (relay OFF)
                    if name in direct_buttons or name in duty_cycle_buttons:
                        self.safe_gpio_output(pin, GPIO.HIGH)
                        self.gpio_output_states[name] = False  # HIGH = pasif = False
                        logger.info(f"GPIO {pin} -> HIGH (relay OFF)")
                    else:
                        logger.info(
                            "GPIO %s shutdown deferred to control loop for %s",
                            pin,
                            name,
                        )

                    # Reset timers when button is turned OFF
                    if name == 'b2':
                        self.nebulizer_in_duty = False
                        self.nebulizer_duty_start = 0
                        logger.info("Nebulizer timer reset to READY")
                    elif name == 'b8':
                        self.ozone_in_duty = False
                        self.ozone_duty_start = 0
                        logger.info("Ozone timer reset to READY")

            # Sync to Firebase
            if self.firebase_manager:
                self.firebase_manager.update_button_state(name, state)

            # Ayarları otomatik kaydet (restart sonrası hatırlansın)
            self.schedule_settings_save(reason='button_toggle')

            return True
        except Exception as e:
            logger.error(f"Button toggle error: {e}")
            return False
    
    def update_slider(self, slider_id, value):
        """Slider değerini güncelle"""
        try:
            if slider_id == 'sld13':
                logger.info("Fan PWM hızı artık otomatik; manuel sld13 güncellemesi yok sayıldı")
                return True

            with self.state_lock:
                self.slider_values[slider_id] = value
            logger.info(f"Slider {slider_id}: {value}")

            # Sync to Firebase
            if self.firebase_manager:
                self.firebase_manager.update_slider_value(slider_id, value)

            return True
        except Exception as e:
            logger.error(f"Slider update error: {e}")
            return False

    def update_patient_context(self, patient_data):
        """Hasta bilgilerini AI için normalize et ve uygula"""
        if not isinstance(patient_data, dict):
            return False
        try:
            normalized = {
                'name': str(patient_data.get('name') or '').strip(),
                'species': str(patient_data.get('species') or '').strip(),
                'breed': str(patient_data.get('breed') or '').strip(),
                'age': str(patient_data.get('age') or '').strip(),
                'weight': str(patient_data.get('weight') or '').strip(),
            }
            self.patient_context.update(normalized)
            self._ensure_valid_care_mode()
            if self.ai_manager:
                self.ai_manager.set_patient_context(self.patient_context)
            return True
        except Exception as e:
            logger.error(f"Patient context update error: {e}")
            return False

    def _parse_age_weeks(self, raw):
        """Hasta yaşını haftaya çevir."""
        return parse_age_weeks(raw)

    def _build_patient_auto_profile(self):
        """Hasta bilgisine gore otomatik ortam hedefleri uret.
        
        Desteklenen türler: Kedi, Köpek, Kuş
        Her tür için yaşa göre farklı sıcaklık ve nem hedefleri.
        """
        return build_patient_auto_profile(self.patient_context)

    def _ensure_valid_care_mode(self):
        """Otomatik modun gecerli bir hasta profiline bagli oldugunu garanti et."""
        if self.care_settings.get('mode') != 'auto':
            return True

        profile = self._build_patient_auto_profile()
        if profile.get('supported'):
            return True

        self.care_settings['mode'] = 'manual'
        # Manuel moda geçildiğinde hasta context'ini temizle ve slider'ları varsayılan değerlere sıfırla
        self.patient_context = {
            'name': '',
            'species': '',
            'breed': '',
            'age': '',
            'weight': ''
        }
        # Varsayılan slider hedefleri (manuel mod için)
        self.slider_values['sld3'] = 25.0  # Temperature target
        self.slider_values['sld2'] = 65    # Humidity target
        self.slider_values['sld12'] = 25.0 # Cooling target
        logger.warning(
            "⚠️  Auto care mode disabled - no supported patient profile "
            f"(reason={profile.get('reason_code')}). Slider values reset to defaults."
        )
        return False

    def set_care_mode(self, mode):
        """Bakim modunu dogrula ve uygula."""
        normalized_mode = str(mode or '').strip().lower()
        if normalized_mode not in ('manual', 'auto'):
            return False, 'invalid_mode'

        if normalized_mode == 'manual':
            self.care_settings['mode'] = 'manual'
            return True, None

        profile = self._build_patient_auto_profile()
        if not profile.get('supported'):
            return False, profile.get('reason_code') or 'unsupported_profile'

        self.care_settings['mode'] = 'auto'
        return True, None

    def get_effective_slider_values(self):
        """Aktif kontrol mantiginda kullanilacak hedef slider degerlerini don."""
        with self.state_lock:
            effective_values = self.slider_values.copy()
            care_mode = self.care_settings.get('mode')

        if care_mode == 'auto':
            profile = self._build_patient_auto_profile()
            if profile.get('supported'):
                effective_values.update(profile['targets'])

        return effective_values

    def get_care_status(self):
        """UI icin bakim modu durumu ve hasta profili bilgisini don."""
        with self.state_lock:
            profile = self._build_patient_auto_profile()
            effective_values = self.get_effective_slider_values()
            care_mode = self.care_settings.get('mode', 'manual')
            patient_name = self.patient_context.get('name', '')
            patient_species = self.patient_context.get('species', '')
            patient_age = self.patient_context.get('age', '')

        return {
            'mode': care_mode,
            'auto_available': bool(profile.get('supported')),
            'manual_locked': care_mode == 'auto' and bool(profile.get('supported')),
            'profile_code': profile.get('profile_code'),
            'reason_code': profile.get('reason_code'),
            'patient_name': patient_name,
            'patient_species': patient_species,
            'patient_age': patient_age,
            'targets': {
                'sld2': effective_values.get('sld2'),
                'sld3': effective_values.get('sld3'),
                'sld12': effective_values.get('sld12'),
            },
            'bands': profile.get('bands', {})
        }
    
    def load_settings(self):
        """Ayarları JSON formatından yükle"""
        logger.info(f"🔍 Loading settings from {SETTINGS_FILE}...")
        try:
            load_result = load_settings_json(path=SETTINGS_FILE, base_dir=SCRIPT_DIR)
            settings_path = str(load_result.path)

            mismatch_status = find_settings_name_ttl(SCRIPT_DIR)
            if mismatch_status.get('has_mismatch'):
                logger.warning(
                    "⚠️  Settings filename case mismatch detected. Expected %s but found %s",
                    mismatch_status.get('expected'),
                    mismatch_status.get('unexpected_variants'),
                )

            if load_result.is_json:
                data = load_result.data
                logger.info(f"✅ JSON settings source: {settings_path}")

                with self.state_lock:
                    if "slider_values" in data:
                        # Ensure values are converted to appropriate types
                        for k, v in data["slider_values"].items():
                            try:
                                self.slider_values[k] = float(v)
                            except (ValueError, TypeError):
                                logger.warning(f"⚠️  Invalid slider value for {k}: {v}")
                        logger.info(f"✅ Slider values updated: {len(data['slider_values'])} items")

                    if "button_states" in data:
                        self.button_states.update(data["button_states"])
                        logger.info(f"✅ Button states updated: {len(data['button_states'])} items")

                    if "ai_enabled" in data and AI_AVAILABLE:
                        self.ai_enabled = data["ai_enabled"]
                        logger.info(f"🤖 AI enabled preference loaded: {self.ai_enabled}")

                    if "system_settings" in data:
                        self.system_settings.update(data["system_settings"])
                        self.system_settings.pop('soothing_audio_enabled', None)
                        self.system_settings.pop('soothing_audio_mode', None)
                        self.system_settings['fan_output_mode'] = self.get_fan_output_mode()
                        self.refresh_fan_output_mode(reapply_current_output=False)
                        logger.info("⚙️  System settings loaded")

                    if "user_profile" in data:
                        self.user_profile.update(data["user_profile"])
                        logger.info("👤 User profile loaded")

                    if "patient_context" in data:
                        self.update_patient_context(data["patient_context"])
                        logger.info("🐾 Patient context loaded")

                    if "current_patient" in data and patient_record_has_content(data["current_patient"]):
                        self.current_patient = dict(data["current_patient"])
                        logger.info("🗂️ Current patient loaded")
                    elif patient_record_has_content(self.patient_context):
                        self.current_patient.update({
                            key: value for key, value in self.patient_context.items()
                            if str(value or '').strip()
                        })
                        if patient_record_has_content(self.current_patient):
                            self.current_patient.setdefault('id', build_patient_id(self.current_patient))
                            self.current_patient.setdefault('savedAt', datetime.datetime.now().isoformat())
                            logger.info("🗂️ Current patient rebuilt from patient context")

                    if "care_settings" in data and isinstance(data["care_settings"], dict):
                        requested_mode = data["care_settings"].get("mode", "manual")
                        ok, reason = self.set_care_mode(requested_mode)
                        if ok:
                            logger.info(f"🩺 Care mode loaded: {self.care_settings['mode']}")
                        else:
                            logger.warning(f"⚠️  Stored care mode ignored: {reason}")

                logger.info("✅ Settings loaded successfully from JSON")
            elif 'non_json_content' in load_result.errors and os.path.exists(settings_path):
                with open(settings_path, "r") as f:
                    file_content = f.read().strip()

                # Eski format
                parts = file_content.split()
                logger.info(f"📄 Found old format settings file with {len(parts)} parts")
                if len(parts) >= 8:
                    # Button states (8 buton için - b9 yok)
                    try:
                        button_state = int(parts[0])
                        for i in range(8):
                            self.button_states[f"b{i+1}"] = bool(button_state & (1 << i))
                        # b9 (cooling) için varsayılan değer
                        self.button_states['b9'] = False
                    except ValueError:
                        logger.error("❌ Invalid button state in old format")

                    # Slider values
                    slider_keys = ["sld1", "sld2", "sld3", "sld4", "sld5", "sld6", "sld7", "sld8", "sld9", "sld10", "sld11", "sld12"]
                    for i, key in enumerate(slider_keys):
                        if i + 1 < len(parts):
                            try:
                                self.slider_values[key] = float(parts[i + 1])
                            except (ValueError, IndexError):
                                pass
                    logger.info("✅ Settings loaded from old format logic")
            elif load_result.is_empty:
                logger.warning(f"⚠️  Settings file {settings_path} is empty!")
                return
            else:
                logger.warning(f"⚠️  Settings file NOT FOUND: {SETTINGS_FILE}. Using defaults.")

            # GUVENLIK: UV ve Ozon butonlari her zaman kapali baslamali
            with self.state_lock:
                self.button_states["b7"] = False
                self.button_states["b8"] = False
                if not self.system_settings.get('cooling_enabled', False):
                    self.button_states["b9"] = False
                    logger.info("🔒 Cooling forced OFF at startup because feature is disabled in settings")
            logger.info("🔒 UV/Ozone forced OFF at startup (safety)")

            logger.info(f"📊 Button states loaded from settings: {self.button_states}")
            logger.info(f"📊 Slider values in memory: {self.slider_values}")

            # GPIO'ları buton durumlarına göre ayarla
            self._apply_button_states_to_gpio()
        except Exception as e:
            logger.error(f"❌ Load settings error: {e}", exc_info=True)
    
    def _apply_button_states_to_gpio(self):
        """Kaydedilmiş buton durumlarını GPIO'lara uygula"""
        if not GPIO_AVAILABLE:
            logger.info("⚠️  GPIO not available - skipping GPIO state restoration")
            return
        
        # Pin mapping - Pin değişiklikleri: b6 (Fan) PWM GPIO18, b9 (Cooling) GPIO20
        pin_map = {
            'b1': 5,   # Therapeutic Lighting
            'b2': 6,   # Nebulizer
            'b3': 13,  # Humidity Control
            'b4': 16,  # Heating Pad
            'b5': 19,  # IR Heater
            'b6': 18,  # Ventilation Fan (PWM GPIO18)
            'b7': 21,  # UV Sterilization
            'b8': 26,  # Ozone Sterilizer
            'b9': 20   # Cooling System (GPIO20)
        }
        
        logger.info("🔧 Applying saved button states to GPIO...")
        
        with self.state_lock:
            button_states_snapshot = dict(self.button_states)

        for button_name, state in button_states_snapshot.items():
            if button_name in pin_map:
                pin = pin_map[button_name]
                if button_name == 'b6':
                    try:
                        with self.state_lock:
                            self.button_states['b6_manual'] = bool(state)
                            self.fan_auto_active = False
                        self.apply_fan_output(bool(state), duty=self.get_fan_speed_percent(), source='restore')
                        status = "ON" if state else "OFF"
                        logger.info(f"  -> {button_name} (fan output): {status}")
                    except Exception as e:
                        logger.error(f"  -> {button_name} (fan output): ERROR - {e}")
                    continue

                # Active-low relay: LOW = ON, HIGH = OFF
                gpio_val = GPIO.LOW if state else GPIO.HIGH
                try:
                    GPIO.output(pin, gpio_val)
                    with self.state_lock:
                        self.gpio_output_states[button_name] = state
                    status = "ON" if state else "OFF"
                    logger.info(f"  → {button_name} (GPIO {pin}): {status}")
                except Exception as e:
                    logger.error(f"  → {button_name} (GPIO {pin}): ERROR - {e}")
        
        logger.info("✅ GPIO states restored from saved settings")
    
    def save_settings(self):
        """Ayarları JSON formatında dosyaya kaydet"""
        try:
            with self.state_lock:
                self.system_settings.pop('soothing_audio_enabled', None)
                self.system_settings.pop('soothing_audio_mode', None)
                # UV ve Ozon butonlarını herzaman kapalı kaydet (güvenlik)
                button_states_to_save = self.button_states.copy()
                button_states_to_save["b7"] = False  # UV Sterilization
                button_states_to_save["b8"] = False  # Ozone Sterilization
                if not self.system_settings.get('cooling_enabled', False):
                    button_states_to_save["b9"] = False  # Cooling should not persist while feature is disabled

                settings_data = {
                    "slider_values": copy.deepcopy(self.slider_values),
                    "button_states": button_states_to_save,
                    "ai_enabled": self.ai_enabled,
                    "system_settings": copy.deepcopy(self.system_settings),
                    "user_profile": copy.deepcopy(self.user_profile),
                    "patient_context": copy.deepcopy(self.patient_context),
                    "current_patient": copy.deepcopy(self.current_patient),
                    "care_settings": copy.deepcopy(self.care_settings)
                }

            write_result = save_settings_json(settings_data, path=SETTINGS_FILE)
            if not write_result.success:
                logger.error(f"Save settings error: {write_result.errors}")
                return False

            logger.debug(f"Settings file saved to: {write_result.path}")

            logger.info("✅ Settings saved (UV/Ozone forced OFF)")
            
            # Sync to Firebase
            if self.firebase_manager:
                self.firebase_manager.sync_controls(self.button_states, self.slider_values)
                logger.debug("✅ Firebase controls synced after save")
                
            return True
        except Exception as e:
            logger.error(f"Save settings error: {e}")
            return False

    def schedule_settings_save(self, delay=None, reason='runtime'):
        """Debounce repeated settings writes to reduce disk churn."""
        if delay is None:
            delay = self.settings_save_delay_sec

        delay = max(0.0, float(delay))

        def _save_task():
            with self.settings_save_lock:
                self.settings_save_timer = None
            self.save_settings()

        with self.settings_save_lock:
            if self.settings_save_timer is not None:
                self.settings_save_timer.cancel()
            self.settings_save_timer = threading.Timer(delay, _save_task)
            self.settings_save_timer.daemon = True
            self.settings_save_timer.start()
        logger.debug("Scheduled debounced settings save (%s, delay=%ss)", reason, delay)

    def flush_scheduled_settings_save(self):
        """Force any pending debounced settings write to disk immediately."""
        timer = None
        with self.settings_save_lock:
            timer = self.settings_save_timer
            self.settings_save_timer = None

        if timer is not None:
            timer.cancel()
            self.save_settings()
            return True
        return False
    
    def start_threads(self):
        """Background thread'leri başlat"""
        self.running = True
        
        # Sensor thread
        def sensor_loop():
            while self.running:
                self.read_sensors()
                if self.ai_vitals_logger:
                    self.ai_vitals_logger.maybe_run_maintenance()
                
                # WebSocket ile sensor verilerini gönder (rate limiting)
                try:
                    snapshot = self.snapshot_runtime_state()
                    logger.debug(f"DEBUG: Emitting sensor_update: {snapshot['sensor_data']}")
                    socketio.emit('sensor_update', {
                        'type': 'sensor_update',
                        'sensors': snapshot['sensor_data']
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
            last_ai_loop_state = None
            no_frame_log_count = 0  # Prevent log spam

            while self.running and self.ai_manager:
                try:
                    # Skip if AI not enabled
                    if not self.ai_enabled:
                        time.sleep(1)
                        continue

                    ai_data = self.ai_manager.get_update()
                    
                    # Log AI data status
                    if ai_data:
                        vitals = ai_data.get('vitals', {})
                        vision_status = ai_data.get('vision', {})
                        logger.debug(
                            "🤖 AI data: status=%s, bpm=%s, conf=%s, activity=%s, frame=%s",
                            vitals.get('status', 'N/A'),
                            vitals.get('respiration_bpm', 'N/A'),
                            vitals.get('confidence', 'N/A'),
                            vision_status.get('activity', 'N/A'),
                            'yes' if ai_data.get('frame') else 'no'
                        )
                    
                    if (
                        self.ai_vitals_logger
                        and self.system_settings.get('logging_enabled', True)
                        and ai_data
                    ):
                        logged = self.ai_vitals_logger.log_if_changed(
                            ai_data,
                            patient_context=self.get_ai_logging_patient_context(),
                        )
                        if logged:
                            logger.info("📝 AI vital logged to database")

                    if ai_data:
                        self._log_ai_behavior_if_needed(ai_data)

                    has_frame = bool(ai_data and ai_data.get('frame') is not None)
                    vision_running = bool(self.ai_manager.vision.running)
                    current_ai_loop_state = (has_frame, vision_running)

                    if current_ai_loop_state != last_ai_loop_state:
                        logger.info(
                            "🎯 AI loop state changed: has_frame=%s, vision_running=%s",
                            has_frame,
                            vision_running,
                        )
                        last_ai_loop_state = current_ai_loop_state

                    if ai_data and ai_data.get('frame'):
                        socketio.emit('ai_update', ai_data)
                        logger.debug(f"✅ AI frame emitted (size: {len(ai_data.get('frame', ''))} bytes)")
                        no_frame_log_count = 0  # Reset counter
                    else:
                        # Log every 30 seconds to prevent spam but still provide visibility
                        no_frame_log_count += 1
                        if no_frame_log_count % 30 == 0:
                            logger.warning(
                                "⚠️  AI update skipped - no frame (vision_running=%s, ai_enabled=%s). "
                                "Check camera connection and ensure animal is in view.",
                                vision_running,
                                self.ai_enabled
                            )
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
                    with self.state_lock:
                        self.control_logic()
                    # WebSocket ile button durumlarını VE GPIO output state'lerini gönder
                    # Sync to all local clients
                    snapshot = self.snapshot_runtime_state()
                    socketio.emit('button_update', {
                        'type': 'button_update',
                        'buttons': snapshot['button_states'],
                        'gpio_outputs': snapshot['gpio_output_states']
                    })
                time.sleep(1)  # 1 saniyede bir
        
        self.sensor_thread = threading.Thread(target=sensor_loop, daemon=True)
        self.control_thread = threading.Thread(target=control_loop, daemon=True)
        
        self.sensor_thread.start()
        self.control_thread.start()

        if self.power_diag_available:
            # First snapshot at startup so boot-time issues land in the log immediately.
            startup_power_snapshot = self._collect_power_diagnostics()
            self.last_power_diag = startup_power_snapshot
            self._log_power_diagnostics_if_needed(startup_power_snapshot, force=True)

            self.power_diag_thread = threading.Thread(target=self.power_diagnostic_loop, daemon=True)
            self.power_diag_thread.start()

        if self.kiosk_watchdog_available:
            self.kiosk_watchdog_thread = threading.Thread(target=self.kiosk_watchdog_loop, daemon=True)
            self.kiosk_watchdog_thread.start()

        if self.ai_manager:
            if self.ai_enabled:
                ai_started, ai_message, ai_health = self._set_ai_runtime_enabled(True, source='start_threads')
                if not ai_started:
                    logger.warning("⚠️ AI manager could not start; disabling AI until user retries")
                    logger.debug("🧠 AI startup result: %s / %s", ai_message, ai_health)
            if not self.ai_thread or not self.ai_thread.is_alive():
                self.ai_thread = threading.Thread(target=ai_loop, daemon=True)
                self.ai_thread.start()
                logger.info("🧠 AI loop thread started")
            else:
                logger.debug("🧠 AI loop thread already running")
        
        logger.info("✅ Background threads started")
    
    def stop_threads(self):
        """Thread'leri durdur"""
        self.running = False

        for thread_attr in ('sensor_thread', 'control_thread', 'power_diag_thread', 'kiosk_watchdog_thread'):
            thread = getattr(self, thread_attr, None)
            if thread:
                thread.join(timeout=2)
                setattr(self, thread_attr, None)

        if self.ai_manager:
            self._set_ai_runtime_enabled(False, source='stop_threads')
            if self.ai_thread:
                self.ai_thread.join(timeout=2)
                self.ai_thread = None

        logger.info("✅ Background threads stopped")
    
    def cleanup(self):
        """Temizlik işlemleri"""
        global GPIO_AVAILABLE
        
        self.stop_threads()
        self.flush_scheduled_settings_save()
        self.save_settings()
        self.stop_fan_pwm()
        if GPIO_AVAILABLE:
            GPIO.cleanup()
        logger.info("✅ Cleanup completed")

# Global server instance
kuvoz_server = KuvozServer()
wifi_wps_service = WifiWPSService(
    logger=logger,
    socketio=socketio,
    udhcpc_script=UDHCPC_SCRIPT,
    get_all_ips=get_all_ips,
)

register_http_routes(
    app,
    socketio=socketio,
    kuvoz_server=kuvoz_server,
    logger=logger,
    docs_dir=DOCS_DIR,
    get_help_docs_index=_get_help_docs_index,
    load_patient_records=lambda: load_patient_records(PATIENTS_FILE),
    save_patient_records=lambda patients: save_patient_records(PATIENTS_FILE, PATIENTS_DIR, patients),
    merge_current_patient_record=merge_current_patient_record,
    build_patient_id=build_patient_id,
)
basic_socket_helpers = register_basic_socket_routes(
    socketio,
    kuvoz_server=kuvoz_server,
    logger=logger,
    ai_available=AI_AVAILABLE,
)
handle_update_slider_logic = basic_socket_helpers['handle_update_slider_logic']
settings_socket_helpers = register_settings_socket_routes(
    socketio,
    kuvoz_server=kuvoz_server,
    logger=logger,
    gpio_available=GPIO_AVAILABLE,
    dht_available=DHT_AVAILABLE,
    oxygen_available=OXYGEN_AVAILABLE,
    co2_available=CO2_AVAILABLE,
    ai_available=AI_AVAILABLE,
    logging_available=LOGGING_AVAILABLE,
    settings_file=SETTINGS_FILE,
    get_local_ip=get_local_ip,
    get_git_version_info=lambda: get_git_version_info(script_dir=SCRIPT_DIR, logger=logger),
    get_git_update_diagnostics=lambda: get_git_update_diagnostics(script_dir=SCRIPT_DIR, logger=logger),
    build_patient_id=build_patient_id,
    patient_record_has_content=patient_record_has_content,
)
handle_save_settings_logic = settings_socket_helpers['handle_save_settings_logic']
register_wifi_socket_routes(
    socketio,
    logger=logger,
    get_all_ips=get_all_ips,
    start_wps_pairing=wifi_wps_service.start_pairing,
)
register_tailscale_socket_routes(
    socketio,
    logger=logger,
    task_manager=task_manager,
    qrcode_module=qrcode if QRCODE_AVAILABLE else None,
    qrcode_available=QRCODE_AVAILABLE,
)
register_system_socket_routes(
    socketio,
    kuvoz_server=kuvoz_server,
    logger=logger,
    ai_available=AI_AVAILABLE,
    gpio_available=GPIO_AVAILABLE,
    script_dir=SCRIPT_DIR,
    task_manager=task_manager,
    perform_disk_cleanup=perform_disk_cleanup,
    get_git_version_info=lambda: get_git_version_info(script_dir=SCRIPT_DIR, logger=logger),
    get_git_update_diagnostics=lambda: get_git_update_diagnostics(script_dir=SCRIPT_DIR, logger=logger),
    classify_git_update_error=classify_git_update_error,
    handle_update_slider_logic=handle_update_slider_logic,
    handle_save_settings_logic=handle_save_settings_logic,
)
register_monitoring_routes(
    app,
    kuvoz_server=kuvoz_server,
    logger=logger,
    ai_vitals_logger_cls=AIVitalsLogger,
    behavior_logger_cls=BehaviorLogger,
    script_dir=SCRIPT_DIR,
    settings_file=SETTINGS_FILE,
)

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
