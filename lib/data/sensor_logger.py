#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sensor Data Logger - Change-based SQLite logging for Kuvoz Recovery Unit

Logs sensor readings to SQLite database only when values change
beyond configured thresholds, reducing data storage and improving
analysis quality.
"""

import sqlite3
import logging
import os
from contextlib import closing
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple, Any

logger = logging.getLogger(__name__)


class SensorLogger:
    """
    Change-based sensor data logger using SQLite.
    
    Only logs sensor readings when values change beyond configured thresholds,
    reducing unnecessary data storage while preserving important transitions.
    """
    
    # Default thresholds for significant change detection
    DEFAULT_THRESHOLDS = {
        'temperature': 2.0,   # °C - log when temp changes by 2.0°C
        'humidity': 10.0,     # % - log when humidity changes by 10%
        'oxygen': 1.0,        # % - log when oxygen changes by 1.0%
        'co2': 100            # ppm - log when CO2 changes by 100 ppm
    }
    
    # Histeresis bands (tolerans aralıkları) - değişken dönemlerde geniş, stabil dönemlerde dar
    HISTERESIS_BANDS = {
        'temperature': {'unstable': 2.0, 'stable': 1.5},  # °C - 1°C farklar anlamsız
        'humidity': {'unstable': 10.0, 'stable': 5.0},    # %
        'oxygen': {'unstable': 1.0, 'stable': 0.5},       # %
        'co2': {'unstable': 80, 'stable': 40}             # ppm
    }
    
    # Stabilizasyon tespiti için parametreler
    STABILITY_CHECK_PERIOD = 600  # 10 dakika içindeki değişimi kontrol et
    STABILITY_THRESHOLD_MULTIPLIER = 1.5  # Eşik değerinin 1.5 katından az değişim = stabil
    
    def __init__(self, db_path: str = "data/sensor_logs.db", thresholds: Dict[str, float] = None, min_interval: int = 300):
        """
        Initialize the sensor logger.
        
        Args:
            db_path: Path to SQLite database file
            thresholds: Custom thresholds for change detection (optional)
            min_interval: Minimum seconds between log entries (default: 300 = 5 min)
        """
        self.db_path = db_path
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS.copy()
        self.min_interval = min_interval
        self.last_values: Dict[str, float] = {}  # Son loglanan değerler
        self.last_log_time: Optional[datetime] = None
        self.histeresis_centers: Dict[str, float] = {}  # Histeresis band merkezleri
        self.is_stable: Dict[str, bool] = {}  # Her sensör için stabilite durumu
        
        # Ensure data directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        # Initialize database
        self._init_database()
        
        # Auto-cleanup on start (prevent disk fill)
        self._auto_cleanup()
        
        logger.info(f"📊 SensorLogger initialized: {db_path} (min_interval={min_interval}s)")
    
    def _init_database(self):
        """Create database tables if they don't exist."""
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # Main sensor readings table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sensor_readings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        temperature REAL,
                        humidity REAL,
                        oxygen REAL,
                        co2 REAL,
                        change_type TEXT
                    )
                ''')
                
                # Index for faster time-based queries
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_timestamp 
                    ON sensor_readings(timestamp)
                ''')
                
                conn.commit()
                logger.debug("Database tables initialized")
                
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def _auto_cleanup(self):
        """
        Auto-cleanup on startup to prevent disk fill.
        - Removes data older than 30 days
        - Limits database size to ~10MB
        """
        try:
            # Cleanup old data (30 days)
            deleted = self.cleanup_old_data(days=30)
            
            # Check database size and vacuum if too large
            db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            max_size = 10 * 1024 * 1024  # 10MB
            
            if db_size > max_size:
                # Delete older data to reduce size
                logger.warning(f"Database too large ({db_size / 1024 / 1024:.1f}MB), cleaning aggressively...")
                self.cleanup_old_data(days=7)  # Keep only 7 days
                
                # Vacuum to reclaim space
                with closing(sqlite3.connect(self.db_path)) as conn:
                    conn.execute('VACUUM')
                
                new_size = os.path.getsize(self.db_path)
                logger.info(f"Database compacted: {db_size / 1024 / 1024:.1f}MB → {new_size / 1024 / 1024:.1f}MB")
                
        except Exception as e:
            logger.error(f"Auto-cleanup error: {e}")
    
    def _parse_sensor_value(self, sensor_data: Dict, key: str) -> Optional[float]:
        """
        Parse sensor value from the sensor_data dict structure.
        
        Args:
            sensor_data: Dict with structure like {'temperature': {'value': '25.5', 'status': 'OK'}}
            key: Sensor key name
            
        Returns:
            Float value or None if not available/parseable
        """
        if key not in sensor_data:
            return None
        
        value = sensor_data[key]
        
        # Handle dict structure: {'value': '25.5', 'status': 'OK'}
        if isinstance(value, dict):
            raw_value = value.get('value', '--')
        else:
            raw_value = value
        
        # Parse to float
        if raw_value in ('--', None, ''):
            return None
        
        try:
            return float(raw_value)
        except (ValueError, TypeError):
            return None
    
    def _is_sensor_stable(self, sensor_type: str) -> bool:
        """
        Sensörün son 10 dakikada stabil olup olmadığını kontrol et.
        
        Args:
            sensor_type: Sensör tipi
            
        Returns:
            True ise stabil, False ise değişken
        """
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                cutoff_time = (datetime.now() - timedelta(seconds=self.STABILITY_CHECK_PERIOD)).isoformat()
                
                cursor.execute(f'''
                    SELECT MIN({sensor_type}), MAX({sensor_type})
                    FROM sensor_readings
                    WHERE timestamp > ? AND {sensor_type} IS NOT NULL
                ''', (cutoff_time,))
                
                result = cursor.fetchone()
                if result and result[0] is not None and result[1] is not None:
                    min_val, max_val = result
                    variation = abs(max_val - min_val)
                    threshold = self.thresholds.get(sensor_type, 1.0) * self.STABILITY_THRESHOLD_MULTIPLIER
                    return variation < threshold
                    
        except sqlite3.Error:
            pass
        
        # Veri yoksa veya hata varsa varsayılan olarak değişken kabul et
        return False
    
    def _has_significant_change(self, sensor_type: str, new_value: float) -> bool:
        """
        Histeresis mantığı ile anlamlı değişiklik kontrolü.
        
        Değer, son loglanan değer etrafındaki tolerans bandı içindeyse log tutma.
        Band dışına çıkınca yeni log yap.
        
        Args:
            sensor_type: Type of sensor ('temperature', 'humidity', etc.)
            new_value: New sensor reading
            
        Returns:
            True if change exceeds histeresis band, False otherwise
        """
        # İlk okuma - her zaman log
        if sensor_type not in self.histeresis_centers:
            self.histeresis_centers[sensor_type] = new_value
            return True
        
        # Stabilite durumunu kontrol et
        if sensor_type not in self.is_stable:
            self.is_stable[sensor_type] = self._is_sensor_stable(sensor_type)
        
        # Histeresis band genişliğini belirle (stabil/değişken)
        bands = self.HISTERESIS_BANDS.get(sensor_type, {'unstable': 1.0, 'stable': 0.5})
        band_width = bands['stable'] if self.is_stable.get(sensor_type, False) else bands['unstable']
        
        # Band merkezinden sapma kontrolü
        center = self.histeresis_centers[sensor_type]
        deviation = abs(new_value - center)
        
        # Band dışına çıktıysa yeni log + band merkezini güncelle
        if deviation > band_width:
            self.histeresis_centers[sensor_type] = new_value
            # Stabilite durumunu yeniden kontrol et (her 5 logda bir)
            if len(self.last_values) % 5 == 0:
                self.is_stable[sensor_type] = self._is_sensor_stable(sensor_type)
            return True
        
        return False
    
    def log_if_changed(self, sensor_data: Dict) -> bool:
        """
        Log sensor readings if any value has changed significantly AND min_interval has passed.
        
        Args:
            sensor_data: Dict containing sensor readings with structure:
                         {'temperature': {'value': '25.5', 'status': 'OK'}, ...}
        
        Returns:
            True if data was logged, False if skipped (no significant change or too soon)
        """
        # Check minimum interval (debounce)
        if self.last_log_time is not None:
            time_since_last_log = (datetime.now() - self.last_log_time).total_seconds()
            if time_since_last_log < self.min_interval:
                return False
        
        # Parse current values
        current_values = {}
        changed_sensors = []
        
        for sensor_type in ['temperature', 'humidity', 'oxygen', 'co2']:
            value = self._parse_sensor_value(sensor_data, sensor_type)
            if value is not None:
                current_values[sensor_type] = value
                if self._has_significant_change(sensor_type, value):
                    changed_sensors.append(sensor_type)
        
        # No significant changes - skip logging
        if not changed_sensors:
            return False
        
        # Determine change type
        if len(changed_sensors) > 1:
            change_type = 'multiple'
        else:
            change_type = changed_sensors[0]
        
        # Log to database
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO sensor_readings 
                    (timestamp, temperature, humidity, oxygen, co2, change_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    current_values.get('temperature'),
                    current_values.get('humidity'),
                    current_values.get('oxygen'),
                    current_values.get('co2'),
                    change_type
                ))
                conn.commit()
            
            # Update last values
            self.last_values.update(current_values)
            self.last_log_time = datetime.now()
            
            logger.debug(f"📊 Sensor data logged (change: {change_type}): {current_values}")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error logging sensor data: {e}")
            return False
    
    def get_readings(self, 
                     start_time: Optional[datetime] = None, 
                     end_time: Optional[datetime] = None,
                     sensor_type: Optional[str] = None,
                     limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Retrieve sensor readings from database.
        
        Args:
            start_time: Start of time range (default: 24 hours ago)
            end_time: End of time range (default: now)
            sensor_type: Filter by specific sensor type
            limit: Maximum number of records to return
            
        Returns:
            List of reading dicts with timestamp and values
        """
        if start_time is None:
            start_time = datetime.now() - timedelta(hours=24)
        if end_time is None:
            end_time = datetime.now()
        
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = '''
                    SELECT timestamp, temperature, humidity, oxygen, co2, change_type
                    FROM sensor_readings
                    WHERE timestamp BETWEEN ? AND ?
                '''
                params = [start_time.isoformat(), end_time.isoformat()]
                
                if sensor_type:
                    query += ' AND (change_type = ? OR change_type = "multiple")'
                    params.append(sensor_type)
                
                query += f' ORDER BY timestamp DESC LIMIT {limit}'
                
                cursor.execute(query, params)
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error retrieving readings: {e}")
            return []
    
    def get_statistics(self, hours: int = 24) -> Dict[str, Dict[str, float]]:
        """
        Calculate statistics for sensor readings.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Dict with min, max, avg for each sensor type
        """
        start_time = datetime.now() - timedelta(hours=hours)
        
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                
                stats = {}
                for sensor in ['temperature', 'humidity', 'oxygen', 'co2']:
                    cursor.execute(f'''
                        SELECT 
                            MIN({sensor}) as min_val,
                            MAX({sensor}) as max_val,
                            AVG({sensor}) as avg_val,
                            COUNT({sensor}) as count
                        FROM sensor_readings
                        WHERE timestamp > ? AND {sensor} IS NOT NULL
                    ''', (start_time.isoformat(),))
                    
                    row = cursor.fetchone()
                    if row and row[3] > 0:  # count > 0
                        stats[sensor] = {
                            'min': row[0],
                            'max': row[1],
                            'avg': round(row[2], 2) if row[2] else None,
                            'count': row[3]
                        }
                
                return stats
                
        except sqlite3.Error as e:
            logger.error(f"Error calculating statistics: {e}")
            return {}
    
    def cleanup_old_data(self, days: int = 30) -> int:
        """
        Remove data older than specified days.
        
        Args:
            days: Age threshold for deletion
            
        Returns:
            Number of deleted records
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'DELETE FROM sensor_readings WHERE timestamp < ?',
                    (cutoff_time.isoformat(),)
                )
                deleted = cursor.rowcount
                conn.commit()
                
                if deleted > 0:
                    logger.info(f"🧹 Cleaned up {deleted} old sensor readings")
                
                return deleted
                
        except sqlite3.Error as e:
            logger.error(f"Error cleaning old data: {e}")
            return 0
    
    def get_record_count(self) -> int:
        """Get total number of records in database."""
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM sensor_readings')
                return cursor.fetchone()[0]
        except sqlite3.Error:
            return 0

    def clear_all_data(self, reason: str = None, context: Dict[str, Any] = None) -> bool:
        """
        Delete all sensor logs from the database.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM sensor_readings')
                # Optional: Reset autoincrement counter
                cursor.execute('DELETE FROM sqlite_sequence WHERE name="sensor_readings"')
                conn.commit()
                
                details = []
                if reason:
                    details.append(f"reason={reason}")

                if isinstance(context, dict):
                    trigger = str(context.get('trigger') or '').strip()
                    if trigger:
                        details.append(f"trigger={trigger}")

                    previous_patient = context.get('previous_patient') or {}
                    next_patient = context.get('next_patient') or {}
                    previous_name = str(previous_patient.get('name') or '').strip()
                    next_name = str(next_patient.get('name') or '').strip()

                    if previous_name or next_name:
                        details.append(f"patient_change={previous_name or '-'}->{next_name or '-'}")

                detail_text = f" ({', '.join(details)})" if details else ""
                logger.info(f"Sensor data cleared{detail_text}")
                self.last_values = {}
                self.last_log_time = None
                self.histeresis_centers = {}
                self.is_stable = {}
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Error clearing sensor data: {e}")
            return False
