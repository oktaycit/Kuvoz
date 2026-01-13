# Ayarlar ve Kullanıcı Profili Yönetimi

## 📋 Genel Bakış

Kuvoz projesine iki yeni sayfa eklendi:
1. **Sistem Ayarları** - Donanım özelliklerini aktif/pasif etme
2. **Kullanıcı Profili** - Firma ve yetkili bilgileri yönetimi

## 🆕 Yeni Sayfalar

### 1. Ayarlar Sayfası (`/settings.html`)

**Erişim:** Ana sayfadan "Ayarlar" butonu ile veya direkt `/settings.html`

**Özellikler:**
- 🔧 **Donanım Özellikleri**
  - GPIO Kontrol (salt okunur durum)
  - Soğutma Sistemi (aktif/pasif)

- 🌡️ **Sensör Ayarları**
  - DHT (Sıcaklık/Nem) sensörü
  - Oksijen sensörü
  - CO2 sensörü (SCD41)
  - Her sensör için ayrı aktif/pasif kontrolü

- 🤖 **Yapay Zeka Özellikleri**
  - AI Modülü (görüntü işleme, hareket algılama)
  - Sensör Veri Kaydı (SQLite logging)

**Davranış:**
- Donanım mevcut değilse toggle devre dışı kalır
- Durumlar gerçek zamanlı gösterilir (Mevcut/Mevcut Değil)
- Değişiklikler `Failure.dat` dosyasına JSON formatında kaydedilir

### 2. Kullanıcı Profili Sayfası (`/user_profile.html`)

**Erişim:** Ana sayfadan "Profil" butonu ile veya direkt `/user_profile.html`

**Özellikler:**
- 🏢 **Firma Bilgileri**
  - Firma Adı
  - Adres (textarea)
  - Telefon
  - E-posta
  - Vergi Numarası
  - Web Sitesi

- 👔 **Yetkili Kişi Bilgileri**
  - Ad Soyad
  - Ünvan (Veteriner Hekim / Teknisyen)
  - Cep Telefonu
  - E-posta

- 💻 **Cihaz Bilgileri** (Salt Okunur)
  - Cihaz Adı
  - IP Adresi (otomatik)
  - Yazılım Sürümü (v3.1.0)
  - Son Güncelleme (otomatik)

**İşlevler:**
- ✅ Kaydet - Bilgileri kalıcı olarak kaydet
- 🔄 Yenile - Sunucudan güncel bilgileri yükle
- 🗑️ Temizle - Tüm form alanlarını boşalt (onay gerektirir)

## 🔌 Backend API

### WebSocket Endpoint'leri

#### 1. Sistem Ayarları

**GET Settings**
```javascript
socket.emit('get_settings', {});

// Response: 'settings_response'
{
    hardware: {
        gpio_available: true/false,
        cooling_available: true/false
    },
    sensors: {
        dht_available: true/false,
        oxygen_available: true/false,
        co2_available: true/false
    },
    features: {
        ai_available: true/false,
        logging_available: true/false
    },
    settings: {
        cooling_enabled: true/false,
        dht_enabled: true/false,
        oxygen_enabled: true/false,
        co2_enabled: true/false,
        ai_enabled: true/false,
        logging_enabled: true/false
    }
}
```

**SAVE Settings**
```javascript
socket.emit('save_settings', {
    cooling_enabled: true,
    dht_enabled: true,
    oxygen_enabled: true,
    co2_enabled: true,
    ai_enabled: false,
    logging_enabled: true
});

// Response: 'settings_saved' or 'error'
```

#### 2. Kullanıcı Profili

**GET Profile**
```javascript
socket.emit('get_profile', {});

// Response: 'profile_response'
{
    company: {
        name: "Firma Adı",
        address: "Adres",
        phone: "+90...",
        email: "ornek@firma.com",
        tax_number: "1234567890",
        website: "https://www.firma.com"
    },
    contact: {
        name: "Ad Soyad",
        title: "Veteriner Hekim",
        mobile: "+90...",
        email: "yetkili@firma.com"
    },
    device: {
        name: "Kuvoz Cihazı",
        ip: "192.168.1.100",
        last_update: "12.01.2026 14:30"
    }
}
```

**SAVE Profile**
```javascript
socket.emit('save_profile', {
    company: { /* firma bilgileri */ },
    contact: { /* yetkili bilgileri */ }
});

// Response: 'profile_saved' or 'error'
```

## 💾 Veri Depolama

### Failure.dat (JSON Format)

Tüm ayarlar ve profil bilgileri `Failure.dat` dosyasında JSON formatında saklanır:

```json
{
    "slider_values": { /* mevcut slider değerleri */ },
    "button_states": { /* buton durumları */ },
    "ai_enabled": false,
    "system_settings": {
        "cooling_enabled": false,
        "dht_enabled": true,
        "oxygen_enabled": true,
        "co2_enabled": true,
        "ai_enabled": false,
        "logging_enabled": true
    },
    "user_profile": {
        "company": { /* firma bilgileri */ },
        "contact": { /* yetkili bilgileri */ },
        "device": { /* cihaz bilgileri */ }
    }
}
```

**Önemli Notlar:**
- UTF-8 encoding kullanılır (Türkçe karakter desteği)
- Sistem başlangıcında otomatik yüklenir
- Değişiklikler anında kaydedilir
- Eski format ile uyumlu (geriye dönük uyumluluk)

## 🎨 UI/UX Özellikleri

### Navigasyon
- Ana sayfada header'da iki yeni buton:
  - ⚙️ **Ayarlar** - Sistem ayarları sayfasına gider
  - 👤 **Profil** - Kullanıcı profil sayfasına gider
- Mobil cihazlarda sadece ikonlar gösterilir (responsive)

### Bildirimler
- ✅ Başarı bildirimleri (yeşil)
- ❌ Hata bildirimleri (kırmızı)
- 3 saniye sonra otomatik kaybolur
- Sağ üst köşede animasyonlu gösterim

### Responsive Tasarım
- Desktop, tablet ve mobil uyumlu
- Mobil cihazlarda form alanları dikey sıralanır
- Touch-friendly butonlar ve toggle'lar

## 🔒 Güvenlik

### Veri Validasyonu
- Tüm form girişleri client-side validasyon
- Backend'de exception handling
- Geçersiz veri için error mesajları

### Varsayılan Davranışlar
- UV ve Ozon sterilizasyon ayarları her zaman OFF olarak kaydedilir
- Sistem başlangıcında güvenli varsayılan değerler

## 🚀 Deployment

### Geliştirme Ortamı
```bash
# Dev server başlat (localhost:5000)
make web-dev
# VEYA
python3 web_server.py
```

### Production
```bash
# Systemd servisini yeniden başlat
sudo systemctl restart kuvoz-web

# Logları izle
journalctl -u kuvoz-web -f
```

### Test
1. Ana sayfada yeni butonların göründüğünü kontrol et
2. Ayarlar sayfasına git, toggle'ları test et, kaydet
3. Profil sayfasına git, bilgileri gir, kaydet
4. Ana sayfaya dön, sistemi yeniden başlat
5. Ayarların korunduğunu doğrula

## 📱 Mobil Uyumluluk

### Ekran Boyutları
- **Desktop** (>768px): Tam özellik seti
- **Tablet** (481-768px): İki kolonlu layout
- **Mobil** (<480px): Tek kolonlu layout, ikon navigasyon

### Touch Optimizasyonu
- Minimum 44x44px touch hedefleri
- Büyük butonlar ve toggle'lar
- Scroll-friendly formlar

## 🐛 Bilinen Sorunlar ve Sınırlamalar

1. **Gerçek Zamanlı Senkronizasyon:** Birden fazla client aynı anda bağlıysa, ayar değişiklikleri diğer clientlara broadcast edilmez (gelecek güncellemede eklenebilir).

2. **Form Validasyonu:** Email ve telefon formatı validasyonu sadece HTML5 tarafından yapılır, backend validasyonu yok.

3. **Undo İşlevi:** Kaydedilen ayarlar için geri alma (undo) özelliği yok.

## 🔮 Gelecek Geliştirmeler

- [ ] Çoklu kullanıcı desteği ve yetkilendirme
- [ ] Ayar geçmişi (audit log)
- [ ] Export/Import profil bilgileri (JSON/CSV)
- [ ] QR kod ile profil paylaşımı
- [ ] Cihaz kayıt numarası ve seri no takibi
- [ ] Bakım geçmişi ve kalibrasyon kayıtları

## 📞 Destek

Sorunlar için GitHub Issues kullanın veya projeyi geliştiren ekiple iletişime geçin.

---

**Son Güncelleme:** 12 Ocak 2026
**Versiyon:** 3.1.0
