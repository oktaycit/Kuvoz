# AI Uyarı Analiz Sistemi

## Genel Bakış

Kuvoz İnkübatör sistemi artık **gelişmiş AI uyarı analiz sistemi** ile donatılmıştır. Bu sistem, AI vital verilerini analiz ederek **anlamlı, aksiyon odaklı raporlar** üretir.

## Yeni Özellikler

### 1. **Detaylı Analiz Scripti** (`analyze_ai_alerts.py`)

Son 24-720 saatlik verileri analiz ederek kapsamlı rapor üretir:

```bash
# Son 24 saatin raporu
python3 analyze_ai_alerts.py --hours 24

# Son 48 saat
python3 analyze_ai_alerts.py --hours 48

# Belirli bir hasta için
python3 analyze_ai_alerts.py --hours 24 --patient-id "2026-03-22_Morbius"

# JSON formatında
python3 analyze_ai_alerts.py --hours 24 --output json
```

#### Örnek Rapor Çıktısı:

```
================================================================================
🏥 KUVOZ VETERİNER İNKÜBATÖR - AI UYARI ANALİZ RAPORU
================================================================================
📅 Rapor Tarihi: 23.03.2026 12:07
⏰ Zaman Aralığı: Son 48 saat
📊 Toplam Hasta: 1

--------------------------------------------------------------------------------
🐾 HASTA: Morbius (2026-03-22_Morbius)
📋 Tür: Kedi

📊 GENEL ÖZET
  • Toplam Okuma: 142
  • Kapsanan Süre: 14.7 saat
  • OK Oranı: %50.7
  • Durum Dağılımı: {'LOW_CONF': 35, 'OK': 72, 'TOO_MUCH_MOTION': 35}

💓 VİTAL BULGULAR
  • Solunum (BPM): 6.1 - 53.9 (Ort: 15.8)
  • Güven: 0.65 - 0.84 (Ort: 0.71)
  • Aktivite: 0.00 - 77.71 (Ort: 15.15)

🔄 HAREKET ANALİZİ
  • Hareket Olayları: 35 (%24.6)
  • Düşük Güven Olayları: 35 (%24.6)

📈 TREND ANALİZİ
  • Yön: Yükselişte (+103.1%)
  • İlk Ortalama: 9.1 BPM
  • Son Ortalama: 18.4 BPM
  • Değişim: +9.4 BPM (+103.1%)

⚠️ ANOMALİLER
  [2026-03-22T22:15:46] 🚨 KRİTİK: Solunum 8.6 BPM (ciddi bradipne)
  [2026-03-22T22:17:06] 🚨 KRİTİK: Solunum 7.9 BPM (ciddi bradipne)
  [2026-03-22T22:33:06] 🚨 KRİTİK: Solunum 7.3 BPM (ciddi bradipne)
  ... ve 45 daha

💡 ÖNERİLER
  🚨 ACİL: 18 kritik solunum anormalliği tespit edildi! Veteriner hekim müdahalesi gerekli.
  📉 Ortalama solunum (15.8 BPM) tür için düşük. Hipotermi veya metabolik sorunlar açısından kontrol edin.
```

### 2. **Hızlı Özet API** (`ai_alert_summary.py`)

Web dashboard için optimize edilmiş kısa özet rapor:

```python
from ai_alert_summary import AIAlertSummary

analyzer = AIAlertSummary()
summary = analyzer.get_quick_summary(hours=24)
```

#### Örnek JSON Çıktısı:

```json
{
  "generated_at": "2026-03-23T12:13:24.419832",
  "time_range_hours": 24,
  "total_patients": 1,
  "patients": [{
    "patient": {
      "id": "2026-03-22_Morbius",
      "name": "Morbius",
      "species": "Kedi"
    },
    "latest_status": {
      "status": "TOO_MUCH_MOTION",
      "respiration_bpm": null,
      "confidence": 0.0,
      "message": "🔄 Hayvan hareketli - ölçüm yapılamıyor"
    },
    "statistics": {
      "total_readings": 146,
      "ok_readings": 74,
      "avg_respiration": 15.6,
      "status_distribution": {
        "TOO_MUCH_MOTION": 36,
        "OK": 74,
        "LOW_CONF": 36
      }
    },
    "alerts": {
      "critical_count": 19,
      "warning_count": 38
    },
    "trend": "stabil",
    "recommendations": [
      "🚨 Kritik solunum değerleri - veteriner kontrolü gerekli",
      "⚠️ Çok sayıda uyarı - hasta yakından izlenmeli"
    ]
  }],
  "overall": {
    "critical_alerts": 19,
    "warning_alerts": 38,
    "health_score": 55
  }
}
```

### 3. **Web API Endpoint**

Yeni API endpoint üzerinden real-time AI uyarı özeti:

```bash
# Son 24 saatin özeti
curl http://localhost:8000/api/ai-alerts?hours=24

# Belirli hasta için
curl http://localhost:8000/api/ai-alerts?hours=48&patient_id=2026-03-22_Morbius
```

## Analiz Özellikleri

### Solunum Analizi

- **Tür bazlı normal aralıklar**:
  - Kedi: 16-40 BPM (kritik: <10, >60)
  - Köpek: 10-30 BPM (kritik: <8, >50)
  - Kuş: 30-100 BPM (kritik: <20, >150)
  - Tavşan: 30-60 BPM (kritik: <20, >80)

- **Anomali tespiti**:
  - 🚨 Kritik düşük solunum (bradipne)
  - 🚨 Kritik yüksek solunum (taşipne)
  - ⚠️ Uyarı seviyesi düşük/yüksek solunum
  - ⚠️ Güvenilmez yüksek solunum okumaları

### Durum Analizi

| Durum | İkon | Açıklama |
|-------|------|----------|
| OK | ✅ | Normal solunum ritmi tespit edildi |
| LOW_CONF | ⚠️ | Düşük güven - solunum verisi belirsiz |
| TOO_MUCH_MOTION | 🔄 | Hayvan çok hareket ediyor |
| NOT_ENOUGH_DATA | ⏳ | Yetersiz veri - bekleniyor |

### Trend Analizi

- **Yön**: Stabil / Yükselişte / Düşüşte
- **İlk ve son ortalama** karşılaştırması
- **Değişim yüzdesi** hesaplama

### Öneri Sistemi

Otomatik öneri üretimi:

- 🚨 Kritik anomali durumunda acil veteriner uyarısı
- ⚠️ Düşük OK oranı durumunda kamera/konum kontrolü
- 🔄 Yüksek hareket durumunda ağrı/stres değerlendirmesi
- 📷 Düşük güven oranı durumunda kamera ayarları
- 📈 Anormal solunum ortalaması durumunda tıbbi öneriler

## Kullanım Senaryoları

### 1. Sabah Kontrolü (Veteriner Hekim)

```bash
# Gece boyunca olan biteni kontrol et
python3 analyze_ai_alerts.py --hours 12
```

**Çıktı**: Son 12 saatteki tüm kritik olaylar ve öneriler

### 2. Hasta Taburcu Etmeden Önce

```bash
# Son 24 saatin detaylı raporu
python3 analyze_ai_alerts.py --hours 24 --patient-id "2026-03-22_Morbius"
```

**Çıktı**: Hasta için tam vital raporu (taburcu kararı için)

### 3. Web Dashboard Entegrasyonu

```javascript
// Frontend'den API çağrısı
fetch('/api/ai-alerts?hours=24')
  .then(response => response.json())
  .then(data => {
    console.log(`Sağlık Skoru: ${data.overall.health_score}`);
    console.log(`Kritik Uyarılar: ${data.overall.critical_alerts}`);
    
    data.patients.forEach(patient => {
      console.log(`${patient.patient.name}: ${patient.latest_status.message}`);
      patient.recommendations.forEach(rec => {
        console.log(`  → ${rec}`);
      });
    });
  });
```

### 4. Otomatik Raporlama (Cron Job)

```bash
# Her sabah 8:00'da rapor üret
0 8 * * * cd /home/vet/kuvoz && python3 analyze_ai_alerts.py --hours 24 --output json > /tmp/ai_report_$(date +\%Y\%m\%d).json
```

## Sağlık Skoru Sistemi

Genel hasta sağlık durumu 0-100 arası puanlanır:

- **90-100**: ✅ Mükemmel - Tüm parametreler normal
- **70-89**: 🟢 İyi - Minör anormallikler
- **50-69**: 🟡 Orta - İzleme gerekli
- **30-49**: 🟠 Kötü - Veteriner kontrolü önerilir
- **0-29**: 🔴 Kritik - Acil müdahale gerekli

### Skor Hesaplama

```python
score = 100
score -= (1 - OK_oranı) * 30  # OK durumu oranı
score -= min(kritik_sayı * 5, 30)  # Kritik uyarılar
score -= 10  # Düşüş trendi varsa
score += 5  # Yükseliş trendi varsa
```

## Veri Kalitesi İyileştirmeleri

### Hareket Filtreleme

- `TOO_MUCH_MOTION` durumları ayrı analiz edilir
- Hareket sırasında düşük güven okumaları filtrelenir
- Hareket sonrası ilk okumalar cooldown olarak işaretlenir

### Düşük Güven Filtreleme

- `LOW_CONF` durumu için özel eşikler
- Aktivite seviyesi ile korelasyon kontrolü
- Güvenilir olmayan okumalar elenir

### Değişim Algılama

- Sadece **anlamlı değişimler** loglanır
- Minimum BPM değişim: 5.0
- Minimum güven değişimi: 0.15
- Heartbeat interval: 15 saniye (zorunlu periyodik kayıt)

## Performans

- **Veritabanı boyutu**: ~120KB (24 saatlik veri)
- **Analiz süresi**: <1 saniye (146 okuma)
- **API yanıt süresi**: <100ms
- **Veri saklama**: 30 gün (otomatik temizleme)

## Sorun Giderme

### Veri Yok Hatası

```bash
# AI izleme başlatılmış mı kontrol et
journalctl -u kuvoz-web.service | grep "AI Manager"

# Veritabanı var mı kontrol et
ls -lh ~/kuvoz/data/ai_vitals.db
```

### Kamera Başarısız

```bash
# Kamera durumunu kontrol et
vcgencmd get_camera

# Kamera modülünü yeniden başlat
sudo systemctl restart kuvoz-web.service
```

### Yüksek Düşük Güven Oranı

1. Kamera lensini temizleyin
2. Işıklandırmayı kontrol edin
3. Kamera açısını ayarlayın
4. Hedefleme çerçevesini kontrol edin

## API Referansı

### GET /api/ai-alerts

**Parametreler:**
- `hours` (opsiyonel): Zaman aralığı (1-720 saat, varsayılan: 24)
- `patient_id` (opsiyonel): Hasta ID

**Yanıt:**
```json
{
  "generated_at": "ISO8601 timestamp",
  "time_range_hours": 24,
  "total_patients": 1,
  "patients": [...],
  "overall": {
    "critical_alerts": 19,
    "warning_alerts": 38,
    "health_score": 55
  }
}
```

## Dosyalar

| Dosya | Açıklama |
|-------|----------|
| `analyze_ai_alerts.py` | Detaylı analiz scripti |
| `ai_alert_summary.py` | Hızlı özet modülü |
| `lib/data/ai_vitals_logger.py` | SQLite veri kayıt sistemi |
| `lib/ai/manager.py` | AI yönetici modülü |
| `lib/ai/analytics.py` | Anomali tespit motoru |
| `lib/ai/vital_signs.py` | Solunum tahmin algoritması |
| `data/ai_vitals.db` | SQLite veritabanı |

## Gelecek Geliştirmeler

- [ ] Grafik dashboard entegrasyonu
- [ ] SMS/Email bildirimleri
- [ ] Trend tahmini (ML tabanlı)
- [ ] Çoklu hasta karşılaştırma
- [ ] Uzun dönem istatistikler
- [ ] PDF rapor export

## İlgili Dokümantasyon

- [AI_ALERTS.md](AI_ALERTS.md) - AI uyarı sistemi genel bakış
- [AI_INTEGRATION.md](AI_INTEGRATION.md) - AI entegrasyon detayları
- [AI_DYNAMIC_VITAL_THRESHOLDS.md](AI_DYNAMIC_VITAL_THRESHOLDS.md) - Dinamik eşik sistemi

---

**Not**: Bu sistem yapay zeka destekli analiz içerir. Kritik durumlarda her zaman veteriner hekim kararı esastır.
