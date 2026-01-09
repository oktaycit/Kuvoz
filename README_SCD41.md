# SCD41 CO2 Sensor Integration

## Overview

SCD41 is the next-generation CO2 sensor from Sensirion, offering improved performance over SCD30:

- **Smaller size**: 10×10mm vs 35×23mm (SCD30)
- **Lower power**: ~5mA average vs ~19mA (SCD30)
- **Faster measurements**: 5 seconds interval (same as SCD30)
- **Better accuracy**: ±40 ppm + 5% of reading
- **Integrated sensors**: CO2, Temperature, Humidity in one package
- **I2C address**: 0x62 (vs 0x61 for SCD30)

## Hardware Connection

### Wiring (I2C)
```
SCD41          Raspberry Pi
-------------------------------
VDD     →      Pin 1  (3.3V)
GND     →      Pin 6  (GND)
SDA     →      Pin 3  (GPIO2, I2C SDA)
SCL     →      Pin 5  (GPIO3, I2C SCL)
```

### Pin Configuration
- **I2C Bus**: `/dev/i2c-1`
- **I2C Address**: `0x62` (fixed, not configurable)
- **Power**: 3.3V only (DO NOT use 5V)

## Installation

### 1. Enable I2C
```bash
sudo raspi-config
# Interface Options → I2C → Enable
```

### 2. Install Python Library
```bash
pip3 install --break-system-packages adafruit-circuitpython-scd4x
```

Or use the project's requirements:
```bash
cd /home/oktay/Projeler/kuvoz
pip3 install --break-system-packages -r requirements.txt
```

### 3. Verify I2C Connection
```bash
i2cdetect -y 1
```
Expected output: SCD41 should appear at address `62`
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
60: -- -- 62 -- -- -- -- -- -- -- -- -- -- -- -- -- 
70: -- -- -- -- -- -- -- --
```

## Testing

### Quick Test
```bash
cd /home/oktay/Projeler/kuvoz
python3 test_scd41_sensor.py
```

Expected output:
```
✓ SCD41 libraries imported successfully

============================================================
SCD41 Sensor Test - Kuvoz Project
============================================================

1. Initializing I2C bus...
   ✓ I2C bus initialized

2. Connecting to SCD41 sensor...
   ✓ SCD41 sensor detected
   Serial number: 0xXXXXXX

3. Starting periodic measurements...
   ✓ Measurements started
   ⏳ Waiting 5 seconds for first reading...

4. Reading sensor data (10 readings)...

   Time  | CO2 (ppm) | Temp (°C) | Humidity (%)
   ----------------------------------------------------
   14:23:15 |       420 |     23.45 |        45.00
   14:23:20 |       422 |     23.46 |        45.10
   ...

5. Stopping measurements...
   ✓ Measurements stopped

============================================================
✓ Test completed successfully!
============================================================
```

### Library Test
```bash
cd /home/oktay/Projeler/kuvoz/lib
python3 SCD41_Sensor.py
```

## Integration with Kuvoz System

### Auto-Detection

The system automatically detects and uses available CO2 sensors:

1. **Priority order**: SCD41 → SCD30 → None
2. **Fallback**: If SCD41 not found, tries SCD30
3. **Notification**: Startup logs show which sensor is active

Example startup log:
```
✅ SCD41 sensor library loaded
🌫️  CO2 Sensor: SCD41
✅ CO2 (SCD41) sensor initialized (5s interval, compact design)
```

### API Compatibility

Both SCD41 and SCD30 provide the same data:
- **CO2**: ppm (parts per million)
- **Temperature**: °C
- **Humidity**: %RH

The system transparently handles both sensors - no code changes needed in other parts.

### Features

1. **Temperature/Humidity Backup**:
   - If DHT sensor fails, SCD41/SCD30 provides temperature and humidity
   - Displayed as "SCD41 (CO2 sensörü)" in UI

2. **Oxygen Estimation**:
   - If oxygen sensor unavailable, estimates O2 from CO2 readings
   - Uses inverse relationship: High CO2 → Low O2

3. **Real-time Updates**:
   - 5-second measurement interval
   - WebSocket push to all connected clients
   - No polling required

## Sensor Comparison

| Feature | SCD41 | SCD30 |
|---------|-------|-------|
| **Size** | 10×10×6.5mm | 35×23×7mm |
| **Power** | ~5mA avg | ~19mA avg |
| **Accuracy** | ±40ppm + 5% | ±30ppm + 3% |
| **Interval** | 5 seconds | 2-1800 seconds |
| **I2C Addr** | 0x62 | 0x61 |
| **Library** | adafruit-circuitpython-scd4x | sensirion-i2c-scd30 |
| **Price** | ~$40 | ~$50 |

## Troubleshooting

### Sensor Not Detected
```bash
# Check I2C connection
i2cdetect -y 1

# Verify 3.3V power (not 5V!)
# Check wiring: SDA→GPIO2, SCL→GPIO3

# Test with simpler library
pip3 install --break-system-packages adafruit-blinka
python3 -c "import board; import busio; i2c = busio.I2C(board.SCL, board.SDA); print('I2C OK')"
```

### Library Import Error
```bash
# Install dependencies
pip3 install --break-system-packages adafruit-circuitpython-scd4x

# Or system packages (Debian Trixie)
sudo apt install python3-adafruit-circuitpython-scd4x
```

### Wrong Readings
- **First 5 seconds**: Sensor warming up, readings not valid
- **High CO2 (>2000ppm)**: Normal indoors, ensure ventilation
- **Temperature offset**: SCD41 has ~4°C self-heating, can be compensated

### Enable Temperature Offset Compensation
```python
from lib.SCD41_Sensor import SCD41Sensor

sensor = SCD41Sensor()
sensor.set_temperature_offset(4.0)  # Compensate for self-heating
```

### Set Altitude (for accurate CO2)
```python
sensor.set_altitude(50)  # meters above sea level
```

## Advanced Features

### Forced Calibration
If sensor drifts over time, recalibrate in fresh air (400-420 ppm):

```python
sensor.perform_forced_calibration(410)  # Current outdoor CO2 level
```

### Low Power Mode
SCD41 supports single-shot measurement (not implemented in current integration):
- Measures once every 5 minutes
- Power: ~0.4mA average
- Useful for battery-powered applications

## Migration from SCD30

No code changes required! The system:
1. Detects SCD41 automatically
2. Uses same data format
3. Handles sensor-specific initialization
4. Logs which sensor is active

To switch:
1. Install SCD41 library: `pip3 install --break-system-packages adafruit-circuitpython-scd4x`
2. Connect SCD41 to I2C (address 0x62)
3. Remove/disconnect SCD30 (address 0x61)
4. Restart: `sudo systemctl restart kuvoz-web`

System will auto-detect and use SCD41.

## References

- **SCD41 Datasheet**: https://sensirion.com/products/catalog/SCD41
- **Adafruit Library**: https://github.com/adafruit/Adafruit_CircuitPython_SCD4X
- **Kuvoz Integration**: [lib/SCD41_Sensor.py](lib/SCD41_Sensor.py)
- **Web Server**: [web_server.py](web_server.py) lines 76-105 (import), 426-479 (init), 934-1024 (read)

## File Changes

### New Files
- `lib/SCD41_Sensor.py` - SCD41 sensor library wrapper
- `test_scd41_sensor.py` - Standalone test script
- `README_SCD41.md` - This file

### Modified Files
- `web_server.py`:
  - Lines 76-105: Import SCD41, fallback to SCD30
  - Lines 426-479: Initialize SCD41 or SCD30
  - Lines 934-1024: Read from SCD41 or SCD30
- `requirements.txt`:
  - Added `adafruit-circuitpython-scd4x`

### No Changes Required
- Frontend (`web/script.js`, `web/index.html`)
- Firebase integration
- AI module
- Other sensors (DHT, Oxygen)

## Notes

1. **Both sensors can coexist** on same I2C bus (different addresses: 0x61, 0x62)
2. **Auto-fallback**: If SCD41 init fails, tries SCD30
3. **Performance**: SCD41 is more efficient for embedded systems (lower power, smaller size)
4. **Accuracy**: Both sensors meet veterinary incubator requirements (±50ppm is acceptable)
5. **Future**: Consider using only SCD41 for new installations

---

**Status**: ✅ Implemented and tested  
**Date**: January 9, 2026  
**Author**: Kuvoz Development Team
