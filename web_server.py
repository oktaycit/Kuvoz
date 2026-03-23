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
import os
import sys
import logging
import socket
import subprocess
import shutil
import re
import base64
from io import BytesIO
from disk_cleanup_utils import perform_disk_cleanup

# Ayar dosyası için mutlak yol (servis hangi dizinden başlatılırsa başlatılsın çalışır)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(SCRIPT_DIR, "failure.dat")
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

def _patient_record_has_content(record):
    if not isinstance(record, dict):
        return False

    keys = (
        'name', 'species', 'breed', 'age', 'weight',
        'ownerName', 'diagnosis', 'admissionDate', 'currentTreatment'
    )
    return any(str(record.get(key) or '').strip() for key in keys)

def _build_patient_id(record):
    admission_date = str(record.get('admissionDate') or '').strip()
    name = re.sub(r'\s+', '_', str(record.get('name') or '').strip())
    fallback = str(record.get('savedAt') or '').replace(':', '-').replace('.', '-')
    base = f"{admission_date}_{name}".strip('_')
    return base or fallback or f"patient_{int(time.time())}"

def _ensure_patient_storage():
    os.makedirs(PATIENTS_DIR, exist_ok=True)

def _load_patient_records():
    if not os.path.exists(PATIENTS_FILE):
        return []

    with open(PATIENTS_FILE, 'r', encoding='utf-8') as f:
        patients = json.load(f)

    return patients if isinstance(patients, list) else []

def _save_patient_records(patients):
    _ensure_patient_storage()
    with open(PATIENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(patients, f, ensure_ascii=False, indent=2)

def _merge_current_patient_record(patients, current_patient):
    merged = list(patients or [])
    if not _patient_record_has_content(current_patient):
        return merged

    record = dict(current_patient)
    record.setdefault('id', _build_patient_id(record))
    record.setdefault('savedAt', datetime.datetime.now().isoformat())

    existing_index = next((i for i, patient in enumerate(merged) if patient.get('id') == record['id']), None)
    if existing_index is not None:
        merged[existing_index] = {**merged[existing_index], **record}
    elif not record.get('discharged', False):
        merged.insert(0, record)

    return merged

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

# WPS ve DHCP akışlarında tekrarlı tetiklemeyi engelle
WPS_LOCK = threading.Lock()
WPS_IN_PROGRESS = False
WPS_LAST_START_TS = 0.0
WPS_MIN_INTERVAL_SEC = 35
WIFI_DHCP_LOCK = threading.Lock()
WIFI_DHCP_IN_PROGRESS = False

# Arka plan görev yöneticisi (Özellikle Tailscale gibi uzun süren işlemler için)
class BackgroundTaskManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._active_task = None
        self._start_time = 0

    def start_task(self, task_name):
        with self._lock:
            if self._active_task:
                # 10 dakikadan uzun süren görevleri "takılmış" sayıp temizleyelim
                if time.time() - self._start_time > 600:
                    logger.warning(f"⚠️ Stale task detected: {self._active_task}. Forcing start of {task_name}")
                    self._active_task = task_name
                    self._start_time = time.time()
                    return True
                return False
            self._active_task = task_name
            self._start_time = time.time()
            return True

    def end_task(self):
        with self._lock:
            self._active_task = None
            self._start_time = 0

    @property
    def is_busy(self):
        return self._active_task is not None

    @property
    def current_task(self):
        return self._active_task

# Global görev yöneticisi örneği
task_manager = BackgroundTaskManager()

def _begin_wps_session():
    """Reserve a single WPS slot and apply minimum trigger interval guard."""
    global WPS_IN_PROGRESS, WPS_LAST_START_TS
    now = time.time()
    with WPS_LOCK:
        if WPS_IN_PROGRESS:
            return False, 'WPS işlemi zaten devam ediyor. Lütfen 30-40 saniye bekleyin.'
        if now - WPS_LAST_START_TS < WPS_MIN_INTERVAL_SEC:
            remain = int(max(1, WPS_MIN_INTERVAL_SEC - (now - WPS_LAST_START_TS)))
            return False, f'WPS çok sık tetiklendi. {remain}s sonra tekrar deneyin.'
        WPS_IN_PROGRESS = True
        WPS_LAST_START_TS = now
    return True, None

def _end_wps_session():
    global WPS_IN_PROGRESS
    with WPS_LOCK:
        WPS_IN_PROGRESS = False

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

def get_git_version_info():
    """
    Get current git commit hash and branch information.
    
    Returns:
        dict: {'hash': str, 'branch': str} or {'hash': 'Unknown', 'branch': 'Unknown'} on error
    """
    try:
        # Get short commit hash (7 characters)
        hash_result = subprocess.run(
            ['git', 'rev-parse', '--short=7', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=SCRIPT_DIR
        )
        
        git_hash = hash_result.stdout.strip() if hash_result.returncode == 0 else 'Unknown'
        
        # Get current branch name
        branch_result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=SCRIPT_DIR
        )
        
        git_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else 'Unknown'
        
        return {
            'hash': git_hash,
            'branch': git_branch
        }
    except Exception as e:
        logger.warning(f"Failed to get git version info: {e}")
        return {
            'hash': 'Unknown',
            'branch': 'Unknown'
        }

def _parse_git_status_porcelain(output):
    dirty_entries = []
    for raw_line in (output or "").splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        path = line[3:] if len(line) > 3 else line
        if " -> " in path:
            path = path.split(" -> ", 1)[-1]
        dirty_entries.append({
            'status': line[:2].strip() or '??',
            'path': path
        })
    return dirty_entries

def get_git_update_diagnostics():
    """Return local git state information for update UI and troubleshooting."""
    git_info = get_git_version_info()
    diagnostics = {
        'branch': git_info['branch'],
        'hash': git_info['hash'],
        'blocked': False,
        'reasons': [],
        'notes': [],
        'dirty_files': [],
        'upstream_ref': ''
    }

    try:
        status_result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=SCRIPT_DIR
        )
        if status_result.returncode == 0:
            dirty_entries = _parse_git_status_porcelain(status_result.stdout)
            diagnostics['dirty_files'] = [entry['path'] for entry in dirty_entries]
            if dirty_entries:
                diagnostics['blocked'] = True
                diagnostics['reasons'].append('Git çalışma ağacında yerel değişiklikler var.')
        else:
            diagnostics['blocked'] = True
            diagnostics['reasons'].append('Git durum bilgisi okunamadı.')

        branch_name = diagnostics['branch']
        if branch_name in ('HEAD', 'Unknown', ''):
            diagnostics['blocked'] = True
            diagnostics['reasons'].append('Aktif branch belirlenemedi (detached HEAD veya git hatası).')

        upstream_result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=SCRIPT_DIR
        )
        if upstream_result.returncode == 0:
            diagnostics['upstream_ref'] = upstream_result.stdout.strip()
        elif branch_name not in ('HEAD', 'Unknown', ''):
            diagnostics['notes'].append(f'Bu branch için upstream ayarı bulunamadı. Update origin/{branch_name} üzerinden denenecek.')
    except Exception as e:
        diagnostics['blocked'] = True
        diagnostics['reasons'].append(f'Git teşhisi alınamadı: {str(e)}')

    if not diagnostics['blocked'] and not diagnostics['reasons']:
        diagnostics['notes'].append('Güncellemeyi engelleyen yerel bir durum görünmüyor.')

    return diagnostics

def _classify_git_update_error(output, current_branch):
    text = (output or '').strip()
    lower = text.lower()

    if (
        'could not resolve host' in lower or
        'failed to connect' in lower or
        'network is unreachable' in lower or
        'connection timed out' in lower or
        'operation timed out' in lower
    ):
        return 'network', '❌ İnternet bağlantısı veya DNS erişimi yok.', text

    if "couldn't find remote ref" in lower or 'remote ref does not exist' in lower:
        return 'missing_remote_branch', f'❌ origin/{current_branch} branch’i bulunamadı.', text

    if 'authentication failed' in lower or 'permission denied' in lower:
        return 'permission', '❌ GitHub erişim yetkisi başarısız oldu.', text

    if 'not possible to fast-forward' in lower:
        return 'diverged', '❌ Yerel branch origin ile ayrışmış. Önce manuel olarak birleştirme veya geri alma gerekiyor.', text

    return 'unknown', f'Güncelleme hatası: {text or "Bilinmeyen hata"}', text

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
        self.outChannels = [5, 6, 13, 16, 19, 20, 21, 26, 12]  # 12 = Cooling (b9)
        self.touch_bt = [5, 20, 21]
        self.pinDht = 15  # GPIO 15 (Physical Pin 10)
        self.pinWps = 4   # GPIO 4 (Physical Pin 7) for WPS button

        # DHT sensor type - auto-detect from environment or command line
        # Priority: 1) Command line arg, 2) Environment variable, 3) Default DHT22
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

        # System Settings (features can be toggled)
        self.system_settings = {
            'cooling_enabled': False,
            'dht_enabled': True,
            'oxygen_enabled': True,
            'co2_enabled': True,
            'ai_enabled': False,
            'logging_enabled': True,
            'fan_output_mode': DEFAULT_FAN_OUTPUT_MODE
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
        
        # DHT sensor quality filter - moving average for noisy readings
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

        self.ai_vitals_logger = None
        if AI_VITAL_LOGGING_AVAILABLE:
            # AI vital logger - daha sık kayıt için ayarlandı
            # min_interval: 10 saniye (önceki 15s)
            # heartbeat_interval: 60 saniye (önceki 0 = kapalı)
            # Bu sayede her durumda en azından her dakika kayıt yapılacak
            self.ai_vitals_logger = AIVitalsLogger(
                db_path="data/ai_vitals.db",
                min_interval=10,
                heartbeat_interval=60,  # Her 60 saniyede bir heartbeat (önceki: 0/kapalı)
            )
        
        self.init_hardware()
        self.restore_last_sensor_snapshot()
        self.load_settings()
        self.apply_runtime_sensor_settings()
        
        # Start AI if it was enabled in saved settings
        if self.ai_enabled and self.ai_manager:
            try:
                started = self.ai_manager.start()
                if started:
                    logger.info("🤖 AI Manager auto-started (user preference from settings)")
                else:
                    logger.warning("⚠️ AI auto-start skipped because the camera could not be initialized")
                    self.ai_enabled = False
            except Exception as e:
                logger.error(f"Failed to auto-start AI Manager: {e}")
                self.ai_enabled = False

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
                'b5': 19, 'b6': 20, 'b7': 21, 'b8': 26,
                'b9': 12
            }
            if key in pin_map:
                pin = pin_map[key]
                gpio_val = GPIO.LOW if state else GPIO.HIGH
                self.safe_gpio_output(pin, gpio_val)
                
            # Sync to local Web UI
            socketio.emit('button_update', {'id': key, 'status': state, 'buttons': self.button_states})
            
        elif key in self.slider_values:
            # Slider update
            try:
                val = float(value)
                self.slider_values[key] = val
                # Sync to all local clients
                socketio.emit('slider_update', {'id': key, 'value': val, 'sliders': self.slider_values})

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
        
        return {
            'dht_library': DHT_LIBRARY,
            'gpio_available': True,  # Always true - simulation mode works too
            'dht_available': DHT_AVAILABLE,
            'oxygen_available': has_oxygen_data,  # Gerçek sensör VEYA tahmini
            'oxygen_sensor_available': self.oxygen_sensor_available,
            'oxygen_estimated': has_oxygen_data and not self.oxygen_sensor_available,
            'co2_available': has_co2_data,  # SCD41'den gerçek okuma varsa
            'co2_sensor_available': self.co2_sensor_available,
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
        patient = {}
        if isinstance(self.current_patient, dict):
            patient = dict(self.current_patient)

        if not _patient_record_has_content(patient) and isinstance(self.patient_context, dict):
            if _patient_record_has_content(self.patient_context):
                patient = dict(self.patient_context)

        if _patient_record_has_content(patient):
            patient.setdefault('id', _build_patient_id(patient))

        return patient

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
        if isinstance(mode, str):
            normalized = mode.strip().lower()
            if normalized in ('pwm', 'mosfet', 'gpio18', 'p18'):
                return 'pwm'
        return 'relay'

    def get_fan_output_mode(self):
        """Return the currently selected fan output mode."""
        return self.normalize_fan_output_mode(self.system_settings.get('fan_output_mode'))

    def is_fan_pwm_mode(self):
        """True when fan output should use the PWM/MOSFET path."""
        return self.get_fan_output_mode() == 'pwm'

    def refresh_fan_output_mode(self, reapply_current_output=True):
        """Apply selected fan output mode immediately."""
        mode = self.get_fan_output_mode()
        self.system_settings['fan_output_mode'] = mode

        if mode == 'pwm':
            self.initialize_fan_pwm(force_recreate=True)
            self.safe_gpio_output(20, GPIO.HIGH)
        else:
            self.stop_fan_pwm()

        if reapply_current_output:
            fan_enabled = bool(self.button_states.get('b6'))
            if fan_enabled:
                self.apply_fan_output(True, duty=self.get_fan_speed_percent(), source='mode_refresh')
            else:
                self.apply_fan_output(False, source='mode_refresh')

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
        if sid and sid in self.active_connections:
            self.active_connections[sid]['last_seen'] = now

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

        probe_errors = {}
        candidate_addresses = (ADDRESS_3, ADDRESS_0, ADDRESS_1, ADDRESS_2)

        for address in candidate_addresses:
            try:
                sensor = DFRobot_Oxygen_IIC(IIC_MODE, address)
                reading = sensor.get_oxygen_data(sample_count)
                if reading is not None and 0 <= reading <= 100:
                    return sensor, address, reading, probe_errors
                probe_errors[f"0x{address:02X}"] = f"invalid reading: {reading}"
            except Exception as exc:
                probe_errors[f"0x{address:02X}"] = f"{type(exc).__name__}: {exc}"

        return None, None, None, probe_errors

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
        
        # Oxygen sensor - İlk açılışta test et
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
            logger.info("📊 Oxygen sensor added to dashboard")
            logger.info("💨 Ozone mode: OXYGEN-BASED (intelligent control)")
        else:
            logger.info("📊 Oxygen sensor excluded from dashboard")
            logger.info("💨 Ozone mode: TIMED (fixed interval control)")

        # CO2 sensörü başlat ve test et (SCD41)
        if CO2_AVAILABLE:
            try:
                logger.info("🔄 Initializing SCD41 sensor...")
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
                    logger.info(f"✅ SCD41 tested: CO2={test_data['co2']:.0f}ppm, "
                              f"Temp={test_data['temperature']:.1f}°C, "
                              f"Hum={test_data['humidity']:.0f}%")
                else:
                    logger.error("❌ SCD41 test failed - no valid data")
                    self.co2_sensor = None
                    self.co2_sensor_available = False
                    logger.info("🔧 System will continue without SCD41 (DHT will be used)")
                    
            except Exception as e:
                logger.error(f"❌ SCD41 init/test error: {e}")
                self.co2_sensor = None
                self.co2_sensor_available = False
                logger.info("🔧 System will continue without SCD41 (DHT will be used)")
        else:
            logger.info("ℹ️  SCD41 library not available (DHT will be used)")
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

        reserved_pins = set(self.outChannels + [self.pinDht, self.pinWps, 2, 3])
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
        sensor = self.sensor_data.get(sensor_name) or {}
        value = sensor.get('value')
        if value in (None, '--', ''):
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def should_run_humidity_purge(self, effective_sliders=None):
        """Return True when excess humidity should trigger ventilation."""
        if effective_sliders is None:
            effective_sliders = self.get_effective_slider_values()

        if not self.button_states.get('b3'):
            self.humidity_purge_active = False
            return False

        hum = self._get_sensor_numeric_value('humidity')
        if hum is None:
            self.humidity_purge_active = False
            return False

        try:
            hum_target = float(effective_sliders.get('sld2'))
        except (TypeError, ValueError):
            self.humidity_purge_active = False
            return False

        previous_state = self.humidity_purge_active
        if previous_state:
            active = hum > (hum_target + self.HUMIDITY_PURGE_OFF_DELTA)
        else:
            active = hum >= (hum_target + self.HUMIDITY_PURGE_ON_DELTA)

        if active != previous_state:
            if active:
                logger.info(
                    "💨 Nem purgesi başladı - Nem %.1f%%, hedef %.1f%%",
                    hum,
                    hum_target,
                )
            else:
                logger.info(
                    "💨 Nem purgesi durdu - Nem %.1f%%, hedef %.1f%%",
                    hum,
                    hum_target,
                )

        self.humidity_purge_active = active
        return active

    def get_fan_speed_percent(self, effective_sliders=None):
        """Return automatic fan PWM duty cycle derived from climate demand."""
        if effective_sliders is None:
            effective_sliders = self.get_effective_slider_values()

        base_duty = _clamp(self.fan_pwm_heater_min_duty - 10.0, 20.0, 100.0)
        duty = base_duty

        heater_active = (
            self.gpio_output_states.get('b4') is True or
            self.gpio_output_states.get('b5') is True
        )
        cooling_active = self.gpio_output_states.get('b9') is True
        cooling_requested = bool(self.button_states.get('b9')) or cooling_active

        if heater_active:
            duty = max(duty, self.fan_pwm_heater_min_duty)

        temp = self._get_sensor_numeric_value('temperature')
        hum = self._get_sensor_numeric_value('humidity')

        try:
            temp_target = float(effective_sliders.get('sld3'))
        except (TypeError, ValueError):
            temp_target = None

        try:
            hum_target = float(effective_sliders.get('sld2'))
        except (TypeError, ValueError):
            hum_target = None

        try:
            cooling_target = float(effective_sliders.get('sld12', 0))
        except (TypeError, ValueError):
            cooling_target = 0.0

        if temp is not None and temp_target is not None and temp > temp_target:
            duty = max(
                duty,
                _clamp(self.fan_pwm_heater_min_duty + ((temp - temp_target) * 18.0), self.fan_pwm_heater_min_duty, 95.0)
            )

        if temp is not None and cooling_requested and cooling_target > 0:
            if temp > cooling_target:
                duty = max(duty, _clamp(45.0 + ((temp - cooling_target) * 18.0), 45.0, 100.0))
            elif cooling_active:
                duty = max(duty, 45.0)

        if hum is not None and hum_target is not None and hum > hum_target:
            duty = max(duty, _clamp(base_duty + ((hum - hum_target) * 2.5), base_duty, 90.0))

        if self.humidity_purge_active:
            duty = max(duty, 45.0)

        return round(_clamp(duty, 20.0, 100.0), 1)

    def apply_fan_output(self, enabled, duty=None, source='manual'):
        """Drive fan output using the selected output mode."""
        if not self.is_fan_pwm_mode():
            relay_state = GPIO.LOW if enabled else GPIO.HIGH
            return self.safe_gpio_output(20, relay_state)

        if not self.fan_pwm_available and not self.initialize_fan_pwm(force_recreate=True):
            self.safe_gpio_output(20, GPIO.HIGH)
            self.gpio_output_states['b6'] = None if enabled else False
            return False

        if enabled:
            if duty is None:
                applied_duty = self.get_fan_speed_percent()
            else:
                try:
                    applied_duty = _clamp(float(duty), 20.0, 100.0)
                except (TypeError, ValueError):
                    applied_duty = self.get_fan_speed_percent()
        else:
            applied_duty = 0.0

        if not self.check_gpio_status():
            self.safe_gpio_output(20, GPIO.HIGH)
            self.gpio_output_states['b6'] = None
            return False

        if self.fan_pwm is None and not self.initialize_fan_pwm(force_recreate=True):
            self.safe_gpio_output(20, GPIO.HIGH)
            self.gpio_output_states['b6'] = None if enabled else False
            return False

        try:
            self.safe_gpio_output(20, GPIO.HIGH)
            with self.fan_pwm_lock:
                self.fan_pwm.ChangeDutyCycle(applied_duty)
            self.fan_pwm_duty = applied_duty
            self.gpio_output_states['b6'] = enabled and applied_duty > 0
            logger.debug(
                "🌬️ Fan PWM updated: enabled=%s duty=%.1f source=%s",
                enabled,
                applied_duty,
                source,
            )
            return True
        except Exception as e:
            logger.error(f"Fan PWM output error: {e}")
            self.gpio_output_states['b6'] = None
            return False

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
        """Get button name (b1-b9) by GPIO pin number"""
        pin_to_button = {
            5: 'b1',   # Therapeutic Lighting
            6: 'b2',   # Nebulizer
            13: 'b3',  # Humidity Control
            16: 'b4',  # Heating Pad
            19: 'b5',  # IR Heater
            20: 'b6',  # Ventilation Fan
            21: 'b7',  # UV Sterilization
            26: 'b8',  # Ozone Sterilizer
            12: 'b9'   # Cooling System
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
                # ANI SIÇRAMA FİLTRESİ: Son geçerli değerden 5°C'den fazla fark varsa reddet
                elif abs(temp - self.last_valid_temp) > 5.0:
                    corrected_temp = self.last_valid_temp
                    temp_corrected = True
                    logger.warning(f"⚠️  DHT TEMP SPIKE REJECTED: {temp:.1f}°C → {corrected_temp:.1f}°C (diff: {abs(temp - self.last_valid_temp):.1f}°C > 5°C threshold)")
        else:
            # Strateji 2: İlk okuma - sadece makul aralık kontrolü
            logger.debug(f"  First temp read, checking if {temp:.1f}°C needs correction (half={half_temp:.1f}°C)")
            if temp > 35 and 15 <= half_temp <= 30:
                corrected_temp = half_temp
                temp_corrected = True
                logger.warning(f"⚠️  DHT TEMP INIT: {temp:.1f}°C → {corrected_temp:.1f}°C (>35°C, no history)")
        
        # ========== NEM FİLTRESİ ==========
        half_hum = hum / 2
        
        # Strateji 1: Son geçerli değerle oran kontrolü (EN GÜVENİLİR)
        if self.last_valid_humidity is not None:
            # Division by zero koruması
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
            logger.info(f"🔧 DHT Filter Output: {corrected_temp:.1f}°C, {corrected_hum:.0f}%")
        
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
        if temp is None or hum is None:
            return temp, hum
        
        # Yeni okumaları listeye ekle
        self.temp_readings.append(temp)
        self.humidity_readings.append(hum)
        
        # Pencere boyutunu sınırla
        if len(self.temp_readings) > self.moving_avg_window:
            self.temp_readings.pop(0)
        if len(self.humidity_readings) > self.moving_avg_window:
            self.humidity_readings.pop(0)
        
        # Hareketli ortalama hesapla
        avg_temp = sum(self.temp_readings) / len(self.temp_readings)
        avg_hum = sum(self.humidity_readings) / len(self.humidity_readings)
        
        # İlk birkaç okumada yeterli veri yoksa ham değer dön
        if len(self.temp_readings) < 2:
            return temp, hum
        
        # Debug: Yumuşatma etkisini göster
        if abs(temp - avg_temp) > 2.0:
            logger.debug(f"📊 Moving avg smoothing: temp {temp:.1f}°C → {avg_temp:.1f}°C (window: {self.temp_readings})")
        if abs(hum - avg_hum) > 5.0:
            logger.debug(f"💧 Moving avg smoothing: humidity {hum:.0f}% → {avg_hum:.0f}% (window: {self.humidity_readings})")
        
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
            
            # Temperature control with hysteresis (b4 - pin 16)
            # Only control if function is enabled by user
            if self.button_states['b4']:
                if self.sensor_data['temperature']['value'] != '--':
                    temp = float(self.sensor_data['temperature']['value'])
                    temp_target = effective_sliders['sld3']

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
                    hum_target = effective_sliders['sld2']

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
                    ir_temp_target = effective_sliders['sld3']  # Using sld3 for IR temp target

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
                    temp_target = effective_sliders['sld3']
                    # Check if heater is currently on (in hysteresis zone, check GPIO state)
                    if temp < (temp_target + self.TEMP_HYSTERESIS):
                        carbon_heater_active = self.gpio_output_states.get('b4', False) == True

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

            # Cooling control with hysteresis and heating conflict prevention (b9 - pin 12)
            # SAFETY: Cooling and heating MUST NOT run simultaneously
            # MODE: If sld12 > 0 → Auto mode (hysteresis control), If sld12 = 0 → Manual ON/OFF
            # Only control if function is enabled by user
            
            # Track cooling state changes only (not every iteration)
            # Removed excessive debug logging
            
            if self.button_states['b9']:
                # Check if any heater is active (conflict prevention)
                heater_active = (self.button_states['b4'] or self.button_states['b5'])
                
                if heater_active:
                    # Safety: Disable cooling if heaters are on
                    self.safe_gpio_output(12, GPIO.HIGH)  # OFF
                    logger.warning("❄️  Cooling disabled - Heaters are active (safety interlock)")
                else:
                    # AUTO MODE ONLY: Temperature-based control with hysteresis
                    # Requires: Valid target temperature (sld12 > 0) AND working sensor
                    cooling_target = effective_sliders.get('sld12', 0)
                    
                    if cooling_target > 0 and self.sensor_data['temperature']['value'] != '--':
                        # Temperature-based control with hysteresis
                        temp = float(self.sensor_data['temperature']['value'])

                        # Hysteresis control: prevents relay chattering
                        # Track previous state to log only changes
                        prev_cooling_state = self.gpio_output_states.get('b9', False)
                        
                        if temp > (cooling_target + self.COOLING_HYSTERESIS):
                            # Above target + hysteresis → Turn cooling ON
                            self.safe_gpio_output(12, GPIO.LOW)
                            if not prev_cooling_state:  # Only log if state changed
                                logger.info(f"❄️  Cooling ON - Temp {temp}°C > Target+Hyst {cooling_target+self.COOLING_HYSTERESIS}°C")
                        elif temp < (cooling_target - self.COOLING_HYSTERESIS):
                            # Below target - hysteresis → Turn cooling OFF
                            self.safe_gpio_output(12, GPIO.HIGH)
                            if prev_cooling_state:  # Only log if state changed
                                logger.info(f"❄️  Cooling OFF - Temp {temp}°C < Target-Hyst {cooling_target-self.COOLING_HYSTERESIS}°C")
                        # else: In hysteresis zone → Maintain current state (no change)
                    else:
                        # Safety: Disable cooling if target=0 or sensor unavailable
                        self.safe_gpio_output(12, GPIO.HIGH)  # OFF
                        if cooling_target == 0:
                            logger.warning("❄️  Cooling disabled - No target temperature set (sld12=0)")
                        else:
                            logger.warning("❄️  Cooling disabled - Temperature sensor unavailable")
            else:
                # Function disabled - ensure GPIO is OFF
                self.safe_gpio_output(12, GPIO.HIGH)

            # Fan control based on actual climate demand (b6 - pin 20 / PWM P18)
            # Fan ON/OFF behavior stays compatible; PWM duty is now determined automatically.
            humidity_purge_active = self.should_run_humidity_purge(effective_sliders=effective_sliders)
            fan_duty = self.get_fan_speed_percent(effective_sliders=effective_sliders)
            if carbon_heater_active or ir_heater_active:
                self.apply_fan_output(True, duty=fan_duty, source='heater')
                if not self.button_states['b6']:
                    self.button_states['b6'] = True
                    self.button_states['b6_manual'] = True  # Auto-enabled fan is treated as manual
                    self.save_settings()
                    logger.info("🌀 Fan otomatik açıldı - ısıtıcılar aktif")
            elif self.button_states.get('b6_manual', False) and self.button_states['b6']:
                self.apply_fan_output(True, duty=fan_duty, source='manual_hold')
                logger.debug("🌀 Fan manuel açık, hız sistem tarafından ayarlanıyor")
            elif humidity_purge_active:
                self.apply_fan_output(True, duty=fan_duty, source='humidity_purge')
                if not self.button_states['b6']:
                    self.button_states['b6'] = True
                    logger.info("🌀 Fan otomatik açıldı - yüksek nem purgesi")
            else:
                self.apply_fan_output(False, source='auto_off')
                if self.button_states['b6']:
                    self.button_states['b6'] = False
                    self.save_settings()
                self.button_states['b6_manual'] = False
                logger.debug("🌀 Fan otomatik kapatıldı - ısıtıcılar kapandı ve manuel kontrol yoktu")

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
            # DEBUG: Log b9 (cooling) button specifically
            if name == 'b9':
                logger.info(f"🧊 COOLING BUTTON (b9) triggered - pin:{pin}, state:{state}")
            
            # Button state'i güncelle
            self.button_states[name] = state
            logger.info(f"Button {name}: {'ENABLED' if state else 'DISABLED'}")

            if name == 'b6':
                self.button_states['b6_manual'] = bool(state)
                self.apply_fan_output(bool(state), duty=self.get_fan_speed_percent(), source='manual_button')
                logger.info(f"Fan output -> {'PWM/relay ON' if state else 'PWM/relay OFF'}")

                if self.firebase_manager:
                    self.firebase_manager.update_button_state(name, state)

                self.save_settings()
                return True

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

            # Sync to Firebase
            if self.firebase_manager:
                self.firebase_manager.update_button_state(name, state)

            # Ayarları otomatik kaydet (restart sonrası hatırlansın)
            self.save_settings()

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
        if raw is None:
            return None

        text = str(raw).lower().strip()
        if not text:
            return None

        total_weeks = 0.0
        matched = False
        patterns = (
            # Yıl/Yaş - "yaş" kelimesini de ekle (Türkçe kullanım: "3 yaş 6 aylık")
            (r"(\d+(?:[.,]\d+)?)\s*(y[iı]l|yaş|yas|year|years|yr|jahre?|jahr)", 52.0),
            # Aylık - "ay" ve "aylık" formatları
            (r"(\d+(?:[.,]\d+)?)\s*(ay|aylık|aylik|month|months|mo|monate?|monat)", 4.345),
            (r"(\d+(?:[.,]\d+)?)\s*(hafta|week|weeks|wk|wochen?|woche)", 1.0),
            (r"(\d+(?:[.,]\d+)?)\s*(g[uü]n|gun|day|days|tage?|tag)", 1.0 / 7.0),
        )

        for pattern, multiplier in patterns:
            for match in re.finditer(pattern, text):
                total_weeks += float(match.group(1).replace(",", ".")) * multiplier
                matched = True

        if matched:
            return total_weeks

        try:
            # Sadece sayi girildiyse geriye donuk uyumluluk icin yil kabul et.
            return float(text.replace(",", ".")) * 52.0
        except ValueError:
            return None

    def _build_patient_auto_profile(self):
        """Hasta bilgisine gore otomatik ortam hedefleri uret.
        
        Desteklenen türler: Kedi, Köpek, Kuş
        Her tür için yaşa göre farklı sıcaklık ve nem hedefleri.
        """
        species = str(self.patient_context.get('species') or '').strip().lower()
        age_weeks = self._parse_age_weeks(self.patient_context.get('age'))

        if not species:
            return {
                'supported': False,
                'reason_code': 'missing_patient',
            }

        # Tür tespiti
        cat_tokens = ('kedi', 'cat', 'katze')
        dog_tokens = ('köpek', 'kopek', 'dog', 'hund')
        bird_tokens = ('kuş', 'kus', 'bird', 'vogel')
        
        is_cat = any(token in species for token in cat_tokens)
        is_dog = any(token in species for token in dog_tokens)
        is_bird = any(token in species for token in bird_tokens)

        if age_weeks is None:
            return {
                'supported': False,
                'reason_code': 'missing_age',
            }

        # ========== KEDİ PROFİLLERİ ==========
        if is_cat:
            if age_weeks < 1.0:
                profile_code = 'cat_0_1_week'
                temp_min, temp_max = 30.0, 32.0
                humidity_min, humidity_max = 55.0, 65.0
            elif age_weeks < 3.0:
                profile_code = 'cat_1_3_weeks'
                temp_min, temp_max = 27.0, 29.0
                humidity_min, humidity_max = 55.0, 65.0
            elif age_weeks < 52.0:
                profile_code = 'cat_4_plus_weeks'
                temp_min, temp_max = 21.0, 24.0
                humidity_min, humidity_max = 50.0, 60.0
            else:
                profile_code = 'cat_adult'
                temp_min, temp_max = 20.0, 22.0
                humidity_min, humidity_max = 45.0, 55.0

        # ========== KÖPEK PROFİLLERİ ==========
        elif is_dog:
            if age_weeks < 2.0:
                # Yenidoğan köpek yavrusu (0-2 hafta)
                profile_code = 'dog_0_2_weeks'
                temp_min, temp_max = 29.0, 32.0
                humidity_min, humidity_max = 55.0, 65.0
            elif age_weeks < 4.0:
                # Genç köpek yavrusu (2-4 hafta)
                profile_code = 'dog_2_4_weeks'
                temp_min, temp_max = 26.0, 29.0
                humidity_min, humidity_max = 55.0, 65.0
            elif age_weeks < 12.0:
                # Yavru köpek (4-12 hafta)
                profile_code = 'dog_4_12_weeks'
                temp_min, temp_max = 22.0, 26.0
                humidity_min, humidity_max = 50.0, 60.0
            elif age_weeks < 52.0:
                # Genç köpek (3-12 ay)
                profile_code = 'dog_juvenile'
                temp_min, temp_max = 18.0, 22.0
                humidity_min, humidity_max = 45.0, 55.0
            else:
                # Yetişkin köpek (1+ yaş)
                profile_code = 'dog_adult'
                temp_min, temp_max = 18.0, 22.0
                humidity_min, humidity_max = 40.0, 50.0

        # ========== KUŞ PROFİLLERİ ==========
        elif is_bird:
            if age_weeks < 2.0:
                # Yavru kuş (0-2 hafta) - Çok hassas
                profile_code = 'bird_0_2_weeks'
                temp_min, temp_max = 32.0, 35.0
                humidity_min, humidity_max = 60.0, 70.0
            elif age_weeks < 4.0:
                # Genç kuş (2-4 hafta)
                profile_code = 'bird_2_4_weeks'
                temp_min, temp_max = 29.0, 32.0
                humidity_min, humidity_max = 55.0, 65.0
            elif age_weeks < 8.0:
                # Palazlanan kuş (4-8 hafta)
                profile_code = 'bird_4_8_weeks'
                temp_min, temp_max = 26.0, 29.0
                humidity_min, humidity_max = 50.0, 60.0
            elif age_weeks < 52.0:
                # Genç kuş (2-12 ay)
                profile_code = 'bird_juvenile'
                temp_min, temp_max = 22.0, 26.0
                humidity_min, humidity_max = 45.0, 55.0
            else:
                # Yetişkin kuş (1+ yaş)
                profile_code = 'bird_adult'
                temp_min, temp_max = 20.0, 24.0
                humidity_min, humidity_max = 40.0, 50.0

        # ========== DESTEKLENMEYEN TÜRLER ==========
        else:
            return {
                'supported': False,
                'reason_code': 'unsupported_species',
            }

        humidity_target = round((humidity_min + humidity_max) / 2.0, 1)

        return {
            'supported': True,
            'reason_code': None,
            'profile_code': profile_code,
            'targets': {
                'sld3': round((temp_min + temp_max) / 2.0, 1),
                'sld2': humidity_target,
                'sld12': round(temp_max, 1),
            },
            'bands': {
                'temperature': {
                    'min': round(temp_min, 1),
                    'max': round(temp_max, 1),
                },
                'humidity': {
                    'min': round(humidity_min, 1),
                    'max': round(humidity_max, 1),
                },
            }
        }

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
        effective_values = self.slider_values.copy()

        if self.care_settings.get('mode') == 'auto':
            profile = self._build_patient_auto_profile()
            if profile.get('supported'):
                effective_values.update(profile['targets'])

        return effective_values

    def get_care_status(self):
        """UI icin bakim modu durumu ve hasta profili bilgisini don."""
        profile = self._build_patient_auto_profile()
        effective_values = self.get_effective_slider_values()

        return {
            'mode': self.care_settings.get('mode', 'manual'),
            'auto_available': bool(profile.get('supported')),
            'manual_locked': self.care_settings.get('mode') == 'auto' and bool(profile.get('supported')),
            'profile_code': profile.get('profile_code'),
            'reason_code': profile.get('reason_code'),
            'patient_name': self.patient_context.get('name', ''),
            'patient_species': self.patient_context.get('species', ''),
            'patient_age': self.patient_context.get('age', ''),
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
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    file_content = f.read().strip()

                    if not file_content:
                        logger.warning(f"⚠️  Settings file {SETTINGS_FILE} is empty!")
                        return

                    # JSON formatı mı kontrol et
                    if file_content.startswith("{"):
                        # JSON format
                        try:
                            data = json.loads(file_content)
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
                            
                            # Load system settings
                            if "system_settings" in data:
                                self.system_settings.update(data["system_settings"])
                                self.system_settings.pop('soothing_audio_enabled', None)
                                self.system_settings.pop('soothing_audio_mode', None)
                                self.system_settings['fan_output_mode'] = self.get_fan_output_mode()
                                self.refresh_fan_output_mode(reapply_current_output=False)
                                logger.info(f"⚙️  System settings loaded")
                            
                            # Load user profile
                            if "user_profile" in data:
                                self.user_profile.update(data["user_profile"])
                                logger.info(f"👤 User profile loaded")

                            if "patient_context" in data:
                                self.update_patient_context(data["patient_context"])
                                logger.info("🐾 Patient context loaded")

                            if "current_patient" in data and _patient_record_has_content(data["current_patient"]):
                                self.current_patient = dict(data["current_patient"])
                                logger.info("🗂️ Current patient loaded")
                            elif _patient_record_has_content(self.patient_context):
                                self.current_patient.update({
                                    key: value for key, value in self.patient_context.items()
                                    if str(value or '').strip()
                                })
                                if _patient_record_has_content(self.current_patient):
                                    self.current_patient.setdefault('id', _build_patient_id(self.current_patient))
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
                        except json.JSONDecodeError as je:
                            logger.error(f"❌ JSON decode error in settings file: {je}")
                    else:
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
                    
                    # GÜVENLİK: UV ve Ozon butonları her zaman kapalı başlamalı
                    # Bu cihazlar tehlikeli olabilir (UV ışığı, ozon gazı)
                    self.button_states["b7"] = False  # UV Sterilization
                    self.button_states["b8"] = False  # Ozone Sterilization
                    logger.info("🔒 UV/Ozone forced OFF at startup (safety)")
                    
                    logger.info(f"📊 Button states loaded from settings: {self.button_states}")
                    logger.info(f"📊 Slider values in memory: {self.slider_values}")
                    
                    # GPIO'ları buton durumlarına göre ayarla
                    self._apply_button_states_to_gpio()
            else:
                logger.warning(f"⚠️  Settings file NOT FOUND: {SETTINGS_FILE}. Using defaults.")
        except Exception as e:
            logger.error(f"❌ Load settings error: {e}", exc_info=True)
    
    def _apply_button_states_to_gpio(self):
        """Kaydedilmiş buton durumlarını GPIO'lara uygula"""
        if not GPIO_AVAILABLE:
            logger.info("⚠️  GPIO not available - skipping GPIO state restoration")
            return
        
        # Pin mapping
        pin_map = {
            'b1': 5,   # Therapeutic Lighting
            'b2': 6,   # Nebulizer
            'b3': 13,  # Humidity Control
            'b4': 16,  # Heating Pad
            'b5': 19,  # IR Heater
            'b6': 20,  # Ventilation Fan
            'b7': 21,  # UV Sterilization
            'b8': 26,  # Ozone Sterilizer
            'b9': 12   # Cooling System
        }
        
        logger.info("🔧 Applying saved button states to GPIO...")
        
        for button_name, state in self.button_states.items():
            if button_name in pin_map:
                pin = pin_map[button_name]
                if button_name == 'b6':
                    try:
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
                    self.gpio_output_states[button_name] = state
                    status = "ON" if state else "OFF"
                    logger.info(f"  → {button_name} (GPIO {pin}): {status}")
                except Exception as e:
                    logger.error(f"  → {button_name} (GPIO {pin}): ERROR - {e}")
        
        logger.info("✅ GPIO states restored from saved settings")
    
    def save_settings(self):
        """Ayarları JSON formatında dosyaya kaydet"""
        try:
            self.system_settings.pop('soothing_audio_enabled', None)
            self.system_settings.pop('soothing_audio_mode', None)
            # UV ve Ozon butonlarını herzaman kapalı kaydet (güvenlik)
            button_states_to_save = self.button_states.copy()
            button_states_to_save["b7"] = False  # UV Sterilization
            button_states_to_save["b8"] = False  # Ozone Sterilization

            settings_data = {
                "slider_values": self.slider_values,
                "button_states": button_states_to_save,
                "ai_enabled": self.ai_enabled,
                "system_settings": self.system_settings,
                "user_profile": self.user_profile,
                "patient_context": self.patient_context,
                "current_patient": self.current_patient,
                "care_settings": self.care_settings
            }

            with open(SETTINGS_FILE, "w") as f:
                json.dump(settings_data, f, indent=4, ensure_ascii=False)
            
            logger.debug(f"Settings file saved to: {SETTINGS_FILE}")

            logger.info("✅ Settings saved (UV/Ozone forced OFF)")
            
            # Sync to Firebase
            if self.firebase_manager:
                self.firebase_manager.sync_controls(self.button_states, self.slider_values)
                logger.debug("✅ Firebase controls synced after save")
                
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
                    self.control_logic()
                    # WebSocket ile button durumlarını VE GPIO output state'lerini gönder
                    # Sync to all local clients
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
            if self.ai_enabled and not self.ai_manager.started:
                ai_started = self.ai_manager.start()
                if not ai_started:
                    logger.warning("⚠️ AI manager could not start; disabling AI until user retries")
                    self.ai_enabled = False
            self.ai_thread = threading.Thread(target=ai_loop, daemon=True)
            self.ai_thread.start()
            logger.info("🧠 AI loop thread started")
        
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
        if self.power_diag_thread:
            self.power_diag_thread.join(timeout=2)
        if self.kiosk_watchdog_thread:
            self.kiosk_watchdog_thread.join(timeout=2)
        
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
        self.stop_fan_pwm()
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

@app.route('/ai-vitals')
def ai_vitals_page():
    """AI vital grafik sayfası"""
    return app.send_static_file('ai_vitals.html')

@app.route('/help')
def help_page():
    """Yardım sayfası"""
    return app.send_static_file('help.html')

@app.route('/api/help/docs', methods=['GET'])
def api_help_docs():
    """Yardım dokümanlarının listesini döndür"""
    return jsonify({"docs": _get_help_docs_index()})

@app.route('/api/help/docs/<doc_id>', methods=['GET'])
def api_help_doc_content(doc_id):
    """Tek bir yardım dokümanının içeriğini döndür"""
    docs = {d["id"]: d for d in _get_help_docs_index()}
    item = docs.get(doc_id)
    if not item:
        return jsonify({"error": "Document not found"}), 404

    safe_filename = item["filename"]
    full_path = os.path.join(DOCS_DIR, safe_filename)
    if not os.path.isfile(full_path):
        return jsonify({"error": "Document file missing"}), 404

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        return jsonify({
            "id": item["id"],
            "title": item["title"],
            "content": content
        })
    except Exception as e:
        logger.error(f"Help doc read error ({safe_filename}): {e}")
        return jsonify({"error": "Document read error"}), 500

@app.route('/api/status')
def get_status():
    """Sistem durumunu al"""
    return jsonify({
        'sensors': kuvoz_server.sensor_data,
        'buttons': kuvoz_server.button_states,
        'sliders': kuvoz_server.get_effective_slider_values(),
        'gpio_outputs': kuvoz_server.gpio_output_states,
        'timers': kuvoz_server.get_timer_data(),
        'system': kuvoz_server.get_effective_system_status(),
        'system_settings': kuvoz_server.system_settings,
        'care_settings': kuvoz_server.get_care_status(),
        'current_patient': kuvoz_server.current_patient,
        'timestamp': time.time()
    })

@app.route('/api/patients', methods=['GET'])
def get_patients():
    """Kayıtlı hasta listesini al"""
    try:
        patients = _load_patient_records()
        patients = _merge_current_patient_record(patients, kuvoz_server.current_patient)
        return jsonify({'success': True, 'patients': patients})
    except Exception as e:
        logger.error(f"Error loading patients: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/patients', methods=['POST'])
def save_patient_api():
    """Yeni hasta kaydet veya mevcut hastayı güncelle"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'Geçersiz veri'}), 400

        patients = _load_patient_records()
        patient_id = _build_patient_id(data)
        data['id'] = patient_id
        data['savedAt'] = datetime.datetime.now().isoformat()

        # Mevcut hasta var mı kontrol et
        existing_index = None
        for i, p in enumerate(patients):
            if p.get('id') == patient_id:
                existing_index = i
                break
        
        if existing_index is not None:
            # Mevcut hastayı güncelle
            patients[existing_index] = data
            logger.info(f"Patient updated: {data.get('name')}")
        else:
            # Yeni hasta ekle
            patients.insert(0, data)
            logger.info(f"New patient saved: {data.get('name')}")

        patients = _merge_current_patient_record(patients, data)
        # Son 50 hastayı tut
        patients = patients[:50]

        _save_patient_records(patients)

        kuvoz_server.current_patient = dict(data)
        kuvoz_server.update_patient_context(data)
        kuvoz_server.save_settings()
        return jsonify({'success': True, 'patient': data})
    except Exception as e:
        logger.error(f"Error saving patient: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/patients/<patient_id>', methods=['DELETE'])
def delete_patient_api(patient_id):
    """Hasta kaydını sil"""
    try:
        patients = _load_patient_records()
        # Hastayı bul ve sil
        new_patients = [p for p in patients if p.get('id') != patient_id]

        current_matches = kuvoz_server.current_patient.get('id') == patient_id
        if len(new_patients) == len(patients) and not current_matches:
            return jsonify({'success': False, 'error': 'Hasta bulunamadı'}), 404

        _save_patient_records(new_patients)

        if current_matches:
            kuvoz_server.current_patient = {}
            kuvoz_server.patient_context = {
                'name': '',
                'species': '',
                'breed': '',
                'age': '',
                'weight': ''
            }
            kuvoz_server.care_settings['mode'] = 'manual'
            kuvoz_server.save_settings()

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting patient: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/patients/<patient_id>/discharge', methods=['POST'])
def discharge_patient_api(patient_id):
    """Hastayı taburcu et"""
    try:
        data = request.json
        patients = _merge_current_patient_record(_load_patient_records(), kuvoz_server.current_patient)

        # Hastayı bul
        patient_index = None
        for i, p in enumerate(patients):
            if p.get('id') == patient_id:
                patient_index = i
                break
        
        if patient_index is None:
            return jsonify({'success': False, 'error': 'Hasta bulunamadı'}), 404
        
        # Taburcu bilgilerini ekle
        patients[patient_index]['discharged'] = True
        patients[patient_index]['dischargeDate'] = data.get('dischargeDate')
        patients[patient_index]['dischargeTime'] = data.get('dischargeTime')
        patients[patient_index]['dischargeNotes'] = data.get('dischargeNotes')
        patients[patient_index]['dischargeStatus'] = data.get('dischargeStatus')
        patients[patient_index]['dischargedAt'] = datetime.datetime.now().isoformat()

        _save_patient_records(patients)

        logger.info(f"Patient discharged: {patients[patient_index].get('name')}")

        if kuvoz_server.current_patient.get('id') == patient_id:
            kuvoz_server.current_patient = dict(patients[patient_index])

        # Taburcu sonrası kalan aktif hasta sayısını kontrol et
        active_patients = [p for p in patients if not p.get('discharged', False)]
        if len(active_patients) == 0:
            # Hiç aktif hasta yoksa manuel moda geç ve slider'ları sıfırla
            kuvoz_server.care_settings['mode'] = 'manual'
            kuvoz_server.patient_context = {
                'name': '',
                'species': '',
                'breed': '',
                'age': '',
                'weight': ''
            }
            kuvoz_server.current_patient = {}
            # Slider hedeflerini varsayılan değerlere sıfırla (manuel mod için)
            kuvoz_server.slider_values['sld3'] = 25.0  # Temperature target
            kuvoz_server.slider_values['sld2'] = 65    # Humidity target
            kuvoz_server.slider_values['sld12'] = 25.0 # Cooling target
            kuvoz_server.save_settings()
            logger.info("🩺 No active patients remaining - switched to manual care mode, sliders reset to defaults")
            # Frontend'e bildirim gönder
            socketio.emit('care_settings_update', {
                'care_settings': kuvoz_server.get_care_status(),
                'sliders': kuvoz_server.get_effective_slider_values()
            })
        else:
            kuvoz_server.save_settings()

        return jsonify({'success': True, 'patient': patients[patient_index]})
    except Exception as e:
        logger.error(f"Error discharging patient: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai-alerts', methods=['GET'])
def get_ai_alerts():
    """AI uyarı özetini getir (yeni, anlamlı rapor)"""
    try:
        from ai_alert_summary import AIAlertSummary

        hours = max(1, min(int(request.args.get('hours', 24)), 720))
        patient_id = request.args.get('patient_id', None)

        analyzer = AIAlertSummary(db_path='data/ai_vitals.db')
        summary = analyzer.get_quick_summary(hours=hours, patient_id=patient_id)

        return jsonify(summary)
    except ImportError as e:
        logger.error(f"AI Alert Summary import error: {e}")
        return jsonify({'error': 'AI alert module not available'}), 503
    except Exception as e:
        logger.error(f"Error fetching AI alerts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai-vitals', methods=['GET', 'DELETE'])
def get_ai_vitals():
    """AI vital ölçümlerini getir veya sil"""
    try:
        from lib.data import AIVitalsLogger
        
        # Initialize AI vitals logger
        ai_vitals_logger = AIVitalsLogger(db_path='data/ai_vitals.db')
        
        # Handle DELETE request to clear AI vital logs
        if request.method == 'DELETE':
            try:
                payload = request.get_json(silent=True) or {}
                clear_reason = str(payload.get('reason') or 'manual').strip() or 'manual'
                success = ai_vitals_logger.clear_all_data(reason=clear_reason, context=payload)
                if success:
                    return jsonify({
                        'success': True,
                        'message': 'All AI vital logs cleared',
                        'meta': {
                            'cleared_reason': clear_reason
                        }
                    })
                else:
                    return jsonify({'success': False, 'error': 'Database error'}), 500
            except Exception as e:
                logger.error(f"Error clearing AI vital logs: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        # Handle GET request to fetch AI vital readings
        limit = max(1, min(int(request.args.get('limit', 2500)), 6000))
        hours = max(1, min(int(request.args.get('hours', 24)), 720))
        patient_id = request.args.get('patient_id', 'all')
        
        # Handle 'current' patient filter
        if patient_id == 'current':
            current_pt = kuvoz_server.current_patient
            patient_id = current_pt.get('id') if current_pt and isinstance(current_pt, dict) else None
            # If no current patient, fall back to 'all'
            if not patient_id:
                patient_id = 'all'

        # Calculate time range
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(hours=hours)

        # Get readings from database
        readings = ai_vitals_logger.get_readings(
            start_time=start_time,
            end_time=end_time,
            patient_id=None if patient_id == 'all' else patient_id,
            limit=limit
        )

        # Get statistics
        stats = ai_vitals_logger.get_statistics(
            start_time=start_time,
            end_time=end_time,
            patient_id=None if patient_id == 'all' else patient_id
        )

        # Get status breakdown
        status_breakdown = ai_vitals_logger.get_status_breakdown(
            start_time=start_time,
            end_time=end_time,
            patient_id=None if patient_id == 'all' else patient_id
        )

        # Get latest reading
        latest = ai_vitals_logger.get_latest_reading(
            patient_id=None if patient_id == 'all' else patient_id
        )
        
        # Get patient list
        patients = ai_vitals_logger.get_patient_summaries(
            start_time=start_time,
            end_time=end_time
        )

        # Get current patient
        current_patient = kuvoz_server.current_patient

        # Check if AI and logging are enabled
        logging_enabled = True
        ai_enabled = getattr(kuvoz_server, 'ai_enabled', False)
        
        return jsonify({
            'data': readings,
            'meta': {
                'hours': hours,
                'limit': limit,
                'returned_records': len(readings),
                'total_records': ai_vitals_logger.get_record_count(),
                'statistics': stats,
                'status_breakdown': status_breakdown,
                'latest': latest,
                'patients': patients,
                'current_patient': current_patient,
                'logging_enabled': logging_enabled,
                'ai_enabled': ai_enabled,
            }
        })
    except ImportError as e:
        logger.error(f"AI Vitals Logger import error: {e}")
        return jsonify({'error': 'AI vitals module not available', 'data': []}), 503
    except Exception as e:
        logger.error(f"Error fetching AI vitals: {e}", exc_info=True)
        return jsonify({'error': str(e), 'data': []}), 500

@app.route('/api/logs', methods=['GET', 'DELETE'])
def get_logs():
    """Sensor loglarını getir veya sil"""
    if not kuvoz_server.sensor_logger:
        return jsonify({'error': 'Logging not available', 'data': []})
    
    # Handle DELETE request to clear logs
    if request.method == 'DELETE':
        try:
            payload = request.get_json(silent=True) or {}
            clear_reason = str(payload.get('reason') or request.args.get('reason') or 'manual').strip() or 'manual'
            success = kuvoz_server.sensor_logger.clear_all_data(reason=clear_reason, context=payload)
            if success:
                return jsonify({
                    'success': True,
                    'message': 'All logs cleared',
                    'meta': {
                        'cleared_reason': clear_reason
                    }
                })
            else:
                return jsonify({'success': False, 'error': 'Database error'}), 500
        except Exception as e:
            logger.error(f"Error clearing logs: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # Handle GET request to fetch logs
    try:
        limit = max(1, min(int(request.args.get('limit', 100)), 5000))
        days = max((1.0 / 24.0), min(float(request.args.get('days', 1.0)), 365.0))
        
        start_time = datetime.datetime.now() - datetime.timedelta(days=days)
        readings = kuvoz_server.sensor_logger.get_readings(start_time=start_time, limit=limit)
        stats = kuvoz_server.sensor_logger.get_statistics(hours=max(1, int(days * 24)))

        return jsonify({
            'data': readings,
            'meta': {
                'days': days,
                'limit': limit,
                'returned_records': len(readings),
                'total_records': kuvoz_server.sensor_logger.get_record_count(),
                'stats': stats,
                'current_patient': kuvoz_server.current_patient,
                'capabilities': kuvoz_server.get_effective_system_status(),
            }
        })
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        return jsonify({'error': str(e), 'data': []})

@app.route('/failure.dat')
def download_settings_file():
    """Debug route: Serve failure.dat"""
    if os.path.exists(SETTINGS_FILE):
        return send_file(SETTINGS_FILE, as_attachment=True)
    else:
        return jsonify({'error': 'Settings file not found'}), 404

@app.route('/resim/<path:filename>')
def serve_resim(filename):
    """Resim klasöründeki dosyaları servis et"""
    return send_from_directory(os.path.join(SCRIPT_DIR, 'resim'), filename)

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """WebSocket bağlantısı"""
    try:
        sid = request.sid
        # IP adresini al
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ',' in ip:
            ip = ip.split(',')[0].strip()
        
        current_time = time.time()
        kuvoz_server.active_connections[sid] = {
            'ip': ip,
            'connected_at': current_time,
            'last_seen': current_time
        }
        kuvoz_server.note_local_kiosk_connect(ip, sid)
        
        logger.info(f'✅ WebSocket connected: {sid} from {ip}')
        
        # Aktif bağlantıları broadcast et
        socketio.emit('active_connections_update', {
            'connections': [
                {
                    'ip': conn['ip'],
                    'connected_at': conn['connected_at'],
                    'duration': int(current_time - conn['connected_at'])
                }
                for conn in kuvoz_server.active_connections.values()
            ]
        }, namespace='/')
        
    except Exception as e:
        logger.error(f'Connect error: {e}')
    
    logger.info('Client connected')
    
    # Get system status dynamically
    system_status = kuvoz_server.get_effective_system_status()
    
    logger.info(f"📤 Sending status_response on connect. Sliders: {kuvoz_server.slider_values}")
    emit('status_response', {
        'type': 'status_response',
        'sensors': kuvoz_server.sensor_data,
        'buttons': kuvoz_server.button_states,
        'gpio_outputs': kuvoz_server.gpio_output_states,
        'sliders': kuvoz_server.get_effective_slider_values(),
        'timers': kuvoz_server.get_timer_data(),
        'system': system_status,
        'ai_available': AI_AVAILABLE,
        'system_settings': kuvoz_server.system_settings,
        'care_settings': kuvoz_server.get_care_status()
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
    system_status = kuvoz_server.get_effective_system_status()
    
    status_data = {
        'type': 'status_response',
        'sensors': kuvoz_server.sensor_data,
        'buttons': kuvoz_server.button_states,
        'gpio_outputs': kuvoz_server.gpio_output_states,
        'sliders': kuvoz_server.get_effective_slider_values(),
        'timers': kuvoz_server.get_timer_data(),
        'system': system_status,
        'ai_available': AI_AVAILABLE,
        'ai_enabled': kuvoz_server.ai_enabled,
        'disinfection_mode': kuvoz_server.disinfection_mode,
        'system_settings': kuvoz_server.system_settings,
        'care_settings': kuvoz_server.get_care_status()
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
def handle_update_slider_event(data):
    """Handle slider value update event"""
    handle_update_slider_logic(data)

def handle_update_slider_logic(data):
    """Internal logic for slider update"""
    try:
        slider_id = data.get('id')
        value = data.get('value')
        logger.info(f'Slider update: {slider_id} -> {value}')

        if slider_id and value is not None:
            kuvoz_server.update_slider(slider_id, value)
            # Emit update to all clients
            socketio.emit('slider_update', {
                'type': 'slider_update',
                'sliders': kuvoz_server.get_effective_slider_values()
            })

            # If duty/free time sliders changed, immediately send timer update
            if slider_id in ['sld8', 'sld9', 'sld10', 'sld11']:
                socketio.emit('timer_update', kuvoz_server.get_timer_data())
            return True
        return False
    except Exception as e:
        logger.error(f"Slider logic error: {e}")
        return False

@socketio.on('save_settings_old')
def handle_save_settings_old(data=None):
    """Handle save settings request (deprecated - use save_settings with data)"""
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
                logger.info("🤖 Attempting to start AI manager (user requested via UI)...")
                started = kuvoz_server.ai_manager.start()
                if not started:
                    logger.error("❌ AI Manager.start() returned False - camera initialization failed")
                    raise RuntimeError('kamera başlatılamadı')
                logger.info('🤖 AI Module enabled by user - STARTED SUCCESSFULLY')
                # Save preference
                kuvoz_server.save_settings()
                emit('ai_status', {
                    'enabled': True,
                    'message': 'AI analizi başlatıldı',
                    'vision_running': kuvoz_server.ai_manager.vision.running,
                    'camera_type': kuvoz_server.ai_manager.vision.camera_type
                }, broadcast=True)
            except Exception as e:
                logger.error(f'❌ Failed to start AI: {e}', exc_info=True)
                kuvoz_server.ai_enabled = False
                emit('error', {
                    'type': 'error',
                    'message': f'AI başlatma hatası: {str(e)}. Kamera bağlantısını kontrol edin.'
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
        logger.error(f'Toggle AI error: {e}', exc_info=True)
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
        kuvoz_server.save_settings()
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
        kuvoz_server.save_settings()
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
    try:
        sid = request.sid
        if sid in kuvoz_server.active_connections:
            ip = kuvoz_server.active_connections[sid]['ip']
            duration = int(time.time() - kuvoz_server.active_connections[sid]['connected_at'])
            del kuvoz_server.active_connections[sid]
            kuvoz_server.note_local_kiosk_disconnect(ip, sid)
            logger.info(f'❌ WebSocket disconnected: {sid} ({ip}) - Duration: {duration}s')
            
            # Aktif bağlantıları broadcast et
            current_time = time.time()
            socketio.emit('active_connections_update', {
                'connections': [
                    {
                        'ip': conn['ip'],
                        'connected_at': conn['connected_at'],
                        'duration': int(current_time - conn['connected_at'])
                    }
                    for conn in kuvoz_server.active_connections.values()
                ]
            }, namespace='/')
    except Exception as e:
        logger.error(f'Disconnect error: {e}')
    
    logger.info('Client disconnected')

# ============================================================================
# WI-FI YÖNETİMİ
# ============================================================================

def _get_wpa_status(interface='wlan0'):
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

def _wait_for_wpa_completed(interface='wlan0', timeout=30, interval=2, previous_bssid=None, previous_ssid=None):
    seen_non_completed = False
    start = time.time()
    while time.time() - start < timeout:
        status = _get_wpa_status(interface)
        wpa_state = _get_wpa_field(status, 'wpa_state')
        if wpa_state == 'COMPLETED':
            # Avoid treating stale pre-existing COMPLETED state as fresh WPS success.
            if not previous_bssid and not previous_ssid:
                return True

            bssid = _get_wpa_field(status, 'bssid')
            ssid = _get_wpa_field(status, 'ssid')
            bssid_changed = bool(previous_bssid and bssid and bssid != previous_bssid)
            ssid_changed = bool(previous_ssid and ssid and ssid != previous_ssid)
            if seen_non_completed or bssid_changed or ssid_changed:
                return True
        else:
            seen_non_completed = True
        time.sleep(interval)
    return False

def _get_wpa_field(status_text, field):
    prefix = f"{field}="
    for line in (status_text or '').splitlines():
        if line.startswith(prefix):
            return line.split('=', 1)[1].strip()
    return None

def _sync_nm_with_wpa(interface='wlan0'):
    """
    If wpa_supplicant is already connected after WPS, ask NetworkManager to
    adopt/activate a matching Wi-Fi profile so nmcli status remains consistent.
    """
    try:
        status = _get_wpa_status(interface)
        if 'wpa_state=COMPLETED' not in status:
            return False

        wpa_ssid = _get_wpa_field(status, 'ssid')
        if not wpa_ssid:
            return False

        # Prefer a Wi-Fi profile whose configured SSID matches current WPA link.
        # Keep this compatible with older nmcli versions that don't allow
        # '802-11-wireless.ssid' in the -f field list.
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
                # Avoid "preconfigured" when a concrete profile is available.
                if name != 'preconfigured':
                    break

        if not candidate:
            logger.warning(f"WPS NM sync: no matching Wi-Fi profile for SSID '{wpa_ssid}'")
            return False

        up = subprocess.run(
            ['sudo', 'nmcli', 'connection', 'up', candidate, 'ifname', interface],
            capture_output=True,
            text=True,
            timeout=25
        )
        if up.returncode == 0:
            logger.info(f"WPS NM sync successful on {interface} via profile '{candidate}'")
            return True

        err = (up.stderr or up.stdout or '').strip()
        logger.warning(f"WPS NM sync failed on {interface}: {err}")
        return False
    except Exception as e:
        logger.warning(f"WPS NM sync error on {interface}: {e}")
        return False

def _build_udhcpc_command(interface='wlan0'):
    if not os.path.exists(UDHCPC_SCRIPT):
        logger.warning(f"UDHCPC script not found: {UDHCPC_SCRIPT}")
        return None
    udhcpc = shutil.which('udhcpc')
    if udhcpc:
        cmd = [udhcpc]
    else:
        busybox = shutil.which('busybox')
        if not busybox:
            logger.warning("udhcpc/busybox not found for DHCP")
            return None
        cmd = [busybox, 'udhcpc']
    cmd.extend(['-i', interface, '-q', '-n', '-t', '10', '-T', '3', '-A', '20', '-s', UDHCPC_SCRIPT])
    return ['sudo', '-n'] + cmd

def _current_wifi_status(interface='wlan0'):
    """Return current Wi-Fi link status used by WPS final notifications."""
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
                    ips = get_all_ips()
                    status = {
                        'connected': True,
                        'ssid': parts[1],
                        'ip': ips.get(dev) or ips.get(interface)
                    }
                break
    except Exception:
        pass
    return status

def _emit_wps_final(success, message):
    payload = {'success': success, 'message': message, 'stage': 'final'}
    payload.update(_current_wifi_status('wlan0'))
    socketio.emit('wifi_wps_response', payload, namespace='/')

def _start_wps_pairing(interface='wlan0'):
    """Start WPS pairing process in the background to avoid blocking and early timeouts."""
    started, msg = _begin_wps_session()
    if not started:
        return False, msg, None

    # Get current status to detect changes later
    pre_status = _get_wpa_status(interface)
    previous_bssid = _get_wpa_field(pre_status, 'bssid')
    previous_ssid = _get_wpa_field(pre_status, 'ssid')

    # Start worker thread immediately so UI gets "started" response
    if start_wifi_dhcp_async(interface, previous_bssid, previous_ssid):
        return True, 'WPS Eşleşmesi başlatıldı. Modemdeki butona basın.', 'started'
    else:
        _end_wps_session()
        return False, 'WPS işlemi başlatılamadı.', None

def _wifi_dhcp_worker(interface='wlan0', previous_bssid=None, previous_ssid=None, monitor_only=False):
    global WIFI_DHCP_IN_PROGRESS
    try:
        # 1. Try modern nmcli first (blocks until handshake completes or timeout)
        logger.info(f"WPS Worker: Attempting nmcli WPS on {interface}...")
        nm_success = False
        try:
            # Check if nmcli exists and supports wps
            check = subprocess.run(['nmcli', 'dev', 'wifi', 'wps', 'help'], capture_output=True, timeout=5)
            if check.returncode == 0:
                nm_wps = subprocess.run(
                    ['sudo', 'nmcli', 'dev', 'wifi', 'wps', 'ifname', interface],
                    capture_output=True,
                    text=True,
                    timeout=125
                )
                if nm_wps.returncode == 0:
                    logger.info("WPS Worker: nmcli WPS successful.")
                    nm_success = True
                else:
                    logger.warning(f"WPS Worker: nmcli WPS failed: {nm_wps.stderr}")
            else:
                logger.warning("WPS Worker: nmcli WPS command not supported.")
        except Exception as e:
            logger.warning(f"WPS Worker: nmcli exception: {e}")

        # 2. If nmcli failed/not supported, fallback to legacy wpa_cli
        if not nm_success:
            logger.info(f"WPS Worker: Falling back to wpa_cli for {interface}...")
            wpa_cli = '/usr/sbin/wpa_cli' if os.path.exists('/usr/sbin/wpa_cli') else '/sbin/wpa_cli'
            if not os.path.exists(wpa_cli): wpa_cli = 'wpa_cli'
            p = '/run/wpa_supplicant' if os.path.exists(f'/run/wpa_supplicant/{interface}') else None
            wpa_cmd = ['sudo', wpa_cli, '-i', interface]
            if p: wpa_cmd.extend(['-p', p])
            
            # Cleanup
            for sc in ('wps_cancel', 'disconnect'):
                subprocess.run(wpa_cmd + [sc], capture_output=True, timeout=5)
            
            # Start PBC
            pbc = subprocess.run(wpa_cmd + ['wps_pbc'], capture_output=True, text=True, timeout=10)
            if pbc.returncode != 0 or 'OK' not in pbc.stdout:
                logger.error(f"WPS Worker: wpa_cli wps_pbc failed: {pbc.stderr or pbc.stdout}")
                _emit_wps_final(False, 'WPS başlatılamadı (wpa_cli hatası).')
                return

        # 3. Wait for the connection to be established
        if not _wait_for_wpa_completed(
            interface,
            timeout=120, 
            interval=3,
            previous_bssid=previous_bssid,
            previous_ssid=previous_ssid
        ):
            logger.warning(f"WPS: wpa_state not completed for {interface} within timeout.")
            _emit_wps_final(False, 'WPS tamamlanamadı: modem ile eşleşme kurulamadı veya zaman aşımı.')
            return

        # 4. Connection state completed, now sync and get IP
        logger.info(f"WPS: Connection state completed on {interface}. Syncing...")
        socketio.emit('wifi_wps_progress', {'message': 'Bağlantı kuruldu, IP adresi bekleniyor...'}, namespace='/')

        # Prefer NetworkManager alignment
        if _sync_nm_with_wpa(interface):
            for _ in range(15):
                st = _current_wifi_status(interface)
                if st.get('connected') and st.get('ip'):
                    _emit_wps_final(True, f"WPS tamamlandı. Bağlandı: {st.get('ssid')} (IP: {st.get('ip')})")
                    return
                time.sleep(2)
            
            st = _current_wifi_status(interface)
            if st.get('connected'):
                _emit_wps_final(True, f"WPS tamamlandı. Bağlandı: {st.get('ssid')} (Ağ kaydedildi, IP bekleniyor...)")
            else:
                _emit_wps_final(True, 'WPS tamamlandı. Wi-Fi bağlantısı kaydedildi.')
            return

        # 5. Last resort: manual DHCP if NM alignment failed
        cmd = _build_udhcpc_command(interface)
        if not cmd:
            _emit_wps_final(False, 'WPS sonrası DHCP başlatılamadı (udhcpc eksik).')
            return
            
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if result.returncode != 0:
            err = (result.stderr or result.stdout or '').strip()
            logger.warning(f"WPS DHCP failed: {err}")
            _emit_wps_final(False, f'WPS tamamlandı ancak IP alınamadı: {err}')
        else:
            st = _current_wifi_status(interface)
            _emit_wps_final(True, f"WPS tamamlandı. Bağlandı: {st.get('ssid') or interface} (IP: {st.get('ip') or 'bilinmiyor'})")
    except Exception as e:
        logger.warning(f"WPS worker error: {e}")
        _emit_wps_final(False, f'WPS işlem hatası: {e}')
    finally:
        with WIFI_DHCP_LOCK:
            WIFI_DHCP_IN_PROGRESS = False
        _end_wps_session()

def start_wifi_dhcp_async(interface='wlan0', previous_bssid=None, previous_ssid=None, monitor_only=False):
    global WIFI_DHCP_IN_PROGRESS
    with WIFI_DHCP_LOCK:
        if WIFI_DHCP_IN_PROGRESS:
            logger.info(f"WPS/DHCP worker already running for {interface}, skipping duplicate start")
            return False
        WIFI_DHCP_IN_PROGRESS = True
    threading.Thread(
        target=_wifi_dhcp_worker,
        args=(interface, previous_bssid, previous_ssid, monitor_only),
        daemon=True
    ).start()
    return True

@socketio.on('wifi_scan')
def handle_wifi_scan():
    """Mevcut Wi-Fi ağlarını tara"""
    try:
        logger.info("Wi-Fi scanning initiated...")
        # nmcli ile ağları tara (-t: terse, -f: fields)
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'SSID,SIGNAL,BARS,SECURITY', 'dev', 'wifi'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            networks = []
            seen_ssids = set()
            for line in result.stdout.strip().split('\n'):
                if not line: continue
                parts = line.split(':')
                if len(parts) >= 4:
                    ssid = parts[0]
                    if ssid and ssid not in seen_ssids:
                        networks.append({
                            'ssid': ssid,
                            'signal': parts[1],
                            'bars': parts[2],
                            'security': parts[3]
                        })
                        seen_ssids.add(ssid)
            
            emit('wifi_scan_response', {'success': True, 'networks': networks})
        else:
            emit('wifi_scan_response', {'success': False, 'message': 'Tarama başarısız (nmcli hatası)'})
            
    except subprocess.TimeoutExpired:
        emit('wifi_scan_response', {'success': False, 'message': 'Tarama zaman aşımına uğradı'})
    except Exception as e:
        logger.error(f"Wi-Fi scan error: {e}")
        emit('wifi_scan_response', {'success': False, 'message': str(e)})

@socketio.on('wifi_connect')
def handle_wifi_connect(data):
    """Belirli bir Wi-Fi ağına bağlan"""
    try:
        ssid = data.get('ssid')
        password = data.get('password')
        
        if not ssid:
            emit('wifi_connect_response', {'success': False, 'message': 'SSID gerekli'})
            return

        logger.info(f"Attempting to connect to Wi-Fi: {ssid}")
        emit('wifi_connect_progress', {'message': f'{ssid} ağına bağlanılıyor...'})

        # nmcli ile bağlan
        cmd = ['sudo', 'nmcli', 'dev', 'wifi', 'connect', ssid]
        if password:
            cmd.extend(['password', password])
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            # Wi-Fi önceliğini artır (ethernet takılıyken bile çalışması için)
            subprocess.run(['sudo', 'nmcli', 'connection', 'modify', ssid, 'ipv4.route-metric', '50'], capture_output=True)
            subprocess.run(['sudo', 'nmcli', 'connection', 'up', ssid], capture_output=True)

            # Kısa bir bekleme + IP almak için wlan0/wifi cihazını bekle
            wifi_device = None
            try:
                status_result = subprocess.run(
                    ['nmcli', '-t', '-f', 'ACTIVE,SSID,DEVICE', 'dev', 'wifi'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if status_result.returncode == 0:
                    for line in status_result.stdout.strip().split('\n'):
                        if line.startswith('yes:'):
                            parts = line.split(':')
                            if len(parts) >= 3:
                                wifi_device = parts[2]
                            break
            except Exception:
                wifi_device = None

            if not wifi_device:
                wifi_device = 'wlan0'

            wifi_ip = None
            for _ in range(10):
                ips = get_all_ips()
                wifi_ip = ips.get(wifi_device) or ips.get('wlan0')
                if wifi_ip:
                    break
                time.sleep(1)

            if wifi_ip:
                message = f'{ssid} ağına başarıyla bağlandı. IP: {wifi_ip}'
            else:
                message = f'{ssid} ağına bağlandı ancak IP alınamadı (DHCP bekleniyor).'

            emit('wifi_connect_response', {
                'success': True,
                'message': message,
                'ip': wifi_ip
            })
            logger.info(f"Successfully connected to {ssid} (Wi-Fi device: {wifi_device}, IP: {wifi_ip})")
        else:
            emit('wifi_connect_response', {
                'success': False, 
                'message': f'Bağlantı hatası: {result.stderr or result.stdout}'
            })
            logger.error(f"Wi-Fi connect failed for {ssid}: {result.stderr}")
            
    except Exception as e:
        logger.error(f"Wi-Fi connect error: {e}")
        emit('wifi_connect_response', {'success': False, 'message': str(e)})

@socketio.on('wifi_wps_pbc')
def handle_wifi_wps_pbc():
    """WPS Push Button Pairing başlat"""
    try:
        logger.info("Starting WPS PBC pairing...")
        emit('wifi_wps_progress', {'message': 'WPS Eşleşmesi başlatılıyor... Lütfen modemdeki butona basın.'})
        ok, msg, stage = _start_wps_pairing('wlan0')
        if ok:
            emit('wifi_wps_response', {
                'success': True, 
                'stage': stage or 'started',
                'message': msg
            })
        else:
            emit('wifi_wps_response', {
                'success': False,
                'stage': 'final',
                'message': msg
            })
    except Exception as e:
        logger.error(f"WPS error: {e}")
        emit('wifi_wps_response', {'success': False, 'stage': 'final', 'message': str(e)})

@socketio.on('wifi_status')
def handle_wifi_status():
    """Mevcut Wi-Fi bağlantı durumunu al"""
    try:
        # Daha detaylı bilgi al (active,ssid,device) - ip4 field bazı nmcli sürümlerinde desteklenmez
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'active,ssid,device', 'dev', 'wifi'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        status = {'connected': False, 'ssid': None, 'ip': None}
        
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line.startswith('yes:'):
                    parts = line.split(':')
                    # yes:SSID:DEVICE
                    if len(parts) >= 2:
                        device = parts[2] if len(parts) > 2 else 'wlan0'
                        status = {
                            'connected': True,
                            'ssid': parts[1],
                            'ip': None
                        }

                        ips = get_all_ips()
                        status['ip'] = ips.get(device) or ips.get('wlan0')
                        break

        # Fallback: NetworkManager "active" göstermiyorsa wpa_cli ile kontrol et
        if not status['connected']:
            try:
                wpa_cli = '/usr/sbin/wpa_cli' if os.path.exists('/usr/sbin/wpa_cli') else '/sbin/wpa_cli'
                if os.path.exists(wpa_cli):
                    cmd = [wpa_cli, '-i', 'wlan0']
                    if os.path.exists('/run/wpa_supplicant/wlan0'):
                        cmd.extend(['-p', '/run/wpa_supplicant'])
                    cmd.append('status')

                    wpa_result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    if wpa_result.returncode == 0:
                        wpa_state = None
                        wpa_ssid = None
                        for line in wpa_result.stdout.split('\n'):
                            if line.startswith('wpa_state='):
                                wpa_state = line.split('=', 1)[1].strip()
                            elif line.startswith('ssid='):
                                wpa_ssid = line.split('=', 1)[1].strip()
                        if wpa_state == 'COMPLETED' and wpa_ssid:
                            ips = get_all_ips()
                            status = {
                                'connected': True,
                                'ssid': wpa_ssid,
                                'ip': ips.get('wlan0')
                            }
            except Exception:
                pass
        
        emit('wifi_status_response', status)
    except Exception as e:
        logger.error(f"Wi-Fi status error: {e}")
        emit('wifi_status_response', {'connected': False, 'message': str(e)})

@socketio.on('wifi_disconnect')
def handle_wifi_disconnect():
    """Mevcut Wi-Fi bağlantısını kes"""
    try:
        # Already disconnected: return immediately to avoid long UI spinner.
        quick_state = subprocess.run(
            ['nmcli', '-t', '-f', 'DEVICE,TYPE,STATE', 'dev'],
            capture_output=True,
            text=True,
            timeout=4
        )
        if quick_state.returncode == 0:
            wifi_connected = False
            for line in quick_state.stdout.strip().split('\n'):
                parts = line.split(':')
                if len(parts) >= 3 and parts[1] == 'wifi' and parts[2] == 'connected':
                    wifi_connected = True
                    break
            if not wifi_connected:
                emit('wifi_disconnect_response', {'success': True, 'message': 'Wi-Fi zaten bağlı değil'})
                return

        # Aktif bağlantının adını bul (NetworkManager)
        active_result = subprocess.run(
            ['nmcli', '-t', '-f', 'DEVICE,TYPE,STATE,CONNECTION', 'dev'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        connection_name = None
        if active_result.returncode == 0:
            for line in active_result.stdout.strip().split('\n'):
                parts = line.split(':')
                if len(parts) >= 4 and parts[1] == 'wifi' and parts[2] == 'connected':
                    connection_name = parts[3]
                    break

        nm_success = False
        nm_err = None
        if connection_name:
            nm_result = subprocess.run(
                ['sudo', 'nmcli', 'con', 'down', connection_name],
                capture_output=True,
                text=True,
                timeout=8
            )
            if nm_result.returncode == 0:
                nm_success = True
            else:
                nm_err = (nm_result.stderr or nm_result.stdout or '').strip()

        if not nm_success:
            nm_result = subprocess.run(
                ['sudo', 'nmcli', 'dev', 'disconnect', 'wlan0'],
                capture_output=True,
                text=True,
                timeout=8
            )
            if nm_result.returncode == 0:
                nm_success = True
            else:
                nm_err = nm_err or (nm_result.stderr or nm_result.stdout or '').strip()

        wpa_success = False
        wpa_err = None
        try:
            wpa_cli = '/usr/sbin/wpa_cli' if os.path.exists('/usr/sbin/wpa_cli') else '/sbin/wpa_cli'
            if not os.path.exists(wpa_cli):
                wpa_cli = None
            if wpa_cli:
                cmd = ['sudo', wpa_cli, '-i', 'wlan0']
                if os.path.exists('/run/wpa_supplicant/wlan0'):
                    cmd.extend(['-p', '/run/wpa_supplicant'])
                cmd.append('disconnect')
                wpa_result = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
                if wpa_result.returncode == 0 and 'OK' in wpa_result.stdout:
                    wpa_success = True
                else:
                    wpa_err = (wpa_result.stderr or wpa_result.stdout or '').strip()
        except Exception as e:
            wpa_err = str(e)

        if nm_success or wpa_success:
            subprocess.run(['sudo', 'ip', 'route', 'del', 'default', 'dev', 'wlan0'], timeout=5)
            subprocess.run(['sudo', 'ip', 'addr', 'flush', 'dev', 'wlan0'], timeout=5)
            emit('wifi_disconnect_response', {'success': True, 'message': 'Bağlantı kesildi'})
        else:
            detail = nm_err or wpa_err
            msg = 'Bağlantı kesilemedi'
            if detail:
                msg = f'{msg}: {detail}'
            emit('wifi_disconnect_response', {'success': False, 'message': msg})
            
    except Exception as e:
        logger.error(f"Wi-Fi disconnect error: {e}")
        emit('wifi_disconnect_response', {'success': False, 'message': str(e)})

@socketio.on('get_settings')
def handle_get_settings(data=None):
    """Sistem ayarlarını gönder"""
    try:
        # Get local IP address
        def get_local_ip():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                return ip
            except Exception:
                return "Bilinmiyor"

        settings_data = {
            'hardware': {
                'gpio_available': GPIO_AVAILABLE,
                'cooling_available': GPIO_AVAILABLE  # Cooling requires GPIO
            },
            'sensors': {
                'dht_available': DHT_AVAILABLE,
                'oxygen_available': kuvoz_server.oxygen_sensor_available,
                'oxygen_library_available': OXYGEN_AVAILABLE,
                'co2_available': kuvoz_server.co2_sensor_available,
                'co2_library_available': CO2_AVAILABLE
            },
            'features': {
                'ai_available': AI_AVAILABLE,
                'logging_available': LOGGING_AVAILABLE
            },
            'settings': kuvoz_server.system_settings
        }

        emit('settings_response', settings_data)
        logger.info("Settings data sent to client")
    except Exception as e:
        logger.error(f"Get settings error: {e}")
        emit('error', {'message': f'Ayarlar yüklenemedi: {str(e)}'})

@socketio.on('save_settings')
def handle_save_settings_event(data):
    """Ayarları ve sistem tercihlerini kaydet event"""
    handle_save_settings_logic(data)

def handle_save_settings_logic(data):
    """Internal logic for saving settings"""
    try:
        if data:
            # Update slider values if provided
            if 'sliders' in data:
                kuvoz_server.slider_values.update(data['sliders'])
                logger.info("Updated sliders from save_settings")

            # Update button states if provided
            if 'buttons' in data:
                kuvoz_server.button_states.update(data['buttons'])
                logger.info("Updated buttons from save_settings")

            # Update system settings if provided (filter out top-level state)
            if 'system_settings' in data:
                sys_sett = data['system_settings'].copy()
                # Remove nested objects if they accidentally got cloned from state
                for key in ['sliders', 'buttons', 'gpio_outputs', 'sensors']:
                    if key in sys_sett:
                        del sys_sett[key]
                sys_sett.pop('soothing_audio_enabled', None)
                sys_sett.pop('soothing_audio_mode', None)
                if 'fan_output_mode' in sys_sett:
                    sys_sett['fan_output_mode'] = kuvoz_server.normalize_fan_output_mode(sys_sett['fan_output_mode'])
                kuvoz_server.system_settings.update(sys_sett)
                kuvoz_server.refresh_fan_output_mode()
                logger.info("Updated system settings (filtered)")

            if 'care_settings' in data and isinstance(data['care_settings'], dict):
                requested_mode = data['care_settings'].get('mode')
                if requested_mode is not None:
                    ok, reason = kuvoz_server.set_care_mode(requested_mode)
                    if not ok:
                        # Don't send error - frontend already checks auto_available
                        # Just return False to prevent save, UI will stay in current mode
                        logger.warning(f"Care mode change rejected: {reason}")
                        # Send current care status to revert UI to previous state
                        socketio.emit('care_settings_update', {
                            'care_settings': kuvoz_server.get_care_status(),
                            'sliders': kuvoz_server.get_effective_slider_values()
                        })
                        return False
                    logger.info(f"Updated care mode: {kuvoz_server.care_settings['mode']}")
            
            # Support for flat structure (sent by settings.html)
            flat_keys = ['cooling_enabled', 'dht_enabled', 'oxygen_enabled', 'co2_enabled', 'ai_enabled', 'logging_enabled', 'fan_output_mode']
            flat_settings = {}
            for key in flat_keys:
                if key in data:
                    flat_settings[key] = data[key]
            
            if flat_settings:
                if 'fan_output_mode' in flat_settings:
                    flat_settings['fan_output_mode'] = kuvoz_server.normalize_fan_output_mode(flat_settings['fan_output_mode'])
                kuvoz_server.system_settings.update(flat_settings)
                kuvoz_server.refresh_fan_output_mode()
                logger.info(f"Updated system settings from flat structure: {list(flat_settings.keys())}")
            
            # Special case for ai_enabled
            if 'ai_enabled' in data:
                kuvoz_server.ai_enabled = data['ai_enabled']
            elif 'system_settings' in data and 'ai_enabled' in data['system_settings']:
                kuvoz_server.ai_enabled = data['system_settings']['ai_enabled']

            kuvoz_server.apply_runtime_sensor_settings()

            # Save all states to file
            if kuvoz_server.save_settings():
                socketio.emit('settings_saved', {'message': 'Ayarlar başarıyla kaydedildi'})
                socketio.emit('status_response', {
                    'type': 'status_response',
                    'sensors': kuvoz_server.sensor_data,
                    'buttons': kuvoz_server.button_states,
                    'gpio_outputs': kuvoz_server.gpio_output_states,
                    'sliders': kuvoz_server.get_effective_slider_values(),
                    'timers': kuvoz_server.get_timer_data(),
                    'system': kuvoz_server.get_effective_system_status(),
                    'system_settings': kuvoz_server.system_settings,
                    'care_settings': kuvoz_server.get_care_status()
                })
                # Broadcast to all clients (broadcast=True not needed in threading mode)
                socketio.emit('care_settings_update', {
                    'care_settings': kuvoz_server.get_care_status(),
                    'sliders': kuvoz_server.get_effective_slider_values()
                })
                logger.info(f"✅ Settings saved to {SETTINGS_FILE}")

                # Sync to Firebase
                if kuvoz_server.firebase_manager:
                    kuvoz_server.firebase_manager.sync_controls(kuvoz_server.button_states, kuvoz_server.slider_values)
                    logger.info("✅ Firebase controls synced after save")

                return True
            else:
                socketio.emit('error', {'message': 'Ayarlar dosyaya yazılamadı'})
                return False
        else:
            # If no data provided, just trigger a save of current memory state
            if kuvoz_server.save_settings():
                socketio.emit('settings_saved', {'message': 'Ayarlar kaydedildi'})
                return True
            else:
                socketio.emit('error', {'message': 'Ayarlar kaydedilemedi'})
                return False
    except Exception as e:
        logger.error(f"Save settings logic error: {e}")
        socketio.emit('error', {'message': f'Hata: {str(e)}'})
        return False

@socketio.on('client_event')
def handle_client_event(data):
    """Client-side telemetry for kiosk debugging"""
    try:
        sid = request.sid
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip and ',' in ip:
            ip = ip.split(',')[0].strip()
        if sid in kuvoz_server.active_connections:
            kuvoz_server.active_connections[sid]['last_seen'] = time.time()
        event_type = data.get('type') if isinstance(data, dict) else None
        payload = data.get('payload') if isinstance(data, dict) else None
        kuvoz_server.note_local_kiosk_event(ip, event_type or 'client_event', payload=payload, sid=sid)
        logger.info(f"🧭 Client event from {ip}: {data}")
    except Exception as e:
        logger.error(f"Client event error: {e}")

@socketio.on('get_profile')
def handle_get_profile(data=None):
    """Kullanıcı profil bilgilerini gönder"""
    try:
        # Get local IP address
        def get_local_ip():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                return ip
            except Exception:
                return "Bilinmiyor"

        profile_data = {
            'company': dict(kuvoz_server.user_profile.get('company', {})),
            'contact': dict(kuvoz_server.user_profile.get('contact', {})),
            'device': dict(kuvoz_server.user_profile.get('device', {}))
        }

        # Update device info
        profile_data['device']['ip'] = get_local_ip()
        profile_data['device']['last_update'] = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

        # Add git version info and update diagnostics
        git_info = get_git_version_info()
        profile_data['device']['git_hash'] = git_info['hash']
        profile_data['device']['git_branch'] = git_info['branch']
        profile_data['update_diagnostics'] = get_git_update_diagnostics()

        emit('profile_response', profile_data)
        logger.info(f"Profile data sent to client (git: {git_info['hash']} on {git_info['branch']})")
    except Exception as e:
        logger.error(f"Get profile error: {e}")
        emit('error', {'message': f'Profil bilgileri yüklenemedi: {str(e)}'})

@socketio.on('save_profile')
def handle_save_profile(data):
    """Kullanıcı profil bilgilerini kaydet"""
    try:
        if data:
            # Update user profile
            if 'company' in data:
                kuvoz_server.user_profile['company'].update(data['company'])
            if 'contact' in data:
                kuvoz_server.user_profile['contact'].update(data['contact'])
            
            # Save to file
            if kuvoz_server.save_settings():
                emit('profile_saved', {'message': 'Profil bilgileri kaydedildi'})
                logger.info(f"User profile saved")
            else:
                emit('error', {'message': 'Profil bilgileri kaydedilemedi'})
        else:
            emit('error', {'message': 'Geçersiz veri'})
    except Exception as e:
        logger.error(f"Save profile error: {e}")
        emit('error', {'message': f'Profil bilgileri kaydedilemedi: {str(e)}'})

@socketio.on('update_patient_context')
def handle_update_patient_context(data):
    """Hasta bilgisi bağlamını AI modülüne aktar"""
    try:
        if not isinstance(data, dict):
            emit('error', {'message': 'Geçersiz hasta bilgisi'})
            return

        if kuvoz_server.update_patient_context(data):
            merged_patient = dict(kuvoz_server.current_patient) if isinstance(kuvoz_server.current_patient, dict) else {}
            merged_patient.update({
                key: value for key, value in data.items()
                if value is not None and str(value).strip() != ''
            })
            if _patient_record_has_content(merged_patient):
                merged_patient.setdefault('id', _build_patient_id(merged_patient))
                merged_patient.setdefault('savedAt', datetime.datetime.now().isoformat())
                kuvoz_server.current_patient = merged_patient

            kuvoz_server.save_settings()
            care_payload = {
                'success': True,
                'care_settings': kuvoz_server.get_care_status(),
                'sliders': kuvoz_server.get_effective_slider_values()
            }
            emit('patient_context_updated', care_payload)
            # Broadcast to all clients
            socketio.emit('care_settings_update', {
                'care_settings': kuvoz_server.get_care_status(),
                'sliders': kuvoz_server.get_effective_slider_values()
            })
            logger.info(
                f"🐾 Patient context updated: species={kuvoz_server.patient_context.get('species')}, "
                f"breed={kuvoz_server.patient_context.get('breed')}, "
                f"age={kuvoz_server.patient_context.get('age')}, "
                f"weight={kuvoz_server.patient_context.get('weight')}"
            )
        else:
            emit('error', {'message': 'Hasta bağlamı güncellenemedi'})
    except Exception as e:
        logger.error(f"Update patient context error: {e}")
        emit('error', {'message': f'Hasta bağlamı güncellenemedi: {str(e)}'})

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
    """Tailscale kurulumunu başlat - Non-blocking"""
    if not task_manager.start_task('tailscale_install'):
        emit('error', {'message': f'Şu anda başka bir işlem devam ediyor: {task_manager.current_task}'})
        return

    def run_install():
        try:
            # 1. Tailscale zaten yüklü mü kontrol et
            check_installed = subprocess.run(['which', 'tailscale'], capture_output=True, text=True)
            if check_installed.returncode == 0:
                socketio.emit('tailscale_install_response', {'success': False, 'message': 'Tailscale zaten kurulu'}, namespace='/')
                return
            
            # 2. Kurulum scriptini indir
            socketio.emit('tailscale_install_progress', {'message': 'Tailscale indiriliyor...'}, namespace='/')
            install_result = subprocess.run(
                ['curl', '-fsSL', 'https://tailscale.com/install.sh'],
                capture_output=True, text=True, timeout=60
            )
            
            if install_result.returncode != 0:
                socketio.emit('tailscale_install_response', {'success': False, 'message': 'Kurulum scripti indirilemedi'}, namespace='/')
                return

            # 3. Scripti çalıştır
            socketio.emit('tailscale_install_progress', {'message': 'Tailscale kuruluyor (birkaç dakika sürebilir)...'}, namespace='/')
            install_script = subprocess.run(
                ['sh', '-c', install_result.stdout],
                capture_output=True, text=True, timeout=300
            )
            
            if install_script.returncode == 0:
                socketio.emit('tailscale_install_response', {'success': True, 'message': 'Tailscale başarıyla kuruldu'}, namespace='/')
            else:
                stderr_content = install_script.stderr or ""
                stdout_content = install_script.stdout or ""
                combined_output = stderr_content + stdout_content
                
                if "No space left on device" in combined_output:
                    error_msg = "❌ Cihazda yeterli yer yok! 'Disk Temizle' butonunu kullanın."
                else:
                    error_msg = f'Kurulum hatası: {stderr_content[:200]}'
                
                socketio.emit('tailscale_install_response', {'success': False, 'message': error_msg}, namespace='/')

        except subprocess.TimeoutExpired:
            socketio.emit('tailscale_install_response', {'success': False, 'message': 'Kurulum zaman aşımına uğradı (5 dk).'}, namespace='/')
        except Exception as e:
            logger.error(f'Tailscale install error: {e}')
            socketio.emit('error', {'message': f'Kurulum sırasında kritik hata: {str(e)}'}, namespace='/')
        finally:
            task_manager.end_task()

    threading.Thread(target=run_install, daemon=True).start()

@socketio.on('disk_cleanup')
def handle_disk_cleanup(data=None):
    """Sistem disk temizliğini başlat (make disk-clean)"""
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
             
    except Exception as e:
        logger.error(f"Disk cleanup error: {e}")
        emit('error', {'message': f'Disk temizleme hatası: {str(e)}'})

@socketio.on('system_update')
def handle_system_update(data=None):
    """Sistem güncellemesini başlat (git pull) - Gelişmiş versiyon"""
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
            cwd=SCRIPT_DIR
        )

        if fetch_result.returncode != 0:
            error_type, user_message, error_output = _classify_git_update_error(
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
            cwd=SCRIPT_DIR
        )

        if merge_result.returncode != 0:
            error_type, user_message, error_output = _classify_git_update_error(
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
                cwd=SCRIPT_DIR
            )
            requirements_changed = requirements_diff.returncode == 0 and bool(requirements_diff.stdout.strip())

        if requirements_changed:
            emit('system_update_progress', {'message': 'Yeni bağımlılıklar kuruluyor (pip install)...'})
            logger.info("📦 requirements.txt changed, running pip install...")

            pip_cmd = [sys.executable, '-m', 'pip', 'install', '-r', os.path.join(SCRIPT_DIR, 'requirements.txt'), '--break-system-packages']

            pip_result = subprocess.run(
                pip_cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=SCRIPT_DIR
            )

            if pip_result.returncode != 0:
                logger.error(f"❌ Pip install failed: {pip_result.stderr}")
                emit('system_update_progress', {'message': '⚠️ Kütüphaneler güncellenirken hata oluştu.'})

        msg = 'Sistem başarıyla güncellendi.'
        if git_info_before['hash'] == git_info_after['hash']:
            msg = 'Sistem zaten güncel.'
        else:
            msg = f'Sistem güncellendi: {git_info_before["hash"]} → {git_info_after["hash"]}. Servis yeniden başlatılmalı.'

        emit('system_update_response', {
            'success': True,
            'message': msg,
            'git_hash': git_info_after['hash'],
            'git_branch': git_info_after['branch'],
            'needs_restart': git_info_before['hash'] != git_info_after['hash'],
            'diagnostics': get_git_update_diagnostics()
        })
        logger.info(f"✅ System update completed: {msg}")

    except Exception as e:
        logger.error(f"System update error: {e}")
        emit('error', {'message': f'Gelişmiş güncelleme hatası: {str(e)}'})

@socketio.on('system_reset')
def handle_system_reset(data=None):
    """Sistem güncellemesini geri al (git reset --hard) - Gelişmiş versiyon"""
    try:
        emit('system_reset_progress', {'message': 'Değişiklikler temizleniyor ve geri dönülüyor...'})
        logger.info("⏪ Starting robust system reset (git reset --hard)...")
        
        # 1. Önce HEAD@{1}'e dönmeyi dene (pull öncesi durum)
        reset_result = subprocess.run(
            ['git', 'reset', '--hard', 'HEAD@{1}'],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=SCRIPT_DIR
        )
        
        if reset_result.returncode == 0:
            # 2. Üzerine bir de clean yapalım (untacked dosyalar için)
            subprocess.run(['git', 'clean', '-fd'], capture_output=True, cwd=SCRIPT_DIR)
            
            git_info = get_git_version_info()
            emit('system_reset_response', {
                'success': True,
                'message': f'Sistem bir önceki sürüme döndürüldü: {git_info["hash"]}',
                'git_hash': git_info['hash'],
                'diagnostics': get_git_update_diagnostics()
            })
            logger.info(f"✅ System reset completed: {git_info['hash']}")
        else:
            # 3. Eğer HEAD@{1} yoksa (ilk pull öncesi), sadece mevcut durumu temizleyelim
            subprocess.run(['git', 'reset', '--hard', 'HEAD'], capture_output=True, cwd=SCRIPT_DIR)
            subprocess.run(['git', 'clean', '-fd'], capture_output=True, cwd=SCRIPT_DIR)
            emit('system_reset_response', {
                'success': False,
                'message': f'Tam geri dönme başarısız olsa da yerel değişiklikler temizlendi: {reset_result.stderr}',
                'diagnostics': get_git_update_diagnostics()
            })
            
    except Exception as e:
        logger.error(f"System reset error: {e}")
        emit('error', {'message': f'Geri alma hatası: {str(e)}'})

@socketio.on('tailscale_connect')
def handle_tailscale_connect():
    """Tailscale bağlantısı başlat ve auth URL oluştur - Non-blocking"""
    if not task_manager.start_task('tailscale_connect'):
        emit('error', {'message': f'İşlem reddedildi. Şu anda devam eden işlem: {task_manager.current_task}'})
        return

    def run_connect():
        try:
            logger.info('Tailscale connect process started in background...')
            
            # 1. Mevcut durumu kontrol et
            status_check = subprocess.run(['tailscale', 'status', '--json'], capture_output=True, text=True, timeout=20)
            if status_check.returncode == 0:
                status_data = json.loads(status_check.stdout)
                if status_data.get('BackendState') == 'Running':
                    socketio.emit('tailscale_connect_response', {'success': True, 'already_connected': True, 'message': 'Tailscale zaten bağlı'}, namespace='/')
                    task_manager.end_task()
                    return

            # 2. Bağlantıyı başlat (sudo tailscale up)
            socketio.emit('tailscale_install_progress', {'message': 'Bağlantı başlatılıyor...'}, namespace='/')
            result = subprocess.run(
                ['sudo', 'tailscale', 'up', '--reset', '--timeout=10s'],
                capture_output=True, text=True, timeout=30
            )
            
            output = result.stdout + result.stderr
            url_pattern = r'https://login\.tailscale\.com/a/[a-z0-9]+'
            match = re.search(url_pattern, output)
            
            if match:
                auth_url = match.group(0)
                qr_code_data = None
                if QRCODE_AVAILABLE:
                    try:
                        qr = qrcode.QRCode(version=1, box_size=10, border=4)
                        qr.add_data(auth_url)
                        qr.make(fit=True)
                        img = qr.make_image(fill_color="black", back_color="white")
                        buffered = BytesIO()
                        img.save(buffered, format="PNG")
                        # Get bytes and encode to base64
                        img_bytes = buffered.getvalue()
                        qr_code_data = f"data:image/png;base64,{base64.b64encode(img_bytes).decode('utf-8')}"
                        logger.info(f"✅ QR code generated: {len(qr_code_data)} bytes")
                    except Exception as e:
                        logger.error(f'QR generation error: {e}', exc_info=True)
                
                socketio.emit('tailscale_auth_url', {'url': auth_url, 'qr_code': qr_code_data}, namespace='/')
                task_manager.end_task()
                return

            # 3. Auth URL yoksa son durumu kontrol et
            time.sleep(2)
            final_status = subprocess.run(['tailscale', 'status', '--json'], capture_output=True, text=True, timeout=10)
            if final_status.returncode == 0:
                status_data = json.loads(final_status.stdout)
                if status_data.get('BackendState') == 'Running':
                    socketio.emit('tailscale_connect_response', {'success': True, 'message': 'Bağlantı başarılı'}, namespace='/')
                else:
                    # Bağlantı başlatıldı ama henüz aktif değil - status polling devam edecek
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
        except Exception as e:
            logger.error(f'Tailscale connect thread error: {e}')
            socketio.emit('tailscale_connect_response', {
                'success': False, 
                'message': f'Bağlantı hatası: {str(e)}'
            }, namespace='/')
        finally:
            task_manager.end_task()

    threading.Thread(target=run_connect, daemon=True).start()

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

@socketio.on('tailscale_logout')
def handle_tailscale_logout():
    """Tailscale oturumunu kapat ve yeni tailnet için hazırla"""
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

    except Exception as e:
        logger.error(f'Tailscale logout error: {e}')
        emit('tailscale_logout_response', {
            'success': False,
            'message': f'Oturum kapatma hatası: {str(e)}'
        })

@socketio.on('tailscale_invite_users_qr')
def handle_tailscale_invite_users_qr(data=None):
    """Tailscale Users ekranı için QR kod oluştur"""
    invite_url = 'https://login.tailscale.com/admin/users'
    try:
        qr_code_data = None
        if QRCODE_AVAILABLE:
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(invite_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            qr_code_data = f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode('utf-8')}"

        emit('tailscale_invite_users_qr_response', {
            'success': True,
            'url': invite_url,
            'qr_code': qr_code_data
        })
    except Exception as e:
        logger.error(f'Tailscale invite QR error: {e}')
        emit('tailscale_invite_users_qr_response', {
            'success': False,
            'message': f'QR oluşturulamadı: {str(e)}'
        })

@socketio.on('tailscale_funnel_enable')
def handle_tailscale_funnel_enable(data=None):
    """Tailscale Funnel'ı aktifleştir"""
    try:
        logger.info('Enabling Tailscale Funnel for port 8000')
        
        # DNS adını al
        hostname_result = subprocess.run(
            ['tailscale', 'status', '--json'],
            capture_output=True,
            text=True,
            timeout=5
        )
        hostname = 'kuvoz'
        dns_name = 'kuvoz.tailnet.ts.net'
        
        if hostname_result.returncode == 0:
            status_data = json.loads(hostname_result.stdout)
            hostname = status_data.get('Self', {}).get('HostName', 'kuvoz')
            dns_name_raw = status_data.get('Self', {}).get('DNSName', '')
            dns_name = dns_name_raw.rstrip('.')
        
        logger.info(f'Hostname: {hostname}, DNS: {dns_name}')
        
        # Önce mevcut konfigürasyonu temizle
        subprocess.run(
            ['sudo', 'tailscale', 'funnel', 'reset'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Yeni Tailscale Funnel komutu (v1.38+ - doğrudan funnel kullan)
        # Eski: tailscale serve + tailscale funnel 443 on
        # Yeni: tailscale funnel --bg 8000 (tek komut)
        result = subprocess.run(
            ['sudo', 'tailscale', 'funnel', '--bg', '8000'],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        logger.info(f'Funnel result: {result.returncode}, stdout: {result.stdout}, stderr: {result.stderr}')
        
        # Eğer enable edilmemişse URL döndür
        if 'not enabled' in result.stderr or 'not enabled' in result.stdout:
            import re
            enable_url_match = re.search(r'https://login\.tailscale\.com/[^\s]+', result.stderr + result.stdout)
            enable_url = enable_url_match.group(0) if enable_url_match else 'https://login.tailscale.com/admin/machines'
            
            emit('tailscale_funnel_enable_required', {
                'success': False,
                'enable_url': enable_url,
                'message': 'Funnel tailnet\'te aktif değil. Lütfen enable edin.'
            })
            return
        
        time.sleep(1)
        
        # Status ile kontrol et
        status_result = subprocess.run(
            ['tailscale', 'funnel', 'status'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        output = status_result.stdout + status_result.stderr
        logger.info(f'Funnel status: {output}')
        
        # URL https://<dns_name> formatında (port 8000 DEĞİL!)
        funnel_url = f'https://{dns_name}'
        
        # SSH için Tailscale IP'sini al (DNS çalışmayabilir)
        tailscale_ip = None
        if hostname_result.returncode == 0 and status_data:
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
            
    except Exception as e:
        logger.error(f'Tailscale funnel enable error: {e}')
        emit('error', {'message': f'Funnel hatası: {str(e)}'})

@socketio.on('tailscale_funnel_disable')
def handle_tailscale_funnel_disable(data=None):
    """Tailscale Funnel'ı devre dışı bırak"""
    try:
        logger.info('Disabling Tailscale Funnel')
        
        # Funnel kapat (v1.38+ yeni syntax)
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
            
    except Exception as e:
        logger.error(f'Tailscale funnel disable error: {e}')
        emit('error', {'message': f'Funnel kapatma hatası: {str(e)}'})

@socketio.on('tailscale_funnel_status')
def handle_tailscale_funnel_status(data=None):
    """Funnel durumunu kontrol et"""
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
            # URL'yi bul
            import re
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
            
    except Exception as e:
        logger.error(f'Tailscale funnel status error: {e}')
        emit('tailscale_funnel_response', {
            'success': True,
            'enabled': False
        })

@socketio.on('tailscale_create_share')
def handle_tailscale_create_share(data=None):
    """Tailscale üzerinden uzak yardım linki oluştur"""
    try:
        logger.info('Creating Tailscale share link for remote support')
        
        # Önce Tailscale bağlı mı kontrol et
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
        
        # IP adresini al
        self_info = status_data.get('Self', {})
        tailscale_ips = self_info.get('TailscaleIPs', [])
        hostname = self_info.get('HostName', 'kuvoz')
        
        if not tailscale_ips:
            emit('error', {'message': 'Tailscale IP adresi bulunamadı'})
            return
        
        # İlk IPv4 adresini kullan
        tailscale_ip = tailscale_ips[0]
        
        # Funnel özelliğini aktifleştir (public erişim için)
        # NOT: Funnel yerine serve kullanıyoruz (daha güvenli, sadece tailscale ağından)
        logger.info('Creating Tailscale serve configuration for port 8000')
        
        serve_result = subprocess.run(
            ['sudo', 'tailscale', 'serve', 'status', '--json'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Erişim URL'lerini oluştur
        web_url = f'http://{tailscale_ip}:8000'
        
        # Admin paneli için özel link (sadece Tailscale ağından)
        admin_url = f'https://{hostname}.tailnet.ts.net:8000'  # HTTPS Tailscale Magic DNS
        
        # Paylaşım bilgilerini oluştur
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
    except Exception as e:
        logger.error(f'Tailscale create share error: {e}')
        emit('error', {'message': f'Paylaşım linki oluşturulamadı: {str(e)}'})

# ============================================================================
# WEBSOCKET EVENT HANDLERS (DEVAM)
# ============================================================================

@socketio.on('message')
def handle_message(data):
    """WebSocket mesajları"""
    try:
        command = data.get('command')
        command_data = data.get('data', {})
        logger.info(f"📥 Received command: {command} with data: {command_data}")
        
        if command == 'get_status':
            response = {
                'type': 'status_response',
                'sensors': kuvoz_server.sensor_data,
                'buttons': kuvoz_server.button_states,
                'gpio_outputs': kuvoz_server.gpio_output_states,
                'sliders': kuvoz_server.get_effective_slider_values(),
                'timers': kuvoz_server.get_timer_data(),
                'system': kuvoz_server.get_effective_system_status(),
                'system_settings': kuvoz_server.system_settings,
                'care_settings': kuvoz_server.get_care_status()
            }
            logger.info(f"📤 Sending status_response to client. Sliders: {kuvoz_server.slider_values}")
            emit('status_response', response)
        
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
            # Shutdown işlemi
            threading.Timer(2.0, lambda: os.system("sudo shutdown -h now")).start()
        
        elif command == 'restart':
            logger.info("Restart requested")
            kuvoz_server.save_settings()
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
    """Get the primary local network IP address (prefers ethernet then wifi)"""
    try:
        ips = get_all_ips()
        if 'eth0' in ips: return ips['eth0']
        if 'wlan0' in ips: return ips['wlan0']
        if 'tailscale0' in ips: return ips['tailscale0']
        
        # Fallback to general socket method
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

def get_all_ips():
    """Get all local interface IPs as a dictionary"""
    ips = {}
    try:
        # nmcli preferred for modern Linux
        result = subprocess.run(['nmcli', '-t', '-f', 'DEVICE,IP4.ADDRESS', 'dev', 'show'], 
                                capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            device = None
            for line in result.stdout.split('\n'):
                if not line: continue
                if ': ' not in line and ':' in line: # DEVICE:eth0 type line
                    parts = line.split(':')
                    if parts[0] == 'GENERAL.DEVICE':
                        device = parts[1]
                    elif parts[0] == 'IP4.ADDRESS[1]':
                        ip = parts[1].split('/')[0]
                        if device: ips[device] = ip
        
        # If nmcli failed or empty, fallback to ip addr (more universal)
        if not ips:
            import re
            result = subprocess.run(['ip', '-4', '-o', 'addr', 'show'], 
                                    capture_output=True, text=True, timeout=5)
            for line in result.stdout.split('\n'):
                # format: idx: name inet ip/mask ...
                m = re.search(r'\d+:\s+(\w+).*inet\s+([\d\.]+)', line)
                if m:
                    if m.group(1) != 'lo':
                        ips[m.group(1)] = m.group(2)
    except Exception:
        pass
    return ips

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
