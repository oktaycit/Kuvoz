#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Behavior Logger - Hayvan yaşam döngüsü davranışlarını SQLite ile kaydeder.

Yeme-içme, dinlenme, boşaltım gibi davranışları izler ve veterinerya özelinde
analiz edilebilecek şekilde veri tabanına kaydeder.
"""

import logging
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BehaviorLogger:
    """Hayvan davranışlarını kaydeder ve analiz eder."""

    # Davranış türleri
    BEHAVIOR_TYPES = {
        'feeding': 'Yeme',
        'drinking': 'İçme',
        'resting': 'Dinlenme',
        'elimination': 'Boşaltım',
        'activity': 'Aktivite',
        'sleep': 'Uyku',
        'play': 'Oyun',
        'grooming': 'Tımar',
        'social': 'Sosyal'
    }

    # Veri saklama süresi (gün)
    RETENTION_DAYS = 90
    MAX_DB_SIZE_BYTES = 20 * 1024 * 1024  # 20MB

    def __init__(
        self,
        db_path: str = "data/behavior_logs.db",
        min_interval: int = 60,  # Minimum kayıt aralığı (saniye)
    ):
        self.db_path = db_path
        self.min_interval = max(1, int(min_interval))
        self.last_behavior_times: Dict[str, datetime] = {}
        
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

        self._init_database()
        self._auto_cleanup()

        logger.info(
            "BehaviorLogger initialized: %s (min_interval=%ss)",
            db_path,
            self.min_interval,
        )

    def _init_database(self) -> None:
        """Veritabanı şemasını oluşturur."""
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # Davranış kayıtları tablosu
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS behavior_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME NOT NULL,
                        patient_id TEXT,
                        patient_name TEXT,
                        patient_species TEXT,
                        behavior_type TEXT NOT NULL,
                        behavior_subtype TEXT,
                        duration INTEGER,  -- saniye cinsinden
                        intensity REAL,    -- 0-10 skalasında yoğunluk
                        notes TEXT,
                        metadata TEXT      -- JSON formatında ekstra veri
                    )
                    """
                )
                
                # İndeksler
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_behavior_timestamp
                    ON behavior_logs(timestamp)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_behavior_patient
                    ON behavior_logs(patient_id, timestamp)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_behavior_type
                    ON behavior_logs(behavior_type, timestamp)
                    """
                )
                
                conn.commit()
        except sqlite3.Error as e:
            logger.error("Behavior DB initialization error: %s", e)
            raise

    def _auto_cleanup(self) -> None:
        """Otomatik veri temizliği yapar."""
        try:
            self.cleanup_old_data(days=self.RETENTION_DAYS)
            db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            if db_size <= self.MAX_DB_SIZE_BYTES:
                return

            logger.warning(
                "Behavior DB grew to %.1f MB, compacting",
                db_size / 1024.0 / 1024.0,
            )
            self.cleanup_old_data(days=30)
            with closing(sqlite3.connect(self.db_path)) as conn:
                conn.execute("VACUUM")
        except Exception as e:
            logger.error("Behavior auto-cleanup error: %s", e)

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        try:
            if value in (None, "", "--"):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_int(value: Any) -> Optional[int]:
        try:
            if value in (None, "", "--"):
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _clean_text(value: Any) -> str:
        return str(value or "").strip()

    def log_behavior(
        self,
        behavior_type: str,
        patient_context: Optional[Dict[str, Any]] = None,
        duration: Optional[int] = None,
        intensity: Optional[float] = None,
        notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        behavior_subtype: Optional[str] = None,
    ) -> bool:
        """
        Davranış kaydı ekler.
        
        Args:
            behavior_type: Davranış türü (feeding, drinking, resting, elimination)
            patient_context: Hasta bilgileri
            duration: Süre (saniye)
            intensity: Yoğunluk (0-10)
            notes: Notlar
            metadata: Ekstra veri (JSON)
            behavior_subtype: Alt tür (örn: wet food, dry food)
        """
        if behavior_type not in self.BEHAVIOR_TYPES:
            logger.warning("Invalid behavior type: %s", behavior_type)
            return False

        now = datetime.now()
        
        # Minimum aralık kontrolü
        last_time = self.last_behavior_times.get(behavior_type)
        if last_time:
            elapsed = (now - last_time).total_seconds()
            if elapsed < self.min_interval:
                logger.debug(
                    "Behavior log skipped: too soon (elapsed=%.0fs, need %ds)",
                    elapsed, self.min_interval
                )
                return False

        patient = patient_context if isinstance(patient_context, dict) else {}
        
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO behavior_logs (
                        timestamp,
                        patient_id,
                        patient_name,
                        patient_species,
                        behavior_type,
                        behavior_subtype,
                        duration,
                        intensity,
                        notes,
                        metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        now.isoformat(),
                        self._clean_text(patient.get("id")),
                        self._clean_text(patient.get("name")),
                        self._clean_text(patient.get("species")),
                        behavior_type,
                        behavior_subtype,
                        duration,
                        intensity,
                        notes,
                        str(metadata) if metadata else None,
                    ),
                )
                conn.commit()

            self.last_behavior_times[behavior_type] = now
            
            logger.info(
                "🐾 Behavior logged: %s - %s (duration=%s, intensity=%s)",
                patient.get("name") or patient.get("id") or "-",
                behavior_type,
                duration,
                intensity
            )
            return True
        except sqlite3.Error as e:
            logger.error("Error logging behavior: %s", e)
            return False

    def get_latest_behavior(
        self, 
        behavior_type: Optional[str] = None, 
        patient_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Son davranış kaydını getirir."""
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                query = """
                    SELECT timestamp, patient_id, patient_name, patient_species,
                           behavior_type, behavior_subtype, duration, intensity,
                           notes, metadata
                    FROM behavior_logs
                """
                params: List[Any] = []
                
                conditions = []
                if patient_id:
                    conditions.append("patient_id = ?")
                    params.append(patient_id)
                if behavior_type:
                    conditions.append("behavior_type = ?")
                    params.append(behavior_type)
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                query += " ORDER BY timestamp DESC LIMIT 1"
                cursor.execute(query, params)
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error("Error retrieving latest behavior: %s", e)
            return None

    def get_behaviors(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        patient_id: Optional[str] = None,
        behavior_types: Optional[List[str]] = None,
        limit: int = 1000,
        order: str = "DESC",
    ) -> List[Dict[str, Any]]:
        """Belirli bir zaman aralığındaki davranış kayıtlarını getirir."""
        if start_time is None:
            start_time = datetime.now() - timedelta(hours=24)
        if end_time is None:
            end_time = datetime.now()

        order_sql = "ASC" if str(order).upper() == "ASC" else "DESC"

        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                query = """
                    SELECT timestamp, patient_id, patient_name, patient_species,
                           behavior_type, behavior_subtype, duration, intensity,
                           notes, metadata
                    FROM behavior_logs
                    WHERE timestamp BETWEEN ? AND ?
                """
                params: List[Any] = [start_time.isoformat(), end_time.isoformat()]

                if patient_id:
                    query += " AND patient_id = ?"
                    params.append(patient_id)

                if behavior_types:
                    normalized_types = [str(item).strip() for item in behavior_types if str(item).strip()]
                    if normalized_types:
                        placeholders = ",".join("?" for _ in normalized_types)
                        query += f" AND behavior_type IN ({placeholders})"
                        params.extend(normalized_types)

                query += f" ORDER BY timestamp {order_sql} LIMIT ?"
                params.append(max(1, int(limit)))

                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error("Error retrieving behavior logs: %s", e)
            return []

    def get_behavior_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        patient_id: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Davranış istatistiklerini getirir."""
        if start_time is None:
            start_time = datetime.now() - timedelta(hours=24)
        if end_time is None:
            end_time = datetime.now()

        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Toplam sayaçlar
                query = """
                    SELECT behavior_type, COUNT(*) as count
                    FROM behavior_logs
                    WHERE timestamp BETWEEN ? AND ?
                """
                params: List[Any] = [start_time.isoformat(), end_time.isoformat()]
                if patient_id:
                    query += " AND patient_id = ?"
                    params.append(patient_id)
                
                query += " GROUP BY behavior_type"
                cursor.execute(query, params)
                
                for row in cursor.fetchall():
                    behavior_type = row[0]
                    count = row[1]
                    stats[behavior_type] = {
                        'count': count,
                        'total_duration': 0,
                        'avg_duration': 0,
                        'total_intensity': 0,
                        'avg_intensity': 0
                    }
                
                # Süre ve yoğunluk istatistikleri
                for behavior_type in stats.keys():
                    query = """
                        SELECT SUM(duration), AVG(duration), SUM(intensity), AVG(intensity)
                        FROM behavior_logs
                        WHERE timestamp BETWEEN ? AND ? AND behavior_type = ?
                    """
                    params = [start_time.isoformat(), end_time.isoformat(), behavior_type]
                    if patient_id:
                        query += " AND patient_id = ?"
                        params.append(patient_id)
                    
                    cursor.execute(query, params)
                    row = cursor.fetchone()
                    
                    if row and row[0] is not None:
                        stats[behavior_type].update({
                            'total_duration': row[0] or 0,
                            'avg_duration': round(row[1] or 0, 2),
                            'total_intensity': row[2] or 0,
                            'avg_intensity': round(row[3] or 0, 2)
                        })
                
                return stats
        except sqlite3.Error as e:
            logger.error("Error calculating behavior statistics: %s", e)
            return {}

    def get_behavior_summary(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        patient_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Davranış özetini getirir."""
        if start_time is None:
            start_time = datetime.now() - timedelta(hours=24)
        if end_time is None:
            end_time = datetime.now()

        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # Genel sayaçlar
                query = """
                    SELECT COUNT(*) as total_behaviors,
                           SUM(CASE WHEN duration IS NOT NULL THEN duration ELSE 0 END) as total_duration
                    FROM behavior_logs
                    WHERE timestamp BETWEEN ? AND ?
                """
                params: List[Any] = [start_time.isoformat(), end_time.isoformat()]
                if patient_id:
                    query += " AND patient_id = ?"
                    params.append(patient_id)
                
                cursor.execute(query, params)
                row = cursor.fetchone()
                
                if not row:
                    return {
                        'total_behaviors': 0,
                        'total_duration': 0,
                        'behavior_counts': {},
                        'daily_patterns': {}
                    }
                
                total_behaviors = row[0] or 0
                total_duration = row[1] or 0
                
                # Davranış türüne göre sayaçlar
                query = """
                    SELECT behavior_type, COUNT(*) as count
                    FROM behavior_logs
                    WHERE timestamp BETWEEN ? AND ?
                """
                params = [start_time.isoformat(), end_time.isoformat()]
                if patient_id:
                    query += " AND patient_id = ?"
                    params.append(patient_id)
                
                query += " GROUP BY behavior_type ORDER BY count DESC"
                cursor.execute(query, params)
                
                behavior_counts = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Günlük desenler (saatlik)
                query = """
                    SELECT strftime('%H', timestamp) as hour, behavior_type, COUNT(*) as count
                    FROM behavior_logs
                    WHERE timestamp BETWEEN ? AND ?
                """
                params = [start_time.isoformat(), end_time.isoformat()]
                if patient_id:
                    query += " AND patient_id = ?"
                    params.append(patient_id)
                
                query += " GROUP BY hour, behavior_type ORDER BY hour, count DESC"
                cursor.execute(query, params)
                
                daily_patterns = {}
                for row in cursor.fetchall():
                    hour = row[0]
                    behavior_type = row[1]
                    count = row[2]
                    
                    if hour not in daily_patterns:
                        daily_patterns[hour] = {}
                    daily_patterns[hour][behavior_type] = count
                
                return {
                    'total_behaviors': total_behaviors,
                    'total_duration': total_duration,
                    'behavior_counts': behavior_counts,
                    'daily_patterns': daily_patterns
                }
        except sqlite3.Error as e:
            logger.error("Error calculating behavior summary: %s", e)
            return {}

    def get_patient_summaries(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Hasta bazlı davranış özetlerini getirir."""
        if start_time is None:
            start_time = datetime.now() - timedelta(days=self.RETENTION_DAYS)
        if end_time is None:
            end_time = datetime.now()

        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT patient_id, patient_name, patient_species,
                           COUNT(*) AS behavior_count,
                           SUM(COALESCE(duration, 0)) AS total_duration,
                           MAX(timestamp) AS last_behavior_time
                    FROM behavior_logs
                    WHERE timestamp BETWEEN ? AND ?
                    GROUP BY patient_id, patient_name, patient_species
                    ORDER BY last_behavior_time DESC
                    LIMIT ?
                    """,
                    (start_time.isoformat(), end_time.isoformat(), max(1, int(limit))),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error("Error retrieving behavior patient summaries: %s", e)
            return []

    def get_record_count(self, patient_id: Optional[str] = None) -> int:
        """Toplam kayıt sayısını getirir."""
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                query = "SELECT COUNT(*) FROM behavior_logs"
                params: List[Any] = []
                if patient_id:
                    query += " WHERE patient_id = ?"
                    params.append(patient_id)
                cursor.execute(query, params)
                row = cursor.fetchone()
                return int(row[0]) if row else 0
        except sqlite3.Error:
            return 0

    def clear_all_data(self, reason: str = None, context: Optional[Dict[str, Any]] = None) -> bool:
        """Tüm davranış verilerini siler."""
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM behavior_logs")
                cursor.execute('DELETE FROM sqlite_sequence WHERE name="behavior_logs"')
                conn.commit()

            details = []
            if reason:
                details.append(f"reason={reason}")

            detail_text = f" ({', '.join(details)})" if details else ""
            logger.info(f"Behavior data cleared{detail_text}")
            return True
        except sqlite3.Error as e:
            logger.error("Error clearing behavior logs: %s", e)
            return False

    def cleanup_old_data(self, days: int = 30) -> int:
        """Eski verileri temizler."""
        cutoff_time = datetime.now() - timedelta(days=max(1, int(days)))

        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM behavior_logs WHERE timestamp < ?",
                    (cutoff_time.isoformat(),),
                )
                deleted = cursor.rowcount
                conn.commit()
                if deleted > 0:
                    logger.info("Cleaned %s old behavior logs", deleted)
                return deleted
        except sqlite3.Error as e:
            logger.error("Error cleaning old behavior logs: %s", e)
            return 0

    def start_logging(self):
        """Loglamayı başlatır."""
        logger.info("Behavior logging started")
        
    def stop_logging(self):
        """Loglamayı durdurur."""
        logger.info("Behavior logging stopped")