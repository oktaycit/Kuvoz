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
        'temperature': 0.5,   # °C - log when temp changes by 0.5°C
        'humidity': 4.0,      # % - log when humidity changes by 4%
        'oxygen': 0.5,        # % - log when oxygen changes by 0.5%
        'co2': 50             # ppm - log when CO2 changes by 50 ppm
    }
    
    def __init__(self, db_path: str = "data/sensor_logs.db", thresholds: Dict[str, float] = None, min_interval: int = 60):
        """
        Initialize the sensor logger.
        
        Args:
            db_path: Path to SQLite database file
            thresholds: Custom thresholds for change detection (optional)
            min_interval: Minimum seconds between log entries (default: 60)
        """
        self.db_path = db_path
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS.copy()
        self.min_interval = min_interval
        self.last_values: Dict[str, float] = {}
        self.last_log_time: Optional[datetime] = None
        
        # Ensure data directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        # Initialize database
        self._init_database()
        logger.info(f"📊 SensorLogger initialized: {db_path} (min_interval={min_interval}s)")
    
    def _init_database(self):
        """Create database tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
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
    
    def _has_significant_change(self, sensor_type: str, new_value: float) -> bool:
        """
        Check if the new value represents a significant change from last logged value.
        
        Args:
            sensor_type: Type of sensor ('temperature', 'humidity', etc.)
            new_value: New sensor reading
            
        Returns:
            True if change exceeds threshold, False otherwise
        """
        if sensor_type not in self.last_values:
            # First reading for this sensor - always log
            return True
        
        last_value = self.last_values[sensor_type]
        threshold = self.thresholds.get(sensor_type, 1.0)
        
        change = abs(new_value - last_value)
        return change >= threshold
    
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
            with sqlite3.connect(self.db_path) as conn:
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
            with sqlite3.connect(self.db_path) as conn:
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
            with sqlite3.connect(self.db_path) as conn:
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
            with sqlite3.connect(self.db_path) as conn:
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
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM sensor_readings')
                return cursor.fetchone()[0]
        except sqlite3.Error:
            return 0
