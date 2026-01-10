#!/usr/bin/env python3
"""
Detailed SCD41 diagnostic script
Tests low-level I2C communication to identify initialization issues
"""

import sys
import time

print("="*60)
print("SCD41 Detailed Diagnostic")
print("="*60)

# Step 1: Check library availability
print("\n1. Checking libraries...")
try:
    import board
    import busio
    print("   ✓ board and busio available")
except ImportError as e:
    print(f"   ✗ Failed to import board/busio: {e}")
    sys.exit(1)

try:
    import adafruit_scd4x
    print("   ✓ adafruit_scd4x available")
except ImportError as e:
    print(f"   ✗ Failed to import adafruit_scd4x: {e}")
    print("   Install with: pip3 install adafruit-circuitpython-scd4x")
    sys.exit(1)

# Step 2: Initialize I2C bus
print("\n2. Initializing I2C bus...")
try:
    i2c = busio.I2C(board.SCL, board.SDA)
    print("   ✓ I2C bus created")
    
    # Try to lock the bus
    while not i2c.try_lock():
        pass
    print("   ✓ I2C bus locked for scanning")
    
    # Scan for devices
    devices = i2c.scan()
    i2c.unlock()
    
    print(f"   ✓ Found {len(devices)} I2C device(s):")
    for device in devices:
        print(f"     - 0x{device:02X} ({device})")
    
    if 0x62 in devices:
        print("   ✓ SCD41 detected at 0x62")
    else:
        print("   ✗ SCD41 NOT found at 0x62")
        sys.exit(1)
        
except Exception as e:
    print(f"   ✗ I2C bus error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 3: Try to initialize sensor with detailed error reporting
print("\n3. Attempting sensor initialization...")
try:
    scd = adafruit_scd4x.SCD4X(i2c)
    print("   ✓ SCD4X object created")
    
except ValueError as e:
    print(f"   ✗ ValueError during init: {e}")
    print("\n   This usually means:")
    print("   - Sensor is not responding to expected commands")
    print("   - Wrong sensor type (SCD30 vs SCD41)")
    print("   - Sensor needs power cycle")
    import traceback
    traceback.print_exc()
    sys.exit(1)
    
except OSError as e:
    print(f"   ✗ OSError during init: {e}")
    print("\n   This usually means:")
    print("   - I2C communication problem")
    print("   - Loose wiring")
    print("   - Insufficient power")
    import traceback
    traceback.print_exc()
    sys.exit(1)
    
except Exception as e:
    print(f"   ✗ Unexpected error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 4: Try to get serial number
print("\n4. Reading sensor serial number...")
try:
    serial = scd.serial_number
    serial_str = f"0x{serial[0]:02X}{serial[1]:02X}{serial[2]:02X}"
    print(f"   ✓ Serial number: {serial_str}")
except Exception as e:
    print(f"   ✗ Failed to read serial: {e}")
    import traceback
    traceback.print_exc()

# Step 5: Start measurements
print("\n5. Starting periodic measurements...")
try:
    scd.start_periodic_measurement()
    print("   ✓ Measurements started")
    print("   ⏳ Waiting 5 seconds for first reading...")
    time.sleep(5)
except Exception as e:
    print(f"   ✗ Failed to start measurements: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 6: Read data
print("\n6. Reading sensor data...")
try:
    if scd.data_ready:
        co2 = scd.CO2
        temp = scd.temperature
        humidity = scd.relative_humidity
        print(f"   ✓ CO2: {co2:.0f} ppm")
        print(f"   ✓ Temperature: {temp:.2f} °C")
        print(f"   ✓ Humidity: {humidity:.2f} %")
    else:
        print("   ⚠ Data not ready yet (wait longer)")
except Exception as e:
    print(f"   ✗ Failed to read data: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("Diagnostic complete")
print("="*60)
