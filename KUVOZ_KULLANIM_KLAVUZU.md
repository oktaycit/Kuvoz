# Kuvoz Veteriner Rehabilitasyon Ünitesi - Kullanım Kılavuzu

**Versiyon:** 3.0 - Veteriner Web Interface Edition  
**Platform:** Raspberry Pi OS Trixie (Debian 13.1)  
**Tarih:** 27 Ekim 2025  
**Geliştirici:** Oktay Çit (@oktaycit)  
**Kullanım Alanı:** Veteriner Kliniği - Kedi/Köpek Rehabilitasyon ve Bakım Ünitesi

---

## 📋 İçindekiler

1. [Genel Bakış](#-genel-bakış)
2. [Sistem Gereksinimleri](#-sistem-gereksinimleri)
3. [Hızlı Başlangıç](#-hızlı-başlangıç)
4. [Kurulum ve Yapılandırma](#-kurulum-ve-yapılandırma)
5. [Web Arayüzü Kullanımı](#-web-arayüzü-kullanımı)
6. [Sensör Sistemi](#-sensör-sistemi)
7. [Kontrol Mantığı](#-kontrol-mantığı)
8. [Otomatik Sistem](#-otomatik-sistem)
9. [Kiosk Modu](#-kiosk-modu)
10. [Sorun Giderme](#-sorun-giderme)
11. [Bakım ve Güncellemeler](#-bakım-ve-güncellemeler)
12. [Teknik Referans](#-teknik-referans)

---

## 🎯 Genel Bakış

Kuvoz Veteriner Rehabilitasyon Ünitesi, Raspberry Pi tabanlı modern bir veteriner bakım ve iyileşme kontrol sistemidir. Kedi, köpek ve küçük hayvanların post-operatif bakımı, rehabilitasyon süreçleri ve iyileşme dönemlerinde optimal çevre koşulları sağlar. Web tabanlı arayüzü sayesinde veteriner hekimler hem yerel hem de uzaktan hasta takibi yapabilir.

### 🌟 Veteriner Kliniği Ana Özellikler

- ✅ **Modern Web Arayüzü**: Veteriner hekimler için responsive tasarım
- ✅ **Real-time Hasta İzleme**: WebSocket ile anlık vital parametre takibi
- ✅ **8 Kanal Tıbbi Cihaz Kontrolü**: Isıtma, havalandırma, nebulizer, UV sterilizasyon
- ✅ **Çoklu Sensör Desteği**: Sıcaklık/nem/oksijen monitoring
- ✅ **Kiosk Modu**: Veteriner teknisyenler için dokunmatik arayüz
- ✅ **Otomatik Bakım Sistemleri**: Termoregülasyon, nem kontrolü, sterilizasyon
- ✅ **Uzaktan Veteriner Takibi**: Ağ üzerinden hasta monitörizasyonu
- ✅ **Hasta Profil Ayarları**: Türe özel konfigürasyonlar (kedi/köpek)

### 🔄 Veteriner Kliniği İçin Teknoloji Geçişi

| Özellik | Eski Sistem (Kivy) | Yeni Sistem (Web) |
|---------|-------------------|-------------------|
| **Erişim** | ❌ Sadece lokal terminal | ✅ Veteriner ofisinden uzaktan erişim |
| **Hasta Takibi** | ❌ Yerinde kontrol | ✅ 7/24 uzaktan monitörizasyon |
| **Mobile Uyumlu** | ❌ Tablet/telefon desteği yok | ✅ Veteriner hekim mobil erişimi |
| **Performans** | ⚠️ Tekli hasta takibi | ✅ Çoklu ünite yönetimi |
| **Güncellemeler** | ❌ Manuel müdahale | ✅ Otomatik sistem güncellemeleri |
| **Kurulum** | ❌ Teknik bilgi gerekli | ✅ Veteriner dostu otomatik kurulum |

---

## 💻 Sistem Gereksinimleri

### Veteriner Kliniği Donanım Gereksinimleri

| Bileşen | Minimum | Önerilen | Veteriner Kullanım |
|---------|---------|----------|-------------------|
| **Raspberry Pi** | Pi 3B+ | Pi 4B (4GB) | 7/24 güvenilir hasta takibi |
| **SD Kart** | 16GB Class 10 | 32GB Class 10 | Hasta verisi kayıt kapasitesi |
| **RAM** | 1GB | 2GB+ | Çoklu hasta monitoring |
| **GPIO Erişimi** | ✅ Gerekli | ✅ Gerekli | Tıbbi cihaz kontrolü |
| **I2C Desteği** | ✅ Gerekli | ✅ Gerekli | Oksijen monitör bağlantısı |
| **Ekran** | 7" | 10"+ Dokunmatik | Veteriner teknisyen arayüzü |
| **Network** | WiFi/Ethernet | Gigabit Ethernet | Veteriner ofis bağlantısı |

### Yazılım Gereksinimleri

```bash
# İşletim Sistemi
Raspberry Pi OS Trixie (Debian 13.1) - ÖNERİLEN
Raspberry Pi OS Bullseye (Debian 11) - Destekleniyor
Ubuntu 22.04+ ARM64 - Test edildi

# Python Sürümü
Python 3.9+ (Sistem Python öneriliyor)

# Web Browser
Chromium Browser (Kiosk modu için)
Firefox ESR (Alternatif)
```

### Veteriner Ünitesi GPIO Pin Konfigürasyonu

```python
# Tıbbi Cihaz Kontrol Kanalları (8 Kanal Veteriner Ekipmanı)
outChannels = [5, 6, 13, 16, 19, 20, 21, 26]
# Pin  | Fiziksel Pin | Veteriner Fonksiyonu
# -----|-------------|---------------------
# GP5  | Pin 29      | b1: Therapeutic Lighting (Terapi Işığı)
# GP6  | Pin 31      | b2: Nebulizer (Solunum Terapi Cihazı)
# GP13 | Pin 33      | b3: Humidity Control (Nem Kontrolü)
# GP16 | Pin 36      | b4: Heating Pad (Isıtma Yatağı)
# GP19 | Pin 35      | b5: IR Heater (Kızılötesi Isıtıcı)
# GP20 | Pin 38      | b6: Ventilation Fan (Havalandırma Fanı)
# GP21 | Pin 40      | b7: UV Sterilization (UV Sterilizasyon)
# GP26 | Pin 37      | b8: Ozone Sterilizer (Ozon Sterilizatörü)

# Monitoring Sensör Pinleri
pinDht = 15         # GPIO 15 (Fiziksel Pin 10) - Sıcaklık/Nem Monitörü
# I2C: SDA=GPIO2 (Pin 3), SCL=GPIO3 (Pin 5) - Oksijen Saturasyon Monitörü
```

---

## ⚡ Hızlı Başlangıç

### 1. Tek Komutla Kurulum

```bash
# Repository'yi klonlayın
git clone https://github.com/oktaycit/Kuvoz.git
cd Kuvoz

# TAM OTOMATİK KURULUM VE BAŞLATMA
make auto-setup
```

Bu komut aşağıdakileri otomatik yapar:
- ✅ Web server bağımlılıklarını kurar
- ✅ Systemd servislerini oluşturur
- ✅ Web server'ı başlatır
- ✅ Kiosk modunu etkinleştirir
- ✅ Otomatik başlatmayı ayarlar

### 2. Erişim Bilgileri

```bash
# Kurulum tamamlandıktan sonra:
Yerel Erişim: http://localhost:5000
Ağ Erişimi: http://[raspberry-pi-ip]:5000

# IP adresini öğrenmek için:
hostname -I
```

### 3. Veteriner İlk Kullanım

1. **Web tarayıcısında** http://localhost:5000 adresine gidin
2. **Hasta monitoring verilerinin** (sıcaklık/nem/oksijen) geldiğini kontrol edin
3. **Tıbbi cihaz butonlarını** (ısıtma, havalandırma, nebulizer) test edin
4. **Hasta türüne göre ayarları** (kedi/köpek) düzenleyin
5. **Hasta profili kaydet** butonuna basarak protokolü aktifleştirin

---

## 🔧 Kurulum ve Yapılandırma

### Manuel Kurulum Adımları

#### 1. Sistem Bağımlılıkları

```bash
# Sistem paketlerini güncelleyin
sudo apt update && sudo apt upgrade -y

# Python ve gerekli araçları kurun
sudo apt install -y python3 python3-pip python3-dev
sudo apt install -y i2c-tools build-essential
sudo apt install -y chromium-browser  # Kiosk modu için
```

#### 2. Python Bağımlılıkları

```bash
# Web server için gerekli paketler
pip3 install flask flask-socketio --break-system-packages

# Alternatif: Sistem paketleri (önerilen)
sudo apt install -y python3-flask python3-flask-socketio
```

#### 3. GPIO ve I2C Yapılandırması

```bash
# GPIO grubu ekleyin
sudo usermod -a -G gpio $USER

# I2C'yi etkinleştirin
sudo raspi-config
# → Interface Options → I2C → Enable

# Değişikliklerin etkili olması için yeniden başlatın
sudo reboot
```

#### 4. Servis Kurulumu

```bash
# Web server servisi
make web-service

# Kiosk modu servisi
make kiosk-service

# Servis durumlarını kontrol edin
make status-all
```

### Yapılandırma Dosyaları

#### `Failure.dat` - Ayar Dosyası

```python
# Ana ayar dosyası (JSON formatı)
{
    "slider_values": {
        "sld1": 30,    # Nebulizer interval (dakika)
        "sld2": 65,    # Humidity target (%)
        "sld3": 25.0,  # Temperature target (°C)
        "sld4": 25.0,  # IR Temperature target (°C)
        "sld5": 30,    # Ozone interval (dakika)
        "sld6": 12,    # Nebulizer hours interval (saat)
        "sld7": 8.0    # Ozone hours interval (saat)
    },
    "button_states": {
        "b1": false,   # Lighting
        "b2": false,   # Nebulizer
        "b3": false,   # Humidity
        "b4": false,   # Carbon Temperature
        "b5": false,   # IR Temperature
        "b6": false,   # Fan
        "b7": false,   # UV Lighting
        "b8": false    # Ozone
    }
}
```

---

## 🌐 Web Arayüzü Kullanımı

### Ana Sayfa Bileşenleri

#### 1. Veteriner Kontrol Üst Bar

- **Bağlantı Durumu**: Hasta monitoring sistem bağlantı göstergesi
- **Tarih/Saat**: Veteriner kayıt zamanı
- **Sistem Başlığı**: Kuvoz Veteriner Rehabilitasyon Ünitesi logosu

#### 2. Hasta Monitoring Paneli

```javascript
// Hasta vital parametreleri dinamik olarak görünür
Vital Parametre | Gösterim | Veteriner Durum
----------------|----------|---------------
Temperature     | 38.5°C   | ✅ Normal (Köpek: 38-39°C)
Humidity        | 60.0%    | ✅ Optimal (50-70%)
Oxygen          | 95.2%    | ✅ İyi Saturasyon (>94%)
```

**Veteriner Renk Kodları:**

- 🟢 **Yeşil**: Hasta stabil, vital parametreler normal
- 🟡 **Sarı**: Veteriner dikkat gerektiren seviye
- 🔴 **Kırmızı**: Acil veteriner müdahale gerekli
- ⚫ **Gri**: Sensör hatası/hasta monitoring kesintisi

#### 3. Kontrol Paneli

##### Veteriner Tıbbi Cihaz Butonları (8 Kanal)

| Buton | Pin | Veteriner Fonksiyon | Klinik Açıklama |
|-------|-----|-------------------|-----------------|
| **B1** | GP5 | Therapeutic Light | Terapi ışığı (sirkadiyen ritim düzenleme) |
| **B2** | GP6 | Nebulizer | Solunum terapi cihazı (bronkodilatör/mukolitik) |
| **B3** | GP13 | Humidity Control | Nem kontrolü (solunum yolu korunması) |  
| **B4** | GP16 | Heating Pad | Isıtma yatağı (hipotermi önleme) |
| **B5** | GP19 | IR Heater | Kızılötesi ısıtıcı (yumuşak ısı terapi) |
| **B6** | GP20 | Ventilation | Havalandırma fanı (oksijen sirkülasyonu) |
| **B7** | GP21 | UV Sterilizer | UV sterilizasyon (patogen kontrolü) |
| **B8** | GP26 | Ozone | Ozon sterilizasyon (ortam dezenfeksiyonu) |

##### Veteriner Hasta Protokol Kontrolleri (7 Kanal)

| Slider | Aralık | Varsayılan | Veteriner Protokol |
|--------|--------|------------|------------------|
| **SLD1** | 5-120 min | 30 min | Nebulizer terapi aralığı (solunum tedavisi) |
| **SLD2** | 40-80% | 60% | Hedef nem seviyesi (solunum konfor zonu) |
| **SLD3** | 35-42°C | 38°C | Hedef sıcaklık (köpek vücut sıcaklığı) |
| **SLD4** | 35-42°C | 37°C | IR hedef sıcaklık (kedi vücut sıcaklığı) |
| **SLD5** | 10-60 min | 45 min | Ozon sterilizasyon aralığı |
| **SLD6** | 2-12 saat | 6 saat | Nebulizer terapi seansı |
| **SLD7** | 4-24 saat | 12 saat | Sterilizasyon döngüsü |

#### 4. Sistem Kontrolleri

```html
<!-- Veteriner Sistem Butonları -->
<button id="saveSettings">💾 Hasta Profili Kaydet</button>
<button id="loadSettings">📂 Protokol Yükle</button>
<button id="emergencyStop">🚨 Acil Durdurma</button>
<button id="shutdown">🔌 Ünite Kapat</button>
<button id="restart">🔄 Sistem Yeniden Başlat</button>
```

### WebSocket İletişim Protokolü

#### Gelen Mesajlar (Veteriner Server → Client)

```javascript
// Hasta vital parametre güncellemesi  
{
  "type": "patient_vitals_update",
  "vitals": {
    "temperature": {"value": "38.5", "status": "Normal", "unit": "°C"},
    "humidity": {"value": "60.0", "status": "Optimal", "unit": "%"},
    "oxygen": {"value": "95.2", "status": "Good", "unit": "%"}  // Saturasyon
  }
}

// Veteriner cihaz durumu güncellemesi
{
  "type": "medical_device_update", 
  "devices": {
    "heating_pad": true,    // B4: Isıtma yatağı aktif
    "nebulizer": false,     // B2: Nebulizer kapalı
    "ventilation": true     // B6: Havalandırma açık
  }
}

// Veteriner sistem mesajı
{
  "type": "veterinary_alert",
  "message": "Hasta protokolü güncellendi - Köpek rehabilitasyon modu aktif",
  "level": "info",  // info, warning, critical
  "timestamp": "2025-10-27T14:30:00Z"
}
```

#### Giden Mesajlar (Client → Server)

```javascript
// Buton kontrolü
{
  "command": "toggle_button",
  "data": {
    "name": "b1",
    "pin": 5,
    "state": true
  }
}

// Slider güncellemesi
{
  "command": "update_slider", 
  "data": {
    "name": "sld1",
    "value": 45
  }
}

// Sistem komutu
{
  "command": "save_settings"
}
```

---

## 🌡️ Veteriner Monitoring Sensör Sistemi

### DHT22 Hasta Vital Parametre Sensörü (Sıcaklık & Nem)

#### Veteriner Teknik Özellikler

```python
# DHT22 Veteriner Monitoring Konfigürasyonu
pinDht = 15         # GPIO 15 (Physical Pin 10)
sensorDht = 22      # DHT22 medical grade sensor
read_interval = 15  # Hasta monitoring aralığı (saniye)

# Veteriner Ölçüm Aralıkları
Hasta Sıcaklığı: 35-42°C (±0.1°C hassasiyet - veteriner grade)
Ortam Nemi: 40-80% RH (±1% hassasiyet - hasta konforu)
Çözünürlük: 0.1°C sıcaklık, 0.1% nem (hasta takibi için yeterli)

# Veteriner Referans Değerleri
Köpek Normal Vücut Sıcaklığı: 38.0-39.2°C
Kedi Normal Vücut Sıcaklığı: 38.1-39.2°C
Optimal Ortam Nemi: 50-70% (solunum konforu)
```

#### Otomatik Sensör Algılama

```python
# DHT_Native kütüphanesi otomatik algılama yapar
from DHT_Native import read_retry

# DHT11 veya DHT22'yi otomatik algılar
humidity, temperature = read_retry(pin=15)

if humidity is not None:
    print(f"Sıcaklık: {temperature}°C")
    print(f"Nem: {humidity}%")
else:
    print("Sensör okunamadı")
```

#### Hata Yönetimi

```python
# 4 aşamalı fallback sistemi
1. DHT_Native.read_retry(retries=3, delay=2)
2. DHT_Native.read() - tek deneme
3. Son bilinen değerleri koruma
4. Simulasyon modu devreye girme

# Değer doğrulama
def validate_sensor_data(temp, hum):
    if temp is None or hum is None:
        return False
    if not (-40 <= temp <= 80):  # Sıcaklık aralığı
        return False
    if not (0 <= hum <= 100):    # Nem aralığı
        return False
    return True
```

### DFRobot Oksijen Saturasyon Monitörü

#### Veteriner Monitoring Özellikleri

```python
# I2C Veteriner Oksijen Monitör Konfigürasyonu
I2C_ADDRESS = 0x73  # Veteriner grade oksijen monitör adresi
bus_number = 1      # I2C bus 1 (medical device bus)
measurement_range = 80-100%  # Oksijen saturasyon yüzdesi (hasta güvenlik aralığı)

# Veteriner Oksijen Monitör Setup
from DFRobot_Oxygen import *
oxygen_monitor = DFRobot_Oxygen_IIC(IIC_MODE, ADDRESS_3)

# Veteriner Referans Değerleri
Normal Oksijen Saturasyonu: >94% (köpek/kedi)
Uyarı Seviyesi: 90-94% (veteriner dikkat gerekli)
Kritik Seviye: <90% (acil müdahale gerekli)
```

#### Kalibrasyon ve Kullanım

```python
# Otomatik kalibrasyon (havada ~20.9% O2)
def calibrate_oxygen_sensor():
    # 20.9% oksijen referansı ile kalibrasyon
    oxygen_sensor.calibrate(20.9, 20)  # 20°C referans sıcaklık
    print("Oksijen sensörü kalibre edildi")

# Okuma işlemi
def read_oxygen(temperature=20):
    try:
        oxygen_concentration = oxygen_sensor.get_oxygen_data(temperature)
        return round(oxygen_concentration, 1)
    except Exception as e:
        print(f"Oksijen sensör hatası: {e}")
        return None
```

#### Sensör Yokluğunda Davranış

```python
# Başlangıçta oksijen sensörü test edilir
def test_oxygen_sensor():
    try:
        oxygen_sensor = DFRobot_Oxygen_IIC(IIC_MODE, ADDRESS_3)
        test_value = oxygen_sensor.get_oxygen_data(20)
        return True
    except:
        return False

# Sensör yoksa:
# 1. Web arayüzünde oksijen kartı gizlenir
# 2. Ozon kontrolü başka mantıkla çalışır
# 3. Hata mesajı gösterilmez (normal durum)
```

---

## 🎛️ Veteriner Hasta Bakım Kontrol Mantığı

### Otomatik Solunum Terapi Sistemi

#### Veteriner Algoritması

```python
def veterinary_respiratory_care():
    """
    Veteriner solunum terapi kontrol algoritması
    Kedi/köpek post-operatif bakım protokolü
    """
    current_humidity = read_patient_environment()
    target_humidity = slider_values['sld2']  # SLD2: Hasta konfor nem %
    humidity_tolerance = 3  # ±3% tolerans (hassas hasta takibi)
    
    if current_humidity is not None:
        if current_humidity < (target_humidity - humidity_tolerance):
            # Düşük nem - solunum yolu kuruluğu riski
            gpio_control(6, True)   # B2: Nebulizer Therapy ON
            gpio_control(13, True)  # B3: Humidity Control ON
            veterinary_log("Solunum terapi başlatıldı - Hava yolu nemlendirilmesi")
            return "Nebulizer terapi aktif - hasta solunum desteği"
            
        elif current_humidity > (target_humidity + humidity_tolerance):
            # Yüksek nem - kondensasyon ve bakteriyel üreme riski
            gpio_control(6, False)  # B2: Nebulizer OFF
            gpio_control(20, True)  # B6: Ventilation Fan ON
            veterinary_log("Havalandırma başlatıldı - Nem kontrolü")
            return "Havalandırma aktif - ortam nem kontrolü"
            
        else:
            # Optimal nem seviyesi - hasta konforu
            veterinary_log("Optimal ortam koşulları - hasta stabil")
            return "Hasta ortam koşulları optimal"
    else:
        veterinary_alert("Nem sensörü hatası - manuel kontrol gerekli")
        return "UYARI: Ortam monitoring kesintisi"
```

#### Timing Kontrolü

```python
# Nebulizer döngü zamanlaması
nebulizer_interval = slider_values['sld1']  # SLD1: 5-120 dakika
nebulizer_hours_interval = slider_values['sld6']  # SLD6: 1-24 saat

def nebulizer_timing_control():
    current_time = time.time()
    
    # Kısa döngü kontrolü (dakika bazında)
    if (current_time - last_nebulizer_time) >= (nebulizer_interval * 60):
        # Nemlendiriciyi 5 dakika çalıştır
        activate_nebulizer(duration=300)  # 5 dakika = 300 saniye
        last_nebulizer_time = current_time
        
    # Uzun döngü kontrolü (saat bazında)
    if (current_time - last_nebulizer_hours) >= (nebulizer_hours_interval * 3600):
        # Yoğun nemlendirme 15 dakika
        activate_nebulizer(duration=900)  # 15 dakika = 900 saniye
        last_nebulizer_hours = current_time
```

### Veteriner Güvenli Sterilizasyon Sistemi

#### Akıllı Hasta Güvenlik Odaklı Ozon Kontrolü

```python
def veterinary_safe_sterilization():
    """
    Veteriner hasta güvenliği odaklı sterilizasyon kontrolü
    Kedi/köpek rehabilitasyon sürecinde güvenli sterilizasyon
    """
    oxygen_saturation = check_patient_oxygen_levels()
    patient_present = check_patient_presence()  # Hasta varlık sensörü
    
    if patient_present:
        # Hasta mevcut - güvenlik öncelikli sterilizasyon
        if oxygen_saturation is not None and oxygen_saturation > 94.0:
            # Güvenli oksijen saturasyonu - minimal ozon terapi
            veterinary_log("Hasta güvenli oksijen seviyesinde - sterilizasyon başlatılabilir")
            activate_patient_safe_sterilization()
        else:
            # Düşük oksijen saturasyonu - ozon sterilizasyon durdur
            deactivate_sterilization("Hasta oksijen saturasyonu düşük - güvenlik riski")
            veterinary_alert("ACİL: Hasta oksijen saturasyonu kritik seviyede")
            
    else:
        # Hasta yok - tam sterilizasyon modu
        veterinary_log("Hasta ünite boş - tam sterilizasyon protokolü aktif")
        activate_full_sterilization_protocol()

def activate_ozone_safe_mode():
    """
    Oksigen sensörü ile güvenli ozon modu
    """
    ozone_interval = slider_values['sld5']  # SLD5: 5-60 dakika
    current_time = time.time()
    
    if (current_time - last_ozone_time) >= (ozone_interval * 60):
        # Ozon 10 dakika çalışır, sonra 2 dakika bekler
        gpio_control(26, True)   # B8: Ozone ON
        time.sleep(600)          # 10 dakika çalış
        gpio_control(26, False)  # B8: Ozone OFF
        time.sleep(120)          # 2 dakika bekle
        
        last_ozone_time = current_time

def activate_ozone_timer_mode():
    """
    Oksijen sensörü olmadan zamanlama tabanlı ozon
    """
    ozone_hours_interval = slider_values['sld7']  # SLD7: 1-24 saat
    current_time = time.time()
    
    if (current_time - last_ozone_hours) >= (ozone_hours_interval * 3600):
        # Kısa süreli ozon (5 dakika)
        gpio_control(26, True)   # B8: Ozone ON
        time.sleep(300)          # 5 dakika çalış
        gpio_control(26, False)  # B8: Ozone OFF
        
        last_ozone_hours = current_time
```

### Veteriner Termoregülasyon Kontrolü

#### Hasta Vücut Sıcaklığı Yönetim Sistemi

```python
def veterinary_thermoregulation():
    """
    Veteriner hasta termoregülasyon algoritması
    Post-operatif hipotemi/hipertermi kontrolü
    """
    patient_temp = read_patient_temperature()
    patient_type = get_patient_profile()  # "dog" veya "cat"
    
    # Hasta türüne göre normal sıcaklık aralıkları
    if patient_type == "dog":
        normal_temp_min, normal_temp_max = 38.0, 39.2  # Köpek normal aralığı
        target_temp = slider_values['sld3']  # SLD3: Köpek hedef sıcaklık
    elif patient_type == "cat":
        normal_temp_min, normal_temp_max = 38.1, 39.2  # Kedi normal aralığı  
        target_temp = slider_values['sld4']  # SLD4: Kedi hedef sıcaklık
    else:
        normal_temp_min, normal_temp_max = 38.0, 39.2  # Varsayılan değerler
        target_temp = 38.5
    
    temp_tolerance = 0.3  # ±0.3°C hassas tolerans (veteriner grade)
    
    if patient_temp is not None:
        if patient_temp < (target_temp - temp_tolerance):
            # Hipotermi riski - nazik ısıtma protokolü
            gpio_control(16, True)  # B4: Heating Pad ON (yumuşak ısı)
            gpio_control(19, True)  # B5: IR Heater ON (kızılötesi terapi)
            veterinary_log(f"Hipotermi önleme aktif - Hasta sıcaklık: {patient_temp}°C")
            return f"Isıtma terapi aktif - Hasta hipotermisi önleniyor"
            
        elif patient_temp > (target_temp + temp_tolerance):
            # Hipertermi riski - aktif soğutma
            gpio_control(16, False) # B4: Heating Pad OFF
            gpio_control(19, False) # B5: IR Heater OFF
            gpio_control(20, True)  # B6: Ventilation Fan ON
            veterinary_alert(f"Hipertermi uyarısı - Hasta sıcaklık: {patient_temp}°C")
            return f"Soğutma sistemi aktif - Hipertermi kontrolü"
            
        else:
            # Hasta termoregülasyon normal
            veterinary_log(f"Hasta termoregülasyon stabil - {patient_temp}°C")
            return f"Hasta sıcaklık optimal ({patient_temp}°C) - {patient_type.upper()}"
    else:
        veterinary_alert("Hasta sıcaklık sensörü hatası - manuel kontrol gerekli")
        return "UYARI: Hasta termoregülasyon monitoring kesintisi"
```

---

## 🤖 Otomatik Sistem

### Thread Tabanlı Kontrol

```python
class AutomationSystem:
    def __init__(self):
        self.control_thread = None
        self.sensor_thread = None
        self.running = False
        
    def start_automation(self):
        """Otomatik sistemi başlat"""
        self.running = True
        
        # Sensör okuma thread'i (15 saniye aralık)
        self.sensor_thread = threading.Thread(
            target=self.sensor_loop, 
            daemon=True
        )
        self.sensor_thread.start()
        
        # Kontrol logic thread'i (5 saniye aralık)
        self.control_thread = threading.Thread(
            target=self.control_loop, 
            daemon=True
        )
        self.control_thread.start()
        
    def sensor_loop(self):
        """Sensör okuma döngüsü"""
        while self.running:
            # DHT22 sensör okuma
            temperature, humidity = read_sensors()
            
            # Oksijen sensör okuma (varsa)
            oxygen = read_oxygen() if oxygen_available else None
            
            # WebSocket ile client'lara gönder
            emit_sensor_data(temperature, humidity, oxygen)
            
            time.sleep(15)  # 15 saniye bekle
            
    def control_loop(self):
        """Kontrol logic döngüsü"""
        while self.running:
            if self.control_active:
                # Otomatik nem kontrolü
                humidity_status = automatic_humidity_control()
                
                # Otomatik sıcaklık kontrolü
                temperature_status = automatic_temperature_control()
                
                # Akıllı ozon kontrolü
                ozone_status = intelligent_ozone_control()
                
                # Timing kontrolü (nebulizer, ozon)
                timing_control()
                
            time.sleep(5)  # 5 saniye bekle
```

### Güvenlik Sistemi

```python
def safety_checks():
    """Güvenlik kontrolleri"""
    
    # Sıcaklık güvenlik kontrolü
    if current_temperature > 50:  # Kritik sıcaklık
        emergency_shutdown("Sıcaklık kritik seviyede!")
        
    # Nem güvenlik kontrolü  
    if current_humidity < 20:  # Çok düşük nem
        force_nebulizer_on("Kritik nem seviyesi!")
        
    # Oksijen güvenlik kontrolü
    if oxygen_available and current_oxygen < 16:  # Tehlikeli seviye
        emergency_ozone_off("Tehlikeli oksijen seviyesi!")
        
    # GPIO güvenlik kontrolü
    if gpio_error_count > 10:  # Çok fazla GPIO hatası
        gpio_reset("GPIO sistem hatası!")

def emergency_shutdown(reason):
    """Acil durum kapatma"""
    print(f"🚨 ACİL DURUM: {reason}")
    
    # Tüm ısıtıcıları kapat
    gpio_control(16, False)  # Carbon Temperature OFF
    gpio_control(19, False)  # IR Temperature OFF
    
    # Fanı aç
    gpio_control(20, True)   # Fan ON
    
    # Ozon kapat
    gpio_control(26, False)  # Ozone OFF
    
    # Kullanıcıya bildir
    emit_emergency_alert(reason)
```

---

## 🖥️ Kiosk Modu

### Tam Ekran Arayüz

Kiosk modu, Raspberry Pi'yi dokunmatik bir kontrol paneline dönüştürür.

#### Özellikler

- ✅ **Tam Ekran**: Menü çubuğu ve pencere kontrolleri gizli
- ✅ **Dokunmatik Uyumlu**: Büyük butonlar ve kolay navigasyon  
- ✅ **Otomatik Başlama**: Sistem boot'ta otomatik açılır
- ✅ **Crash Recovery**: Browser çökerse otomatik yeniden başlar
- ✅ **Mouse Gizleme**: İmleci otomatik gizler
- ✅ **Screensaver Devre Dışı**: Ekran sürekli açık kalır

#### Kurulum

```bash
# Kiosk servisini kur
make kiosk-service

# Manuel başlatma
make kiosk-start

# Otomatik başlatmayı etkinleştir
make kiosk-autostart

# Kiosk durumunu kontrol et
make kiosk-status
```

#### Kiosk Script'i

```bash
#!/bin/bash
# scripts/start-kiosk.sh

# Display ayarları
export DISPLAY=:0
export XAUTHORITY=/home/pi/.Xauthority

# Screensaver'ı devre dışı bırak
xset s off
xset -dpms
xset s noblank

# Mouse'u gizle
unclutter -idle 0.5 -root &

# Chromium kiosk modu
chromium-browser \
    --kiosk \
    --no-sandbox \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-restore-session-state \
    --disable-background-timer-throttling \
    --disable-backgrounding-occluded-windows \
    --disable-renderer-backgrounding \
    --disable-features=TranslateUI \
    --disable-ipc-flooding-protection \
    --window-position=0,0 \
    --window-size=1920,1080 \
    http://localhost:5000
```

#### Systemd Servisi

```ini
# /etc/systemd/system/kuvoz-kiosk.service
[Unit]
Description=Kuvoz Incubator Kiosk Mode
After=graphical-session.target kuvoz-web.service
Wants=graphical-session.target
Requires=kuvoz-web.service

[Service]
Type=simple
User=pi
Group=pi
Environment=DISPLAY=:0
Environment=HOME=/home/pi
ExecStartPre=/bin/sleep 10
ExecStart=/home/pi/Kuvoz/scripts/start-kiosk.sh
Restart=always
RestartSec=10

[Install]
WantedBy=graphical.target
```

### Touch Optimizasyonları

#### CSS Touch Friendly

```css
/* Büyük dokunmatik butonlar */
.gpio-button {
    min-height: 80px;
    min-width: 120px;
    font-size: 1.2em;
    touch-action: manipulation;
}

/* Slider'lar için büyük thumbs */
.slider {
    height: 40px;
}

.slider::-webkit-slider-thumb {
    height: 40px;
    width: 40px;
}

/* Kiosk modu için özel stiller */
@media (max-width: 1024px) {
    .container {
        padding: 10px;
    }
    
    .sensor-card {
        min-height: 150px;
    }
    
    .control-panel {
        grid-gap: 15px;
    }
}
```

#### JavaScript Touch Events

```javascript
// Touch event optimizasyonları
function initTouchEvents() {
    // Butonlar için touch feedback
    document.querySelectorAll('.gpio-button').forEach(button => {
        button.addEventListener('touchstart', (e) => {
            e.preventDefault();
            button.classList.add('touched');
        });
        
        button.addEventListener('touchend', (e) => {
            e.preventDefault();
            button.classList.remove('touched');
            button.click();
        });
    });
    
    // Slider'lar için touch desteği
    document.querySelectorAll('.slider').forEach(slider => {
        slider.addEventListener('touchmove', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            const rect = slider.getBoundingClientRect();
            const pos = (touch.clientX - rect.left) / rect.width;
            const value = slider.min + (slider.max - slider.min) * pos;
            slider.value = Math.round(value);
            updateSliderValue(slider);
        });
    });
}
```

---

## 🔧 Sorun Giderme

### Yaygın Sorunlar ve Çözümleri

#### 1. Web Server Başlamıyor

**Belirtiler:**
- http://localhost:5000 erişilemiyor
- "Connection refused" hatası
- Port 5000 dinlemiyor

**Çözüm Adımları:**

```bash
# 1. Service durumunu kontrol et
make web-status
sudo systemctl status kuvoz-web

# 2. Port durumunu kontrol et
netstat -tlnp | grep :5000
sudo lsof -i :5000

# 3. Python bağımlılıklarını kontrol et
python3 -c "import flask; print('Flask OK')"
python3 -c "import flask_socketio; print('SocketIO OK')"

# 4. Manuel başlatma ile debug
python3 web_server.py

# 5. Log kontrol
sudo journalctl -u kuvoz-web -f
```

**Çözümler:**
```bash
# Bağımlılık sorunu
pip3 install flask flask-socketio --break-system-packages

# Port kullanımda
sudo killall python3
sudo systemctl restart kuvoz-web

# İzin sorunu
sudo usermod -a -G gpio $USER
sudo reboot
```

#### 2. Sensör Okuma Hataları

**DHT22 Sensör Sorunları:**

```bash
# DHT sensör test
python3 -c "
import sys
sys.path.append('lib')
from DHT_Native import read_retry
result = read_retry(pin=15)
print(f'Sonuç: {result}')
"

# GPIO pin kontrol
gpio readall | grep "15"

# Bağlantı kontrol
gpio mode 15 in
gpio read 15
```

**Oksijen Sensör Sorunları:**

```bash
# I2C kontrol
sudo i2cdetect -y 1

# I2C izinleri
sudo usermod -a -G i2c $USER

# Sensör test
python3 -c "
import sys
sys.path.append('lib')
from DFRobot_Oxygen import *
sensor = DFRobot_Oxygen_IIC(IIC_MODE, ADDRESS_3)
print(f'Oksijen: {sensor.get_oxygen_data(20)}%')
"
```

#### 3. GPIO Kontrol Sorunları

**Belirtiler:**
- Butonlar çalışmıyor
- Röle kontrolü başarısız
- GPIO permission denied

**Çözüm:**

```bash
# GPIO grubu kontrol
groups $USER | grep gpio

# GPIO grubu ekle
sudo usermod -a -G gpio $USER
sudo reboot

# GPIO pin durumu kontrol
gpio readall

# Manuel GPIO test
gpio mode 5 out
gpio write 5 1  # Röle aç
gpio write 5 0  # Röle kapat
```

#### 4. Kiosk Modu Çalışmıyor

**Sorun Tespiti:**

```bash
# Display değişkeni kontrol
echo $DISPLAY

# X11 test
xhost +local:

# Browser test
chromium-browser --version
firefox-esr --version

# Kiosk service kontrol
sudo systemctl status kuvoz-kiosk
```

**Çözümler:**

```bash
# Display ayarla
export DISPLAY=:0

# X11 izinleri
xhost +local:

# Browser kur
sudo apt install chromium-browser
# veya
sudo apt install firefox-esr

# Service yeniden başlat
sudo systemctl restart kuvoz-kiosk
```

#### 5. Ağ Erişim Sorunları

**Uzaktan Erişim:**

```bash
# IP adres kontrol
hostname -I
ip addr show

# Port kontrol
netstat -tlnp | grep :5000

# Firewall kontrol
sudo ufw status

# Ağ test
ping [raspberry-pi-ip]
telnet [raspberry-pi-ip] 5000
```

### Debug Araçları

#### 1. Sistem Durumu Kontrol

```bash
# Kuvoz sistem durumu
make system-status

# Tüm servis durumları
make status-all

# Log görüntüleme  
make logs-all
```

#### 2. Hardware Test

```bash
# GPIO test
make test-gpio

# DHT sensör test
make test-dht

# Oksijen sensör test
make test-oxygen

# I2C test
make test-i2c
```

#### 3. Performance Test

```bash
# DHT performans test
python3 -c "
import sys, time
sys.path.append('lib')
from DHT_Native import DHT_Native

dht = DHT_Native(pin=15)
for i in range(10):
    start = time.time()
    result = dht.read_retry()
    end = time.time()
    print(f'#{i+1}: {result} - {end-start:.3f}s')
    time.sleep(1)
"
```

#### 4. Network Debug

```bash
# WebSocket bağlantı test
python3 -c "
from flask_socketio import SocketIOTestClient
from web_server import app, socketio

client = SocketIOTestClient(app, socketio)
received = client.get_received()
print(f'WebSocket test: {received}')
"
```

---

## 🔧 Bakım ve Güncellemeler

### Düzenli Bakım

#### Günlük Kontroller

```bash
# Sistem durumu (günlük)
make status-all

# Log kontrol
sudo journalctl -u kuvoz-web --since "24 hours ago"

# Disk alanı kontrol
df -h

# Bellek kullanımı
free -h
```

#### Haftalık Bakım

```bash
# Sistem güncellemeleri
sudo apt update && sudo apt upgrade -y

# Log temizleme
sudo journalctl --vacuum-time=7d

# Geçici dosya temizleme
make clean

# Ayar yedekleme
make backup
```

#### Aylık Bakım

```bash
# Tam sistem yedekleme
sudo dd if=/dev/mmcblk0 of=/backup/kuvoz-backup-$(date +%Y%m%d).img bs=4M

# SD kart kontrol
sudo fsck /dev/mmcblk0p2

# Performans analizi
make performance-test
```

### Güncelleme Prosedürü

#### Kod Güncellemeleri

```bash
# Git güncellemesi
cd /home/pi/Kuvoz
git fetch origin
git status

# Yedek alma
make backup

# Güncelleme çekme
git pull origin web-interface

# Servis yeniden başlatma
sudo systemctl restart kuvoz-web
sudo systemctl restart kuvoz-kiosk
```

#### Konfigürasyon Güncellemeleri

```bash
# Yeni ayarları uygulama
make web-service      # Web servis güncellemesi
make kiosk-service    # Kiosk servis güncellemesi

# Daemon reload
sudo systemctl daemon-reload

# Service durumu kontrol
make status-all
```

### Yedekleme ve Geri Yükleme

#### Ayar Yedekleme

```bash
# Otomatik yedekleme
make backup

# Manuel yedekleme
cp Failure.dat backup/Failure.dat.$(date +%Y%m%d_%H%M%S)

# Yedek listesi
ls -la backup/
```

#### Geri Yükleme

```bash
# Son yedekten geri yükleme
make restore

# Belirli yedekten geri yükleme
cp backup/Failure.dat.20251027_1430 Failure.dat

# Ayarları yeniden yükleme
curl -X POST http://localhost:5000/api/load_settings
```

#### Tam Sistem Yedeği

```bash
# SD kart imaj yedeği
sudo dd if=/dev/mmcblk0 of=/external/kuvoz-full-backup.img bs=4M status=progress

# Sıkıştırılmış yedek
sudo dd if=/dev/mmcblk0 bs=4M | gzip > /external/kuvoz-backup-$(date +%Y%m%d).img.gz

# Geri yükleme
sudo dd if=/external/kuvoz-backup.img of=/dev/mmcblk0 bs=4M status=progress
```

---

## 📚 Teknik Referans

### API Referansı

#### HTTP Endpoints

```bash
# Ana sayfa
GET /                          # Web arayüzü

# API endpoints
POST /api/save_settings        # Ayarları kaydet
POST /api/load_settings        # Ayarları yükle
POST /api/button_control       # Buton kontrolü
POST /api/slider_control       # Slider kontrolü
GET  /api/sensor_data          # Sensör verisi
POST /api/system_command       # Sistem komutu
```

#### WebSocket Events

```javascript
// Client → Server
'toggle_button'     // Buton toggle
'update_slider'     // Slider güncelleme
'save_settings'     // Ayar kaydetme
'load_settings'     // Ayar yükleme
'system_command'    // Sistem komutu

// Server → Client  
'sensor_update'     // Sensör veri güncellemesi
'button_update'     // Buton durum güncellemesi
'slider_update'     // Slider değer güncellemesi
'system_message'    // Sistem mesajı
'connection_status' // Bağlantı durumu
```

### Dosya Yapısı

```
Kuvoz/
├── 📁 web/                      # Web arayüzü dosyaları
│   ├── index.html              # Ana sayfa
│   ├── styles.css              # CSS stilleri  
│   ├── script.js               # JavaScript kodu
│   └── debug.html              # Debug sayfası
├── 📁 lib/                      # Kütüphane dosyaları
│   ├── DHT_Native.py           # DHT sensör sürücüsü
│   └── DFRobot_Oxygen.py       # Oksijen sensör sürücüsü
├── 📁 scripts/                  # Shell script'leri
│   ├── start-kiosk.sh          # Kiosk başlatma
│   └── quick_web_test.sh       # Hızlı test
├── 📁 systemd/                  # Systemd servis dosyaları
│   ├── kuvoz-web.service       # Web server servisi
│   └── kuvoz-kiosk.service     # Kiosk servisi
├── 📁 config/                   # Konfigürasyon dosyaları
│   └── openbox-autostart       # X11 autostart
├── 📁 backup/                   # Yedek dosyaları
├── 📄 web_server.py            # Flask web server
├── 📄 main3.py                 # Eski Kivy uygulaması
├── 📄 Failure.dat              # Ayar dosyası (JSON)
├── 📄 Makefile                 # Ana makefile
├── 📄 README_WEB.md            # Web arayüzü README
└── 📄 KUVOZ_KULLANIM_KLAVUZU.md # Bu kullanım kılavuzu
```

### Makefile Komut Referansı

#### Kurulum Komutları

```bash
make auto-setup        # Tam otomatik kurulum
make web-install       # Web server kurulum
make web-deps          # Web bağımlılıkları
make install-system    # Sistem paketleri ile kurulum
make config            # Sistem konfigürasyonu
```

#### Çalıştırma Komutları

```bash
make web-start         # Web server başlat
make kiosk-start       # Kiosk modu başlat
make start-all         # Tüm servisleri başlat
make run               # Eski Kivy uygulaması
make run-dht11         # DHT11 ile çalıştır
```

#### Servis Yönetimi

```bash
make web-service       # Web servisi kur
make kiosk-service     # Kiosk servisi kur
make status-all        # Tüm servis durumları
make logs-all          # Tüm servis logları
make restart-all       # Tüm servisleri yeniden başlat
```

#### Test ve Debug

```bash
make test              # Sistem testleri
make test-dht          # DHT sensör testi
make test-web          # Web sistem testi
make debug             # Debug modu
make troubleshoot      # Sorun giderme rehberi
```

#### Bakım Komutları

```bash
make backup            # Ayar yedekleme
make restore           # Ayar geri yükleme
make clean             # Temizlik
make uninstall-all     # Tüm servisleri kaldır
```

### Performans Parametreleri

#### Sistem Kaynakları

| Kaynak | Normal | Yüksek Yük | Kritik |
|--------|--------|------------|--------|
| **CPU** | <30% | 30-70% | >70% |
| **RAM** | <50% | 50-80% | >80% |
| **Disk** | <70% | 70-90% | >90% |
| **Network** | <10Mbps | 10-50Mbps | >50Mbps |

#### Timing Parametreleri

```python
# Sensör okuma aralıkları
DHT_READ_INTERVAL = 15      # DHT sensör okuma (saniye)
OXYGEN_READ_INTERVAL = 30   # Oksijen sensör okuma (saniye)
CONTROL_LOOP_INTERVAL = 5   # Kontrol logic döngüsü (saniye)
WEBSOCKET_PING = 25         # WebSocket ping aralığı (saniye)

# Timeout değerleri
DHT_READ_TIMEOUT = 5        # DHT okuma timeout (saniye)
I2C_TIMEOUT = 3             # I2C okuma timeout (saniye)
GPIO_TIMEOUT = 1            # GPIO işlem timeout (saniye)
WEB_REQUEST_TIMEOUT = 30    # Web request timeout (saniye)

# Retry parametreleri
DHT_RETRY_COUNT = 3         # DHT okuma retry sayısı
I2C_RETRY_COUNT = 2         # I2C okuma retry sayısı
WEBSOCKET_RETRY_COUNT = 5   # WebSocket bağlantı retry
```

---

## 🎉 Veteriner Kliniği Kurulum Tamamlandı

Kuvoz Veteriner Rehabilitasyon Ünitesi v3.0 ile modern, güvenilir ve veteriner dostu bir hasta bakım ve iyileşme kontrol sistemi elde ettiniz. Web tabanlı arayüzü sayesinde veteriner hekimler hem klinik içi hem de uzaktan hasta takibi yapabilir, kiosk modu ile teknisyenler için profesyonel dokunmatik arayüz ve otomatik bakım sistemleri ile güvenli hasta bakımı sağlanmaktadır.

### 🎯 Veteriner Sistem Başarı Kriterleri

- ✅ **Kurulum**: `make auto-setup` ile tek komutta veteriner ünitesi tamamlandı
- ✅ **Hasta Monitoring**: http://localhost:5000 erişimi ile hasta takibi aktif
- ✅ **Vital Parametre Sensörleri**: DHT22 ve oksijen saturasyon monitörü çalışıyor
- ✅ **Tıbbi Cihaz Kontrolü**: 8 kanal veteriner ekipmanı kontrolü aktif
- ✅ **Otomatik Bakım**: Termoregülasyon/solunum terapi/sterilizasyon çalışıyor
- ✅ **Veteriner Kiosk**: Tam ekran teknisyen arayüzü hazır
- ✅ **7/24 Monitoring**: Otomatik hasta takip sistemi etkin

### 🚀 Veteriner Kliniği Sonraki Adımlar

1. **Hasta Profil Kalibrasyonu**: Kedi/köpek türüne göre sensör kalibrasyonu
2. **Veteriner Alarm Sistemi**: Kritik vital parametreler için uyarı sistemi
3. **Hasta Kayıt Sistemi**: SQLite ile hasta geçmişi ve tedavi kayıtları
4. **Veteriner Mobil App**: iOS/Android ile veteriner hekim uzaktan erişimi  
5. **Klinik Cloud Integration**: Hasta verilerinin cloud backup'ı
6. **Multi-Ünite Yönetimi**: Birden fazla rehabilitasyon ünitesinin merkezi kontrolü

### 📞 Destek

**GitHub Repository**: https://github.com/oktaycit/Kuvoz  
**Issues**: https://github.com/oktaycit/Kuvoz/issues  
**Wiki**: https://github.com/oktaycit/Kuvoz/wiki  
**Developer**: Oktay Çit (@oktaycit)

---

**Kuvoz Veteriner Rehabilitasyon Ünitesi v3.0** �🐕🐱  
*Modern veteriner web arayüzü ile akıllı hasta bakım otomasyonu*

**Kullanım Alanı**: Veteriner Kliniği - Kedi/Köpek Rehabilitasyon ve Post-Operatif Bakım  
**Son Güncelleme**: 27 Ekim 2025  
**Lisans**: MIT License - Veteriner Kullanım İzinli