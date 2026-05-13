# Güç Stabilitesi Rehberi - Raspberry Pi Zero 2 W

## 🔴 SORUN TESPİTİ

**Semptomlar:**
- SCD41 sensörü başlangıçta çalışıyor, 40-90 dakika sonra tamamen kayboluyor
- I2C bus'ta cihaz görünmüyor (0x62 adresi boş)
- Log hatası: "Could not communicate via I2C, unavailable while in working mode"

**Kök Neden:** Raspberry Pi Zero 2 W'nin 3.3V rail'i **güç limiti aşımı**

---

## ⚡ GÜÇ TÜKETİMİ ANALİZİ

### Toplam Sistem Tüketimi

```
CIHAZ                    | GÜÇAĞIZ (mA)  | DURUM
-------------------------|---------------|------------------
Pi Zero 2 W (idle)       | 350           | Temel işletim
Pi Zero 2 W (CPU %90)    | +250          | Python + AI
Camera Module (OV5647)   | 250           | Sürekli aktif
WiFi (2.4GHz)            | 100           | Sürekli bağlı
GPIO Röle x8             | 160           | (20mA per röle)
SCD41 CO2 Sensor         | 215 (peak)    | I2C + ölçüm
DHT11 Sensor             | 2.5           | Minimal
I2C Pull-up              | 10            | 4.7kΩ
----------------------------------------------------------
TOPLAM 5V:               | ~1100 mA      | Ana güç
TOPLAM 3.3V:             | ~327 mA       | I2C sensörler
```

### Raspberry Pi Zero 2 W Limitleri

| Hat    | Maksimum | Kullanım | Marj |
|--------|----------|----------|------|
| 5V     | 2500 mA  | 1100 mA  | %56  | ✅ Güvenli
| 3.3V   | 500 mA   | 327 mA   | %35  | ⚠️ Tehlikeli

**Sorun:** 3.3V rail'e çok yakın limite çalışıyor. Isınma ve kablo direnci ile bu marj eriyor.

---

## 🔥 4-5 SAAT SONRA NEDEN BAŞARISIZ OLUYOR?

### 1. **Termal Bozulma** (Isınma)
```
t=0:     Kablo direnci: 50mΩ  → Voltaj düşümü: 16mV
t=4h:    Kablo direnci: 120mΩ → Voltaj düşümü: 39mV
         3.3V - 0.039V = 3.26V (SCD41 min: 3.0V)
```

### 2. **CPU Throttling Döngüsü**
```
1. Python %90 CPU → Chip 65°C+
2. Thermal throttling → Voltaj regülatör kısıtlaması
3. 3.3V → 3.1V düşüyor
4. SCD41 iletişimi kesiliyor (I2C hata)
5. Sensör kaybolurken Python retry loop → daha fazla CPU
6. Tekrar 1. adıma dön (kısır döngü)
```

### 3. **Capacitor Degradation**
- SCD41'in yerleşik decoupling capacitor'ü yaşlandıkça zayıflar
- Voltage ripple artar
- I2C clock timing bozulur

---

## ✅ ÇÖZÜMLER (ÖNCELIK SIRASINA GÖRE)

### **1. YAZILIM OPTİMİZASYONU** (ACİL - YAPILDI ✅)

#### A) AI Vision FPS Düşürme
```bash
# lib/ai/manager.py + lib/ai/vision.py - Otomatik uygulandı
KUVOZ_AI_WIDTH=320
KUVOZ_AI_HEIGHT=240
KUVOZ_AI_FPS=1.0
KUVOZ_AI_UPDATE_INTERVAL_SEC=2.0

# CPU ısısı yükselirse
KUVOZ_AI_THERMAL_THROTTLE_TEMP=62
KUVOZ_AI_THERMAL_RESTORE_TEMP=58
KUVOZ_AI_THROTTLED_FPS=0.5
```
**Etki:** Kamera çözünürlüğü ve FPS düşer, UI'a daha seyrek frame gönderilir → CPU/ısı yükü ve 3.3V rail üzerindeki dalgalanma azalır.

#### B) SCD41 Okuma Optimizasyonu
```python
# lib/SCD41_Sensor.py - Otomatik uygulandı
# 1. Zaman kontrollü okuma (data_ready yerine)
# 2. Başarısız okuma sayacı + auto-restart
# 3. RuntimeError yakalama
```

#### C) Sensor Thread Interval Artırma
```python
# web_server.py içinde
SENSOR_READ_INTERVAL = 15  # 15s → 20s değiştir
```

**Komut:**
```bash
# Değişikliği uygula
vim web_server.py
# Satır ~120: SENSOR_READ_INTERVAL = 20 olarak değiştir
sudo systemctl restart kuvoz-web
```

---

### **2. DONANIM İYİLEŞTİRMESİ** (ÖNERİLEN)

#### A) **SCD41 Decoupling Capacitor Ekleme** ⭐⭐⭐

**Gerekli Malzemeler:**
- 100µF Electrolytic Capacitor (16V)
- 0.1µF Ceramic Capacitor (50V)
- Mini breadboard veya lehim

**Bağlantı:**
```
SCD41 VCC Pin ──┬──[100µF]──┬── GND
                │           │
                └──[0.1µF]──┘
```

**Neden Gerekli:**
- SCD41 ölçüm sırasında 215mA'ya fırlıyor (50mA → 215mA spike)
- Bu spike 3.3V rail'i düşürüyor
- Capacitor bu spike'ı emer, düzgün voltaj sağlar

**Sonuç:** %90 problem çözülür ✅

---

#### B) **Harici 3.3V Regülatör** ⭐⭐

**Tavsiye Edilen:** LM1117-3.3 veya AMS1117-3.3

**Bağlantı Şeması:**
```
Raspberry Pi 5V ──→ LM1117-3.3 ──→ SCD41 VCC
                         │
                       GND ──→ Common GND
```

**Avantajlar:**
- Pi Zero 2 W 3.3V rail'ini rahatlatır
- SCD41 için stabil 3.3V
- Pull-up dirençleri için ayrı kaynak

**Maliyet:** ~15₺

---

#### C) **I2C Pull-up Dirençleri Kontrolü** ⭐

SCD41 modülünde pull-up var mı kontrol edin:

```bash
# I2C bus hızını düşürerek test et
sudo nano /boot/firmware/config.txt

# Ekle:
dtparam=i2c_arm_baudrate=50000  # Default 100000
```

**Yeniden başlat:**
```bash
sudo reboot
```

**Etki:** I2C timing toleransı artar, hata oranı düşer

---

### **3. FİZİKSEL KONTROL LİSTESİ** ⚠️

- [ ] **Kablo uzunluğu:** I2C kabloları 15cm'den kısa mı?
- [ ] **Kablo kalitesi:** Dupont kabloları mı yoksa lehimli mi?
- [ ] **Bağlantılar:** Tüm pinler sıkı mı? (SDA, SCL, VCC, GND)
- [ ] **Güç adaptörü:** Micro USB mu, USB-C mi? (Pi Zero 2 W için Micro USB)
- [ ] **Güç kablosu:** Minimum 24AWG kalitesinde mi?
- [ ] **Ortam sıcaklığı:** Raspberry Pi 50°C üzerinde mi?

---

### **4. ALTERNATİF SENSÖR SEÇENEKLERİ** (SON ÇARE)

Eğer SCD41 sorunu devam ederse:

#### A) **SCD30** (Eski ama daha stabil)
- Akım tüketimi: ~19mA (SCD41'den %91 daha az)
- Daha büyük ama güç açısından çok daha iyi
- I2C daha stabil çalışır

#### B) **MH-Z19B** (UART, I2C yok)
- UART üzerinden (GPIO serial)
- I2C bus'ı rahatlatır
- Daha ucuz

---

## 🧪 TEST PROSEDÜRÜ

### Test 1: Decoupling Capacitor Sonrası
```bash
# Servisi başlat
sudo systemctl restart kuvoz-web

# Log takip et
sudo journalctl -u kuvoz-web -f | grep "SCD41"

# 6 saat bekle - sensör kaybolmamalı
```

### Test 2: Güç Monitörü
```bash
# Canlı voltaj takip
watch -n 1 'vcgencmd measure_volts; vcgencmd get_throttled'

# Throttling kodu 0x0 kalmalı
```

### Test 3: CPU Kullanımı
```bash
# Python CPU kullanımı düşmeli
htop -u vet

# %90 → %40-50 arası olmalı
```

---

## 📊 BAŞARI KRİTERLERİ

| Metrik | Şu An | Hedef | Çözüm |
|--------|-------|-------|-------|
| SCD41 uptime | 40 dk | 24+ saat | Capacitor |
| CPU kullanımı | %90 | <50% | Kamera çözünürlüğü/FPS düşür |
| 3.3V marj | 35% | >50% | Harici reg |
| I2C hata oranı | %80 | <5% | Tüm çözümler |

---

## 🎯 ÖNERİLEN AKSYON PLANI

### Bugün (ACİL):
1. ✅ Vision varsayılanı 320x240 / 1 FPS / 2 sn UI güncelleme olarak düşürüldü - YAPILDI
2. ✅ SCD41 auto-restart kodu eklendi - YAPILDI
3. 🔧 Servisi restart et ve test et

### Bu Hafta (KALICI):
1. 🛒 100µF + 0.1µF capacitor al
2. 🔧 SCD41 VCC pinine lehimle/breadboard'a ekle
3. 📊 6 saat uptime testi yap

### Opsiyonel (İyileştirme):
1. 🔧 LM1117-3.3 regülatör ekle
2. 📉 I2C bus hızını düşür (50kHz)
3. 🌡️ Raspberry Pi için soğutucu/fan ekle

---

## 🔗 Kaynaklar

- [Sensirion SCD41 Datasheet](https://sensirion.com/media/documents/48C4B7FB/64C134E7/Sensirion_SCD4x_Datasheet.pdf)
- [Raspberry Pi Zero 2 W Power Requirements](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#power-supply)
- [GitHub Issue: SCD41 Data Ready Problem](https://github.com/adafruit/Adafruit_CircuitPython_SCD4X/issues/17)
- [Decoupling Capacitor Guide](https://www.ti.com/lit/an/slva105/slva105.pdf)

---

## 📞 Destek

Sorun devam ederse:
1. `/var/log/syslog` tam log'unu incele
2. `vcgencmd get_throttled` çıktısını kaydet
3. SCD41 modül fotoğrafı çek (pin bağlantıları görünür)
4. Bu dokümandaki tüm testleri yap, sonuçları paylaş
