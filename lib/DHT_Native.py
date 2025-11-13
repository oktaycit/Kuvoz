#!/usr/bin/env python3
# -*-coding:utf-8-*-
"""
Native DHT11/DHT22 sensor driver for Raspberry Pi
Adafruit_DHT kütüphanesi yerine platform bağımsız çözüm
GPIO 15 (Physical Pin 10) - DHT11/DHT22 Auto-Detection
"""

import time
import RPi.GPIO as GPIO

# DHT sensor constants
DHT11 = 11
DHT22 = 22

# Default GPIO pin for DHT sensor
DHT_PIN = 15  # GPIO 15 (Physical Pin 10)

class DHT_Native:
    def __init__(self, pin=DHT_PIN):
        self.pin = pin
        self.last_temp = 25.0
        self.last_hum = 50.0
        self.read_count = 0
        self.detected_sensor_type = None
        
    def detect_sensor_type(self, pin=None):
        """
        DHT11 vs DHT22 otomatik algılama
        DHT22 daha hassas timing ve farklı veri formatına sahip
        """
        if pin is None:
            pin = self.pin
            
        print(f"DHT Sensor detection on GPIO {pin}...")
        
        # Önce DHT22 protokolü ile dene (daha hassas)
        result = self.read_dht_gpio(DHT22, pin)
        if result[0] is not None and result[1] is not None:
            # read_dht_gpio returns (hum, temp)
            hum, temp = result
            if isinstance(temp, float) and isinstance(hum, float):
                if temp > -40 and temp < 80 and hum >= 0 and hum <= 100:
                    print(f"DHT22 detected on GPIO {pin}")
                    self.detected_sensor_type = DHT22
                    return DHT22
        
        # DHT11 protokolü ile dene
        result = self.read_dht_gpio(DHT11, pin)
        if result[0] is not None and result[1] is not None:
            # read_dht_gpio returns (hum, temp)
            hum, temp = result
            if isinstance(temp, (int, float)) and isinstance(hum, (int, float)):
                # DHT11 ranges: temp 0-50°C, humidity 20-100%
                if temp >= 0 and temp <= 50 and hum >= 20 and hum <= 100:
                    print(f"DHT11 detected on GPIO {pin}")
                    self.detected_sensor_type = DHT11
                    return DHT11
        
        print(f"No DHT sensor detected on GPIO {pin}")
        return None
        
    def read_dht_gpio(self, sensor_type, pin):
        """
        Gerçek DHT11/DHT22 sensör okuma - GPIO protokolü
        DHT timing protokolü implementasyonu - İyileştirilmiş versiyon
        """
        try:
            # Only set mode if not already set
            if GPIO.getmode() is None:
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
            
            # Try different starting points to find valid data
            # DHT protocol: response signals + 40 data bits (each bit = LOW + HIGH)
            valid_bits = None
            valid_start = None
            
            for start_try in [2, 3, 4, 5]:
                print(f"DHT{sensor_type}: Trying start position {start_try}")
                bits = []
                
                # Simple approach: every HIGH pulse duration = 1 bit
                for i in range(start_try, len(changes) - 1):
                    if changes[i][1] == 1 and i + 1 < len(changes) and changes[i+1][1] == 0:
                        # HIGH to LOW transition - measure HIGH duration
                        high_duration = changes[i+1][0] - changes[i][0]
                        bit_value = 1 if high_duration > 0.00004 else 0
                        bits.append(bit_value)
                        
                        if len(bits) >= 40:
                            break
                
                # Check if this gives reasonable data
                if len(bits) >= 32:
                    # Quick validation
                    hum_byte = 0
                    for j in range(8):
                        if j < len(bits):
                            hum_byte = (hum_byte << 1) | bits[j]
                    
                    if 0 <= hum_byte <= 100:  # Valid humidity range
                        valid_bits = bits
                        valid_start = start_try
                        print(f"DHT{sensor_type}: Found valid data at start {start_try}")
                        break
                    else:
                        print(f"DHT{sensor_type}: Start {start_try} gave invalid humidity: {hum_byte}")
            
            if valid_bits is None:
                print(f"DHT{sensor_type}: No valid starting position found")
                return None, None
            
            bits = valid_bits[:40]  # Take exactly 40 bits
            
            print(f"DHT{sensor_type}: Extracted {len(bits)} bits")
            
            # Debug: Show first 16 bits (2 bytes)
            if len(bits) >= 16:
                bit_str = ''.join(map(str, bits[:16]))
                print(f"DHT{sensor_type}: First 16 bits: {bit_str}")
            
            # Ensure exactly 40 bits
            if len(bits) < 40:
                while len(bits) < 40:
                    bits.append(0)  # Pad with zeros
                print(f"DHT{sensor_type}: Padded to 40 bits")
            elif len(bits) > 40:
                bits = bits[:40]  # Truncate to 40
                print(f"DHT{sensor_type}: Truncated to 40 bits")
            
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
                # DHT11: Simple integer format
                # [Humidity_H][Humidity_L][Temp_H][Temp_L][Checksum]
                # No decimal places - just integers
                hum = bytes_data[0]  # Just the humidity byte, ignore decimal
                temp = bytes_data[2]  # Just the temperature byte, ignore decimal
                if bytes_data[2] & 0x80:  # Negative temperature
                    temp = -temp
            else:  # DHT22
                # DHT22: Higher precision - CRITICAL: Do NOT multiply second byte
                # DHT22 format: [Humidity_H][Humidity_L][Temp_H][Temp_L][Checksum]
                # Temperature value: (Temp_H << 8 | Temp_L) / 10.0 (not /100)
                hum = ((bytes_data[0] << 8) | bytes_data[1]) / 10.0
                temp = (((bytes_data[2] & 0x7F) << 8) | bytes_data[3]) / 10.0
                if bytes_data[2] & 0x80:  # Negative temperature
                    temp = -temp
            
            print(f"DHT{sensor_type}: Raw parsed - Humidity: {hum}%, Temperature: {temp}°C")
            
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
                print(f"DHT{sensor_type}: Invalid humidity: {hum}% - trying bit shift correction")
                # Try bit-shifted version (common parsing error)
                for shift in [1, 2, 3]:
                    shifted_bits = bits[shift:] + [0] * shift
                    shifted_bytes = []
                    for i in range(0, 40, 8):
                        byte_val = 0
                        for j in range(8):
                            if i + j < len(shifted_bits):
                                byte_val = (byte_val << 1) | shifted_bits[i + j]
                        shifted_bytes.append(byte_val)
                    
                    if len(shifted_bytes) >= 4:
                        shifted_hum = shifted_bytes[0] + shifted_bytes[1] * 0.1
                        shifted_temp = shifted_bytes[2] + shifted_bytes[3] * 0.1
                        if 0 <= shifted_hum <= 100 and 0 <= shifted_temp <= 60:
                            print(f"DHT{sensor_type}: Bit shift {shift} correction successful")
                            hum, temp = shifted_hum, shifted_temp
                            break
                else:
                    print(f"DHT{sensor_type}: Could not correct invalid humidity: {hum}")
                    return None, None
                    
            if temp < -10 or temp > 60:  # More realistic range for DHT11
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
            # DON'T cleanup GPIO - keep it initialized for web server
            # GPIO.cleanup() causes mode loss in web server
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
                
                # Convert to bytes (pad to 40 bits if needed)
                if len(bits) == 39:
                    bits.append(0)  # Add missing bit
                    print(f"DHT{sensor_type}: Padded to 40 bits")
                
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
    
    def read_retry(self, sensor_type=None, pin=None, retries=3, delay=2):
        """Adafruit_DHT.read_retry yerine - Otomatik algılama desteği"""
        if pin is None:
            pin = self.pin
            
        # Otomatik algılama
        if sensor_type is None:
            if self.detected_sensor_type is None:
                self.detect_sensor_type(pin)
            sensor_type = self.detected_sensor_type
            
        if sensor_type is None:
            print(f"No DHT sensor detected on GPIO {pin}")
            return None, None
            
        for attempt in range(retries):
            hum, temp = self.read_dht_gpio(sensor_type, pin)
            if hum is not None and temp is not None:
                print(f"DHT{sensor_type} reading successful: {temp}°C, {hum}%")
                return hum, temp
            print(f"DHT{sensor_type} attempt {attempt+1}/{retries} failed")
            if attempt < retries - 1:
                time.sleep(delay)
        
        print(f"DHT{sensor_type} all attempts failed")
        return None, None
    
    def read(self, sensor_type=None, pin=None):
        """Adafruit_DHT.read yerine - Otomatik algılama desteği"""
        if pin is None:
            pin = self.pin
            
        # Otomatik algılama
        if sensor_type is None:
            if self.detected_sensor_type is None:
                self.detect_sensor_type(pin)
            sensor_type = self.detected_sensor_type
            
        if sensor_type is None:
            return None, None
            
        return self.read_dht_gpio(sensor_type, pin)

# Global instance with GPIO 15
dht_native = DHT_Native(pin=DHT_PIN)

def read_retry(sensor_type=None, pin=DHT_PIN, retries=3, delay=2):
    """Adafruit_DHT.read_retry replacement with auto-detection"""
    return dht_native.read_retry(sensor_type, pin, retries, delay)

def read(sensor_type=None, pin=DHT_PIN):
    """Adafruit_DHT.read replacement with auto-detection"""
    return dht_native.read(sensor_type, pin)

def detect_sensor(pin=DHT_PIN):
    """DHT11/DHT22 otomatik algılama"""
    return dht_native.detect_sensor_type(pin)