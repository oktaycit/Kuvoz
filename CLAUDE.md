# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Kuvoz** is a Raspberry Pi-based veterinary incubator control system for post-operative care and rehabilitation of pets (dogs/cats) in veterinary clinics. The system manages environmental conditions (temperature, humidity, oxygen), controls medical equipment via 8-channel GPIO relays, and provides a web-based monitoring interface with real-time WebSocket communication.

**Technology Stack:**
- Backend: Python 3.9+ / Flask / Flask-SocketIO
- Frontend: Vanilla JavaScript (ES6+) / HTML5 / CSS3
- Hardware: Raspberry Pi OS Trixie, RPi.GPIO, DHT sensors, I2C oxygen sensor
- Deployment: systemd services, Chromium kiosk mode

## Architecture Overview

### Multi-threaded Backend ([web_server.py](web_server.py))

```
Main Thread (Flask)
├── WebSocket Handler (Socket.IO)
├── Sensor Reading Thread (15s interval)
│   └── DHT22 + Optional Oxygen sensor
└── Control Logic Thread (5s interval)
    ├── Temperature/Humidity control
    ├── Nebulizer duty cycles
    └── Ozone sterilization
```

**Key Backend Class:** `KuvozServer`
- Hardware initialization with feature flags: `GPIO_AVAILABLE`, `DHT_AVAILABLE`, `OXYGEN_AVAILABLE`
- Thread-safe GPIO operations via `safe_gpio_output(pin, state)`
- Settings persistence in JSON format ([failure.dat](failure.dat))
- Adaptive ozone control based on oxygen sensor availability

### Frontend Architecture ([web/script.js](web/script.js))

**Key Frontend Class:** `KuvozController`
- WebSocket connection management with auto-reconnect
- Real-time sensor display updates
- User input handling (buttons, sliders)
- Dynamic UI adaptation based on sensor availability

### GPIO Pin Mapping (8-Channel Relay)

```python
outChannels = [5, 6, 13, 16, 19, 20, 21, 26]  # BCM GPIO numbers

# Pin  | Physical | Function
# -----|----------|-----------------------------
# GP5  | Pin 29   | B1: Therapeutic Lighting
# GP6  | Pin 31   | B2: Nebulizer (respiratory therapy)
# GP13 | Pin 33   | B3: Humidity Control
# GP16 | Pin 36   | B4: Heating Pad
# GP19 | Pin 35   | B5: IR Heater
# GP20 | Pin 38   | B6: Ventilation Fan
# GP21 | Pin 40   | B7: UV Sterilization
# GP26 | Pin 37   | B8: Ozone Sterilizer
```

**Sensor Pins:**
- DHT sensor: GPIO 15 (Physical Pin 10)
- I2C (oxygen): SDA=GPIO2 (Pin 3), SCL=GPIO3 (Pin 5)

## Development Environment

- Development Environment: MacBook
- Application Environment: Raspberry Pi
- SSH Access: `ssh oktay@raspberrypi`
- File Transfer: Use `scp` to transfer files between development and application environments
- Project Backup: Use GitHub for version control and backup

## Common Development Commands

### Build and Run

```bash
# Full automated setup
make auto-setup

# Development server (no systemd)
make web-dev
# OR directly: python3 web_server.py

# Manual debug server (port 8080)
python3 web_debug_server.py
```

### Testing

```bash
# System and hardware tests
make test

# Individual sensor tests
make test-dht          # DHT sensor
make test-oxygen       # Oxygen sensor
make test-gpio         # GPIO functionality

# Web interface test
make web-test
```

### Service Management

```bash
# Start/stop services
make start-all         # Start all services
make stop-all          # Stop all services
make restart-all       # Restart all services
make status-all        # Check all service status

# Individual services
make web-start         # Web server only
make kiosk-start       # Kiosk mode only

# View logs
make logs-all
journalctl -u kuvoz-web -f    # Web server logs
```

### Maintenance

```bash
# Backup/restore settings
make backup
make restore

# Clean temporary files
make clean

# Troubleshooting
make troubleshoot
make debug-trixie      # Raspberry Pi OS Trixie specific
```

## Critical Development Guidelines

### WebSocket Protocol (DO NOT BREAK)

**Server → Client events:**
```javascript
'sensor_update'     // Sensor data: {sensors: {temperature, humidity, oxygen}}
'button_update'     // Button state: {name: "b1", state: true}
'timer_update'      // Timer state: {nebulizer: {...}, ozone: {...}}
'status_response'   // Full system status
```

**Client → Server events:**
```javascript
'get_status'        // Request full status
'toggle_button'     // Toggle GPIO: {name: "b1", pin: 5, state: true}
'update_slider'     // Update slider: {name: "sld1", value: 30}
'save_settings'     // Save current configuration
```

**DO NOT rename or remove these event names without updating both [web_server.py](web_server.py) and [web/script.js](web/script.js).**

### Hardware Access Pattern

All hardware operations MUST:
1. Check feature flags first: `if GPIO_AVAILABLE:`, `if DHT_AVAILABLE:`, `if oxygen_sensor_available:`
2. Use thread-safe wrappers: `self.safe_gpio_output(pin, state)` instead of direct RPi.GPIO calls
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

**Configuration file:** [failure.dat](failure.dat) (JSON format)

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

**Button IDs:** `b1` through `b8` (mapped to GPIO channels)

### Sensor Libraries

**DHT Sensor:** Use `DHT_Native` library ([lib/DHT_Native.py](lib/DHT_Native.py))
- Adafruit_DHT is disabled due to platform issues
- Supports DHT11 and DHT22 with auto-detection
- Thread-safe, platform-independent

**Oxygen Sensor:** DFRobot I2C sensor ([lib/DFRobot_Oxygen.py](lib/DFRobot_Oxygen.py))
- Optional - system adapts if sensor is not present
- When available: enables intelligent ozone control based on O2 levels
- When absent: falls back to time-based ozone control

### Adaptive Ozone Control Logic

The system has two ozone control modes:

**With Oxygen Sensor** (intelligent mode):
```python
if O2 > 24%:    # HIGH-O2: full ozone cycle (30 min)
elif O2 >= 18%: # NORMAL: short ozone cycle (15 min)
else:           # LOW-O2: ozone disabled (safety)
```

**Without Oxygen Sensor** (timed mode):
- Fixed 8-hour intervals
- 30-minute ozone cycles
- Manual monitoring required

## UI Behavior

### Dynamic Sensor Display

The frontend automatically adapts:
- **3-column grid** when oxygen sensor is available (temp, humidity, oxygen cards)
- **2-column grid** when oxygen sensor is absent (temp, humidity cards only)
- Oxygen card is completely hidden (not just disabled) when sensor unavailable

Implementation: `checkOxygenSensorAvailability()` and `toggleOxygenSensorDisplay()` in [web/script.js](web/script.js)

### Ozone Mode Indicator

Visual indicator on B8 (Ozone) button shows current mode:
- **O2-SMART** (green): Intelligent oxygen-based control
- **HIGH-O2** (yellow): High oxygen level - active ozone
- **NORMAL** (blue): Normal oxygen - short ozone cycles
- **LOW-O2** (red): Low oxygen - ozone disabled
- **TIMED** (blue): No oxygen sensor - fixed interval control

## Deployment

### File Structure
```
/
├── web/                      # Frontend (served as static files)
│   ├── index.html           # Main dashboard
│   ├── script.js            # Controller logic
│   └── styles.css           # Responsive styles
├── lib/                      # Custom sensor drivers
│   ├── DHT_Native.py        # DHT11/DHT22 driver
│   └── DFRobot_Oxygen.py    # I2C oxygen sensor
├── systemd/                  # Service definitions
│   ├── kuvoz-web.service    # Web server
│   └── kuvoz-kiosk.service  # Kiosk mode
├── scripts/                  # Shell scripts
│   └── start-kiosk.sh       # Kiosk launcher
├── web_server.py            # Main Flask application
├── failure.dat              # Settings (JSON)
└── Makefile                 # Build automation
```

### Production Access

- Local: http://localhost:8000
- Network: http://[raspberry-pi-ip]:8000
- Kiosk: Chromium fullscreen on HDMI display

### Service Dependencies

```
kuvoz-web.service (web server)
  ↓ depends on
kuvoz-kiosk.service (UI display)
  ↓ requires
graphical.target (X11 session)
```

## Testing Workflow

Before committing changes:

1. **Run web server locally:** `make web-dev` or `python3 web_server.py`
2. **Check browser console:** Open http://localhost:8000 and verify no Socket.IO errors
3. **Verify sensor updates:** Confirm `status_response` event received on connection
4. **Test GPIO controls:** Toggle buttons and verify state updates
5. **Check settings persistence:** Save/load settings and restart server

## Known Platform-Specific Issues

### Raspberry Pi OS Trixie (Debian 13.1)

- Adafruit_DHT library incompatible (platform detection fails)
- Solution: Use DHT_Native exclusively
- Install dependencies: `make install-system` (uses system packages)
- Avoid `pip install --break-system-packages` when possible

### GPIO Permissions

Users must be in `gpio` and `i2c` groups:
```bash
sudo usermod -a -G gpio,i2c $USER
sudo reboot
```

### Socket.IO Buffer Issues

To prevent "Too many packets in payload" errors:
```python
socketio = SocketIO(app,
    max_http_buffer_size=1000000,  # 1MB
    ping_timeout=60000,            # 60s
    ping_interval=25000)           # 25s
```

## Integration Points

### Adding New GPIO Channel

1. Add pin to `outChannels` list in [web_server.py](web_server.py)
2. Initialize in `init_hardware()` method
3. Add button state to `button_states` dict
4. Update [web/index.html](web/index.html) with new button
5. Add event handler in [web/script.js](web/script.js)
6. Update [README_WEB.md](README_WEB.md) GPIO mapping table

### Adding New Slider

1. Add slider ID to `slider_values` dict in [web_server.py](web_server.py)
2. Add control element in [web/index.html](web/index.html)
3. Add event listener in [web/script.js](web/script.js): `updateSliderValue()`
4. Implement control logic in `control_logic()` thread

### Adding New Sensor

1. Import library in [web_server.py](web_server.py) with try/except
2. Set availability flag: `NEWSENSOR_AVAILABLE`
3. Initialize in `init_hardware()` with test reading
4. Add sensor data to `self.sensor_data` dict if available
5. Read in `read_sensors()` method (sensor thread)
6. Emit via WebSocket in `sensor_update` event
7. Update frontend to display new sensor card

## Documentation

- [README_WEB.md](README_WEB.md) - Web interface overview
- [KUVOZ_KULLANIM_KLAVUZU.md](docs/KUVOZ_KULLANIM_KLAVUZU.md) - Complete user manual (Turkish)
- [OXYGEN_OZONE_ANALYSIS.md](OXYGEN_OZONE_ANALYSIS.md) - Ozone control strategies
- [DHT_NATIVE_MANUAL.md](DHT_NATIVE_MANUAL.md) - DHT sensor driver documentation
- [SYSTEM_REQUIREMENTS.md](docs/SYSTEM_REQUIREMENTS.md) - Hardware/software requirements

## Migration Notes

This project migrated from Kivy desktop app to web interface:
- **v1.0-v2.0:** Kivy-based GUI (deprecated)
- **v3.0:** Modern web architecture (current)

Legacy files ([main3.py](main3.py), [form.kv](form.kv)) are kept for reference but not used in production.

## Memories

- vereceğin outputlar türkçe olsun.