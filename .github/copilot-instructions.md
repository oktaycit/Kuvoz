# Kuvoz — AI Coding Agent Instructions

Raspberry Pi-based veterinary incubator control system for post-operative pet care. Flask/Socket.IO backend with multi-threaded sensor reading & GPIO control, vanilla JS frontend with real-time WebSocket communication, Chromium kiosk mode for touchscreen deployment.

## Architecture Overview

### Multi-threaded Backend ([web_server.py](web_server.py))

```
Main Thread (Flask/Socket.IO)
├── Sensor Reading Thread (15s interval) → DHT22, Oxygen (I2C), CO2 (SCD30)
├── Control Logic Thread (5s interval) → Temperature/Humidity PID, Duty cycles
└── WebSocket Handler → Real-time bidirectional communication
```

**Core Class:** `KuvozServer` in [web_server.py](web_server.py) (1600+ lines)
- Feature flags: `GPIO_AVAILABLE`, `DHT_AVAILABLE`, `OXYGEN_AVAILABLE`, `CO2_AVAILABLE`, `AI_AVAILABLE`
- Thread-safe GPIO via `safe_gpio_output(pin, state)` - ALWAYS use this, never raw `GPIO.output()`
- Settings persistence: JSON file `Failure.dat` (loaded in `load_settings()`, saved in `save_settings()`)
- Duty cycle state tracking: `nebulizer_in_duty`, `ozone_in_duty`, `nebulizer_duty_start`, `ozone_duty_start`

### Frontend Architecture ([web/script.js](web/script.js))

**Core Class:** `KuvozController` - WebSocket client with auto-reconnect
- Real-time sensor updates via `socket.on('sensor_update')`
- User controls via `socket.emit('toggle_button', 'update_slider')`
- Multi-language support (Turkish/English) via `translations` object
- Dynamic UI adaptation based on sensor availability flags

### GPIO Pin Mapping (8-Channel Relay, BCM mode)

```python
outChannels = [5, 6, 13, 16, 19, 20, 21, 26]  # web_server.py line ~150

# BCM  | Physical | Function              | Button ID
# -----|----------|----------------------|----------
# GP5  | Pin 29   | Therapeutic Lighting  | b1
# GP6  | Pin 31   | Nebulizer            | b2 (duty cycle)
# GP13 | Pin 33   | Humidity Control      | b3
# GP16 | Pin 36   | Heating Pad          | b4
# GP19 | Pin 35   | IR Heater            | b5
# GP20 | Pin 38   | Ventilation Fan       | b6
# GP21 | Pin 40   | UV Sterilization     | b7
# GP26 | Pin 37   | Ozone Sterilizer     | b8 (duty cycle, O2-aware)

# Sensor Pins
pinDht = 15              # GPIO 15 (Physical Pin 10) - DHT22 temperature/humidity
# I2C: SDA=GPIO2 (Pin 3), SCL=GPIO3 (Pin 5) - Oxygen sensor, CO2 sensor (SCD30)
```

**Critical:** Relay logic is **INVERTED** - `GPIO.LOW` = ON, `GPIO.HIGH` = OFF. See `safe_gpio_output()` in [web_server.py](web_server.py#L650).

## WebSocket Protocol (DO NOT BREAK)

### Server → Client Events

```javascript
'sensor_update'     // {sensors: {temperature: {value, status}, humidity: {...}, oxygen: {...}, co2: {...}}}
'button_update'     // {name: "b1", state: true}
'timer_update'      // {nebulizer: {in_duty, remaining, duty_duration, free_duration}, ozone: {...}}
'status_response'   // Full system status (buttons, sliders, sensors, timers, ai)
'ai_update'         // {vision: {motion_detected, ...}, analytics: {...}, frame: "base64_jpeg"}
'error'             // {message: "error text"}
'success'           // {message: "success text"}
```

### Client → Server Events

```javascript
'get_status'        // {page: "main"} - Request full status
'toggle_button'     // {name: "b1", state: true} - Control GPIO relay
'update_slider'     // {name: "sld1", value: 30} - Update control parameters
'save_settings'     // {} - Persist current state to Failure.dat
'shutdown'          // {} - System shutdown
'restart'           // {} - System restart
```

**Implementation locations:**
- Server handlers: [web_server.py](web_server.py) lines 1288-1475 (search `@socketio.on`)
- Client handlers: [web/script.js](web/script.js) lines 545-665 (method `connectWebSocket()`)

## Duty Cycle Logic (Nebulizer & Ozone)

**State machines** in [web_server.py](web_server.py):
- `nebulizer_control()` (line ~765): Starts duty cycle when button activated
- `update_nebulizer_duty_cycle()` (line ~785): State machine - alternates between DUTY (ON) and FREE (OFF) periods
- `ozone_control()` (line ~823): Similar to nebulizer, with **oxygen-aware** duration adjustment
- `update_ozone_duty_cycle()` (line ~857): Extends duty time by 1.5x if O2 > 24% (never reduces for low O2 to avoid user confusion)

**Slider mappings** (see `slider_values` dict in `__init__`):
- `sld8`: Nebulizer duty time (min), `sld9`: Nebulizer free time (min)
- `sld10`: Ozone duty time (min), `sld11`: Ozone free time (min)

**Why this pattern:** Duty cycles prevent continuous nebulizer/ozone operation (medical safety). Ozone adjustment based on O2 optimizes sterilization efficiency when oxygen-enriched environment is detected.

## Development Workflow

### Quick Start (No systemd)
```bash
# Dev server on localhost:5000
make web-dev
# OR directly: python3 web_server.py

# Debug terminal UI on port 8080
python3 web_debug_server.py
```

### Testing
```bash
make test              # Full hardware test suite
make test-dht          # DHT sensor only
make test-oxygen       # Oxygen sensor only
make test-gpio         # GPIO functionality
```

### Production Deployment
```bash
make auto-setup        # Full automated setup + enable services
make web-service       # Install/start web server systemd service
make kiosk-service     # Install/start Chromium kiosk systemd service

# Service management
make start-all         # Start web + kiosk services
make logs-all          # View logs
journalctl -u kuvoz-web -f    # Tail web server logs
```

### DHT Sensor Type Override
```bash
# Default is DHT22, override with:
python3 web_server.py --dht11
# OR: DHT_SENSOR_TYPE=11 python3 web_server.py
```
See `_detect_dht_sensor_type()` in [web_server.py](web_server.py#L125).

## Integration Points

### EMQX + GreptimeDB (Mobile App Backend)
- Branch: `MQTT-&-GreptimeDb-version`
- MQTT bridge: [emqx_bridge.py](emqx_bridge.py) - Publishes sensor data to EMQX broker
- Time-series DB: GreptimeDB for historical sensor data
- Setup: `make emqx-setup`, docs: [README_EMQX.md](README_EMQX.md)

### Firebase Integration
- Bidirectional control: [lib/firebase_manager.py](lib/firebase_manager.py)
- Remote control listener: `handle_firebase_control()` in [web_server.py](web_server.py#L230)

### AI Module (Optional)
- Vision engine: [lib/ai/vision.py](lib/ai/vision.py) - Motion detection, camera feed
- Analytics: [lib/ai/analytics.py](lib/ai/analytics.py) - Sensor data analysis
- Manager: [lib/ai/manager.py](lib/ai/manager.py) - Coordinates vision + analytics
- Enabled when `AI_AVAILABLE = True` (requires camera hardware)

### Sensor Data Logging
- Logger: [lib/data/sensor_logger.py](lib/data/sensor_logger.py)
- SQLite storage: `data/sensor_logs.db`
- Min interval: 60 seconds (configurable)

### CO2-based Oxygen Estimation (New Feature)
When oxygen sensor is unavailable, system estimates O2 from CO2 readings:
- Method: `estimate_oxygen_from_co2()` in [web_server.py](web_server.py#L425)
- Algorithm: Piecewise linear interpolation (CO2 ↑ = O2 ↓)
- Range: 400-2000+ ppm CO2 → 20.9%-15% O2
- Status display: "Tahmini (CO2: XXX ppm)" to indicate estimated value
- Ozone control: Works with both real and estimated O2 values
- Documentation: [CO2_TO_O2_ESTIMATION.md](CO2_TO_O2_ESTIMATION.md)

## Coding Conventions

### Hardware Access Patterns
```python
# ✅ CORRECT - Thread-safe with feature flag check
if GPIO_AVAILABLE:
    self.safe_gpio_output(pin, GPIO.LOW)  # Turn relay ON

# ❌ WRONG - Direct GPIO call, race conditions
GPIO.output(pin, GPIO.LOW)
```

### WebSocket Emission Pattern
```python
# Server emission (from any thread)
socketio.emit('sensor_update', {
    'sensors': self.sensor_data
}, namespace='/')

# Client emission (from JS)
this.socket.emit('toggle_button', {name: 'b1', state: true});
```

### Slider Value Access
```python
# Server-side: slider_values dict (keys: 'sld1'..'sld11')
target_temp = self.slider_values['sld3']

# Client-side: update via update_slider event, read from status_response
```

## Safety Rules

### High-Risk Changes (ASK FIRST)
1. Modifying GPIO pin numbers in `outChannels` array
2. Changing socket event names (breaks client-server contract)
3. Altering slider ID mappings (`sld1`..`sld11`)
4. Adding new systemd services or modifying existing `.service` files
5. Changes to duty cycle state machine logic (nebulizer/ozone control)

### Low-Risk Improvements (DO IT)
1. Add null checks in [web/script.js](web/script.js) before DOM manipulation (follow existing try/catch patterns)
2. Improve error handling in sensor reading threads
3. Add dashboard countdown timers for duty cycles (UI feature gap)
4. Enhance logging with more context (use `logger.info/warning/error`)
5. Refactor repeated code into helper methods

## Common Patterns to Copy

### Add New Sensor
```python
# 1. Feature flag at top of file
NEW_SENSOR_AVAILABLE = False
try:
    from lib.new_sensor import NewSensor
    NEW_SENSOR_AVAILABLE = True
except ImportError:
    print("⚠️  New sensor not available")

# 2. Init in KuvozServer.__init__()
self.new_sensor = None
if NEW_SENSOR_AVAILABLE:
    self.new_sensor = NewSensor()
    self.sensor_data['new_metric'] = {'value': '--', 'status': 'Initializing...'}

# 3. Read in sensor thread (method read_sensors())
if self.new_sensor:
    value = self.new_sensor.read()
    self.sensor_data['new_metric'] = {'value': value, 'status': 'OK'}
```

### Add New Control Button
```python
# 1. Server: Add to outChannels and button_states (KuvozServer.__init__)
self.button_states['b9'] = False

# 2. Server: Add GPIO control in control_logic()
if self.button_states['b9']:
    self.safe_gpio_output(NEW_PIN, GPIO.LOW)

# 3. Client: Add UI in index.html, wire event in script.js
// In handleButtonClick():
this.socket.emit('toggle_button', {name: 'b9', state: newState});
```

## Key Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| [web_server.py](web_server.py) | 1617 | Backend core - Flask, Socket.IO, GPIO, sensors, control logic |
| [web/script.js](web/script.js) | 1941 | Frontend core - WebSocket client, UI updates, translations |
| [Makefile](Makefile) | 1150 | Build, test, deploy automation |
| [README_WEB.md](README_WEB.md) | 328 | Web interface documentation |
| [CLAUDE.md](CLAUDE.md) | 369 | Extended development guide |
| [lib/firebase_manager.py](lib/firebase_manager.py) | - | Firebase Realtime Database integration |
| [emqx_bridge.py](emqx_bridge.py) | 501 | MQTT bridge for mobile app |

## Development Environment

- **Dev Machine:** macOS (file editing, git)
- **Target Device:** Raspberry Pi OS Trixie (Debian 13.1)
- **Deployment:** SSH to `oktay@192.168.1.132`, `scp` for file transfer
- **Backup:** GitHub repository

When making changes: Test locally with `make web-dev`, verify WebSocket handshake in browser console, check `status_response` payload structure matches expectations.
