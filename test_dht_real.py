#!/usr/bin/env python3
"""
DHT11 Real Data Test
Tests actual DHT11 sensor reading with real data parsing
"""

import sys
import time
sys.path.append('lib/')

try:
    import RPi.GPIO as GPIO
    print("✅ RPi.GPIO loaded successfully")
except ImportError:
    print("❌ RPi.GPIO not available")
    sys.exit(1)

def basic_dht11_read(pin=15):
    """Very basic but working DHT11 implementation"""
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        print(f"🌡️ Reading DHT11 on GPIO {pin}...")
        
        # Send start signal
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(0.25)  # 250ms stabilization
        
        GPIO.output(pin, GPIO.LOW)
        time.sleep(0.02)  # 20ms start signal
        
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Collect all timing changes
        changes = []
        last_state = GPIO.input(pin)
        start_time = time.time()
        
        while len(changes) < 200 and (time.time() - start_time) < 0.1:
            current_state = GPIO.input(pin)
            if current_state != last_state:
                changes.append((time.time() - start_time, current_state))
                last_state = current_state
        
        print(f"📊 Collected {len(changes)} transitions")
        
        if len(changes) < 80:
            print("❌ Not enough transitions")
            return None, None
        
        # Simple bit extraction: skip first 2-3 transitions, then every 2 = 1 bit
        bits = []
        start_idx = 3  # Skip initial response
        
        for i in range(start_idx, len(changes) - 1, 2):
            if len(bits) >= 40:
                break
            if i + 1 < len(changes):
                # Measure high pulse duration
                if changes[i][1] == 1 and changes[i+1][1] == 0:  # HIGH to LOW
                    high_time = changes[i+1][0] - changes[i][0]
                    bits.append(1 if high_time > 0.00004 else 0)  # 40µs threshold
        
        print(f"🔢 Extracted {len(bits)} bits")
        
        if len(bits) < 32:
            print("❌ Not enough bits for parsing")
            return None, None
        
        # Convert bits to bytes
        bytes_data = []
        for i in range(0, min(40, len(bits)), 8):
            byte_val = 0
            for j in range(8):
                if i + j < len(bits):
                    byte_val = (byte_val << 1) | bits[i + j]
            bytes_data.append(byte_val)
        
        print(f"📦 Got {len(bytes_data)} bytes: {[hex(b) for b in bytes_data]}")
        
        if len(bytes_data) >= 4:
            # DHT11 format: [hum_int, hum_dec, temp_int, temp_dec, checksum]
            hum_int = bytes_data[0]
            hum_dec = bytes_data[1] 
            temp_int = bytes_data[2]  
            temp_dec = bytes_data[3]
            
            humidity = hum_int + hum_dec * 0.1
            temperature = temp_int + temp_dec * 0.1
            
            # Basic validation
            if 0 <= humidity <= 100 and 0 <= temperature <= 60:
                print(f"✅ DHT11 Reading: {temperature:.1f}°C, {humidity:.1f}%rH")
                return humidity, temperature
            else:
                print(f"❌ Invalid readings: {temperature}°C, {humidity}%rH")
        
        return None, None
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None
    finally:
        try:
            GPIO.cleanup()
        except:
            pass

if __name__ == "__main__":
    print("🔧 DHT11 Real Data Test")
    print("=" * 30)
    
    success_count = 0
    for attempt in range(3):
        print(f"\n🔄 Attempt {attempt + 1}/3:")
        
        hum, temp = basic_dht11_read(22)
        
        if hum is not None and temp is not None:
            print(f"✅ Success: {temp:.1f}°C, {hum:.1f}%rH")
            success_count += 1
            break
        else:
            print("❌ Failed")
            if attempt < 2:
                print("   Waiting 2 seconds...")
                time.sleep(2)
    
    if success_count > 0:
        print(f"\n🎉 DHT11 test successful after {success_count} attempts!")
    else:
        print("\n❌ All attempts failed")
        print("Check connections:")
        print("  DHT11 VCC → 3.3V")
        print("  DHT11 DATA → GPIO 15") 
        print("  DHT11 GND → GND")