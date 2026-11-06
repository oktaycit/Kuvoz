# Kuvoz Incubator Control System v3.0 - Web Interface

Modern web tabanlı kuluçka makinesi kontrol sistemi. Kivy yerine **Chromium Kiosk Mode** ile çalışır.

## 🌟 Özellikler

### 🌐 Web Interface
- **Responsive HTML/CSS/JavaScript** arayüz
- **Real-time WebSocket** iletişimi
- **Mobile-friendly** tasarım
- **Offline-capable** Progressive Web App

### 🎛️ Kontrol Sistemi
- **9 GPIO Channel** röle kontrolü (b9: soğutma dahil)
- **Opsiyonel PWM fan kontrolü** ayrı GPIO hattı üzerinden sistemin otomatik hız ayarı
- **SCD41** varsayılan iklim sensörü
- **DHT11/DHT22** yedek sıcaklık & nem sensörü
- **DFRobot Oxygen** opsiyonel oksijen sensörü  
- **Otomatik nebulizer** kontrol (oksijen sensörü yoksa)
- **Zamanlı ozon** kontrolü
- **Thread-safe GPIO** operasyonlar

### 🖥️ Kiosk Mode
- **Chromium fullscreen** interface
- **Auto-start** sistem boot'ta
- **Touch-friendly** controls
- **Auto-hide cursor**

## 📋 Sistem Gereksinimleri

- **Raspberry Pi OS Trixie** (Debian 13.1)
- **Python 3.13+**
- **Chromium Browser**
- **GPIO access** (pi user)
- **I2C enabled** (oksijen sensörü için)

## 🚀 Kurulum

### 1. Hızlı Kurulum
```bash
# Repository clone
git clone https://github.com/oktaycit/Kuvoz.git
cd Kuvoz

# Web interface kurulumu
make web-setup

# Sistem başlatma
make web-start
make kiosk-start
```

### 2. Adım Adım Kurulum

#### Web Dependencies
```bash
make web-install
```

#### Systemd Services
```bash
make web-service
make kiosk-service
```

#### Manuel Başlatma
```bash
# Web server
make web-dev

# Kiosk mode (ayrı terminal)
make kiosk-manual
```

## 🔧 Kullanım

### Web Interface Erişimi
- **Local**: http://localhost:8000
- **Network**: http://[raspberry-pi-ip]:8000
- **Kiosk Mode**: Otomatik fullscreen

### GPIO Pin Mapping
```python
outChannels = [5, 6, 13, 16, 19, 20, 21, 26, 12]
# b1: Pin 5  - Lighting
# b2: Pin 6  - Nebulizer  
# b3: Pin 13 - Humidity
# b4: Pin 16 - Carbon Temperature
# b5: Pin 19 - IR Temperature
# b6: Pin 20 - Fan
# b7: Pin 21 - UV Lighting
# b8: Pin 26 - Ozone
# b9: Pin 12 - Cooling
```

### PWM Fan Notu
PWM doğrudan röle çıkışına uygulanmaz. Fan hız kontrolü için fanın ayrı bir MOSFET/PWM sürücüsüne bağlanması gerekir.
Çıkış tipi sistem ayarlarından `relay` veya `pwm` olarak seçilebilir.

Örnek ortam değişkenleri:
```bash
export KUVOZ_FAN_PWM_ENABLED=1
export KUVOZ_FAN_PWM_PIN=18
export KUVOZ_FAN_PWM_FREQ=25000
export KUVOZ_FAN_PWM_HEATER_MIN_DUTY=35
```

### Sensor Configuration
```python
pinDht = 15      # DHT fallback data pin
sensorDht = 22   # DHT fallback sensor type
# I2C: SDA=GPIO2, SCL=GPIO3 (SCD41 + Oxygen sensor)
```

### Varsayılan Sensör Stratejisi
- `SCD41` ana sensördür; sıcaklık, nem ve CO2 verisini buradan alır.
- `DHT11/DHT22` yalnızca `SCD41` yoksa veya okuma başarısızsa yedek olarak devreye girer.
- Oksijen sensörü standart kurulumun parçası değildir; gerektiğinde opsiyonel olarak eklenir.

## 📁 Dosya Yapısı

```
Kuvoz/
├── web/                    # Web interface
│   ├── index.html         # Ana sayfa
│   ├── help.html          # Yardım kılavuzları sayfası
│   ├── styles.css         # CSS stilleri
│   └── script.js          # JavaScript logic
├── web_server.py          # Flask backend server
├── systemd/               # Service dosyaları
│   ├── kuvoz-web.service  # Web server service
│   └── kuvoz-kiosk.service # Kiosk mode service
├── scripts/               # Shell scriptleri
│   └── start-kiosk.sh     # Kiosk başlatma
├── config/                # Konfigürasyon
│   └── openbox-autostart  # X11 autostart
├── lib/                   # Sensor kütüphaneleri
│   ├── DHT_Native.py      # Fallback DHT driver
│   ├── DFRobot_Oxygen.py  # Optional oxygen sensor
│   └── SCD41_Sensor.py    # Primary SCD41 climate sensor
├── Makefile              # Ana makefile
├── chromium_kiosk.mk     # Kiosk setup commands
└── failure.dat           # Settings storage
```

## 🎯 Makefile Komutları

### 📦 Kurulum
```bash
make web-install     # Web dependencies
make web-setup       # Full setup
make kiosk-setup     # Kiosk only setup
```

### ⚡ Servis Yönetimi
```bash
make web-start       # Web server başlat
make web-stop        # Web server durdur
make kiosk-start     # Kiosk mode başlat
make kiosk-stop      # Kiosk mode durdur
make web-status      # Servis durumu
```

### 🔧 Geliştirme
```bash
make web-dev         # Development server
make web-test        # Interface testi
make kiosk-manual    # Manuel kiosk
```

### 🧹 Maintenance
```bash
make web-clean       # Setup temizle
make web-help        # Komut yardımı
```

## 🌐 Web Interface Özellikleri

### 📊 Dashboard
- **Real-time sensor** değerleri
- **GPIO button** durumları
- **Visual indicators** (renk kodlu)
- **Connection status** göstergesi

### 🎛️ Controls
- **9 GPIO button** toggles
- **12 manuel slider** ayarı + PWM modunda otomatik fan hızı göstergesi
- **System controls** (shutdown/restart)
- **Settings save/load**

### 📱 Mobile Support
- **Responsive design**
- **Touch-friendly** buttons
- **Swipe gestures**
- **Portrait/landscape** orientations

## 🔧 Teknik Detaylar

### Backend Architecture
```python
# Flask + WebSocket server
class KuvozServer:
    - GPIO control
    - Sensor reading  
    - WebSocket communication
    - Thread management

# Background threads
- Sensor thread: 15s interval
- Control thread: 1s interval
```

### Frontend Architecture
```javascript
// WebSocket client
class KuvozController:
    - Real-time communication
    - UI state management
    - Error handling
    - Offline fallback
```

### WebSocket Protocol
```json
// Sensor update
{
  "type": "sensor_update",
  "sensors": {
    "temperature": {"value": "25.5", "status": "OK"},
    "humidity": {"value": "65", "status": "OK"},
    "oxygen": {"value": "20.9", "status": "OK"}
  }
}

// Button control
{
  "command": "toggle_button",
  "data": {
    "name": "b1",
    "pin": 5,
    "state": true
  }
}
```

## 🔍 Troubleshooting

### Web Server Başlamıyor
```bash
# Service durumu kontrol
make web-status

# Manuel başlatma
make web-dev

# Log kontrol
journalctl -u kuvoz-web -f
```

### Kiosk Mode Problemi
```bash
# Display kontrol
echo $DISPLAY

# X11 test
xhost +local:

# Manuel başlatma
make kiosk-manual
```

### GPIO Permission Error
```bash
# User groups kontrol
groups $USER

# GPIO group ekle
sudo usermod -a -G gpio $USER
```

## 📚 Migration from Kivy

### Eski Kivy Sistem
- ❌ form.kv layout dosyası
- ❌ main3.py Kivy app
- ❌ TabbedPanel UI
- ❌ Render problems

### Yeni Web Sistem  
- ✅ HTML/CSS/JS interface
- ✅ web_server.py Flask app
- ✅ Responsive design
- ✅ Cross-platform compatible

### Migration Script
```bash
# Kivy dependencies kaldır
pip uninstall kivy

# Web dependencies kur
make web-install

# Service'leri yeniden kur
make web-setup
```

## 🤝 Katkıda Bulunma

1. Fork the project
2. Feature branch oluştur
3. Changes commit et
4. Branch'i push et
5. Pull Request aç

## 🔧 Bakım ve Destek

### Otomatik Bakım Sistemleri

Kuvoz sistemi **24/7 kesintisiz çalışma** için otomatik bakım sistemleriyle donatılmıştır:

- ✅ **Chromium Cache Yönetimi**: 50MB cache limiti, otomatik temizleme
- ✅ **Log Rotation**: Günlük log rotation, 7 gün saklama, 10MB limit
- ✅ **Günlük Otomatik Bakım**: Her gece 03:00'da otomatik cache temizliği ve yeniden başlatma
- ✅ **Memory Leak Önleme**: Düzenli kiosk yeniden başlatma

### Dokümantasyon

- **📘 [MAINTENANCE.md](docs/MAINTENANCE.md)** - Uzun süreli çalışma, bakım ve sorun giderme kılavuzu
- **📗 [KUVOZ_KULLANIM_KLAVUZU.md](docs/KUVOZ_KULLANIM_KLAVUZU.md)** - Kapsamlı kullanım kılavuzu
- **📙 [CLAUDE.md](CLAUDE.md)** - Geliştirici ve AI asistan kılavuzu
- **📕 [SYSTEM_REQUIREMENTS.md](docs/SYSTEM_REQUIREMENTS.md)** - Sistem gereksinimleri
- **📚 [docs/INDEX.md](docs/INDEX.md)** - Tüm Markdown kılavuzlarının indeksi
- **📓 [docs/AI_DYNAMIC_VITAL_THRESHOLDS.md](docs/AI_DYNAMIC_VITAL_THRESHOLDS.md)** - Dinamik vital eşik sistemi

## 📄 Lisans

MIT License - Detaylar için LICENSE dosyasına bakın.

## 👨‍💻 Geliştirici

**Oktay Çit** - [@oktaycit](https://github.com/oktaycit)

## 🔗 Links

- **GitHub**: https://github.com/oktaycit/Kuvoz
- **Issues**: https://github.com/oktaycit/Kuvoz/issues
- **Wiki**: https://github.com/oktaycit/Kuvoz/wiki

---

*Kuvoz Incubator Control System v3.0 - Modern web interface with Chromium Kiosk Mode* 🌐🖥️


### Kamera kaynağı seçimi

Sistem Ayarları → Kamera Kaynağı bölümünden **Raspberry Pi / Yerel Kamera**
veya **IP Kamera (RTSP)** seçilebilir. Eski ayar dosyaları yerel kamera ile
çalışmaya devam eder; Picamera2 ve mevcut OpenCV yedek yolu korunur.
IP kamera için yerel RTSP yayın adresini girip **Kamera Seçimini Kaydet**
düğmesine basın. Kaynak değişimi yalnızca kamera analizini yeniler.

Baysal test kamerasının düşük çözünürlüklü yayını:
`rtsp://192.168.1.175:554/live/ch00_1` (480×480, H.265).
Kuvozfurkan cihazında kuvöz içi kamera yayını:
`rtsp://192.168.1.24:554/live/ch00_1` (480×480, H.265; 23 Ekim 2026 tarihinde doğrulandı).
Kamera için yönlendiricide sabit DHCP adresi ayırmak önerilir.
Bu seçim analiz hızını veya vital ölçümün doğruluğunu kendiliğinden artırmaz.

IP yayını arka planda okunur ve yalnızca en yeni kare işlenir. Bağlantı
kesildiğinde görüntü ve önceki vital tahmin temizlenir; yeniden bağlantı
otomatik denenir. IP kamera seçiliyken yerel kameraya sessiz geçiş yapılmaz.
Adres kullanıcı adı/parola içeriyorsa bunlar mevcut yerel ayar dosyasına
kaydedilir; kamera adresini ve ayarlar sayfasını buna göre koruyun.


IP kamera analiz profili varsayılan olarak 5 kare/sn hedefler
(`system_settings.ip_camera_analysis_fps`, 3–8 aralığı). Hayvan yokken
75 saniyelik ilk gözlemden sonra yaşam döngüsü taraması 1 kare/sn,
yoğun harekette 2 kare/sn çalışır. Yerel kameranın eski hız ayarları korunur.
Önizleme ve solunum tahmini en fazla saniyede bir yenilenir; kare örnekleme
bağımsız sürer. `ai_health.effective_fps` son beş saniyede alınan gerçek
analiz hızını gösterir. IP analiz hızı 3 kare/sn altındaysa sayısal solunum
sonucu üretilmez (`LOW_SAMPLE_RATE`). Mevcut sıcaklık koruması korunur.
Bunlar performans ayarlarıdır; hayvan üzerinde referans ölçümle doğrulama
yapılmadan solunum doğruluğu kabul edilmemelidir.


### Canlı görüntü üzerinde alan seçimi

İş yükünü hayvan üzerinde yoğunlaştırmak için **hayvanın tamamını** küçük bir
payla seçin; solunum alanını baş, kaplar ve zeminden uzak, görünür gövde üzerinde
ayrıca seçin. Hayvan alanında hareket analizi yapılır, solunum sinyali yalnızca
ikinci alandan alınır. Seçili hayvanı izleyen optik akışın yanında ikinci bir
hareket-kontur takibi çalıştırılmaz. Yaşam döngüsüne iletilen konumlar tam
görüntü koordinatlarında kalır; mama/su alanları kamera değişince yeniden ayarlanmalıdır.

Optik akış piramitleri hayvanın yakın çevresiyle sınırlıdır; en fazla 40 takip
noktası kullanılır ve noktalar saniyede bir veya sayıları azaldığında yenilenir.
Gövde görünümü çok benzer kaldığında pahalı takip saniyede bir yapılır;
görünüm değişikliği bu beklemeyi kaldırır. Solunum örneklemesi bundan bağımsızdır.
Takip kaybında 1 kare/sn yeniden arama yapılır ve sayısal solunum temizlenir.
Bu sırada gözlenen kaba hareket yaşam döngüsü için korunur; kilit yokken
dinlenme veya yeme/içme doğrulanmış sayılmaz.
IP okuyucu akışı çözmeye devam eder, gereksiz renk dönüşümlerini atlar ve
bellekte yalnızca analiz çözünürlüğündeki son kareyi tutar. Video kaydı biriktirmez.
Her RTSP bağlantısının ilk 10 saniyesi kod çözücünün toparlanması için analize
verilmez; ilk görüntü veya yeniden bağlantı bu nedenle gecikebilir.
Küçük görüntüler CPU üzerinde işlenir; okuyucu ve analiz iş parçacıklarında
OpenCL kapalı tutulur. Küçük ölçek titreşimleri alanı yeniden boyutlandırıp
biriken solunum örneklerini sıfırlamaz; gerçek hareket ve takip kaybı yine durdurur.
`ai_health.pixel_budget` tam kare, hareket, son optik akış ve solunum alanlarının
piksel sayılarını gösterir; bunlar toplam işlemci tüketimi değildir. Kamera
akışının kod çözme maliyeti alan kırpmayla ortadan kalkmaz.

Sistem Ayarları → Solunum Bölgesi → **Canlı görüntü üzerinde hayvan ve
solunum alanı seç** bağlantısı `camera_regions.html` sayfasını açar.
**Hayvanın tamamı** ve **Göğüs / karın** düğmeleriyle hangi kutunun
çizileceğini seçin; fare veya parmakla sürükleyin. Mavi kutu yaşam döngüsü
analizini sınırlar, sarı kutu solunum sinyalinin alınacağı bölgedir.
Sarı kutu, mavi kutu etkinse onun içinde olmalıdır. Alanlar normalize
koordinatlarla saklanır; telefon, kiosk ve masaüstünde aynı bölgeyi gösterir.
**Alanları kaydet** yalnızca alan ayarlarını değiştirir, servis başlatmaz.
Kutuları ayrı ayrı devre dışı bırakarak otomatik takibe dönülebilir.

Bağlantı kesildiğinde çizim/kaydetme kapanır. Kamera kaynağı veya görüntü
yönü değişmişse eski görüntüden yapılan seçim reddedilir. Seçilen hayvan ve solunum kutuları optik akışla birlikte taşınır.
Hareket veya takip kurulması sırasında solunum duraklar. Takip kaybı,
görüntü kesilmesi, belirgin dönme/şekil değişimi veya görüntü dışına çıkma
durumunda önceki solunum sonucu ve örnekler temizlenir.

**Pozisyon değişiminde otomatik yeniden bulma:** Saniyede bir eski görünüm
aranır; eşleşmezse ORB doku noktaları ve yerel zemin/gövde ton farkı kullanılır.
Doku eşleşmesi azaldığında son güvenilir kareye göre değişmiş ve gövde görünümüne
uyan bölge de aday olabilir; bu yedek yol yalnız yaşam döngüsünü yeniden başlatır.
Kap alanları ve görüntünün dış kenarları aramadan çıkarılır. Birbirinden uzak
iki güçlü aday, boş sahne veya yetersiz eşleşme otomatik kilit oluşturmaz.
Aday en az iki saniye boyunca üç kez doğrulanır; ardından en az iki saniye ve
beş kararlı kare beklenir. Hayvanın bulunması yaşam döngüsünü yeniden başlatır;
aynı eski dikdörtgenin veya duruşun korunması gerekmez.

Solunum alanı yeni siluetin belli bir yüzdesi olarak tahmin edilmez. İlk seçilen
gövde alanı için birden fazla doku noktasının geometrik eşleşmesi ve hizalanmış
görüntü benzerliği gerekir. Yalnız hayvan bulunursa yaşam döngüsü **2 kare/sn**
ile sürer; gövde alanı iki saniyede bir tekrar aranır. Alan doğrulanıp hayvan
kararlı olduğunda **5 kare/sn** örneklemeye dönülür ve yeni solunum penceresi
birikir. Eski vital değerler yeni poza taşınmaz. İlk referans ve son iki güvenilir
görünüm tutulur; görünüm belleği 40 KB ile sınırlıdır, tam kare geçmişi biriktirilmez.
Başarısız referans yenilemeleri de dahil yeni görünüm çıkarma en fazla beş saniyede
bir yapılır. Gövde doğrulama taramasında siluet/zemin araması tekrar çalıştırılmaz.
`ai_health.region_tracking` içindeki `respiration_ready`, `recovery_kind` ve
`appearance_reference_bytes` bu durumu izlemeyi sağlar.

`KUVOZ_AI_CAMERA_REFERENCE_DIR` tanımlıysa, tek bir atomik kalibrasyon dosyasında
bu küçük hafıza ve son güvenilir gri kare korunur. Kararlı takipte en fazla
60 saniyede bir yenilenir; video geçmişi tutulmaz. Servis yeniden başlayınca
ekranın eski koordinatları doğrudan güvenilir sayılmaz: kayıtlı referansla yeniden
arama yapılır. Kamera kaynağı, yönü, çözünürlüğü veya alan seçimi/revizyonu
değişmişse eski dosya reddedilir. `reference_restored` alanı yüklemeyi gösterir.
Kuvozfurkan servisinde dizin `/home/vet/kuvoz/data/camera_reference` olarak ayarlıdır.

Bu tek hayvan için görüntü dokusu takibidir; tür veya anatomiyi tanıyan bir
model değildir. Yeterli doku/görüş bulunmadığında otomatik arama sürer ve
sayısal solunum bekler. İlk alan seçimi ölçüm doğruluğunu tek başına doğrulamaz.

### IP kamerayı MAC adresiyle yeniden bulma

Ayarlar → Kamera Kaynağı altında **Kamerayı otomatik bul** düğmesi, girilen
RTSP adresinin doğrudan bağlı olduğu yerel ağdaki kamera adaylarını listeler.
Kamerayı seçip kaydedince `ip_camera_mac` kalıcı olarak saklanır. MAC alanını
boş bırakmak önceki, yalnızca adrese bağlı çalışma biçimini korur.

Bağlantı kurulurken IP adresinin kayıtlı MAC ile eşleşmesi gerekir. IP değişirse
komşu tablosu, gerekirse yalnızca aynı yerel alt ağ taranır; başka MAC adresindeki
kameraya geçilmez. RTSP yolu, portu ve varsa kullanıcı bilgileri korunur. Aynı
kimlik denetimi HD önizlemeye de uygulanır. Başarısız aramalar 5 saniyeden
başlayıp en fazla 120 saniye aralığa uzar; sağlıklı yayında ağ taraması yapılmaz.
Tarama yönetici yetkisi gerektirmez, en fazla 1024 yerel adres ve 16 geçici işçiyle
sınırlıdır. Kamera elektriksizken ölçüm üretilmez, erişim dönünce yeniden bağlanılır.

IP adresinden MAC kimliğine ilk geçişte eski takip hafızası otomatik olarak
başka bir kameraya kabul edilmez. Aynı cihaz olduğu doğrulanmış kurulumlarda
`scripts/migrate_camera_reference.py --previous-url <eski-rtsp-adresi> --mac <kayıtlı-mac>`
komutu eski kamera/kalibrasyon imzasını ve yerel ağdaki MAC eşleşmesini kontrol
eder, referansı yedekler ve atomik olarak yeni kimliğe taşır. Sonraki açılışta
eski koordinatlara doğrudan kilitlenmek yerine canlı görüntüde yeniden arar.

### Sabit kamerada farklı pozisyonları izleme

`KUVOZ_AI_SCENE_TRACKING=1` sabit kuvöz kamerası için sahne destekli takibi açar
(`systemd/kuvoz-scene-tracking.conf` isteğe bağlı servis ek ayarıdır). Küçük gri
arka plan hafızası, seçilmiş hayvanın görünüş referansları ve yerel optik akış
birlikte kullanılır. Mama/su alanları aramadan çıkarılır. Duruş değişince hayvan
bütün gövdesinin eski şekline uymak zorunda kalmadan yeniden bulunur. Sabit
pozisyonda pahalı görünüş araması yerine küçük bir doku kontrolü yapılır.
Arka plan kamera/kalibrasyon imzasıyla birlikte saklanır; değişen kameraya taşınmaz.
Referanslar ve sahne maskeleri toplamı yaklaşık 0,2 MB ham görüntü belleğidir.

Solunum için önce kayıtlı gövde yüzeyi yerel olarak eşleştirilir. Bu doku yeni
pozisyonda görünmüyorsa hayvanın kalın, içte kalan ve dokulu yüzeyinde otomatik
aday alan seçilebilir. Bu alan anatomik referans olarak öğrenilmez. Alan en az
üç gözlem ve dört saniye kararlı kalınca örnekleme başlar. Hareket, takip kaybı,
alan değişimi ve yetersiz kare hızı örnek penceresini temizler. Sayısal tahmin
ancak en az 30 saniye / beş çevrim, dört küçük yüzeyin en az üçünde uyumlu
periyodiklik, frekans yoğunluğu ve zaman içinde tekrar doğrulanınca gösterilir.
Arka plan üzerinden ışık kazancı/ofseti düzeltilir; gürültü, genel ışık titreşimi
ve tek bir parçanın hareketi tek başına solunum sayısı oluşturmaz.

Kuvozfurkan'da sahne izleme etkinleştirilmiştir. `region_tracking` içindeki
`respiration_source` değeri `reference` veya `surface`, `surface_samples` ise
ikinci yöntemin gerçek örnek sayısını gösterir. Başlamış örnekleme, tek başına
geçerli bir solunum sayısı veya klinik ölçüm doğrulaması anlamına gelmez.

Kısa pozisyon kayıplarında son 15 saniyede doğrulanmış görünüş/konum ve sahne
ayrımı birlikte kullanılır; tek başına histogramla sınırsız arama yapılmaz.
Açılışta son 24 saat içindeki aynı kamera/kalibrasyona bağlı güvenilir kare bu
sürekliliği başlatabilir, ancak eski koordinatlar doğrudan kilit sayılmaz.
Son iki gövde görünüşü yenilenirken ilk anatomik referans korunur; otomatik
solunum yüzeyi hiçbir zaman anatomik referans olarak kaydedilmez.


### Kamera gözlemi — ilk sürüm

`/camera-observation` ekranı, AI oturumunun en fazla son bir saatindeki hareketli/düşük hareket sürelerini, dakikalık hareket çizelgesini ve doğrulanmış konum değişimlerini gösterir. `/ai-vitals` adresi de bu ekrana açılır. Eski vital kayıtları korunur; kamera solunum tahmini ve yeni vital raporu üretimi devre dışıdır.

- Karanlık, aşırı aydınlık, düşük netlik, düşük takip güveni ve 10 saniyeden eski görüntü değerlendirme dışıdır. Görünürlük/örtülme için ayrıca eğitilmiş bir model yoktur.
- Konum değişimi: normalize kadrajda merkez uzaklığı 0,10'u aşan, 5 saniye süren yer değiştirme. Takip yeniden kazanıldığında yeni referans alınır.
- Postür alanı yalnızca takip bölgesinin yatay/dikey yönelim tahminidir; anatomik yatma/oturma/ayakta durma sınıflandırması henüz yoktur. Seçilen bölgenin şekli sonucu etkiler.
- Özetler bellektedir; AI yeniden başlatıldığında veya hasta kimliği değiştiğinde sıfırlanır. Düşük hareket uyku veya klinik iyileşme olarak yorumlanmaz.
- Doğrulama: `python3 -m unittest test_camera_observation test_ai_manager_lifecycle test_ai_behavior_mapper test_ai_vision_load_profiles`. Gerçek kamera eşikleri Raspberry Pi görüntüleriyle doğrulanmalıdır.

### Arayüz dilleri ve klinik hatırlatmalar

Dil menüsü Türkçe, İngilizce, Almanca, İspanyolca, Portekizce, Rusça,
Korece, Çince, Japonca ve Arapça seçeneklerini içerir. Arapça seçildiğinde
sayfa sağdan sola gösterilir. Küçük kiosk ekranında dil seçimi bakım menüsündedir.

Bakım menüsündeki **Hatırlatmalar** ekranından tedavi veya ilaç için açıklama,
tarih/saat ve tekrar aralığı belirlenir. `0` tek seferlik hatırlatmadır.
Kayıt oluşturulurken mevcut hastanın kimliği/adı eklenir; hasta değişse bile
hatırlatmanın hasta bilgisi korunur. Kayıtlar `data/reminders.json` dosyasına
atomik olarak yazılır. Cihaz yeniden başlarsa geçmiş tarihli bekleyen kayıtlar
ilk bağlantıda gösterilir.

Açık arayüzler 5 saniyede bir cihazın saatine göre durumu kontrol eder. Süresi
gelen kayıtlar onaylanana, iptal edilene veya 5 dakika ertelenene kadar görünür.
Ses için önce ekrana dokunulması, tarayıcının açık tutulması ve cihazın ses
çıkışının çalışması gerekir; etkin sesli bildirim 30 saniyede bir tekrarlanır.
Tarayıcı kapalıyken ses üretilmez. Tekrarlı kaydın sonraki zamanı, **Tamamlandı**
onayından itibaren hesaplanır; kaçırılan uygulamalar peş peşe hatırlatılmaz.
Bu özellik ilaç uygulamaz ve GPIO çıkışlarını değiştirmez.

API: `GET/POST /api/reminders`,
`PATCH /api/reminders/<id>` (`action`: `acknowledge`, `snooze`, `cancel`).
