# Kuvoz Kritik Sorun Analizi

## Özet
Repo tekrar incelendi ve önceki analiz notları güncel kodla karşılaştırıldı. İlk analiz faydalı bir başlangıçtı, ancak bazı maddeler güncel kodla tam örtüşmüyordu.

En kritik alan, birden fazla thread ve Socket.IO handler tarafından paylaşılan mutable state nesnelerine senkronizasyon olmadan erişilmesiydi.

Özellikle şu yapılar yüksek risk taşıyordu:

- `button_states`
- `slider_values`
- `gpio_output_states`
- `system_settings`
- `active_connections`

Bu alanlarda risk; bellek sızıntısından çok yarış durumu, eksik snapshot, kayıp güncelleme ve UI'ye tutarsız veri yayınıydı.

## Kritik Bulgular

### 1. Paylaşılan runtime state için eksik senkronizasyon
**Öncelik**: Yüksek  
**Konum**: `web_server.py`, `app/routes/socket_settings_routes.py`, `app/hardware/gpio_controller.py`

#### Sorun
Birden fazla thread aynı state nesnelerine erişiyor:

- kontrol döngüsü
- sensör döngüsü
- Socket.IO event handler'ları
- ayar kaydetme akışı

Özellikle bu tip erişimler riskliydi:

```python
self.button_states[name] = state
self.slider_values[slider_id] = value
self.gpio_output_states[name] = True
self.system_settings.update(flat_settings)
```

#### Risk
- UI'ye yarım güncellenmiş veri gitmesi
- ayar kaydında karışık state snapshot'ı
- GPIO durumu ile buton durumunun kısa süreli uyumsuz görünmesi

#### Uygulanan düzeltme
- `state_lock` eklendi.
- Kritik state güncellemeleri lock içine alındı.
- Socket yayınlarında doğrudan paylaşılan dict yerine snapshot helper kullanımı başlatıldı.
- `GPIOController` içindeki `gpio_output_states` yazımları lock ile korundu.

#### Kalan iyileştirme
Sensör verisi yazım akışı ileride daha sistematik bir snapshot modeline taşınmalı.

### 2. `active_connections` erişiminde yarış durumu
**Öncelik**: Yüksek  
**Konum**: `app/routes/socket_routes.py`, `app/routes/socket_settings_routes.py`, `web_server.py`

#### Sorun
Önceki analizde bu alan için "sonsuz büyüme" denmişti, ancak bu doğru değildi. `disconnect` tarafında silme işlemi zaten mevcut.

Gerçek sorun:

- connect/disconnect/client_event akışlarının aynı dict'e locksız erişmesi
- yayın sırasında `.values()` üzerinden gezerken eşzamanlı değişiklik olması
- kiosk izleme mantığında `last_seen` alanının yarış durumuna açık olması

#### Risk
- bağlantı listesinin eksik veya tutarsız yayınlanması
- nadir çalışma zamanı hataları
- yanlış bağlantı süresi veya kiosk canlılık bilgisi

#### Uygulanan düzeltme
- `connection_lock` eklendi.
- bağlantı ekleme, güncelleme, silme yardımcı metotlara taşındı.
- aktif bağlantı yayını helper payload üzerinden yapılmaya başlandı.

### 3. Ayar kaydetme akışı dosya bazında güvenli, state bazında eksikti
**Öncelik**: Yüksek  
**Konum**: `web_server.py`, `app/settings_store.py`, `app/routes/socket_settings_routes.py`

#### Sorun
Önceki analiz dosya yazım tarafını olduğundan daha sorunlu gösteriyordu. Gerçekte `save_settings_json()` temp dosya + replace kullandığı için dosya seviyesinde güvenli.

Ancak state tarafında açık vardı:

- ayar dict'leri farklı yerlerde locksız güncelleniyordu
- `save_settings()` bunları tek seferde tutarlı snapshot almadan yazıyordu

#### Risk
- kayıp güncelleme
- aynı anda değişen state'in karışık haliyle diske yazılması

#### Uygulanan düzeltme
- `save_settings()` lock altında tutarlı snapshot alacak şekilde güncellendi.
- `save_settings` öncesindeki önemli update noktaları lock içine alındı.

## Yanlış veya Güncel Koda Uymayan Eski Maddeler

### 4. "WebSocket emit thread-safe değil" maddesi yeniden çerçevelendi
**Durum**: Kısmen yanıltıcı

Mevcut sistem `Flask-SocketIO`yu `threading` modunda kullanıyor. Buradaki ana risk tek başına `socketio.emit()` çağrısı değil; emit edilen verinin aynı anda başka thread'ler tarafından değişebilmesiydi.

Doğru yaklaşım:

- emit öncesi snapshot/payload üretmek
- paylaşılan mutable state'i kilitlemek

### 5. "active_connections sonsuz büyüyor" maddesi kaldırıldı
**Durum**: Hatalı

`disconnect` sırasında temizleme zaten mevcut. Sorun bellek sızıntısından çok senkronizasyon eksikliğiydi.

### 6. "AI Manager vitals_history yarışı" maddesi kaldırıldı
**Durum**: Güncel kodla uyuşmuyor

İlk analizde bahsedilen yapı güncel `lib/ai/manager.py` içinde aynı şekilde bulunmuyor. AI modülünde lifecycle/state lock altyapısı zaten var.

## Orta Öncelikli Konular

### 7. Ayar şeması doğrulama eksikliği
**Öncelik**: Orta

`failure.dat` güvenli yazılıyor ama içerik doğrulaması sınırlı. Bozuk veya eksik alanlar için merkezi doğrulama hâlâ eksik.

Öneri:

- `validate_settings_payload()` benzeri tek giriş noktası
- slider tipleri ve aralıkları için kontrol
- bilinmeyen anahtarlar için warning log

### 8. Kimlik doğrulama eksikliği
**Öncelik**: Orta

Yerel ağdaki herkesin cihaza erişebilmesi operasyonel risk oluşturuyor.

Öneri:

- basit oturum tabanlı giriş
- en azından ayarlar ve kontrol uçları için koruma
- opsiyonel kiosk bypass mantığı

### 9. Geniş exception blokları
**Öncelik**: Orta

Donanım tarafında geniş exception tamamen kaçınılmaz olabilir, ancak ayar, dosya ve subprocess akışlarında daha spesifik exception kullanımı debug maliyetini düşürür.

## Düşük Öncelikli Konular

### 10. Magic number kullanımı
Bazı kritik eşikler isimlendirilmiş olsa da bütün sabitler aynı düzeyde merkezileştirilmiş değil.

### 11. Log gürültüsü
Uzun süre çalışan cihazlarda sensör ve AI logları için daha tutarlı rate limiting faydalı olur.

## Uygulanan Düzeltmeler

Bu analiz güncellemesiyle birlikte aşağıdaki kod düzeltmeleri de yapıldı:

1. `state_lock` ve `connection_lock` eklendi.
2. `active_connections` erişimi yardımcı metotlarla merkezileştirildi.
3. Socket yayınlarında snapshot/payload helper kullanımı başlatıldı.
4. `save_settings()` lock altında tutarlı snapshot alacak şekilde düzeltildi.
5. `GPIOController` içindeki `gpio_output_states` güncellemeleri lock ile korundu.
6. Ayar kaydetme ve bazı HTTP/Socket state güncellemeleri lock içine alındı.

## Sonraki Adımlar

1. Sensör verisi yazımlarını da tek tip snapshot modeline taşımak.
2. Ayarlar için şema doğrulama eklemek.
3. Kritik kontrol uçlarına kimlik doğrulama koymak.
4. Küçük bir concurrency regression testi eklemek.

## Sonuç

Repo genel yapısı sağlam. Asıl problem "tamamen yanlış mimari" değil, birkaç kritik shared-state noktasının zamanla büyümüş olmasıydı. Yapılan düzeltmelerle en riskli yarış durumu alanları belirgin şekilde azaltıldı.

**Analiz Tarihi**: 11 Nisan 2026  
**Durum**: Repo gerçeğine göre güncellendi  
**Sonraki Adım**: Sensör state akışı ve settings validation katmanını güçlendirmek
