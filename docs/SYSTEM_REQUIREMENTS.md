# Kuvoz İnkübatör Sistem Gereksinimleri

## İşletim Sistemi

### Raspberry Pi OS Detayları
- **Version**: Trixie (Debian 13.1)
- **Codename**: `trixie`
- **Debian Version**: `13.1`
- **Architecture**: ARM64/ARM32 (Raspberry Pi uyumlu)

### Sistem Kontrolü
```bash
# OS versiyonunu kontrol etmek için:
cat /etc/os-release

# Çıktı örneği:
# VERSION_CODENAME=trixie
# DEBIAN_VERSION_FULL=13.1
```

## Donanım Gereksinimleri

### Raspberry Pi Modeli
- **Minimum**: Raspberry Pi 3B+
- **Önerilen**: Raspberry Pi 4B (4GB RAM+)
- **GPIO Pinleri**: 40-pin header gerekli

### Yazılım Gereksinimleri
- **İşletim Sistemi**: Raspberry Pi OS Trixie
- **Python**: 3.11+
- **İletişim**: wpasupplicant, network-manager, libnl-3-200
- **Web Arayüzü**: Chromium Browser (Kiosk Modu)

### Sensör Bağlantıları
- **DHT11/DHT22**: GPIO Pin 15 (Data)
- **DFRobot Oxygen**: I2C (SDA/SCL)
- **Relay Modülü**: 8-kanal, GPIO kontrollü

### GPIO Pin Kullanımı
```python
# GPIO pinleri (BCM numaralandırma)
outChannels = [5, 6, 13, 16, 19, 20, 21, 26]  # 8 röle kanalı
touch_bt = [5, 20, 21]  # Özel dokunmatik davranış
pinDht = 15  # DHT sensör veri pini
```

## Python Bağımlılıkları

### Ana Framework
```bash
# Kivy GUI framework
pip3 install kivy==2.1.0

# GPIO kontrolü
pip3 install RPi.GPIO

# DHT sensör sürücüsü
pip3 install Adafruit-DHT
```

### I2C Kütüphaneleri
```bash
# I2C desteği için
pip3 install smbus
```

### Sistem Kütüphaneleri
- `threading` (built-in)
- `time` (built-in)
- `os` (built-in)
- `sys` (built-in)

## Sistem Konfigürasyonu

### I2C Aktivasyonu
```bash
# Raspberry Pi Configuration Tool
sudo raspi-config
# → Interface Options → I2C → Enable

# Manuel aktivasyon
echo 'dtparam=i2c_arm=on' | sudo tee -a /boot/config.txt
sudo reboot
```

### GPIO İzinleri
```bash
# Kullanıcıyı gpio grubuna ekle
sudo usermod -a -G gpio $USER

# Root yetkisi gerektiren işlemler:
# - GPIO kontrolü
# - Sistem kapatma (shutdown)
```

### Otomatik Başlatma (İsteğe Bağlı)
```bash
# Systemd service dosyası oluştur
sudo nano /etc/systemd/system/kuvoz.service

[Unit]
Description=Kuvoz Incubator Control
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/Kuvoz
ExecStart=/usr/bin/python3 main3.py
Restart=always

[Install]
WantedBy=multi-user.target

# Servisi etkinleştir
sudo systemctl enable kuvoz.service
sudo systemctl start kuvoz.service
```

## Geliştirme Ortamı

### Önerilen IDE
- **VS Code** (Remote SSH ile)
- **Thonny** (Pi üzerinde yerel)
- **VNC Viewer** (grafik arayüz için)

### Remote Geliştirme
```bash
# SSH bağlantısı
ssh pi@raspberrypi.local

# X11 Forwarding (GUI test için)
ssh -X pi@raspberrypi.local
```

## Test ve Debug

### Donanım Testi
```bash
# GPIO testi
python3 -c "import RPi.GPIO as GPIO; print('GPIO OK')"

# I2C cihazları listele
i2cdetect -y 1

# DHT sensör testi
python3 -c "import Adafruit_DHT; print('DHT OK')"
```

### Kivy Testi
```bash
# Kivy kurulum testi
python3 -c "import kivy; print(f'Kivy {kivy.__version__}')"

# OpenGL desteği kontrolü
glxinfo | grep OpenGL
```

## Performans Optimizasyonu

### GPU Memory Split
```bash
# GPU bellek ayırma (grafik performansı için)
sudo raspi-config
# → Advanced Options → Memory Split → 128
```

### CPU Scaling
```bash
# CPU frekans yönetimi
echo 'performance' | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

### Swap Ayarları
```bash
# Swap boyutunu artır (GUI uygulamaları için)
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# CONF_SWAPSIZE=1024
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

## Güvenlik ve Bakım

### Güvenlik Duvarı
```bash
# UFW güvenlik duvarı (isteğe bağlı)
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 5900  # VNC için
```

### Sistem Güncellemeleri
```bash
# Düzenli güncelleme rutini
sudo apt update && sudo apt upgrade -y
sudo pip3 install --upgrade kivy RPi.GPIO Adafruit-DHT
```

### Log Dosyaları
```bash
# Sistem logları
sudo journalctl -u kuvoz.service -f

# Python hata logları
tail -f /var/log/syslog | grep python
```

## Sorun Giderme

### Yaygın Problemler

#### GPIO İzin Hatası
```bash
# Çözüm: Root yetkisi veya gpio grubu
sudo python3 main3.py
# veya
sudo usermod -a -G gpio $USER
```

#### I2C Bağlantı Hatası
```bash
# I2C durumunu kontrol et
sudo i2cdetect -y 1
# Beklenmeyen: 0x73 adresinde cihaz görünmeli
```

#### Kivy Display Hatası
```bash
# Display değişkeni ayarla
export DISPLAY=:0.0
# veya SSH için X11 forwarding
ssh -X pi@raspberrypi.local
```

#### Sensor Okuma Hatası
```bash
# DHT sensör bağlantısını kontrol et
# Pin 15'te 3.3V-5V arası gerilim olmalı
gpio readall | grep 15
```

Bu sistem gereksinimleri belgesi, projenin Raspberry Pi OS Trixie (Debian 13.1) üzerinde çalıştırılması için gerekli tüm konfigürasyonları içerir.