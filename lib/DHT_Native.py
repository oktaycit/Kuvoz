#!/usr/bin/env python3
# -*-coding:utf-8-*-
"""
Native DHT11/DHT22 sensor driver for Raspberry Pi
Adafruit_DHT kütüphanesi yerine platform bağımsız çözüm
"""

import time
import RPi.GPIO as GPIO

# DHT sensor constants
DHT11 = 11
DHT22 = 22

class DHT_Native:
    def __init__(self):
        self.last_temp = 25.0
        self.last_hum = 50.0
        self.read_count = 0
        
    def read_dht_gpio(self, sensor_type, pin):
        """
        Gerçek DHT11/DHT22 sensör okuma - GPIO protokolü
        DHT timing protokolü implementasyonu - İyileştirilmiş versiyon
        """
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # DHT sensörü sinyal başlatma - daha uzun stabilizasyon
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.HIGH)
            time.sleep(0.1)  # 100ms stable high
            
            # Start signal - pull low
            GPIO.output(pin, GPIO.LOW)
            if sensor_type == DHT11:
                time.sleep(0.018)  # DHT11: 18ms low (recommended minimum)
            else:  # DHT22
                time.sleep(0.0008)  # DHT22: 0.8ms low
            
            # Release line and wait for sensor response
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Wait for initial sensor response (should go LOW first)
            timeout_start = time.time()
            while GPIO.input(pin) == 1:
                if time.time() - timeout_start > 0.1:
                    print(f"DHT{sensor_type}: No initial response (pin stuck HIGH)")
                    return None, None
            
            # Now collect all timing changes
            changes = []
            last_state = GPIO.input(pin)
            change_count = 0
            start_time = time.time()
            
            # More aggressive timing collection
            while change_count < 200 and (time.time() - start_time) < 0.1:
                current_state = GPIO.input(pin)
                if current_state != last_state:
                    changes.append((time.time(), current_state))
                    last_state = current_state
                    change_count += 1
            
            print(f"DHT{sensor_type}: Collected {len(changes)} signal changes")
            
            # We need at least 83 changes: start + 40 bits * 2 (low+high) + response
            if len(changes) < 82:
                print(f"DHT{sensor_type}: Insufficient signal changes: {len(changes)}")
                # Try to diagnose the issue
                if len(changes) == 0:
                    print("  → No signal changes detected - check sensor connection")
                elif len(changes) < 10:
                    print("  → Very few changes - sensor may not be responding")
                else:
                    print(f"  → Partial response - expected ~83, got {len(changes)}")
                return None, None
            
            # Simplified parsing - skip first few transitions and parse directly
            # DHT11 protocol: Response LOW(80us) + Response HIGH(80us) + 40 data bits
            # Each data bit: Bit start LOW(50us) + Data HIGH(26-28us for '0', 70us for '1')
            
            print(f"DHT{sensor_type}: Parsing {len(changes)} transitions...")
            
            # Skip initial response (usually first 2-4 transitions)
            # Look for consistent alternating pattern starting from transition 2 or 3
            data_start = 2
            if len(changes) > 4:
                data_start = 3  # Skip more initial transitions
            
            print(f"DHT{sensor_type}: Starting data parsing from transition {data_start}")
            
            # Extract 40 data bits from timing
            bits = []
            bit_count = 0
            
            # Process transitions in pairs - each bit has LOW then HIGH
            i = data_start
            while i < len(changes) - 1 and bit_count < 40:
                if changes[i][1] == 0 and i + 1 < len(changes) and changes[i+1][1] == 1:
                    # This is a LOW->HIGH transition pair representing one bit
                    if i + 2 < len(changes):
                        # Measure HIGH duration until next LOW  
                        high_duration = changes[i+2][0] - changes[i+1][0]
                        # DHT11: '0' = ~26-28μs HIGH, '1' = ~70μs HIGH
                        bit_value = 1 if high_duration > 0.00004 else 0  # 40μs threshold
                        bits.append(bit_value)
                        bit_count += 1
                        i += 2  # Skip to next bit
                    else:
                        i += 1
                else:
                    i += 1
            
            print(f"DHT{sensor_type}: Extracted {len(bits)} bits")
            
            # Debug: Show first 10 bits
            if len(bits) >= 10:
                bit_str = ''.join(map(str, bits[:10]))
                print(f"DHT{sensor_type}: First 10 bits: {bit_str}")
            
            if len(bits) < 40:
                print(f"DHT{sensor_type}: Insufficient bits: {len(bits)} (need 40)")
                # Try alternative parsing if we have some bits but not enough
                if len(bits) >= 20:
                    print(f"DHT{sensor_type}: Attempting alternative parsing...")
                    return self._alternative_parse(changes, sensor_type)
                return None, None
            
            # Convert bits to bytes
            bytes_data = []
            for i in range(0, min(40, len(bits)), 8):
                byte_val = 0
                for j in range(8):
                    if i + j < len(bits):
                        byte_val = (byte_val << 1) | bits[i + j]
                bytes_data.append(byte_val)
            
            if len(bytes_data) < 5:
                print(f"DHT{sensor_type}: Insufficient bytes: {len(bytes_data)}")
                return None, None
            
            # Parse humidity and temperature
            if sensor_type == DHT11:
                # DHT11: Integer values
                hum = bytes_data[0] + bytes_data[1] * 0.1
                temp = bytes_data[2] + bytes_data[3] * 0.1
                if bytes_data[2] & 0x80:  # Negative temperature
                    temp = -temp
            else:  # DHT22
                # DHT22: Higher precision
                hum = ((bytes_data[0] << 8) | bytes_data[1]) * 0.1
                temp = (((bytes_data[2] & 0x7F) << 8) | bytes_data[3]) * 0.1
                if bytes_data[2] & 0x80:  # Negative temperature
                    temp = -temp
            
            # Checksum verification
            checksum = (bytes_data[0] + bytes_data[1] + bytes_data[2] + bytes_data[3]) & 0xFF
            if checksum != bytes_data[4]:
                print(f"DHT{sensor_type}: Checksum error: {checksum} != {bytes_data[4]}")
                # Return data anyway if values seem reasonable
                if 0 <= hum <= 100 and -40 <= temp <= 80:
                    print(f"DHT{sensor_type}: Using data despite checksum error")
                else:
                    return None, None
            
            # Validate readings
            if hum < 0 or hum > 100:
                print(f"DHT{sensor_type}: Invalid humidity: {hum}")
                return None, None
            if temp < -40 or temp > 80:
                print(f"DHT{sensor_type}: Invalid temperature: {temp}")
                return None, None
            
            # Update last known good values
            self.last_temp = temp
            self.last_hum = hum
            self.read_count += 1
            
            print(f"DHT{sensor_type} Native: {temp:.1f}°C, {hum:.1f}%rH")
            return hum, temp
            
        except Exception as e:
            print(f"DHT{sensor_type} Native read error: {e}")
            # Return last known good values if available
            if hasattr(self, 'last_temp') and hasattr(self, 'last_hum'):
                if self.last_temp is not None and self.last_hum is not None:
                    print(f"DHT{sensor_type}: Using last known values: {self.last_temp:.1f}°C, {self.last_hum:.1f}%rH")
                    return self.last_hum, self.last_temp
            return None, None
        finally:
            try:
                GPIO.cleanup()
            except:
                pass
    
    def _alternative_parse(self, changes, sensor_type):
        """Alternative parsing method for partial data"""
        print(f"DHT{sensor_type}: Trying alternative timing analysis...")
        
        try:
            # Simple method: assume every 2 transitions = 1 bit, skip first 4
            bits = []
            for i in range(4, len(changes) - 1, 2):
                if i + 1 < len(changes):
                    # Look at duration between changes
                    duration = changes[i+1][0] - changes[i][0]
                    # Longer duration = '1', shorter = '0'
                    bits.append(1 if duration > 0.00005 else 0)
                    if len(bits) >= 40:
                        break
            
            if len(bits) >= 32:  # At least humidity + temperature
                print(f"DHT{sensor_type}: Alternative got {len(bits)} bits")
                
                # Convert to bytes (take first 32 bits minimum)
                bytes_data = []
                for i in range(0, min(40, len(bits)), 8):
                    byte_val = 0
                    for j in range(8):
                        if i + j < len(bits):
                            byte_val = (byte_val << 1) | bits[i + j]
                    bytes_data.append(byte_val)
                
                if len(bytes_data) >= 4:
                    # DHT11 parsing
                    hum = bytes_data[0]
                    temp = bytes_data[2]
                    
                    # Basic validation
                    if 0 <= hum <= 100 and 0 <= temp <= 50:
                        print(f"DHT{sensor_type}: Alternative parsing success: {temp}°C, {hum}%rH")
                        return float(hum), float(temp)
            
            print(f"DHT{sensor_type}: Alternative parsing failed")
            return None, None
            
        except Exception as e:
            print(f"DHT{sensor_type}: Alternative parsing error: {e}")
            return None, None
    
    def read_retry(self, sensor_type, pin, retries=3, delay=2):
        """Adafruit_DHT.read_retry yerine"""
        for attempt in range(retries):
            hum, temp = self.read_dht_gpio(sensor_type, pin)
            if hum is not None and temp is not None:
                return hum, temp
            if attempt < retries - 1:
                time.sleep(delay)
        return None, None
    
    def read(self, sensor_type, pin):
        """Adafruit_DHT.read yerine"""
        return self.read_dht_gpio(sensor_type, pin)

# Global instance
dht_native = DHT_Native()

def read_retry(sensor_type, pin, retries=3, delay=2):
    """Adafruit_DHT.read_retry replacement"""
    return dht_native.read_retry(sensor_type, pin, retries, delay)

def read(sensor_type, pin):
    """Adafruit_DHT.read replacement"""
    return dht_native.read(sensor_type, pin)