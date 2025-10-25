#!/usr/bin/env python3
"""
Basic GPIO Test for DHT11 pin
Tests if GPIO pin 15 is accessible and functional
"""

import time
import sys

try:
    import RPi.GPIO as GPIO
    print("✅ RPi.GPIO imported successfully")
except ImportError:
    print("❌ RPi.GPIO not available - running on non-Pi system")
    sys.exit(1)

def test_gpio_pin(pin=22):
    """Test basic GPIO functionality on DHT11 pin"""
    try:
        print(f"🔍 Testing GPIO pin {pin}...")
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Test OUTPUT mode
        print(f"Setting pin {pin} as OUTPUT...")
        GPIO.setup(pin, GPIO.OUT)
        
        print("Setting pin HIGH...")
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(0.1)
        
        print("Setting pin LOW...")
        GPIO.output(pin, GPIO.LOW)
        time.sleep(0.1)
        
        # Test INPUT mode with pullup
        print(f"Setting pin {pin} as INPUT with pullup...")
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Read pin state multiple times
        for i in range(5):
            state = GPIO.input(pin)
            print(f"Pin {pin} state {i+1}: {state}")
            time.sleep(0.1)
        
        # Test INPUT without pullup
        print(f"Setting pin {pin} as INPUT without pullup...")
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_OFF)
        
        for i in range(5):
            state = GPIO.input(pin)
            print(f"Pin {pin} state (no pullup) {i+1}: {state}")
            time.sleep(0.1)
        
        print(f"✅ GPIO pin {pin} test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ GPIO test error: {e}")
        return False
    finally:
        try:
            GPIO.cleanup()
        except:
            pass

def check_dht11_connection(pin=22):
    """Check if DHT11 sensor is responding on the pin"""
    try:
        print(f"🌡️ Checking DHT11 connection on pin {pin}...")
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # DHT11 start signal
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(0.25)  # Wait 250ms for sensor to stabilize
        
        print("Sending DHT11 start signal...")
        GPIO.output(pin, GPIO.LOW)
        time.sleep(0.02)  # 20ms low signal
        
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Wait for sensor response (should go LOW then HIGH)
        start_time = time.time()
        timeout = 0.01  # 10ms timeout
        
        # Wait for LOW (sensor response)
        while GPIO.input(pin) == 1 and (time.time() - start_time) < timeout:
            pass
        
        if GPIO.input(pin) == 1:
            print("❌ No DHT11 response - sensor may not be connected")
            return False
        
        print("✅ DHT11 response detected (signal went LOW)")
        
        # Wait for HIGH (sensor ready to send data)
        start_time = time.time()
        while GPIO.input(pin) == 0 and (time.time() - start_time) < timeout:
            pass
        
        if GPIO.input(pin) == 0:
            print("❌ DHT11 didn't go HIGH - sensor may be faulty")
            return False
        
        print("✅ DHT11 ready signal detected (signal went HIGH)")
        print("✅ DHT11 sensor appears to be connected and responding")
        return True
        
    except Exception as e:
        print(f"❌ DHT11 connection test error: {e}")
        return False
    finally:
        try:
            GPIO.cleanup()
        except:
            pass

if __name__ == "__main__":
    print("🔧 GPIO and DHT11 Connection Test")
    print("=" * 40)
    
    # Allow pin override from command line
    pin = 22
    if len(sys.argv) > 1:
        try:
            pin = int(sys.argv[1])
            print(f"Using GPIO pin {pin} from command line")
        except ValueError:
            print("Invalid pin number, using default GPIO 22")
    
    # Test basic GPIO functionality
    gpio_ok = test_gpio_pin(pin)
    print()
    
    if gpio_ok:
        # Test DHT11 sensor connection
        dht_ok = check_dht11_connection(pin)
        print()
        
        if dht_ok:
            print("🎉 All tests passed! DHT11 sensor is connected and ready.")
        else:
            print(f"⚠️ GPIO works but DHT11 sensor may not be connected to pin {pin}")
            print(f"   Check wiring: DHT11 data pin → GPIO {pin} (physical pin 15)")
            print("   Also ensure DHT11 has power: VCC → 3.3V, GND → GND")
    else:
        print("❌ GPIO test failed - check Raspberry Pi GPIO permissions")
        print("   Try running with sudo or add user to gpio group")