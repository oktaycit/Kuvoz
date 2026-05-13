# 🤖 Kuvoz AI Entegrasyonu

Bu doküman, evcil hayvan recovery ünitesi (Kuvoz) sistemindeki yapay zeka özelliklerini açıklamaktadır.

## 📋 İçindekiler

- [Genel Bakış](#genel-bakış)
- [AI Modülleri](#ai-modülleri)
  - [Vision Engine](#1-vision-engine---görüş-motoru)
  - [Analytics Engine](#2-analytics-engine---analitik-motoru)
  - [AI Manager](#3-ai-manager---ai-yöneticisi)
- [Kullanım Senaryoları](#kullanım-senaryoları)
- [Teknik Altyapı](#teknik-altyapı)
- [Gelecek Geliştirmeler](#gelecek-geliştirmeler)

---

## Genel Bakış

Kuvoz, hasta, yeni doğmuş veya operasyon sonrası iyileşme sürecindeki evcil hayvanlar için tasarlanmış bir **recovery ünitesidir**. Sistem, hayvanların iyileşme sürecini optimize etmek için yapay zeka teknolojilerinden yararlanır. AI sistemi iki ana alanda çalışır:

1. **Görüntü İşleme**: Kamera ile düşük FPS yaşam döngüsü, hareket/dinlenme ve aktivite takibi
2. **Sensör Analitiği**: Sıcaklık, nem ve oksijen verilerinde anomali tespiti

```
┌─────────────────────────────────────────────────────────────┐
│                      AI Manager                             │
│  ┌─────────────────────┐    ┌─────────────────────────┐    │
│  │   Vision Engine     │    │   Analytics Engine      │    │
│  │   ---------------   │    │   ------------------    │    │
│  │   • Kamera Yönetimi │    │   • Veri Toplama        │    │
│  │   • Hareket Tespiti │    │   • Trend Analizi       │    │
│  │   • Frame İşleme    │    │   • Anomali Tespiti     │    │
│  └─────────────────────┘    └─────────────────────────┘    │
│                              │                              │
│              WebSocket (varsayılan 2 sn)                    │
│                              ↓                              │
│                     ┌───────────────┐                       │
│                     │  Web Arayüzü  │                       │
│                     └───────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

---

## AI Modülleri

### 1. Vision Engine - Görüş Motoru

**Dosya**: `lib/ai/vision.py`

Kamera tabanlı görüntü işleme modülü. Recovery ünitesi içindeki hayvanı düşük yük profiliyle izler; ana amaç yaşam döngüsü, hareket/dinlenme ve aktivite analizi yapmaktır. Kameradan türetilen solunum/vital tahminleri yardımcı ve deneysel veridir.

#### Özellikler

| Özellik | Değer |
|---------|-------|
| Çözünürlük | Varsayılan 320 x 240 piksel (`KUVOZ_AI_WIDTH`, `KUVOZ_AI_HEIGHT`) |
| Frame Hızı | Varsayılan 1 FPS (`KUVOZ_AI_FPS`) |
| Düşük Yük Profilleri | Boş/kararsız kadrajda 0.5 FPS, yoğun harekette yaklaşık 0.75 FPS |
| Termal Koruma | Varsayılan 62°C üstünde 0.5 FPS, 58°C altında normale dönüş |
| UI Güncellemesi | Varsayılan 2 saniye (`KUVOZ_AI_UPDATE_INTERVAL_SEC`) |
| Kamera Desteği | Raspberry Pi Camera, USB Webcam |
| Çıktı Formatı | Base64 JPEG |

Ortam değişkenleri servis dosyasından veya çalışma ortamından verilebilir. Değerler güvenli aralıkta sınırlandırılır: genişlik 160-640, yükseklik 120-480, FPS 0.25-5.0.

#### Kamera Desteği

```python
# Raspberry Pi Native Camera (picamera2)
from picamera2 import Picamera2

# Standart USB/CSI Kameralar (OpenCV)
import cv2
```

Sistem otomatik olarak şu sırayla kamera arar:
1. **picamera2** - Raspberry Pi native kamera modülü
2. **OpenCV** - USB webcam veya diğer kameralar

#### Hareket Algılama Algoritması

Vision Engine, ardışık frameler arasındaki farkı analiz ederek hareket tespit eder:

```python
# Frame farkı hesaplama
diff = cv2.absdiff(self.last_frame, gray)
_, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)

# Hareket oranı hesaplama
non_zero_count = cv2.countNonZero(thresh)
movement_ratio = (non_zero_count / total_pixels) * 100

# Durum belirleme (eşik: %1)
if movement_ratio > 1.0:
    status = "HAREKETLI"
else:
    status = "DURGUN"
```

#### Çıktılar

- **status**: Hayvanın hareket durumu (`HAREKETLI` / `DURGUN`)
- **activity_level**: Aktivite yüzdesi (0-100%)
- **frame**: Base64 encode edilmiş JPEG görüntü

---

### 2. Analytics Engine - Analitik Motoru

**Dosya**: `lib/ai/analytics.py`

Sensör verilerini analiz ederek anormallikleri tespit eden modül.

#### Veri Toplama

Sistem son **60 okumayı** (yaklaşık 5 dakikalık veri) saklar:

```python
self.history = {
    'temperature': deque(maxlen=60),  # Sıcaklık geçmişi
    'humidity': deque(maxlen=60),     # Nem geçmişi
    'oxygen': deque(maxlen=60)        # Oksijen geçmişi
}
```

#### Anomali Tespiti Algoritmaları

##### 1. Isıtıcı-Sıcaklık Tutarsızlığı

Isıtıcı açıkken sıcaklığın düşmesi bir arıza göstergesidir:

```python
# Son 10 okumada trend analizi (lineer regresyon)
recent_trend = np.polyfit(range(10), temps[-10:], 1)[0]

if heater_on and recent_trend < -0.05:
    # UYARI: Isıtıcı açık ama sıcaklık düşüyor!
```

**Olası Nedenler:**
- Isıtıcı arızası
- Kapak açık kalmış
- Yalıtım sorunu

##### 2. Ani Oksijen Düşüşü

Oksijen seviyesindeki ani düşüş tehlikeli olabilir:

```python
# Son 5 okumada %5'ten fazla düşüş
if oxygen_now < oxygen_5_readings_ago * 0.95:
    # UYARI: Oksijen seviyesinde ani düşüş!
```

**Olası Nedenler:**
- Havalandırma arızası
- Aşırı yoğunluk
- Ortam sızıntısı

---

### 3. AI Manager - AI Yöneticisi

**Dosya**: `lib/ai/manager.py`

Vision ve Analytics motorlarını koordine eden merkezi yönetici.

#### Sorumluluklar

1. **Motor Başlatma/Durdurma**: Tüm AI bileşenlerinin yaşam döngüsü
2. **Veri Akışı**: Sensör verilerinin Analytics'e beslenmesi
3. **Frontend Güncellemesi**: WebSocket üzerinden UI'a veri gönderimi
4. **Vital Değişim Raporlama**: Dinamik eşiklerle zaman etiketli vital değişim üretimi

#### Kullanım

```python
# Başlatma
ai_manager = AIManager()
ai_manager.start()

# Sensör verisi güncelleme
ai_manager.update_sensors(
    sensor_data={'temperature': 37.5, 'humidity': 65, 'oxygen': 21.0},
    actuator_state={'heater_on': True}
)

# Durum alma
update = ai_manager.get_update()
# {
#   "vision": {"status": "DURGUN", "activity_level": 0.3},
#   "analytics": {"anomalies": [], "data_points": {...}},
#   "vital_reports": [{"timestamp": "...", "message": "..."}],
#   "frame": "base64_jpeg_data..."
# }
```

#### Dinamik Vital Eşikleri

AI Manager, vital değişim rapor eşiklerini hasta profiline göre ayarlar:

- Tür (`species`)
- Cins (`breed`)
- Yaş (`age`)
- Ağırlık (`weight`)

İlgili API/event:

- `update_patient_context` (frontend -> backend)
- `AIManager.set_patient_context(...)`
- `AIManager._get_dynamic_thresholds()`

---

## Kullanım Senaryoları

### 🐾 Hayvan İzleme

Vision Engine ile recovery ünitesi içindeki hayvanın durumu izlenir:

- **Aktivite Tespiti**: Hayvanın hareket ve aktivite seviyesi takibi
- **Yaşam Döngüsü İzleme**: Dinlenme, hareket ve bakım olaylarının kamera destekli yorumlanması
- **Davranış İzleme**: Uyku, uyanıklık, huzursuzluk gibi durumlara yardımcı gözlem
- **Uzaktan İzleme**: Web arayüzü üzerinden düşük bant genişlikli kamera takibi
- **Görsel Durum Takibi**: İyileşme sürecindeki davranış değişimlerinin izlenmesi

### 🌡️ Ortam Kontrolü

Analytics Engine ile optimal iyileşme koşulları sağlanır:

- **Sıcaklık Takibi**: Hayvan türüne göre ideal sıcaklık aralığı
- **Nem Kontrolü**: Solunum rahatlığı için nem dengesi
- **Oksijen İzleme**: Yeterli oksijen seviyesi garantisi

### ⚠️ Erken Uyarı Sistemi

Anomali tespiti ile sorunlar erkenden belirlenir:

- **Isıtıcı Arızası**: Sıcaklık trend analizi ile erken uyarı
- **Havalandırma Sorunu**: Oksijen düşüş tespiti
- **Aktivite Azalması**: Hayvanın hareketsizliği durumunda bildirim
- **Anormal Aktivite**: Beklenmeyen hareket kalıpları

---

## Teknik Altyapı

### Bağımlılıklar

```bash
# Görüntü İşleme
opencv-python>=4.5.0
numpy>=1.20.0

# Raspberry Pi Kamera (opsiyonel)
picamera2>=0.3.0
```

### Sistem Gereksinimleri

| Bileşen | Minimum | Önerilen |
|---------|---------|----------|
| RAM | 512 MB | 1 GB |
| CPU | 1 GHz | 1.4 GHz |
| Kamera | - | USB/CSI Kamera |

### Web Arayüzü Entegrasyonu

AI verileri Socket.IO üzerinden varsayılan olarak 2 saniyede bir gönderilir. Event adı değişmemiştir; sadece gönderim aralığı `KUVOZ_AI_UPDATE_INTERVAL_SEC` ile ayarlanabilir:

```javascript
// Frontend'de AI güncellemelerini alma
socket.on('ai_update', (data) => {
    // Kamera görüntüsü güncelleme
    if (data.frame) {
        document.getElementById('aiCameraFeed').src = 
            'data:image/jpeg;base64,' + data.frame;
    }
    
    // Uyarıları gösterme
    if (data.analytics.anomalies.length > 0) {
        showAlerts(data.analytics.anomalies);
    }
});
```

---

## Gelecek Geliştirmeler

### 🔮 Planlanan Özellikler

1. **Makine Öğrenmesi Modelleri**
   - Hayvan sağlık durumu tahmini
   - İyileşme süresi tahmini
   - Stres/rahatsızlık sınıflandırması

2. **Gelişmiş Görüntü Analizi**
   - Solunum hızı tespiti
   - Postür analizi
   - Anormal davranış tespiti

3. **Tahmine Dayalı Bakım**
   - Sensör arıza tahmini
   - Bakım zamanı önerileri
   - Enerji optimizasyonu

4. **Ses Analizi**
   - Hayvan ses tespiti (ağlama, inleme)
   - Alarm sistemleri entegrasyonu
   - Stres seviyesi belirleme

---

## 📁 Dosya Yapısı

```
lib/ai/
├── __init__.py          # Modül başlatıcı
├── vision.py            # Görüntü işleme motoru
├── analytics.py         # Sensör analiz motoru
└── manager.py           # AI koordinatörü

web/
├── script.js            # updateAIDisplay() fonksiyonu
├── styles.css           # AI panel stilleri
└── index.html           # AI panel HTML yapısı
```

---

## 📞 Destek

Sorularınız için GitHub Issues kullanabilirsiniz.

---

*Bu doküman Kuvoz AI sistemi için hazırlanmıştır. Son güncelleme: Mayıs 2026*
