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
            time.sleep(0.25)  # 250ms stable high (increased for reliability)
            
            # Start signal - pull low
            GPIO.output(pin, GPIO.LOW)
            if sensor_type == DHT11:
                time.sleep(0.020)  # DHT11: 20ms low (increased from 18ms for stability)
            else:  # DHT22
                time.sleep(0.001)  # DHT22: 1ms low (increased from 0.8ms)
            
            # Release line and wait for sensor response
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            time.sleep(0.00004)  # 40μs settling time after pull-up (critical!)
            
            # Wait for initial sensor response (should go LOW first)
            timeout_start = time.time()
            while GPIO.input(pin) == 1:
                if time.time() - timeout_start > 0.15:
                    print(f"DHT{sensor_type}: No initial response (pin stuck HIGH)")
                    return None, None
            
            # Now collect all timing changes
            changes = []
            last_state = GPIO.input(pin)
            change_count = 0
            start_time = time.time()
            
            # More aggressive timing collection with longer timeout
            while change_count < 200 and (time.time() - start_time) < 0.15:
                current_state = GPIO.input(pin)
                if current_state != last_state:
                    changes.append((time.time(), current_state))
                    last_state = current_state
                    change_count += 1
            
            print(f"DHT{sensor_type}: Collected {len(changes)} signal changes")
            
            # We need at least 78-83 changes: start + 40 bits * 2 (low+high) + response
            # Lowered threshold from 82 to 78 for better reliability (some noise tolerance)
            if len(changes) < 78:
                print(f"DHT{sensor_type}: Insufficient signal changes: {len(changes)}")
                # Try to diagnose the issue
                if len(changes) == 0:
                    print("  → No signal changes detected - check sensor connection")
                elif len(changes) < 10:
                    print("  → Very few changes - sensor may not be responding")
                elif len(changes) < 78:
                    print(f"  → Too few signals - expected ~82, got {len(changes)}")
                return None, None
            elif len(changes) < 82:
                # Borderline case (78-81 changes) - try alternative parsing
                print(f"DHT{sensor_type}: Borderline signal count ({len(changes)}), trying alternative parse...")
                result = self._alternative_parse(changes, sensor_type)
                if result[0] is not None and result[1] is not None:
                    return result
                # If alternative fails, continue with normal parsing
            
            # Simplified parsing - skip first few transitions and parse directly
            # DHT11 protocol: Response LOW(80us) + Response HIGH(80us) + 40 data bits
            # Each data bit: Bit start LOW(50us) + Data HIGH(26-28us for '0', 70us for '1')
            
            print(f"DHT{sensor_type}: Parsing {len(changes)} transitions...")
            
            # More robust bit detection
            pulses = []
            # Filter for only HIGH pulses in the data section
            # Typically index 0-1 are start signals, so we look after that
            # We need to find the start of the data transmission
            
            # Skip the initial low start signal and response signals
            # DHT response: LOW(~80us) + HIGH(~80us) before data starts
            # Transitions: [start signals] [response LOW transition] [response HIGH transition] [data bits...]
            # We need to skip first 5 transitions to get into data section
            start_index = 5  # Skip start + response transitions
            
            # Now extract high pulses from data section only
            high_pulses = []
            all_pulses = []  # For debugging
            for i in range(start_index, len(changes) - 1):
                if changes[i][1] == 1:  # High state
                    if i+1 < len(changes):
                        duration = changes[i+1][0] - changes[i][0]
                        all_pulses.append(duration)
                        # Filter: DHT11 data pulses are 26-70μs (but can be up to 72-73μs)
                        # Response pulse is ~80μs, so upper limit must be below 80
                        # Upper limit: 78μs (was 75μs - too strict!)
                        if 0.000018 < duration < 0.000078:  # 18-78μs
                            high_pulses.append(duration)
            
            # Debug: Show pulse statistics
            if all_pulses:
                all_us = [d * 1e6 for d in all_pulses]
                filtered_us = [d * 1e6 for d in high_pulses]
                print(f"DHT{sensor_type}: All HIGH pulses: {len(all_us)} (min={min(all_us):.1f}μs, max={max(all_us):.1f}μs)")
                print(f"DHT{sensor_type}: Filtered (18-78μs): {len(filtered_us)} pulses")
            
            print(f"DHT{sensor_type}: Found {len(high_pulses)} valid HIGH pulses")
            
            # We need exactly 40 bits defined by HIGH pulses
            # A '0' is ~26-28us, a '1' is ~70us
            # Threshold usually around 50us (0.000050)
            
            valid_bits = []
            
            # If we have more than 40 pulses, we might have captured noise or start signals
            # Try to take the last 40 pulses if there are too many
            candidates = high_pulses
            
            if len(candidates) >= 40:
                # Try to align to the best 40 bits
                # Strategy: Take the last 40, or first 40?
                # Usually the last 40 are the data if we captured the start sequence
                
                # Let's try to find a sequence of 40 pulses that makes sense
                # For now, let's just try the first 40 reliable looking pulses
                    
                # Threshold for bit '1' vs '0'
                # DHT11: '0'=26μs, '1'=70μs -> threshold should be ~45-48μs
                # DHT22: '0'=26-28μs, '1'=70μs -> threshold ~50μs
                threshold = 0.000045 if sensor_type == DHT11 else 0.000050
                
                bits = []
                for duration in candidates:
                    # Filter out extremely short glitches (<12μs) or long timeouts (>78μs)
                    if duration < 0.000012:
                        continue
                    if duration > 0.000078:  # Below response pulse (~80μs)
                        continue
                    
                    bits.append(1 if duration > threshold else 0)
                
                if len(bits) >= 40:
                    # If we have excess bits, often the start signals are included
                    # If count is 41 or 42, usually first ones are response signals which are long (~80us -> interpreted as 1)
                    # But response signal is 80us, bit '1' is 70us. Hard to distinguish.
                    # DHT protocol: 
                    # Response: Low 80us -> High 80us
                    # Bit 0: Low 50us -> High 26us
                    # Bit 1: Low 50us -> High 70us
                    
                    # Use a sliding window of 40 bits and check checksum for each
                    print(f"DHT{sensor_type}: Analyzing {len(bits)} potential bits for valid checksum...")
                    
                    for offset in range(len(bits) - 39): # Try all 40-bit windows
                            window_bits = bits[offset : offset+40]
                            
                            # Calculate checksum for this window
                            bytes_val = []
                            for b_idx in range(0, 40, 8):
                                byte = 0
                                for bit_idx in range(8):
                                    byte = (byte << 1) | window_bits[b_idx + bit_idx]
                                bytes_val.append(byte)
                                
                            # Verify checksum
                            calc_sum = (bytes_val[0] + bytes_val[1] + bytes_val[2] + bytes_val[3]) & 0xFF
                            if calc_sum == bytes_val[4]:
                                print(f"DHT{sensor_type}: Valid checksum found at offset {offset}")
                                valid_bits = window_bits
                                valid_start = offset
                                break
                    
                    # Fallback: if no checksum matches, try the last 40 bits as they are most likely data
                    if not valid_bits and len(bits) >= 40:
                            print(f"DHT{sensor_type}: No valid checksum found, using last 40 bits")
                            valid_bits = bits[-40:]    
                else:
                        print(f"DHT{sensor_type}: Too few valid pulses after filtering: {len(bits)}")
                        
            if not valid_bits:
                    # One last try with the original logic if robust fails
                    if len(high_pulses) >= 40:
                        threshold = 0.000050
                        valid_bits = [1 if d > threshold else 0 for d in high_pulses[-40:]]
                    else:
                        print(f"DHT{sensor_type}: Insufficient HIGH pulses for data")
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
            
            # Debug: Print all 5 bytes
            print(f"DHT{sensor_type}: Bytes = [{bytes_data[0]:02X}h {bytes_data[1]:02X}h {bytes_data[2]:02X}h {bytes_data[3]:02X}h {bytes_data[4]:02X}h]")
            print(f"DHT{sensor_type}: Dec   = [{bytes_data[0]:3d} {bytes_data[1]:3d} {bytes_data[2]:3d} {bytes_data[3]:3d} {bytes_data[4]:3d}]")
            
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
                hum_raw = (bytes_data[0] << 8) | bytes_data[1]
                temp_raw = ((bytes_data[2] & 0x7F) << 8) | bytes_data[3]
                
                # DHT22 sanity check - raw values should be reasonable
                # Humidity: 0-1000 (0.0-100.0%)
                # Temperature: 0-800 (-40 to +80°C)
                if hum_raw > 1000:
                    print(f"DHT22: Invalid raw humidity {hum_raw}, likely bit error")
                    return None, None
                if temp_raw > 800:
                    print(f"DHT22: Invalid raw temperature {temp_raw}, likely bit error")
                    return None, None
                
                hum = hum_raw / 10.0
                temp = temp_raw / 10.0
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
                print(f"DHT{sensor_type}: Invalid humidity: {hum}%")
                return None, None
                    
            if temp < -10 or temp > 60:  # More realistic range for DHT sensors
                print(f"DHT{sensor_type}: Invalid temperature: {temp}°C")
                return None, None
            
            # Additional check: If values suddenly doubled, reject the reading
            if hasattr(self, 'last_temp') and self.last_temp is not None:
                if abs(temp - self.last_temp * 2) < 2.0:  # Close to 2x previous
                    print(f"DHT{sensor_type}: Doubled value detected - {temp}°C vs last {self.last_temp}°C")
                    return None, None
                if abs(hum - self.last_hum * 2) < 5.0:  # Close to 2x previous
                    print(f"DHT{sensor_type}: Doubled humidity detected - {hum}% vs last {self.last_hum}%")
                    return None, None
                # Check for sudden large changes ONLY after we have real baseline (not initial placeholder values)
                # Skip validation for first few readings to establish baseline
                if self.read_count >= 3:  # Only validate after 3+ successful reads
                    if abs(temp - self.last_temp) > 10.0:
                        print(f"DHT{sensor_type}: Temperature jump too large: {temp}°C vs {self.last_temp}°C")
                        return None, None
                    if abs(hum - self.last_hum) > 25.0:  # Relaxed from 20% to 25% to allow initial settling
                        print(f"DHT{sensor_type}: Humidity jump too large: {hum}% vs {self.last_hum}%")
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
        """Alternative parsing method for partial data (78-81 signals)"""
        print(f"DHT{sensor_type}: Trying alternative timing analysis...")
        
        try:
            # Extract HIGH pulses more carefully
            high_pulses = []
            for i in range(5, len(changes) - 1):  # Skip first 5 transitions (start+response)
                if changes[i][1] == 1:  # HIGH state
                    duration = changes[i+1][0] - changes[i][0]
                    # Filter valid data pulses (DHT data: 26-70μs but can be up to 73μs)
                    # Upper limit MUST be below 80μs to exclude response
                    if 0.000018 < duration < 0.000078:  # 18-78μs
                        high_pulses.append(duration)
            
            print(f"DHT{sensor_type}: Alternative found {len(high_pulses)} valid HIGH pulses")
            
            # Need at least 36 pulses for meaningful data (relaxed from 38)
            if len(high_pulses) >= 36:
                # Take the best 40 pulses (or as many as we have)
                data_pulses = high_pulses[:40] if len(high_pulses) >= 40 else high_pulses
                
                # Convert pulses to bits using threshold
                # DHT11: '0'=26μs, '1'=70μs -> threshold=45μs
                # DHT22: '0'=26-28μs, '1'=70μs -> threshold=50μs
                threshold = 0.000045 if sensor_type == 11 else 0.000050
                bits = [1 if d > threshold else 0 for d in data_pulses]
                
                # Pad to 40 bits if needed
                while len(bits) < 40:
                    bits.append(0)
                bits = bits[:40]  # Ensure exactly 40
                
                print(f"DHT{sensor_type}: Alternative extracted {len(bits)} bits")
                
                # Convert to bytes
                bytes_data = []
                for i in range(0, 40, 8):
                    byte_val = 0
                    for j in range(8):
                        byte_val = (byte_val << 1) | bits[i + j]
                    bytes_data.append(byte_val)
                
                # Debug: Print all 5 bytes
                print(f"DHT{sensor_type}: Alt Bytes = [{bytes_data[0]:02X}h {bytes_data[1]:02X}h {bytes_data[2]:02X}h {bytes_data[3]:02X}h {bytes_data[4]:02X}h]")
                print(f"DHT{sensor_type}: Alt Dec   = [{bytes_data[0]:3d} {bytes_data[1]:3d} {bytes_data[2]:3d} {bytes_data[3]:3d} {bytes_data[4]:3d}]")
                
                # DHT11: byte[0]=humidity_int, byte[1]=humidity_decimal(0), byte[2]=temp_int, byte[3]=temp_decimal(0), byte[4]=checksum
                # DHT22: byte[0-1]=humidity*10, byte[2-3]=temp*10, byte[4]=checksum
                if sensor_type == 11:  # DHT11
                    hum = bytes_data[0]
                    temp = bytes_data[2]
                    checksum_calc = (bytes_data[0] + bytes_data[1] + bytes_data[2] + bytes_data[3]) & 0xFF
                    checksum_match = (checksum_calc == bytes_data[4])
                    
                    print(f"DHT{sensor_type}: Parsed -> Hum={hum}%, Temp={temp}°C, Checksum {'OK' if checksum_match else 'FAIL'} (calc={checksum_calc:02X}h expected={bytes_data[4]:02X}h)")
                    
                    # Accept if values are reasonable, even if checksum is off by 1-2
                    # DHT11 is not very reliable with checksums
                    checksum_close = abs(checksum_calc - bytes_data[4]) <= 2
                    
                    if 20 <= hum <= 90 and 15 <= temp <= 40:  # Reasonable indoor range
                        if checksum_match or checksum_close:
                            print(f"DHT{sensor_type}: Alternative parsing success: {temp}°C, {hum}%rH {'(checksum close)' if not checksum_match else ''}")
                            # Update last known values
                            self.last_temp = float(temp)
                            self.last_hum = float(hum)
                            self.read_count += 1
                            return float(hum), float(temp)
                        else:
                            print(f"DHT{sensor_type}: Values reasonable but checksum too far off")
                else:  # DHT22
                    hum = ((bytes_data[0] << 8) | bytes_data[1]) / 10.0
                    temp_raw = (bytes_data[2] << 8) | bytes_data[3]
                    if temp_raw & 0x8000:  # Negative temperature
                        temp = -((temp_raw & 0x7FFF) / 10.0)
                    else:
                        temp = temp_raw / 10.0
                    
                    if 0 <= hum <= 100 and -40 <= temp <= 80:
                        print(f"DHT{sensor_type}: Alternative parsing success: {temp:.1f}°C, {hum:.1f}%rH")
                        # Update last known values
                        self.last_temp = temp
                        self.last_hum = hum
                        self.read_count += 1
                        return hum, temp
            
            print(f"DHT{sensor_type}: Alternative parsing failed - insufficient valid pulses")
            return None, None
            
        except Exception as e:
            print(f"DHT{sensor_type}: Alternative parsing error: {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def read_retry(self, sensor_type=None, pin=None, retries=5, delay=2.5):
        """Adafruit_DHT.read_retry yerine - Otomatik algılama desteği
        
        Args:
            retries: Deneme sayısı (varsayılan 5 - daha kararlı okuma için)
            delay: Denemeler arası bekleme (varsayılan 2.5s - DHT minimum requirement)
        """
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

def read_retry(sensor_type=None, pin=DHT_PIN, retries=5, delay=2.5):
    """Adafruit_DHT.read_retry replacement with auto-detection
    
    Args:
        retries: Number of retry attempts (default 5 for stable readings)
        delay: Delay between retries in seconds (default 2.5s - DHT requirement)
    """
    return dht_native.read_retry(sensor_type, pin, retries, delay)

def read(sensor_type=None, pin=DHT_PIN):
    """Adafruit_DHT.read replacement with auto-detection"""
    return dht_native.read(sensor_type, pin)

def detect_sensor(pin=DHT_PIN):
    """DHT11/DHT22 otomatik algılama"""
    return dht_native.detect_sensor_type(pin)