#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Uyarı Analiz Sistemi - Kuvoz İnkübatör
Bu script, AI vital verilerini analiz ederek anlamlı raporlar üretir.

Kullanım:
    python3 analyze_ai_alerts.py [--hours 24] [--patient_id <id>] [--output json|text]
"""

import json
import sqlite3
import sys
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any, Optional


class AIAlertAnalyzer:
    """AI vital verilerini analiz ederek anlamlı raporlar üretir."""

    # Durum öncelik sıralaması (kriticilik seviyesi)
    STATUS_PRIORITY = {
        'TOO_MUCH_MOTION': 1,
        'OK': 2,
        'LOW_CONF': 3,
        'NOT_ENOUGH_DATA': 4,
        'UNAVAILABLE': 5,
    }

    # Durum açıklamaları
    STATUS_DESCRIPTIONS = {
        'OK': '✅ Normal - Solunum ritmi tespit edildi',
        'LOW_CONF': '⚠️ Düşük Güven - Solunum verisi belirsiz',
        'TOO_MUCH_MOTION': '🔄 Hareketli - Hayvan çok hareket ediyor',
        'NOT_ENOUGH_DATA': '⏳ Yetersiz Veri - Bekleniyor...',
        'UNAVAILABLE': '❌ Veri Yok - Ölçüm yapılamadı',
    }

    # Tür bazlı normal solunum aralıkları (BPM)
    SPECIES_NORMAL_RANGES = {
        'Kedi': {'min': 16, 'max': 40, 'critical_low': 10, 'critical_high': 60},
        'Kedi (domestik)': {'min': 16, 'max': 40, 'critical_low': 10, 'critical_high': 60},
        'Köpek': {'min': 10, 'max': 30, 'critical_low': 8, 'critical_high': 50},
        'Köpek (küçük ırk)': {'min': 15, 'max': 40, 'critical_low': 10, 'critical_high': 60},
        'Köpek (büyük ırk)': {'min': 8, 'max': 24, 'critical_low': 6, 'critical_high': 40},
        'Kuş': {'min': 30, 'max': 100, 'critical_low': 20, 'critical_high': 150},
        'Tavşan': {'min': 30, 'max': 60, 'critical_low': 20, 'critical_high': 80},
        'Kemirgen': {'min': 40, 'max': 120, 'critical_low': 30, 'critical_high': 150},
    }

    def __init__(self, db_path: str = 'data/ai_vitals.db'):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """Veritabanına bağlan."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            return True
        except sqlite3.Error as e:
            print(f"❌ Veritabanı hatası: {e}")
            return False

    def disconnect(self):
        """Veritabanı bağlantısını kapat."""
        if self.conn:
            self.conn.close()

    def get_readings(
        self,
        hours: int = 24,
        patient_id: Optional[str] = None,
        limit: int = 2500,
        min_confidence: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Belirtilen zaman aralığındaki okumaları getir.
        
        Args:
            hours: Kaç saatlik veri alınacak
            patient_id: Hasta ID (opsiyonel)
            limit: Maksimum kayıt sayısı
            min_confidence: Minimum güven eşiği (0.0-1.0). Düşük güvenilir kayıtlar filtrelenir.
        """
        start_time = datetime.now() - timedelta(hours=hours)
        end_time = datetime.now()

        query = """
            SELECT timestamp, patient_id, patient_name, patient_species,
                   respiration_bpm, confidence, status, method,
                   activity_level, vision_status, peaks, window_seconds
            FROM ai_vital_readings
            WHERE timestamp BETWEEN ? AND ?
              AND (confidence IS NULL OR confidence >= ?)
        """
        params = [start_time.isoformat(), end_time.isoformat(), min_confidence]

        if patient_id:
            query += " AND patient_id = ?"
            params.append(patient_id)

        query += " ORDER BY timestamp ASC LIMIT ?"
        params.append(limit)

        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"❌ Okuma hatası: {e}")
            return []

    def analyze_patient(self, readings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Tek bir hasta için detaylı analiz yap."""
        if not readings:
            return None

        # Hasta bilgileri
        patient_info = {
            'id': readings[0]['patient_id'],
            'name': readings[0]['patient_name'],
            'species': readings[0]['patient_species'],
        }

        # Durum dağılımı
        status_counts = defaultdict(int)
        for r in readings:
            status_counts[r['status']] += 1

        # Solunum istatistikleri (sadece OK durumu)
        ok_readings = [r for r in readings if r['status'] == 'OK' and r['respiration_bpm'] is not None]
        bpm_values = [r['respiration_bpm'] for r in ok_readings]
        confidence_values = [r['confidence'] for r in ok_readings if r['confidence'] is not None]

        # Aktivite seviyesi
        activity_values = [r['activity_level'] for r in readings if r['activity_level'] is not None]

        # Hareket durumu
        motion_readings = [r for r in readings if r['status'] == 'TOO_MUCH_MOTION']
        motion_count = len(motion_readings)

        # Düşük güven durumu
        low_conf_readings = [r for r in readings if r['status'] == 'LOW_CONF']

        # Anormallik tespiti
        anomalies = self._detect_anomalies(ok_readings, patient_info['species'])

        # Trend analizi
        trend = self._analyze_trend(ok_readings)

        # Öneriler
        recommendations = self._generate_recommendations(
            status_counts, bpm_values, motion_count,
            len(low_conf_readings), anomalies, patient_info['species']
        )

        return {
            'patient': patient_info,
            'summary': {
                'total_readings': len(readings),
                'time_span_hours': self._calculate_time_span(readings),
                'status_distribution': dict(status_counts),
                'ok_percentage': round(status_counts.get('OK', 0) / len(readings) * 100, 1) if readings else 0,
            },
            'vitals': {
                'respiration': {
                    'min': min(bpm_values) if bpm_values else None,
                    'max': max(bpm_values) if bpm_values else None,
                    'avg': round(sum(bpm_values) / len(bpm_values), 1) if bpm_values else None,
                    'readings_count': len(bpm_values),
                },
                'confidence': {
                    'min': min(confidence_values) if confidence_values else None,
                    'max': max(confidence_values) if confidence_values else None,
                    'avg': round(sum(confidence_values) / len(confidence_values), 2) if confidence_values else None,
                },
                'activity': {
                    'min': round(min(activity_values), 2) if activity_values else None,
                    'max': round(max(activity_values), 2) if activity_values else None,
                    'avg': round(sum(activity_values) / len(activity_values), 2) if activity_values else None,
                },
            },
            'motion': {
                'motion_events': motion_count,
                'motion_percentage': round(motion_count / len(readings) * 100, 1) if readings else 0,
            },
            'low_confidence': {
                'low_conf_events': len(low_conf_readings),
                'low_conf_percentage': round(len(low_conf_readings) / len(readings) * 100, 1) if readings else 0,
            },
            'anomalies': anomalies,
            'trend': trend,
            'recommendations': recommendations,
        }

    def _detect_anomalies(
        self,
        ok_readings: List[Dict[str, Any]],
        species: str
    ) -> List[Dict[str, Any]]:
        """Anormal solunum değerlerini tespit et."""
        anomalies = []
        normal_range = self.SPECIES_NORMAL_RANGES.get(species, {
            'min': 10, 'max': 40, 'critical_low': 8, 'critical_high': 60
        })

        for r in ok_readings:
            bpm = r['respiration_bpm']
            if bpm is None:
                continue

            timestamp = r['timestamp']

            # Kritik düşük
            if bpm < normal_range['critical_low']:
                anomalies.append({
                    'timestamp': timestamp,
                    'type': 'CRITICAL_LOW_BPM',
                    'severity': 'critical',
                    'message': f'🚨 KRİTİK: Solunum {bpm} BPM (ciddi bradipne)',
                    'value': bpm,
                })
            # Kritik yüksek
            elif bpm > normal_range['critical_high']:
                anomalies.append({
                    'timestamp': timestamp,
                    'type': 'CRITICAL_HIGH_BPM',
                    'severity': 'critical',
                    'message': f'🚨 KRİTİK: Solunum {bpm} BPM (ciddi taşipne)',
                    'value': bpm,
                })
            # Uyarı düşük
            elif bpm < normal_range['min']:
                anomalies.append({
                    'timestamp': timestamp,
                    'type': 'WARNING_LOW_BPM',
                    'severity': 'warning',
                    'message': f'⚠️ UYARI: Solunum {bpm} BPM (normalin altında)',
                    'value': bpm,
                })
            # Uyarı yüksek
            elif bpm > normal_range['max']:
                anomalies.append({
                    'timestamp': timestamp,
                    'type': 'WARNING_HIGH_BPM',
                    'severity': 'warning',
                    'message': f'⚠️ UYARI: Solunum {bpm} BPM (normalin üzerinde)',
                    'value': bpm,
                })

            # Düşük güven ile birlikte yüksek solunum
            if bpm > normal_range['max'] * 1.2 and r['confidence'] and r['confidence'] < 0.5:
                anomalies.append({
                    'timestamp': timestamp,
                    'type': 'UNRELIABLE_HIGH_BPM',
                    'severity': 'warning',
                    'message': f'⚠️ GÜVENİLMEZ: Yüksek solunum ({bpm} BPM) ancak düşük güven ({r["confidence"]})',
                    'value': bpm,
                })

        return anomalies

    def _analyze_trend(self, ok_readings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Solunum trendini analiz et."""
        if len(ok_readings) < 3:
            return {'direction': 'insufficient_data', 'description': 'Yetersiz veri'}

        # İlk ve son 5 okumanın ortalaması
        first_5 = [r['respiration_bpm'] for r in ok_readings[:5] if r['respiration_bpm'] is not None]
        last_5 = [r['respiration_bpm'] for r in ok_readings[-5:] if r['respiration_bpm'] is not None]

        if not first_5 or not last_5:
            return {'direction': 'insufficient_data', 'description': 'Yetersiz veri'}

        avg_first = sum(first_5) / len(first_5)
        avg_last = sum(last_5) / len(last_5)
        change = avg_last - avg_first
        change_pct = (change / avg_first * 100) if avg_first > 0 else 0

        if abs(change_pct) < 5:
            direction = 'stable'
            description = f'Stabil (±{abs(change_pct):.1f}%)'
        elif change > 0:
            direction = 'increasing'
            description = f'Yükselişte (+{change_pct:.1f}%)'
        else:
            direction = 'decreasing'
            description = f'Düşüşte ({change_pct:.1f}%)'

        return {
            'direction': direction,
            'description': description,
            'first_avg': round(avg_first, 1),
            'last_avg': round(avg_last, 1),
            'change': round(change, 1),
            'change_percentage': round(change_pct, 1),
        }

    def _generate_recommendations(
        self,
        status_counts: Dict[str, int],
        bpm_values: List[float],
        motion_count: int,
        low_conf_count: int,
        anomalies: List[Dict[str, Any]],
        species: str
    ) -> List[str]:
        """Duruma göre öneriler üret."""
        recommendations = []
        total = sum(status_counts.values())

        if total == 0:
            return ['📊 Veri yok - AI izleme sistemi başlatılmalı']

        # Kritik anomali kontrolü
        critical_anomalies = [a for a in anomalies if a['severity'] == 'critical']
        if critical_anomalies:
            recommendations.append(
                f'🚨 ACİL: {len(critical_anomalies)} kritik solunum anormalliği tespit edildi! '
                'Veteriner hekim müdahalesi gerekli.'
            )

        # Düşük OK oranı
        ok_pct = status_counts.get('OK', 0) / total * 100
        if ok_pct < 50:
            recommendations.append(
                f'⚠️ Dikkat: OK durumunun oranı %{ok_pct:.1f} (düşük). '
                'Kamera açısı veya ışıklandırma kontrol edilmeli.'
            )

        # Yüksek hareket
        motion_pct = motion_count / total * 100
        if motion_pct > 30:
            recommendations.append(
                f'🔄 Hayvan çok hareketli (%{motion_pct:.1f}). '
                'Ağrı kesici veya sakinleştirici değerlendirilebilir.'
            )

        # Yüksek düşük güven
        low_conf_pct = low_conf_count / total * 100
        if low_conf_pct > 40:
            recommendations.append(
                f'⚠️ Düşük güven oranı yüksek (%{low_conf_pct:.1f}). '
                'Kamera netliği ve konumlandırması kontrol edilmeli.'
            )

        # Solunum trendi
        if bpm_values:
            avg_bpm = sum(bpm_values) / len(bpm_values)
            normal_range = self.SPECIES_NORMAL_RANGES.get(species, {'min': 10, 'max': 40})

            if avg_bpm < normal_range['min']:
                recommendations.append(
                    f'📉 Ortalama solunum ({avg_bpm:.1f} BPM) tür için düşük. '
                    'Hipotermi veya metabolik sorunlar açısından kontrol edin.'
                )
            elif avg_bpm > normal_range['max']:
                recommendations.append(
                    f'📈 Ortalama solunum ({avg_bpm:.1f} BPM) tür için yüksek. '
                    'Ağrı, stres veya solunum yolu problemi açısından değerlendirin.'
                )

        # Anomali önerileri
        warning_anomalies = [a for a in anomalies if a['severity'] == 'warning']
        if warning_anomalies and not critical_anomalies:
            recommendations.append(
                f'📊 {len(warning_anomalies)} solunum uyarısı kaydedildi. '
                'Hasta yakından izlenmeli.'
            )

        if not recommendations:
            recommendations.append('✅ Tüm parametreler normal. İzlemeye devam edin.')

        return recommendations

    def _calculate_time_span(self, readings: List[Dict[str, Any]]) -> float:
        """Okumaların zaman aralığını hesapla (saat)."""
        if len(readings) < 2:
            return 0

        try:
            first = datetime.fromisoformat(readings[0]['timestamp'])
            last = datetime.fromisoformat(readings[-1]['timestamp'])
            return (last - first).total_seconds() / 3600
        except (ValueError, TypeError):
            return 0

    def generate_report(
        self,
        hours: int = 24,
        patient_id: Optional[str] = None,
        output_format: str = 'text'
    ) -> str:
        """Genel rapor üret."""
        readings = self.get_readings(hours=hours, patient_id=patient_id)

        if not readings:
            return "❌ Son {} saat içinde veri bulunamadı.".format(hours)

        # Hastalara göre grupla
        patients = defaultdict(list)
        for r in readings:
            pid = r['patient_id'] or 'unknown'
            patients[pid].append(r)

        # Her hasta için analiz
        analyses = []
        for pid, patient_readings in patients.items():
            analysis = self.analyze_patient(patient_readings)
            if analysis:
                analyses.append(analysis)

        if output_format == 'json':
            return json.dumps({
                'generated_at': datetime.now().isoformat(),
                'time_range_hours': hours,
                'total_patients': len(analyses),
                'patients': analyses,
            }, indent=2, ensure_ascii=False)

        # Text format
        return self._format_text_report(analyses, hours)

    def _format_text_report(
        self,
        analyses: List[Dict[str, Any]],
        hours: int
    ) -> str:
        """Metin formatında rapor oluştur."""
        lines = []
        lines.append("=" * 80)
        lines.append("🏥 KUVOZ VETERİNER İNKÜBATÖR - AI UYARI ANALİZ RAPORU")
        lines.append("=" * 80)
        lines.append(f"📅 Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        lines.append(f"⏰ Zaman Aralığı: Son {hours} saat")
        lines.append(f"📊 Toplam Hasta: {len(analyses)}")
        lines.append("")

        for analysis in analyses:
            patient = analysis['patient']
            summary = analysis['summary']
            vitals = analysis['vitals']
            motion = analysis['motion']
            anomalies = analysis['anomalies']
            trend = analysis['trend']
            recommendations = analysis['recommendations']

            lines.append("-" * 80)
            lines.append(f"🐾 HASTA: {patient['name'] or 'Bilinmeyen'} ({patient['id']})")
            lines.append(f"📋 Tür: {patient['species'] or 'Belirtilmemiş'}")
            lines.append("")

            # Özet
            lines.append("📊 GENEL ÖZET")
            lines.append(f"  • Toplam Okuma: {summary['total_readings']}")
            lines.append(f"  • Kapsanan Süre: {summary['time_span_hours']:.1f} saat")
            lines.append(f"  • OK Oranı: %{summary['ok_percentage']:.1f}")
            lines.append(f"  • Durum Dağılımı: {summary['status_distribution']}")
            lines.append("")

            # Vital bulgular
            lines.append("💓 VİTAL BULGULAR")
            resp = vitals['respiration']
            if resp['avg'] is not None:
                lines.append(f"  • Solunum (BPM): {resp['min']:.1f} - {resp['max']:.1f} (Ort: {resp['avg']:.1f})")
            else:
                lines.append(f"  • Solunum (BPM): Veri yok")

            conf = vitals['confidence']
            if conf['avg'] is not None:
                lines.append(f"  • Güven: {conf['min']:.2f} - {conf['max']:.2f} (Ort: {conf['avg']:.2f})")

            activity = vitals['activity']
            if activity['avg'] is not None:
                lines.append(f"  • Aktivite: {activity['min']:.2f} - {activity['max']:.2f} (Ort: {activity['avg']:.2f})")
            lines.append("")

            # Hareket analizi
            lines.append("🔄 HAREKET ANALİZİ")
            lines.append(f"  • Hareket Olayları: {motion['motion_events']} (%{motion['motion_percentage']:.1f})")
            lines.append(f"  • Düşük Güven Olayları: {analysis['low_confidence']['low_conf_events']} "
                        f"(%{analysis['low_confidence']['low_conf_percentage']:.1f})")
            lines.append("")

            # Trend
            lines.append("📈 TREND ANALİZİ")
            lines.append(f"  • Yön: {trend['description']}")
            if trend.get('first_avg'):
                lines.append(f"  • İlk Ortalama: {trend['first_avg']} BPM")
                lines.append(f"  • Son Ortalama: {trend['last_avg']} BPM")
                lines.append(f"  • Değişim: {trend['change']:+.1f} BPM ({trend['change_percentage']:+.1f}%)")
            lines.append("")

            # Anomaliler
            if anomalies:
                lines.append("⚠️ ANOMALİLER")
                for a in anomalies[:10]:  # İlk 10 anomali
                    lines.append(f"  [{a['timestamp'][:19]}] {a['message']}")
                if len(anomalies) > 10:
                    lines.append(f"  ... ve {len(anomalies) - 10} daha")
            else:
                lines.append("✅ Anomali tespit edilmedi")
            lines.append("")

            # Öneriler
            lines.append("💡 ÖNERİLER")
            for rec in recommendations:
                lines.append(f"  {rec}")
            lines.append("")

        lines.append("=" * 80)
        lines.append("📌 Not: Bu rapor AI destekli analiz içerir. Kritik durumlarda veteriner hekim kararı esastır.")
        lines.append("=" * 80)

        return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='AI Uyarı Analiz Sistemi - Kuvoz İnkübatör'
    )
    parser.add_argument(
        '--hours', type=int, default=24,
        help='Analiz edilecek zaman aralığı (saat) - Varsayılan: 24'
    )
    parser.add_argument(
        '--patient-id', type=str, default=None,
        help='Hasta ID (tüm hastalar için boş bırakın)'
    )
    parser.add_argument(
        '--output', type=str, choices=['text', 'json'], default='text',
        help='Çıktı formatı - Varsayılan: text'
    )
    parser.add_argument(
        '--db', type=str, default='data/ai_vitals.db',
        help='Veritabanı yolu - Varsayılan: data/ai_vitals.db'
    )
    parser.add_argument(
        '--min-confidence', type=float, default=0.5,
        help='Minimum güven eşiği (0.0-1.0). Düşük güvenilir kayıtlar filtrelenir. Varsayılan: 0.5'
    )

    args = parser.parse_args()

    analyzer = AIAlertAnalyzer(db_path=args.db)

    if not analyzer.connect():
        sys.exit(1)

    try:
        report = analyzer.generate_report(
            hours=args.hours,
            patient_id=args.patient_id,
            output_format=args.output
        )
        print(report)
    finally:
        analyzer.disconnect()


if __name__ == '__main__':
    main()
