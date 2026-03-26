# Ayarlar ve Profil Kilavuzu (Sade Surum)

Bu belge, Ayarlar ve Profil sayfalarini kullanan klinik personeli icin hazirlanmistir.
Teknik altyapi, gelistirici notlari ve sistem ici detaylar bu surume dahil edilmemistir.

## 1. Amac

Ayarlar ve Profil bolumu;

- Cihazin kullanim tercihlerini yonetmek,
- Kurum ve yetkili bilgilerini guncel tutmak,
- Gunluk kullanimda duzenli ve guvenli bir is akisı saglamak

icin kullanilir.

## 2. Ayarlar Sayfasi

Ayarlar sayfasinda, kullaniciya acik olan secenekler cihazin kullanim davranisini belirler.

Bu sayfada yer alan baslica alanlar:

- Sogutma sistemi ac/kapa secenegi
- Fan cikis modu secimi: `relay` veya `pwm`
- DHT, oksijen ve CO2 sensorlerinin aktiflik durumu
- AI modulu ve sensor veri kaydi ayarlari
- Disk Temizle, Sistem Guncelle ve Geri Al islemleri

AI ile ilgili kullanim notlari:

- AI vital gecmisi olusmasi icin hem `AI Modulu` hem de `Sensor Veri Kaydi` acik olmalidir.
- AI grafiklerinde her saniyenin degil, anlamli degisimlerin ve stabil durumda yaklasik 3 dakikalik ozet kayitlarin gorunmesi normaldir.
- `LOW_CONF`, `TOO_MUCH_MOTION` ve benzeri guvenilmez durumlar ayni kararsiz izlem donemi icinde toplu gorunebilir.

Kullanim onerileri:

1. Degisiklik yapmadan once mevcut durumu gozden gecirin.
2. Sadece ihtiyac olan ayarlari degistirin.
3. Kaydetmeden once degerlerin dogru oldugunu kontrol edin.
4. Kayit sonrasi ana ekranda beklenen davranisi dogrulayin.

Not: Donanimi bulunmayan ozellikler cihazda pasif olabilir.
Not: Dinlendirici ses ayarlari ana paneldeki `Ses Ortami` alanindan yonetilir; bu ozellik ayarlar sayfasinda ayrica bulunmaz.

## 3. Profil Sayfasi

Profil sayfasinda kurum ve yetkili kisi bilgileri tutulur.

Genel alanlar:

- Kurum/Firma bilgileri
- Iletisim bilgileri
- Yetkili kisi bilgileri
- Cihaza ait temel tanitim bilgileri (varsa)

Kullanim onerileri:

1. Bilgileri eksiksiz ve guncel tutun.
2. Iletisim alanlarinda kurum tarafindan onayli bilgiler kullanin.
3. Yetkili degisikliginde bilgileri ayni gun guncelleyin.

## 4. Sistem Bakimi ve Disk Temizleme

`Disk Temizle` butonu ayarlar sayfasindaki bakim aracidir.

Bu islem:

- Sistem loglarini temizler
- Sensor loglarini temizler
- AI vital loglarini temizler
- Gecici dosyalari temizler

Onemli notlar:

- Islem geri alinamaz.
- Gecmis log incelemesi ihtiyaci varsa temizlikten once teknik ekip bilgilendirilmelidir.
- Temizlik sonrasi cihaz yeniden veri biriktirmeye normal sekilde devam eder.
- Hayvan Yasam Dongusu davranis kayitlari bu butonun kapsamina dahil degildir.
- AI vital gecmisi normal kullanimda yaklasik 30 gun tutulur; `Disk Temizle` yalnizca bu kayitlari erken temizlemek istediginizde kullanilmalidir.
- Sensor loglari icin `Loglar`, AI gecmisi icin `AI Vital Grafikleri` ekrani kullanilir.

## 5. Kaydetme ve Guncelleme

- `Kaydet`: Yapilan degisiklikleri uygular.
- `Yenile`: Ekrandaki bilgileri tekrar yukler.
- `Temizle`: Form alanlarini bosaltir; yanlislikla kullanilmamasi icin dikkatli olun.

Not: Kritik bilgileri temizlemeden once kurum kayitlarinizda yedegi oldugundan emin olun.

## 6. Guvenli Kullanim

- Ayarlar ve profil degisiklikleri yalnizca yetkili personel tarafindan yapilmalidir.
- Erişim bilgileri ve iletisim verileri izinsiz kisilerle paylasilmamalidir.
- Uzak destek surecinde paylasilan veriler en az kapsamla sinirli tutulmalidir.

## 7. Sik Yapilan Hatalar

- Gereksiz ayar degisikligi yapip takip etmemek
- Eski iletisim bilgileriyle devam etmek
- Kontrol etmeden kaydetmek
- Disk temizligini geri alinabilir sanmak

Bu hatalari azaltmak icin her degisiklik sonrasi kisa bir ekran kontrolu yapin.

## 8. Sorun Durumunda

1. Sayfayi yenileyip bilgilerin guncel halini tekrar kontrol edin.
2. Degisiklik uygulanmadiysa tekrar kaydetmeyi deneyin.
3. Sorun surerse teknik destek kaydi acin.
4. Klinik guvenligi etkileyen durumlarda yerel proseduru onceliklendirin.

## 9. Yasal Not

Profil alanlarina girilen kisisel veriler ilgili mevzuata uygun sekilde islenmelidir.
KVKK kapsamindaki bilgilendirme ve acik riza metni icin:

- `docs/KVKK_AYDINLATMA_VE_ACIK_RIZA_METNI.md`

---

Son guncelleme: 2026-03-26
