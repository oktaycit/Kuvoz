# Kuvoz Incubator Control Algorithm Analysis

## Overall Architecture
The system operates on a **dual-threaded control loop** with **state-driven automation**:

1. **Sensor Thread** (15-second cycle): Reads environmental data
2. **Control Thread** (1-second cycle): Executes control logic and updates UI

## Control Mapping & Hardware Layout

| Button | GPIO Pin | Function | Control Type | Slider |
|--------|----------|----------|--------------|--------|
| b1 | 5 | Lighting | Manual/Touch | - |
| b2 | 6 | Nebulizer (IR) | Timed Sequence | sld1 (on-time), sld6 (off-time) |
| b3 | 13 | Humidity Control | Threshold-based | sld2 (setpoint) |
| b4 | 16 | Carbon Heater | Threshold-based | sld3 (setpoint) |
| b5 | 19 | IR Heater | Threshold-based | sld4 (setpoint) |
| b6 | 20 | Fan | Manual/Touch | - |
| b7 | 21 | UV Lighting | Manual/Touch | - |
| b8 | 26 | Ozone Generator | Timed Sequence | sld5 (on-time), sld7 (off-time) |

## Control Logic Algorithms

### 1. Threshold-Based Control (b3, b4, b5)
```python
def f_out(self, btn, sln, controlPrm):
    if(button_enabled AND sensor_value < setpoint):
        activate_relay()  # GPIO.LOW
        show_green_indicator()
    else:
        deactivate_relay()  # GPIO.HIGH
        show_white_indicator()
```

**Applied to:**
- **Humidity** (b3): `KuvozParam.nem < sld2.value`
- **Carbon Temp** (b4): `KuvozParam.sicaklik < sld3.value`
- **IR Temp** (b5): `KuvozParam.sicaklik < sld4.value`

### 2. Timed Sequence Control (b2 - Nebulizer, b8 - Ozone)

#### Nebulizer Algorithm (b2):
```python
if button_enabled:
    if on_time >= (sld1.value * 60_seconds):
        if off_interval < (sld6.value * 60_seconds):
            relay_OFF()  # Cool-down period
            increment_off_counter()
        else:
            reset_to_on_cycle()
    else:
        relay_ON()  # Active nebulizing
        increment_on_counter()
```

#### Ozone Algorithm (b8):
```python
if button_enabled:
    if on_time >= (sld5.value * 60_seconds):
        if off_interval < (sld7.value * 3600_seconds):  # Hours!
            relay_OFF()  # Long rest period
            increment_off_counter()
        else:
            reset_to_on_cycle()
    else:
        relay_ON()  # Active ozone generation
        increment_on_counter()
```

## Sensor Data Processing

### Multi-Sensor Reading with Validation
```python
def sensorRead(self):
    # Read DHT11/22 (temp/humidity)
    hum, temp = Adafruit_DHT.read_retry(sensorDht, pinDht)
    
    # Read I2C oxygen sensor (20-sample average)
    oxygen_data = self.oxygen.get_oxygen_data(COLLECT_NUMBER)
    
    # Validate oxygen (5% < reading < 90%)
    if(5.0 < oxygen_data < 90.0):
        KuvozParam.oksijen = oxygen_data
    
    # Validate temperature/humidity
    if(valid_float_readings):
        KuvozParam.nem = hum
        KuvozParam.sicaklik = temp
        reset_error_counter()
    elif(error_count > 5):
        set_safe_defaults()  # 0 values trigger failsafe
```

### Sensor Specifications
- **DHT11/DHT22**: Temperature & humidity via GPIO pin 15
- **DFRobot Oxygen**: I2C sensor with 20-sample averaging for stability
- **Error Handling**: 5-failure threshold before failsafe activation

## State Persistence Algorithm

### Startup State Recovery
```python
# Read from Failure.dat: "btState sld1 sld2 sld3 sld4 sld5 sld6 sld7"
if file_exists("Failure.dat"):
    data = parse_line()
    btState = int(data[0])  # 8-bit button state
    for i in range(7):
        slider[i] = float(data[i+1])
    restore_button_states()
```

### Emergency Shutdown Protocol
```python
def cikis(self):
    save_current_state_to_file()
    stop_all_threads()
    system_shutdown()  # "sudo shutdown -h now"
```

## Visual Feedback System

### Color-Coded Status Indicators
- **Green `[0,1,0,1]`**: Relay active (heating/cooling/generating)
- **White `[1,1,1,1]`**: Relay inactive (standby)
- **Button Text**: Shows countdown timers for timed sequences

### Real-time Display Updates
- Temperature: `%2.1f°C` format
- Humidity: `%%%drH` format  
- Oxygen: `%2.2f%%` format

## Threading Architecture

### Thread 1: Sensor Reading (peryodSensor)
```python
while True:
    read_all_sensors()
    time.sleep(15)  # 15-second interval
    if(stop_signal):
        break
```

### Thread 2: Control Loop (peryodOut)
```python
while True:
    execute_control_logic()
    update_ui_display()
    save_state_string()
    time.sleep(1)  # 1-second interval
    if(stop_signal):
        break
```

## Critical Safety Features

1. **Sensor Failure Handling**: After 5 consecutive read failures, sensors reset to 0 (triggers failsafe)
2. **GPIO Cleanup**: Ensures all pins return to HIGH (relay off) on exit
3. **State Persistence**: Power-cycle recovery maintains user settings
4. **Immediate Shutdown**: Emergency stop with state save
5. **Relay Logic**: LOW = Active, HIGH = Inactive (fail-safe for relay modules)

## Performance Characteristics

- **Sensor Update Rate**: 15 seconds (prevents sensor overheating)
- **Control Loop Rate**: 1 second (responsive control)
- **I2C Averaging**: 20 samples for stable oxygen readings
- **Thread Safety**: Global state managed via `KuvozParam` class
- **Memory Usage**: Minimal state storage in global variables

## Algorithm Weaknesses Identified

### Thread Safety Issues
1. **Race Conditions**: No mutex protection on shared state variables
2. **Global State**: Multiple threads accessing `KuvozParam` without synchronization

### Control Logic Issues
3. **Single Point of Failure**: DHT sensor failure affects multiple control loops
4. **No Hysteresis**: Threshold control may cause relay chattering near setpoint
5. **Hard-coded Validation**: Oxygen sensor limits (5-90%) not configurable

### Timing Issues
6. **Timer Reset Logic**: Ozone timer has inconsistent reset behavior (`o2_time_val = 1` vs `0`)
7. **Manual Button Interference**: No protection against manual override during automated sequences

### Error Handling
8. **Silent Failures**: Some sensor errors only print to console
9. **Incomplete Validation**: Temperature/humidity bounds not validated

## Recommended Improvements

### 1. Thread Synchronization
```python
import threading
sensor_lock = threading.Lock()

def thread_safe_sensor_update():
    with sensor_lock:
        KuvozParam.sicaklik = new_temp
        KuvozParam.nem = new_humidity
```

### 2. Hysteresis Control
```python
def threshold_control_with_hysteresis(current_value, setpoint, hysteresis=0.5):
    if relay_state == OFF and current_value < (setpoint - hysteresis):
        return TURN_ON
    elif relay_state == ON and current_value > (setpoint + hysteresis):
        return TURN_OFF
    return MAINTAIN_STATE
```

### 3. Configurable Validation
```python
class SensorLimits:
    OXYGEN_MIN = 5.0
    OXYGEN_MAX = 90.0
    TEMP_MIN = -10.0
    TEMP_MAX = 60.0
    HUMIDITY_MIN = 0.0
    HUMIDITY_MAX = 100.0
```

This algorithm provides robust environmental control with multiple safety mechanisms, but would benefit from improved thread synchronization, configurable validation parameters, and hysteresis-based control to prevent relay chattering.