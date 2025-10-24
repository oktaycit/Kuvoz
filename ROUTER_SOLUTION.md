# Zyxel Router SSH Port Yönlendirme Sorunu - Alternatif Çözümler

## 🔧 Router Konfigürasyonu Gerekli

### ❌ Problem:
- SSH port 22 router tarafından bloklanıyor
- Port forwarding yapılmamış
- Zyxel router konfigürasyon gerekli

### ✅ Hızlı Çözümler:

## 1️⃣ GitHub Repository Yöntemi (ÖNERİLEN)

```bash
# Raspberry Pi'de:
git clone https://github.com/oktaycit/Kuvoz.git
cd Kuvoz
make web-deps-install
make web-platform-fix-full
```

## 2️⃣ USB/SD Kart Yöntemi

1. **USB'ye kopyala**: Tüm dosyaları USB'ye at
2. **Raspberry Pi'ye tak**: USB'yi Raspberry Pi'ye tak
3. **Kopyala**: `cp -r /media/usb0/Kuvoz /home/oktay/`

## 3️⃣ Yerel Ağ Üzerinden (Router LAN)

Eğer aynı yerel ağdaysanız:
```bash
# Raspberry Pi IP'sini bul (yerel ağ)
ping raspberrypi.local

# Yerel IP ile SCP
scp -r . pi@192.168.1.XXX:/home/oktay/kuvoz/
```

## 4️⃣ Cloud Drive Yöntemi

```bash
# Google Drive, Dropbox vs. kullan
# Raspberry Pi'de wget ile indir
wget https://drive.google.com/kuvoz.zip
unzip kuvoz.zip
```

## 5️⃣ Router Konfigürasyonu (Gelecek için)

### Zyxel Router SSH Port Forwarding:

1. **Router Admin Panel**: http://192.168.1.1
2. **Advanced → NAT → Port Forwarding**
3. **Yeni Kural**:
   - Service Name: SSH-Kuvoz
   - External Port: 22 (veya 2222)
   - Internal Port: 22
   - Internal IP: [Raspberry Pi IP]
   - Protocol: TCP

## 📋 Hızlı Setup GitHub Yöntemi:

```bash
# 1. GitHub'dan indir
git clone https://github.com/oktaycit/Kuvoz.git kuvoz

# 2. Klasöre gir
cd kuvoz

# 3. Python packages kur
make web-deps-install

# 4. DHT platform fix ile başlat
make web-platform-fix-full

# 5. Browser kiosk mode
make auto-browser
```

## 🔍 Network Troubleshooting:

```bash
# Router IP bulma
ipconfig | findstr Gateway

# Raspberry Pi ping test (yerel ağ)
ping raspberrypi.local
ping 192.168.1.XXX

# Port test
telnet 88.235.245.254 22
nc -v 88.235.245.254 22
```

## ⚡ Hemen Çalışır Çözüm:

**GitHub Repository güncelleyip Raspberry Pi'den çek!**

1. **Windows'ta**: Git commit & push
2. **Raspberry Pi'da**: Git clone/pull
3. **Setup**: Otomatik kurulum scriptleri hazır

Bu yöntem router konfigürasyonuna gerek kalmadan hemen çalışır! 🎉