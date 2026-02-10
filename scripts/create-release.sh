#!/bin/bash
# Kuvoz v3.0 İmaj Hazırlama ve Release Scripti
# Kullanım: ./create-release.sh

set -e  # Hata durumunda dur

VERSION="v3.0.0"
IMG_NAME="kuvoz-${VERSION}.img.gz"
RELEASE_DIR="$HOME/Desktop/kuvoz-release"

echo "🚀 Kuvoz ${VERSION} Release Hazırlığı"
echo "======================================"

# 1. Release dizini oluştur
mkdir -p "${RELEASE_DIR}"
cd "${RELEASE_DIR}"

echo ""
echo "📝 Adım 1: SD kartı hazırlayın"
echo "   - SSH ile cihaza bağlanın: ssh vet@kuvoz.local"
echo "   - Temizlik scriptini çalıştırın veya manuel temizleyin"
echo "   - Cihazı kapatın: sudo shutdown -h now"
echo "   - SD kartı Mac'e takın"
echo ""
read -p "SD kart hazır mı? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ İptal edildi"
    exit 1
fi

# 2. SD kartı bul
echo ""
echo "💾 Adım 2: SD kartı bulunuyor..."
diskutil list
echo ""
read -p "SD kart device'ı girin (örn: disk4): " DISK_NUM
DISK_DEV="/dev/disk${DISK_NUM}"
RDISK_DEV="/dev/rdisk${DISK_NUM}"

# Onay al
echo ""
echo "⚠️  DİKKAT: ${DISK_DEV} kullanılacak"
diskutil info ${DISK_DEV} | grep "Device / Media Name"
read -p "Devam edilsin mi? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ İptal edildi"
    exit 1
fi

# 3. İmaj oluştur
echo ""
echo "📸 Adım 3: İmaj oluşturuluyor..."
echo "   Bu işlem 10-20 dakika sürebilir..."

# Unmount
diskutil unmountDisk ${DISK_DEV}

# dd ile imaj oluştur
sudo dd if=${RDISK_DEV} of=kuvoz-${VERSION}.img bs=4m status=progress

echo "✅ İmaj oluşturuldu: $(ls -lh kuvoz-${VERSION}.img | awk '{print $5}')"

# 4. Sıkıştır
echo ""
echo "🗜️  Adım 4: İmaj sıkıştırılıyor..."
gzip -9 -v kuvoz-${VERSION}.img

echo "✅ Sıkıştırma tamamlandı: $(ls -lh ${IMG_NAME} | awk '{print $5}')"

# 5. Checksum oluştur
echo ""
echo "🔐 Adım 5: Checksum oluşturuluyor..."
shasum -a 256 ${IMG_NAME} > ${IMG_NAME}.sha256
cat ${IMG_NAME}.sha256

# 6. Release notes oluştur
echo ""
echo "📄 Adım 6: Release notes oluşturuluyor..."
cat > release-notes.md << 'EOF'
# Kuvoz v3.0.0 - Veteriner Web Interface

## 🎉 Yenilikler

### Web Arayüzü
- ✅ Modern, responsive tasarım (mobil uyumlu)
- ✅ Real-time hasta monitoring (WebSocket)
- ✅ Çoklu dil desteği (Türkçe, İngilizce, Almanca)
- ✅ Dokunmatik ekran optimizasyonu

### Uzaktan Erişim
- ✅ Tailscale entegrasyonu (güvenli VPN)
- ✅ Evden/ofisten hasta takibi
- ✅ Uzaktan sistem yönetimi

### Otomatik Sistemler
- ✅ Akıllı termoregülasyon
- ✅ Nem kontrol algoritması
- ✅ Güvenli sterilizasyon sistemi
- ✅ Nebulizer timing kontrolü

### Yeni Özellikler
- ✅ Hasta profil yönetimi
- ✅ Sistem güncellemeleri (OTA)
- ✅ Wi-Fi WPS desteği
- ✅ Gelişmiş hata yönetimi

## 📥 Kurulum

### Gereksinimler
- Raspberry Pi 3B+ veya üzeri (Pi 4B önerilir)
- 16GB+ microSD kart (32GB önerilir, Class 10)
- DHT22 sıcaklık/nem sensörü (GPIO 15)
- 8 kanal röle modülü
- İnternet bağlantısı (Wi-Fi veya Ethernet)

### Kurulum Adımları

#### Windows Kullanıcıları
1. [Balena Etcher](https://etcher.balena.io/) indirin ve kurun
2. `kuvoz-v3.0.0.img.gz` dosyasını indirin
3. SD kartı bilgisayara takın
4. Etcher'da: Flash from file → İmajı seçin → SD kartı seçin → Flash!
5. 5-10 dakika bekleyin
6. SD kartı Raspberry Pi'ye takın ve açın

#### Mac/Linux Kullanıcıları
```bash
# İmajı indirin
wget https://github.com/oktaycit/Kuvoz/releases/download/v3.0.0/kuvoz-v3.0.0.img.gz

# SD kartı bulun
diskutil list  # Mac
lsblk          # Linux

# İmajı yazın (Mac)
sudo dd if=kuvoz-v3.0.0.img.gz | gunzip | sudo dd of=/dev/rdisk4 bs=4m status=progress

# İmajı yazın (Linux)
sudo dd if=kuvoz-v3.0.0.img.gz | gunzip | sudo dd of=/dev/sdb bs=4M status=progress
```

### İlk Açılış
1. Raspberry Pi'yi açın (2-3 dakika bekleyin)
2. Tarayıcıda `http://kuvoz.local:5000` adresine gidin
3. Varsayılan kullanıcı: `vet` / şifre: `kuvoz2025`
4. Wi-Fi ayarlarını yapın (Settings → Wi-Fi)
5. Tailscale kurulumu (opsiyonel): Settings → Remote Access

## 🔧 v1/v2'den Upgrade

Mevcut Kuvoz v1 veya v2 kullanıcılarıysanız:

1. **Yedek Alın**: Mevcut ayarlarınızı kaydedin
2. **SD Kart Değiştirin**: Yeni SD karta v3.0 imajını yazın
3. **Donanım Kontrol**: Sensör bağlantılarını kontrol edin (GPIO 15 için DHT22)
4. **Ayarları Geri Yükleyin**: Hasta profillerinizi yeniden oluşturun

### v1/v2'den Farklar
- ❌ Kivy arayüzü kaldırıldı → ✅ Web arayüzü
- ❌ Lokal terminal → ✅ Uzaktan erişim
- ✅ Tüm GPIO pinleri aynı (uyumluluk)
- ✅ Sensör konfigürasyonu aynı

## 📞 Destek

- **E-posta**: destek@kuvoz.com (24 saat içinde yanıt)
- **Dokümantasyon**: [GitHub Wiki](https://github.com/oktaycit/Kuvoz)
- **Sorun Bildirimi**: [GitHub Issues](https://github.com/oktaycit/Kuvoz/issues)

## 🔒 Güvenlik

**SHA256 Checksum**: Dosya ile birlikte gelen `.sha256` dosyasını kontrol edin:
```bash
shasum -a 256 -c kuvoz-v3.0.0.img.gz.sha256
```

## 📜 Lisans

Bu yazılım mevcut Kuvoz kullanıcıları için ücretsizdir.
Ticari kullanım için lütfen iletişime geçin.

---

**Kuvoz v3.0.0** - Veteriner Rehabilitasyon Ünitesi
© 2025 Oktay Çit
EOF

echo "✅ Release notes oluşturuldu"

# 7. GitHub CLI kontrolü
echo ""
echo "🐙 Adım 7: GitHub Release..."
if ! command -v gh &> /dev/null; then
    echo "⚠️  GitHub CLI (gh) bulunamadı"
    echo "   Kurulum: brew install gh"
    echo ""
    echo "📦 Dosyalar hazır:"
    echo "   - ${IMG_NAME}"
    echo "   - ${IMG_NAME}.sha256"
    echo "   - release-notes.md"
    echo ""
    echo "Manuel olarak yükleyin:"
    echo "   https://github.com/oktaycit/Kuvoz/releases/new"
    exit 0
fi

# GitHub'a login kontrolü
if ! gh auth status &> /dev/null; then
    echo "🔐 GitHub'a giriş yapın:"
    gh auth login
fi

# Release oluştur
echo ""
read -p "GitHub Release oluşturulsun mu? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📤 Release yayınlanıyor..."
    gh release create ${VERSION} \
        --repo oktaycit/Kuvoz \
        --title "Kuvoz ${VERSION} - Veteriner Web Interface" \
        --notes-file release-notes.md \
        ${IMG_NAME} \
        ${IMG_NAME}.sha256
    
    echo ""
    echo "✅ Release yayınlandı!"
    echo "🔗 https://github.com/oktaycit/Kuvoz/releases/${VERSION}"
else
    echo ""
    echo "📦 Dosyalar hazır:"
    echo "   - ${IMG_NAME}"
    echo "   - ${IMG_NAME}.sha256"
    echo "   - release-notes.md"
    echo ""
    echo "Manuel yükleme:"
    echo "   https://github.com/oktaycit/Kuvoz/releases/new"
fi

echo ""
echo "🎉 Tamamlandı!"
