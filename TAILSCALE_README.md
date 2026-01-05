# Tailscale Uzaktan Erişim - Kuvoz

Kuvoz veteriner inkübatörüne internet üzerinden güvenli erişim için Tailscale VPN entegrasyonu.

## 🎯 Özellikler

- ✅ **Kolay Kurulum**: Tek tıkla Tailscale kurulumu
- 📱 **QR Kod Girişi**: Mobil cihazdan QR kod ile hızlı bağlantı
- 🔒 **Güvenli Bağlantı**: End-to-end şifreli VPN tüneli
- 🌐 **Her Yerden Erişim**: Internet bağlantısı olan her yerden erişim
- 🚀 **Kolay Kullanım**: Kullanıcı dostu web arayüzü

## 📋 Gereksinimler

- Raspberry Pi (Kuvoz sistemi kurulu)
- Internet bağlantısı
- Tailscale hesabı (ücretsiz)

## 🚀 Kurulum

### 1. Komut Satırından Kurulum

```bash
# QR kod bağımlılıklarını kur (önce bu!)
make tailscale-deps

# Tailscale'i kur
make tailscale-install

# Bağlantıyı başlat
make tailscale-up

# Durumu kontrol et
make tailscale-status
```

**Not**: Raspberry Pi OS Trixie, PEP 668 nedeniyle `pip3 install` yerine sistem paketlerini kullanır.

### 2. Web Arayüzünden Kurulum

1. Kuvoz ana sayfasında **"Uzaktan Erişim"** butonuna tıklayın
2. **"Tailscale'i Kur"** butonuna basın (kurulu değilse)
3. **"Bağlantı Kur"** butonuna basın
4. QR kod ekranda görünecektir

## 📱 Mobil Cihazdan Bağlanma

### Adım 1: QR Kod Okutma
1. Kuvoz web arayüzünde QR kod görüntülenir
2. Mobil cihazınızın kamerasıyla QR kodu okutun
3. Tailscale giriş sayfası açılacak

### Adım 2: Tailscale Hesabı
- **Hesabınız varsa**: Giriş yapın
- **Hesabınız yoksa**: Ücretsiz hesap oluşturun (1 dakika sürer)
  - Google, Microsoft veya email ile kayıt

### Adım 3: Cihazı Onaylama
1. Tailscale hesabınıza giriş yapın
2. "Kuvoz-XXXXX" cihazını ağınıza ekleyin
3. Onaylayın

### Adım 4: Tailscale Uygulaması
1. Mobil cihazınıza Tailscale uygulamasını indirin:
   - **iOS**: App Store'dan "Tailscale"
   - **Android**: Play Store'dan "Tailscale"
2. Aynı hesapla giriş yapın
3. VPN'i aktifleştirin

### Adım 5: Kuvoz'a Erişim
1. Tailscale VPN açıkken
2. Tarayıcıda Tailscale IP adresini açın:
   ```
   http://100.x.x.x:8000
   ```
3. Kuvoz kontrol paneline erişebilirsiniz! 🎉

## 🔧 Kullanım

### Bağlantıyı Başlatma
```bash
make tailscale-up
```
veya web arayüzünden **"Bağlantı Kur"** butonu

### Bağlantıyı Kesme
```bash
make tailscale-down
```
veya web arayüzünden **"Bağlantıyı Kes"** butonu

### Durumu Kontrol Etme
```bash
make tailscale-status
```

### IP Adresini Öğrenme
```bash
tailscale ip -4
```

## 📊 Web Arayüzü

Tailscale sayfası (`/tailscale.html`) şu bilgileri gösterir:

- ✅ **Kurulum Durumu**: Tailscale kurulu mu?
- 🔗 **Bağlantı Durumu**: Aktif bağlantı var mı?
- 🌐 **IP Adresleri**: Uzaktan erişim için IP listesi
- 📱 **QR Kod**: Mobil bağlantı için QR kod
- 🔄 **Canlı Güncelleme**: Otomatik durum kontrolü

## 🛡️ Güvenlik

### Tailscale Güvenlik Özellikleri
- **End-to-end Şifreleme**: WireGuard protokolü
- **Zero Trust**: Sadece yetkili cihazlar erişebilir
- **NAT Traversal**: Router ayarı gerektirmez
- **Audit Log**: Tüm bağlantılar kayıt altında

### Kuvoz Güvenlik Önerileri
- Tailscale hesap şifrenizi güçlü tutun
- İki faktörlü kimlik doğrulama (2FA) kullanın
- Kullanılmayan cihazları Tailscale panelinden kaldırın
- Bağlantı kullanmadığınızda `tailscale down` yapın

## 🐛 Sorun Giderme

### Tailscale Kurulumu Başarısız
```bash
# Manuel kurulum deneyin
curl -fsSL https://tailscale.com/install.sh | sh
```

### Bağlantı Kurulmuyor
```bash
# Servisi yeniden başlatın
sudo systemctl restart tailscaled

# Durumu kontrol edin
sudo systemctl status tailscaled
```

### QR Kod Oluşmuyor
```bash
# Debian sistem paketlerini kullanın (önerilen)
make tailscale-deps

# Veya manuel kurulum
sudo apt install python3-qrcode python3-pil

# Veya (riskli, önerilmez)
pip3 install --break-system-packages qrcode[pil] pillow
```

### Auth URL Açılmıyor
1. QR kod yerine linki manuel kopyalayın
2. Tarayıcıda açın
3. Giriş yapıp cihazı onaylayın

### IP Adresi Görünmüyor
```bash
# Bağlantıyı yeniden başlatın
sudo tailscale down
sudo tailscale up
```

## 📚 Ek Kaynaklar

- [Tailscale Dokümantasyonu](https://tailscale.com/kb/)
- [Tailscale Mobil Uygulamalar](https://tailscale.com/download)
- [WireGuard Protokolü](https://www.wireguard.com/)

## 💡 İpuçları

### Sabit IP Adresi
Tailscale Admin panelinden cihazınıza sabit IP atayabilirsiniz:
1. https://login.tailscale.com/admin/machines
2. Kuvoz cihazını bulun
3. "..." menüsünden "Disable key expiry"
4. "Edit IP" ile sabit IP atayın

### Birden Fazla Cihaz
- Aynı Tailscale hesabına 100'e kadar cihaz ekleyebilirsiniz
- Her cihazdan Kuvoz'a erişebilirsiniz
- Ofis bilgisayarı, ev bilgisayarı, tablet, telefon...

### MagicDNS
Tailscale'in MagicDNS özelliği ile cihaz adıyla erişim:
```bash
# IP yerine cihaz adı
http://kuvoz:8000
```

## 🔄 Güncelleme

```bash
# Tailscale'i güncelle
sudo apt update
sudo apt upgrade tailscale

# QR kod kütüphanelerini güncelle (sistem paketleri)
sudo apt install --only-upgrade python3-qrcode python3-pil
```

## 📞 Destek

Sorun yaşıyorsanız:
1. `make tailscale-status` çıktısını kontrol edin
2. `journalctl -u tailscaled` loglarını inceleyin
3. Tailscale topluluk forumuna başvurun: https://forum.tailscale.com/

---

**Not**: Tailscale ücretsiz hesap 20 cihaza kadar destekler. Kurumsal kullanım için ücretli planları değerlendirebilirsiniz.
