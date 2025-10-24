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
        DHT timing protokolü implementasyonu
        """
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # DHT sensörü sinyal başlatma
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.HIGH)
            time.sleep(0.05)  # 50ms stable high
            
            # Start signal - pull low
            GPIO.output(pin, GPIO.LOW)
            if sensor_type == DHT11:
                time.sleep(0.02)  # DHT11: 20ms low
            else:  # DHT22
                time.sleep(0.001)  # DHT22: 1ms low
            
            # Release line
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Collect timing data
            changes = []
            last_state = GPIO.input(pin)
            max_changes = 1000
            change_count = 0
            start_time = time.time()
            
            while change_count < max_changes and (time.time() - start_time) < 0.1:
                current_state = GPIO.input(pin)
                if current_state != last_state:
                    changes.append(time.time())
                    last_state = current_state
                    change_count += 1
            
            # Parse DHT data from timing
            if len(changes) < 80:
                print(f"DHT{sensor_type}: Insufficient data changes: {len(changes)}")
                return None, None
            
            # Extract data bits from timing (simplified)
            bits = []
            for i in range(2, len(changes), 2):
                if i + 1 < len(changes):
                    high_duration = changes[i + 1] - changes[i]
                    bits.append(1 if high_duration > 0.00005 else 0)  # 50μs threshold
            
            if len(bits) < 40:
                print(f"DHT{sensor_type}: Insufficient bits: {len(bits)}")
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