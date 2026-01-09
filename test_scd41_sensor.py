#!/usr/bin/env python3
"""
SCD41 CO2, Temperature, and Humidity Sensor Test Script
Tests I2C communication and sensor readings for Sensirion SCD41
"""

import sys
import time

# Try to import the sensor library
try:
    import board
    import busio
    import adafruit_scd4x
    SCD41_AVAILABLE = True
    print("✓ SCD41 libraries imported successfully")
except ImportError as e:
    print(f"✗ Failed to import required libraries: {e}")
    print("\nInstall with:")
    print("  pip3 install adafruit-circuitpython-scd4x")
    SCD41_AVAILABLE = False
    sys.exit(1)

def test_scd41():
    """Test SCD41 sensor connection and readings"""
    print("\n" + "="*60)
    print("SCD41 Sensor Test - Kuvoz Project")
    print("="*60)
    
    try:
        # Initialize I2C bus
        print("\n1. Initializing I2C bus...")
        i2c = busio.I2C(board.SCL, board.SDA)
        print("   ✓ I2C bus initialized")
        
        # Initialize SCD41 sensor
        print("\n2. Connecting to SCD41 sensor...")
        scd = adafruit_scd4x.SCD4X(i2c)
        print(f"   ✓ SCD41 sensor detected")
        print(f"   Serial number: 0x{scd.serial_number[0]:02X}{scd.serial_number[1]:02X}{scd.serial_number[2]:02X}")
        
        # Start periodic measurement
        print("\n3. Starting periodic measurements...")
        scd.start_periodic_measurement()
        print("   ✓ Measurements started")
        print("   ⏳ Waiting 5 seconds for first reading...")
        time.sleep(5)
        
        # Take multiple readings
        print("\n4. Reading sensor data (10 readings)...")
        print("\n   Time  | CO2 (ppm) | Temp (°C) | Humidity (%)")
        print("   " + "-"*52)
        
        for i in range(10):
            if scd.data_ready:
                co2 = scd.CO2
                temperature = scd.temperature
                humidity = scd.relative_humidity
                
                timestamp = time.strftime("%H:%M:%S")
                print(f"   {timestamp} | {co2:>9.0f} | {temperature:>9.2f} | {humidity:>12.2f}")
            else:
                print(f"   {time.strftime('%H:%M:%S')} | Data not ready yet...")
            
            time.sleep(5)
        
        print("\n5. Stopping measurements...")
        scd.stop_periodic_measurement()
        print("   ✓ Measurements stopped")
        
        print("\n" + "="*60)
        print("✓ Test completed successfully!")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error during test: {e}")
        print("\nTroubleshooting:")
        print("  1. Check I2C connections (SDA=GPIO2/Pin3, SCL=GPIO3/Pin5)")
        print("  2. Verify sensor power (3.3V)")
        print("  3. Enable I2C: sudo raspi-config → Interface Options → I2C")
        print("  4. Check I2C devices: i2cdetect -y 1")
        print("     (SCD41 should appear at address 0x62)")
        return False

if __name__ == "__main__":
    print("\nPress Ctrl+C to exit at any time\n")
    try:
        success = test_scd41()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(0)
