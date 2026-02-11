# 🌐 Kuvoz Uzaktan Erişim Kurulum Kılavuzu

**Versiyon:** 1.0  
**Tarih:** 3 Ocak 2026  
**Amaç:** Veteriner hekimlerin Kuvoz cihazına uzaktan erişimini sağlamak

---

## 📋 İçindekiler

1. [Tailscale ile Uzaktan Erişim (ÖNERİLEN)](#-tailscale-ile-uzaktan-erişim-önerilen)
2. [Cloudflare Tunnel ile Uzaktan Erişim](#-cloudflare-tunnel-ile-uzaktan-erişim)
3. [Karşılaştırma ve Seçim](#-karşılaştırma-ve-seçim)

---

## 🚀 Tailscale ile Uzaktan Erişim (ÖNERİLEN)

### Neden Tailscale?

- ✅ **Kurulum Süresi:** 5 dakika
- ✅ **Güvenlik:** WireGuard VPN (askeri seviye şifreleme)
- ✅ **Hız:** Peer-to-peer doğrudan bağlantı
- ✅ **Ücretsiz:** 100 cihaza kadar
- ✅ **Mobil Destek:** iOS ve Android uygulamaları
- ✅ **NAT Geçişi:** Router ayarı gerektirmez

### Adım 1: Raspberry Pi'de Tailscale Kurulumu

```bash
# Raspberry Pi'ye SSH ile bağlanın
ssh pi@raspberry-pi-ip

# Tailscale kurulum script'ini çalıştırın
curl -fsSL https://tailscale.com/install.sh | sh

# Tailscale'i başlatın ve kimlik doğrulama linkini alın
sudo tailscale up

# Çıktıda bir link göreceksiniz:
# "To authenticate, visit: https://login.tailscale.com/a/xxxxx"
```

### Adım 2: Tarayıcıda Kimlik Doğrulama

1. Terminal'de verilen linke tıklayın veya kopyalayıp tarayıcıya yapıştırın
2. Tailscale hesabı oluşturun veya Google/Microsoft/Apple hesabınızla giriş yapın
3. Cihazınızı onaylayın
4. Raspberry Pi artık Tailscale ağınıza bağlı!

### Adım 3: Tailscale IP Adresini Öğrenin

```bash
# Raspberry Pi'nizin Tailscale IP adresini görün
tailscale ip -4

# Örnek çıktı: 100.100.100.42
```

### Adım 4: Magic DNS'i Etkinleştirin (İsteğe Bağlı ama ÖNERİLEN)

1. [Tailscale Admin Console](https://login.tailscale.com/admin/dns)'a gidin
2. **DNS** sekmesine tıklayın
3. **MagicDNS**'i etkinleştirin

Artık IP adresi yerine cihaz adıyla erişebilirsiniz:
```
http://kuvoz:8000
# veya
http://raspberrypi:8000
```

### Adım 5: Mobil Cihazdan Erişim

#### iOS:
1. App Store'dan [Tailscale iOS](https://apps.apple.com/app/tailscale/id1470499037) uygulamasını indirin
2. Aynı hesapla giriş yapın
3. VPN'i açın
4. Safari'de `http://100.100.100.42:8000` adresine gidin (kendi IP'nizi kullanın)

#### Android:
1. Play Store'dan [Tailscale Android](https://play.google.com/store/apps/details?id=com.tailscale.ipn) uygulamasını indirin
2. Aynı hesapla giriş yapın
3. VPN'i açın
4. Chrome'da `http://100.100.100.42:8000` adresine gidin

### Adım 6: Masaüstü Bilgisayardan Erişim

#### macOS/Windows/Linux:
1. [Tailscale İndir](https://tailscale.com/download)
2. Kurulumu yapın
3. Aynı hesapla giriş yapın
4. Tarayıcıda `http://kuvoz:8000` veya `http://100.100.100.42:8000`

### Güvenlik İpuçları

```bash
# Sadece belirli port'ları açmak için ACL (Access Control List) kullanın
# Tailscale Admin Console → Access Controls

# Örnek ACL:
{
  "acls": [
    {
      "action": "accept",
      "src": ["autogroup:members"],
      "dst": ["tag:kuvoz:8000"]
    }
  ]
}
```

### Otomatik Başlatma

Tailscale zaten otomatik başlar, ama kontrol etmek için:

```bash
# Tailscale servis durumunu kontrol edin
sudo systemctl status tailscaled

# Otomatik başlatmayı etkinleştirin
sudo systemctl enable tailscaled
sudo systemctl start tailscaled
```

---

## ☁️ Cloudflare Tunnel ile Uzaktan Erişim

### Neden Cloudflare Tunnel?

- ✅ **Tamamen Ücretsiz:** Hiçbir limit yok
- ✅ **DDoS Koruması:** Cloudflare CDN koruması
- ✅ **Port Forwarding Gerektirmez**
- ✅ **HTTPS Otomatik:** SSL sertifikası otomatik
- ⚠️ **Biraz Daha Karmaşık:** Kurulum için 15-20 dakika
- ⚠️ **Cloudflare Hesabı Gerekli**

### Adım 1: Cloudflare Hesabı Oluşturun

1. [Cloudflare](https://dash.cloudflare.com/sign-up) hesabı oluşturun
2. Email doğrulaması yapın

### Adım 2: Cloudflared Kurulumu (Raspberry Pi)

```bash
# Raspberry Pi'ye SSH ile bağlanın
ssh pi@raspberry-pi-ip

# Cloudflared indir (ARM64 veya ARM32 - Pi versiyonunuza göre)
# Raspberry Pi 4/3B+ için ARM64:
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64

# Raspberry Pi 3/Zero için ARM32:
# wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm

# İzin ver ve taşı
sudo mv cloudflared-linux-arm64 /usr/local/bin/cloudflared
sudo chmod +x /usr/local/bin/cloudflared

# Kurulumu doğrula
cloudflared --version
```

### Adım 3: Cloudflare'e Giriş Yapın

```bash
# Kimlik doğrulama başlat
cloudflared tunnel login

# Terminal'de bir link göreceksiniz:
# "Please open the following URL in your browser: https://dash.cloudflare.com/..."
# Bu linke tıklayın ve tarayıcıda Cloudflare hesabınızla giriş yapın
```

### Adım 4: Tunnel Oluşturun

```bash
# "kuvoz-tunnel" adında bir tunnel oluşturun
cloudflared tunnel create kuvoz-tunnel

# Çıktıda tunnel ID göreceksiniz:
# "Created tunnel kuvoz-tunnel with id: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

# Tunnel listesini görün
cloudflared tunnel list
```

### Adım 5: Tunnel Yapılandırma Dosyası

```bash
# Cloudflared config klasörü oluşturun
sudo mkdir -p /etc/cloudflared

# Yapılandırma dosyası oluşturun
sudo nano /etc/cloudflared/config.yml
```

Aşağıdaki içeriği yapıştırın (TUNNEL_ID'yi kendi tunnel ID'nizle değiştirin):

```yaml
tunnel: TUNNEL_ID_BURAYA_YAPIŞTIRIN
credentials-file: /root/.cloudflared/TUNNEL_ID_BURAYA_YAPIŞTIRIN.json

ingress:
  # Kuvoz web arayüzü
  - hostname: kuvoz.yourdomain.com  # İsteğe bağlı: kendi domain'iniz
    service: http://localhost:8000
  
  # Catch-all rule (gerekli)
  - service: http_status:404
```

**NOT:** Eğer domain'iniz yoksa, Cloudflare size otomatik bir subdomain verecek:
```yaml
tunnel: TUNNEL_ID_BURAYA_YAPIŞTIRIN
credentials-file: /root/.cloudflared/TUNNEL_ID_BURAYA_YAPIŞTIRIN.json

ingress:
  - service: http://localhost:8000
```

### Adım 6: DNS Kaydı Oluşturun (Domain Varsa)

```bash
# Domain'iniz varsa DNS kaydı oluşturun
cloudflared tunnel route dns kuvoz-tunnel kuvoz.yourdomain.com
```

Domain'iniz yoksa bu adımı atlayabilirsiniz. Cloudflare size otomatik bir URL verecek.

### Adım 7: Tunnel'ı Başlatın

```bash
# Test için manuel başlatın
sudo cloudflared tunnel run kuvoz-tunnel

# Çıktıda erişim URL'ini göreceksiniz:
# "https://kuvoz-tunnel.trycloudflare.com" veya kendi domain'iniz
```

### Adım 8: Systemd Servisi Oluşturun (Otomatik Başlatma)

```bash
# Servisi kur
sudo cloudflared service install

# Servisi başlat
sudo systemctl start cloudflared

# Otomatik başlatmayı etkinleştir
sudo systemctl enable cloudflared

# Durum kontrol
sudo systemctl status cloudflared
```

### Adım 9: Cloudflare Dashboard'dan Kontrol

1. [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/) → Networks → Tunnels
2. "kuvoz-tunnel" görünüyor olmalı
3. **Public Hostname** kısmında URL'iniz var

### Mobil ve Masaüstü Erişim

Artık herhangi bir cihazdan (VPN gerektirmeden) erişebilirsiniz:

```
https://kuvoz-tunnel.trycloudflare.com
# veya
https://kuvoz.yourdomain.com
```

**NOT:** HTTPS otomatik olarak etkinleştirilir (SSL sertifikası Cloudflare tarafından sağlanır).

---

## 🔍 Karşılaştırma ve Seçim

| Özellik | Tailscale | Cloudflare Tunnel |
|---------|-----------|-------------------|
| **Kurulum Karmaşıklığı** | ⭐⭐⭐⭐⭐ Çok Kolay | ⭐⭐⭐ Orta |
| **Kurulum Süresi** | 5 dakika | 15-20 dakika |
| **Gecikme (Latency)** | ⭐⭐⭐⭐⭐ Çok Düşük (P2P) | ⭐⭐⭐ Orta (Cloudflare CDN üzerinden) |
| **Güvenlik** | ⭐⭐⭐⭐⭐ WireGuard VPN | ⭐⭐⭐⭐⭐ HTTPS + Cloudflare |
| **Ücretsiz Limit** | 100 cihaz | Sınırsız |
| **Mobil Uygulama** | ✅ iOS/Android | ❌ Tarayıcı gerekli |
| **Router Ayarı** | ❌ Gerektirmez | ❌ Gerektirmez |
| **DDoS Koruması** | ⚠️ Yok | ✅ Var |
| **HTTPS Otomatik** | ❌ (Manuel kurulum) | ✅ Otomatik |
| **Kullanım Kolaylığı** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Veteriner Kliniği İçin** | ✅ ÖNERİLEN | ✅ Alternatif |

### Hangi Durumda Hangisi?

#### Tailscale Kullanın:
- ✅ **Hızlı kurulum istiyorsanız**
- ✅ **Mobil uygulamadan erişecekseniz**
- ✅ **Düşük gecikme (real-time monitoring) kritikse**
- ✅ **Sadece veteriner ekibi erişecekse** (100 cihaz yeterli)
- ✅ **En basit çözümü istiyorsanız**

#### Cloudflare Tunnel Kullanın:
- ✅ **Public erişim gerekiyorsa** (herhangi bir tarayıcıdan)
- ✅ **HTTPS otomatik istiyorsanız**
- ✅ **DDoS koruması istiyorsanız**
- ✅ **Kendi domain'inizi kullanacaksanız**
- ✅ **100'den fazla cihaz erişecekse**

---

## 🛠️ Makefile Entegrasyonu

Her iki çözüm için de Makefile komutları eklenmiştir:

### Tailscale Komutları:

```bash
# Tailscale kurulumu
make tailscale-install

# Tailscale başlat
make tailscale-start

# Tailscale IP adresini görüntüle
make tailscale-status

# Tailscale durdur
make tailscale-stop
```

### Cloudflare Tunnel Komutları:

```bash
# Cloudflared kurulumu
make cloudflare-install

# Tunnel oluştur
make cloudflare-setup

# Tunnel başlat
make cloudflare-start

# Tunnel durumu
make cloudflare-status

# Tunnel durdur
make cloudflare-stop
```

---

## 📱 Veteriner Mobil Erişim Örneği

### Senaryo: Veteriner hekim ofisten hasta takibi

#### Tailscale ile:
1. Telefonda Tailscale uygulamasını aç
2. VPN'i etkinleştir
3. Safari/Chrome'da `http://kuvoz:8000` aç
4. **Gecikme:** ~10-50ms (P2P)

#### Cloudflare Tunnel ile:
1. Safari/Chrome'da `https://kuvoz-tunnel.trycloudflare.com` aç
2. **Gecikme:** ~50-200ms (CDN üzerinden)

---

## 🔐 Güvenlik Önerileri

### Her İki Çözüm İçin:

```bash
# 1. Web server'a HTTP basic authentication ekleyin
# web_server.py içine:

from flask import request, Response

def check_auth(username, password):
    """Kullanıcı adı ve parola kontrolü"""
    return username == 'veteriner' and password == 'GÜÇLÜ_PAROLA_BURAYA'

def authenticate():
    """Authentication hatası"""
    return Response(
        'Giriş gerekli\n'
        'Lütfen kullanıcı adı ve parola girin', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# Rotalara ekleyin:
@app.route('/')
@requires_auth
def index():
    return render_template('index.html')
```

### 2. IP Whitelist (Tailscale)

```bash
# Tailscale ACL ile sadece belirli cihazları izin verin
# Admin Console → Access Controls
```

### 3. Rate Limiting (Cloudflare Tunnel)

```bash
# Cloudflare Dashboard → Security → WAF
# Rate limiting kuralları ekleyin
```

---

## 🆘 Sorun Giderme

### Tailscale

```bash
# Bağlantı kontrol
sudo tailscale status

# Log kontrol
sudo journalctl -u tailscaled -f

# Yeniden başlatma
sudo systemctl restart tailscaled

# Bağlantıyı sıfırlama
sudo tailscale down
sudo tailscale up
```

### Cloudflare Tunnel

```bash
# Tunnel durumu
sudo cloudflared tunnel info kuvoz-tunnel

# Log kontrol
sudo journalctl -u cloudflared -f

# Yeniden başlatma
sudo systemctl restart cloudflared

# Manuel test
sudo cloudflared tunnel run kuvoz-tunnel --loglevel debug
```

---

## 📞 Destek

**Tailscale Dokümantasyon:** https://tailscale.com/kb  
**Cloudflare Tunnel Dokümantasyon:** https://developers.cloudflare.com/cloudflare-one/connections/connect-apps

---

## ✅ Kurulum Sonrası Kontrol Listesi

- [ ] Uzaktan erişim çalışıyor (mobil cihazdan test et)
- [ ] WebSocket bağlantısı çalışıyor (real-time sensör verileri görünüyor)
- [ ] Buton kontrolleri çalışıyor
- [ ] Otomatik başlatma etkin (Raspberry Pi yeniden başladığında)
- [ ] Güvenlik ayarları yapıldı (authentication/ACL)
- [ ] Yedek erişim yöntemi hazır (her iki çözümü de kurabilirsiniz)

---

**ÖNERİ:** İkisini de kurun! Tailscale mobil erişim için, Cloudflare Tunnel yedek erişim için kullanılabilir.
