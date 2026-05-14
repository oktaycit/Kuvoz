# Kuvoz 3.0 Temel Özellikler ve Hedef Strateji

Tarih: 10 Mayıs 2026

Bu belge, Kuvoz 3.0 cihazının ne olduğu, hangi probleme odaklandığı, hangi özelliklerle farklılaştığı ve ilk ticarileşme stratejisinin nasıl kurulması gerektiğini netleştirmek için hazırlanmıştır.

## 1. Kısa Tanım

Kuvoz 3.0; veteriner kliniklerinde operasyon sonrası bakım, yenidoğan desteği, hipotermi riski, oksijen desteği ve yakın gözlem gerektiren kedi/köpek hastalar için geliştirilen akıllı recovery ve kontrollü bakım ünitesidir.

Ürün yalnızca bir kabin değildir. Kuvoz 3.0; sensörler, röle kontrollü ekipmanlar, dokunmatik web arayüzü, kayıt sistemi, uzaktan erişim ve AI destekli erken uyarı yaklaşımını bir araya getiren modüler bir veteriner bakım platformudur.

Ana konumlandırma:

> Kuvoz 3.0, kontrollü bakım ortamını ölçen, yöneten, kaydeden ve kliniğe erken uyarı farkındalığı sağlayan akıllı veteriner recovery platformudur.

## 2. Çözdüğü Temel Problem

Veteriner kliniklerinde yoğun bakım veya recovery süreci çoğu zaman şu zorluklarla yürür:

- Hasta ortam koşulları sürekli değişebilir.
- Personel her hastayı kesintisiz izleyemez.
- Sıcaklık, nem, oksijen/CO2 ve ekipman durumu ayrı ayrı takip edilir.
- Gece veya yoğun saatlerde küçük değişimler geç fark edilebilir.
- Eski cihazlarda kayıt, uzaktan erişim ve trend takibi sınırlıdır.

Kuvoz 3.0'ın hedefi, veteriner hekimin klinik kararının yerine geçmek değildir. Hedef; bakım ortamını daha görünür, daha izlenebilir, daha kontrollü ve daha kolay yönetilebilir hale getirmektir.

## 3. Hedef Kullanıcı

Birincil hedef kullanıcılar:

- Cerrahi operasyon yapan küçük ve orta ölçekli veteriner klinikleri
- Kedi/köpek yoğun bakım veya recovery alanı olan klinikler
- Yenidoğan, hipotermi, post-op ve oksijen destekli bakım vakalarını daha düzenli izlemek isteyen klinikler
- Mevcut Kuvoz v1 veya benzer kabin sahibi olup cihazını akıllı hale getirmek isteyen kullanıcılar

İkincil hedef kullanıcılar:

- Büyük veteriner hastaneleri
- Birden fazla şubesi olan klinik grupları
- Distribütörler ve veteriner ekipman satıcıları
- Yurt dışı pazarlarda mevcut kabinleri modernize etmek isteyen servis/entegrasyon ortakları

## 4. Temel Ürün İlkeleri

Kuvoz 3.0 geliştirilirken aşağıdaki ilkeler korunmalıdır:

- **Güvenlik önce gelir:** UV, ozon, aşırı sıcaklık, oksijen düşüşü, sensör hatası ve ekipman arızası senaryoları yazılım ve donanım tarafında güvenli ele alınmalıdır.
- **Klinik kullanımı sade olmalıdır:** 7 inç dokunmatik ekranda ve mobil tarayıcıda yatay taşma olmadan, büyük dokunma alanlarıyla kullanılmalıdır.
- **Veri anlamlı olmalıdır:** Sistem yalnızca sayı göstermemeli; trend, alarm, geçmiş kayıt ve klinik aksiyon ihtiyacını görünür hale getirmelidir.
- **Offline-first çalışmalıdır:** Cihaz klinik içinde internet olmadan temel kontrol görevlerini sürdürebilmeli; uzaktan erişim ek değer olarak çalışmalıdır.
- **Servis edilebilir olmalıdır:** Sensör, röle, fan, ısıtıcı ve kontrol modülü değişimleri sahada hızlı yapılabilecek şekilde modüler düşünülmelidir.
- **Aşırı tıbbi vaatlerden kaçınılmalıdır:** Tanı, tedavi veya klinik karar vaadi verilmemeli; cihaz destekleyici bakım ve karar farkındalığı diliyle anlatılmalıdır.

## 5. Temel Özellikler

### 5.1 Kontrollü Bakım Ortamı

- Sıcaklık takibi ve hedef sıcaklık kontrolü
- Nem takibi ve nemlendirme kontrolü
- CO2 takibi için SCD41 ana sensör stratejisi
- DHT11/DHT22 yedek sıcaklık/nem sensörü desteği
- Opsiyonel oksijen sensörü desteği
- Isıtıcı, IR ısıtıcı, fan, soğutma ve nemlendirme ekipmanlarının otomatik/manuel yönetimi

### 5.2 Ekipman Kontrolü

Kuvoz 3.0, Raspberry Pi tabanlı GPIO/röle yapısı üzerinden aşağıdaki ekipmanları yönetir:

| Kanal | İşlev |
|---|---|
| B1 | Terapötik aydınlatma |
| B2 | Nebulizatör |
| B3 | Nem kontrolü |
| B4 | Isıtma pedi / karbon ısıtıcı |
| B5 | IR ısıtıcı |
| B6 | Havalandırma fanı |
| B7 | UV sterilizasyon |
| B8 | Ozon sterilizasyon |
| B9 | Soğutma veya ek kontrol hattı |

Not: UV ve ozon hasta içerideyken kullanılacak rutin bakım fonksiyonu olarak değil, güvenlik kilitleri ve prosedürlerle sınırlandırılmış dezenfeksiyon/sterilizasyon fonksiyonu olarak ele alınmalıdır.

### 5.3 Web Tabanlı Kontrol Paneli

- Raspberry Pi üzerinde Flask + Socket.IO tabanlı backend
- Gerçek zamanlı WebSocket iletişimi
- Chromium kiosk modunda 7 inç dokunmatik ekran desteği
- Mobil tarayıcılardan erişim
- Büyük dokunma hedefleri, kompakt başlıklar ve tek kolon mobil formlar
- Sensör durumuna göre dinamik arayüz
- Ayar kaydetme/yükleme ve cihaz yeniden başlatma/kapatma kontrolleri

### 5.4 Kayıt, Grafik ve Alarm Altyapısı

- Sensör değerlerinin zaman içinde kaydı
- Geçmiş trendlerin grafikle izlenmesi
- Kritik, uyarı ve bilgi seviyelerinde alarm mantığı
- Isıtıcı açıkken sıcaklığın düşmesi gibi tutarsızlıkların yakalanması
- Ani oksijen düşüşü, aşırı sıcaklık, nem dengesizliği ve sensör okuma hatası gibi olayların görünür hale getirilmesi

### 5.5 AI Destekli Erken Uyarı Katmanı

AI katmanı, Kuvoz 3.0'ın temel farklılaşma alanıdır. Amaç tanı koymak değil, dikkat gerektiren durumları daha erken görünür hale getirmektir.

Öncelikli AI kullanım alanları:

- Kamera üzerinden hareket ve aktivite takibi
- Hareketsizlik veya normal dışı hareket örüntülerinin işaretlenmesi
- Sensör trend analizi
- Hasta türü, yaş, kilo ve profil bilgisine göre bağlamsal alarm eşikleri
- Bakım süreci için özet/rapor üretimi

### 5.6 Uzaktan Erişim ve Destek

- Klinik ağı içinden web arayüzüne erişim
- Tailscale benzeri güvenli uzaktan erişim altyapısı
- Servis ve destek için uzaktan log inceleme
- Yazılım güncelleme ve cihaz sağlık kontrolü altyapısı
- KVKK uyumlu kamera/uzaktan erişim bilgilendirmesi

## 6. Ürün Paketleri

İlk ticarileşme için tek bir büyük ürün yerine paketli yapı önerilir.

| Paket | Hedef | İçerik |
|---|---|---|
| Kuvoz v1 Servis / Refresh | Eski müşteri tabanını yeniden aktive etmek | Bakım, kontrol, sensör/ekipman durumu, upgrade uygunluk raporu |
| Kuvoz 3.0 Upgrade Kit | Mevcut kabinleri akıllı hale getirmek | Kontrol paneli, sensörler, röle entegrasyonu, web arayüzü, log ve alarm |
| Kuvoz 3.0 Smart Upgrade | Daha güçlü klinikler | Kamera, uzaktan erişim, AI uyarı, gelişmiş grafik ve rapor |
| Kuvoz 3.0 Smart ICU | Tam cihaz satışı | Kabin + kontrol sistemi + sensörler + güvenlik + servis paketi |
| Kuvoz Cloud / Klinik Paneli | Çoklu cihaz veya şube yönetimi | Merkezi takip, raporlama, uzaktan destek ve lisanslı yazılım katmanı |

Stratejik öncelik:

> İlk ölçeklenebilir ürün tam kabin değil, mevcut cihazları Kuvoz 3.0 seviyesine taşıyan Upgrade Kit olmalıdır.

## 7. Farklılaşma Noktaları

Kuvoz 3.0 rakiplerden yalnızca donanım listesiyle ayrışmamalıdır. Ana fark yazılım, veri ve servis edilebilirlik tarafında kurulmalıdır.

Öne çıkarılacak farklar:

- Gerçek zamanlı web tabanlı kontrol
- Lokal/offline çalışabilen mimari
- Mobil ve kiosk uyumlu arayüz
- Sensör kaydı, grafik ve alarm geçmişi
- AI destekli hareket/trend farkındalığı
- Uzaktan destek ve güncellenebilir yazılım
- Modüler upgrade kit yaklaşımı
- Vetmarketi'nin mevcut müşteri, satış ve servis güveni

Kullanılabilecek kısa mesaj:

> Sadece kontrollü bakım kabini değil; kayıt tutan, uyaran ve uzaktan izlenebilen akıllı veteriner recovery sistemi.

## 8. Hedef Strateji

### 8.1 İlk 12 Ay Ana Stratejisi

Kuvoz 3.0, ilk aşamada sıfırdan yeni bir startup gibi değil, Vetmarketi'nin mevcut ticari güveni ve Kuvoz v1 müşteri tabanı üzerinden doğrulanmalıdır.

Ana strateji:

1. Mevcut Kuvoz v1 kullanıcılarıyla yeniden temas kur.
2. Servis/refresh paketiyle güven tazele.
3. Upgrade Kit ile düşük riskli ilk satışları yap.
4. Sahada 5-8 ödemeli pilotla ürün stabilitesini kanıtla.
5. Referans klinikler, video, datasheet ve servis prosedürleri hazırlandıktan sonra kontrollü ticari satışa geç.
6. Tam cihaz üretimini, upgrade kit sahada doğrulandıktan sonra büyüt.

### 8.2 Faz Planı

| Dönem | Hedef | Ana Çıktı |
|---|---|---|
| 0-30 gün | CRM temizliği ve saha gerçeği | İlk 10 pilot/upgrade adayı |
| 1-3 ay | V1 refresh ve ilk ödemeli pilotlar | 2-3 kurulu upgrade kit |
| 3-6 ay | Vetmarketi lansman hazırlığı | Ürün sayfası, datasheet, 5-8 pilot/upgrade |
| 6-9 ay | Kontrollü ticari satış | 10-15 satış/sipariş, servis süreci standardı |
| 9-12 ay | Yapılanma kararı | 15-30 toplam satış/sipariş ve 2. yıl planı |

### 8.3 Kanal Stratejisi

Türkiye için birincil kanal:

- Vetmarketi.com
- Mevcut Kuvoz v1 müşteri listesi
- Klinik ziyaretleri ve demo kurulumları
- Referans klinik video/yorumları
- WhatsApp Business ve doğrudan satış takibi

Yurt dışı için öncelik sırası:

1. GCC / Orta Doğu
2. Balkanlar ve Doğu Avrupa
3. AB ve İngiltere
4. ABD/Kanada

Yurt dışı pazarda ilk hamle tam kabinden çok, servis edilebilir upgrade kit ve akıllı kontrol/izleme katmanı üzerinden yapılmalıdır.

## 9. Başarı Ölçütleri

İlk 12 ay için takip edilmesi gereken ana metrikler:

| Alan | Ölçüt |
|---|---|
| Müşteri doğrulama | 100 V1 kaydının CRM'e aktarılması, 40-50 müşteri görüşmesi |
| Pilot | 5-8 ödemeli pilot/upgrade kurulumu |
| Referans | En az 3 referans klinik |
| Ürün stabilitesi | En az 60 gün sahada kritik hatasız çalışma |
| Servis | Standart montaj, bakım ve arıza kontrol listesi |
| Satış | 12 ayda 15-30 upgrade veya tam cihaz satış/siparişi |
| Güvenlik | UV/ozon kilidi, sıcaklık/oksijen alarmı, sensör hata senaryoları |
| Pazarlama | Ürün sayfası, teknik datasheet, SSS, garanti ve servis dokümanı |

## 10. Kritik Riskler

| Risk | Etki | Önlem |
|---|---|---|
| Cihaz güveninin yeterince kanıtlanmaması | Yüksek | Sınırlı pilot, saha logları, güvenlik kilitleri, servis prosedürü |
| Donanım listesiyle rakiplerden ayrışamama | Yüksek | Yazılım, kayıt, uzaktan izleme ve AI farkını merkeze almak |
| Ücretsiz pilotların geri bildirim kalitesini düşürmesi | Orta | İndirimli ama ödemeli pilot modeli |
| Stok ve nakit riski | Yüksek | Ön ödeme ve sipariş üzerine üretim |
| AI vaatlerinin fazla iddialı olması | Orta | Tanı/tedavi değil, karar destek ve erken farkındalık dili |
| KVKK ve kamera kullanımı | Yüksek | Açık rıza, bilgilendirme metni, yetkili erişim ve loglama |
| UV/ozon güvenlik riski | Yüksek | Hasta içerideyken çalışmayı engelleyen yazılım/donanım kilitleri |

## 11. Öncelikli Ürün Yol Haritası

### Kısa Vade

- SCD41 + DHT fallback sensör stratejisini sahada stabil hale getirmek
- 7 inç dokunmatik ve mobil arayüzde taşmasız, hızlı kullanım deneyimi
- Ozon/UV güvenlik modlarını netleştirmek
- Sensör kayıt, grafik ve alarm geçmişini güvenilir hale getirmek
- V1 upgrade montaj sürecini 2-4 saat hedefiyle standartlaştırmak

### Orta Vade

- Kamera ve AI hareket/aktivite takibini klinik kullanıma uygun hale getirmek
- Hasta profiline göre alarm eşiklerini dinamikleştirmek
- Klinik raporu ve bakım özeti üretmek
- Uzaktan destek, güncelleme ve cihaz sağlık kontrolünü paketlemek
- Vetmarketi ürün sayfası ve demo materyallerini tamamlamak

### Uzun Vade

- Çoklu cihaz klinik paneli
- Abonelik veya lisanslı yazılım modeli
- Distribütör yönetimi ve yurt dışı servis ağı
- CE/EMC/LVD/RoHS teknik dosya hazırlığı
- Klinik verilerden anonim ürün iyileştirme analitiği

## 12. Konumlandırma Dili

Kullanılması önerilen ifadeler:

- Akıllı veteriner recovery platformu
- Kontrollü bakım ve izleme ünitesi
- Sensör kayıtlı ve uzaktan izlenebilir bakım sistemi
- AI destekli erken uyarı ve farkındalık katmanı
- Vetmarketi güvencesiyle Kuvoz 3.0 Smart ICU

Kaçınılması gereken ifadeler:

- Tedavi eder
- Tanı koyar
- Hayati riski engeller
- Yoğun bakım ihtiyacını ortadan kaldırır
- Veteriner hekim kontrolü gerekmez

## 13. Net Sonuç

Kuvoz 3.0'ın en güçlü ticari yolu, önce mevcut Kuvoz v1 müşteri tabanında Upgrade Kit olarak doğrulanmak, ardından Vetmarketi üzerinden Smart ICU tam cihaz ve yazılım/AI katmanı olarak büyümektir.

Başarı, kabinin fiziksel özelliklerinden çok şu üç alana bağlıdır:

1. Sahada güvenilir ve servis edilebilir çalışma
2. Klinik ekibine gerçekten zaman kazandıran sade arayüz
3. Kayıt, uzaktan izleme ve AI uyarı ile rakiplerden net ayrışma

Kuvoz 3.0 bu üç alanı birlikte başarırsa, yalnızca yerli bir veteriner kuvozu değil; Türkiye'den çıkabilecek akıllı veteriner bakım platformu olarak konumlanabilir.

## 14. İlgili Belgeler

- [Kuvoz 3.0 Pazar ve İhracat Analizi](KUVOZ_3_0_PAZAR_VE_IHRACAT_ANALIZI.md)
- [Kuvoz 3.0 Şirketleşme Yol Haritası](KUVOZ_3_0_SIRKETLESME_YOL_HARITASI.md)
- [Kuvoz Klinik Tanıtım Paketi](KLINIK_TANITIM_PAKETI.md)
- [Kuvoz AI Farkı Klinik Tanıtım Paketi](KLINIK_AI_TANITIM_PAKETI.md)
- [Kuvoz Lisanslama Stratejisi](KUVOZ_LISANSLAMA_STRATEJISI.md)
