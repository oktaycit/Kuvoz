# Kuvoz Veterinary Incubator Control System

## Project Overview

**Kuvoz** is a Raspberry Pi-based veterinary incubator control system designed for post-operative care and rehabilitation of pets (primarily dogs and cats) in veterinary clinics. The system manages environmental conditions (temperature, humidity, oxygen), controls medical equipment via GPIO relays, and provides a modern web-based monitoring interface with real-time WebSocket communication.

### Key Features

- **Environmental Control**: Temperature, humidity, and oxygen monitoring with automated control
- **9-Channel GPIO Relay**: Controls lighting, nebulizer, heating, cooling, fans, UV/ozone sterilization
- **Web Interface**: Modern HTML5/CSS3/JavaScript dashboard with WebSocket real-time updates
- **Kiosk Mode**: Chromium fullscreen display for clinical monitoring
- **Sensor Support**: DHT11/DHT22 (temperature/humidity), DFRobot Oxygen (I2C), SCD41 (CO2)
- **Firebase Integration**: Optional cloud connectivity for remote monitoring
- **AI-Powered Alerts**: Dynamic vital threshold adjustment and intelligent alert system

### Technology Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Python 3.11+ / Flask / Flask-SocketIO |
| **Frontend** | Vanilla JavaScript (ES6+) / HTML5 / CSS3 |
| **Hardware** | Raspberry Pi OS Trixie (Debian 13.1) |
| **GPIO** | RPi.GPIO library (BCM pin numbering) |
| **Sensors** | DHT_Native (custom), DFRobot_Oxygen, SCD41 |
| **Deployment** | systemd services, Chromium kiosk mode |
| **Database** | JSON file storage (`failure.dat`) |

## Architecture

### Backend (`web_server.py`)

Multi-threaded Flask application with the following components:

```
Main Thread (Flask Web Server)
├── WebSocket Handler (Socket.IO)
├── Sensor Reading Thread (15s interval)
│   ├── DHT22 temperature/humidity
│   ├── DFRobot Oxygen (I2C)
│   └── SCD41 CO2 sensor
└── Control Logic Thread (5s interval)
    ├── Temperature/humidity control
    ├── Nebulizer duty cycles
    ├── Ozone sterilization
    └── Cooling system management
```

**Key Class**: `KuvozServer`
- Hardware initialization with feature flags (`GPIO_AVAILABLE`, `DHT_AVAILABLE`, `OXYGEN_AVAILABLE`, `CO2_AVAILABLE`)
- Thread-safe GPIO operations via `safe_gpio_output(pin, state)`
- Settings persistence in JSON format
- Adaptive ozone control based on oxygen sensor availability

### Frontend (`web/`)

**Key Class**: `KuvozController` (`web/script.js`)
- WebSocket connection management with auto-reconnect
- Real-time sensor display updates
- User input handling (buttons, sliders)
- Dynamic UI adaptation based on sensor availability

### GPIO Pin Mapping

```python
# 9-Channel Relay (BCM GPIO numbers)
outChannels = [5, 6, 13, 16, 19, 20, 21, 26, 12]

# Pin  | Physical | Function
# -----|----------|----------------------------------
# GP5  | Pin 29   | B1: Therapeutic Lighting
# GP6  | Pin 31   | B2: Nebulizer (respiratory therapy)
# GP13 | Pin 33   | B3: Humidity Control
# GP16 | Pin 36   | B4: Heating Pad (Carbon)
# GP19 | Pin 35   | B5: IR Heater
# GP20 | Pin 38   | B6: Ventilation Fan
# GP21 | Pin 40   | B7: UV Sterilization
# GP26 | Pin 37   | B8: Ozone Sterilizer
# GP12 | Pin 32   | B9: Cooling System

# Sensor Pins
pinDht = 15        # DHT22 data pin (Physical Pin 10)
I2C: SDA=GPIO2, SCL=GPIO3  # Oxygen sensor, CO2 sensor
```

## Directory Structure

```
kuvoz/
├── web/                        # Frontend web interface
│   ├── index.html             # Main dashboard
│   ├── help.html              # Help documentation
│   ├── settings.html          # Settings page
│   ├── alerts.html            # AI alerts display
│   ├── patient_info.html      # Patient information
│   ├── styles.css             # Main styles
│   ├── script.js              # Frontend controller
│   └── socket.io.min.js       # Socket.IO client
├── lib/                        # Sensor libraries
│   ├── DHT_Native.py          # Custom DHT11/DHT22 driver
│   ├── DFRobot_Oxygen.py      # I2C oxygen sensor
│   ├── SCD41_Sensor.py        # SCD41 CO2 sensor
│   └── ai/                    # AI module
├── systemd/                    # systemd service files
│   ├── kuvoz-web.service      # Web server service
│   └── kuvoz-kiosk.service    # Kiosk mode service
├── scripts/                    # Shell scripts
│   ├── start-kiosk.sh         # Kiosk launcher
│   └── setup-*.sh             # Setup scripts
├── docs/                       # Documentation
│   ├── INDEX.md               # Documentation index
│   ├── KUVOZ_KULLANIM_KLAVUZU.md  # User manual
│   ├── AI_ALERTS.md           # AI alert system
│   └── ...                    # More docs
├── config/                     # Configuration files
│   └── failure.dat            # Settings storage (JSON)
├── web_server.py              # Main Flask application
├── firebase_bridge.py         # Firebase integration
├── Makefile                   # Build automation
├── requirements.txt           # Python dependencies
└── QWEN.md                    # This file
```

## Building and Running

### Quick Start

```bash
# Full automated setup (recommended for new installations)
make auto-setup

# This will:
# 1. Install web dependencies
# 2. Set up systemd services
# 3. Configure kiosk mode
# 4. Start all services
```

### Manual Setup

```bash
# Install system dependencies
make system-deps

# Install Python dependencies
make web-deps

# Configure system (I2C, GPIO permissions)
make config

# Test hardware
make test

# Start web server (development mode)
make web-dev
# OR directly: python3 web_server.py

# Start kiosk mode (separate terminal)
make kiosk-manual
```

### Service Management

```bash
# Start/stop all services
make start-all
make stop-all
make restart-all

# Individual services
make web-start        # Web server
make web-stop
make kiosk-start      # Kiosk mode
make kiosk-stop

# Check status
make status-all
make logs-web         # Web server logs
make logs-kiosk       # Kiosk logs
```

### Testing

```bash
# Full system test
make test

# Individual sensor tests
make test-dht         # DHT sensor
make test-oxygen      # Oxygen sensor
make test-scd41       # CO2 sensor
make gpio-test        # GPIO functionality

# Web interface test
make web-test
```

## Development Conventions

### WebSocket Protocol (Critical - DO NOT BREAK)

**Server → Client events:**
```javascript
'sensor_update'     // Sensor data: {sensors: {temperature, humidity, oxygen, co2}}
'button_update'     // Button state: {name: "b1", state: true}
'timer_update'      // Timer state: {nebulizer: {...}, ozone: {...}}
'status_response'   // Full system status
'ai_alert'          // AI-generated alert
```

**Client → Server events:**
```javascript
'get_status'        // Request full status
'toggle_button'     // Toggle GPIO: {name: "b1", pin: 5, state: true}
'update_slider'     // Update slider: {name: "sld1", value: 30}
'save_settings'     // Save current configuration
```

### Hardware Access Pattern

All hardware operations MUST:
1. Check feature flags first: `if GPIO_AVAILABLE:`, `if DHT_AVAILABLE:`
2. Use thread-safe wrappers: `self.safe_gpio_output(pin, state)`
3. Handle exceptions gracefully with fallback to simulation mode

Example:
```python
def control_heating(self, enable):
    if not GPIO_AVAILABLE:
        logger.info(f"Simulation: Heating {'ON' if enable else 'OFF'}")
        return
    try:
        self.safe_gpio_output(16, GPIO.HIGH if enable else GPIO.LOW)
    except Exception as e:
        logger.error(f"Heating control error: {e}")
```

### Settings Management

**Configuration file**: `failure.dat` (JSON format)

**Slider IDs** (DO NOT change without updating both backend and frontend):
```python
'sld1': Nebulizer interval (minutes)
'sld2': Humidity target (%)
'sld3': Temperature target (°C)
'sld4': IR Temperature target (°C)
'sld5': Ozone interval (minutes)
'sld6': Nebulizer hours interval
'sld7': Ozone hours interval
'sld8': Nebulizer duty time (min)
'sld9': Nebulizer free time (min)
'sld10': Ozone duty time (min)
'sld11': Ozone free time (min)
```

### Coding Style

- **Language**: Turkish comments and documentation (per user preference)
- **Python**: PEP 8 compliant, type hints where applicable
- **JavaScript**: ES6+ with classes, async/await for async operations
- **Error Handling**: Graceful degradation with simulation mode fallbacks

## Key Configuration Files

### systemd Services

**Web Server** (`systemd/kuvoz-web.service`):
```ini
[Unit]
Description=Kuvoz Incubator Web Server
After=network.target

[Service]
Type=simple
User=vet
WorkingDirectory=/home/vet/kuvoz
ExecStart=/usr/bin/python3 /home/vet/kuvoz/web_server.py
Restart=always
SupplementaryGroups=gpio i2c spi

[Install]
WantedBy=multi-user.target
```

### Python Dependencies (`requirements.txt`)

```
flask
flask-socketio
eventlet
firebase-admin
rpi.gpio; platform_system=="Linux"
qrcode[pil]
pillow
adafruit-circuitpython-scd4x; platform_system=="Linux"
smbus2; platform_system=="Linux"
```

## Troubleshooting

### Common Issues

**GPIO Permission Error:**
```bash
# Add user to gpio and i2c groups
sudo usermod -a -G gpio,i2c $USER
sudo reboot
```

**DHT Sensor Not Reading:**
```bash
# Test DHT sensor
make test-dht

# Check pin connection (GPIO 15)
# Verify 3.3V-5V power to sensor
```

**Web Server Not Starting:**
```bash
# Check service status
make web-status

# View logs
make logs-web

# Manual start for debugging
python3 web_server.py
```

**Kiosk Mode Issues:**
```bash
# Check display
echo $DISPLAY

# Test X11
xhost +local:

# Manual kiosk start
make kiosk-manual
```

### Platform-Specific Notes

**Raspberry Pi OS Trixie (Debian 13.1):**
- Adafruit_DHT library incompatible - use `DHT_Native` exclusively
- Use system packages when possible: `make install-system`
- Chromium kiosk mode requires specific flags for Wayland compatibility

## Documentation

- **[docs/INDEX.md](docs/INDEX.md)** - Complete documentation index
- **[README_WEB.md](README_WEB.md)** - Web interface overview
- **[KUVOZ_KULLANIM_KLAVUZU.md](docs/KUVOZ_KULLANIM_KLAVUZU.md)** - User manual (Turkish)
- **[CLAUDE.md](CLAUDE.md)** - AI assistant guidelines
- **[SYSTEM_REQUIREMENTS.md](docs/SYSTEM_REQUIREMENTS.md)** - Hardware/software requirements
- **[MAINTENANCE.md](docs/MAINTENANCE.md)** - Maintenance procedures

## User Information

- **Output Language**: Turkish (for all user-facing output)
- **Development Environment**: MacBook (remote development via SSH)
- **Target Environment**: Raspberry Pi (production)
- **Default User**: `vet` (password: `vetmarketi`)

## Quick Reference

```bash
# Most common commands
make auto-setup      # Full automated installation
make web-start       # Start web server
make kiosk-start     # Start kiosk mode
make status-all      # Check all services
make logs-all        # View all logs
make restart-all     # Restart everything

# Access web interface
# Local: http://localhost:8000
# Network: http://[raspberry-pi-ip]:8000
```
