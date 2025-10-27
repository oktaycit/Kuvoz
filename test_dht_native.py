#!/usr/bin/env python3
"""
DHT Native Test Script - Auto-Detection
Tests DHT11/DHT22 sensor using DHT_Native library with GPIO 15
"""

import sys
import time
sys.path.append('lib/')

def check_environment():
    """Check if we're running on Raspberry Pi"""
    try:
        import RPi.GPIO as GPIO
        print('✅ RPi.GPIO available - running on Raspberry Pi')
        return True
    except ImportError:
        print('❌ RPi.GPIO not available - not running on Raspberry Pi')
        return False

try:
    if not check_environment():
        print('This test must be run on a Raspberry Pi with GPIO access')
        sys.exit(1)
    
    from DHT_Native import read_retry, detect_sensor, DHT_PIN
    print('🌡️  DHT Auto-Detection Test with DHT_Native...')
    print(f'📍 Using GPIO pin {DHT_PIN} (physical pin 10)')
    print('Make sure DHT11/DHT22 is connected:')
    print(f'  DHT VCC  → 3.3V (pin 1)')
    print(f'  DHT DATA → GPIO {DHT_PIN} (pin 10)')  
    print(f'  DHT GND  → GND (pin 6)')
    print('=' * 50)
    
    # Otomatik sensör algılama
    print('\n🔍 Auto-detecting DHT sensor type...')
    detected_type = detect_sensor()
    if detected_type:
        sensor_name = "DHT22" if detected_type == 22 else "DHT11"
        print(f'✅ {sensor_name} detected on GPIO {DHT_PIN}')
    else:
        print(f'❌ No DHT sensor detected on GPIO {DHT_PIN}')
        print('   Check wiring and connections.')
        sys.exit(1)
    
    print('\n' + '=' * 50)
    success_count = 0
    for i in range(3):
        print(f'\n🔄 Reading attempt {i+1}/3...')
        # Otomatik algılama ile okuma (sensör tipi belirtilmez)
        hum, temp = read_retry()
        if hum is not None and temp is not None:
            print(f'✅ Success: {temp:.1f}°C, {hum:.1f}%rH ({sensor_name})')
            success_count += 1
            break
        else:
            print(f'❌ Attempt {i+1} failed')
            if i < 2:
                print('   Waiting 3 seconds before retry...')
                time.sleep(3)
    
    if success_count > 0:
        print(f'\n🎉 {sensor_name} native test completed successfully!')
        sys.exit(0)
    else:
        print('\n❌ All attempts failed!')
        print('\nTroubleshooting:')
        print('1. Check DHT11 wiring (see connections above)')
        print('2. Run: python3 test_gpio_basic.py 22')
        print('3. Try different DHT11 sensor (sensor may be faulty)')
        print('4. Check power supply (DHT11 needs stable 3.3V)')
        sys.exit(1)

except ImportError as e:
    print(f'❌ Import error: {e}')
    print('Make sure DHT_Native.py is in lib/ directory')
    sys.exit(1)
    
except Exception as e:
    print(f'❌ Unexpected error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)