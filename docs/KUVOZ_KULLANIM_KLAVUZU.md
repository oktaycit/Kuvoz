# Kuvoz Kullanim Kilavuzu (Sade Surum)

Bu kilavuz, Kuvoz cihazini kullanan veteriner hekim ve klinik personeli icin hazirlanmistir.
Teknik altyapi detaylari bu belgeye bilerek dahil edilmemistir.

## 1. Amac

Kuvoz; hasta hayvanlarin sicaklik, nem ve hava kosullarini kontrollu tutmak,
gozlem surecini kolaylastirmak ve guvenli bir kullanim deneyimi saglamak icin kullanilir.

## 2. Bu Rehber Kimler Icin

- Veteriner hekim
- Veteriner teknikeri / klinik personeli
- Cihazdan sorumlu operasyon kullanicisi

## 3. Ilk Kullanim

1. Cihazin enerji baglantisinin guvenli oldugunu kontrol edin.
2. Ana ekranda sensor kartlarinin veri gosterdigini dogrulayin.
3. Cihaz kontrol butonlarini kisa sureli test edin.
4. Kullanici profili ve iletisim alanlarini doldurun.

Not: Ilk kurulum ve teknik altyapi ayarlari yetkili personel tarafindan yapilmalidir.

## 4. Gunluk Kullanim Akisi

1. Hastayi uygun protokole gore kuvoza alin.
2. Hedef degerleri klinik ihtiyaca gore ayarlayin.
3. Sensor verilerini duzenli takip edin.
4. Gerekli oldugunda ilgili kontrol cikislarini acip kapatin.
5. Islem sonunda kayitlari ve genel durumu kontrol edin.

## 5. Ekran Uzerindeki Ana Alanlar

- Sensor Alani: Sicaklik, nem ve diger olcumler
- Kontrol Alani: Cihaz fonksiyon ac/kapa kontrolleri
- Ayarlar: Hedef degerler ve sistem tercihleri
- Profil: Kurum ve yetkili kisi bilgileri
- Veri Yonetimi: Hasta bilgileri ve log ekranlari
- AI Alanlari: AI uyarilari ve AI vital grafik ekranlari
- Ses Ortami: Dinlendirici ses kontrolu ve ses profili secimi
- Hayvan Yasam Dongusu: Yeme-icme, dinlenme, bosaltim gibi davranislari takip eden ozellik
- Yardim: Kullanim ve yasal metinler

## 6. Ayarlar Sayfasinda Neler Var

Ayarlar sayfasi, cihazin gunluk kullanim davranisini belirleyen temel alanlari icerir:

- Sogutma sistemi ac/kapa secenegi
- Fan cikis modu secimi: `relay` veya `pwm`
- DHT, oksijen ve CO2 sensorlerinin aktiflik durumu
- AI modulu ve sensor veri kaydinin acik/kapali kullanimi
- Disk Temizle, Sistem Guncelle ve Geri Al islemleri

Not: Bazi secenekler sadece ilgili donanim mevcutsa aktif gorunur veya kullanilabilir.

## 7. AI Kullanimi

AI ozellikleri, canli izleme ve gecmis trend takibi icin kullanilir.

- AI Modulu acik oldugunda sistem kamera goruntusu, hareket durumu ve AI vital verilerini gosterir.
- `AI Uyarilari` ekraninda canli analiz, hareket durumu ve aktif uyarilar izlenir.
- `AI Vital Grafikleri` ekraninda solunum, guven ve durum gecmisi zaman icinde incelenir.
- AI kapaliyken AI grafikleri yeni veri uretmez; mevcut eski kayitlar yine goruntulenebilir.

Kullanim notlari:

- AI modulu cihaz tarafinda desteklenmiyorsa acilamaz.
- AI acma/kapama tercihi ayarlardan degistirilebilir.
- Kritik kararlar sadece AI ekranina bakilarak verilmemelidir; klinik gozlem onceliklidir.

## 8. Hayvan Yasam Dongusu Takibi

Yeni eklenen ozellik sayesinde hayvanlarin yeme-icme, dinlenme, bosaltim gibi davranislari izlenebilir.

- `Hayvan Yasam Dongusu` ekraninda hayvanin davranislarini manuel olarak kaydedebilirsiniz
- Sistem bu verileri zamanla analiz ederek hayvanin genel saglik durumu hakkinda bilgi saglar
- Davranis verileri SQLite veritabani uzerinde saklanir
- Gelistirilmis raporlama ozellikleri ile hayvanin gelisimini takip edebilirsiniz

## 9. Log Kayitlari ve Gecmis Veri

Kuvoz iki farkli kayit akisi sunar:

- `Loglar` ekrani: Sensor verilerinin gecmis kayitlarini gosterir.
- `AI Vital Grafikleri` ekrani: AI tarafindan uretilen vital kayitlarini gosterir.

Log kayitlariyla ilgili temel davranislar:

- Sensor Veri Kaydi aciksa sistem uygun araliklarda sensor kaydi olusturur.
- AI vital kayitlari icin hem `AI Modulu` hem de `Sensor Veri Kaydi` acik olmalidir.
- `Loglar` ekranindaki `Temizle` butonu sensor loglarini siler.
- `Disk Temizle` butonu sistem loglariyla birlikte sensor ve AI vital loglarini da temizler.
- Log temizleme islemleri geri alinamaz.

## 10. Ses Ortami ve Dinlendirici Ses

Ana paneldeki `Ses Ortami` alani, hastayi rahatlatmaya yonelik dinlendirici ses kontrolunu sunar.

- Ses ac/kapa dugmesi manuel kontrol saglar.
- `Kedi`, `Kopek` ve `Sessiz` olmak uzere uc profil bulunur.
- Sistem, hasta turune gore uygun sesi onerilebilir.
- AI guvenlik nedeniyle gerekli gordugunde dinlendirici sesi gecici olarak engelleyebilir.

Kullanim notlari:

- Sesin baslamasi icin tarayicida ekrana bir kez dokunmaniz gerekebilir.
- `Sessiz` modda ek ses calmayabilir; bu normal davranistir.
- Ses sistemi desteklenmeyen tarayicilarda ozellik pasif kalabilir.

## 11. Sistem Bakimi ve Temizleme

`Disk Temizle` butonu, sistem bakimi icin kullanilir.

- Sistem loglari ve gecici dosyalari temizler
- Sensor loglarini temizler
- AI vital loglarini temizler
- Davranis loglarini temizler
- Islem geri alinamaz

Bu buton, ozellikle servis sonrasi veya cihazdaki kayit birikimini temizlemek istediginizde kullanilmalidir.

## 12. Guvenli Kullanim Kurallari

- Cihaz yalnizca egitimli personel tarafindan kullanilmalidir.
- Kritik alarm veya beklenmedik davranista manuel kontrol onceliklidir.
- Klinik kararlar her zaman veteriner hekim sorumlulugundadir.
- Tibbiy/degerlendirme kararlari tek basina yazilim ciktisina birakilmamalidir.

## 13. Uzak Erisim ve Destek

- Uzak erisim ozelligi yalnizca ihtiyac oldugunda acilmalidir.
- Erisim bilgileri sadece yetkili destek personeliyle paylasilmalidir.
- Islem bittiginde paylasim ve uzaktan erisim kapatilmalidir.

## 14. Sorun Durumunda

1. Once cihazin genel durumunu ve ag baglantisini kontrol edin.
2. Sensor verisi yoksa sayfayi yenileyin ve tekrar kontrol edin.
3. Devam eden sorunlarda teknik servise bilgi verin.
4. Kritik vakalarda klinik guvenlik prosedurunu uygulayin.

## 15. Yasal ve Sorumluluk Notu

- Kuvoz bir destek sistemidir; profesyonel veteriner degerlendirmesinin yerine gecmez.
- Kullanim sorumlulugu, ilgili mevzuat ve klinik prosedurler kapsaminda kullaniciya aittir.
- KVKK ve acik riza metni icin yardim menusundeki ilgili belgeyi kullanin.

## 16. Belge Kapsami

Bu sade surum teknik uygulama ayrintilarini, komutlari ve sistem ic mimarisini icermez.
Teknik dokumanlar yalnizca yetkili teknik ekip icin ayrica yonetilir.

---

Son guncelleme: 2026-03-24