Program# Dezenfeksiyon Güvenlik Modu (Disinfection Safety Mode)

## Genel Bakış

Dezenfeksiyon güvenlik modu, UV ve Ozon dezenfeksiyon cihazlarının kullanımı sırasında sistemin güvenliğini sağlayan otomatik koruma sistemidir. Bu mod aktif olduğunda, normal çalışma fonksiyonları (ısıtma, nemlendirme, fan, vb.) otomatik olarak devre dışı bırakılır.

## Özellikler

### 🔒 Otomatik Koruma
- UV (b7) veya Ozon (b8) aktifleştirildiğinde sistem otomatik olarak dezenfeksiyon moduna girer
- Tüm normal kontrol fonksiyonları (b1-b6) otomatik olarak kapatılır
- Kontrol döngüsü (`control_logic()`) devre dışı bırakılır

### ⚠️ Kullanıcı Uyarıları
**Başlangıç Onay Modalı** (cleaning.html):
- UV veya Ozon butonu açılmaya çalışıldığında önce onay modalı görüntülenir
- Kullanıcıya şunlar hatırlatılır:
  - Normal kontrollerin devre dışı kalacağı
  - Sadece UV/Ozon çalışabileceği
  - Hayvanların kafes dışında olması gerektiği
- Kullanıcı "Başlat ve Devam Et" butonuna basmalıdır

**Görsel Göstergeler**:
- **Temizlik Sayfası**: Mor renk pulslu banner "DEZENFEKSIYON MODU AKTİF"
- **Ana Sayfa**: Mor renk uyarı banner'ı "Normal kontroller devre dışı"
- **Toast Bildirimleri**: Mod değişikliklerinde otomatik bildirim

### 🔓 Otomatik Çıkış
- UV **VE** Ozon **her ikisi de** kapatıldığında mod otomatik olarak devre dışı kalır
- Normal kontroller yeniden aktif hale gelir
- Kullanıcıya başarı bildirimi gösterilir

## Teknik Uygulama

### Backend (web_server.py)

#### Durum Yönetimi
```python
# KuvozServer.__init__() içinde
self.disinfection_mode = False
self.disinfection_start_time = 0
```

#### Kontrol Döngüsü Koruması
```python
def control_logic(self):
    """Ana kontrol döngüsü"""
    # ⚠️ SAFETY: Skip all normal controls when in disinfection mode
    if self.disinfection_mode:
        logger.debug("🦠 Disinfection mode active - normal controls disabled")
        return
    
    # Normal control logic continues...
```

#### WebSocket Event Handlers

**Mod Aktivasyonu** (`@socketio.on('toggle_button')`):
```python
# UV veya Ozon AÇILDIĞINDA
if name in ['b7', 'b8'] and state == True:
    if not kuvoz_server.disinfection_mode:
        kuvoz_server.disinfection_mode = True
        
        # Tüm normal fonksiyonları kapat (b1-b6)
        for btn_name in ['b1', 'b2', 'b3', 'b4', 'b5', 'b6']:
            if kuvoz_server.button_states.get(btn_name):
                # Turn off the function
                pin_index = int(btn_name[1:]) - 1
                btn_pin = kuvoz_server.outChannels[pin_index]
                kuvoz_server.toggle_button(btn_name, btn_pin, False)
        
        # Tüm istemcileri bilgilendir
        emit('disinfection_mode', {
            'active': True,
            'message': 'Dezenfeksiyon modu aktif'
        }, broadcast=True)
```

**Mod Deaktivasyonu**:
```python
# UV veya Ozon KAPATILDIĞINDA - Her ikisi de OFF ise çık
if name in ['b7', 'b8'] and state == False:
    if kuvoz_server.disinfection_mode:
        uv_off = not kuvoz_server.button_states.get('b7', False)
        ozone_off = not kuvoz_server.button_states.get('b8', False)
        
        if uv_off and ozone_off:
            kuvoz_server.disinfection_mode = False
            emit('disinfection_mode', {
                'active': False,
                'message': 'Normal kontroller tekrar aktif'
            }, broadcast=True)
```

**Durum Yanıtı** (`@socketio.on('get_status')`):
```python
status_data = {
    # ... diğer veriler
    'disinfection_mode': kuvoz_server.disinfection_mode
}
```

### Frontend (cleaning.html + script.js)

#### Onay Modalı HTML
```html
<!-- 🦠 Disinfection Confirmation Modal -->
<div class="modal-overlay" id="disinfectionConfirmModal">
    <div class="modal-content">
        <h2>⚠️ Dezenfeksiyon Modu Başlatılacak</h2>
        <p>
            🔒 Tüm normal kontroller devre dışı kalacak<br>
            🦠 Sadece UV ve Ozon çalışabilecek<br>
            ⚠️ Hayvanların kafes dışında olduğundan emin olun
        </p>
        <button id="disinfectionCancelBtn">İptal</button>
        <button id="disinfectionConfirmBtn">Başlat ve Devam Et</button>
    </div>
</div>
```

#### JavaScript Event Interceptor
```javascript
// UV/Ozon butonlarını yakalama
function interceptDisinfectionButton(buttonElement, buttonName, pinNumber) {
    buttonElement.addEventListener('click', function(e) {
        const isCurrentlyOff = !window.kuvozController.buttonStates[buttonName];
        
        if (isCurrentlyOff) {
            e.preventDefault();
            e.stopPropagation();
            
            // Modal göster
            disinfectionConfirmModal.style.display = 'flex';
        }
    }, true); // Capture phase - diğer handler'lardan önce çalışır
}
```

#### WebSocket Listener
```javascript
// Server'dan gelen disinfection_mode eventlerini dinle
socket.on('disinfection_mode', function(data) {
    if (data.active) {
        disinfectionBanner.style.display = 'flex';
        showToast('🦠 Dezenfeksiyon modu aktif', 'warning');
    } else {
        disinfectionBanner.style.display = 'none';
        showToast('✅ Normal kontroller aktif', 'success');
    }
});
```

## Kullanım Senaryoları

### Senaryo 1: UV Dezenfeksiyon Başlatma
1. Kullanıcı Temizlik sayfasına gider
2. UV butonuna basar
3. ⚠️ Onay modalı belirir
4. "Başlat ve Devam Et" butonuna basar
5. ✅ UV açılır, dezenfeksiyon banner'ı görünür
6. 🔒 Tüm normal kontroller (ısıtma, nem, vs.) kapatılır
7. Kullanıcı işlem tamamlanınca UV'yi kapatır
8. ✅ Dezenfeksiyon modu kapanır, normal kontroller aktif olur

### Senaryo 2: Hem UV hem Ozon Kullanımı
1. Kullanıcı UV başlatır (yukarıdaki adımlar)
2. Dezenfeksiyon modu zaten aktif
3. Ozon butonuna basar → Bu sefer modal GÖRÜNMEYEBİLİR (zaten dezenfeksiyon modundayız)
4. Ozon aktif olur
5. Kullanıcı önce UV'yi kapatır → Dezenfeksiyon modu DEVAM EDER (Ozon hala açık)
6. Kullanıcı Ozon'u da kapatır → ✅ Şimdi dezenfeksiyon modu kapanır

### Senaryo 3: Ana Sayfadan Kontrol Denemesi
1. Temizlik sayfasında dezenfeksiyon modu aktif
2. Kullanıcı Ana Sayfa'ya gider
3. 🦠 Mor banner görünür: "Dezenfeksiyon modu aktif"
4. Isıtma butonuna basmaya çalışır
5. ❌ Buton etkinleşmez (backend reddeder)
6. Kullanıcı Temizlik sayfasına geri döner
7. UV/Ozon'u kapatır
8. Ana Sayfa'ya döndüğünde normal kontroller çalışır

## Güvenlik Özellikleri

### Çoklu Koruma Katmanları

1. **UI Seviyesi**: 
   - Onay modalı kullanıcıyı uyarır
   - Banner'lar görsel geri bildirim sağlar

2. **Event Handler Seviyesi**:
   - Button click event'leri capture phase'de yakalanır
   - Normal handler'lar çalışmadan önce kontrol edilir

3. **Backend Seviyesi**:
   - `control_logic()` dezenfeksiyon modunda tamamen atlanır
   - Normal buton toggle istekleri reddedilebilir (isteğe bağlı)

4. **State Synchronization**:
   - WebSocket ile tüm istemciler senkronize edilir
   - Broadcast mesajları sayesinde multi-tab desteği

### Thread Safety
- `disinfection_mode` flag'i ana thread tarafından güncellenir
- `control_logic()` thread'i sadece okuma yapar (race condition yok)
- GPIO state değişiklikleri `safe_gpio_output()` kullanır

## Konfigürasyon

### Dezenfeksiyon Butonları
```python
# web_server.py
DISINFECTION_BUTTONS = ['b7', 'b8']  # UV ve Ozon
```

### Normal Kontrol Butonları
```python
# web_server.py - Dezenfeksiyon modunda kapatılacak butonlar
NORMAL_CONTROL_BUTTONS = ['b1', 'b2', 'b3', 'b4', 'b5', 'b6']
```

### Modal Mesajları
Mesajlar [cleaning.html](../web/cleaning.html) içinde hardcode edilmiştir. Çoklu dil desteği için `data-i18n` özellikleri eklenebilir.

## Test Prosedürü

### Manuel Test
1. **Başlangıç Testi**:
   ```bash
   # Web server'ı başlat
   python3 web_server.py
   
   # Browser'da aç: http://localhost:8000
   ```

2. **Onay Modalı Testi**:
   - Temizlik sayfasına git
   - UV butonuna bas
   - Modal'ın göründğünü doğrula
   - İptal'e bas → Modal kapanmalı, UV açılmamalı
   - Tekrar bas → "Başlat ve Devam Et" → UV açılmalı

3. **Banner Testi**:
   - UV açık iken mor banner'ın göründüğünü doğrula
   - Ana Sayfa'ya git → Banner orada da görünmeli

4. **Kontrol Devre Dışı Testi**:
   - Dezenfeksiyon modu aktif iken
   - Isıtma butonuna bas → Backend loglarında "disinfection mode active" mesajı görmeli
   - UV'yi kapat → Banner kaybolmalı
   - Isıtma butonuna bas → Şimdi çalışmalı

### Otomatik Test (Gelecek)
```python
# test_disinfection_mode.py (TODO)
def test_disinfection_mode_activation():
    """UV açıldığında dezenfeksiyon modunun aktifleştiğini test et"""
    pass

def test_normal_controls_disabled():
    """Normal kontrollerin devre dışı kaldığını test et"""
    pass

def test_disinfection_mode_exit():
    """Tüm dezenfeksiyon butonları kapatıldığında çıkışı test et"""
    pass
```

## Troubleshooting

### Problem: Modal gösterilmiyor
**Çözüm**: Browser console'da JavaScript hataları kontrol et
```javascript
console.log('disinfectionConfirmModal:', document.getElementById('disinfectionConfirmModal'));
```

### Problem: Banner hep gösteriliyor
**Çözüm**: Sunucu loglarını kontrol et, buton durumlarını doğrula
```bash
journalctl -u kuvoz-web -f | grep "disinfection"
```

### Problem: Normal kontroller hala çalışıyor
**Çözüm**: `control_logic()` içindeki return statement'ı kontrol et
```python
# web_server.py - control_logic() başında
if self.disinfection_mode:
    logger.debug("🦠 Disinfection mode active")
    return  # ← Bu satır eksik olabilir
```

## İlgili Dosyalar

### Backend
- [web_server.py](../web_server.py) - Ana server, lines 180-183 (state), 716-719 (control), 1468-1525 (handlers)

### Frontend  
- [web/cleaning.html](../web/cleaning.html) - Temizlik sayfası, modal + banner
- [web/index.html](../web/index.html) - Ana sayfa, banner
- [web/script.js](../web/script.js) - WebSocket handlers, UI updates

### Dokümantasyon
- [README_WEB.md](../README_WEB.md) - Genel web arayüzü dokümantasyonu
- [CLAUDE.md](../CLAUDE.md) - Proje geliştirme kılavuzu

## Gelecek Geliştirmeler

### Planlanan Özellikler
1. **Zamanlayıcı Entegrasyonu**: 
   - Dezenfeksiyon süresi otomatik kapatma
   - Tahmini bitiş zamanı gösterimi

2. **Log Kaydı**:
   - Dezenfeksiyon oturumlarının detaylı loglanması
   - Süre, kullanılan cihazlar, oksijen seviyeleri

3. **Çoklu Dil Desteği**:
   - Modal ve banner'lar için i18n
   - Türkçe/İngilizce toggle

4. **Oksijen Sensörü Entegrasyonu**:
   - Ozon kullanımı sırasında O2 seviyesi uyarıları
   - Kritik seviyede otomatik kapatma

5. **Mobil Bildirim**:
   - Firebase Push Notification
   - Dezenfeksiyon tamamlandı bildirimi

## Sürüm Geçmişi

### v1.0.0 (25 Aralık 2025)
- ✅ İlk implementasyon
- ✅ Backend state yönetimi
- ✅ Frontend onay modalı
- ✅ Görsel banner'lar
- ✅ WebSocket senkronizasyonu
- ✅ Multi-tab desteği

---

**Son Güncelleme**: 25 Aralık 2025  
**Yazar**: AI Coding Agent (GitHub Copilot)  
**Lisans**: Kuvoz Project © 2025
