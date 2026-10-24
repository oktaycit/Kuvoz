# Kuvöz STM32F407VE + BM5010NN İmplementasyon Planı

Tarih: 25 Eylül 2026  
Hedef: İnternet ve HMI arızasında da güvenli çalışabilen ilk saha prototipi

## Uygulama durumu

- [x] Ayrı `/Users/oktaycit/Projeler/kuvoz-esp` proje alanı oluşturuldu.
- [x] B1–B9 donanım arayüzü ve güvenlik gereksinimi taslakları yazıldı.
- [x] Pi–STM32 protokol v1 taslağı oluşturuldu.
- [x] Donanımdan bağımsız C kontrol çekirdeği ve ilk host testleri oluşturuldu.
- [x] Isıtma–soğutma ve nebulizatör–fan interlock testleri geçti.
- [ ] Kart revizyonu ve elektriksel yük envanteri doğrulanacak.
- [ ] STM32CubeMX/HAL projesi kesin pin tablosuyla üretilecek.
- [ ] Boot-safe GPIO, IWDG ve fiziksel haberleşme loopback testi yapılacak.

## 1. Sabitlenen mimari

```text
BMBC BM5010NN HMI
        |
  İzole RS485 / Modbus RTU
        |
STM32F407VE ana kontrol kartı
  |-- 2 x SHT31 sıcaklık/nem
  |-- 1 x DS18B20 bağımsız sıcaklık
  |-- O2 ve CO2 sensörleri (opsiyonel faz)
  |-- 9 güvenli işlev çıkışı -> sürücü -> röle/kontaktör/MOSFET
  |-- buzzer, ikaz LED'i, kapı/acil durum girişleri
  `-- opsiyonel haberleşme kartı -> HTTPS -> Firebase
```

- STM32 bütün kontrol ve emniyet kararlarının tek sahibidir.
- HMI yalnızca ölçüm gösterir, ayar talebi ve kullanıcı komutu gönderir.
- HMI, RS485 veya internet kesilse de son doğrulanmış reçeteyle kontrol sürer.
- Firebase doğrudan HMI'ya bağlanmaz. Gerekirse ayrı ağ kartı kullanılır.
- Bulut veya HMI komutları doğrudan röle süremez; STM32 emniyet kapısından geçer.

## 2. MVP kapsamı

İlk çalışan sürümde:

- iki noktadan sıcaklık/nem ölçümü,
- bağımsız aşırı sıcaklık ölçümü,
- ısıtma, IR ısıtma, fan ve nemlendirme kontrolü,
- dokuz işlev çıkışının servis modunda tek tek testi,
- yerel sesli/görsel alarm,
- ayarların kalıcı saklanması,
- BM5010NN üzerinde ana ekran, ayarlar, alarm ve servis ekranları,
- sensör kopması, HMI kopması ve watchdog testleri bulunacaktır.

Oksijen, CO2, ozon otomasyonu ve Firebase MVP sonrasında devreye alınacaktır. Ozon çıkışı bu işlev tamamlanana kadar varsayılan kapalı tutulacaktır. İlk MVP, mevcut Raspberry Pi yazılımının yerine bir anda geçmeyecek; Pi ile paralel gözlem (shadow mode), yüklerin kademeli devri ve geri dönüş testi uygulanacaktır.

## 2.1 Mevcut sistemle uyumluluk tabanı

STM32 davranışı, yalnız eski sekiz röle tablosuna göre değil güncel uygulamaya göre doğrulanacaktır:

| Kimlik | Güncel işlev | Pi çıkışı | STM32 hedefi |
|---|---|---:|---|
| B1 | Terapi aydınlatması | GPIO5 | Dijital röle |
| B2 | Nebulizatör | GPIO6 | Dijital röle + fan interlock |
| B3 | Nem kontrolü | GPIO13 | Dijital röle |
| B4 | Isıtma pedi | GPIO16 | Emniyet zincirli röle/kontaktör |
| B5 | IR ısıtıcı | GPIO19 | Emniyet zincirli röle/kontaktör |
| B6 | Havalandırma fanı | GPIO20 röle veya GPIO18 PWM | Röle ve MOSFET/PWM varyantı |
| B7 | UV sterilizasyon | GPIO21 | Kilitlemeli dijital röle |
| B8 | Ozon sterilizasyon | GPIO26 | Varsayılan kapalı, güvenlik kilitli röle |
| B9 | Soğutma | GPIO12 | Dijital röle/kontaktör |

- Güncel ayar sözleşmesi `sld1..sld13` ve düğme sözleşmesi `b1..b9` olarak korunur.
- Birincil iklim kaynağı SCD41; seçime/arıza durumuna göre DHT11/DHT22 yedektir. STM32 sensör seçimi bununla aynı sonucu üretmeli veya kontrollü bir ürün kararıyla değiştirilmelidir.
- CO2 yüksekliği fanı devreye alır; yüksek nem purgesi fan talebi üretir; aktif nebulizatör fanı zorla kapatır.
- B4/B5 çalışırken PWM fanın asgari görevi, B9 soğutma hedefi (`sld12`) ve manuel PWM görevi (`sld13`) eşdeğer testlerle korunur.
- Web arayüzü geçiş döneminde mevcut Socket.IO olay adlarını kullanmaya devam eder. Pi, STM32 telemetrisini mevcut `sensor_update`, `button_update`, `timer_update` ve `status_response` yapılarına çeviren gateway rolünde kalabilir.

## 3. Donanım iş paketleri

### HW-01 — Kart ve yük envanteri

- STM32 kartının tam revizyonunu ve şemasını doğrula.
- Sekiz yük için gerilim, sürekli akım, kalkış akımı ve aktif seviyeyi ölç.
- Isıtıcıların toplam gücünü ve röle/kontaktör ihtiyacını belirle.
- BM5010NN COM2 pin dizilimini HMI kılavuzu veya ölçümle doğrula.
- SHT31, DS18B20, O2 ve CO2 sensörlerinin tam modelini kaydet.

**Çıkış:** Onaylı pin tablosu, yük tablosu ve pano tek-hat şeması.  
**Kabul:** Belirsiz pin, besleme veya yük akımı kalmaması.

### HW-02 — Güç ve emniyet zinciri

- 230 VAC girişe sigorta, ana şalter, PE/topraklama ve uygun klemens ekle.
- 24 V DIN güç kaynağından BM5010NN'yi besle.
- STM32 ve röleler için 24 V → 5 V izole DC/DC kullan.
- Isıtıcı enerjisini manuel resetli mekanik termostat ve uygun kontaktörden geçir.
- Güç verildiğinde bütün rölelerin donanımsal olarak kapalı kalmasını sağla.
- Şebeke ve SELV bölümlerini pano içinde fiziksel olarak ayır.

**Kabul:** STM32 sökülüyken veya reset halindeyken ısıtıcılar enerjilenmemeli.

### HW-03 — I/O ara kartı

- Dokuz işlev çıkışını sürmek için ULN2803A'nın sekiz kanalı yanında ikinci uygun sürücü kanalı veya daha geniş bir sürücü çözümü kullan.
- Fan PWM varyantı için röleden ayrı, fanın gerilim/akımına uygun logic-level MOSFET sürücüsü ve donanımsal kapalı varsayılan ekle.
- Her kanal için durum LED'i ve ölçüm/test noktası koy.
- Endüktif DC yüklerde geri tepme koruması; AC yüklerde uygun snubber/MOV kullan.
- Kapı, acil durdurma ve termostat geri bildirimi için en az üç dijital giriş ayır.
- SWD ve servis UART/USB bağlantılarını erişilebilir bırak.

### HW-04 — RS485 hattı

- 3,3 V uyumlu, galvanik izole RS485 transceiver kullan.
- A/B hattına TVS, seçilebilir 120 ohm sonlandırma ve bias dirençleri ekle.
- BM5010NN COM2 ile kısa, ekranlı twisted-pair kablo kullan.
- İlk ayar: `115200 veya 38400, 8N1, slave 1`; gerçek kararlılık testine göre sabitle.

**Kabul:** Röleler anahtarlanırken 24 saatlik testte CRC/zaman aşımı oranı kabul edilen sınırda olmalı; başlangıç hedefi `%0,1` altında.

## 4. STM32 yazılım yapısı

Sulama projesinden STM32F407 başlangıç, watchdog, kalıcı ayar, fault manager, USB/SWD derleme ve test altyapısı yeniden kullanılabilir. Sulamaya özel vana, TFT ve reçete kodları doğrudan taşınmayacaktır.

Firmware, ana web uygulaması deposuna gömülmeden kardeş proje dizini olan `/Users/oktaycit/Projeler/kuvoz-esp` altında geliştirilecektir. `kuvoz` ile `kuvoz-esp` birbirinin kaynak dosyalarını doğrudan import etmeyecek; entegrasyon yalnız sürümlü protokol ve ortak test vektörleri üzerinden yapılacaktır.

```text
kuvoz-esp/
  Core/
  App/
    sensors/       SHT31, DS18B20, O2, CO2
    control/       sıcaklık, nem, fan ve terapi durum makineleri
    safety/        interlock, fault manager, watchdog
    outputs/       güvenli röle/PWM soyutlaması
    hmi/           Modbus RTU register sunucusu
    persistence/   ayarlar, CRC ve sürümleme
    diagnostics/   olay kaydı ve servis telemetrisi
  Protocol/        Pi/HMI sözleşmeleri ve üretilen sabitler
  Tests/           host birim, golden-vector ve HIL testleri
  Docs/            pin tablosu, güvenlik gerekleri ve karar kayıtları
```

Ana döngüler:

| İş | Periyot | Davranış |
|---|---:|---|
| Sensör örnekleme | 1 s | Okuma, filtreleme, yaş ve geçerlilik kontrolü |
| Emniyet kontrolü | 50–100 ms | Limit ve interlock değerlendirme |
| Kontrol algoritması | 500 ms | Histerezisli sıcaklık/nem/fan kontrolü |
| HMI register güncelleme | 200 ms | Atomik durum görüntüsü |
| Kalıcı kayıt | Değişiklikten 2–5 s sonra | Flash aşınmasını önleyen gecikmeli yazma |
| Watchdog | Sürekli | Yalnız sağlıklı görevler tamamlanınca besleme |

Kontrol durumları:

`BOOT_SAFE → SELF_TEST → STANDBY → RUNNING → DEGRADED/FAULT`

- `BOOT_SAFE`: bütün kritik yükler kapalı.
- `SELF_TEST`: sensör, ayar CRC'si, girişler ve röle varsayılanları kontrol edilir.
- `DEGRADED`: yedek sensörle sınırlı çalışma; HMI'da açık uyarı.
- `FAULT`: ısıtma, nem, IR ve ozon kapalı; fan güvenli politikaya göre çalışır.

## 5. HMI–STM32 Modbus sözleşmesi

STM32, Modbus RTU slave; BM5010NN master olacaktır. BMBC HMI Editor içinde uygun Modbus RTU master sürücüsü doğrulanmadan ekran geliştirmesine başlanmaz.

### Salt-okunur giriş registerları (`3xxxx`)

| Adres | Alan | Birim/ölçek |
|---:|---|---|
| 30001 | Oda sıcaklığı 1 | °C × 10, signed |
| 30002 | Oda nemi 1 | %RH × 10 |
| 30003 | Oda sıcaklığı 2 | °C × 10, signed |
| 30004 | Oda nemi 2 | %RH × 10 |
| 30005 | Isıtıcı sıcaklığı | °C × 10, signed |
| 30006 | Oksijen | % × 10, yoksa `0xFFFF` |
| 30007 | CO2 | ppm, yoksa `0xFFFF` |
| 30008 | Sistem durumu | durum enum |
| 30009 | Aktif hata kodu | fault enum |
| 30010 | Sensör geçerlilik bitleri | bit maskesi |
| 30011 | Çıkış gerçek durumları B1–B9 | bit maskesi |
| 30012 | HMI haberleşme sayacı | artan sayaç |
| 30013–30014 | Çalışma süresi | 32-bit saniye |
| 30015 | Firmware sürümü | packed major/minor |
| 30016 | Fan gerçek PWM görevi | % × 10 |
| 30017 | İklim sensör kaynağı | SCD41/DHT/SHT31 enum |
| 30018 | Haberleşme/telemetri yaşı | saniye |

### Ayar holding registerları (`4xxxx`)

| Adres | Alan | İzin verilen ilk aralık |
|---:|---|---|
| 40001 | Sıcaklık hedefi | 20,0–40,0 °C |
| 40002 | Sıcaklık histerezisi | 0,2–2,0 °C |
| 40003 | Nem hedefi | %30–80 RH |
| 40004 | Nem histerezisi | %2–10 RH |
| 40005 | Yüksek sıcaklık alarmı | hedef + güvenli sınır |
| 40006 | Düşük sıcaklık alarmı | ürün gereksinimine göre |
| 40007 | Fan güvenli görev oranı | %0–100 |
| 40008 | Kullanıcı modu | enum |
| 40009 | Komut sıra numarası | tekrar engelleme |
| 40010 | Komut kodu | start/stop/reset/silence |
| 40011 | Komut değeri | komuta bağlı |
| 40012 | Komut onayı | STM32 sonuç kodu |
| 40013 | Soğutma hedefi | °C × 10; kapalı/manual kodu ayrıca tanımlı |
| 40014 | Fan kontrol modu | auto/manual enum |
| 40015 | Fan çıkış modu | relay/PWM enum; servis yetkili |
| 40016 | Manuel fan görevi | % × 10 |

Register numaraları ilk HMI prototipinden sonra `v1` olarak dondurulur. Her yazma STM32 tarafından aralık, durum, interlock ve sıra numarasıyla doğrulanır. HMI'daki değer, STM32 onayından sonra kesinleşir.

Modbus tablosu tek bir makine-okunur kaynakta (CSV/YAML) tutulup STM32 sabitleri, Pi eşleyicisi, HMI etiket listesi ve test fixture'ları buradan üretilmelidir. 32-bit alanların word sırası, signed değerler, `0xFFFF` geçersiz değeri ve ölçekler sözleşmede açıkça sabitlenmelidir.

## 5.1 Pi–STM32 geçiş haberleşmesi

- İlk tercih: HMI için ayrılmış RS485'ten bağımsız UART/USB-CDC veya ikinci izole RS485 hattı.
- Çerçeve: sürüm, mesaj tipi, sıra numarası, payload uzunluğu, payload ve CRC.
- Mesajlar: `HELLO`, `SNAPSHOT`, `SENSOR_SAMPLE`, `OUTPUT_STATE`, `SETTINGS_GET/SET`, `COMMAND`, `ACK/NACK`, `FAULT_EVENT`, `HEARTBEAT`.
- STM32 komutları yalnız sıra numarası yeni, CRC doğru, süre aşımı dolmamış ve emniyet durumu uygunsa uygular.
- Haberleşme kesilince Pi/HMI röle durumunun sahibi olmaz; STM32 son doğrulanmış reçeteyle devam eder veya hata politikasına geçer.
- Pi tarafındaki adaptör, mevcut web istemcisine protokol değişikliği göstermeden STM32 durumunu güncel Socket.IO şemasına dönüştürür.

## 6. BM5010NN ekranları

1. **Açılış/self-test:** firmware, sensör ve haberleşme durumu.
2. **Ana ekran:** büyük sıcaklık/nem değerleri, hedefler, çalışma modu ve alarm şeridi.
3. **Kontrol:** başlat/durdur, hedef sıcaklık/nem ve izinli terapi fonksiyonları.
4. **Alarmlar:** aktif hata, sade açıklama, zaman ve yapılacak işlem.
5. **Servis:** giriş/çıkışlar, ham sensörler, registerlar ve kontrollü röle testi.
6. **Sistem:** sürümler, çalışma saati, HMI/STM32 bağlantı durumu.

Operatör ekranında teknik register numarası gösterilmez. Kritik ayar ve servis ekranları PIN ile korunur. HMI bağlantısı kaybolduğunda STM32 yerel alarm verir fakat kontrolü bırakmaz.

## 7. Opsiyonel Firebase haberleşme kartı

Bu faz, yerel sistem kabul testlerinden sonra başlatılır.

- Fiziksel arayüz: STM32'nin HMI'dan ayrı UART/RS485 portu.
- İlk tercih: kablolu Ethernet destekli küçük gateway; Wi-Fi yalnız kablo mümkün değilse.
- Protokol: sürümlü çerçeve, CRC, sıra numarası ve ACK/NACK.
- Buluta gidenler: telemetri, aktif hata, olay ve cihaz sağlığı.
- Buluttan gelenler: yalnız izin verilen ayar/komut talepleri.
- Ağ kartı röle GPIO'suna bağlanmaz.
- Firebase erişimi HTTPS/TLS, cihaz bazlı kimlik ve dar güvenlik kurallarıyla yapılır.
- İnternet kesintisinde sınırlı çevrimdışı kuyruk ve artan yeniden deneme uygulanır.
- Servis hesabı özel anahtarı firmware'e gömülmez.

**Kabul:** Gateway sökülünce veya kilitlenince yerel kontrol ve HMI etkilenmemeli.

## 8. Uygulama fazları ve tahmini takvim

| Faz | Süre | Teslimat | Geçiş kriteri |
|---|---:|---|---|
| 0 — Doğrulama | 2–3 gün | Kart/yük/pin/HMI protokol raporu | Belirsiz kritik bağlantı yok |
| 1 — Masaüstü donanım | 4–5 gün | Güç, RS485, sensör ve röle test düzeneği | Güvenli açılış ve tekil I/O testi |
| 2 — Firmware temel | 1 hafta | Sürücüler, watchdog, fault, olay kaydı ve kalıcı ayar | Simüle arızalarda güvenli çıkış |
| 3 — Kontrol motoru | 1 hafta | Isıtma, IR, nem, fan/PWM, soğutma durum makineleri | Pi ile aynı girdilerde eşdeğer karar |
| 4 — HMI | 1 hafta | Dört ana ekran ve Modbus v1 | 24 saat kesintisiz HMI testi |
| 5 — Pi köprüsü ve shadow mode | 3–5 gün | Seri protokol adaptörü, Socket.IO uyumu, karar karşılaştırma kaydı | Röleler hâlâ Pi'deyken 72 saat karar farkı raporu |
| 6 — Entegrasyon | 1 hafta | Tam prototip pano ve kademeli yük devri | Hata enjeksiyon ve geri dönüş testleri geçer |
| 7 — Soak/saha pilotu | 1–2 hafta | Test raporu ve pilot cihaz | 72 saat yük testi + kontrollü pilot |
| 8 — Bulut opsiyonu | 1–2 hafta | Gateway/Firebase prototipi | Ağ arızası yerel sistemi etkilemez |

Yerel MVP için gerçekçi hedef, parçalar hazırsa **6–8 hafta**dır. Bulut işlevi ayrı teslimattır.

## 9. Test ve kabul matrisi

Zorunlu testler:

- soğuk açılış, sıcak yeniden başlatma ve ani enerji kesintisi,
- SHT31 sensörlerinin tek tek ve birlikte sökülmesi,
- iki SHT31 arasında sapma oluşturma,
- SCD41/DHT/SHT31 kaynak değişimi ve eski/geçersiz veri,
- DS18B20 aşırı sıcaklık ve mekanik termostat açması,
- HMI kablosu kopması ve hatalı register yazımı,
- RS485'e elektriksel gürültü ve yoğun röle anahtarlama,
- STM32 watchdog kilitlenme simülasyonu,
- rölenin açık/kapalı yapışması için geri bildirim senaryosu,
- B9 soğutmanın ısıtma ile çakışması ve güvenli dead-band,
- fan röle/PWM modları, minimum görev, CO2/nem talepleri ve nebulizatör-fan interlock'u,
- B7 UV ve B8 ozon için hasta/kapı/servis modu kilitleri,
- bozuk ayar CRC'si ve fabrika varsayılanına dönüş,
- 72 saat kesintisiz nominal yük testi,
- maksimum ortam sıcaklığında pano termal testi.

Pilot öncesi tüm kritik arızalarda beklenen güvenli çıkış durumu ölçülüp imzalı test formuna kaydedilir. Canlı hayvanla deneme, masaüstü ve boş kabin testleri tamamlanmadan yapılmaz.

## 10. İlk sprint backlog'u

1. Kart revizyonu, yükler ve sensör modelleri için fotoğraf/etiket envanteri çıkar.
2. BM5010NN COM2 pin dizilimi ile Modbus RTU master sürücüsünü HMI Editor'da doğrula.
3. `/Users/oktaycit/Projeler/kuvoz-esp` içinde B1–B9, fan PWM, girişler ve sensörler için kesin pin tablosunu oluştur; STM32CubeMX projesini aç.
4. `b1..b9`, `sld1..sld13`, sensör alanları ve hata kodları için sürümlü uyumluluk matrisi hazırla.
5. Güvenli GPIO başlangıcı, watchdog ve fault manager'ı ayağa kaldır.
6. Bir SHT31, bir DS18B20 ve tek röleyle masaüstü testini tamamla.
7. İzole RS485 üzerinden test registerı okuyup yaz.
8. Pi–STM32 protokolünün `HELLO`, `SNAPSHOT`, `COMMAND` ve `ACK/NACK` mesajlarını masaüstü simülatöründe doğrula.
9. Sonuca göre dokuz işlev çıkışlı I/O ara kartı şemasını dondur.

İlk sprintin bitiş ölçütü: HMI'da canlı sıcaklık görülmesi, hedef değerin STM32 tarafından doğrulanarak alınması ve herhangi bir reset/kablo kopmasında rölenin güvenli kapalı kalmasıdır.

## 11. Sahiplik, geçiş ve geri dönüş kuralları

1. **Host simülasyonu:** STM32 kontrol motoru donanımdan ayrıştırılır; kayıtlı Pi sensör akışlarıyla masaüstü birim testleri çalışır.
2. **Shadow mode:** Pi çıkışları sürmeye devam eder. STM32 aynı sensör/ayarlarla yalnız karar üretir; farklar zaman damgalı kaydedilir.
3. **Tekil yük devri:** Önce B1 gibi düşük riskli yük, sonra fan/nem, en son ısıtıcılar devredilir. Her adımda fiziksel geri dönüş anahtarı veya sökülebilir köprü bulunur.
4. **Emniyet devri:** Watchdog, termostat, sensör kopması, haberleşme kaybı ve enerji kesintisi testleri tamamlanmadan B4/B5 STM32'ye verilmez.
5. **Kontrol sahipliği:** Aynı yükü Pi ve STM32 asla paralel sürmez. Sahiplik donanımsal seçim ve yazılım durumu ile tekil olmalıdır.
6. **Geri dönüş:** Onaylı Pi sürümü, kablo/pin geri dönüş şeması ve ayar dönüştürücüsü pilot boyunca saklanır. Geri dönüş süresi masaüstünde ölçülür.

## 12. Açık kararlar ve ilk kapılar

- STM32F407VE kartının kesin modeli/revizyonu ve kullanılabilir pinleri.
- Dokuzuncu röle kanalı ile fan PWM güç katının elektriksel tasarımı.
- Ürün sensör seti: mevcut SCD41 + DHT yedeğinin korunması mı, çift SHT31'e geçiş mi?
- B4/B5/B9 için yük gücü, kontaktör/SSR seçimi ve donanımsal geri bildirim.
- Kapı sensörü, hasta varlığı ve acil durdurmanın gerçek giriş donanımı.
- BM5010NN'nin Modbus RTU master kabiliyeti, register veri tipleri ve kablo pin dizilimi.
- Pi'nin nihai üründe web/bulut gateway olarak kalıp kalmayacağı.
- Ozon/UV kullanımının klinik prosedürü; bu karar olmadan otomatik B7/B8 etkinleştirilmez.

Bu kapılar kapanmadan PCB ve HMI register haritası üretim için dondurulmaz.

### Depo ve sürümleme sınırı

- `kuvoz`: Raspberry Pi web arayüzü, Socket.IO gateway, Firebase, kayıt, AI ve hasta profilleri.
- `kuvoz-esp`: STM32 firmware'i, BM5010NN Modbus sözleşmesi, bootloader, kart konfigürasyonu ve donanım testleri.
- Protokol sürümü iki tarafta açıkça sabitlenir; uyumsuz major sürümde çıkış komutu kabul edilmez.
- Ortak golden test vektörlerinin ana kopyası `kuvoz-esp/Tests/vectors` altında tutulur; Pi tarafındaki testler yayınlanmış sürümü kullanır.
- Firmware binary ve üretim paketleri ana `kuvoz` deposuna kaynak olarak kopyalanmaz; sürüm etiketi ve checksum ile yayımlanır.

## 13. Mevcut koddan doğrulanacak güvenlik farkları

- Mevcut ozon hesabı yüksek O2'de çalışma süresini uzatıyor; düşük/geçersiz O2 için tek başına kesin kapatma garantisi vermiyor. STM32 gereksinimi, **gerçek O2 geçersiz veya onaylı alt sınırın altındaysa B8 OFF** olarak tanımlanmalı; CO2'den türetilen tahmini O2 ozon izni vermemelidir.
- Dezenfeksiyon modunun bugün B1–B6'yı kapatma davranışı; kapı/hasta varlığı girişleri ve B7/B8 karşılıklı kilitleriyle ürün güvenlik gereksinimine dönüştürülmelidir.
- Haberleşme heartbeat kaybında fanın OFF mı yoksa güvenli ventilasyon görevinde mi kalacağı risk analiziyle kararlaştırılmalıdır; tek bir evrensel varsayım kullanılmamalıdır.
- Duty/free fazlarının reset sonrasında `READY/OFF` başlaması veya kalıcı sürdürülmesi açıkça seçilmeli ve güç kesintisi testine bağlanmalıdır.
