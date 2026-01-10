# Yeni Kuvoz Cihazı Kurulum Rehberi

Bu doküman yeni bir Raspberry Pi cihazını Kuvoz sistemi için yapılandırma sürecini açıklar.

## Hızlı Kurulum (Otomatik)

### 1. Raspberry Pi'da Çalıştır

Yeni Raspberry Pi cihazında (mevcut kullanıcı ile):

```bash
cd /home/pi  # veya mevcut kullanıcı dizini
git clone https://github.com/oktaycit/Kuvoz.git kuvoz
cd kuvoz
make setup-new-device
```

Script otomatik olarak:
- ✅ `vet` kullanıcısı oluşturur (sudo yetkili)
- ✅ Şifre ayarlar: `vetmarketi`
- ✅ SSH key authentication yapılandırır
- ✅ Hostname ayarlar (interaktif seçim)
- ✅ SSH sunucu etkinleştirir

### 2. Hostname Seçenekleri

Script çalıştığında hostname seçimi yapabilirsiniz:
1. `vetmarketi` (genel, varsayılan)
2. `oktaykuvoz` (lokal test cihazı)
3. `vetmarketizero` (Raspberry Pi Zero 2W)
4. Özel hostname
5. Mevcut hostname'i koru

### 3. Test Et

Kurulum tamamlandıktan sonra:

```bash
# Admin bilgisayarından test et
ssh vet@vetmarketi          # Hostname ile
ssh vet@192.168.1.XXX       # IP adresi ile

# Şifresiz giriş olmalı (SSH key authentication)
```

## Manuel Kurulum

Otomatik script kullanmak istemiyorsanız:

### 1. vet Kullanıcısı Oluştur

```bash
# Raspberry Pi'da çalıştır
sudo useradd -m -s /bin/bash -G sudo vet
echo 'vet:vetmarketi' | sudo chpasswd

# Şifresiz sudo
echo "vet ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/vet
sudo chmod 440 /etc/sudoers.d/vet
```

### 2. SSH Key Ekle

Admin bilgisayarınızdan:

```bash
# Public key'i kopyala
cat ~/.ssh/id_ed25519.pub

# Raspberry Pi'da oluştur
sudo mkdir -p /home/vet/.ssh
echo "ssh-ed25519 AAAA... user@host" | sudo tee /home/vet/.ssh/authorized_keys
sudo chown -R vet:vet /home/vet/.ssh
sudo chmod 700 /home/vet/.ssh
sudo chmod 600 /home/vet/.ssh/authorized_keys
```

### 3. Hostname Ayarla

```bash
# Raspberry Pi'da
sudo hostnamectl set-hostname vetmarketi

# /etc/hosts güncelle
sudo nano /etc/hosts
# 127.0.1.1 satırını düzenle: 127.0.1.1   vetmarketi

# Yeniden başlat
sudo reboot
```

### 4. SSH Sunucu Etkinleştir

```bash
sudo systemctl enable ssh
sudo systemctl start ssh
```

## Kuvoz Uygulaması Kurulumu

Cihaz hazır olduktan sonra:

```bash
# vet kullanıcısı ile giriş yap
ssh vet@vetmarketi

# Kuvoz kurulumu
cd /home/vet
git clone https://github.com/oktaycit/Kuvoz.git kuvoz
cd kuvoz

# Tam otomatik kurulum
make auto-setup

# Veya adım adım
make web-install        # Bağımlılıkları kur
make web-service        # Web sunucu servisi
make kiosk-service      # Kiosk modu (isteğe bağlı)
```

## Uzak Yönetim Entegrasyonu

Admin bilgisayarınızda Makefile'a yeni cihazı ekleyin:

```makefile
# Makefile
REMOTE_USER := vet
REMOTE_HOST_LOCAL := oktaykuvoz
REMOTE_HOST_UZAK := vetmarketizero
REMOTE_HOST_YENİ := vetmarketi      # Yeni cihaz ekle
REMOTE_PATH := /home/$(REMOTE_USER)/kuvoz
```

Yeni deployment komutu ekleyin:

```makefile
.PHONY: deploy-yeni
deploy-yeni:
	@echo "📦 Yeni cihaza deployment..."
	@rsync -avz --exclude 'venv' --exclude '__pycache__' \
		$(PROJECT_DIR)/ $(REMOTE_USER)@$(REMOTE_HOST_YENİ):$(REMOTE_PATH)/
	@ssh $(REMOTE_USER)@$(REMOTE_HOST_YENİ) "cd $(REMOTE_PATH) && sudo systemctl restart kuvoz-web"
	@echo "✅ Deployment tamamlandı"
```

## Kontrol Listesi

Yeni cihaz kurulumunda kontrol edin:

- [ ] `vet` kullanıcısı oluşturuldu
- [ ] Şifre: `vetmarketi` çalışıyor
- [ ] SSH key authentication aktif (şifresiz giriş)
- [ ] Sudo yetkisi var (şifresiz)
- [ ] Hostname doğru ayarlandı
- [ ] SSH sunucu çalışıyor
- [ ] Admin bilgisayardan SSH bağlantısı test edildi
- [ ] Kuvoz deposu klonlandı
- [ ] Web sunucu kuruldu ve çalışıyor
- [ ] Servisler otomatik başlatılıyor

## Varsayılan Ayarlar

| Parametre | Değer |
|-----------|-------|
| Kullanıcı | `vet` |
| Şifre | `vetmarketi` |
| Home | `/home/vet` |
| Proje | `/home/vet/kuvoz` |
| Hostname | `vetmarketi` (varsayılan) |
| SSH Port | 22 |
| Web Port | 8000 |

## Sorun Giderme

### SSH Bağlantı Hatası

```bash
# Cihazın IP adresini bul
hostname -I

# Doğrudan IP ile test et
ssh vet@192.168.1.XXX

# SSH key debug
ssh -v vet@vetmarketi
```

### Kullanıcı Bulunamadı

```bash
# vet kullanıcısının varlığını kontrol et
id vet

# Kullanıcı yoksa oluştur
sudo useradd -m -s /bin/bash -G sudo vet
```

### Hostname Çalışmıyor

```bash
# Hostname kontrolü
hostname
hostnamectl status

# /etc/hosts kontrolü
cat /etc/hosts | grep 127.0.1.1

# mDNS ile dene
ssh vet@vetmarketi.local
```

### Sudo Şifre Soruyor

```bash
# Sudoers dosyasını kontrol et
sudo cat /etc/sudoers.d/vet

# Yoksa oluştur
echo "vet ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/vet
sudo chmod 440 /etc/sudoers.d/vet
```

## Güvenlik Notları

### SSH Key Yönetimi

- Public key'i serbestçe paylaşabilirsiniz
- Private key'i (`~/.ssh/id_ed25519`) ASLA paylaşmayın
- Farklı admin bilgisayarlar için farklı key'ler kullanın

### Şifre Politikası

- Varsayılan şifre: `vetmarketi` (basit, test/demo için)
- Üretim ortamında daha güçlü şifre kullanın
- SSH key authentication tercih edilir

### Ağ Güvenliği

- SSH portunu varsayılan 22'den değiştirmeyi düşünün
- Firewall kuralları ekleyin
- Sadece güvenilir ağlardan erişim sağlayın

## İlgili Komutlar

```bash
# Cihaz durumu
make status-local      # Lokal cihaz
make status-uzak       # Uzak cihaz

# Deployment
make deploy-all        # Tüm cihazlar
make deploy-local      # Lokal cihaz

# Log izleme
make logs-local        # Lokal cihaz logları
make logs-uzak         # Uzak cihaz logları

# SSH bağlantısı
make ssh-local         # Lokal cihaza bağlan
make ssh-uzak          # Uzak cihaza bağlan
```

## Yardım

Detaylı yardım için:

```bash
make help              # Tüm komutlar
make remote-help       # Uzak yönetim komutları
```

Script ile ilgili sorunlar:
- Script dosyası: `setup-new-device.sh`
- İzinler: `chmod +x setup-new-device.sh`
- Manuel çalıştırma: `./setup-new-device.sh`
