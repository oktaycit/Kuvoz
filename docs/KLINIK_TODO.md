# Kuvoz Klinik TODO / Backlog

Bu belge, Kuvoz sisteminin veteriner klinik kullanimina gore gelistirilmesi icin hazirlanmis urun TODO listesidir.
Amac; teknik ozellikleri yalnizca eklemek degil, klinik guvenlik, is akisi ve kullanilabilirligi guclendirmektir.

## 1. Olmazsa Olmaz

- Alarm kapsamını genislet:
  Sicaklik disinda oksijen, CO2, nem, sensor kopmasi, enerji kesintisi, ag kopmasi ve cihaz cikisi arizalari icin merkezi alarm yapisi ekle.
- Alarm gecmisi ekle:
  Hangi alarm ne zaman olustu, kim tarafindan fark edildi, ne zaman susturuldu veya cozuldu bilgisi kaydedilsin.
- Tahmini ve gercek sensor verisini kesin bicimde ayir:
  CO2'den turetilen oksijen verisi klinik kararlarda gercek sensor olcumu gibi gorunmemeli.
- Ozon ve UV icin daha sert guvenlik bariyerleri kur:
  Hasta varligi, kapak/kapi durumu, cift onay, geri sayim ve islem sonrasi zorunlu havalandirma adimlari eklenmeli.
- Sensor veya kontrol kaybi durumunda guvenli moda gec:
  Kritik sensor kaybi, veri tutarsizligi veya kontrol dongusu hatasinda sistem kendini guvenli duruma almali ve bunu acikca bildirmeli.

## 2. Yuksek Oncelik

- Otomatik bakim modunu protokol bazli hale getir:
  Yalnizca tur ve yasa gore degil; post-op, neonatal, solunum destegi, travma, hipotermi riski gibi klinik senaryolari destekle.
- Hasta profilini zenginlestir:
  Kilo, irk, brakisefalik risk, tani, operasyon tarihi, klinik not ve sorumlu hekim alanlari ekle.
- Ana ekrana trend gorunumu ekle:
  Son 30 dakika ve son 6 saat icin sicaklik, nem, CO2 ve oksijen egilimleri mini grafiklerle gosterilsin.
- Uzaktan kritik alarm bildirimi ekle:
  Telefon bildirimi, e-posta veya mesajlasma entegrasyonlari ile kritik alarmlar gecikmeden iletilebilsin.
- Bakim/kalibrasyon hatirlaticilari ekle:
  Sensor kalibrasyonu, filtre degisimi, fan temizligi ve periyodik servis tarihleri takip edilsin.

## 3. Iyi Olur

- Tek dokunus klinik presetler ekle:
  `Yenidogan kedi`, `Yenidogan kopek`, `Post-op kucuk irk`, `Solunum destegi`, `Kus/egzotik` gibi hazir senaryolar sun.
- Manuel ve otomatik mod ayrimini daha netlestir:
  Sistem onerisi ile aktif uygulanan hedefler ayri gosterilsin; hekimin onayladigi hedefler acikca isaretlensin.
- Hasta zaman cizelgesi ekle:
  Ilac uygulamasi, beslenme, tuvalet, tarti, agri gozlemi ve diger mudahaleler zaman ekseninde tutulabilsin.
- Rol bazli kullanim dusun:
  Veteriner hekim, tekniker ve teknik servis icin farkli yetki seviyeleri tanimlanabilsin.
- Vardiya devri ekrani ekle:
  Son durum ozeti, aktif alarmlar ve bekleyen gorevler tek ekranda gorunebilsin.

## 4. Arayuz ve Kullanilabilirlik

- Ana ekranda daha net klinik durum ozeti sun:
  "Hasta stabil", "yakin izlem gerekli", "kritik mudahale gerekli" gibi ust seviye durum rozetleri ekle.
- Hedef degerlere klinik referans bandi ekle:
  Gecerli hedefin yaninda kabul edilebilir aralik ve alarm esikleri de gosterilsin.
- Kritik butonlarda yanlis dokunma korumasi ekle:
  Ozon, UV, sogutma ve isitma gibi cikislarda kritik durumlara gore ek onay mantigi dusun.
- Baglanti durumu daha gorunur olsun:
  Kiosk, ag ve websocket kopmalarinda ekran ustunde belirgin bir uyari gosterilsin.

## 5. Veri ve Izlenebilirlik

- Hasta bazli ortam gecmisi tut:
  Sensor verileri yalnizca sistem logu olarak degil, hasta oturumu ile iliskili tutulabilsin.
- Klinik olay etiketleme ekle:
  "Ilac verildi", "hasta cikarildi", "kuvoz acildi", "temizlik yapildi" gibi olaylar loglara islenebilsin.
- Raporlama ciktilari hazirla:
  Taburculuk, post-op takip veya vaka sunumu icin PDF/CSV ozetleri olusturulabilsin.

## 6. Teknik Donusum Notlari

- Bu backlog once guvenlik ve alarm basliklariyla ele alinmali.
- Klinik karar destegi ozellikleri, gercek sensor verisi ve tahmini veri ayrimi netlestirilmeden buyutulmemeli.
- AI ve analiz modulleri, ana klinik kontrol akisinin yerine gecmemeli; her zaman yardimci katman olarak konumlanmali.

## 7. Onerilen Uygulama Sirasi

1. Alarm altyapisi ve guvenli mod davranislari
2. Ozon/UV guvenlik kilitleri
3. Tahmini vs gercek sensor veri ayrimi
4. Protokol bazli otomatik bakim modu
5. Hasta bazli kayit ve trend ekranlari
6. Uzaktan bildirimler ve raporlama

---

Son guncelleme: 2026-04-22
