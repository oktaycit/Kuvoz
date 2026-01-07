# SCD30 CO2 Sensör Troubleshooting

## Sorun: "Veri henüz hazır değil" Hatası

### Neden
Yeni SCD30 sensör versiyonları:
- İlk ölçüm için **15-20 saniye** bekleme gerektirir (eski versiyon: 2-3 saniye)
- Measurement interval 5 saniye kullanıyor (2 saniye çok kısa)
- `get_data_ready()` bazı versiyonlarda düzgün çalışmayabilir
- İlk 1-2 okuma genelde geçersiz (sensor warm-up)

### Çözüm (✅ Uygulandı)

#### 1. Test Script Güncellemeleri (`test_scd30_sensor.py`)
```python
# ✅ Soft reset eklendi
scd30.soft_reset()
time.sleep(0.5)

# ✅ Measurement interval ayarlandı (5 saniye)
scd30.set_measurement_interval(5)

# ✅ Auto-calibration kapatıldı (daha tutarlı okumalar)
scd30.deactivate_automatic_self_calibration()

# ✅ Warm-up süresi artırıldı (20 saniye)
warmup_time = 20
time.sleep(warmup_time)

# ✅ Okuma denemeleri artırıldı (10)
max_attempts = 10

# ✅ get_data_ready() hatası olsa bile okuma yapılıyor
try:
    ready = scd30.get_data_ready()
except:
    ready = True  # 3. denemeden sonra zorla oku

# ✅ Okumalar arası bekleme ayarlandı (6 saniye)
time.sleep(6)  # Measurement interval + buffer
```

#### 2. Web Server Güncellemeleri (`web_server.py`)
```python
# ✅ Sensör başlatma iyileştirildi
try:
    self.co2_sensor.soft_reset()
    self.co2_sensor.set_measurement_interval(5)  # 5 saniye
    self.co2_sensor.deactivate_automatic_self_calibration()
    self.co2_sensor.start_periodic_measurement(0)
except Exception as e:
    logger.warning(f"Config warning: {e}")  # Hata göster ama devam et

# ✅ get_data_ready() hatası yakalanıyor
try:
    ready = self.co2_sensor.get_data_ready()
except Exception as ready_err:
    # Bazı versiyonlarda get_data_ready() çalışmayabilir
    if self._scd30_warmup_reads >= 2:
        ready = True  # Warm-up tamamsa okumayı dene

# ✅ İlk 2 okuma atlanıyor (warm-up)
if self._scd30_warmup_reads < 2:
    self._scd30_warmup_reads += 1
    self.co2_sensor.read_measurement_data()  # Buffer'ı temizle
    # Bu okumayı kullanma
```

### Test Etme

#### Raspberry Pi'de Test
```bash
# SSH ile bağlan
ssh oktay@192.168.1.196

# Test script'i çalıştır
cd ~/kuvoz
python3 test_scd30_sensor.py
```

**Beklenen Çıktı:**
```
🧪 SCD30 CO2 Sensörü Test Ediliyor...
✅ SCD30 kütüphaneleri import edildi
✅ Soft reset yapıldı
✅ Measurement interval: 5 saniye
✅ Auto-calibration kapatıldı (veya uyarı mesajı)
✅ SCD30 sensörü başlatıldı

⏳ Sensör ısınıyor (measurement interval: 5s)...
   → 20 saniye bekleniyor...
   → Sensör durumu kontrol ediliyor...
   → get_data_ready() = True (veya False)

✅ Şimdi gerçek ölçümler başlıyor...

🔍 Ölçüm 1/10:
   CO2: 456 ppm ✅
   Sıcaklık: 23.5 °C ✅
   Nem: 45.2 % ✅

🎉 SONUÇ: SCD30 ÇALIŞIYOR VE GEÇERLİ DEĞERLER VERİYOR
```

**Not:** Eğer ilk 3-4 denemede "Veri henüz hazır değil" görürseniz, 3. denemeden sonra zorla okuma yapılacak.

#### Web Server'da Test
```bash
# Web server'ı başlat
make web-dev

# Log'larda şunları göreceksiniz:
# ✅ CO2 (SCD30) sensor initialized (5s interval, no auto-cal)
# 🔄 SCD30 warm-up read 1/2 (skipping...)
# 🔄 SCD30 warm-up read 2/2 (skipping...)
# 🌡️ CO2: 456 ppm (OK)
```

## Diğer Yaygın Sorunlar

### I2C Bağlantı Hatası
```bash
# I2C cihazlarını kontrol et
sudo i2cdetect -y 1

# SCD30 0x61 adresinde görünmeli:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 60: -- 61 -- -- -- -- -- -- -- -- -- -- -- -- -- --
```

**Çözüm:** Kabloları kontrol et (SDA=Pin 3, SCL=Pin 5, VCC=3.3V, GND)

### Çok Yüksek CO2 Değerleri (>5000 ppm)
- Sensör kalibrasyonu gerekebilir
- Dış mekanda (400 ppm) 20 dakika bekletin
- Manuel kalibrasyon: `scd30.set_forced_recalibration_value(400)`

### Negatif Sıcaklık/Nem Değerleri
- Sensör resetleyin: Güç kes/ver
- Script'i yeniden çalıştırın
- İlk 2 okuma otomatik atlanıyor

## Donanım Özellikleri (Modül Bilgileri)

Görseldeki SCD30 modül bilgileri:
```
CO2 Measurement Range: 400-10,000 ppm
CO2 Accuracy: ±(30 ppm + 3%)
Temperature: ±0.5°C @ 25°C (-10°C ~ 60°C)
Humidity: ±3% RH
I2C Address: 0x61
```

## Referanslar

- **Ana Dokümantasyon:** [README_SCD30.md](README_SCD30.md)
- **CO2-O2 Tahmini:** [CO2_TO_O2_ESTIMATION.md](CO2_TO_O2_ESTIMATION.md)
- **Test Script:** [test_scd30_sensor.py](test_scd30_sensor.py)
- **Web Server Entegrasyonu:** [web_server.py](web_server.py#L344-L400)

## Güncelleme Tarihi
2 Ocak 2026 - Yeni SCD30 sensör versiyonu için iyileştirmeler
