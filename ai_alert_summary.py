#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Uyarı Özet API - Kuvoz İnkübatör
Kısa, öz ve anlamlı AI uyarı özeti üretir (web dashboard için optimize edilmiş)
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


class AIAlertSummary:
    """AI vital verilerinden kısa ve anlamlı özetler üretir."""

    SPECIES_RANGES = {
        'Kedi': {'min': 16, 'max': 40, 'critical_low': 10, 'critical_high': 60},
        'Köpek': {'min': 10, 'max': 30, 'critical_low': 8, 'critical_high': 50},
        'Kuş': {'min': 30, 'max': 100, 'critical_low': 20, 'critical_high': 150},
        'Tavşan': {'min': 30, 'max': 60, 'critical_low': 20, 'critical_high': 80},
    }

    def __init__(self, db_path: str = 'data/ai_vitals.db'):
        self.db_path = db_path

    def get_quick_summary(
        self,
        hours: int = 24,
        patient_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Hızlı özet rapor üretir."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            start_time = datetime.now() - timedelta(hours=hours)
            end_time = datetime.now()
            query = """
                SELECT timestamp, patient_id, patient_name, patient_species,
                       respiration_bpm, confidence, status, activity_level, vision_status
                FROM ai_vital_readings
                WHERE timestamp BETWEEN ? AND ?
            """
            params = [start_time.isoformat(), end_time.isoformat()]

            if patient_id:
                query += " AND patient_id = ?"
                params.append(patient_id)

            query += " ORDER BY timestamp DESC LIMIT 1000"

            cursor = conn.cursor()
            cursor.execute(query, params)
            readings = [dict(row) for row in cursor.fetchall()]

            if not readings:
                return self._empty_summary(hours)

            # Grup by hasta
            patients = {}
            for r in readings:
                pid = r['patient_id'] or 'unknown'
                if pid not in patients:
                    patients[pid] = []
                patients[pid].append(r)

            patient_summaries = []
            critical_count = 0
            warning_count = 0

            for pid, patient_readings in patients.items():
                summary = self._analyze_single_patient(patient_readings)
                patient_summaries.append(summary)

                # Sayaçları güncelle
                critical_count += summary.get('alerts', {}).get('critical_count', 0)
                warning_count += summary.get('alerts', {}).get('warning_count', 0)

            return {
                'generated_at': datetime.now().isoformat(),
                'time_range_hours': hours,
                'total_patients': len(patient_summaries),
                'patients': patient_summaries,
                'overall': {
                    'critical_alerts': critical_count,
                    'warning_alerts': warning_count,
                    'health_score': self._calculate_health_score(patient_summaries),
                },
            }

        except sqlite3.Error as e:
            return {'error': str(e)}
        finally:
            if conn:
                conn.close()

    def _analyze_single_patient(
        self,
        readings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Tek hasta için analiz."""
        if not readings:
            return self._empty_patient_summary()

        # En son okuma
        latest = readings[0]

        # Hasta bilgisi
        patient_info = {
            'id': latest['patient_id'],
            'name': latest['patient_name'] or 'Bilinmeyen',
            'species': latest['patient_species'] or 'Belirtilmemiş',
        }

        # OK durumundaki okumalar
        ok_readings = [
            r for r in readings
            if r['status'] == 'OK' and r['respiration_bpm'] is not None
        ]

        # Solunum istatistikleri
        bpm_values = [r['respiration_bpm'] for r in ok_readings]
        avg_bpm = sum(bpm_values) / len(bpm_values) if bpm_values else None

        # Durum dağılımı
        status_counts = {}
        for r in readings:
            s = r['status']
            status_counts[s] = status_counts.get(s, 0) + 1

        # Anomali tespiti
        species = patient_info['species']
        range_info = self.SPECIES_RANGES.get(species, {
            'min': 10, 'max': 40, 'critical_low': 8, 'critical_high': 60
        })

        critical_alerts = 0
        warning_alerts = 0
        alert_messages = []

        for r in ok_readings:
            bpm = r['respiration_bpm']
            if bpm < range_info['critical_low']:
                critical_alerts += 1
            elif bpm < range_info['min']:
                warning_alerts += 1
            elif bpm > range_info['critical_high']:
                critical_alerts += 1
            elif bpm > range_info['max']:
                warning_alerts += 1

        # Son durum değerlendirmesi
        current_status = latest['status']
        current_bpm = latest['respiration_bpm']
        current_confidence = latest['confidence']

        # Durum mesajı
        if current_status == 'TOO_MUCH_MOTION':
            status_message = "🔄 Hayvan hareketli - ölçüm yapılamıyor"
        elif current_status == 'LOW_CONF':
            status_message = "⚠️ Düşük güven - kamera/konum kontrol edilmeli"
        elif current_status == 'OK':
            if current_bpm:
                if current_bpm < range_info['min']:
                    status_message = f"⚠️ Solunum düşük ({current_bpm} BPM)"
                elif current_bpm > range_info['max']:
                    status_message = f"⚠️ Solunum yüksek ({current_bpm} BPM)"
                else:
                    status_message = f"✅ Normal ({current_bpm} BPM)"
            else:
                status_message = "✅ Durum stabil"
        else:
            status_message = "⏳ Veri bekleniyor"

        # Öneri
        recommendations = []
        if critical_alerts > 0:
            recommendations.append("🚨 Kritik solunum değerleri - veteriner kontrolü gerekli")
        if warning_alerts > 5:
            recommendations.append("⚠️ Çok sayıda uyarı - hasta yakından izlenmeli")
        if status_counts.get('TOO_MUCH_MOTION', 0) > len(readings) * 0.3:
            recommendations.append("🔄 Hayvan çok hareketli - ağrı/stres değerlendirin")
        if status_counts.get('LOW_CONF', 0) > len(readings) * 0.4:
            recommendations.append("📷 Kamera açısı/konumu kontrol edilmeli")
        if not recommendations:
            recommendations.append("✅ Parametreler normal - izlemeye devam")

        # Trend (basit)
        trend = "stabil"
        if len(ok_readings) >= 10:
            first_avg = sum([r['respiration_bpm'] for r in ok_readings[-1:-6:-1]]) / 5
            last_avg = sum([r['respiration_bpm'] for r in ok_readings[:5]]) / 5
            if last_avg > first_avg * 1.2:
                trend = "yükselişte ↗️"
            elif last_avg < first_avg * 0.8:
                trend = "düşüşte ↘️"

        return {
            'patient': patient_info,
            'latest_status': {
                'status': current_status,
                'respiration_bpm': current_bpm,
                'confidence': current_confidence,
                'activity_level': latest.get('activity_level'),
                'vision_status': latest.get('vision_status'),
                'timestamp': latest['timestamp'],
                'message': status_message,
            },
            'statistics': {
                'total_readings': len(readings),
                'ok_readings': len(ok_readings),
                'avg_respiration': round(avg_bpm, 1) if avg_bpm else None,
                'status_distribution': status_counts,
            },
            'alerts': {
                'critical_count': critical_alerts,
                'warning_count': warning_alerts,
                'messages': alert_messages[:5],  # İlk 5
            },
            'trend': trend,
            'recommendations': recommendations,
        }

    def _empty_summary(self, hours: int) -> Dict[str, Any]:
        return {
            'generated_at': datetime.now().isoformat(),
            'time_range_hours': hours,
            'total_patients': 0,
            'patients': [],
            'overall': {
                'critical_alerts': 0,
                'warning_alerts': 0,
                'health_score': 0,
            },
            'message': '⏳ Son {} saat içinde veri yok'.format(hours),
        }

    def _empty_patient_summary(self) -> Dict[str, Any]:
        return {
            'patient': {'id': '', 'name': '', 'species': ''},
            'latest_status': {
                'status': 'NO_DATA',
                'respiration_bpm': None,
                'confidence': None,
                'activity_level': None,
                'vision_status': None,
                'timestamp': None,
                'message': 'Veri yok',
            },
            'statistics': {
                'total_readings': 0,
                'ok_readings': 0,
                'avg_respiration': None,
                'status_distribution': {},
            },
            'alerts': {
                'critical_count': 0,
                'warning_count': 0,
                'messages': [],
            },
            'trend': 'unknown',
            'recommendations': ['📊 Veri yok - AI izleme başlatılmalı'],
        }

    def _calculate_health_score(
        self,
        patient_summaries: List[Dict[str, Any]]
    ) -> int:
        """Genel sağlık skoru hesapla (0-100)."""
        if not patient_summaries:
            return 0

        total_score = 0
        for summary in patient_summaries:
            score = 100

            # OK oranı
            stats = summary['statistics']
            if stats['total_readings'] > 0:
                ok_ratio = stats['ok_readings'] / stats['total_readings']
                score -= (1 - ok_ratio) * 30

            # Kritik uyarılar
            alerts = summary['alerts']
            score -= min(alerts['critical_count'] * 5, 30)

            # Trend
            trend = summary.get('trend', 'stabil')
            if trend == 'düşüşte ↘️':
                score -= 10
            elif trend == 'yükselişte ↗️':
                score += 5

            total_score += max(0, min(100, score))

        return round(total_score / len(patient_summaries))


# Test
if __name__ == '__main__':
    analyzer = AIAlertSummary()
    summary = analyzer.get_quick_summary(hours=24)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
