# 🚀 Kuvoz Raspberry Pi Setup - Router SSH Bypass Method

## ✅ GitHub Repository Push Completed!

Branch: `web-interface`  
Repository: https://github.com/oktaycit/Kuvoz

## 📡 Raspberry Pi'de Kurulum (Router Konfigürasyonu Gerektirmez!)

### 1️⃣ Raspberry Pi'ye Bağlan

```bash
# Yerel ağ üzerinden (HDMI + klavye) veya
# Alternatif yöntemlerle (VNC, TeamViewer, etc.)
```

### 2️⃣ GitHub'dan Proje İndir

```bash
# Git kurulumu (gerekirse)
sudo apt update
sudo apt install -y git

# Kuvoz projesini indir
git clone -b web-interface https://github.com/oktaycit/Kuvoz.git kuvoz

# Klasöre gir
cd kuvoz
```

### 3️⃣ Otomatik Setup Script

```bash
# Setup script'i çalıştır
chmod +x setup_raspberry_pi.sh
./setup_raspberry_pi.sh
```

**VEYA** manuel kurulum:

### 4️⃣ Manuel Kurulum

```bash
# Python dependencies
make web-deps-install

# DHT sensor test
make dht11-test

# Platform fix ile web server başlat
make web-platform-fix-full
```

### 5️⃣ Kiosk Mode (Opsiyonel)

```bash
# Browser kiosk mode
make auto-browser

# Veya manuel
make kiosk-manual
```

## 🌐 Web Interface Erişim

- **Yerel**: http://localhost:8000
- **Ağ**: http://[RaspberryPi-IP]:8000
- **Örnek**: http://192.168.1.100:8000

## 📊 Özellikler

- ✅ **DHT11 Pin 15**: Sıcaklık/Nem sensörü
- ✅ **8-CH Relay**: GPIO kontrol
- ✅ **Web Interface**: Real-time WebSocket
- ✅ **Platform Fix**: Adafruit_DHT + DHT_Native fallback
- ✅ **Browser Support**: Chromium + Firefox fallback
- ✅ **Kiosk Mode**: Tam ekran interface

## 🔧 Debug Komutları

```bash
# DHT sensor test
make dht11-test

# GPIO debug
make web-debug-gpio

# Platform troubleshooting
make fix-adafruit-platform

# Web server simulation
make web-sim
```

## 📱 Mobile/Remote Access

Router port forwarding olmadan bile yerel ağ üzerinden erişilebilir:

```bash
# Raspberry Pi IP'sini bul
hostname -I

# Telefondan/PC'den eriş
http://[RaspberryPi-IP]:8000
```

## 🎯 Başarı Kriterleri

1. ✅ **GPIO**: 8-channel relay kontrol
2. ✅ **DHT11**: Pin 15'den sıcaklık/nem okuma
3. ✅ **Web Interface**: Responsive, real-time
4. ✅ **Kiosk**: Tam ekran browser mode
5. ✅ **Network**: Yerel ağ erişimi

Router SSH port forwarding artık gerekli değil! 🎉