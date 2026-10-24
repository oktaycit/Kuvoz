# Kuvöz STM32F407 + BM5010NN Kontrol Paneli Planı

Tarih: 25 Eylül 2026  
Durum: İlk prototip için öneri

## Mimari karar

İlk prototipte elde bulunan **STM32F407VE geliştirme kartı** ana kontrolcü, elde bulunan **BMBC BM5010NN** ise dokunmatik operatör paneli olarak kullanılacaktır. STM32 sensörleri, sekiz çıkışı ve bütün emniyet mantığını çalıştıracak; HMI yalnızca gösterge ve kullanıcı komutlarını yönetecektir.

İki birim kısa, ekranlı ve kilitli soketli bir **izole RS485** hattıyla haberleşecektir. Raspberry Pi, ESP32, Android tablet, DWIN, işletim sistemi ve zorunlu ağ bağlantısı kullanılmayacaktır. Donanımsal aşırı sıcaklık termostatı ve güvenli röle açılış devresi, mikrodenetleyiciden bağımsız koruma sağlayacaktır.

Firebase gerekiyorsa sisteme üçüncü, opsiyonel bir **iletişim kartı** eklenir. Bu kart kontrol döngüsüne dahil olmaz. STM32'den salt durum/ölçüm verisi alır, Firebase'e gönderir ve buluttan gelen komutları STM32'ye istek olarak iletir. İnternet, Firebase veya iletişim kartı arızasında kuvöz ve HMI normal çalışmaya devam eder.

## Önerilen prototip donanımı

| Parça | Seçim | Adet | Yaklaşık fiyat | Gerekçe |
|---|---|---:|---:|---|
| Ana kontrolcü | Mevcut STM32F407VE geliştirme kartı | 1 | Mevcut | Sensör, röle, alarm ve emniyet kontrolü |
| Operatör paneli | Mevcut BMBC BM5010NN, 10,1 inç 1024×600 | 1 | Mevcut | 4 telli rezistif dokunmatik, COM2/COM3 RS485, IP65 ön panel |
| Haberleşme | İzole 3,3 V RS485 alıcı-verici modülü, TVS, 120 ohm sonlandırma ve kilitli soket | 1 set | 300–700 TL | Röle ve ısıtıcı kaynaklı elektriksel gürültüye dayanıklı bağlantı |
| Bulut iletişim kartı | Opsiyonel ESP32-C3 tabanlı tak-çıkar ağ kartı; Wi-Fi veya Ethernet/4G varyantı | 0/1 | Varyanta göre hesaplanacak | HTTPS ile Firebase; kontrol yetkisi yok, ağ kesilse de cihaz çalışır |
| Ana sıcaklık/nem | Orijinal Sensirion SHT31 modülü | 2 | 350–600 TL/adet | I²C, tipik ±0,2 °C ve ±2 %RH; iki sensörle sapma/arızayı algılama |
| Bağımsız sıcaklık gözetimi | Kablolu DS18B20, mümkünse orijinal | 1 | 150–300 TL | Isıtıcı bölgesinde ayrı aşırı sıcaklık kontrolü |
| Oksijen | Mevcut DFRobot SEN0322 | 1 | Mevcut / opsiyonel | 0–25 %Vol, I²C; mevcut yazılım mantığına uyumlu |
| CO₂ | Mevcut SCD30/SCD41 | 1 | Mevcut / opsiyonel | Havalandırma ölçümü; ilk STM32 sürümü için zorunlu değil |
| Çıkış sürücüsü | ULN2803A sürücü modülü veya ULN2803A'lı özel ara kart | 1 | 100–250 TL | STM32 GPIO'larını röle girişlerinden ayırır |
| Röle | 8 kanal, 5 V, optokuplörlü, JD-VCC ayrılabilir röle kartı | 1 | 250–500 TL | Mevcut sekiz yükü sürer; kontrol ve bobin beslemesi ayrılabilir |
| Ana kontrol güç kaynağı | 24 V DIN ray güç kaynağı, en az 30 W | 1 | Teklif alınacak | BM5010NN 18–30 VDC ve 10 W; çevre birimleri için akım payı |
| Düşük gerilim dönüştürücü | İzole 24 V → 5 V DC/DC, en az 15 W | 1 | Teklif alınacak | STM32 ve 5 V röle bobinlerini HMI beslemesinden ayırır |
| Emniyet termostatı | Manuel resetli mekanik termostat, uygun sıcaklık aralığı | 1 | 300–700 TL | Yazılım ve ESP'den bağımsız olarak ısıtıcı enerjisini keser |
| Alarm | 5 V aktif buzzer + kırmızı LED | 1 | 50–100 TL | Sensör/ısı/ağ arızasında yerel uyarı |
| Montaj | DIN kutu, sigorta, klemens, kablo rakoru, PCB/protoboard | 1 set | 600–1.200 TL | Temas, izolasyon ve servis güvenliği |

HMI ve STM32 mevcut olduğundan oksijen/CO₂ sensörleri hariç ilk prototip toplamı yaklaşık **3.000–5.500 TL** olacaktır. Fiyatlar satın alma anında tekrar kontrol edilmelidir.

## Neden bu parçalar?

- Mevcut STM32F407 kartı ve sulama projesindeki kontrol altyapısı yeniden kullanılabilir.
- BM5010NN ayrı bir HMI olduğundan grafik yükü ana kontrol yazılımına girmez.
- HMI veya RS485 arızalansa bile STM32 kontrolü güvenli biçimde sürdürür.
- BM5010NN; çift çekirdekli 1 GHz Cortex-A7, 128 MB Flash/RAM ve 1024×600 çözünürlükle kuvöz arayüzü için geniş kapasite sunar.
- Firebase servis hesabı anahtarı cihaza gömülmez; iletişim kartı cihaz bazlı Firebase kimliği ve dar kapsamlı güvenlik kurallarıyla çalışır.
- Android tablet + kablolu Ethernet uygulanabilir; ancak tablet, sürekli şarj, adaptör/hub, Android güncellemeleri ve kiosk ayarları sahadaki destek yükünü artırır.
- DHT11/DHT22 ana kontrol sensörü yapılmaz. SHT31 daha kararlı ve hassastır.
- Röle kartı STM32 GPIO'suna doğrudan bağlanmaz. ULN2803A ara sürücüsü kullanılır.
- Katı hâl rölesi her kanal için uygun değildir; DC yük, AC yük ve yük akımı görülmeden tek tip SSR seçilmez.
- Tek sensöre güvenilmez. İki SHT31 arasındaki fark sınırı aşarsa ısıtma güvenli duruma geçer.

## İlk prototip bağlantı planı

Kesin GPIO listesi kart revizyonu görüldükten sonra sabitlenecektir. Şimdilik işlevler:

- I²C: iki SHT31 (adresler 0x44 ve 0x45), oksijen ve/veya CO₂ sensörü; adres çakışması doğrulanacak
- 1-Wire: DS18B20
- 8 dijital çıkış: B1–B8, ULN2803A üzerinden röle kartına
- 1 dijital çıkış: buzzer/alarm
- 1 dijital giriş: manuel reset/acil durdurma geri bildirimi
- SWD: üretim, hata ayıklama ve kurtarma bağlantısı
- USB/UART bootloader: kontrollü saha güncellemesi ve servis kayıtları
- İzole RS485: BM5010NN HMI; Modbus RTU, CRC ve bağlantı zaman aşımı
- HMI portu: COM2, 2 telli RS485; konektör pin dizilimi ayrı bağlantı dokümanından veya ölçümle doğrulanacak

## Zorunlu emniyet kuralları

1. Açılışta bütün yükler kapalı kalır; pinler ancak sistem testi tamamlanınca etkinleşir.
2. Sensör verisi geçersiz veya eskiyse ısıtıcı, IR ısıtıcı, nem ve ozon kapanır; fan güvenli moda geçer.
3. Isıtıcı beslemesi yazılımdan bağımsız manuel-reset termostattan geçirilir.
4. Watchdog etkin olur; kilitlenmede röleler güvenli kapalı duruma döner.
5. Ozon çıkışı donanımsal veya yazılımsal kilitleme ile hayvan varken çalıştırılmaz.
6. Şebeke gerilimi tarafı ile düşük gerilim tarafı ayrı bölmelerde tutulur; uygun sigorta, topraklama ve kablo kesiti kullanılır.
7. Prototip, veteriner kullanımına alınmadan önce hata senaryoları ve uzun süreli sıcaklık testlerinden geçirilir. Bu taslak tek başına medikal cihaz sertifikasyonu sağlamaz.
8. HMI/RS485 bağlantısı kesilse dahi STM32 son doğrulanmış ayarlarla kontrolü sürdürür; yerel alarm üretir.
9. Bulut komutları doğrudan röle sürmez. STM32 komut kimliği, zaman aşımı, tekrar ve güvenlik kilitlerini doğruladıktan sonra uygular; ozon ve ısıtma yerel emniyet kurallarını hiçbir zaman aşamaz.

## Yazılım başlangıç sırası

1. Sulama projesindeki STM32F407 tabanını ayırarak kuvöz projesini başlatma; pin güvenli başlatma ve watchdog
2. SHT31 + DS18B20 sürücüleri, sensör doğrulama ve simülasyon testleri
3. Sekiz röle için güvenli durum makinesi
4. Sıcaklık/nem kontrolü ve bağımsız limitler
5. BMBC HMI Editor ile BM5010NN kuvöz arayüzü ve Modbus RTU register haritası
6. Oksijen/CO₂ ve ozon kilitlemeleri
7. USB/SWD servis güncellemesi, olay kaydı ve saha testleri
8. Opsiyonel iletişim kartı, çevrimdışı kuyruk, Firebase kimlik doğrulama ve komut onay akışı

## Satın almadan önce doğrulanacaklar

- Mevcut sekiz yükün AC/DC gerilimi, sürekli akımı ve ilk kalkış akımı
- Mevcut oksijen ve CO₂ sensörlerinin tam model/revizyonu
- STM32F407VE kartının tam model/revizyonu ve kullanılabilir UART/I²C pinleri
- BM5010NN doğrulanan değerler: 1024×600, 18–30 VDC, 10 W, COM1 RS232, COM2 2W/4W RS485, COM3 2W RS485
- BM5010NN seri port konektörünün pin dizilimi; ürün föyünde belirtilmediği için kablo yapılmadan önce doğrulanmalı
- SHT31 modüllerinin adres seçim padi ve Sensirion sensörü içermesi
- Röle kartında JD-VCC ayrımı ve aktif seviye
- Mekanik termostatın kuvöz çalışma aralığı ve kontak akım değeri
