# Kuvoz Incubator Control System v3.0 - Web Interface

Modern web tabanlı kuluçka makinesi kontrol sistemi. Kivy yerine **Chromium Kiosk Mode** ile çalışır.

## 🌟 Özellikler

### 🌐 Web Interface
- **Responsive HTML/CSS/JavaScript** arayüz
- **Real-time WebSocket** iletişimi
- **Mobile-friendly** tasarım
- **Offline-capable** Progressive Web App

### 🎛️ Kontrol Sistemi
- **9 GPIO Channel** röle kontrolü (b9: soğutma dahil)
- **DHT22** sıcaklık & nem sensörü
- **DFRobot Oxygen** oksijen sensörü  
- **Otomatik nebulizer** kontrol (oksijen sensörü yoksa)
- **Zamanlı ozon** kontrolü
- **Thread-safe GPIO** operasyonlar

### 🖥️ Kiosk Mode
- **Chromium fullscreen** interface
- **Auto-start** sistem boot'ta
- **Touch-friendly** controls
- **Auto-hide cursor**

## 📋 Sistem Gereksinimleri

- **Raspberry Pi OS Trixie** (Debian 13.1)
- **Python 3.13+**
- **Chromium Browser**
- **GPIO access** (pi user)
- **I2C enabled** (oksijen sensörü için)

## 🚀 Kurulum

### 1. Hızlı Kurulum
```bash
# Repository clone
git clone https://github.com/oktaycit/Kuvoz.git
cd Kuvoz

# Web interface kurulumu
make web-setup

# Sistem başlatma
make web-start
make kiosk-start
```

### 2. Adım Adım Kurulum

#### Web Dependencies
```bash
make web-install
```

#### Systemd Services
```bash
make web-service
make kiosk-service
```

#### Manuel Başlatma
```bash
# Web server
make web-dev

# Kiosk mode (ayrı terminal)
make kiosk-manual
```

## 🔧 Kullanım

### Web Interface Erişimi
- **Local**: http://localhost:8000
- **Network**: http://[raspberry-pi-ip]:8000
- **Kiosk Mode**: Otomatik fullscreen

### GPIO Pin Mapping
```python
outChannels = [5, 6, 13, 16, 19, 20, 21, 26, 12]
# b1: Pin 5  - Lighting
# b2: Pin 6  - Nebulizer  
# b3: Pin 13 - Humidity
# b4: Pin 16 - Carbon Temperature
# b5: Pin 19 - IR Temperature
# b6: Pin 20 - Fan
# b7: Pin 21 - UV Lighting
# b8: Pin 26 - Ozone
# b9: Pin 12 - Cooling
```

### Sensor Configuration
```python
pinDht = 15      # DHT22 data pin
sensorDht = 22   # DHT22 sensor type
# I2C: SDA=GPIO2, SCL=GPIO3 (Oxygen sensor)
```

## 📁 Dosya Yapısı

```
Kuvoz/
├── web/                    # Web interface
│   ├── index.html         # Ana sayfa
│   ├── help.html          # Yardım kılavuzları sayfası
│   ├── styles.css         # CSS stilleri
│   └── script.js          # JavaScript logic
├── web_server.py          # Flask backend server
├── systemd/               # Service dosyaları
│   ├── kuvoz-web.service  # Web server service
│   └── kuvoz-kiosk.service # Kiosk mode service
├── scripts/               # Shell scriptleri
│   └── start-kiosk.sh     # Kiosk başlatma
├── config/                # Konfigürasyon
│   └── openbox-autostart  # X11 autostart
├── lib/                   # Sensor kütüphaneleri
│   ├── DHT_Native.py      # Native DHT driver
│   └── DFRobot_Oxygen.py  # Oxygen sensor
├── Makefile              # Ana makefile
├── chromium_kiosk.mk     # Kiosk setup commands
└── failure.dat           # Settings storage
```

## 🎯 Makefile Komutları

### 📦 Kurulum
```bash
make web-install     # Web dependencies
make web-setup       # Full setup
make kiosk-setup     # Kiosk only setup
```

### ⚡ Servis Yönetimi
```bash
make web-start       # Web server başlat
make web-stop        # Web server durdur
make kiosk-start     # Kiosk mode başlat
make kiosk-stop      # Kiosk mode durdur
make web-status      # Servis durumu
```

### 🔧 Geliştirme
```bash
make web-dev         # Development server
make web-test        # Interface testi
make kiosk-manual    # Manuel kiosk
```

### 🧹 Maintenance
```bash
make web-clean       # Setup temizle
make web-help        # Komut yardımı
```

## 🌐 Web Interface Özellikleri

### 📊 Dashboard
- **Real-time sensor** değerleri
- **GPIO button** durumları
- **Visual indicators** (renk kodlu)
- **Connection status** göstergesi

### 🎛️ Controls
- **9 GPIO button** toggles
- **12 slider** ayarları (sld1-sld12)
- **System controls** (shutdown/restart)
- **Settings save/load**

### 📱 Mobile Support
- **Responsive design**
- **Touch-friendly** buttons
- **Swipe gestures**
- **Portrait/landscape** orientations

## 🔧 Teknik Detaylar

### Backend Architecture
```python
# Flask + WebSocket server
class KuvozServer:
    - GPIO control
    - Sensor reading  
    - WebSocket communication
    - Thread management

# Background threads
- Sensor thread: 15s interval
- Control thread: 1s interval
```

### Frontend Architecture
```javascript
// WebSocket client
class KuvozController:
    - Real-time communication
    - UI state management
    - Error handling
    - Offline fallback
```

### WebSocket Protocol
```json
// Sensor update
{
  "type": "sensor_update",
  "sensors": {
    "temperature": {"value": "25.5", "status": "OK"},
    "humidity": {"value": "65", "status": "OK"},
    "oxygen": {"value": "20.9", "status": "OK"}
  }
}

// Button control
{
  "command": "toggle_button",
  "data": {
    "name": "b1",
    "pin": 5,
    "state": true
  }
}
```

## 🔍 Troubleshooting

### Web Server Başlamıyor
```bash
# Service durumu kontrol
make web-status

# Manuel başlatma
make web-dev

# Log kontrol
journalctl -u kuvoz-web -f
```

### Kiosk Mode Problemi
```bash
# Display kontrol
echo $DISPLAY

# X11 test
xhost +local:

# Manuel başlatma
make kiosk-manual
```

### GPIO Permission Error
```bash
# User groups kontrol
groups $USER

# GPIO group ekle
sudo usermod -a -G gpio $USER
```

## 📚 Migration from Kivy

### Eski Kivy Sistem
- ❌ form.kv layout dosyası
- ❌ main3.py Kivy app
- ❌ TabbedPanel UI
- ❌ Render problems

### Yeni Web Sistem  
- ✅ HTML/CSS/JS interface
- ✅ web_server.py Flask app
- ✅ Responsive design
- ✅ Cross-platform compatible

### Migration Script
```bash
# Kivy dependencies kaldır
pip uninstall kivy

# Web dependencies kur
make web-install

# Service'leri yeniden kur
make web-setup
```

## 🤝 Katkıda Bulunma

1. Fork the project
2. Feature branch oluştur
3. Changes commit et
4. Branch'i push et
5. Pull Request aç

## 🔧 Bakım ve Destek

### Otomatik Bakım Sistemleri

Kuvoz sistemi **24/7 kesintisiz çalışma** için otomatik bakım sistemleriyle donatılmıştır:

- ✅ **Chromium Cache Yönetimi**: 50MB cache limiti, otomatik temizleme
- ✅ **Log Rotation**: Günlük log rotation, 7 gün saklama, 10MB limit
- ✅ **Günlük Otomatik Bakım**: Her gece 03:00'da otomatik cache temizliği ve yeniden başlatma
- ✅ **Memory Leak Önleme**: Düzenli kiosk yeniden başlatma

### Dokümantasyon

- **📘 [MAINTENANCE.md](docs/MAINTENANCE.md)** - Uzun süreli çalışma, bakım ve sorun giderme kılavuzu
- **📗 [KUVOZ_KULLANIM_KLAVUZU.md](docs/KUVOZ_KULLANIM_KLAVUZU.md)** - Kapsamlı kullanım kılavuzu
- **📙 [CLAUDE.md](CLAUDE.md)** - Geliştirici ve AI asistan kılavuzu
- **📕 [SYSTEM_REQUIREMENTS.md](docs/SYSTEM_REQUIREMENTS.md)** - Sistem gereksinimleri
- **📚 [docs/INDEX.md](docs/INDEX.md)** - Tüm Markdown kılavuzlarının indeksi
- **📓 [docs/AI_DYNAMIC_VITAL_THRESHOLDS.md](docs/AI_DYNAMIC_VITAL_THRESHOLDS.md)** - Dinamik vital eşik sistemi

## 📄 Lisans

MIT License - Detaylar için LICENSE dosyasına bakın.

## 👨‍💻 Geliştirici

**Oktay Çit** - [@oktaycit](https://github.com/oktaycit)

## 🔗 Links

- **GitHub**: https://github.com/oktaycit/Kuvoz
- **Issues**: https://github.com/oktaycit/Kuvoz/issues
- **Wiki**: https://github.com/oktaycit/Kuvoz/wiki

---

*Kuvoz Incubator Control System v3.0 - Modern web interface with Chromium Kiosk Mode* 🌐🖥️
