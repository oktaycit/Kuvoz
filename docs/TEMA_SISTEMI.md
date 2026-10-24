# Arayüz temaları

Ayarlar → Görünüm → Tema: **Klinik**, **Gece**, **Bakım**.

- Klinik: açık yüzeyler, üstte ölçümler ve solda cihaz kontrolleri.
- Gece: koyu yüzeyler, kamera solda; mobilde kamera kontrollerden önce gelir.
- Bakım: sıcaklık/nem hedefleri ve bakım kontrolleri önce gelir.
- Seçim anında uygulanır. Tarayıcının aynı site adresindeki `localStorage` alanında `kuvoz.theme` anahtarıyla saklanır; aynı adresteki açık sekmeler eşitlenir. Telefon ve kiosk ayrı seçim yapabilir.
- Varsayılan veya geçersiz tercih: Klinik. Depolama engelliyse seçim o sayfada çalışır ve kaydedilemediği bildirilir.
- Görünüm tercihi GPIO, sensör, hasta veya sunucu ayarlarını değiştirmez.

`web/theme.js` sayfanın ilk çiziminden önce tercihi okur; Ayarlar'daki erişilebilir radyo grubunu oluşturur. `web/themes.css` ortak renkleri ve üç panel düzenini içerir. Mevcut sayfa stillerinden sonra yüklenmelidir. Yeni HTML sayfalarına bu iki dosyayı ekleyin. Chart.js grafik metinleri ve ekran klavyesi de ortak paleti kullanır.

23 Ekim 2026 doğrulaması: 19 HTML girişinde ortak dosyalar; üç temada 800×480 panel; 14 ana alt menüde 390×844 Gece görünümü; tercih yenileme ve sayfa geçişi; kapalı donanım kontrollerinin gizliliği; depolama hatası/geçersiz tercih/sekme eşitleme; mevcut 11 panel ve kamera testi. Fiziksel ekranda dokunma ve donanım çıkışları denenmedi.

Kuvozfurkan'da yalnız tema dosyaları ve HTML bağlantıları güncellendi. Diğer yerel değişiklikler taşınmadı. Önceki HTML dosyaları: `~/kuvoz/backups/themes-20261023-215657`. Servis yeniden başlatılmadı. Açık tarayıcı ekranını yenilemek gerekir.

## Bakım temasının referans düzeni

`web/care-layout.js` ve `web/care-layout.css` yalnız Bakım ana panelinde çalışır. Solda üç büyük ölçüm ve kamera/O₂ bilgisi, sağda hedefler ve ekipman durumları, altta İzlem/Hasta/Kayıtlar/Sistem bulunur.

Ekipman durum listesi salt okunurdur. **Kontroller** düğmesi mevcut aç/kapat düğmelerini ve nebülizatör seçeneklerini açar. Kamera bilgi alanı canlı kamera panelini; Sistem ise bütün yönetim menülerini açar. Hedef +/- ve manuel/otomatik düğmeleri mevcut işleyicileri kullanır. Yeni Socket.IO bağlantısı veya donanım komutu tanımlanmadı.

Orijinal düğmeler ve kimlikler taşınır; kopyalanmaz. Başka temaya geçişte yerlerine geri döner. Ekran boyutu değişiminde mod düğmeleri korunur. O₂ sensörü yok/tahmini durumunda bu temanın alt bilgi alanı sayısal tahmini gizler; backend alarm/kontrol politikası değişmez.

Kontroller: 1619×971 referans boyutu, 800×480 kiosk ve 390×844 mobil; üç panelin açılıp kapanması; Klinik/Gece/Bakım arasında sekmelerden geçiş; kimliklerin tekilliği; mevcut 11 panel/kamera testi. Son görüntüler `output/care-reference/` dizininde. Önceki cihaz ana sayfası `~/kuvoz/backups/care-reference-20261023-222401/` altında saklandı. Yalnız yeni iki görünüm dosyası ve ana sayfadaki dosya bağlantıları aktarıldı; servis yeniden başlatılmadı.

## Klinik referans düzeni (24 Ekim 2026)

Klinik tema ilk görsele göre düzenlendi. Üstte sıcaklık/nem/CO₂/O₂, ortada gerçek uyarı durumu, altta mevcut ekipman düğmeleri ve canlı kamera, en altta dört bölüm bulunur. Düğmelerdeki anahtar biçimi gerçek çıkış durumunu yansıtır; mevcut olay işleyicileri korunur. **Hedefler ve süreler** sıcaklık/nem hedeflerini, nebülizatör sürelerini ve opsiyonel hedefleri açar.

`care-layout.js` artık Klinik ve Bakım referanslarının ortak düğüm taşıma/geri yükleme ve diyalog altyapısıdır. `care-layout.css` ortak temel; `clinical-layout.css` yalnız Klinik düzeninin farklarıdır. Gece yerleşimi night-layout.css ile tanımlanır. Tema geçişlerinde aynı düğümler geri yüklenir, yeni soket bağlantısı açılmaz. Cihaz adı mevcut sokette salt okunur `get_settings` yanıtından alınır; kamera görüntüsü takip sonucuna göre gizlenmez, gerçek kare tazeliğiyle değerlendirilir.

Doğrulama: 800×480 Klinik, 390×844 mobil, Klinik→Bakım→Gece→Klinik geçişi, kimlik tekilliği, hedef/kamera paneli, canlı görüntü ve mevcut 11 test. Çıkışlar test amacıyla açılıp kapatılmadı. Kuvozfurkan'da önceki dosyalar `~/kuvoz/backups/clinical-reference-20261024-100758/` altında saklandı. Yalnız üç görünüm dosyası ve ana sayfadaki dosya bağlantıları güncellendi; servis yeniden başlatılmadı. Son görüntüler `output/clinical-reference/` altında.

## Gece referans düzeni (24 Ekim 2026)

Gece teması ikinci görsele göre yenilendi: solda İzlem/Hasta/Kayıtlar/Sistem, üstte büyük ölçümler, ortada kamera, sağda dikey ekipman düğmeleri. Mobilde gezinme alta, cihaz kontrolleri kameranın altına geçer. **Üstteki sürgü simgesi** mevcut hedef/süre/mod ayarlarını açar; kamera büyütme ve Sistem menüsü korunur.

`night-layout.css` Gece yerleşim farklarını içerir. Ortak CSS ve düğüm taşıma kodu üç temayı da kapsar. Aynı kontroller ve olay işleyicileri kullanılır; yeni donanım komutu veya soket bağlantısı eklenmez. Kamera, sensör ve cihaz durumları gerçek veriye bağlıdır. Görseldeki örnek alarm/değerler üretilmez.

800×480: altı ekipman satırı 44 px ve kontrol bölümü 264 px, kaydırmadan sığar. Opsiyonel ek çıkış varsa liste kaydırılabilir. 390×844 mobilde yatay taşma yoktur. Üç tema arasında geçiş, kimlik tekilliği, hedef/Sistem/kamera panelleri, canlı görüntü ve mevcut 11 test doğrulandı. Son görüntüler `output/night-reference/` altında. Cihazdaki önceki dosyalar `~/kuvoz/backups/night-reference-20261024-121052/` dizininde; servis yeniden başlatılmadı.
