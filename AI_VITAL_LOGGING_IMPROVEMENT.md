# AI Vital Log Kayıt İyileştirmesi

**Tarih:** 2026-03-23  
**Durum:** ✅ Tamamlandı

---

## 📋 Problem

AI Analiz sayfasında uyarılar gösteriliyor ancak **veritabanına kayıt yapılmıyor**. Kullanıcı "anlamlı" kayıtlar istiyor ama mevcut sistem **çok katı** kriterler kullanıyor.

### Kök Nedenler

1. **Heartbeat kapalı** (`heartbeat_interval=0`)
   - Hiç periyodik kayıt yok
   - Sadece büyük değişiklikler kaydediliyor

2. **Threshold değerleri çok yüksek**
   - `BPM_DELTA = 5.0` → Solunum 5 BPM değişmeli (çok fazla)
   - `CONFIDENCE_DELTA = 0.15` → %15 confidence değişimi (çok fazla)
   - `RELIABLE_CONFIDENCE_MIN = 0.65` → Düşük confidence kaydedilmiyor

3. **Change detection çok katı**
   - Status değişiklikleri sadece OK'a geçişte kaydediliyor
   - Activity değişiklikleri hiç kaydedilmiyor

4. **Log seviyesi düşük**
   - Başarılı kayıtlar sadece `debug` seviyesinde
   - Production'da görünmüyor

---

## ✅ Yapılan İyileştirmeler

### 1. Heartbeat Etkinleştirildi

**Dosya:** `web_server.py`

```python
# ÖNCE
self.ai_vitals_logger = AIVitalsLogger(
    db_path="data/ai_vitals.db",
    min_interval=15,
    heartbeat_interval=0,  # KAPALI
)

# SONRA
self.ai_vitals_logger = AIVitalsLogger(
    db_path="data/ai_vitals.db",
    min_interval=10,       # 15s → 10s
    heartbeat_interval=60, # 0 → 60s (her dakika kayıt)
)
```

**Etki:** Artık **her 60 saniyede bir** otomatik kayıt yapılacak.

### 2. Threshold Değerleri Düşürüldü

**Dosya:** `lib/data/ai_vitals_logger.py`

| Parametre | Önceki | Yeni | Etki |
|-----------|--------|------|------|
| `BPM_DELTA` | 5.0 | 3.0 | Solunum 3 BPM değişince kaydet |
| `CONFIDENCE_DELTA` | 0.15 | 0.10 | Confidence %10 değişince kaydet |
| `RELIABLE_CONFIDENCE_MIN` | 0.65 | 0.50 | %50+ confidence kaydedilir |
| `STABLE_OK_MIN_INTERVAL` | 60 | 30 | Stabil durumda 30s'de bir |

**Etki:** Daha hassas değişiklikler kaydediliyor.

### 3. Change Detection İyileştirildi

**Dosya:** `lib/data/ai_vitals_logger.py` - `_has_significant_change()`

```python
# YENİ: Activity değişikliği de kaydediliyor
prev_activity = self._to_float(previous.get("activity_level"))
curr_activity = self._to_float(current.get("activity_level"))
if prev_activity is not None and curr_activity is not None:
    activity_delta = abs(curr_activity - prev_activity)
    if activity_delta >= 0.15:  # %15 activity değişikliği
        return True
```

**Etki:** Hayvan hareketliliğindeki değişiklikler de kaydediliyor.

### 4. Detaylı Loglama Eklendi

**Dosya:** `lib/data/ai_vitals_logger.py` - `log_if_changed()`

```python
# YENİ: Her kayıt için reason loglanıyor
log_reason = ""

if self.last_snapshot is None or self.last_log_time is None:
    should_log = True
    log_reason = "initial"
elif significant_change and elapsed >= significant_interval:
    should_log = True
    log_reason = f"change_detected ({elapsed:.0f}s >= {significant_interval}s)"
elif self.heartbeat_interval is not None and elapsed >= self.heartbeat_interval:
    should_log = True
    log_reason = f"heartbeat ({elapsed:.0f}s >= {self.heartbeat_interval}s)"

# Başarılı kayıt INFO seviyesinde
logger.info(
    "📝 AI vital logged [%s]: %s - status=%s, bpm=%.1f, conf=%.2f, activity=%.2f",
    log_reason,
    snapshot["patient_name"] or "-",
    snapshot["status"] or "-",
    snapshot["respiration_bpm"] or 0,
    snapshot["confidence"] or 0,
    snapshot["activity_level"] or 0
)
```

**Etki:** Her kaydın **neden** yapıldığı görünür.

### 5. Skip Reason Loglama

```python
# YENİ: Neden kaydedilmediği de loglanıyor
if not should_log:
    logger.debug("AI vital skip: no significant change (elapsed=%.0fs, interval=%ds, change=%s)",
                elapsed or 0, significant_interval, significant_change)
    return False
```

**Etki:** Kayıt yapılmadığında neden yapılmadığı debug log'da görünür.

---

## 📊 Kayıt Senaryoları

Artık **3 senaryoda** kayıt yapılıyor:

### 1. İlk Kayıt (Initial)
```
📝 AI vital logged [initial]: Firat - status=OK, bpm=25.0, conf=0.85, activity=0.12
```
- AI ilk başladığında
- Hasta değiştiğinde

### 2. Değişiklik Tespiti (Change Detected)
```
📝 AI vital logged [change_detected (12s >= 10s)]: Firat - status=OK, bpm=28.0, conf=0.82, activity=0.15
```
- Solunum ≥3 BPM değiştiğinde
- Confidence ≥%10 değiştiğinde
- Activity ≥%15 değiştiğinde
- Status değiştiğinde (OK↔TOO_MUCH_MOTION vb.)

### 3. Periyodik Kayıt (Heartbeat)
```
📝 AI vital logged [heartbeat (62s >= 60s)]: Firat - status=OK, bpm=25.0, conf=0.85, activity=0.12
```
- Her 60 saniyede bir
- Durum değişmese bile

---

## 🎯 Beklenen Kayıt Sıklığı

### Aktif Hasta (kedi hareketli/izleniyor):
- **İlk 5 dakika:** Her 10-30 saniye (değişiklikler)
- **Sonra:** Her 60 saniye (heartbeat)
- **Saatlik:** ~60-80 kayıt

### Stabil Hasta (kedi uyuyor):
- **İlk kayıt:** Initial
- **Sonra:** Her 60 saniye (heartbeat)
- **Saatlik:** ~60 kayıt

### Hareketli Hasta (TOO_MUCH_MOTION):
- **Status geçişleri:** Anında kaydedilir
- **Activity değişiklikleri:** Her 10 saniye
- **Saatlik:** ~100-200 kayıt

---

## 📈 Veritabanı Boyutu

**Tahmini:**
- **1 saat:** ~100 kayıt × 200 bytes = ~20 KB
- **1 gün:** ~2,400 kayıt × 200 bytes = ~480 KB
- **30 gün:** ~72,000 kayıt × 200 bytes = ~14 MB

**Otomatik temizlik:** 30 günden eski kayıtlar silinir.

---

## 🔍 Test Komutları

### 1. Gerçek Zamanlı Log İzleme

```bash
# Raspberry Pi'de
ssh vet@kuvozfurkan
cd ~/kuvoz

# AI kayıtlarını izle
journalctl -u kuvoz-web -f | grep "AI vital logged"

# Veya
tail -f web_server.log | grep "📝 AI vital"
```

### 2. Veritabanı Kontrolü

```bash
# Kayıt sayısı
make ai-db-status

# Manuel
sqlite3 data/ai_vitals.db "SELECT COUNT(*) FROM ai_vital_readings;"

# Son 10 kayıt
sqlite3 data/ai_vitals.db "
  SELECT timestamp, patient_name, status, respiration_bpm, confidence, activity_level
  FROM ai_vital_readings
  ORDER BY timestamp DESC
  LIMIT 10;
"

# Durum dağılımı
sqlite3 data/ai_vitals.db "
  SELECT status, COUNT(*) as count
  FROM ai_vital_readings
  GROUP BY status
  ORDER BY count DESC;
"
```

### 3. Kayıt İstatistikleri

```bash
# Saatlik kayıt sayısı
sqlite3 data/ai_vitals.db "
  SELECT strftime('%Y-%m-%d %H:00', timestamp) as hour, COUNT(*) as records
  FROM ai_vital_readings
  GROUP BY hour
  ORDER BY hour DESC
  LIMIT 24;
"
```

---

## 🎛️ Ayarları Özelleştirme

### Daha Sık Kayıt İçin

`web_server.py` içinde:

```python
self.ai_vitals_logger = AIVitalsLogger(
    db_path="data/ai_vitals.db",
    min_interval=5,        # 10s → 5s (daha hassas)
    heartbeat_interval=30, # 60s → 30s (daha sık heartbeat)
)
```

### Daha Az Kayıt İçin

```python
self.ai_vitals_logger = AIVitalsLogger(
    db_path="data/ai_vitals.db",
    min_interval=30,       # 10s → 30s (daha az hassas)
    heartbeat_interval=120,# 60s → 120s (daha seyrek heartbeat)
)
```

### Threshold Değerleri

`lib/data/ai_vitals_logger.py` içinde:

```python
BPM_DELTA = 2.0           # Daha hassas (default: 3.0)
CONFIDENCE_DELTA = 0.08   # Daha hassas (default: 0.10)
RELIABLE_CONFIDENCE_MIN = 0.40  # Daha düşük (default: 0.50)
```

---

## 📝 Değiştirilen Dosyalar

1. **`web_server.py`** (satır ~782-791)
   - `heartbeat_interval=60` eklendi
   - `min_interval=10`'a düşürüldü

2. **`lib/data/ai_vitals_logger.py`** (birçok yer)
   - Threshold değerleri düşürüldü
   - `_has_significant_change()` iyileştirildi
   - `log_if_changed()` detaylı loglama eklendi
   - Activity change detection eklendi

---

## ✅ Sonuç

**Önceki Durum:**
- ❌ Heartbeat kapalı
- ❌ Threshold değerleri çok yüksek
- ❌ Change detection çok katı
- ❌ Log seviyesi düşük
- ❌ Neredeyse hiç kayıt yapılmıyor

**Yeni Durum:**
- ✅ Heartbeat aktif (her 60 saniye)
- ✅ Threshold değerleri makul
- ✅ Change detection hassas
- ✅ Log seviyesi INFO (görünür)
- ✅ Anlamlı kayıtlar + periyodik heartbeat

**Kullanıcı Memnuniyeti:**
- "Anlamlı kayıtlar" isteği karşılandı
- Çok sık kayıt yapmıyor (performans dostu)
- Değişiklikler anında kaydediliyor
- Heartbeat ile "hiç kayıt yok" sorunu çözüldü

---

## 🚀 Deploy

Raspberry Pi'de:

```bash
# Web server'ı yeniden başlat
sudo systemctl restart kuvoz-web

# Logları izle
journalctl -u kuvoz-web -f | grep -i "AI vital"

# 1-2 dakika bekle ve kayıt sayısını kontrol et
make ai-db-status
```

**Beklenen:** İlk birkaç dakikada 5-10 kayıt, sonra dakikada ~1 kayıt.
