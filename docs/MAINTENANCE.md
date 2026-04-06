# Kuvoz Sistem Bakımı ve Uzun Süreli Çalışma Kılavuzu

## 📋 İçindekiler
- [Genel Bakış](#genel-bakış)
- [Otomatik Bakım Sistemleri](#otomatik-bakım-sistemleri)
- [Manuel Bakım İşlemleri](#manuel-bakım-işlemleri)
- [Sorun Giderme](#sorun-giderme)
- [Performans İzleme](#performans-izleme)

---

## 🎯 Genel Bakış

Kuvoz sistemi **24/7 kesintisiz çalışma** için optimize edilmiştir. Uzun süreli çalışmada potansiyel sorunları önlemek için aşağıdaki otomatik ve manuel bakım işlemleri uygulanmaktadır.

### Potansiyel Sorunlar
1. **Chromium Cache Büyümesi**: Kiosk modunda cache sürekli büyüyebilir
2. **Log Dosyası Büyümesi**: Sürekli loglama disk alanını tüketebilir
3. **Memory Leak**: Uzun süreli çalışmada memory leak oluşabilir
4. **Dokunmatik Ekran Tepkisizliği**: Cache/memory sorunları tepkisizliğe yol açabilir

### Çözümler
- ✅ Chromium cache limitleri
- ✅ Otomatik log rotation
- ✅ Günlük otomatik bakım
- ✅ Memory temizleme

---

## 🤖 Otomatik Bakım Sistemleri

### 1. Chromium Cache Yönetimi

**Yapılandırma**: `scripts/start-kiosk.sh`

```bash
--disk-cache-size=52428800        # 50MB disk cache limiti
--media-cache-size=52428800       # 50MB media cache limiti
--aggressive-cache-discard        # Agresif cache temizleme
--disable-application-cache       # Application cache devre dışı
```

**Sonuç**: Cache maksimum ~100MB'da sabitlenir, sürekli büyümez.

---

### 2. Log Rotation Sistemi

**Yapılandırma**: `/etc/logrotate.d/kuvoz`

```
/home/oktay/kuvoz/logs/*.log {
    daily                  # Günlük rotation
    rotate 7              # Son 7 gün saklanır
    compress              # Eski loglar sıkıştırılır
    delaycompress         # En son log compress edilmez
    missingok             # Dosya yoksa hata verme
    notifempty            # Boş dosyaları rotate etme
    create 0644 oktay oktay
    maxsize 10M           # Maksimum log boyutu
}
```

**Log Dosyaları**:
- `kuvoz/logs/kiosk.log` - Kiosk modu logları
- `kuvoz/logs/maintenance.log` - Bakım işlemi logları

**Manuel Test**:
```bash
sudo logrotate -f /etc/logrotate.d/kuvoz
```

---

### 3. Günlük Otomatik Bakım

**Script**: `scripts/kuvoz-maintenance.sh`

**Çalışma Zamanı**: Her gece **03:00**

**Yapılan İşlemler**:
1. 7 günden eski cache dosyalarını sil
2. Kiosk servisini yeniden başlat (memory temizliği)
3. Bakım logunu güncelle

**Cron Job**: `/etc/cron.d/kuvoz-maintenance`
```
0 3 * * * root /home/oktay/kuvoz/scripts/kuvoz-maintenance.sh
```

**Manuel Çalıştırma**:
```bash
sudo /home/oktay/kuvoz/scripts/kuvoz-maintenance.sh
```

**Bakım Logunu Kontrol Etme**:
```bash
tail -20 /home/oktay/kuvoz/logs/maintenance.log
```

---

## 🛠️ Manuel Bakım İşlemleri

### Haftalık Bakım (Önerilen)

#### 1. Log Dosyalarını Kontrol Etme
```bash
# Log boyutlarını görüntüle
du -sh /home/oktay/kuvoz/logs/

# Son hataları kontrol et
tail -50 /home/oktay/kuvoz/logs/kiosk.log | grep -i error
```

#### 2. Cache Boyutunu Kontrol Etme
```bash
# Chromium cache boyutu
du -sh /home/oktay/kuvoz/chromium-data/

# 100MB'ı aşıyorsa manuel temizleme
sudo systemctl stop kuvoz-kiosk
rm -rf /home/oktay/kuvoz/chromium-data/*
sudo systemctl start kuvoz-kiosk
```

#### 3. Sistem Kaynaklarını Kontrol Etme
```bash
# Memory kullanımı
free -h

# Disk kullanımı
df -h

# CPU ve memory durumu
top -bn1 | head -20
```

---

### Aylık Bakım (Önerilen)

#### 1. Sistem Güncellemeleri
```bash
sudo apt update
sudo apt upgrade -y
sudo reboot  # Gerekirse
```

#### 2. Servis Durumunu Kontrol Etme
```bash
# Web server durumu
sudo systemctl status kuvoz-web

# Kiosk durumu
sudo systemctl status kuvoz-kiosk

# Servis başarısızlıklarını kontrol et
journalctl -u kuvoz-web --since "1 month ago" | grep -i failed
journalctl -u kuvoz-kiosk --since "1 month ago" | grep -i failed
```

#### 3. Sensor Kalibrasyonu
```bash
# DHT sensor test
make test-dht

# Oksijen sensörü test
make test-oxygen

# Tüm sistem testi
make test
```

---

## 🔧 Sorun Giderme

### Sorun 1: Dokunmatik Ekran Tepki Vermiyor

**Belirtiler**: Buton ve slider'lar çalışmıyor

**Çözüm**:
```bash
# 1. Cache'i temizle ve kiosk'u yeniden başlat
sudo systemctl stop kuvoz-kiosk
rm -rf /home/oktay/kuvoz/chromium-data
sudo systemctl start kuvoz-kiosk

# 2. Çalışmazsa sistem reboot
sudo reboot

# 3. Touch event'lerin aktif olduğunu kontrol et
ps aux | grep chromium | grep touch-events
```

**Önleme**: Günlük otomatik bakım zaten bunu önlemeli.

---

### Sorun 2: Sistem Yavaşladı

**Belirtiler**: Genel yavaşlık, gecikmeler

**Kontroller**:
```bash
# 1. Memory kullanımı
free -h
# Eğer swap kullanılıyorsa memory yetersiz

# 2. CPU kullanımı
top -bn1 | grep Cpu
# %100 CPU kullanımı varsa sorun var

# 3. Disk doluluk
df -h
# /dev/root %90 üzerindeyse disk dolu
```

**Çözümler**:
```bash
# Memory yetersizse servisleri yeniden başlat
sudo systemctl restart kuvoz-web
sudo systemctl restart kuvoz-kiosk

# Disk doluysa eski logları temizle
sudo find /home/oktay/kuvoz/logs -name "*.log.*" -mtime +7 -delete
sudo apt clean

# Son çare: Reboot
sudo reboot
```

---

### Sorun 3: Kiosk Açılmıyor / Siyah Ekran

**Kontroller**:
```bash
# 1. Web server çalışıyor mu?
curl -I http://localhost:8000
sudo systemctl status kuvoz-web

# 2. Kiosk servisi çalışıyor mu?
sudo systemctl status kuvoz-kiosk

# 3. X11 display var mı?
echo $DISPLAY
# :0 veya :1 görmeli
```

**Önemli Not**:
Ekran kararması her zaman uyku modu anlamına gelmez. 2026-04-06 tarihinde sahada görülen vakada ekran karanlık görünmesine rağmen:
- `lightdm` ve `Xorg` çalışıyordu
- `xset q` çıktısında screensaver `timeout: 0` idi
- `DPMS is Disabled` görünüyordu
- asıl sorun disk doluluğu nedeniyle Chromium'un başlayamamasıydı

Bu durumda kiosk loglarında tipik olarak şu hatalar görülür:

```bash
journalctl -u kuvoz-kiosk -n 50 --no-pager

# Tipik hata örnekleri:
# No space left on device (28)
# Failed to create socket directory
# Failed to create a ProcessSingleton for your profile directory
```

Bu belirtiler varsa sorun uyku değil, depolama alanıdır.

**Çözümler**:
```bash
# Web server başlat
sudo systemctl start kuvoz-web

# Kiosk başlat
sudo systemctl start kuvoz-kiosk

# Display sorunu varsa
export DISPLAY=:0
sudo systemctl restart kuvoz-kiosk

# Chromium loglarını kontrol et
journalctl -u kuvoz-kiosk -n 50
```

---

### Sorun 4: Sensör Değerleri Hatalı

**Belirtiler**: Sensör değerleri "--" veya mantıksız

**Kontroller**:
```bash
# DHT sensor test
make test-dht

# Oksijen sensörü test
make test-oxygen

# GPIO bağlantıları
gpio readall
```

**Çözümler**:
```bash
# Web server'ı yeniden başlat
sudo systemctl restart kuvoz-web

# Sensor pin'lerini kontrol et
# DHT: GPIO 15 (Physical Pin 10)
# I2C: SDA=GPIO2 (Pin 3), SCL=GPIO3 (Pin 5)

# Kablolama sorunlarını kontrol et
```

---

## 📊 Performans İzleme

### Sistem Sağlık Kontrolü

**Hızlı Kontrol Scripti**:
```bash
#!/bin/bash
echo "=== Kuvoz Sistem Sağlık Kontrolü ==="
echo ""
echo "📊 Memory Kullanımı:"
free -h | grep Mem
echo ""
echo "💾 Disk Kullanımı:"
df -h | grep "/$"
echo ""
echo "📁 Log Boyutu:"
du -sh /home/oktay/kuvoz/logs/
echo ""
echo "🗂️ Cache Boyutu:"
du -sh /home/oktay/kuvoz/chromium-data/
echo ""
echo "🌐 Web Server:"
systemctl is-active kuvoz-web
echo ""
echo "🖥️ Kiosk:"
systemctl is-active kuvoz-kiosk
echo ""
echo "🌡️ CPU Sıcaklığı:"
vcgencmd measure_temp
```

**Kullanım**:
```bash
# Scripti kaydet
nano ~/kuvoz-health-check.sh
chmod +x ~/kuvoz-health-check.sh

# Çalıştır
~/kuvoz-health-check.sh
```

---

### İzlenecek Metrikler

| Metrik | Normal | Uyarı | Kritik |
|--------|--------|-------|--------|
| Memory Kullanımı | < 60% | 60-80% | > 80% |
| Disk Kullanımı | < 70% | 70-85% | > 85% |
| CPU Sıcaklığı | < 60°C | 60-75°C | > 75°C |
| Cache Boyutu | < 100MB | 100-200MB | > 200MB |
| Log Boyutu | < 10MB | 10-50MB | > 50MB |

**Kritik seviyede eylem**:
```bash
sudo systemctl restart kuvoz-web kuvoz-kiosk
# veya
sudo reboot
```

---

## 📅 Bakım Takvimi

### Günlük (Otomatik)
- ✅ 03:00 - Otomatik bakım scripti çalışır
- ✅ Log rotation kontrolü
- ✅ Cache temizliği
- ✅ Kiosk yeniden başlatma

### Haftalık (Manuel - Önerilen)
- 🔍 Log dosyalarını kontrol et
- 🔍 Cache boyutunu kontrol et
- 🔍 Sistem kaynaklarını kontrol et
- 🔍 Sensör değerlerini doğrula

### Aylık (Manuel - Önerilen)
- 🔄 Sistem güncellemelerini yap
- 🔄 Servis durumunu kontrol et
- 🔄 Sensor kalibrasyonu yap
- 🔄 GPIO bağlantılarını kontrol et

### 6 Aylık (Tavsiye)
- 🔧 Donanım kontrolü (fan temizliği, kablo kontrolü)
- 🔧 Sistem yedekleme
- 🔧 Güvenlik güncellemeleri

---

## 🔐 Yedekleme ve Geri Yükleme

### Ayarları Yedekleme
```bash
# Ayarları yedekle
make backup

# Yedek dosyası: kuvoz/backup/failure.dat.backup.YYYYMMDD_HHMMSS
```

### Ayarları Geri Yükleme
```bash
# Son yedeği geri yükle
make restore

# Belirli bir yedeği geri yükle
cp kuvoz/backup/failure.dat.backup.20250111_103000 kuvoz/failure.dat
sudo systemctl restart kuvoz-web
```

### Tam Sistem Yedekleme
```bash
# Tüm projeyi yedekle (SD karta)
sudo tar -czf /media/usb/kuvoz-backup-$(date +%Y%m%d).tar.gz /home/oktay/kuvoz

# Sadece ayar ve logları yedekle
tar -czf kuvoz-settings-$(date +%Y%m%d).tar.gz \
    /home/oktay/kuvoz/failure.dat \
    /home/oktay/kuvoz/logs/
```

### Küçültülmüş İmaj Üretme
Raspberry Pi üzerinde doğrudan yeniden yazılabilir bir kurulum imajı üretmek için:

```bash
chmod +x ~/build_portable_image_remote.sh
nohup ~/build_portable_image_remote.sh > ~/build_portable_image_nohup.log 2>&1 < /dev/null &
```

Bu script şu akışı uygular:
- boş alanı sıfırlayıp sıkıştırma verimini artırır
- `/dev/mmcblk0` üzerinden ham imaj alır
- `PiShrink` ile küçültülmüş `.img` üretir
- çıktıyı `.img.xz` olarak sıkıştırır
- yeterli alan varsa USB belleğe checksum ile kopyalar

İlerlemeyi izlemek için:

```bash
tail -f ~/build_portable_image_nohup.log
```

---

## 📞 Destek ve İletişim

**Sorunlarla karşılaşırsanız**:

1. **Logları kontrol edin**:
   ```bash
   journalctl -u kuvoz-web -n 100
   journalctl -u kuvoz-kiosk -n 100
   ```

2. **GitHub Issues**: https://github.com/oktaycit/Kuvoz/issues

3. **Troubleshooting**:
   ```bash
   make troubleshoot
   ```

---

## 📚 İlgili Belgeler

- [README.md](README.md) - Genel proje bilgisi
- [KUVOZ_KULLANIM_KLAVUZU.md](KUVOZ_KULLANIM_KLAVUZU.md) - Kullanım kılavuzu
- [README_WEB.md](README_WEB.md) - Web arayüzü dökümantasyonu
- [SYSTEM_REQUIREMENTS.md](SYSTEM_REQUIREMENTS.md) - Sistem gereksinimleri

---

**Son Güncelleme**: 2025-01-11
**Versiyon**: 3.1.0
