# Kuvoz 3.0 Vetmarketi Uzerinden Dusuk Riskli Sirketlesme Yol Haritasi

Tarih: 10 Mayis 2026

Bu belge, Kuvoz 3.0 konseptinin sifirdan yeni bir startup gibi degil, mevcut ticari yapisi olan Vetmarketi uzerinden daha dusuk riskle urunlesmesi icin revize edilmistir.

Yeni ana varsayimlar:

- Vetmarketi halihazirda ticari olarak vardir.
- Vetmarketi, Kuvoz v1 ile 2016 yilindan beri pazardadir.
- Kuvoz v1 yaklasik 100 firmaya/klinige ulasmistir.
- Bilinen musteri listesi Google Sheets uzerinde tutulmaktadir: https://docs.google.com/spreadsheets/d/13dL0bOJnElXzDXxAhKCr8325xhlxlS4vPOfgxDnNI1s/edit?usp=sharing
- Bu oturumda Google Sheet dogrudan okunamadi; Google oturumu/erisim izni istedi. Musteri isimleri KVKK ve ticari gizlilik nedeniyle bu repo dokumanina kopyalanmamalidir.

## 1. Revize Ana Strateji

Onceki plan, Kuvoz'u yeni bir teknoloji sirketi/startup olarak kurmaya odaklaniyordu. Yeni ve daha dusuk riskli plan:

> Kuvoz 3.0, ilk 12 ay boyunca Vetmarketi icinde yeni nesil akilli kuvoz urun hatti olarak dogrulanmali; ayri sirket, Teknopark subesi veya spin-off yapisi ancak satis, pilot ve yatirim ihtiyaci netlestikten sonra kurulmalidir.

Bu yaklasim uc temel riski azaltir:

- Sirket kurma ve operasyon riski
- Ilk musteri bulma riski
- Pazar guveni ve marka bilinirligi riski

Vetmarketi'nin mevcut avantaji:

- 2016'dan beri kuvoz urunu satmis olmasi
- Yaklasik 100 bilinen musteri temasi
- Veteriner ekipman pazarinda mevcut ticari guven
- E-ticaret, faturalama, satis ve servis altyapisi
- Mevcut Kuvoz v1 kullanicilarindan dogrudan geri bildirim alabilme imkani

Bu nedenle Kuvoz 3.0 icin ilk hedef yeni sirket kurmak degil, mevcut musteri tabanindan baslayarak:

1. V1 kullanicilarini yeniden aktive etmek
2. V1 icin upgrade/deger artisi sunmak
3. Kuvoz 3.0 MVP'yi gercek kliniklerde dogrulamak
4. Pesin siparis/depozito ile nakit riskini azaltmak
5. Ayri sirket/Teknopark kararini satis verisiyle almak

## 2. Onerilen Yapi

### 2.1 Ilk 12 Ay Icin Onerilen Model

| Baslik | Oneri |
|---|---|
| Ticari yapi | Vetmarketi mevcut sirketi uzerinden devam |
| Urun markasi | Vetmarketi Kuvoz 3.0 veya Kuvoz 3.0 Smart ICU |
| Ilk ticari hedef | Mevcut Kuvoz v1 musteri tabanina upgrade, servis ve yenileme satisi |
| Yeni sirket | Hemen kurulmamalidir; 12 ay sonu karar noktasi olarak tutulmalidir |
| Teknopark | Hemen zorunlu degil; Vetmarketi Ar-Ge projesi veya ayri spin-off secenegi 6-12 ayda degerlendirilmeli |
| Uretim | Siparis/depozito bazli, dusuk stokla |
| Kanal | Vetmarketi.com + mevcut musteri listesi + klinik demo |
| Finansman | Vetmarketi nakdi + pesin siparis + pilot odemesi + uygun hibe/kredi |

### 2.2 12 Ay Sonrasi Opsiyonlar

| Opsiyon | Ne Zaman Mantikli? | Avantaj | Risk |
|---|---|---|---|
| Vetmarketi icinde urun hatti | Satislar organik buyuyorsa | En dusuk operasyon riski | Ar-Ge tesvikleri sinirli kalabilir |
| Vetmarketi Teknopark Ar-Ge projesi/subesi | Yazilim/AI Ar-Ge'si belirginlesirse | Vergi ve Ar-Ge destegi | Ayrimli muhasebe ve proje takibi gerekir |
| Kuvoz Teknoloji A.S. spin-off | Yatirim, ihracat veya SaaS buyumesi gerekirse | Yatirim ve IP icin temiz yapi | Yeni sirket operasyon riski |
| Lisans modeli | Dis pazarda uretici/distributor bulunursa | Sermaye ihtiyaci dusuk | Marka ve kalite kontrol riski |

Net tavsiye:

> Ilk 12 ay Vetmarketi icinden ilerle. 12. ayda satis, pilot ve nakit verisine gore Teknopark subesi mi, ayri Kuvoz Teknoloji A.S. mi, yoksa Vetmarketi urun hatti mi devam edecek karar ver.

## 3. Musteri Tabani Stratejisi

Vetmarketi'nin 2016'dan beri Kuvoz v1 ile yaklasik 100 firmaya ulasmis olmasi, Kuvoz 3.0 icin en buyuk risk azalticidir. Bu liste yeni musteri aramak yerine ilk dogrulama, satis ve referans motoru olarak kullanilmalidir.

### 3.1 CRM Temizligi

Google Sheets musteri listesi once CRM formatina cevrilmeli. Musteri detaylari repo icinde saklanmamalidir.

Her kayit icin minimum alanlar:

- Klinik/firma adi
- Il/ilce
- Satin alma yili
- Satin alinan urun versiyonu
- Cihaz halen aktif mi?
- Servis gecmisi
- Memnuniyet durumu
- Yetkili kisi
- Telefon/e-posta
- Instagram/web sitesi
- Potansiyel segment
- Son gorusme tarihi
- Sonraki aksiyon

### 3.2 Segmentasyon

| Segment | Tanim | Aksiyon |
|---|---|---|
| A - Aktif ve memnun V1 kullanicisi | Cihazi kullaniyor, marka algisi olumlu | Ilk referans ve upgrade adayi |
| B - Aktif ama servis ihtiyaci olan | Cihaz var ama bakim/sorun yasamis | Once servis/guven onarimi, sonra upgrade |
| C - Kullanimi azalmis/dormant | Cihaz alinmis ama aktif kullanim belirsiz | Yeniden aktivasyon, uygun fiyatli refresh paketi |
| D - Buyuk klinik/hastane | Birden fazla cihaz veya yuksek hasta akisi olabilir | Kuvoz 3.0 Smart ICU pilotu |
| E - Negatif deneyimli | Sorun yasamis veya memnun degil | Satis degil, once dinleme ve telafi |

### 3.3 Ilk 100 Musteri Icin Hedef Funnel

| Adim | Hedef |
|---|---:|
| Listedeki kayitlari temizleme | 100 kayit |
| Ulasilabilen musteri | 60-70 |
| Kisa memnuniyet/servis gorusmesi | 40-50 |
| Kuvoz 3.0 demo ilgisi | 20-30 |
| Pilot/upgrade teklifi | 10-15 |
| Ilk odemeli pilot veya upgrade | 5-8 |
| Referans video/yorum | 3-5 |

Bu hedefler, sifirdan startup'a gore cok daha dusuk musteri edinme maliyeti yaratir.

## 4. Urun Stratejisi

### 4.1 Urun Siralamasi

Ilk urun siralamasi su sekilde olmali:

1. Kuvoz v1 Servis ve Refresh Paketi
2. Kuvoz v1 -> Kuvoz 3.0 Upgrade Kit
3. Kuvoz 3.0 Smart Retrofit Paket
4. Kuvoz 3.0 Smart ICU Tam Cihaz
5. Kuvoz Cloud / Klinik Paneli

Bu siralama, hem mevcut musteri tabanina deger sunar hem de tam cihaz uretim riskini geciktirir.

### 4.2 Kuvoz v1 Servis ve Refresh Paketi

Amac:

- Eski musterilerle yeniden temas kurmak
- Cihazlarin gercek saha durumunu gormek
- Guven tazelemek
- Upgrade satisina zemin hazirlamak

Icerik:

- Genel cihaz kontrolu
- Role, fan, isitici, nem ve guc kontrolu
- Temizlik/sterilizasyon kontrol listesi
- Sensor kalibrasyon kontrolu
- Yazilim/arayuz durum tespiti
- Upgrade uygunluk raporu

Ticari kullanim:

- Ilk 20 musteri icin kampanyali/indirimli yapilabilir.
- Servis ziyareti sonunda Kuvoz 3.0 upgrade teklifi verilir.

### 4.3 Kuvoz 3.0 Upgrade Kit

Amac:

- V1 cihazlari yeni yazilim, sensor, log, uzaktan izleme ve alarm sistemine tasimak

Icerik:

- Raspberry Pi tabanli kontrol unitesi
- Dokunmatik veya mevcut ekrana uyumlu web panel
- Sicaklik, nem, CO2 ve opsiyonel O2 sensoru
- Kamera/canli izleme altyapisi
- Role kontrol modulu
- UV, ozon, nebulizator, fan ve isitici kontrolu
- Sensor kaydi ve grafikler
- Alarm/uyari sistemi
- Uzaktan destek altyapisi

Oncelik:

- En az mekanik degisiklikle uygulanabilir versiyon olmalidir.
- Montaj suresi 2-4 saat hedeflenmelidir.
- Moduler servis parcasi mantigiyla tasarlanmalidir.

### 4.4 Kuvoz 3.0 Smart ICU Tam Cihaz

Tam cihaz, upgrade kit dogrulanmadan ana urun yapilmamalidir.

Cikis kriterleri:

- En az 5 odemeli upgrade/pilot
- En az 3 referans klinik
- En az 60 gun saha stabilitesi
- Tekrarlanabilir montaj/kontrol listesi
- Net BOM ve brut marj hesabi
- Servis ve garanti proseduru

### 4.5 Kuvoz Cloud: Offline-first + Cloud-assisted

Kuvoz Cloud ilk fazda cihazin karar mekanizmasi olmamalidir. Oncelik, her Kuvoz 3.0 cihazinin internet olmadan da guvenli ve bagimsiz calismasidir.

Onerilen mimari:

> Cihaz klinik icinde offline-first calisir; Cloud ise izleme, kayit, raporlama, bildirim ve Vetmarketi servis operasyonu icin destek katmani olur.

Bu yaklasim su nedenlerle onemlidir:

- Klinik ortamdaki guvenlik algisini guclendirir.
- Internet kesintisinde isitma, nem, oksijen, role kontrolu, alarm ve guvenlik kilitleri devam eder.
- Hekime "cihaz internete bagli olmazsa calismaz" riski yaratmaz.
- Cloud gelir modeli daha sonra abonelik ve servis paketi olarak eklenebilir.
- Vetmarketi servis ekibi cihaz sagligini ve bakim gecmisini uzaktan takip edebilir.

Cloud oncelik sirasi:

| Donem | Oncelik | Satis Vaadi |
|---|---|---|
| 0-6 ay | Bagimsiz cihaz | Internet olmasa da calisir |
| 6-12 ay | Opsiyonel Kuvoz Cloud | Hastayi ve cihazi uzaktan izlersiniz |
| 12+ ay | Merkezi klinik/servis paneli | Tum kuvozleri tek ekrandan yonetirsiniz |

Ilk Cloud surumunde onerilen fonksiyonlar:

- Sensor trendleri
- Alarm gecmisi
- Bakim kayitlari
- Cihaz sagligi
- Servis loglari
- Klinik disindan izleme
- Raporlama
- Bildirimler

Ilk Cloud surumunde sinirlanmasi gereken fonksiyonlar:

- Uzaktan isitici ac/kapat
- Uzaktan role kontrolu
- Uzaktan UV/ozon baslatma
- Klinik icinde yerel onay olmadan kritik ayar degisikligi

Kritik kontrol fonksiyonlari ileride acilacaksa, mutlaka:

- Yetkilendirme
- Islem logu
- Cift onay
- Lokal cihaz uzerinde gorunur uyari
- Guvenlik kilidi
- Geri alma/manuel override

kosullariyla acilmalidir.

## 5. Fiyatlama ve Nakit Riskini Azaltma

### 5.1 Onerilen Paketler

| Paket | Hedef | Tahmini Fiyat |
|---|---|---:|
| V1 Kontrol / Servis Tespiti | Eski musteri reaktivasyonu | 3.000 - 7.500 TL |
| V1 Refresh Paketi | Bakim + temel parca yenileme | 10.000 - 25.000 TL |
| Upgrade Basic | Sensor + kontrol + lokal panel | 35.000 - 50.000 TL |
| Upgrade Smart | Kamera + uzaktan erisim + log + alarm | 55.000 - 80.000 TL |
| Upgrade AI | AI uyari + rapor + klinik panel | 80.000 - 110.000 TL |
| Kuvoz 3.0 Smart ICU | Tam cihaz | 135.000 - 180.000 TL |

Fiyatlar, saha maliyeti ve Vetmarketi'nin mevcut fiyat konumu netlestikce revize edilmelidir.

### 5.2 Pesin Siparis Modeli

Stok riski icin:

- Upgrade kitte %40-50 on odeme
- Tam cihazda %50 on odeme
- Kalan odeme kurulumda
- Pilot kliniklerde indirim karsiligi referans/video/geri bildirim taahhudu
- Ucretsiz pilot yerine "indirimli odemeli pilot" modeli

Ucretsiz pilot sayisi cok sinirli tutulmalidir. Ucretsiz urun, klinikte ciddiyeti ve geri bildirim kalitesini dusurebilir.

## 6. Finansman Ihtiyaci - Revize

Vetmarketi mevcut ticari yapiyi, marka guvenini, faturalama altyapisini ve musteri listesini sagladigi icin finansman ihtiyaci onceki plana gore belirgin sekilde azalir.

### 6.1 Ilk 90 Gun: 750 Bin - 1,5 Milyon TL

Hedef:

- CRM temizligi
- 2-3 upgrade kit prototipi
- V1 saha incelemeleri
- Demo/video/dokuman
- Ilk odemeli pilot teklifleri

| Kalem | Tahmini Butce |
|---|---:|
| Prototip parcalari ve sensorler | 250 bin - 500 bin TL |
| Yazilim ve arayuz sertlestirme | 250 bin - 500 bin TL |
| Saha servis/demolar | 100 bin - 250 bin TL |
| Video, datasheet, urun sayfasi | 75 bin - 200 bin TL |
| Hukuk/KVKK/sozlesme taslaklari | 75 bin - 150 bin TL |

### 6.2 Ilk 6 Ay: 1,8 - 3,5 Milyon TL

Hedef:

- 5-8 odemeli pilot/upgrade
- 10-15 teklif
- 3 referans klinik
- Teknik servis ve montaj standardi

| Kalem | Tahmini Butce |
|---|---:|
| 5-8 pilot/upgrade kit uretimi | 700 bin - 1,4 milyon TL |
| Yazilim, log, uzaktan destek, alarm gelistirme | 500 bin - 1 milyon TL |
| Saha kurulum ve servis operasyonu | 250 bin - 500 bin TL |
| Test, guvenlik ve belgelendirme on calisma | 200 bin - 400 bin TL |
| Pazarlama, referans video, Vetmarketi sayfasi | 150 bin - 250 bin TL |

### 6.3 Ilk 12 Ay: 3,5 - 6,5 Milyon TL

Hedef:

- 15-30 upgrade veya tam cihaz satisi
- Tekrarlanabilir montaj ve kalite kontrol
- Vetmarketi urun hattinin netlesmesi
- Teknopark/ayri sirket kararinin verilmesi

Bu butce, satis gelirleri ve on odemelerle kismen kendi kendini finanse edebilir.

### 6.4 12 Ay Sonrasi Buyume: 8 - 15 Milyon TL

Bu kaynak ancak su kosullardan sonra dusunulmelidir:

- Urun saha stabilitesini kanitladiysa
- 15+ odemeli musteri varsa
- Tekrarlanabilir uretim maliyeti biliniyorsa
- Servis yukumlulugu yonetilebiliyorsa
- Ihracat veya tam cihaz seri uretimi icin net talep varsa

## 7. Finansman Kaynaklari - Revize

### 7.1 Birinci Kaynak: Vetmarketi Operasyonel Nakit ve On Siparis

Bu planda ana finansman kaynagi yatirimci degil, pazar dogrulamasi ve on siparis olmalidir.

Oncelik sirasi:

1. Vetmarketi ic kaynaklari
2. V1 musterilerinden servis/refresh gelirleri
3. Upgrade on odemeleri
4. Pilot klinik odemeleri
5. KOSGEB/TUBITAK destekleri
6. Ancak gerekirse melek/stratejik yatirim

### 7.2 KOSGEB

KOSGEB 2026 Girisimci Destek Programi duyurusunda is gelistirme destegi kapsaminda 1,5 milyon TL'ye kadar, %80 oraninda geri odemeli destek; kredi finansman destegi kapsaminda 1 milyon TL'ye kadar isletme sermayesi destegi ve finansman maliyetinin %50'sinin KOSGEB tarafindan karsilanmasi belirtilmistir.

Vetmarketi mevcut sirket oldugu icin uygunluk mutlaka mali musavir ve KOSGEB uzmaniyla kontrol edilmelidir. Yeni girisimci destekleri yerine KOBI, dijital donusum, kapasite veya Ar-Ge odakli programlar daha uygun olabilir.

Kaynak: https://www.kosgeb.gov.tr/site/tr/genel/destekdetay/9335/girisimci-destek-programi-2026-yili-1-donem-basvurulari-basladi

### 7.3 TUBITAK 1707 Siparis Ar-Ge

Vetmarketi modeli icin TUBITAK 1707, BiGG'e gore daha mantikli olabilir. Cunku 1707, musterisi hazir yenilikci urunlerde siparise dayali Ar-Ge mantigina uygundur.

Olasi kurgu:

- Musteri kurulus: Vetmarketi veya bir klinik zinciri
- Tedarikci kurulus: Ar-Ge'yi yapan KOBI/yapi
- Proje: Kuvoz v1 cihazlarini Kuvoz 3.0 akilli izleme ve erken uyari platformuna donusturen kontrol sistemi

Bu model, musteri gereksinimini ve ticarilesme potansiyelini basvuruya guclu sekilde tasir.

Kaynak: https://tubitak.gov.tr/tr/duyuru/1707-siparis-ar-ge-2026-2-cagrisi-acildi

### 7.4 TUBITAK 1507 / TEYDEB

1507, teknik Ar-Ge tarafi netlesince dusunulmelidir.

Olasi proje basliklari:

- Veteriner ICU cihazlari icin sensor fuzyonlu erken uyari algoritmasi
- Ozon/UV guvenlik kilidi ve akilli sterilizasyon kontrolu
- Klinik ortama uygun offline-first uzaktan izleme mimarisi
- Hasta baglamina duyarli AI alarm esigi sistemi

Kaynak: https://tubitak.gov.tr/tr/destekler/sanayi/ulusal-destek-programlari/1507-tubitak-kobi-ar-ge-baslangic-destek-programi

### 7.5 TUBITAK BiGG 1812

BiGG, mevcut Vetmarketi modeli icin birincil yol degildir. Daha cok ayri bir Kuvoz Teknoloji A.S. kurulacaksa ve ekip uygun girisimci profilini tasiyorsa degerlendirilmelidir.

2026-1 duyurusunda, Mukemmeliyet Muhru alan girisimlere %3 hisse karsiliginda 1.350.000 TL yatirim ve izleme surecinde 1.350.000 TL'ye kadar devam yatirimi bilgisi yer almaktadir.

Kaynak: https://tubitak.gov.tr/tr/duyuru/1812-yatirim-tabanli-girisimcilik-destek-programi-2026-1-tohum-oncesi-yatirim-cagrisi-basvuruya-acildi

## 8. Teknopark Karari

Teknopark hala avantajlidir; ancak artik ilk gun zorunlu degildir.

### 8.1 Neden Hemen Zorunlu Degil?

- Vetmarketi zaten ticari faaliyet yurutuyor.
- Ilk hedef Ar-Ge tesviki degil, mevcut musteri tabaninda satis dogrulamasidir.
- Teknopark basvurusu ve ayrimli muhasebe operasyonel yuk getirir.
- Cihaz satis gelirinin ne kadarinin Ar-Ge/yazilim kazanci sayilacagi dikkatli ayrilmalidir.

### 8.2 Ne Zaman Mantikli?

Teknopark su kosullarda mantikli hale gelir:

- Kuvoz 3.0 yazilim/AI gelistirmesi tam zamanli ekip gerektiriyorsa
- Klinik paneli/SaaS katmani gelistiriliyorsa
- TUBITAK 1507/1707 projesi yazilacaksa
- Ihracat ve yatirim icin Ar-Ge kimligi guclendirilecekse
- Yazilim lisansi ve donanim satisi muhasebede ayrilabiliyorsa

### 8.3 Onerilen Teknopark Yolu

1. Ilk 0-6 ay: Vetmarketi icinden pazar dogrulama
2. 6-9 ay: Teknopark proje dosyasi hazirligi
3. 9-12 ay: Vetmarketi Ar-Ge projesi veya Kuvoz Teknoloji spin-off karari
4. 12+ ay: Teknopark icinde yazilim/AI/kontrol sistemi gelistirme

Teknopark projesi basligi:

> Veteriner yogun bakim uniteleri icin sensor fuzyonlu, uzaktan izlenebilir ve AI destekli erken uyari kontrol platformu.

## 9. Basari Sansi, Kritik Riskler ve Kanitlama Stratejisi

Kuvoz 3.0 projesinin basari sansi, mevcut strateji ve Turkiye veterinerlik pazar dinamikleri dikkate alindiginda yuksek gorunmektedir. Ancak bu basari, sadece teknik urun kalitesine degil; guven, referans, servis standardi ve dogru vaat diline baglidir.

Ozet degerlendirme:

> Kuvoz 3.0 icin basari sansi %80-85 bandinda kuvvetli; fakat bu oran, ilk 12 ayda ucretli pilot disiplini, referans klinik kaniti, servis standardi ve kontrollu AI/Cloud vaadi saglanirsa gecerlidir.

Bu degerlendirme bir garanti degil, stratejik basari potansiyeli tahminidir. Asagidaki kosullar saglanmazsa basari ihtimali hizla duser.

### 9.1 Neden Basarili Olabilir?

| Avantaj | Aciklama | Stratejik Kullanimi |
|---|---|---|
| Dogru urun konumlandirmasi | Pazar artik sadece sicak kabin degil; takip, kayit, alarm ve uzaktan izleme bekliyor | Kuvoz 3.0 "akilli bakim asistani" olarak anlatilmali |
| Vetmarketi kanali | Vetmarketi ticari olarak var ve Kuvoz v1 ile sahada bilinirlik olusturdu | Ilk satislar mevcut musteri tabanindan baslatilmali |
| V1 musteri tabani | Yaklasik 100 eski musteri ilk dogrulama hunisi olarak kullanilabilir | CRM, servis/refresh ve upgrade kampanyasi birlikte yurutilmeli |
| Upgrade Kit modeli | Tam cihaz stok riski yerine mevcut cihazlari yukselterek odeme niyeti olculur | Ilk 90 gunde 2-3 ucretli pilot, ilk 6 ayda 5-8 upgrade hedeflenmeli |
| Moduler servis | Sensor, role, kontrol paneli ve yazilim katmanlari sahada servis edilebilir | Garanti ve servis maliyeti daha yonetilebilir hale gelir |
| Offline-first mimari | Internet kesilse bile temel cihaz guvenligi devam eder | Klinik guveni ve satin alma karari guclenir |

### 9.2 Basariyi Engelleyebilecek Kritik Riskler

| Risk | Neden Kritik? | Onlem |
|---|---|---|
| AI vaadinin yanlis anlatilmasi | Hekimde "tani koyan cihaz" beklentisi veya tibbi sorumluluk riski yaratabilir | AI sadece erken uyari, trend ve farkindalik katmani olarak konumlanmali |
| Upgrade Kit montaj karmasasi | Farkli V1 kabin durumlari 2-4 saatlik montaj hedefini zorlayabilir | Kurulum on kontrol formu, uygunluk raporu ve standart montaj checklist'i hazirlanmali |
| Doviz ve maliyet baskisi | Raspberry Pi, sensor ve elektronik bilesen maliyeti klinik butcesini zorlayabilir | On odeme, kademeli paket ve servis/abonelik modeli kullanilmali |
| Vetmarketi marka riski | Teknik hata sadece Kuvoz'u degil Vetmarketi guvenini etkiler | Genis lansman yerine sinirli ucretli pilot ve net garanti dokumani ile ilerlenmeli |
| Ucretsiz pilot riski | Ucretsiz urun klinikte ciddiyeti ve geri bildirim kalitesini dusurebilir | Indirimli ama ucretli pilot modeli uygulanmali |
| Cloud guvenlik riski | Uzaktan kritik kontrol yanlis kullanilirsa cihaz guvenligi tartisilir | Cloud ilk fazda okuma agirlikli kalmali; kritik kontrol yerel onay gerektirmeli |

### 9.3 Basari Sansini Artiracak Oneriler

| Oneri | Gerekce | Ilk Aksiyon |
|---|---|---|
| Referans klinik videolari | Veteriner hekimler meslektas deneyimine guvenir | Ilk 3 pilot klinikten kisa video, hekim yorumu ve vaka akisi alinmali |
| Kiralama/lisans modeli | Kucuk-orta kliniklerde ilk satin alma bariyerini azaltir | Upgrade + Kuvoz Cloud aboneligi icin aylik/yillik paket hazirlanmali |
| Sertifikasyon hazirligi | Ihracat ve kurumsal satis icin CE/EMC beklentisi dogabilir | CE/EMC teknik dosya, risk analizi ve test gereksinimleri erken listelenmeli |
| Servis dokumani | Teknik guven ve marka korumasi icin sarttir | Kurulum, ariza, garanti ve uzaktan destek prosedurleri yazilmalidir |
| Net AI dili | Tani/tedavi vaadi hukuki ve etik risk yaratir | Tum pazarlama metinlerinde "karar destek/uyari" dili kullanilmali |

### 9.4 Kuvoz Cloud Icin Net Karar

Kuvoz Cloud icin oncelik merkezi yonetim paneli degil, bagimsiz cihaz guvenligini bozmayan destek katmani olmalidir.

Dogru siralama:

1. 0-6 ay: Bagimsiz cihaz
2. 6-12 ay: Opsiyonel Kuvoz Cloud
3. 12+ ay: Merkezi klinik/servis paneli

Bu nedenle ilk lansman dili:

> Kuvoz 3.0 internet olmasa da calisir; Kuvoz Cloud ise uzaktan izleme, kayit, raporlama, bildirim ve servis takibi icin ek deger sunar.

Klinik icinde satin alma kararini guclendirecek ana mesaj budur. Cloud, cihaz guvenligini degil; klinik operasyonunu ve Vetmarketi servis modelini guclendirmelidir.

### 9.5 Basari Icin 12 Aylik Kanit Esikleri

| Donem | Kanit Esigi |
|---|---|
| 0-30 gun | 100 V1 kayit temizlendi, ilk 30 musteri arandi, 10 pilot adayi belirlendi |
| 1-3 ay | 2-3 ucretli pilot kuruldu, montaj checklist'i ve servis raporu olustu |
| 3-6 ay | 5-8 odemeli pilot/upgrade, 3 referans klinik, ilk referans video/yorum |
| 6-9 ay | 10-15 satis/siparis, servis maliyeti ve kurulum suresi olculebilir hale geldi |
| 9-12 ay | 15-30 satis/siparis, Teknopark/ayri sirket karari icin veri olustu |

Bu esikler tutarsa Kuvoz 3.0, Turkiye pazarinda standart belirleyen yerli akilli hayvan kuvozu oyuncusu olma potansiyeline sahiptir. Esikler tutmazsa buyuk stok, ayri sirket ve yatirim kararlari ertelenmelidir.

## 10. Vetmarketi Icin 0-12 Ay Yol Haritasi

### Faz 0: CRM ve Saha Gercegi (0-30 Gun)

Hedef:

- 100 kisilik V1 musteri tabanini satisa hazir CRM'e cevirmek
- V1 cihazlarin gercek durumunu anlamak
- Ilk 10 pilot/upgrade adayini secmek

Yapilacaklar:

- Google Sheets musteri listesi temizlenecek.
- Musteriler A/B/C/D/E segmentlerine ayrilacak.
- Ilk 30 musteri telefonla aranacak.
- 10 musteri icin kisa memnuniyet ve servis ihtiyaci formu doldurulacak.
- Kuvoz 3.0 demo anlatimi icin 1 sayfalik PDF hazirlanacak.
- V1 refresh ve upgrade teklif sablonlari hazirlanacak.

Cikti:

- Temizlenmis CRM
- Ilk 10 pilot adayi
- V1 servis/refresh teklif sablonu
- Upgrade demo PDF'i

### Faz 1: V1 Refresh ve Ilk Upgrade Pilotlari (1-3 Ay)

Hedef:

- Mevcut musterilerle guven yenilemek
- 2-3 upgrade kit kurmak
- Ucretsiz pilot yerine odemeli pilot disiplini kurmak

Yapilacaklar:

- 10 eski V1 musterisine servis/refresh teklifi verilecek.
- 3 musteriye indirimli upgrade pilotu sunulacak.
- Pilotlar icin geri bildirim ve referans sozlesmesi yapilacak.
- Ozon/UV guvenlik kilidi ve alarm senaryolari saha testine alinacak.
- Montaj suresi, sorunlar ve servis ihtiyaci olculecek.

Cikti:

- 2-3 odemeli pilot
- Ilk saha raporu
- Montaj ve servis kontrol listesi
- Referans video/yorum taslagi

### Faz 2: Vetmarketi Lansman Hazirligi (3-6 Ay)

Hedef:

- Urunu Vetmarketi uzerinde guvenilir sekilde yayinlamak
- 5-8 odemeli upgrade/pilot seviyesine ulasmak

Yapilacaklar:

- Vetmarketi urun sayfasi hazirlanacak.
- "Kuvoz v1 sahiplerine ozel 3.0 upgrade" kampanyasi hazirlanacak.
- Teknik datasheet, SSS, garanti ve servis dokumani yayina hazirlanacak.
- CRM'deki ilk 60 musteriye sirali kampanya yapilacak.
- 3 referans klinik fotograf/video/yorum icin hazirlanacak.

Cikti:

- Vetmarketi urun sayfasi
- 5-8 odemeli pilot/upgrade
- 3 referans klinik
- Fiyat ve paket netligi

### Faz 3: Kontrollu Ticari Satis (6-9 Ay)

Hedef:

- 10-15 upgrade satisi veya imzali siparis
- Tam cihaz icin talep olcup stok riskini azaltmak

Yapilacaklar:

- CRM'in tamamina ikinci temas yapilacak.
- V1 sahiplerine son tarihli upgrade kampanyasi sunulacak.
- Yeni musteri adaylari icin tam cihaz on siparis kampanyasi acilacak.
- Kurulum ve servis icin standart is emri sistemi kurulacak.
- Ariza/geri bildirim kayitlari CRM'e baglanacak.

Cikti:

- 10-15 satis/siparis
- Standart is emri sureci
- Servis ve garanti maliyeti verisi
- Tam cihaz icin net talep sinyali

### Faz 4: Yapilanma Karari (9-12 Ay)

Hedef:

- Vetmarketi icinde mi devam, Teknopark projesi mi, ayri sirket mi karar vermek

Karar kriterleri:

- 15+ odemeli musteri var mi?
- Musteri sikayetleri yonetilebilir mi?
- Servis maliyeti brut marji yemiyor mu?
- Upgrade montaji tekrarlanabilir mi?
- Tam cihaz talebi gercek mi?
- Yazilim/AI icin ayri ekip ihtiyaci dogdu mu?
- Ihracat/distributor ilgisi var mi?

Cikti:

- 2. yil yapilanma karari
- Teknopark veya TUBITAK dosyasi
- Tam cihaz uretim plani
- Ihracat/kanal plani

## 11. KPI Hedefleri

| Donem | KPI |
|---|---|
| 0-30 gun | 100 musterilik liste temizlendi, ilk 30 musteri arandi, 10 pilot adayi secildi |
| 1-3 ay | 2-3 odemeli pilot, 10 servis/refresh teklifi, 1 saha raporu |
| 3-6 ay | 5-8 odemeli pilot/upgrade, 3 referans klinik, Vetmarketi urun sayfasi |
| 6-9 ay | 10-15 satis/siparis, servis sureci standardi, tam cihaz talep verisi |
| 9-12 ay | 15-30 toplam satis/siparis, Teknopark/ayri sirket karari, 2. yil butcesi |

## 12. Hukuk, IP ve Veri

Vetmarketi uzerinden ilerlemek riski azaltir; ancak IP ve veri sahipligi mutlaka netlestirilmelidir.

Yapilacaklar:

- Kuvoz markasi ve logo haklari kimin uzerinde netlestirilecek.
- Kuvoz 3.0 yazilim kodu, elektronik tasarim ve dokumanlar icin sahiplik kaydi tutulacak.
- Disaridan gelistirici/danisman kullanilirse fikri mulkiyet devri sozlesmesi yapilacak.
- Musteri listesi repo dosyalarina kopyalanmayacak.
- CRM erisimi yetkilendirilecek.
- Kamera/uzaktan erisim icin KVKK aydinlatma ve onay metni hazirlanacak.
- Servis uzaktan erisimleri loglanacak.
- Garanti, iade, servis ve yedek parca sorumlulugu yazili hale getirilecek.

## 13. Riskler ve Onlemler

| Risk | Etki | Onlem |
|---|---|---|
| Eski V1 musterilerinde negatif deneyim | Yuksek | Once servis/refresh ve dinleme; direkt satis baskisi yapma |
| Ucretsiz pilotlarin ciddiye alinmamasi | Orta | Indirimli odemeli pilot modeli |
| Stok riski | Yuksek | On odeme ve siparis uzerine uretim |
| Vetmarketi markasinin teknik ariza nedeniyle zarar gormesi | Yuksek | Sinirli pilot, net garanti, guvenlik kilitleri |
| Yazilim/AI vaatlerinin fazla iddiali olmasi | Orta | "Karar destek/uyari" dili; tani/tedavi vaadi yok |
| Musteri verisi ve KVKK | Yuksek | Listeyi repo disinda tut, yetkili erisim ve aydinlatma metni |
| Teknopark muhasebe karmasasi | Orta | Ilk 6 ay ticari dogrulama; sonra ayrimli muhasebe |
| Servis kapasitesi | Yuksek | Moduler parca, uzaktan diagnostik, egitilmis servis checklist |

## 14. Ilk 30 Gun Aksiyon Listesi

- Google Sheets musteri listesini CRM formatina temizle.
- 100 musteriyi A/B/C/D/E segmentlerine ayir.
- Ilk 30 musteri icin arama planini hazirla.
- V1 memnuniyet/servis ihtiyaci mini anketini yaz.
- V1 Refresh Paketi teklif sablonunu hazirla.
- Kuvoz 3.0 Upgrade Kit tek sayfalik tanitim PDF'ini hazirla.
- Ilk 3 pilot icin teknik uygunluk kontrol listesi yaz.
- Upgrade kit BOM ve montaj maliyetini revize et.
- Ozon/UV guvenlik kilidi gereksinimini netlestir.
- Vetmarketi urun sayfasi icin icerik taslagi hazirla.
- KVKK ve uzaktan erisim onay metinlerini taslakla.

## 15. Ilk 90 Gun Aksiyon Listesi

- 60-70 musteriye ulas.
- 10-15 servis/refresh teklifi ver.
- 3 odemeli upgrade pilotu kur.
- Her pilot icin 30 gunluk saha raporu olustur.
- 1-2 referans video/yorum al.
- Vetmarketi'de "Kuvoz v1 sahiplerine ozel 3.0 upgrade" kampanyasini hazirla.
- Standart kurulum, servis ve garanti dokumanlarini tamamla.
- TUBITAK 1707/1507 uygunluk kontrolu icin danisman/mali musavir gorusmesi yap.

## 16. Sonuc ve Net Tavsiye

Bu revizyondan sonra Kuvoz 3.0 icin en dusuk riskli yol sudur:

1. Yeni sirketi hemen kurma.
2. Vetmarketi'nin 2016'dan beri olusan Kuvoz v1 musteri tabanini ilk pazar olarak kullan.
3. Ilk urunu tam cihaz degil, V1 Refresh + Kuvoz 3.0 Upgrade Kit yap.
4. Ucretsiz pilot yerine indirimli odemeli pilot kullan.
5. Stok yerine on odeme ve siparis uzerine uretim modeliyle ilerle.
6. Ilk 6 ayda 5-8 odemeli pilot/upgrade hedefle.
7. Ilk 12 ayda 15-30 satis/siparis hedefle.
8. Kuvoz Cloud'u ilk fazda karar mekanizmasi degil, izleme/kayit/raporlama/servis katmani olarak konumlandir.
9. Teknopark veya ayri Kuvoz Teknoloji A.S. kararini 12. ayda, gercek satis verisiyle ver.

Kuvoz 3.0'in asil avantaji artik sadece teknoloji degil; Vetmarketi'nin 2016'dan beri olusturdugu saha guveni, musteri tabani ve ticari kanaliyla birlikte teknolojiye donusmesidir.

## 17. Kullanilan Kaynaklar

- Kuvoz 3.0 Pazar ve Ihracat Analizi: `docs/KUVOZ_3_0_PAZAR_VE_IHRACAT_ANALIZI.md`
- Vetmarketi Kuvoz v1 musteri listesi: https://docs.google.com/spreadsheets/d/13dL0bOJnElXzDXxAhKCr8325xhlxlS4vPOfgxDnNI1s/edit?usp=sharing
- TUBITAK 1812 BiGG 2026-1 duyurusu: https://tubitak.gov.tr/tr/duyuru/1812-yatirim-tabanli-girisimcilik-destek-programi-2026-1-tohum-oncesi-yatirim-cagrisi-basvuruya-acildi
- TUBITAK 1707 Siparis Ar-Ge 2026-2 duyurusu: https://tubitak.gov.tr/tr/duyuru/1707-siparis-ar-ge-2026-2-cagrisi-acildi
- TUBITAK 1507 KOBI Ar-Ge Baslangic Destek Programi: https://tubitak.gov.tr/tr/destekler/sanayi/ulusal-destek-programlari/1507-tubitak-kobi-ar-ge-baslangic-destek-programi
- KOSGEB Girisimci Destek Programi 2026 duyurusu: https://www.kosgeb.gov.tr/site/tr/genel/destekdetay/9335/girisimci-destek-programi-2026-yili-1-donem-basvurulari-basladi
- 2025 Yili Vergi Harcamalari Listesi, 4691 Teknoloji Gelistirme Bolgeleri Kanunu istisnalari: https://www.sbb.gov.tr/wp-content/uploads/2025/01/4-2025-Yili-Vergi-Harcamalari-Listesi_2025Butcesi.pdf
