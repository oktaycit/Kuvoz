# Raspberry Pi OS Trixie - Chromium Installation Guide

## 🔍 Problem: chromium-browser paketi bulunamıyor

Raspberry Pi OS Trixie (Debian 13.1) sürümünde Chromium paket adları değişti.

### ✅ Çözüm 1: Güncel Paket Adları

```bash
# Mevcut paketi kontrol et
make chromium-check

# Trixie için doğru paket adı
sudo apt install chromium

# Eski adla deneme (fallback)
sudo apt install chromium-browser
```

### ✅ Çözüm 2: Snap Chromium

```bash
# Snap Chromium kurulumu
sudo apt install snapd
sudo snap install chromium

# Snap binary path
/snap/bin/chromium
```

### ✅ Çözüm 3: Firefox Alternatifi

```bash
# Firefox ESR kurulumu
make firefox-install

# Firefox kiosk mode
make firefox-manual
```

### ✅ Çözüm 4: Otomatik Browser Seçimi

```bash
# Mevcut browser'ı otomatik kullan
make auto-browser
```

## 🔧 Python Packages - externally-managed-environment Fix

### ✅ Çözüm 1: Sistem Paketleri (Önerilen)

```bash
# Flask ve diğer web paketleri sistem paketleri ile
sudo apt install python3-flask python3-flask-socketio python3-eventlet

# Otomatik kurulum
make web-deps-install
```

### ✅ Çözüm 2: Virtual Environment

```bash
# Virtual environment oluştur
python3 -m venv web_venv

# Activate ve paketleri kur
source web_venv/bin/activate
pip install flask flask-socketio eventlet

# Web server'ı venv ile çalıştır
web_venv/bin/python web_server.py
```

### ✅ Çözüm 3: Break System Packages (Son Çare)

```bash
# Sistem korumasını bypass et
pip3 install --break-system-packages flask flask-socketio eventlet
```

## 🚀 Hızlı Web Setup

```bash
# Tam kurulum (Chromium + Python packages)
make web-install

# Sadece Python packages
make web-deps-install

# Web server başlat
make web-run
```

### APT Repository Güncelleme

```bash
# Repository listesini güncelle
sudo apt update

# Chromium arama
apt search chromium

# Mevcut paketler
apt list --installed | grep chromium
```

### Debian Trixie Sources

`/etc/apt/sources.list` kontrol et:

```bash
deb http://deb.debian.org/debian trixie main
deb-src http://deb.debian.org/debian trixie main

deb http://deb.debian.org/debian-security/ trixie-security main
deb-src http://deb.debian.org/debian-security/ trixie-security main

deb http://deb.debian.org/debian trixie-updates main
deb-src http://deb.debian.org/debian trixie-updates main
```

## 🛠️ Manual Installation

### Direct Chromium Download

```bash
# Manual .deb download (son çare)
wget https://packages.debian.org/trixie/chromium
sudo dpkg -i chromium_*.deb
sudo apt-get install -f  # Dependencies fix
```

### Flatpak Chromium

```bash
# Flatpak kurulumu
sudo apt install flatpak
sudo flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

# Chromium flatpak
sudo flatpak install flathub org.chromium.Chromium

# Flatpak çalıştırma
flatpak run org.chromium.Chromium --kiosk --app=http://localhost:5000
```

## 🔍 Browser Detection Script

```bash
#!/bin/bash
# Browser bulma ve kiosk başlatma

if command -v chromium >/dev/null 2>&1; then
    echo "✅ Using: chromium"
    chromium --kiosk --app=http://localhost:5000
elif command -v chromium-browser >/dev/null 2>&1; then
    echo "✅ Using: chromium-browser"
    chromium-browser --kiosk --app=http://localhost:5000
elif command -v /snap/bin/chromium >/dev/null 2>&1; then
    echo "✅ Using: snap chromium"
    /snap/bin/chromium --kiosk --app=http://localhost:5000
elif command -v firefox-esr >/dev/null 2>&1; then
    echo "✅ Using: firefox-esr"
    firefox-esr --kiosk --private-window http://localhost:5000
else
    echo "❌ No suitable browser found!"
    exit 1
fi
```

## 📋 Makefile Komutları

```bash
# Browser kontrol
make chromium-check

# Otomatik browser kullan
make auto-browser

# Firefox alternatifi
make firefox-install
make firefox-manual

# Manuel troubleshooting
make browser-help
```

## 🚨 Known Issues

### Issue 1: Package Not Found

**Error**: `Package 'chromium-browser' has no installation candidate`
**Solution**: Use `chromium` instead of `chromium-browser`

### Issue 2: Snap Permission

**Error**: Snap chromium permission denied
**Solution**:

```bash
sudo snap connect chromium:camera
sudo snap connect chromium:audio-record
```

### Issue 3: X11 Display

**Error**: Cannot open display
**Solution**:

```bash
export DISPLAY=:0
xhost +local:
```

### Issue 4: GPU Issues

**Error**: GPU process crashed
**Solution**: Add `--disable-gpu` flag

## 🔧 System Requirements

- **Raspberry Pi OS**: Trixie (Debian 13.1)
- **Architecture**: arm64 recommended
- **RAM**: 2GB minimum for Chromium
- **Storage**: 500MB free space
- **Display**: HDMI output

## 📞 Support Commands

```bash
# System info
cat /etc/os-release
uname -a

# Package manager info
apt --version
dpkg --version

# Display info
echo $DISPLAY
xrandr

# Browser test
make web-test
curl -I http://localhost:5000
```
```