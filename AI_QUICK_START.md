# AI Uyarı Sistemi - Hızlı Başlangıç

## Komutlar

### Detaylı Rapor (Terminal)

```bash
# Son 24 saatin raporu (text)
python3 analyze_ai_alerts.py --hours 24

# Son 48 saat, JSON formatında
python3 analyze_ai_alerts.py --hours 48 --output json

# Belirli hasta için
python3 analyze_ai_alerts.py --hours 24 --patient-id "2026-03-22_Morbius"
```

### API Çağrıları

```bash
# Basit çağrı
curl 'http://localhost:8000/api/ai-alerts?hours=24'

# JSON formatında
curl 'http://localhost:8000/api/ai-alerts?hours=24' | python3 -m json.tool

# Belirli hasta için
curl 'http://localhost:8000/api/ai-alerts?hours=24&patient_id=2026-03-22_Morbius'
```

### JavaScript (Frontend)

```javascript
// AI uyarılarını getir
async function getAIAlerts(hours = 24) {
  const response = await fetch(`/api/ai-alerts?hours=${hours}`);
  const data = await response.json();
  
  console.log(`Sağlık Skoru: ${data.overall.health_score}/100`);
  console.log(`Kritik Uyarılar: ${data.overall.critical_alerts}`);
  
  data.patients.forEach(patient => {
    console.log(`${patient.patient.name}: ${patient.latest_status.message}`);
    patient.recommendations.forEach(rec => {
      console.log(`  → ${rec}`);
    });
  });
  
  return data;
}

// Kullanım
getAIAlerts(24);
```

## Durum İkonları

| İkon | Anlam | Aksiyon |
|------|-------|---------|
| ✅ | Normal | İzlemeye devam |
| ⚠️ | Uyarı | Kontrol et |
| 🚨 | Kritik | Acil müdahale |
| 🔄 | Hareketli | Bekle |
| 📷 | Kamera | Ayar kontrol |
| 📊 | Veri yok | Sistem kontrol |

## Sağlık Skoru Yorumlama

| Skor | Durum | Aksiyon |
|------|-------|---------|
| 90-100 | ✅ Mükemmel | Rutin izleme |
| 70-89 | 🟢 İyi | Minör kontroller |
| 50-69 | 🟡 Orta | Yakın izleme |
| 30-49 | 🟠 Kötü | Veteriner çağır |
| 0-29 | 🔴 Kritik | ACİL MÜDAHALE |

## Örnek Çıktı

```
================================================================================
🏥 KUVOZ VETERİNER İNKÜBATÖR - AI UYARI ANALİZ RAPORU
================================================================================
📅 Rapor Tarihi: 23.03.2026 12:07
⏰ Zaman Aralığı: Son 24 saat
📊 Toplam Hasta: 1

--------------------------------------------------------------------------------
🐾 HASTA: Morbius (2026-03-22_Morbius)
📋 Tür: Kedi

📊 GENEL ÖZET
  • Toplam Okuma: 146
  • OK Oranı: %50.7
  • Sağlık Skoru: 55/100

💓 VİTAL BULGULAR
  • Solunum: 6.1 - 53.9 BPM (Ort: 15.8)
  • ⚠️ DÜŞÜK (Normal: 16-40)

⚠️ ANOMALİLER
  • 19 kritik solunum anormalliği
  • 39 uyarı

💡 ÖNERİLER
  🚨 ACİL: Kritik solunum değerleri - veteriner kontrolü gerekli
  📉 Ortalama solunum tür için düşük - hipotermi kontrolü
```

## Dosyalar

| Dosya | Açıklama |
|-------|----------|
| `analyze_ai_alerts.py` | Detaylı analiz scripti |
| `ai_alert_summary.py` | API modülü |
| `data/ai_vitals.db` | Veritabanı (~120KB/gün) |
| `docs/AI_ALERT_ANALYSIS.md` | Detaylı dokümantasyon |

## Sorun Giderme

### Veri Yok
```bash
# AI izleme başlatılmış mı?
journalctl -u kuvoz-web.service | grep "AI Manager"

# Veritabanı kontrol
ls -lh ~/kuvoz/data/ai_vitals.db
```

### API Çalışmıyor
```bash
# Web servisi restart
sudo systemctl restart kuvoz-web.service

# API testi
curl 'http://localhost:8000/api/ai-alerts?hours=24'
```

### Yüksek Düşük Güven
1. Kamera lensini temizle
2. Işıklandırmayı kontrol et
3. Kamera açısını ayarla

## İpuçları

- **Sabah kontrolü**: `--hours 12` (gece raporu)
- **Taburcu raporu**: `--patient-id <id>` (hasta özel)
- **JSON export**: `--output json > rapor.json`
- **Cron job**: Her sabah 8:00'da otomatik rapor

---

**Detaylı bilgi**: `docs/AI_ALERT_ANALYSIS.md`
