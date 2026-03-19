# Kuvoz Projesi İçin Alternatif Tek Kartlı Bilgisayarlar

## Mevcut Donanım Gereksinimleri

Kuvoz veteriner inkübatör kontrol sistemi için gerekli özellikler:

### Kritik Gereksinimler
1. **GPIO Pin Desteği**: 8 kanal röle kontrolü için (BCM GPIO)
2. **I2C Bus Desteği**: Oksijen sensörü (DFRobot I2C) için
3. **DHT Sensör Desteği**: Sıcaklık ve nem okuma (DHT22)
4. **Python 3.9+**: Flask backend için
5. **Web Tarayıcı**: Chromium/Firefox kiosk modu için
6. **Ağ Bağlantısı**: WiFi ve/veya Ethernet
7. **Güç**: 5V DC stabil güç kaynağı

### Mevcut Kullanılan Kütüphaneler
- `RPi.GPIO` veya alternatif GPIO kütüphaneleri
- `DHT_Native` (DHT11/DHT22 için)
- `DFRobot_Oxygen` (I2C oksijen sensörü için)
- `Flask`, `Flask-SocketIO`
- `smbus2` (I2C iletişimi için)

---

## Orange Pi Alternatifleri

### 1. Orange Pi 3B

#### Teknik Özellikler
| Özellik | Değer |
|---------|-------|
| SoC | Rockchip RK3566 (4 çekirdek, 1.8GHz) |
| RAM | 2GB/4GB LPDDR4X |
| Depolama | eMMC 8GB/16GB/32GB + microSD |
| GPIO | 26-pin header (SPI, I2C, UART, PWM) |
| Ağ | Gigabit Ethernet + WiFi 5 + BT 5.0 |
| USB | 2x USB 2.0, 1x USB Type-C (OTG) |
| Güç | 5V/3A USB Type-C |
| Fiyat | ~$35-45 |

#### Kuvoz Uyumluluğu
- ✅ **GPIO**: 26-pin header, I2C ve SPI desteği var
- ✅ **Python**: Armbian/Orange Pi OS ile Python 3.8+
- ✅ **I2C**: Donanımsal I2C desteği mevcut
- ⚠️ **GPIO Kütüphanesi**: `OPi.GPIO` veya `wiringOP` kullanılmalı
- ⚠️ **Kiosk**: Chromium/Armbian desteği var ama Raspberry Pi kadar olgun değil

#### Kod Değişikliği Gereksinimi
```python
# RPi.GPIO yerine OPi.GPIO
try:
    import OPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
```

---

### 2. Orange Pi Zero 3

#### Teknik Özellikler
| Özellik | Değer |
|---------|-------|
| SoC | Allwinner H618 (4 çekirdek, 1.5GHz) |
| RAM | 1GB/1.5GB/2GB/4GB LPDDR4X |
| Depolama | microSD + opsiyonel eMMC |
| GPIO | 26-pin header (I2C, SPI, UART) |
| Ağ | Gigabit Ethernet + WiFi 5 + BT 5.0 |
| USB | 1x USB 2.0, 1x USB Type-C |
| Güç | 5V/3A Type-C |
| Fiyat | ~$20-30 |

#### Kuvoz Uyumluluğu
- ✅ **Fiyat/Performans**: En uygun fiyatlı seçenek
- ✅ **GPIO**: 26-pin ile tüm gerekli pinler mevcut
- ⚠️ **RAM**: 2GB+ modeli önerilir (web server + kiosk için)
- ⚠️ **Güç**: Type-C ama bazı modellerde güç yönetimi sorunlu olabilir

---

### 3. Orange Pi 5

#### Teknik Özellikler
| Özellik | Değer |
|---------|-------|
| SoC | Rockchip RK3588S (8 çekirdek, 2.4GHz) |
| RAM | 4GB/8GB/16GB LPDDR4X |
| Depolama | eMMC + microSD + M.2 NVMe |
| GPIO | 40-pin header (Raspberry Pi uyumlu) |
| Ağ | 2.5GbE + WiFi 6 + BT 5.0 |
| USB | 4x USB 3.0, 1x USB Type-C |
| Güç | 5V/4A Type-C |
| Fiyat | ~$60-90 |

#### Kuvoz Uyumluluğu
- ✅ **GPIO**: 40-pin Raspberry Pi uyumlu header
- ✅ **Performans**: En güçlü seçenek
- ✅ **I2C**: Çoklu I2C bus desteği
- ✅ **Kiosk**: 4K HDMI çıkışı, modern tarayıcı desteği
- ⚠️ **Fiyat**: Daha pahalı ama uzun vadeli yatırım

---

## Banana Pi Alternatifleri

### 1. Banana Pi M4 Zero

#### Teknik Özellikler
| Özellik | Değer |
|---------|-------|
| SoC | Allwinner H618 (4 çekirdek, 1.5GHz) |
| RAM | 2GB LPDDR4 |
| Depolama | microSD |
| GPIO | 40-pin (Raspberry Pi Zero uyumlu) |
| Ağ | WiFi 5 + BT 5.0 (Ethernet yok) |
| USB | 1x USB 2.0, 1x Micro USB (OTG) |
| Güç | 5V/2.5A Micro USB |
| Fiyat | ~$25-35 |

#### Kuvoz Uyumluluğu
- ✅ **GPIO**: Raspberry Pi Zero uyumlu 40-pin
- ✅ **Boyut**: Kompakt tasarım
- ⚠️ **Ethernet Yok**: Sadece WiFi (güvenilirlik için Ethernet önerilir)
- ⚠️ **Güç**: Micro USB (eski standart)

---

### 2. Banana Pi M5

#### Teknik Özellikler
| Özellik | Değer |
|---------|-------|
| SoC | Amlogic S905X3 (4 çekirdek, 1.9GHz) |
| RAM | 4GB DDR4 |
| Depolama | eMMC 16GB + microSD |
| GPIO | 40-pin (Raspberry Pi uyumlu) |
| Ağ | Gigabit Ethernet + WiFi + BT |
| USB | 2x USB 2.0, 1x USB 3.0 |
| Güç | 5V/2A Type-C |
| Fiyat | ~$50-60 |

#### Kuvoz Uyumluluğu
- ✅ **GPIO**: Tam Raspberry Pi uyumlu
- ✅ **Amlogic**: İyi Linux desteği
- ⚠️ **GPIO Kütüphanesi**: `BPI.GPIO` veya `wiringBP` gerekli

---

### 3. Banana Pi BPI-M6

#### Teknik Özellikler
| Özellik | Değer |
|---------|-------|
| SoC | Amlogic S905X4 (4 çekirdek, 2.0GHz) |
| RAM | 4GB/8GB DDR4 |
| Depolama | eMMC 32GB + microSD + M.2 |
| GPIO | 40-pin header |
| Ağ | Gigabit Ethernet + WiFi 6 + BT 5.3 |
| USB | 3x USB (1x 3.0) |
| Güç | 5V/3A Type-C |
| Fiyat | ~$70-85 |

#### Kuvoz Uyumluluğu
- ✅ **Tüm Özellikler**: Tam donanımlı
- ✅ **WiFi 6**: Modern ağ desteği
- ✅ **M.2**: Ekstra depolama seçeneği
- ⚠️ **Fiyat**: Yüksek segment

---

## Karşılaştırmalı Tablo

| Model | GPIO | I2C | RAM | Ethernet | WiFi | Fiyat | Kuvoz Uygunluğu |
|-------|------|-----|-----|----------|------|-------|-----------------|
| **Raspberry Pi 4B** | ✅40-pin | ✅2 | 4GB | ✅Gigabit | ✅5 | $55 | ⭐⭐⭐⭐⭐ (Mevcut) |
| **Raspberry Pi 3B+** | ✅40-pin | ✅1 | 1GB | ✅Gigabit | ✅4 | $35 | ⭐⭐⭐⭐ |
| **Orange Pi 3B** | ✅26-pin | ✅2 | 4GB | ✅Gigabit | ✅5 | $40 | ⭐⭐⭐⭐ |
| **Orange Pi Zero 3** | ✅26-pin | ✅1 | 2GB | ✅Gigabit | ✅5 | $25 | ⭐⭐⭐⭐ |
| **Orange Pi 5** | ✅40-pin | ✅3 | 8GB | ✅2.5GbE | ✅6 | $75 | ⭐⭐⭐⭐⭐ |
| **Banana Pi M4 Zero** | ✅40-pin | ✅1 | 2GB | ❌ | ✅5 | $30 | ⭐⭐⭐ |
| **Banana Pi M5** | ✅40-pin | ✅1 | 4GB | ✅Gigabit | ✅5 | $55 | ⭐⭐⭐⭐ |
| **Banana Pi M6** | ✅40-pin | ✅2 | 4GB | ✅Gigabit | ✅6 | $75 | ⭐⭐⭐⭐ |

---

## GPIO Kütüphane Karşılaştırması

### Raspberry Pi
```python
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)
```

### Orange Pi (Armbian)
```python
import OPi.GPIO as GPIO
# veya
from wiringpi import GPIO
```

### Banana Pi
```python
import BPI.GPIO as GPIO
# veya
import wiringBP as GPIO
```

### Evrensel Yaklaşım (Önerilen)
```python
# web_server.py içinde platform bağımsız GPIO wrapper
try:
    import RPi.GPIO as GPIO
    GPIO_TYPE = "RPi"
except ImportError:
    try:
        import OPi.GPIO as GPIO
        GPIO_TYPE = "OPi"
    except ImportError:
        try:
            import BPI.GPIO as GPIO
            GPIO_TYPE = "BPI"
        except ImportError:
            GPIO = None
            GPIO_TYPE = "None"
```

---

## Önerilen Modeller

### 🏆 En İyi Fiyat/Performans: Orange Pi Zero 3 (2GB/4GB)
- **Fiyat**: ~$25-30
- **Artılar**: Ucuz, yeterli performans, Gigabit Ethernet, WiFi
- **Eksiler**: 26-pin GPIO (yeterli), Type-C güç yönetimi
- **Kuvoz İçin**: Tüm gereksinimleri karşılıyor

### 🥈 En İyi Uyum: Orange Pi 3B
- **Fiyat**: ~$40-45
- **Artılar**: 40-pin'e yakın 26-pin, eMMC seçeneği, stabil Armbian
- **Eksiler**: Raspberry Pi kadar dokümantasyon yok
- **Kuvoz İçin**: Ideal denge

### 🥇 Premium Seçenek: Orange Pi 5
- **Fiyat**: ~$60-90
- **Artılar**: 8 çekirdek, 40-pin RPi uyumlu, WiFi 6, NVMe
- **Eksiler**: Pahalı
- **Kuvoz İçin**: Gelecek-proof, AI özellikleri için hazır

---

## Migration (Geçiş) Adımları

### 1. İşletim Sistemi Kurulumu
```bash
# Orange Pi için Armbian
# https://www.armbian.org/orange-pi-3b/

# Banana Pi için Banana Pi OS veya Armbian
# https://www.banana-pi.org/
```

### 2. GPIO Kütüphanesi Değişikliği

`web_server.py` içinde mevcut GPIO import kısmını değiştir:

```python
# MEVCUT KOD (RPi özel)
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False

# YENİ KOD (Platform bağımsız)
GPIO_AVAILABLE = False
GPIO_TYPE = None

# Try RPi.GPIO first (Raspberry Pi)
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
    GPIO_TYPE = "RPi"
except ImportError:
    # Try OPi.GPIO (Orange Pi)
    try:
        import OPi.GPIO as GPIO
        GPIO_AVAILABLE = True
        GPIO_TYPE = "OPi"
    except ImportError:
        # Try BPI.GPIO (Banana Pi)
        try:
            import BPI.GPIO as GPIO
            GPIO_AVAILABLE = True
            GPIO_TYPE = "BPI"
        except ImportError:
            GPIO = None
            GPIO_TYPE = "None"
            logger.warning("No GPIO library found - running in simulation mode")
```

### 3. Pin Mapping Güncelleme

Her kartın pin mapping'i farklıdır. Orange Pi 3B için:

```python
# Orange Pi 3B GPIO Mapping (BCM style)
# RPi BCM -> OPi3B
PIN_MAP = {
    5: 5,    # B1
    6: 6,    # B2
    13: 13,  # B3
    16: 16,  # B4
    19: 19,  # B5
    20: 20,  # B6
    21: 21,  # B7
    26: 26,  # B8
}
```

### 4. I2C Aktifleştirme

```bash
# Orange Pi (Armbian)
sudo armbian-config
# System -> Hardware -> I2C enable

# veya
sudo nano /boot/armbianEnv.txt
# overlays=i2c0 i2c1
```

### 5. DHT Sensör Testi

```bash
# DHT_Native kütüphanesi Orange Pi'de de çalışmalı
python3 test_dht_native.py
```

---

## Satın Alma Önerileri (Türkiye)

### Orange Pi
- **AliExpress**: Official Orange Pi Store
- **Türkiye**: Robotistan, Direnc.net, Robolink
- **Fiyatlar**: Gümrük + KDV dahil ~2x

### Banana Pi
- **AliExpress**: Official Banana Pi Store
- **Türkiye**: Robotex, Elektrikçiler Çarşısı

### Raspberry Pi (Karşılaştırma)
- **Türkiye**: Robotistan, Adafruit Türkiye, Robolink
- **Fiyat**: Genelde daha pahalı ama kolay bulunur

---

## Sonuç ve Tavsiye

### Kısa Vadeli (Mevcut Sistem Devam)
**Raspberry Pi 4B/3B+** kullanmaya devam edin. En stabil ve test edilmiş platform.

### Orta Vadeli (Maliyet Optimizasyonu)
**Orange Pi Zero 3 (4GB)** veya **Orange Pi 3B**
- %40-50 maliyet azaltma
- Yeterli performans
- Minimal kod değişikliği

### Uzun Vadeli (Ölçekleme)
**Orange Pi 5**
- AI özellikleri için yeterli güç
- Çoklu hasta takibi
- Görüntü işleme potansiyeli
- Gelecek-proof

---

## Test Planı

1. **Orange Pi Zero 3** satın al (en ucuz seçenek)
2. Armbian kur ve temel testleri yap
3. GPIO pin testini çalıştır
4. DHT sensör okumasını test et
5. I2C oksijen sensörünü test et
6. Flask web server'ı çalıştır
7. Kiosk modunu test et
8. Uzun süreli stabilite testi yap

---

**Doküman Tarihi**: 2026-03-19
**Hazırlayan**: Kuvoz Development Team