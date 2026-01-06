# Raspberry Pi Zero 2 W - Optimizasyon Rehberi

## 🎯 Hızlı Başlangıç (Tek Komut)

```bash
cd ~/kuvoz
make setup-zero2w
```

Bu komut **otomatik olarak**:
- ✅ Minimal bağımlılıkları kurar
- ✅ Web servisini konfigüre eder
- ✅ AI modülünü devre dışı bırakır (~30MB RAM)
- ✅ Kiosk modunu devre dışı bırakır (~120MB RAM)
- ✅ RAM optimizasyonlarını uygular
- ✅ Sistemi tam optimize eder

## 📊 Yeni Makefile Komutları

### Durum Kontrolü
```bash
make status-zero2w
```
Gösterir:
- 💾 RAM kullanımı (kullanılan/toplam)
- 🌐 Web servisi durumu + URL
- 🖥️ Kiosk modu durumu (önerilen: kapalı)
- 🤖 AI modülü durumu (önerilen: kapalı)
- 🌡️ CPU sıcaklığı
- 📡 Port 8000 durumu
- 📊 Disk kullanımı

### Sistem Analizi
```bash
make check-zero2w
```
Detaylı sistem bilgileri:
- RAM/Swap durumu
- OS tipi (Lite vs Desktop)
- GPU memory ayarı
- Sensör tespiti
- Servis durumları
- Optimizasyon önerileri

### AI Modülünü Devre Dışı Bırak
```bash
make disable-ai
```
- `ENABLE_AI = False` ayarlar
- ~30MB RAM tasarrufu
- Log spam'i önler

### Kiosk Modunu Devre Dışı Bırak
```bash
make disable-kiosk
```
- Systemd servisini durdurur
- ~120MB RAM tasarrufu
- Uzaktan erişim bilgisi gösterir

### RAM Optimizasyonları
```bash
make optimize-zero2w
```
- GPU memory: 128MB → 64MB
- Swap: 2GB → 100MB
- Log rotation ayarları
- Gereksiz servis kontrolü

## 🚫 Sorunlar ve Nedenleri

### 1. NEON SIMD Hatası
```
The hardware on this system lacks support for NEON SIMD extensions.
```

**Neden:** Debian Trixie'deki Chromium binary'si Zero 2 W'nin ARM Cortex-A53 CPU'sunu desteklemiyor.

**Çözüm:** Kiosk mode kullanma (make disable-kiosk)

### 2. Display Hatası
```
xset: unable to open display ""
```

**Neden:** X server çalışmıyor veya DISPLAY değişkeni ayarlanmamış (Lite OS'te normal).

**Çözüm:** X server yerine uzaktan tarayıcı erişimi

### 3. AI Log Spam
```
⚠️  AI update skipped - no frame available yet (her saniye)
```

**Neden:** AI modülü aktif ama kamera yok.

**Çözüm:** make disable-ai

### 4. Port Çakışması
```
Port 8000 is in use by another program
```

**Neden:** Systemd servisi zaten çalışıyor, manuel `make web-start` çakışır.

**Çözüm:** `sudo systemctl restart kuvoz-web` kullan

## ✅ Önerilen Kurulum (Adım Adım)

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

### Optimize Öncesi
```
Sistem (Lite):          ~180MB
Web Server:             ~80MB
AI Module (aktif):      ~30MB
Kiosk (Chromium):       ~120MB
─────────────────────────────
Toplam:                 ~410MB / 512MB  ❌ Riskli
```

### Optimize Sonrası (`make setup-zero2w`)
```
Sistem (Lite):          ~180MB
Web Server:             ~80MB
AI Module (kapalı):     ~0MB   ✅
Kiosk (kapalı):         ~0MB   ✅
─────────────────────────────
Toplam:                 ~260MB / 512MB  ✅ Güvenli
Boş RAM:                ~252MB          ✅ Rahat
```

### Karşılaştırma Tablosu
| Yapılandırma | RAM Kullanımı | Durum |
|--------------|---------------|-------|
| Web + AI + Kiosk | ~410MB / 512MB | ❌ Riskli, donmalar olabilir |
| Web + AI | ~290MB / 512MB | ⚠️ Sınırda |
| Web + Kiosk | ~380MB / 512MB | ❌ Riskli |
| **Web ONLY** | **~260MB / 512MB** | **✅ Optimal** |

## 🎯 Tam Otomatik Kurulum (Önerilen)

```bash
cd ~/kuvoz
git pull                  # Son güncellemeleri çek
make setup-zero2w         # Tek komutla kurulum
sudo reboot               # Optimizasyonlar için yeniden başlat
```

Reboot sonrası:
```bash
make status-zero2w        # Durum kontrolü
# Web arayüzü: http://192.168.1.50:8000
```

## 📋 Manuel Kurulum (Adım Adım)

```bash
cd ~/kuvoz
git pull

# 1. Minimal bağımlılıklar
make deps-minimal

# 2. Web bağımlılıkları
make web-deps

# 3. AI'ı kapat (RAM tasarrufu)
make disable-ai

# 4. Kiosk'u kapat (RAM tasarrufu)
make disable-kiosk

# 5. Web servisini kur
make web-service

# 6. RAM optimizasyonları
make optimize-zero2w

# 7. Yeniden başlat
### Sistem Durumu
```bash
# Kapsamlı durum raporu
make status-zero2w

# Detaylı sistem analizi
make check-zero2w

# RAM kullanımı
free -h

# CPU sıcaklığı
vcgencmd measure_temp

# Disk kullanımı
df -h
```

### Servis  ve Öneriler

### ✅ Zero 2 W İçin En İyi Yapılandırma

**Tek Komut:**
```bash
make setup-zero2w
```

**Bu yapılandırma:**
- ✅ ~260MB RAM kullanımı (512MB'nin %50'si)
- ✅ ~250MB boş RAM (acil durumlar için)
- ✅ Stabil ve hızlı çalışma
- ✅ DHT sensör simülasyonu (bağlı değilse)
- ✅ Uzaktan erişim (telefon/tablet/laptop)
- ✅ Log spam yok
- ✅ Otomatik yeniden başlatma

### 📱 Erişim Yöntemleri

**Yerel Ağ:**
```
http://192.168.1.50:8000
```

**Tailscale (Her Yerden):**
```bash
make tailscale-install
# Web arayüzünden QR kod ile bağlan
```

### ⚠️ YAPMA

❌ Kiosk mode açma (RAM problemi)
❌ AI modülünü aktif etme (gereksiz)
❌ Desktop OS kurma (Lite kullan)
❌ `make web-start` komutunu servis çalışırken çalıştırma

### ✅ YAP

✅ `make setup-zero2w` ile kur
✅ `make status-zero2w` ile kontrol et
✅ Telefon/tablet ile bağlan
✅ Lite OS kullan
✅ DHT sensör yoksa simülasyon modunda çalış

### 🔧 Sorun Çözme

| Sorun | Çözüm |
|-------|-------|
| Port 8000 çakışması | `sudo systemctl restart kuvoz-web` |
| AI log spam | `make disable-ai` |
| Yüksek RAM | `make status-zero2w` kontrol et |
| DHT sensör hatası | Simülasyon modu otomatik aktif olur |
| Kiosk NEON hatası | `make disable-kiosk` |

**Destek:** Tüm komutları görmek için `make help`
sudo systemctl status kuvoz-web

# Logları izle
sudo journalctl -u kuvoz-web -f

# Son 50 satır
sudo journalctl -u kuvoz-web -n 50

# Port kontrolü
netstat -tlnp | grep 8000
```

### Modül Durumları
```bash
# AI modülü durumu
grep "^ENABLE_AI" ~/kuvoz/web_server.py

# Kiosk servisi durumu
systemctl status kuvoz-kiosk

# Çalışan Python processleri
ps aux | grep python3 "Uzaktan Erişim"

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
