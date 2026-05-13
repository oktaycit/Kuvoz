# AI Alert Teşhis Rehberi

## Problem
Son güncellemeden sonra Yapay Zeka hiç log kayıt almadı. Bu durumun birkaç olası nedeni olabilir:

## Olası Nedenler

### 1. AI Modülü Enable Edilmemiş
- Web UI'da AI toggle kapalı olabilir
- Settings'te `ai_enabled: False` olarak kaydedilmiş olabilir

### 2. Kamera Başlatılamamış
- Kamera fiziksel olarak bağlı değil
- Kamera sürücüleri yüklü değil (`picamera2` veya `opencv`)
- `/dev/video0` cihazı mevcut değil
- Kamera başka bir proses tarafından kullanılıyor

### 3. Kedi Kamera Görüş Alanına Girmiyor
- Kamera açısı yanlış
- Kedi çok hareketli (`TOO_MUCH_MOTION` durumu)
- Işık koşulları yetersiz

### 4. Logging Disabled
- `system_settings.logging_enabled: False`

## Teşhis Adımları

### 1. Diagnostic Script Çalıştır

```bash
# Raspberry Pi'de çalıştır
cd ~/kuvoz
python3 diagnose_ai_alerts.py
```

Bu script şunları kontrol eder:
- ✅ `data/` klasörü ve `ai_vitals.db` varlığı
- ✅ AI modül import edilebilirliği
- ✅ Camera device mevcutluğu (`/dev/video*`)
- ✅ Son AI logları

### 2. Web Server Loglarını İncele

```bash
# systemd servisi kullanılıyorsa
journalctl -u kuvoz-web -f | grep -i "AI\|camera\|vision"

# Manuel çalıştırılıyorsa
tail -f web_server.log | grep -i "AI\|camera\|vision"
```

**Aranacak log mesajları:**

| Mesaj | Anlamı |
|-------|--------|
| `🤖 AI Module enabled by user - STARTED SUCCESSFULLY` | AI başarıyla başlatıldı |
| `❌ AI Manager.start() returned False` | Kamera başlatılamadı |
| `⚠️ AI update skipped - no frame` | AI çalışıyor ama frame üretmiyor |
| `📝 AI vital logged to database` | Veritabanına kayıt yapıldı |
| `🎯 AI loop state changed` | AI durumu değişti |

Not:
- `AI vital skip` mesajları artık `debug` seviyesindedir; normal production journal çıktısında görünmemesi beklenir.
- Bu nedenle teşhiste öncelik `AI vital logged`, `AI loop state changed`, kamera ve frame uyarılarında olmalıdır.
- Son kamera optimizasyonundan sonra düşük FPS normaldir: varsayılan kamera işleme 320x240 / 1 FPS, UI güncellemesi yaklaşık 2 saniyede birdir. Yalnızca görüntü hiç gelmiyorsa veya `AI update skipped - no frame` uyarıları sürekli tekrarlıyorsa kamera bağlantısını inceleyin.

### Beklenen Kamera Performansı

| Ayar | Varsayılan | Ortam Değişkeni |
|------|------------|-----------------|
| Kamera genişliği | 320 px | `KUVOZ_AI_WIDTH` |
| Kamera yüksekliği | 240 px | `KUVOZ_AI_HEIGHT` |
| Kamera işleme hızı | 1 FPS | `KUVOZ_AI_FPS` |
| UI gönderim aralığı | 2 sn | `KUVOZ_AI_UPDATE_INTERVAL_SEC` |
| Termal yavaşlama eşiği | 62°C | `KUVOZ_AI_THERMAL_THROTTLE_TEMP` |
| Termal dönüş eşiği | 58°C | `KUVOZ_AI_THERMAL_RESTORE_TEMP` |
| Termal yavaşlama hızı | 0.5 FPS | `KUVOZ_AI_THROTTLED_FPS` |

### 3. UI'da AI'ı Enable Et

1. Web arayüzünü aç: `http://raspberrypi:8000`
2. Settings > AI Settings bölümüne git
3. AI toggle'ı ON konumuna getir
4. Console'da (F12 > Console) veya server loglarında hata var mı kontrol et

### 4. Kamera Testi

```bash
# Camera device var mı?
ls -la /dev/video*

# picamera2 testi
python3 -c "from picamera2 import Picamera2; picam = Picamera2(); print('✅ picamera2 OK')"

# OpenCV testi
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('✅ OpenCV OK' if cap.isOpened() else '❌ OpenCV FAIL')"
```

## Çözüm Senaryoları

### Senaryo 1: AI Enable Değil
**Çözüm:** UI'dan AI'ı enable edin.

### Senaryo 2: Kamera Başlatılamıyor
**Çözüm:**
1. Kamera kablosunu kontrol edin (CSI bağlantısı)
2. Kamera modülünü yeniden takın
3. `sudo raspi-config` > Interface Options > Camera > Enable
4. Reboot: `sudo reboot`

### Senaryo 3: Kedi Görüş Alanında Değil
**Çözüm:**
1. Kamera açısını ayarlayın
2. Kedi inkübatörde mi kontrol edin
3. Işık koşullarını iyileştirin

### Senaryo 4: Frame Üretilmiyor
**Çözüm:**
1. Loglarda `vision_running` değerini kontrol edin
2. `camera_type` değerini kontrol edin (`picamera2` veya `opencv`)
3. AI'ı disable edip tekrar enable edin

## Veritabanı Kontrolü

```bash
# Kayıt sayısı
sqlite3 data/ai_vitals.db "SELECT COUNT(*) FROM ai_vital_readings;"

# Son 10 kayıt
sqlite3 data/ai_vitals.db "SELECT timestamp, patient_name, status, respiration_bpm FROM ai_vital_readings ORDER BY timestamp DESC LIMIT 10;"

# Durum dağılımı
sqlite3 data/ai_vitals.db "SELECT status, COUNT(*) FROM ai_vital_readings GROUP BY status;"
```

## Beklenen AI Durumları

| Status | Açıklama |
|--------|----------|
| `OK` | Normal solunum ölçümü |
| `TOO_MUCH_MOTION` | Hayvan çok hareketli |
| `LOW_CONF` | Düşük güven (kamera net değil) |
| `NOT_ENOUGH_DATA` | Yetersiz veri |
| `UNAVAILABLE` | AI mevcut değil |

## İstatistikler

AI düzgün çalışıyorsa:
- Anlamlı değişimlerde vital snapshot kaydedilir
- Stabil ve güvenilir `OK` durumunda yaklaşık **3 dakikada bir** özet kayıt oluşur
- `LOW_CONF`, `TOO_MUCH_MOTION` ve benzeri güvenilmez durumlar aynı kararsız izlem dönemi içinde gruplanabilir
- AI vital verileri yaklaşık **30 gün** tutulur; sistem periyodik bakım ile eski kayıtları temizler

## Yardım

Sorun devam ediyorsa:
1. `diagnose_ai_alerts.py` output'unu kaydedin
2. Son 100 satır web server log'unu kaydedin
3. Web UI console output'unu kaydedin
