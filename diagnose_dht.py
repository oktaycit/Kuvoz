#!/usr/bin/env python3
"""
DHT Sensor Diagnostic Tool
Comprehensive testing for DHT11/DHT22 connection issues
"""

import sys
import time
sys.path.append('lib/')

def main():
    print("=" * 60)
    print("DHT SENSOR DIAGNOSTIC TOOL")
    print("=" * 60)
    
    # 1. Check RPi.GPIO
    print("\n[1/5] Checking RPi.GPIO...")
    try:
        import RPi.GPIO as GPIO
        print("    ✅ RPi.GPIO available")
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
    except ImportError:
        print("    ❌ RPi.GPIO not available - not on Raspberry Pi")
        return False
    except Exception as e:
        print(f"    ❌ GPIO setup error: {e}")
        return False
    
    # 2. Check DHT_Native library
    print("\n[2/5] Checking DHT_Native library...")
    try:
        from DHT_Native import DHT_Native, DHT_PIN
        print(f"    ✅ DHT_Native loaded (default pin: GPIO {DHT_PIN})")
    except ImportError as e:
        print(f"    ❌ DHT_Native import error: {e}")
        return False
    
    # 3. Test GPIO pin access
    print(f"\n[3/5] Testing GPIO pin {DHT_PIN} access...")
    try:
        # Output test
        GPIO.setup(DHT_PIN, GPIO.OUT)
        GPIO.output(DHT_PIN, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(DHT_PIN, GPIO.LOW)
        time.sleep(0.1)
        print(f"    ✅ GPIO {DHT_PIN} output mode works")
        
        # Input test
        GPIO.setup(DHT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        state = GPIO.input(DHT_PIN)
        print(f"    ✅ GPIO {DHT_PIN} input mode works (state: {state})")
    except Exception as e:
        print(f"    ❌ GPIO {DHT_PIN} access error: {e}")
        return False
    
    # 4. Check for signal activity on pin
    print(f"\n[4/5] Checking for signal activity on GPIO {DHT_PIN}...")
    try:
        # Monitor pin for 2 seconds to see if there's any activity
        GPIO.setup(DHT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        states = []
        start = time.time()
        while time.time() - start < 2.0:
            states.append(GPIO.input(DHT_PIN))
            time.sleep(0.001)
        
        unique_states = set(states)
        if len(unique_states) > 1:
            print(f"    ✅ Pin shows activity (states: {unique_states})")
        else:
            print(f"    ⚠️  Pin stuck at {states[0]} (no activity)")
            print(f"       → Check sensor connection or sensor may be faulty")
    except Exception as e:
        print(f"    ❌ Signal check error: {e}")
    
    # 5. Try DHT sensor detection
    print(f"\n[5/5] Attempting DHT sensor detection...")
    try:
        dht = DHT_Native(pin=DHT_PIN, verbose=True)
        
        print("\n    Trying DHT22 detection...")
        sensor_type = dht.detect_sensor_type()
        
        if sensor_type:
            sensor_name = "DHT22" if sensor_type == 22 else "DHT11"
            print(f"\n    ✅ {sensor_name} detected!")
            
            # Try a read
            print(f"\n    Attempting read from {sensor_name}...")
            result = dht.read_dht_gpio(sensor_type, DHT_PIN)
            if result[0] is not None and result[1] is not None:
                hum, temp = result
                print(f"    ✅ Read successful: {temp:.1f}°C, {hum:.1f}%rH")
            else:
                print(f"    ⚠️  Detection succeeded but read failed")
                print(f"       → Try multiple reads (sensor timing issue)")
        else:
            print("\n    ❌ No DHT sensor detected")
            print("\n    TROUBLESHOOTING STEPS:")
            print("    1. Check physical connections:")
            print(f"       - DHT VCC  → 3.3V (Physical Pin 1)")
            print(f"       - DHT DATA → GPIO {DHT_PIN} (Physical Pin 10)")
            print(f"       - DHT GND  → GND (Physical Pin 6)")
            print("    2. Check if sensor LED is on (if available)")
            print("    3. Try a different DHT sensor (sensor may be faulty)")
            print("    4. Check for loose wires or bad connections")
            print("    5. Measure voltage at VCC pin (should be ~3.3V)")
            print("    6. Try re-seating the sensor in the breadboard")
            return False
            
    except Exception as e:
        print(f"    ❌ Detection error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            GPIO.cleanup()
        except:
            pass
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
