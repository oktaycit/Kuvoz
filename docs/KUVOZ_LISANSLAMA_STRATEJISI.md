# Kuvoz Lisanslama Stratejisi

Taslak surum: 2026-05-08

Bu dokuman, Kuvoz cihazinin veteriner kliniklerine VetMarketi kanaliyla sunulmasi icin lisanslama, fiyatlandirma ve operasyon modelini ozetler.

## Temel Yaklasim

Kuvoz lisans modeli klinigin temel bakim guvenligini riske atmamalidir. Cihazin isi, nem, fan, lokal dashboard, alarm ve manuel kontrol gibi temel fonksiyonlari lisans suresi doldu diye kapanmamalidir.

Lisans daha cok su alanlari yonetmelidir:

- AI kamera ve hareket/vital analiz ozellikleri
- Uzaktan izleme ve destek
- Raporlama ve gecmis kayitlar
- Yazilim guncellemeleri
- Teknik destek ve servis hakki
- Coklu cihaz / hastane entegrasyonlari

Bu model klinige "cihaz kilidi" gibi degil, "AI + servis + destek guvencesi" gibi anlatilmalidir.

## VetMarketi Kanali

VetMarketi fatura kesebildigi ve teknik destek saglayabildigi icin ilk pazara cikis icin en dusuk riskli kanal olarak konumlandirilabilir.

VetMarketi'nin rolu:

- Satis ve faturalama
- Musteri/kayit takibi
- Kurulum ve ilk destek organizasyonu
- Lisans yenileme takibi
- Teknik destek ilk temas noktasi
- Kliniklerle guven iliskisi

Kuvoz tarafinin rolu:

- Cihaz tasarimi ve urun recetesi
- Yazilim, AI ve sensor mimarisi
- Lisans kontrol altyapisi
- Teknik dokumantasyon
- Egitim icerigi
- Uretim/kalite standartlari

## Lisans Kontrol Mimarisi

### Cihaz Bazli Lisans

Her cihaz icin benzersiz bir `device_id` olusturulmalidir. Bu kimlik, Raspberry Pi seri numarasi, sistem makine kimligi ve kurulum sirasinda uretilen salt degerinin hashlenmesiyle turetilebilir.

Ornek lisans dosyasi:

```json
{
  "license_id": "KUV-2026-00042",
  "customer": "Klinik Adi",
  "seller": "VetMarketi",
  "device_id": "abc123...",
  "plan": "clinical_ai",
  "features": [
    "ai_camera",
    "remote_monitoring",
    "reports",
    "updates",
    "support"
  ],
  "issued_at": "2026-05-08",
  "expires_at": "2027-05-08",
  "support_until": "2027-05-08"
}
```

### Imzali Lisans Dosyasi

Lisans dosyasi VetMarketi/Kuvoz tarafinda ozel anahtarla imzalanmali, cihazda yalnizca public key bulunmalidir. Musteri lisans dosyasini degistirirse imza dogrulamasi bozulur.

Onerilen teknik yontem:

- Ed25519 imza
- `license.dat` veya `license.json`
- Cihazda public key ile dogrulama
- Private key'in cihaza hic konmamasi

Alternatif olarak JWT/EdDSA kullanilabilir; ancak ilk surum icin imzali JSON dosyasi daha okunabilir ve saha destek acisindan daha kolaydir.

### Online ve Offline Aktivasyon

Veteriner kliniklerinde internet her zaman guvenilir olmayabilir. Bu nedenle iki aktivasyon yolu desteklenmelidir:

- Online aktivasyon: Sistem Ayarlari sayfasindan aktivasyon kodu girilir, cihaz VetMarketi lisans servisinden lisansi ceker.
- Offline aktivasyon: VetMarketi lisans dosyasi uretir, Sistem Ayarlari sayfasindan dosya yuklenir.

### Grace Period

Lisans suresi dolunca cihaz aniden kisitlanmamalidir.

Onerilen surec:

- 0-30 gun: Uyari gosterilir, tum lisansli ozellikler calismaya devam eder.
- 30+ gun: AI, rapor, uzaktan izleme ve guncelleme haklari pasiflesir.
- Temel cihaz kontrolu her durumda calisir.

## Paketler

| Paket | Hedef | Icerik | Onerilen fiyat |
|---|---|---|---:|
| Kuvoz Base | Tum cihazlar | Isitma, nem, fan, lokal dashboard, temel alarm ve manuel kontrol | Cihazla birlikte omur boyu |
| Care Support | Kucuk/orta klinikler | Uzaktan destek, yazilim guncelleme, log kontrolu, servis takibi | 9.900 TL/yil veya 990 TL/ay |
| AI Klinik | Klinik ve poliklinikler | AI kamera, hareket/vital analiz, uyarilar, raporlar, uzaktan izleme | 19.900 TL/yil veya 1.990 TL/ay |
| Hospital / Coklu Cihaz | Poliklinik ve hastaneler | Coklu cihaz, oncelikli destek, ozel kurulum, gelismis rapor | 49.900 TL/yil+ |

Fiyatlar B2B tekliflerde KDV haric konumlandirilabilir. Sahada basitlik icin yillik odeme ana model, aylik fiyat ise karar vermeyi kolaylastiran karsilastirma fiyati olarak sunulmalidir.

## Onerilen Ticari Model

Ilk satis modeli:

- Cihaz satis fiyatina ilk 12 ay AI Klinik lisansi dahil edilir.
- Ikinci yildan itibaren AI Klinik lisansi 19.900 TL/yil olarak yenilenir.
- Yenileme yapilmadiginda cihaz temel fonksiyonlariyla calismaya devam eder.
- AI, rapor, uzaktan izleme ve destek haklari pasiflesir.

Bu model klinigin ilk satin alma kararini kolaylastirir. Klinik cihazi kullandiktan ve faydayi gordukten sonra ikinci yil yenileme daha dogal hale gelir.

## Pilot / Lansman Programi

Ilk 20 klinik icin "Kurucu Klinik Programi" uygulanabilir.

Onerilen teklif:

- Ilk 3 ay AI lisansi ucretsiz
- Sonrasinda 14.900 TL/yil lansman fiyati
- Klinik geri bildirimi alinmasi
- Referans yorumu ve saha fotograf/video izni
- Ariza, kurulum ve kullanim verisinin kayit altina alinmasi

Bu program sirketlesme ve buyuk olcekli uretim kararindan once pazar dogrulamasi saglar.

## Coklu Cihaz Indirimi

Onerilen indirim yapisi:

- 1. cihaz: Tam fiyat
- 2. cihaz: %30 lisans indirimi
- 3+ cihaz: %40 lisans indirimi
- Hayvan hastanesi / zincir klinik: Teklif usulu

## Hangi Ozellikler Kisitlanabilir?

Lisans bitince kisitlanabilecek ozellikler:

- AI kamera analizi
- AI vital tahminleri
- AI uyarilari
- Uzaktan izleme
- Gelismis raporlar
- Yazilim guncellemeleri
- Oncelikli destek

Kisitlanmamasi gereken ozellikler:

- Isitma kontrolu
- Nem kontrolu
- Fan kontrolu
- Manuel role kontrolleri
- Lokal sensor okumasi
- Kritik alarm ve temel guvenlik ekranlari
- Dezenfeksiyon guvenlik kilitleri

## Fiyatlandirma Gerekcesi

Kuvoz, siradan bir veteriner klinik yazilimi degildir. Fiziksel cihaz, sensorler, AI kamera, lokal kiosk, uzaktan destek ve sahada teknik servis gerektirir. Bu nedenle klasik klinik yazilimlarinin ust paketlerine yakin veya uzerinde konumlanabilir.

2026 kosullarinda veteriner yazilimlarinda aylik paketlerin kabaca yuzlerce TL'den birkac bin TL'ye ciktigi gorulmektedir. Kuvoz icin 1.990 TL/ay karsiligi olan 19.900 TL/yil AI Klinik paketi, klinigin yogun bakim/post-op takipten yaratacagi ek gelirle karsilanabilir bir seviyede kalir.

Yillik fiyatlar enflasyon ve kur etkisi nedeniyle her yil guncellenmelidir. Guncelleme icin pratik formul:

```text
Yeni fiyat = onceki fiyat x (1 + yillik enflasyon veya uretim maliyeti artis orani)
```

Ancak mevcut musteriler icin yenileme fiyat artisi daha yumusak uygulanmalidir.

## Uygulama Yol Haritasi

1. Lisans dosyasi formati ve public/private key yapisi belirlenir.
2. Backend'e `LicenseManager` eklenir.
3. Sistem Ayarlari sayfasina lisans durumu ve lisans yukleme alani eklenir.
4. AI ve uzaktan izleme ozellikleri lisans flag'lerine baglanir.
5. VetMarketi icin lisans uretme script'i hazirlanir.
6. Pilot klinikler icin manuel lisans uretimiyle baslanir.
7. Talep arttiginda VetMarketi lisans paneli gelistirilir.

## Risk Notlari

- Lisans mekanizmasi klinik bakimi durduracak sekilde tasarlanmamalidir.
- Uretici, satici, teknik servis ve yazilim saglayici rolleri yazili olarak ayrilmalidir.
- Kullanici sozlesmesi, garanti kosullari ve destek kapsam dokumani hazirlanmalidir.
- Urun guvenligi, CE/uygunluk, elektrik guvenligi ve servis sorumlulugu lisanslamadan bagimsiz olarak ele alinmalidir.

## Kisa Konumlandirma

Kuvoz lisansi, cihazi kilitleyen bir mekanizma degil; veteriner kliniklerine AI destekli yogun bakim takibi, uzaktan destek, raporlama ve yazilim guncelleme guvencesi saglayan yillik servis paketidir.
