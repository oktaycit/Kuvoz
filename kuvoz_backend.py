#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kuvoz Incubator Control System - Backend Only
Web interface için - Kivy dependencies kaldırıldı
GPIO kontrol ve sensor okuma modülü
"""

import threading
import time
import os
import sys
import math
import logging

# GPIO import
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("⚠️  RPi.GPIO not available - simulation mode")
    GPIO_AVAILABLE = False

# Sensor libraries
sys.path.append("lib/")
try:
    from DFRobot_Oxygen import *
    OXYGEN_AVAILABLE = True
except ImportError:
    print("⚠️  DFRobot_Oxygen not available - using simulation")
    OXYGEN_AVAILABLE = False

try:
    from DHT_Native import read_retry, read
    DHT_AVAILABLE = True
except ImportError:
    print("⚠️  DHT_Native not available - using simulation")
    DHT_AVAILABLE = False

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KuvozParam:
    """Global parametre sınıfı"""
    def __init__(self):
        self.sicaklik = 0.0
        self.nem = 0.0
        self.oksijen = 0.0
        self.system_active = True

# Global instance
KuvozParam = KuvozParam()

class KuvozBackend:
    """Kuvoz backend sistemi - Web interface için"""
    
    def __init__(self):
        # GPIO configuration
        self.outChannels = [5, 6, 13, 16, 19, 20, 21, 26]
        self.touch_bt = [5, 20, 21]
        self.pinDht = 15
        self.sensorDht = 22  # DHT22
        
        # System state
        self.button_states = {}
        self.slider_values = {
            'sld1': 30,   # Nebulizer interval (minutes)
            'sld2': 65,   # Humidity target (%)
            'sld3': 25.0, # Temperature target (°C)
            'sld4': 25.0, # IR Temperature target (°C)
            'sld5': 30,   # Ozone interval (minutes)
            'sld6': 12,   # Nebulizer hours interval
            'sld7': 8.0   # Ozone hours interval
        }
        
        # Control logic
        self.sensor_error_count = 0
        self.last_nebulizer_time = 0
        self.last_ozone_time = 0
        self.ir_state = False
        self.ozon_state = False
        
        # Threading
        self.running = False
        self.sensor_thread = None
        self.control_thread = None
        
        # Oxygen sensor
        self.oxygen_sensor = None
        
        self.init_system()
    
    def init_system(self):
        """Sistem başlatma"""
        logger.info("🚀 Initializing Kuvoz Backend System...")
        
        # GPIO setup
        if GPIO_AVAILABLE:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                
                # Output channels
                for pin in self.outChannels:
                    GPIO.setup(pin, GPIO.OUT)
                    GPIO.output(pin, GPIO.HIGH)  # Relay OFF başlangıç
                
                # Button states
                for i, pin in enumerate(self.outChannels):
                    self.button_states[f'b{i+1}'] = False
                
                logger.info("✅ GPIO initialized successfully")
            except Exception as e:
                logger.error(f"❌ GPIO initialization error: {e}")
        
        # Oxygen sensor
        if OXYGEN_AVAILABLE:
            try:
                self.oxygen_sensor = DFRobot_Oxygen_IIC(IIC_MODE, ADDRESS_3)
                logger.info("✅ Oxygen sensor initialized")
            except Exception as e:
                logger.error(f"❌ Oxygen sensor error: {e}")
                self.oxygen_sensor = None
        
        # Load settings
        self.load_failure_dat()
        
        logger.info("✅ Kuvoz Backend initialized")
    
    def safe_gpio_output(self, pin, state):
        """Thread-safe GPIO output"""
        if GPIO_AVAILABLE:
            try:
                GPIO.output(pin, state)
                return True
            except RuntimeError as e:
                logger.error(f"GPIO RuntimeError on pin {pin}: {e}")
                return False
            except Exception as e:
                logger.error(f"GPIO error on pin {pin}: {e}")
                return False
        return False
    
    def read_sensors(self):
        """Sensör okuma"""
        try:
            # DHT sensor
            if DHT_AVAILABLE:
                hum, temp = read_retry(self.sensorDht, self.pinDht)
                if hum is not None and temp is not None:
                    if isinstance(hum, float) and isinstance(temp, float):
                        KuvozParam.nem = hum
                        KuvozParam.sicaklik = temp
                        self.sensor_error_count = 0
                        logger.debug(f"DHT: {temp:.1f}°C, {hum:.1f}%")
                    else:
                        raise ValueError("Invalid DHT data types")
                else:
                    raise ValueError("DHT read returned None")
            else:
                # Simulation
                import random
                KuvozParam.sicaklik = 23 + random.random() * 5
                KuvozParam.nem = 60 + random.random() * 10
            
            # Oxygen sensor
            if self.oxygen_sensor:
                try:
                    oxygen_data = self.oxygen_sensor.get_oxygen_data(COLLECT_NUMBER)
                    KuvozParam.oksijen = oxygen_data
                except Exception as e:
                    logger.error(f"Oxygen sensor error: {e}")
                    # Automatic nebulizer control when oxygen sensor fails
                    self.nebulizer_auto_control()
            else:
                # Simulation
                import random
                KuvozParam.oksijen = 20 + random.random() * 2
        
        except Exception as e:
            logger.error(f"Sensor read error: {e}")
            self.sensor_error_count += 1
            
            if self.sensor_error_count > 5:
                logger.warning("Too many sensor errors - resetting to safe state")
                self.reset_to_safe_state()
    
    def control_logic(self):
        """Ana kontrol mantığı"""
        try:
            current_time = time.time()
            
            # Temperature control (b4 - pin 16)
            temp_target = self.slider_values['sld3']
            if KuvozParam.sicaklik < temp_target:
                self.safe_gpio_output(16, GPIO.LOW)  # Heating ON
                self.button_states['b4'] = True
            else:
                self.safe_gpio_output(16, GPIO.HIGH)  # Heating OFF
                self.button_states['b4'] = False
            
            # Humidity control (b3 - pin 13)
            hum_target = self.slider_values['sld2']
            if KuvozParam.nem < hum_target:
                self.safe_gpio_output(13, GPIO.LOW)  # Humidity ON
                self.button_states['b3'] = True
            else:
                self.safe_gpio_output(13, GPIO.HIGH)  # Humidity OFF
                self.button_states['b3'] = False
            
            # IR control timing (b2 - pin 6)
            self.ir_control(current_time)
            
            # Ozone control timing (b8 - pin 26)
            self.ozon_control(current_time)
        
        except Exception as e:
            logger.error(f"Control logic error: {e}")
    
    def ir_control(self, current_time):
        """IR nebulizer timed control"""
        try:
            ir_interval = self.slider_values['sld6'] * 3600  # hours to seconds
            ir_duration = self.slider_values['sld1'] * 60   # minutes to seconds
            
            if not self.ir_state and (current_time - self.last_nebulizer_time) > ir_interval:
                # Start IR
                self.safe_gpio_output(6, GPIO.LOW)
                self.button_states['b2'] = True
                self.ir_state = True
                self.last_nebulizer_time = current_time
                logger.info(f"IR Nebulizer ON for {self.slider_values['sld1']} minutes")
                
                # Schedule turn off
                def turn_off_ir():
                    time.sleep(ir_duration)
                    self.safe_gpio_output(6, GPIO.HIGH)
                    self.button_states['b2'] = False
                    self.ir_state = False
                    logger.info("IR Nebulizer OFF")
                
                threading.Thread(target=turn_off_ir, daemon=True).start()
        
        except Exception as e:
            logger.error(f"IR control error: {e}")
    
    def ozon_control(self, current_time):
        """Ozone timed control"""
        try:
            ozon_interval = self.slider_values['sld7'] * 3600  # hours to seconds
            ozon_duration = self.slider_values['sld5'] * 60   # minutes to seconds
            
            if not self.ozon_state and (current_time - self.last_ozone_time) > ozon_interval:
                # Start Ozone
                self.safe_gpio_output(26, GPIO.LOW)
                self.button_states['b8'] = True
                self.ozon_state = True
                self.last_ozone_time = current_time
                logger.info(f"Ozone ON for {self.slider_values['sld5']} minutes")
                
                # Schedule turn off
                def turn_off_ozon():
                    time.sleep(ozon_duration)
                    self.safe_gpio_output(26, GPIO.HIGH)
                    self.button_states['b8'] = False
                    self.ozon_state = False
                    logger.info("Ozone OFF")
                
                threading.Thread(target=turn_off_ozon, daemon=True).start()
        
        except Exception as e:
            logger.error(f"Ozone control error: {e}")
    
    def nebulizer_auto_control(self):
        """Automatic nebulizer when oxygen sensor unavailable"""
        try:
            current_time = time.time()
            auto_interval = 1800  # 30 minutes
            
            if (current_time - self.last_nebulizer_time) > auto_interval:
                duration = 300  # 5 minutes
                
                self.safe_gpio_output(6, GPIO.LOW)
                self.button_states['b2'] = True
                self.last_nebulizer_time = current_time
                logger.info(f"Auto Nebulizer ON for {duration/60} minutes (oxygen sensor unavailable)")
                
                def turn_off_auto_nebulizer():
                    time.sleep(duration)
                    self.safe_gpio_output(6, GPIO.HIGH)
                    self.button_states['b2'] = False
                    logger.info("Auto Nebulizer OFF")
                
                threading.Thread(target=turn_off_auto_nebulizer, daemon=True).start()
        
        except Exception as e:
            logger.error(f"Auto nebulizer error: {e}")
    
    def reset_to_safe_state(self):
        """Güvenli duruma geç"""
        logger.warning("Resetting system to safe state")
        try:
            for pin in self.outChannels:
                self.safe_gpio_output(pin, GPIO.HIGH)  # All relays OFF
            
            for key in self.button_states:
                self.button_states[key] = False
            
            self.sensor_error_count = 0
        except Exception as e:
            logger.error(f"Safe state reset error: {e}")
    
    def toggle_button(self, button_name, pin, state):
        """Manuel buton kontrolü"""
        try:
            gpio_state = GPIO.LOW if state else GPIO.HIGH
            if self.safe_gpio_output(pin, gpio_state):
                self.button_states[button_name] = state
                logger.info(f"Button {button_name} (pin {pin}): {'ON' if state else 'OFF'}")
                return True
            return False
        except Exception as e:
            logger.error(f"Button toggle error: {e}")
            return False
    
    def update_slider(self, slider_id, value):
        """Slider değeri güncelle"""
        try:
            self.slider_values[slider_id] = value
            logger.info(f"Slider {slider_id}: {value}")
            self.save_failure_dat()
            return True
        except Exception as e:
            logger.error(f"Slider update error: {e}")
            return False
    
    def load_failure_dat(self):
        """Failure.dat dosyasından ayarları yükle"""
        try:
            if os.path.exists("Failure.dat"):
                with open("Failure.dat", "r") as f:
                    line = f.read().strip()
                    if line:
                        parts = line.split()
                        if len(parts) >= 8:
                            # Button states
                            button_state = int(parts[0])
                            for i in range(8):
                                self.button_states[f'b{i+1}'] = bool(button_state & (1 << i))
                            
                            # Slider values
                            slider_keys = ['sld1', 'sld2', 'sld3', 'sld4', 'sld5', 'sld6', 'sld7']
                            for i, key in enumerate(slider_keys):
                                if i + 1 < len(parts):
                                    self.slider_values[key] = float(parts[i + 1])
                
                logger.info("✅ Settings loaded from Failure.dat")
        except Exception as e:
            logger.error(f"Load settings error: {e}")
    
    def save_failure_dat(self):
        """Ayarları Failure.dat dosyasına kaydet"""
        try:
            # Button states to bit pattern
            button_state = 0
            for i in range(8):
                if self.button_states.get(f'b{i+1}', False):
                    button_state |= (1 << i)
            
            # Create line
            line_parts = [str(button_state)]
            slider_keys = ['sld1', 'sld2', 'sld3', 'sld4', 'sld5', 'sld6', 'sld7']
            for key in slider_keys:
                line_parts.append(str(self.slider_values[key]))
            
            with open("Failure.dat", "w") as f:
                f.write(" ".join(line_parts))
            
            logger.info("✅ Settings saved to Failure.dat")
            return True
        except Exception as e:
            logger.error(f"Save settings error: {e}")
            return False
    
    def start_background_threads(self):
        """Background thread'leri başlat"""
        self.running = True
        
        def sensor_thread():
            """Sensor okuma thread'i"""
            while self.running:
                try:
                    self.read_sensors()
                    time.sleep(15)  # 15 saniyede bir
                except Exception as e:
                    logger.error(f"Sensor thread error: {e}")
                    time.sleep(5)
        
        def control_thread():
            """Kontrol thread'i"""
            while self.running:
                try:
                    if KuvozParam.system_active:
                        self.control_logic()
                    time.sleep(1)  # 1 saniyede bir
                except Exception as e:
                    logger.error(f"Control thread error: {e}")
                    time.sleep(2)
        
        self.sensor_thread = threading.Thread(target=sensor_thread, daemon=True)
        self.control_thread = threading.Thread(target=control_thread, daemon=True)
        
        self.sensor_thread.start()
        self.control_thread.start()
        
        logger.info("✅ Background threads started")
    
    def stop_background_threads(self):
        """Background thread'leri durdur"""
        self.running = False
        if self.sensor_thread:
            self.sensor_thread.join(timeout=2)
        if self.control_thread:
            self.control_thread.join(timeout=2)
        logger.info("✅ Background threads stopped")
    
    def shutdown_system(self):
        """Sistem kapatma"""
        logger.info("🔌 System shutdown requested")
        self.save_failure_dat()
        self.reset_to_safe_state()
        self.stop_background_threads()
        
        if GPIO_AVAILABLE:
            GPIO.cleanup()
        
        # System shutdown
        os.system("sudo shutdown -h now")
    
    def restart_system(self):
        """Sistem yeniden başlatma"""
        logger.info("🔄 System restart requested")
        self.save_failure_dat()
        self.reset_to_safe_state()
        self.stop_background_threads()
        
        if GPIO_AVAILABLE:
            GPIO.cleanup()
        
        # System restart
        os.system("sudo reboot")
    
    def get_system_status(self):
        """Sistem durumu bilgisi"""
        return {
            'sensors': {
                'temperature': {'value': f"{KuvozParam.sicaklik:.1f}", 'status': 'OK'},
                'humidity': {'value': f"{KuvozParam.nem:.1f}", 'status': 'OK'},
                'oxygen': {'value': f"{KuvozParam.oksijen:.1f}", 'status': 'OK'}
            },
            'buttons': self.button_states,
            'sliders': self.slider_values,
            'system': {
                'gpio_available': GPIO_AVAILABLE,
                'dht_available': DHT_AVAILABLE,
                'oxygen_available': OXYGEN_AVAILABLE and self.oxygen_sensor is not None,
                'error_count': self.sensor_error_count
            }
        }

def main():
    """Ana fonksiyon - test için"""
    logger.info("🚀 Starting Kuvoz Backend (standalone mode)")
    
    backend = KuvozBackend()
    backend.start_background_threads()
    
    try:
        logger.info("✅ Backend running - Press Ctrl+C to stop")
        while True:
            time.sleep(10)
            status = backend.get_system_status()
            logger.info(f"Status: T={status['sensors']['temperature']['value']}°C "
                       f"H={status['sensors']['humidity']['value']}% "
                       f"O={status['sensors']['oxygen']['value']}%")
    
    except KeyboardInterrupt:
        logger.info("⏹️  Backend stopped by user")
    
    finally:
        backend.stop_background_threads()
        if GPIO_AVAILABLE:
            GPIO.cleanup()
        logger.info("✅ Backend cleanup completed")

if __name__ == "__main__":
    main()