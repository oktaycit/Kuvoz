#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DHT11 Sensor Test - Pin 15 kontrol
"""

import sys
import time

def test_dht11():
    """DHT11 pin 15 test"""
    print("🌡️  DHT11 Sensor Test - Pin 15")
    print("==============================")
    
    # 1. Adafruit_DHT test
    print("1️⃣  Testing Adafruit_DHT library:")
    try:
        import Adafruit_DHT
        
        print("✅ Adafruit_DHT import: OK")
        print(f"📦 Version: {getattr(Adafruit_DHT, 'VERSION', 'Unknown')}")
        
        # DHT11 test - pin 15
        print("\n🧪 Reading DHT11 from pin 15...")
        for attempt in range(3):
            hum, temp = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, 15)
            if hum is not None and temp is not None:
                print(f"✅ Attempt {attempt+1}: {temp:.1f}°C, {hum:.0f}%rH")
                return True
            else:
                print(f"❌ Attempt {attempt+1}: Failed")
                time.sleep(2)
        
        print("❌ Adafruit_DHT read failed after 3 attempts")
        
    except ImportError as e:
        print(f"❌ Adafruit_DHT not available: {e}")
    except Exception as e:
        print(f"❌ Adafruit_DHT error: {e}")
    
    # 2. DHT_Native fallback test
    print("\n2️⃣  Testing DHT_Native library:")
    try:
        sys.path.append("lib/")
        from DHT_Native import read_retry, read
        
        print("✅ DHT_Native import: OK")
        
        # DHT11 test - pin 15
        print("\n🧪 Reading DHT11 with DHT_Native...")
        for attempt in range(3):
            hum, temp = read_retry(11, 15)
            if hum is not None and temp is not None:
                print(f"✅ Attempt {attempt+1}: {temp:.1f}°C, {hum:.0f}%rH")
                return True
            else:
                print(f"❌ Attempt {attempt+1}: Failed")
                time.sleep(2)
        
        print("❌ DHT_Native read failed after 3 attempts")
        
    except ImportError as e:
        print(f"❌ DHT_Native not available: {e}")
    except Exception as e:
        print(f"❌ DHT_Native error: {e}")
    
    # 3. GPIO manual test
    print("\n3️⃣  Testing GPIO access:")
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(15, GPIO.OUT)
        GPIO.output(15, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.setup(15, GPIO.IN)
        print("✅ GPIO pin 15 access: OK")
        GPIO.cleanup()
        
    except Exception as e:
        print(f"❌ GPIO test failed: {e}")
    
    print("\n💡 Troubleshooting:")
    print("==================")
    print("1. DHT11 bağlantısını kontrol edin:")
    print("   - VCC: 3.3V or 5V")
    print("   - GND: Ground")
    print("   - Data: GPIO 15 (pin 10)")
    print("   - Pull-up resistor: 10kΩ between VCC and Data")
    print("")
    print("2. Wiring kontrolü:")
    print("   - DHT11 data pin -> GPIO 15")
    print("   - Pull-up resistor ekli mi?")
    print("   - Breadboard bağlantıları sağlam mı?")
    print("")
    print("3. DHT11 sensor kontrol:")
    print("   - Sensor çalışıyor mu?")
    print("   - Farklı bir sensör deneyin")
    print("   - Güç bağlantısı doğru mu?")
    
    return False

if __name__ == "__main__":
    success = test_dht11()
    if success:
        print("\n🎉 DHT11 test başarılı!")
        sys.exit(0)
    else:
        print("\n💥 DHT11 test başarısız!")
        sys.exit(1)