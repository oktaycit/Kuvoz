# Raspberry Pi Zero 2 W - Kiosk Mode Sorunları ve Çözümler

## 🚫 Sorunlar

### 1. NEON SIMD Hatası
```
The hardware on this system lacks support for NEON SIMD extensions.
```

**Neden:** Debian Trixie'deki Chromium binary'si Zero 2 W'nin ARM Cortex-A53 CPU'sunu desteklemiyor (veya yanlış algılıyor).

### 2. Display Hatası
```
xset: unable to open display ""
```

**Neden:** X server çalışmıyor veya DISPLAY değişkeni ayarlanmamış.

## ✅ Çözümler

### Çözüm 1: Kiosk Mode KULLANMA (ÖNERİLEN)

**Zero 2 W için en optimize çözüm:**

```bash
# Kiosk servisini devre dışı bırak
sudo systemctl stop kuvoz-kiosk
sudo systemctl disable kuvoz-kiosk

# Sadece web server çalışsın
sudo systemctl enable kuvoz-web
sudo systemctl start kuvoz-web
```

**Avantajları:**
- ✅ ~120MB RAM tasarrufu
- ✅ X server gereksiz (Lite OS'te sorun yok)
- ✅ Daha hızlı ve kararlı
- ✅ Mobil/tablet/PC'den tarayıcıyla erişim

**Erişim:**
```
Telefon/Tablet: http://192.168.1.50:8000
Laptop:         http://192.168.1.50:8000
```

### Çözüm 2: Hafif Browser Kullan

Chromium yerine **Midori** (en hafif browser):

```bash
# Midori kur
sudo apt install midori -y

# Yeni lite kiosk script'ini kullan
cd ~/kuvoz
chmod +x scripts/start-kiosk-lite.sh

# Test et
./scripts/start-kiosk-lite.sh
```

### Çözüm 3: X Server Kur (Lite OS kullanıyorsan)

```bash
# Minimal X server
sudo apt install xserver-xorg-core xinit openbox lightdm -y

# X'i başlat
startx &

# Veya LightDM ile otomatik başlat
sudo systemctl enable lightdm
sudo reboot
```

### Çözüm 4: VNC ile Uzaktan Erişim

```bash
# RealVNC kur
sudo apt install realvnc-vnc-server -y
sudo systemctl enable vncserver-x11-serviced
sudo systemctl start vncserver-x11-serviced

# Laptop/PC'den VNC ile bağlan
# VNC Viewer: 192.168.1.50:5900
```

## 📊 RAM Karşılaştırması (Zero 2 W için)

```
Web Server + Kiosk (Chromium):  ~400MB / 512MB  ❌ Riskli
Web Server + Kiosk (Midori):    ~320MB / 512MB  ⚠️  Sınırda
Web Server ONLY:                ~260MB / 512MB  ✅ Güvenli
```

## 🎯 Önerilen Kurulum (Zero 2 W için)

```bash
cd ~/kuvoz

# 1. Kiosk'u devre dışı bırak
sudo systemctl disable kuvoz-kiosk

# 2. Sadece web server
sudo systemctl enable kuvoz-web
sudo systemctl start kuvoz-web

# 3. Durumu kontrol et
make check-zero2w

# 4. Telefon/tablet/PC'den bağlan
# http://192.168.1.50:8000
```

## 💡 Bonus: Tailscale ile Uzaktan Erişim

Zero 2 W'de kiosk yerine **Tailscale** kullan:

```bash
# Tailscale kur
make tailscale-install

# Web arayüzünden QR kod oluştur
# http://192.168.1.50:8000 → "Uzaktan Erişim"

# Her yerden erişim
# https://kuvoz-xxxxx.tailnet-name.ts.net:8000
```

## 🔍 Debug Komutları

```bash
# X server çalışıyor mu?
ps aux | grep X

# DISPLAY değişkeni
echo $DISPLAY

# Browser kurulu mu?
which chromium-browser midori firefox-esr

# RAM kullanımı
free -h

# Servis durumu
systemctl status kuvoz-web
systemctl status kuvoz-kiosk
```

## 🎬 Sonuç

**Zero 2 W için en iyi seçenek:** Kiosk mode kullanma, sadece web server + uzaktan tarayıcı erişimi.
