#!/bin/bash
# Yeni Kuvoz Cihazı Başlangıç Kurulumu
# vet kullanıcısı oluşturma, hostname ayarlama, SSH yapılandırması

set -e

echo "🏥 Yeni Kuvoz Cihazı Kurulum Scripti"
echo "====================================="
echo ""

# Raspberry Pi kontrolü
if [[ ! -f /proc/cpuinfo ]] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "⚠️  Bu script Raspberry Pi için tasarlanmıştır"
    read -p "Devam etmek istiyor musunuz? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Root kontrolü
if [ "$EUID" -eq 0 ]; then
    echo "❌ Bu scripti root olarak çalıştırmayın"
    echo "   Normal kullanıcı ile çalıştırın, gerektiğinde sudo kullanılacak"
    exit 1
fi

# SSH public key'i kontrol et
SSH_KEY=""
if [ -f "$HOME/.ssh/authorized_keys" ]; then
    # Mevcut kullanıcının key'ini kopyala
    SSH_KEY=$(head -n 1 "$HOME/.ssh/authorized_keys" 2>/dev/null || true)
fi

if [ -z "$SSH_KEY" ]; then
    echo "⚠️  SSH public key bulunamadı"
    echo "   Lütfen admin bilgisayarınızdan public key'inizi sağlayın:"
    echo "   (Örnek: ssh-ed25519 AAAAC3... user@host)"
    read -p "Public key: " SSH_KEY
    
    if [ -z "$SSH_KEY" ]; then
        echo "❌ SSH key gerekli!"
        exit 1
    fi
fi

echo "✅ SSH Key bulundu"
echo ""

# ======================
# 1. VET KULLANICI OLUŞTUR
# ======================
echo "👤 1/3 - vet kullanıcısı oluşturuluyor..."

if id "vet" &>/dev/null; then
    echo "⚠️  vet kullanıcısı zaten mevcut"
    read -p "Mevcut kullanıcıyı yeniden yapılandır? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Kullanıcı oluşturma atlanıyor..."
    else
        sudo usermod -aG sudo vet
        echo "✅ vet kullanıcısı sudo grubuna eklendi"
    fi
else
    # Kullanıcı oluştur
    sudo useradd -m -s /bin/bash -G sudo vet
    echo "✅ vet kullanıcısı oluşturuldu"
fi

# Şifre ayarla
echo "🔐 vet kullanıcısı için şifre ayarlanıyor (vetmarketi)..."
echo 'vet:vetmarketi' | sudo chpasswd
echo "✅ Şifre: vetmarketi"

# SSH yapılandırması
echo "🔑 SSH yapılandırması..."
sudo mkdir -p /home/vet/.ssh
echo "$SSH_KEY" | sudo tee /home/vet/.ssh/authorized_keys > /dev/null
sudo chown -R vet:vet /home/vet/.ssh
sudo chmod 700 /home/vet/.ssh
sudo chmod 600 /home/vet/.ssh/authorized_keys
echo "✅ SSH key authentication yapılandırıldı"

# Sudoers yapılandırması (şifresiz sudo)
if [ ! -f /etc/sudoers.d/vet ]; then
    echo "vet ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/vet > /dev/null
    sudo chmod 440 /etc/sudoers.d/vet
    echo "✅ Şifresiz sudo yapılandırıldı"
fi

echo ""

# ======================
# 2. HOSTNAME AYARLA
# ======================
echo "🏷️  2/3 - Hostname yapılandırması..."

CURRENT_HOSTNAME=$(hostname)
echo "Mevcut hostname: $CURRENT_HOSTNAME"
echo ""
echo "Önerilen hostname'ler:"
echo "  1) kuvoz          (varsayılan, standart)"
echo "  2) vetmarketi     (genel)"
echo "  3) oktaykuvoz     (lokal test)"
echo "  4) vetmarketizero (uzak zero 2w)"
echo "  5) Özel hostname gir"
echo "  6) Değiştirme (mevcut kalsın)"
echo ""
read -p "Seçiminiz (1-6): " CHOICE

case $CHOICE in
    1)
        NEW_HOSTNAME="kuvoz"
        ;;
    2)
        NEW_HOSTNAME="vetmarketi"
        ;;
    3)
        NEW_HOSTNAME="oktaykuvoz"
        ;;
    4)
        NEW_HOSTNAME="vetmarketizero"
        ;;
    5)
        read -p "Yeni hostname: " NEW_HOSTNAME
        ;;
    6)
        NEW_HOSTNAME="$CURRENT_HOSTNAME"
        echo "Hostname değiştirilmeyecek"
        ;;
    *)
        NEW_HOSTNAME="kuvoz"
        echo "Varsayılan: kuvoz"
        ;;
esac

if [ "$NEW_HOSTNAME" != "$CURRENT_HOSTNAME" ]; then
    echo "Hostname '$CURRENT_HOSTNAME' → '$NEW_HOSTNAME' değiştiriliyor..."
    
    # Hostname dosyasını güncelle
    echo "$NEW_HOSTNAME" | sudo tee /etc/hostname > /dev/null
    
    # /etc/hosts dosyasını güncelle
    sudo sed -i "s/127.0.1.1.*$CURRENT_HOSTNAME/127.0.1.1\t$NEW_HOSTNAME/g" /etc/hosts
    
    # Eğer hiç 127.0.1.1 yoksa ekle
    if ! grep -q "127.0.1.1" /etc/hosts; then
        echo "127.0.1.1	$NEW_HOSTNAME" | sudo tee -a /etc/hosts > /dev/null
    fi
    
    # Hostname'i hemen uygula
    sudo hostnamectl set-hostname "$NEW_HOSTNAME"
    
    echo "✅ Hostname değiştirildi: $NEW_HOSTNAME"
    echo "   (Tam etkili olması için yeniden başlatma önerilir)"
else
    echo "✅ Hostname değiştirilmedi"
fi

echo ""

# ======================
# 3. SSH SERVER YAPILANDIRMASI
# ======================
echo "🔌 3/3 - SSH sunucu yapılandırması..."

# SSH servisinin çalıştığından emin ol
if ! systemctl is-active --quiet ssh; then
    echo "SSH servisi başlatılıyor..."
    sudo systemctl enable ssh
    sudo systemctl start ssh
    echo "✅ SSH servisi etkinleştirildi"
else
    echo "✅ SSH servisi zaten çalışıyor"
fi

# SSH yapılandırma önerileri
echo ""
echo "🔒 SSH Güvenlik Önerileri:"
echo "   - PasswordAuthentication yes (şifre ile giriş için)"
echo "   - PermitRootLogin no (root girişi kapalı)"
echo "   - Port 22 (standart)"
echo ""
echo "Mevcut SSH yapılandırmanızı kontrol etmek için:"
echo "   cat /etc/ssh/sshd_config | grep -E 'PasswordAuthentication|PermitRootLogin|Port '"
echo ""

# IP adresini göster
IP_ADDRESS=$(hostname -I | awk '{print $1}')
echo "📍 Cihaz IP Adresi: $IP_ADDRESS"
echo ""

# ======================
# ÖZET
# ======================
echo "✅ YENİ CİHAZ KURULUMU TAMAMLANDI!"
echo "=================================="
echo ""
echo "👤 Kullanıcı Bilgileri:"
echo "   Kullanıcı adı: vet"
echo "   Şifre:        vetmarketi"
echo "   Sudo yetkisi: ✓ (şifresiz)"
echo "   SSH key auth: ✓"
echo ""
echo "🏷️  Sistem Bilgileri:"
echo "   Hostname:     $NEW_HOSTNAME"
echo "   IP Adresi:    $IP_ADDRESS"
echo ""
echo "🔌 SSH Bağlantı Komutları:"
echo "   ssh vet@$NEW_HOSTNAME"
if [ "$NEW_HOSTNAME" != "kuvoz" ]; then
    echo "   ssh vet@kuvoz (diğer cihazlar için standart)"
fi
echo "   ssh vet@$IP_ADDRESS"
echo ""
echo "📦 Sıradaki Adımlar:"
echo "   1. Kuvoz uygulamasını kur:"
echo "      cd /home/vet"
echo "      git clone https://github.com/oktaycit/Kuvoz.git kuvoz"
echo "      cd kuvoz"
echo "      make auto-setup"
echo ""
echo "   2. Makefile'dan uzak yönetim için bu cihazı ekle:"
echo "      REMOTE_HOST_XXX := $NEW_HOSTNAME"
echo ""
echo "   3. Test et:"
echo "      ssh vet@$NEW_HOSTNAME 'echo \"✅ Bağlantı başarılı\"'"
echo ""

# Yeniden başlatma önerisi
if [ "$NEW_HOSTNAME" != "$CURRENT_HOSTNAME" ]; then
    echo "⚠️  Hostname değişikliği için yeniden başlatma önerilir:"
    echo "   sudo reboot"
    echo ""
    read -p "Şimdi yeniden başlatmak ister misiniz? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🔄 Sistem yeniden başlatılıyor..."
        sudo reboot
    fi
fi

echo "✨ Kurulum tamamlandı!"
