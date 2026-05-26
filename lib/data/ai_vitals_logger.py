#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Vital Signs Logger - SQLite persistence for AI-derived vital snapshots.

Stores the AI module's respiration/confidence/status timeline in a compact,
change-aware format so it can later be visualized on a dedicated history page.
"""

import logging
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AIVitalsLogger:
    """Persist AI vital measurements with aggressive change detection.
    
    AGRESİF FİLTRELEME: Sadece ÖNEMLİ değişiklikleri kaydet.
    - Çok sık kayıt yapma
    - Düşük kaliteli durumları sınırlı kaydet
    - Stabil durumlarda minimum kayıt
    """

    # AGRESİF THRESHOLDLAR - Sadece önemli değişiklikleri kaydet
    BPM_DELTA = 5.0  # Solunum EN AZ 5 BPM değişmeli (önceki: 3.0)
    CONFIDENCE_DELTA = 0.20  # Confidence EN AZ %20 değişmeli (önceki: 0.10)
    ACTIVITY_DELTA = 0.35  # Activity EN AZ %35 değişmeli (daha agresif)
    RELIABLE_CONFIDENCE_MIN = 0.60  # Güvenilir kayıt için minimum confidence
    STABLE_OK_MIN_INTERVAL = 180  # Stabil OK durumunda 3 dakikada bir (daha agresif)
    UNSTABLE_MAX_RECORDS = 5  # Arka arkaya max 5 unstable kayıt (sonra skip)
    MOTION_EVENT_THRESHOLD = 0.50  # Hareket olayı olarak kaydetmek için minimum activity
    
    LOW_SIGNAL_STATUSES = {"LOW_CONF", "NOT_ENOUGH_DATA", "UNAVAILABLE"}
    MOTION_STATUSES = {"TOO_MUCH_MOTION"}
    UNSTABLE_STATUSES = LOW_SIGNAL_STATUSES | MOTION_STATUSES
    RETENTION_DAYS = 30
    MAX_DB_SIZE_BYTES = 10 * 1024 * 1024
    MAINTENANCE_INTERVAL = timedelta(hours=6)

    def __init__(
        self,
        db_path: str = "data/ai_vitals.db",
        min_interval: int = 30,  # AGRESİF: Minimum 30 saniye (önceki: 10s)
        heartbeat_interval: Optional[int] = 180,  # AGRESİF: 3 dakikada bir heartbeat (önceki: 60s)
    ):
        self.db_path = db_path
        self.min_interval = max(1, int(min_interval))
        if heartbeat_interval in (None, "", 0, "0", False):
            self.heartbeat_interval = 180  # Default 180s (agresif)
        else:
            self.heartbeat_interval = max(self.min_interval, int(heartbeat_interval))
        self.significant_interval = self.min_interval
        self._unstable_record_count = 0  # Arka arkaya unstable kayıt sayacı
        self.last_snapshot: Optional[Dict[str, Any]] = None
        self.last_log_time: Optional[datetime] = None
        self._last_maintenance_at: Optional[datetime] = None

        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

        self._init_database()
        self._auto_cleanup()
        self._last_maintenance_at = datetime.now()
        self._restore_runtime_state()

        logger.info(
            "AIVitalsLogger initialized: %s (min_interval=%ss, heartbeat=%s)",
            db_path,
            self.min_interval,
            f"{self.heartbeat_interval}s" if self.heartbeat_interval is not None else "disabled",
        )

    def _init_database(self) -> None:
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ai_vital_readings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME NOT NULL,
                        patient_id TEXT,
                        patient_name TEXT,
                        patient_species TEXT,
                        respiration_bpm REAL,
                        confidence REAL,
                        status TEXT,
                        method TEXT,
                        activity_level REAL,
                        vision_status TEXT,
                        peaks INTEGER,
                        window_seconds REAL
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_ai_vitals_timestamp
                    ON ai_vital_readings(timestamp)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_ai_vitals_patient
                    ON ai_vital_readings(patient_id, timestamp)
                    """
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error("AI vital DB initialization error: %s", e)
            raise

    def _auto_cleanup(self) -> None:
        try:
            self.cleanup_old_data(days=self.RETENTION_DAYS)
            db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            if db_size <= self.MAX_DB_SIZE_BYTES:
                return

            logger.warning(
                "AI vital DB grew to %.1f MB, compacting",
                db_size / 1024.0 / 1024.0,
            )
            self.cleanup_old_data(days=7)
            with closing(sqlite3.connect(self.db_path)) as conn:
                conn.execute("VACUUM")
        except Exception as e:
            logger.error("AI vital auto-cleanup error: %s", e)

    def maybe_run_maintenance(
        self,
        *,
        now: Optional[datetime] = None,
        force: bool = False,
    ) -> bool:
        """Run periodic retention/compaction checks while the service stays up."""
        current_time = now or datetime.now()
        if not force and self._last_maintenance_at is not None:
            elapsed = current_time - self._last_maintenance_at
            if elapsed < self.MAINTENANCE_INTERVAL:
                return False

        self._last_maintenance_at = current_time
        logger.debug("Running periodic AI vital maintenance")
        self._auto_cleanup()
        return True

    def _restore_runtime_state(self) -> None:
        latest = self.get_latest_reading()
        if not latest:
            return

        self.last_snapshot = latest
        timestamp = latest.get("timestamp")
        if timestamp:
            try:
                self.last_log_time = datetime.fromisoformat(str(timestamp))
            except ValueError:
                self.last_log_time = None

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

    def _clean_status(self, value: Any) -> str:
        return self._clean_text(value).upper()

    def _extract_snapshot(
        self,
        ai_data: Dict[str, Any],
        patient_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(ai_data, dict):
            return None

        vitals = ai_data.get("vitals") if isinstance(ai_data.get("vitals"), dict) else {}
        vision = ai_data.get("vision") if isinstance(ai_data.get("vision"), dict) else {}
        patient = patient_context if isinstance(patient_context, dict) else {}

        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "patient_id": self._clean_text(patient.get("id")),
            "patient_name": self._clean_text(patient.get("name")),
            "patient_species": self._clean_text(patient.get("species")),
            "respiration_bpm": self._to_float(vitals.get("respiration_bpm")),
            "confidence": self._to_float(vitals.get("confidence")),
            "status": self._clean_text(vitals.get("status")),
            "method": self._clean_text(vitals.get("method")),
            "activity_level": self._to_float(vision.get("activity")),
            "vision_status": self._clean_text(vision.get("status")),
            "peaks": self._to_int(vitals.get("peaks")),
            "window_seconds": self._to_float(vitals.get("window_seconds")),
        }

        has_content = any(
            snapshot.get(key) not in (None, "")
            for key in (
                "respiration_bpm",
                "confidence",
                "status",
                "activity_level",
                "vision_status",
            )
        )
        return snapshot if has_content else None

    @staticmethod
    def _numeric_changed(
        previous: Optional[float],
        current: Optional[float],
        threshold: float,
    ) -> bool:
        if previous is None and current is None:
            return False
        if previous is None or current is None:
            return True
        return abs(current - previous) >= threshold

    @staticmethod
    def _text_changed(previous: Any, current: Any) -> bool:
        return str(previous or "").strip() != str(current or "").strip()

    def _is_unstable_snapshot(self, snapshot: Optional[Dict[str, Any]]) -> bool:
        """Group unreliable AI states into a single degraded episode."""
        if not snapshot:
            return False
        return self._clean_status(snapshot.get("status")) in self.UNSTABLE_STATUSES

    def _is_low_quality_ok_snapshot(self, snapshot: Optional[Dict[str, Any]]) -> bool:
        if not snapshot:
            return False

        status = self._clean_status(snapshot.get("status"))
        confidence = self._to_float(snapshot.get("confidence"))
        return (
            status == "OK"
            and (confidence is None or confidence < self.RELIABLE_CONFIDENCE_MIN)
        )

    def _is_meaningful_snapshot(self, snapshot: Optional[Dict[str, Any]]) -> bool:
        if not snapshot:
            return False
        return not self._is_low_quality_ok_snapshot(snapshot)

    def _is_reliable_ok_snapshot(self, snapshot: Optional[Dict[str, Any]]) -> bool:
        if not snapshot:
            return False

        status = self._clean_status(snapshot.get("status"))
        respiration = self._to_float(snapshot.get("respiration_bpm"))
        confidence = self._to_float(snapshot.get("confidence"))
        return (
            status == "OK"
            and respiration is not None
            and confidence is not None
            and confidence >= self.RELIABLE_CONFIDENCE_MIN
        )

    def _heartbeat_due(self, elapsed: Optional[float]) -> bool:
        return (
            self.heartbeat_interval is not None
            and elapsed is not None
            and elapsed >= self.heartbeat_interval
        )

    def _has_significant_change(
        self,
        previous: Optional[Dict[str, Any]],
        current: Dict[str, Any],
    ) -> bool:
        """
        AGRESİF değişiklik tespiti - Sadece ÇOK ÖNEMLİ değişiklikleri kaydet.
        
        Kayıt senaryoları (en önemliden en aze):
        1. Hasta değişti → KAYDET
        2. Unstable → Stable geçiş → KAYDET (iyileşme)
        3. Stable → Unstable geçiş → KAYDET (kötüleşme)
        4. OK durumunda büyük BPM/confidence değişikliği → KAYDET
        5. Unstable episode içindeki alt durum değişimleri → SKIP
        
        Kaydetmeme senaryoları:
        - Aynı unstable durum (örn: sürekli LOW_CONF) → SKIP
        - OK durumunda küçük değişiklikler → SKIP
        - Activity'de küçük değişiklikler → SKIP
        """
        if not previous:
            return True  # İlk kayıt her zaman kaydet

        if self._text_changed(previous.get("patient_id"), current.get("patient_id")):
            return True  # Hasta değişti

        previous_status = self._clean_status(previous.get("status"))
        current_status = self._clean_status(current.get("status"))
        previous_unstable = self._is_unstable_snapshot(previous)
        current_unstable = self._is_unstable_snapshot(current)

        previous_ok = self._is_reliable_ok_snapshot(previous)
        current_ok = self._is_reliable_ok_snapshot(current)

        # UNSTABLE durumlarını tek bozulmuş episode olarak grupla.
        if previous_unstable and current_unstable:
            return False

        if previous_unstable != current_unstable:
            # Unstable <-> Stable geçişi - mutlaka kaydet
            return True

        if previous_status != current_status:
            # Durum değişti - kaydet (OK'a geçişleri de dahil)
            return True

        # Her ikisi de OK ve reliable - SADECE BÜYÜK değişiklikleri kaydet
        if previous_ok and current_ok:
            bpm_changed = self._numeric_changed(
                previous.get("respiration_bpm"),
                current.get("respiration_bpm"),
                self.BPM_DELTA,  # 5.0 BPM (agresif)
            )
            conf_changed = self._numeric_changed(
                previous.get("confidence"),
                current.get("confidence"),
                self.CONFIDENCE_DELTA,  # 0.20 (agresif)
            )
            return bpm_changed or conf_changed

        # Stabil ama low-quality durumlar - SADECE BÜYÜK activity değişikliği
        prev_activity = self._to_float(previous.get("activity_level"))
        curr_activity = self._to_float(current.get("activity_level"))
        if prev_activity is not None and curr_activity is not None:
            activity_delta = abs(curr_activity - prev_activity)
            if activity_delta >= self.ACTIVITY_DELTA:  # 0.30 (agresif - %30 değişim)
                return True

        return False

    def log_if_changed(
        self,
        ai_data: Dict[str, Any],
        patient_context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        AGRESİF AI vital kaydı - Sadece ÇOK ÖNEMLİ değişiklikleri kaydet.
        
        AGRESİF FİLTRELEME kuralları:
        1. İlk kayıt her zaman kaydedilir
        2. Hasta değiştiğinde kaydedilir
        3. Unstable → Stable geçişte kaydedilir (iyileşme)
        4. Stable → Unstable geçişte kaydedilir (kötüleşme)
        5. OK durumunda BÜYÜK değişiklik (≥5 BPM veya ≥%20 confidence)
        6. Heartbeat dolduğunda kararlı/kararsız durumlarda zaman çizgisi kaydı
        
        ASLA kaydetme:
        - Heartbeat dolmadan aynı unstable durumu arka arkaya (örn: sürekli LOW_CONF)
        - OK durumunda küçük değişiklikler
        - min_interval geçmeden tekrar kayıt
        """
        snapshot = self._extract_snapshot(ai_data, patient_context=patient_context)
        
        # ANLAMSIZ snapshot'ları tamamen reddet
        if not self._is_meaningful_snapshot(snapshot):
            logger.debug("🚫 AI vital skip: meaningless (status=%s, conf=%s)", 
                        snapshot.get('status') if snapshot else 'None',
                        snapshot.get('confidence') if snapshot else 'None')
            return False

        now = datetime.now()
        elapsed = (now - self.last_log_time).total_seconds() if self.last_log_time else None
        
        current_status = self._clean_status(snapshot.get("status"))
        current_unstable = self._is_unstable_snapshot(snapshot)
        current_ok = self._is_reliable_ok_snapshot(snapshot)
        previous_unstable = self._is_unstable_snapshot(self.last_snapshot)
        
        # AGRESİF KURAL 1: Aynı unstable durumu arka arkaya kaydetme.
        # Heartbeat dolduysa yine kayıt bırak; aksi halde uzun süren
        # NOT_ENOUGH_DATA/LOW_CONF dönemleri grafikte veri yok gibi görünür.
        if current_unstable and previous_unstable:
            previous_status = self._clean_status(self.last_snapshot.get("status")) if self.last_snapshot else None
            if current_status == previous_status and not self._heartbeat_due(elapsed):
                # Aynı unstable durum - arka arkaya kaydetme
                logger.debug("🚫 AI vital skip: same unstable status '%s'", current_status)
                return False
        
        # AGRESİF KURAL 2: Stabil OK durumunda minimum interval'ı uzat
        significant_change = self._has_significant_change(self.last_snapshot, snapshot)
        significant_interval = self.significant_interval
        
        if current_ok and self._is_reliable_ok_snapshot(self.last_snapshot):
            # Stabil OK - çok daha uzun interval kullan (2 dakika)
            significant_interval = self.STABLE_OK_MIN_INTERVAL
            if not significant_change:
                # OK durumunda değişiklik yoksa heartbeat'i bekle
                if elapsed is not None and elapsed < self.heartbeat_interval:
                    logger.debug("🚫 AI vital skip: stable OK, no change (elapsed=%.0fs, need %ds)",
                                elapsed or 0, significant_interval)
                    return False
        
        # AGRESİF KURAL 3: Unstable durumda min_interval dolmadan kayıt yazma.
        # Heartbeat kararı aşağıdaki merkezi blokta verilir.
        if current_unstable and elapsed is not None and elapsed < self.min_interval:
            if not significant_change:
                logger.debug("🚫 AI vital skip: unstable, too soon (elapsed=%.0fs, need %ds)",
                            elapsed or 0, self.min_interval)
                return False
        
        # Kayıt kararı ver
        should_log = False
        log_reason = ""
        
        if self.last_snapshot is None or self.last_log_time is None:
            should_log = True
            log_reason = "initial"
        elif significant_change and elapsed >= significant_interval:
            should_log = True
            log_reason = f"change_detected ({elapsed:.0f}s >= {significant_interval}s)"
        elif self._heartbeat_due(elapsed):
            should_log = True
            if current_unstable:
                log_reason = f"unstable_heartbeat ({elapsed:.0f}s >= {self.heartbeat_interval}s)"
            else:
                log_reason = f"heartbeat ({elapsed:.0f}s >= {self.heartbeat_interval}s)"
        
        if not should_log:
            logger.debug(
                "🚫 AI vital skip: no significant change (elapsed=%.0fs, interval=%ds, change=%s, status=%s)",
                elapsed or 0,
                significant_interval,
                significant_change,
                current_status,
            )
            return False

        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO ai_vital_readings (
                        timestamp,
                        patient_id,
                        patient_name,
                        patient_species,
                        respiration_bpm,
                        confidence,
                        status,
                        method,
                        activity_level,
                        vision_status,
                        peaks,
                        window_seconds
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot["timestamp"],
                        snapshot["patient_id"] or None,
                        snapshot["patient_name"] or None,
                        snapshot["patient_species"] or None,
                        snapshot["respiration_bpm"],
                        snapshot["confidence"],
                        snapshot["status"] or None,
                        snapshot["method"] or None,
                        snapshot["activity_level"],
                        snapshot["vision_status"] or None,
                        snapshot["peaks"],
                        snapshot["window_seconds"],
                    ),
                )
                conn.commit()

            self.last_snapshot = snapshot
            self.last_log_time = now
            
            # Başarılı kaydı logla
            logger.info(
                "📝 AI vital logged [%s]: %s - status=%s, bpm=%.1f, conf=%.2f, activity=%.2f",
                log_reason,
                snapshot["patient_name"] or snapshot["patient_id"] or "-",
                snapshot["status"] or "-",
                snapshot["respiration_bpm"] or 0,
                snapshot["confidence"] or 0,
                snapshot["activity_level"] or 0
            )
            return True
        except sqlite3.Error as e:
            logger.error("Error logging AI vital snapshot: %s", e)
            return False

    def get_latest_reading(self, patient_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                query = """
                    SELECT timestamp, patient_id, patient_name, patient_species,
                           respiration_bpm, confidence, status, method,
                           activity_level, vision_status, peaks, window_seconds
                    FROM ai_vital_readings
                """
                params: List[Any] = []
                if patient_id:
                    query += " WHERE patient_id = ?"
                    params.append(patient_id)
                query += " ORDER BY timestamp DESC LIMIT 1"
                cursor.execute(query, params)
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error("Error retrieving latest AI vital reading: %s", e)
            return None

    def get_readings(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        patient_id: Optional[str] = None,
        statuses: Optional[List[str]] = None,
        limit: int = 1000,
        order: str = "DESC",
    ) -> List[Dict[str, Any]]:
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
                           respiration_bpm, confidence, status, method,
                           activity_level, vision_status, peaks, window_seconds
                    FROM ai_vital_readings
                    WHERE timestamp BETWEEN ? AND ?
                """
                params: List[Any] = [start_time.isoformat(), end_time.isoformat()]

                if patient_id:
                    query += " AND patient_id = ?"
                    params.append(patient_id)

                normalized_statuses = [str(item).strip() for item in (statuses or []) if str(item).strip()]
                if normalized_statuses:
                    placeholders = ",".join("?" for _ in normalized_statuses)
                    query += f" AND status IN ({placeholders})"
                    params.extend(normalized_statuses)

                query += f" ORDER BY timestamp {order_sql} LIMIT ?"
                params.append(max(1, int(limit)))

                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error("Error retrieving AI vital readings: %s", e)
            return []

    def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        patient_id: Optional[str] = None,
    ) -> Dict[str, Dict[str, Optional[float]]]:
        if start_time is None:
            start_time = datetime.now() - timedelta(hours=24)
        if end_time is None:
            end_time = datetime.now()

        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                stats: Dict[str, Dict[str, Optional[float]]] = {}
                for field in ("respiration_bpm", "confidence", "activity_level"):
                    query = f"""
                        SELECT MIN({field}), MAX({field}), AVG({field}), COUNT({field})
                        FROM ai_vital_readings
                        WHERE timestamp BETWEEN ? AND ? AND {field} IS NOT NULL
                    """
                    params: List[Any] = [start_time.isoformat(), end_time.isoformat()]
                    if patient_id:
                        query += " AND patient_id = ?"
                        params.append(patient_id)

                    cursor.execute(query, params)
                    row = cursor.fetchone()
                    if row and row[3]:
                        stats[field] = {
                            "min": row[0],
                            "max": row[1],
                            "avg": round(row[2], 2) if row[2] is not None else None,
                            "count": row[3],
                        }
                return stats
        except sqlite3.Error as e:
            logger.error("Error calculating AI vital statistics: %s", e)
            return {}

    def get_status_breakdown(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        patient_id: Optional[str] = None,
    ) -> Dict[str, int]:
        if start_time is None:
            start_time = datetime.now() - timedelta(hours=24)
        if end_time is None:
            end_time = datetime.now()

        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                query = """
                    SELECT COALESCE(status, 'UNSPECIFIED') AS vital_status, COUNT(*)
                    FROM ai_vital_readings
                    WHERE timestamp BETWEEN ? AND ?
                """
                params: List[Any] = [start_time.isoformat(), end_time.isoformat()]
                if patient_id:
                    query += " AND patient_id = ?"
                    params.append(patient_id)

                query += " GROUP BY COALESCE(status, 'UNSPECIFIED') ORDER BY COUNT(*) DESC"
                cursor.execute(query, params)
                return {str(row[0]): int(row[1]) for row in cursor.fetchall()}
        except sqlite3.Error as e:
            logger.error("Error calculating AI vital status breakdown: %s", e)
            return {}

    def get_patient_summaries(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
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
                           COUNT(*) AS record_count,
                           MAX(timestamp) AS last_timestamp
                    FROM ai_vital_readings
                    WHERE timestamp BETWEEN ? AND ?
                    GROUP BY patient_id, patient_name, patient_species
                    ORDER BY last_timestamp DESC
                    LIMIT ?
                    """,
                    (start_time.isoformat(), end_time.isoformat(), max(1, int(limit))),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error("Error retrieving AI vital patient summaries: %s", e)
            return []

    def get_record_count(self, patient_id: Optional[str] = None) -> int:
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                query = "SELECT COUNT(*) FROM ai_vital_readings"
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
        """Delete all stored AI vital readings and reset runtime logger state."""
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM ai_vital_readings")
                cursor.execute('DELETE FROM sqlite_sequence WHERE name="ai_vital_readings"')
                conn.commit()

            details = []
            if reason:
                details.append(f"reason={reason}")

            if isinstance(context, dict):
                trigger = str(context.get("trigger") or "").strip()
                if trigger:
                    details.append(f"trigger={trigger}")

                previous_patient = context.get("previous_patient") or {}
                next_patient = context.get("next_patient") or {}
                previous_name = str(previous_patient.get("name") or "").strip()
                next_name = str(next_patient.get("name") or "").strip()
                if previous_name or next_name:
                    details.append(f"patient_change={previous_name or '-'}->{next_name or '-'}")

            detail_text = f" ({', '.join(details)})" if details else ""
            logger.info(f"AI vital data cleared{detail_text}")
            self.last_snapshot = None
            self.last_log_time = None
            return True
        except sqlite3.Error as e:
            logger.error("Error clearing AI vital readings: %s", e)
            return False

    def cleanup_old_data(self, days: int = 30) -> int:
        cutoff_time = datetime.now() - timedelta(days=max(1, int(days)))

        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM ai_vital_readings WHERE timestamp < ?",
                    (cutoff_time.isoformat(),),
                )
                deleted = cursor.rowcount
                conn.commit()
                if deleted > 0:
                    logger.info("Cleaned %s old AI vital readings", deleted)
                return deleted
        except sqlite3.Error as e:
            logger.error("Error cleaning old AI vital readings: %s", e)
            return 0
