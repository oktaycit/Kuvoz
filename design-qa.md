# Gece referans düzeni — 24 Ekim 2026

final result: passed

## Kaynak ve görüntüler

Kaynak: `/Users/oktaycit/.codex/generated_images/01a16a11-565b-72e0-bdfa-50e13476d04c/exec-b9592d94-b0d8-42e5-80f9-588bdd9e1004.png` (1619×971).

Canlı Kuvozfurkan görüntüleri: `/Users/oktaycit/Projeler/kuvoz/output/night-reference/`.

- `night-reference-size.png`: 1619×971 CSS ve piksel, yoğunluk 1, kaynakla aynı boyut.
- `comparison.jpg`: kaynak ve uygulama eşit 800×480'e normalize edilerek yan yana; tam görünüm incelendi.
- `controls-comparison.jpg`: aynı koordinatlardan sağ kontroller ayrıntısı, 864×490; ayrıca açılarak incelendi.
- `night-800.png`: gerçek 800×480 kiosk görünümü.
- `night-mobile.png`: 390×844 CSS görünümün 390×1179 tam sayfa kaydı. Yapışkan alt menü tam sayfa görüntüsünde ilk görünümün altına sabitlenir; kullanıcı kaydırdığında görünümün altında kalır.
- `targets-800.png`, `system-800.png`, `camera-expanded.png`: panellerin erişim kanıtları.
- `clinical-regression.png`, `care-regression.png`: diğer temaların korunması.

## Beş görsel yüzey

- **Tipografi:** büyük beyaz sayılar, küçük açık mavi kaynak/hedefler, dikey kontrollerde başlık ve gerçek durum alt satırı. Mevcut sans font ailesi ve tabular sayılar korunur.
- **Yerleşim:** sol rail, üç büyük sensör, durum bandı, geniş kamera ve sağda altı düğme. Referansla aynı boyutta bölge oranları karşılaştırıldı. Kiosk 76 px rail ve 24 px alt bilgi alanına uyarlanır; her kontrol en az 44 px. Altı kontrol için bölüm clientHeight ve scrollHeight 264 px; kaydırma gerekmez.
- **Renkler:** gece mavisi zemin, koyu mavi kartlar, turkuaz etkin anahtar/gezinme, açık metin. Gerçek uyarı yokken nötr bant; mevcut uyarılar anlamsal renkte gösterilir. Diyaloglardaki açık renkli mod/sayaç yüzeyleri koyu palete bağlandı.
- **Görseller:** mevcut Font Awesome ikonları ve gerçek kamera görüntüsü kullanılır. Kaynaktaki boş kamera yerine gerçek kare gösterilmesi kasıtlıdır. Kırpma/takip algoritması değiştirilmedi.
- **İçerik:** örnek sayılar, hasta ve tarih yerine canlı bilgiler; örnekteki beş etkin çıkış yerine gerçek çıkış durumları. Sensörsüz O₂ sayısal tahmini gösterilmez; yokluğu alt bilgide belirtilir. Kilit etiketinde gerçek eylem “Ekranı kilitle” kullanılır.

## Düzeltmeler ve doğrulama

1. Gece ortak referans altyapısına alındı; Klinik ve Bakım koşulları ayrı kaldı. Aynı mevcut düğümler taşınır, işleyiciler kopyalanmaz.
2. Sağ liste dikey grid olarak kuruldu. İlk kompakt kontroldeki 2 px taşma, boşlukların ayarlanmasıyla giderildi; 264/264 px son ölçüm geçti.
3. Night hedef diyaloğunda açık mod/sayaç alanı farkları giderildi; hedef ve zamanlayıcı kontrolleri erişilebilir kaldı.
4. Mobilde 390 px clientWidth ve scrollWidth eşit, kenar dışına taşan görünür öğe yok. Mod düğmeleri doğru kapsayıcıda kalıyor.
5. Klinik→Bakım→Gece aynı açık sayfada tercih olayıyla test edildi. Her tema doğru sınıfı/ebeveynleri kullanıyor; tekrar eden id yok.
6. Sistem, hedefler ve kamera büyütme panelleri açılıp kapatıldı; kamera ana yüzeyine döndü. Çıkış ve hedef değiştirme komutları canlı cihazda tetiklenmedi.
7. JavaScript söz dizimi, `git diff --check` ve mevcut 11 panel/kamera testi geçti. Son tarayıcı hata kaydı boş. Yerel ve cihazdaki dört görünüm dosyasının SHA-256 değerleri aynı; servis aktif, yeniden başlatma yapılmadı.

## Sınırlar ve P3 farklar

Standart ikon biçimleri, uzun gerçek hasta adı ve bazı boşluk/font ayrıntıları kaynaktan farklıdır. Örnek kritik alarm veya etkin ekipman durumu üretilmedi. Küçük ekranda dokunma hedeflerini korumak için yazı/boşluklar sıkıştırıldı. Fiziksel dokunmatik ve gerçek röle aç/kapat testi bu görsel işte yapılmadı. Yeni bitmap varlık gerekmedi. İşlevi engelleyen P0/P1/P2 bulgusu kalmadı.
