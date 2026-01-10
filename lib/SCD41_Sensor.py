#!/usr/bin/env python3
"""
SCD41 CO2, Temperature, and Humidity Sensor Library for Kuvoz
Sensirion SCD41 - Compact CO2 sensor with integrated temperature and humidity
I2C Address: 0x62
"""

import time
import logging

logger = logging.getLogger(__name__)

try:
    import board
    import busio
    import adafruit_scd4x
    SCD41_AVAILABLE = True
except ImportError:
    SCD41_AVAILABLE = False
    logger.warning("SCD41 library not available. Install with: pip3 install adafruit-circuitpython-scd4x")


class SCD41Sensor:
    """
    Sensirion SCD41 CO2, Temperature, and Humidity Sensor
    
    Features:
    - CO2 measurement range: 0-40000 ppm
    - Temperature range: -10 to 60°C
    - Humidity range: 0-100% RH
    - Measurement interval: 5 seconds
    - Lower power consumption than SCD30
    """
    
    def __init__(self, i2c_bus=None):
        """
        Initialize SCD41 sensor
        
        Args:
            i2c_bus: Optional I2C bus object. If None, creates default I2C bus.
        """
        if not SCD41_AVAILABLE:
            raise ImportError("SCD41 libraries not available")
        
        try:
            # Initialize I2C bus if not provided
            if i2c_bus is None:
                self.i2c = busio.I2C(board.SCL, board.SDA)
            else:
                self.i2c = i2c_bus
            
            # Initialize sensor
            self.scd = adafruit_scd4x.SCD4X(self.i2c)
            
            # Get serial number
            serial = self.scd.serial_number
            serial_str = f"0x{serial[0]:02X}{serial[1]:02X}{serial[2]:02X}"
            logger.info(f"SCD41 initialized. Serial: {serial_str}")
            
            # Start periodic measurements
            self.scd.start_periodic_measurement()
            logger.info("SCD41 periodic measurements started")
            
            # Wait for first measurement
            time.sleep(5)
            
            self.initialized = True
            self.failed_read_count = 0
            self.last_read_time = time.time()
            self.measurement_interval = 5  # SCD41 measures every 5 seconds
            
        except Exception as e:
            logger.error(f"Failed to initialize SCD41: {e}")
            self.initialized = False
            raise
    
    def read_co2(self):
        """
        Read CO2 concentration
        
        Returns:
            float: CO2 in ppm, or None if reading failed
        """
        try:
            if not self.initialized:
                return None
            
            # Check if enough time passed since last read (avoid too frequent reads)
            time_since_last_read = time.time() - self.last_read_time
            if time_since_last_read < self.measurement_interval:
                logger.debug(f"SCD41 waiting for measurement interval ({time_since_last_read:.1f}s < {self.measurement_interval}s)")
                return None
            
            # Try to read data - data_ready check can fail in working mode
            try:
                if self.scd.data_ready:
                    co2 = self.scd.CO2
                    self.last_read_time = time.time()
                    self.failed_read_count = 0  # Reset failure counter on success
                    return float(co2)
                else:
                    logger.debug("SCD41 data not ready yet")
                    return None
            except RuntimeError as re:
                # Handle "unavailable while in working mode" error
                if "working mode" in str(re).lower():
                    logger.debug(f"SCD41 in working mode, will retry")
                    self.failed_read_count += 1
                    if self.failed_read_count > 20:  # After 20 failures, try restart
                        logger.warning(f"SCD41 failed {self.failed_read_count} times, attempting restart...")
                        self._restart_sensor()
                    return None
                else:
                    raise
                
        except Exception as e:
            logger.error(f"Failed to read CO2 from SCD41: {e}")
            self.failed_read_count += 1
            return None
    
    def read_temperature(self):
        """
        Read temperature
        
        Returns:
            float: Temperature in °C, or None if reading failed
        """
        try:
            if not self.initialized:
                return None
            
            if self.scd.data_ready:
                temp = self.scd.temperature
                return float(temp)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to read temperature from SCD41: {e}")
            return None
    
    def read_humidity(self):
        """
        Read relative humidity
        
        Returns:
            float: Humidity in %RH, or None if reading failed
        """
        try:
            if not self.initialized:
                return None
            
            if self.scd.data_ready:
                humidity = self.scd.relative_humidity
                return float(humidity)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to read humidity from SCD41: {e}")
            return None
    
    def read_all(self):
        """
        Read all sensor values at once
        
        Returns:
            dict: {'co2': float, 'temperature': float, 'humidity': float}
                  Values are None if reading failed
        """
        try:
            if not self.initialized:
                return {'co2': None, 'temperature': None, 'humidity': None}
            
            # Check if enough time passed since last read
            time_since_last_read = time.time() - self.last_read_time
            if time_since_last_read < self.measurement_interval:
                logger.debug(f"SCD41 waiting for measurement interval ({time_since_last_read:.1f}s)")
                return {'co2': None, 'temperature': None, 'humidity': None}
            
            # Try to read data - data_ready check can fail in working mode
            try:
                if self.scd.data_ready:
                    result = {
                        'co2': float(self.scd.CO2),
                        'temperature': float(self.scd.temperature),
                        'humidity': float(self.scd.relative_humidity)
                    }
                    self.last_read_time = time.time()
                    self.failed_read_count = 0  # Reset failure counter on success
                    return result
                else:
                    logger.debug("SCD41 data not ready")
                    return {'co2': None, 'temperature': None, 'humidity': None}
            except RuntimeError as re:
                # Handle "unavailable while in working mode" error
                if "working mode" in str(re).lower():
                    logger.debug(f"SCD41 in working mode, will retry")
                    self.failed_read_count += 1
                    if self.failed_read_count > 20:  # After 20 failures, try restart
                        logger.warning(f"SCD41 failed {self.failed_read_count} times, attempting restart...")
                        self._restart_sensor()
                    return {'co2': None, 'temperature': None, 'humidity': None}
                else:
                    raise
                
        except Exception as e:
            logger.error(f"Failed to read from SCD41: {e}")
            self.failed_read_count += 1
            return {'co2': None, 'temperature': None, 'humidity': None}
    
    def _restart_sensor(self):
        """
        Internal method to restart the sensor when communication fails
        """
        try:
            logger.info("Restarting SCD41 sensor...")
            
            # Try to stop measurements
            try:
                self.scd.stop_periodic_measurement()
                time.sleep(1)
            except:
                pass  # May fail if sensor is unresponsive
            
            # Wait a bit
            time.sleep(2)
            
            # Restart measurements
            self.scd.start_periodic_measurement()
            time.sleep(5)  # Wait for first measurement
            
            self.failed_read_count = 0
            self.last_read_time = time.time()
            logger.info("✅ SCD41 sensor restarted successfully")
            
        except Exception as e:
            logger.error(f"Failed to restart SCD41 sensor: {e}")
            self.initialized = False
    
    def set_temperature_offset(self, offset):
        """
        Set temperature offset for compensation
        
        Args:
            offset: Temperature offset in °C (typical: 4°C for self-heating)
        """
        try:
            # Must stop measurements before setting offset
            self.scd.stop_periodic_measurement()
            time.sleep(0.5)
            
            self.scd.temperature_offset = offset
            logger.info(f"SCD41 temperature offset set to {offset}°C")
            
            # Restart measurements
            self.scd.start_periodic_measurement()
            time.sleep(5)
            
        except Exception as e:
            logger.error(f"Failed to set temperature offset: {e}")
    
    def set_altitude(self, altitude):
        """
        Set altitude for CO2 compensation
        
        Args:
            altitude: Altitude in meters above sea level
        """
        try:
            # Must stop measurements before setting altitude
            self.scd.stop_periodic_measurement()
            time.sleep(0.5)
            
            self.scd.altitude = int(altitude)
            logger.info(f"SCD41 altitude set to {altitude}m")
            
            # Restart measurements
            self.scd.start_periodic_measurement()
            time.sleep(5)
            
        except Exception as e:
            logger.error(f"Failed to set altitude: {e}")
    
    def perform_forced_calibration(self, target_co2=400):
        """
        Perform forced recalibration to target CO2 value
        
        Args:
            target_co2: Target CO2 concentration in ppm (outdoor: 400-420 ppm)
        
        Returns:
            int: FRC correction value, or None if failed
        """
        try:
            # Must stop measurements before calibration
            self.scd.stop_periodic_measurement()
            time.sleep(0.5)
            
            correction = self.scd.forced_recalibration(target_co2)
            logger.info(f"SCD41 forced calibration performed. Correction: {correction}")
            
            # Restart measurements
            self.scd.start_periodic_measurement()
            time.sleep(5)
            
            return correction
            
        except Exception as e:
            logger.error(f"Failed to perform forced calibration: {e}")
            return None
    
    def close(self):
        """Stop measurements and clean up"""
        try:
            if self.initialized:
                self.scd.stop_periodic_measurement()
                logger.info("SCD41 measurements stopped")
                self.initialized = False
        except Exception as e:
            logger.error(f"Error closing SCD41: {e}")
    
    def __del__(self):
        """Destructor - ensure measurements are stopped"""
        self.close()


# Convenience function for quick testing
def test_sensor():
    """Quick test function"""
    print("Testing SCD41 sensor...")
    
    try:
        sensor = SCD41Sensor()
        print("✓ Sensor initialized")
        
        for i in range(5):
            data = sensor.read_all()
            if data['co2'] is not None:
                print(f"  CO2: {data['co2']:.0f} ppm, Temp: {data['temperature']:.2f}°C, Humidity: {data['humidity']:.1f}%")
            else:
                print("  Waiting for data...")
            time.sleep(5)
        
        sensor.close()
        print("✓ Test complete")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")


if __name__ == "__main__":
    test_sensor()
