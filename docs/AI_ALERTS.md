# AI Uyarıları ve Tahminler Sistemi

## Genel Bakış

Kuvoz İnkübatör sistemi, yapay zeka destekli gerçek zamanlı izleme ve uyarı sistemi ile donatılmıştır. Bu sistem, sensör verilerini sürekli analiz ederek potansiyel sorunları önceden tespit eder ve kullanıcıyı bilgilendirir.

## Özellikleri

### 1. **Canlı Kamera Görüntüsü** 🎥
- Raspberry Pi kamera modülü üzerinden gerçek zamanlı görüntü
- Hareket algılama (Motion Detection)
- Aktivite seviyesi takibi
- 640x480 çözünürlük, 5 FPS

### 2. **AI Tahminleri** 📊
- **Sıcaklık Trendi:** Anlık sıcaklık değişimlerini takip eder
  - Yükselme/Düşme trendi gösterir
  - Stabilite analizi yapar
  
- **Nem Trendi:** Nem seviyesi değişimlerini izler
  - Ani değişimleri tespit eder
  - Optimal seviye önerileri sunar

- **Oksijen Trendi:** Oksijen konsantrasyonunu analiz eder
  - Kritik seviyeleri uyarır
  - Havalandırma önerileri sunar

### 3. **Akıllı Uyarı Sistemi** ⚠️

#### Kritik Uyarılar (🔥❗)
- Sıcaklık 40°C üzeri
- Oksijen %18'in altında
- Sistem malfunctions

#### Uyarılar (⚠️)
- Sıcaklık 35-40°C arası
- Nem %80 üzeri veya %30 altı
- Oksijen %19.5 altında
- Isıtıcı açıkken sıcaklık düşüşü

#### Bilgi Mesajları (ℹ️)
- Sistem dengesizlikleri
- Bakım önerileri
- Performans tavsiyeleri

## Nasıl Kullanılır?

### Ana Sayfadan Erişim
1. Ana kontrol panelinde "AI Uyarıları" butonuna tıklayın
2. Alternatif olarak, AI panelindeki "Detaylı AI Analizi" butonunu kullanın
3. Doğrudan `http://<IP>:8000/alerts.html` adresine gidin

### Sayfa Bileşenleri

#### İstatistik Kartları (Üst Kısım)
- **Toplam Uyarı:** Aktif uyarı sayısı
- **Kritik Uyarı:** Acil müdahale gerektiren uyarılar
- **Hareket Durumu:** Kamera hareket algılama sonucu
- **Aktivite Seviyesi:** Yüzdesel aktivite oranı

#### Kamera Görüntüsü
- Gerçek zamanlı video feed
- Hareket göstergesi (yeşil/gri nokta)
- Zaman damgası

#### AI Tahminleri Bölümü
Her sensör için:
- Mevcut ortalama değer
- Trend yönü (↑ Yükseliyor / ↓ Düşüyor / − Stabil)
- Değişim miktarı

#### Aktif Uyarılar
- Renkli uyarı kartları
- Önem seviyesine göre sıralama
- Zaman damgası ve kategori bilgisi

## Teknik Detaylar

### Veri Toplama
- **Geçmiş Penceresi:** Son 60 okuma (yaklaşık 5 dakika)
- **Güncelleme Sıklığı:** 5 saniyede bir (sensörler)
- **AI Analiz:** 1 saniyede bir

### Algoritma Özellikleri

#### 1. Trend Analizi
```python
# Son 10 okumanın lineer regresyonu
trend = polyfit(range(10), last_10_readings, 1)[0]
```

#### 2. Anomali Tespiti
- **Varyans Kontrolü:** Dengesiz okumalar için
- **Eşik Değerleri:** Kritik seviyeler için
- **Oran Karşılaştırma:** Ani değişimler için

#### 3. Durum-Aksiyon İlişkisi
- Isıtıcı açık → Sıcaklık artmalı
- Havalandırma aktif → Oksijen stabil olmalı
- Nem kontrol çalışıyor → Nem değişmemeli

### WebSocket İletişimi

Sistem, Socket.IO protokolü kullanarak gerçek zamanlı veri alışverişi yapar:

```javascript
// Gelen mesajlar
socket.on('ai_update', callback)      // AI verileri (1s)
socket.on('sensor_update', callback)  // Sensör verileri (5s)

// Giden mesajlar
socket.emit('get_status', {page: 'alerts'})
```

## Uyarı Seviyeleri ve Anlamları

| Seviye | Renk | İkon | Anlamı | Aksiyon |
|--------|------|------|--------|---------|
| **Kritik** | Kırmızı | 🔥❗ | Acil müdahale | Hemen kontrol edin |
| **Uyarı** | Turuncu | ⚠️ | Dikkat gerekli | Yakında kontrol edin |
| **Bilgi** | Mavi | ℹ️ | Bilgilendirme | İzlemeye devam |
| **Normal** | Yeşil | ✅ | Her şey yolunda | Aksiyon gerekmez |

## Performans Optimizasyonu

### Tarayıcı Gereksinimleri
- Modern tarayıcı (Chrome, Firefox, Edge, Safari)
- WebSocket desteği
- JavaScript etkin
- Minimum 1280x720 çözünürlük (tablet/PC için)

### Veri Tüketimi
- **Kamera feed:** ~14KB/frame × 1 FPS = ~14KB/s
- **Sensör verileri:** ~2KB her 5 saniyede
- **Toplam:** ~15-20KB/s bandwidth kullanımı

### Bellek Kullanımı
- **Client-side:** ~5-10MB (tarayıcı)
- **Server-side:** ~35MB (Python process)

## Sorun Giderme

### Kamera görüntüsü gelmiyor
```bash
# Kamera durumunu kontrol et
vcgencmd get_camera

# Kamera modülünü yeniden başlat
sudo systemctl restart kuvoz-web.service
```

### Uyarılar görünmüyor
1. AI modülünün aktif olduğundan emin olun
2. Log dosyalarını kontrol edin:
   ```bash
   journalctl -u kuvoz-web.service -f | grep AI
   ```
3. Sensör verilerinin geldiğini doğrulayın

### Yavaş yükleme
1. Raspberry Pi CPU kullanımını kontrol edin: `top`
2. Ağ bağlantısını test edin: `ping 192.168.1.196`
3. Tarayıcı konsolunda hata olup olmadığını bakın (F12)

## Gelişmiş Özellikler

### Otomatik Bildirimler
Ana sayfada kritik uyarılar için toast notification otomatik gösterilir:
- Kırmızı: Kritik durumlar
- Turuncu: Uyarılar
- Sadece yeni uyarılar bildirilir (tekrar etmez)

### Geçmiş Veriler
Sensör geçmişi son 20 okuma saklanır ve trend analizinde kullanılır.

### Mobil Uyumluluk
Sayfa responsive tasarımdır:
- Tablet: 2 sütun grid
- Mobil: Tek sütun, touch-friendly

## API Referansı

### GET /alerts.html
Ana uyarılar sayfasını yükler.

### WebSocket Events
- `ai_update`: AI analiz sonuçları
  ```json
  {
    "vision": {
      "status": "HAREKETLI",
      "activity": 45.2
    },
    "analytics": {
      "anomalies": ["⚠️ Uyarı mesajı"],
      "data_points": {"temperature": 60, "humidity": 60}
    },
    "frame": "base64_encoded_jpeg"
  }
  ```

- `sensor_update`: Sensör değerleri
  ```json
  {
    "sensors": {
      "temperature": {"value": "25.0", "status": "OK"},
      "humidity": {"value": "65", "status": "OK"},
      "oxygen": {"value": "20.9", "status": "OK"}
    }
  }
  ```

## Güvenlik

- Yerel ağ erişimi (192.168.x.x)
- Şifreleme: HTTP (production'da HTTPS önerilir)
- Kimlik doğrulama: Opsiyonel (Firebase entegrasyonu ile)

## Bakım ve Güncellemeler

### Düzenli Kontroller
- Kamera lensi temizliği (haftalık)
- Log dosyası boyutu kontrolü (aylık)
- Yazılım güncellemeleri (gerektiğinde)

### Yedekleme
```bash
# Sensör loglarını yedekle
sudo cp /home/oktay/kuvoz/data/sensor_logs.db ~/backup/
```

## İletişim ve Destek

Sorunlar veya öneriler için:
- GitHub Issues: [Kuvoz Repository]
- Dokümantasyon: `/docs` klasörü
- Log analizi: `journalctl -u kuvoz-web.service`

---

**Not:** Bu sistem, veteriner profesyonellerinin karar verme sürecini desteklemek için tasarlanmıştır. Kritik durumlarda her zaman uzman müdahalesi gereklidir.
