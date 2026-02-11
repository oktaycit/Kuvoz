# Kuvoz İnkübatör Kontrol Sistemi - Otomatik Başlatma

Bu belge Kuvoz sisteminin otomatik başlatma özelliklerini ve basitleştirilmiş kurulum sürecini açıklar.

## 🚀 Hızlı Başlangıç

### Tek Komutla Tam Kurulum

```bash
make auto-setup
```

Bu komut tüm sistemi kurar ve otomatik başlatma servislerini etkinleştirir.

### Alternatif Hızlı Kurulum

```bash
./quick-install.sh
```

veya

```bash
chmod +x auto-boot-setup.sh
./auto-boot-setup.sh
```

## 🌐 Web Arayüzü (Önerilen)

Kuvoz artık modern web arayüzü ile çalışır:

### Web Manuel Başlatma

```bash
make web-start          # Web sunucusu başlat
```

### Web Otomatik Başlatma

```bash
make web-autostart      # Boot'ta otomatik başla
```

### Web Arayüzü Özellikleri

- ✅ Gerçek zamanlı DHT11/DHT22 sensor verileri
- ✅ Socket.IO ile anlık güncellemeler
- ✅ Modern, responsive tasarım
- ✅ Cross-platform erişim (Windows, Mac, mobil)
- ✅ GPIO 15 üzerinden DHT sensör desteği

### Erişim Bilgileri

- **Yerel**: <http://localhost:8000>
- **Ağ**: http://[raspberry-pi-ip]:8000
- **Port**: 8000 (UFW firewall kuralları otomatik)

## 🖥️ Kiosk Modu

Raspberry Pi'yi tam ekran kiosk olarak kullanın:

### Manuel Başlatma

```bash
make kiosk-start        # Tam ekran kiosk modu
```

### Otomatik Başlatma

```bash
make kiosk-autostart    # Grafik oturumda otomatik başla
```

## 🔧 Servis Yönetimi

### Toplu Yönetim

```bash
make status-all         # Tüm servis durumları
make start-all          # Tüm servisleri başlat
make stop-all           # Tüm servisleri durdur
make restart-all        # Tüm servisleri yeniden başlat
make logs-all           # Tüm servis logları
```

### Ayrı Yönetim

```bash
# Web Sunucusu
make web-start          # Başlat
make web-stop           # Durdur
make web-status         # Durum
make web-logs           # Loglar

# Kiosk Modu
make kiosk-start        # Başlat
make kiosk-stop         # Durdur
make kiosk-status       # Durum
make kiosk-logs         # Loglar
```

## 📊 Durum Kontrolü

### Sistem Durumu

```bash
make system-status      # Detaylı sistem durumu
make status-all         # Servis durumları
```

### Test Komutları

```bash
make test-dht           # DHT sensör testi
make web-status         # Web sunucu durumu
```

## ⚙️ Sensör Konfigürasyonu

### DHT Sensör (GPIO 15)

- **DHT11**: Otomatik algılama
- **DHT22**: Otomatik algılama
- **Pin**: GPIO 15 (Physical Pin 10)
- **Kütüphane**: DHT_Native.py (Adafruit bağımsız)

### Sensör Test

```bash
make test-dht           # DHT sensör testi
python3 test_dht_real.py    # Native test
```

## 🛠️ Sorun Giderme

### Web Sunucusu Sorunları

```bash
make web-status         # Durum kontrol
make web-logs           # Log kontrolü
make web-restart        # Yeniden başlat
netstat -tlnp | grep 8000  # Port kontrolü
```

### Kiosk Sorunları

```bash
make kiosk-status       # Browser durumu
ps aux | grep chromium  # Chromium kontrolü
export DISPLAY=:0       # X11 display ayarla
```

### Systemd Servis Durumu

```bash
sudo systemctl status kuvoz-web.service
sudo systemctl status kuvoz-kiosk.service
sudo journalctl -u kuvoz-web.service -f
```

## 📁 Servis Dosyaları

### Systemd Servisleri

- `/etc/systemd/system/kuvoz-web.service` - Web sunucusu
- `/etc/systemd/system/kuvoz-kiosk.service` - Kiosk modu

### Script Dosyaları

- `scripts/start-kiosk.sh` - Kiosk başlatma script'i
- `auto-boot-setup.sh` - Otomatik boot kurulumu
- `quick-install.sh` - Hızlı kurulum

## 🔄 Yeniden Başlatma

Sistem yeniden başlatıldığında:

1. ✅ Web sunucusu otomatik başlar (kuvoz-web.service)
2. ✅ Grafik oturum açıldığında kiosk otomatik başlar (kuvoz-kiosk.service)
3. ✅ DHT sensör verileri gerçek zamanlı güncellenir

## 📱 Uzaktan Erişim

### Windows/Mac/Mobil Erişim

1. Raspberry Pi IP adresini bulun: `hostname -I`
2. Browser'da açın: `http://[pi-ip]:8000`
3. Gerçek zamanlı sensor verilerini görüntüleyin

### Firewall Ayarları

```bash
sudo ufw allow 8000     # Port 8000'i aç
sudo ufw status         # Durum kontrol
```

## 🗑️ Kaldırma

### Tüm Servisleri Kaldır

```bash
make uninstall-all      # Tüm systemd servisleri
```

### Sadece Web Servisi

```bash
sudo systemctl stop kuvoz-web.service
sudo systemctl disable kuvoz-web.service
sudo rm /etc/systemd/system/kuvoz-web.service
```

## 💡 İpuçları

1. **Web arayüzü Kivy'den daha güvenilir** - Socket.IO ile gerçek zamanlı güncelleme
2. **Cross-platform erişim** - Windows, Mac, mobil cihazlardan erişilebilir
3. **Otomatik başlatma** - Sistem reboot sonrası otomatik çalışır
4. **DHT sensör otomatik algılama** - DHT11/DHT22 arasında otomatik seçim
5. **Browser fallback** - Chromium yoksa Firefox kullanır

## 🔗 İlgili Dosyalar

- `web_server.py` - Flask web sunucusu
- `web/index.html` - Web arayüzü
- `lib/DHT_Native.py` - Native DHT kütüphanesi
- `Makefile` - Otomatik kurulum komutları
