# Soğutma Sistemi (Opsiyonel Özellik)

## Genel Bakış

Kuvoz sistemine opsiyonel soğutma özelliği eklendi. Bu özellik özellikle sıcak bölgelerdeki veterinerler için hayvanların ateşini düşürmek amacıyla tasarlanmıştır.

## Donanım Gereksinimleri

### GPIO Pin Bağlantısı
- **GPIO Pin:** 12 (Physical Pin 32)
- **Relay:** 8. kanal relay (veya ek relay modülü)
- **Buton ID:** b9
- **Cihaz:** Soğutma ünitesi (fan, soğutma pedi, vs.)

### Relay Mantığı
- `GPIO.LOW` = Soğutma AÇIK (relay aktif)
- `GPIO.HIGH` = Soğutma KAPALI (relay pasif)

## Yazılım Özellikleri

### 1. Güvenlik Önlemleri

#### Isıtma-Soğutma Çakışma Koruması
Sistem, ısıtma ve soğutma cihazlarının aynı anda çalışmasını **otomatik olarak engeller**:

```python
# Backend kontrol mantığı (web_server.py)
if self.button_states['b9']:  # Soğutma aktif
    heater_active = (self.button_states['b4'] or self.button_states['b5'])
    
    if heater_active:
        # GÜVENLİK: Isıtıcılar açıksa soğutmayı kapat
        self.safe_gpio_output(12, GPIO.HIGH)
        logger.warning("❄️  Cooling disabled - Heaters are active")
```

**Davranış:**
- Kullanıcı soğutmayı etkinleştirdiğinde ısıtıcılar (b4 veya b5) açıksa → Soğutma devre dışı bırakılır
- Uyarı mesajı loglanır
- UI'da buton görsel olarak aktif görünür ancak GPIO fiziksel olarak kapalıdır

### 2. Hysteresis Kontrolü

Relay'lerin sürekli açılıp kapanmasını (chattering) önlemek için hysteresis kullanılır:

```python
self.COOLING_HYSTERESIS = 0.5  # °C
```

**Mantık:**
- Sıcaklık `hedef + 0.5°C` üzerine çıkarsa → Soğutma AÇIK
- Sıcaklık `hedef - 0.5°C` altına düşerse → Soğutma KAPALI
- Aradaki 1°C bölgede (hysteresis zone) → Mevcut durum korunur

**Örnek:**
- Hedef: 30.0°C
- Açılma: 30.5°C'nin üzerinde
- Kapanma: 29.5°C'nin altında
- 29.5-30.5°C arası → Değişiklik yok (relay korunur)

### 3. Sensör Güvenliği

Sıcaklık sensörü okunamazsa soğutma otomatik kapatılır:

```python
if self.sensor_data['temperature']['value'] == '--':
    self.safe_gpio_output(12, GPIO.HIGH)
    logger.warning("⚠️  Temperature sensor unavailable - cooling disabled")
```

## Kullanıcı Arayüzü

### Hedef Sıcaklık Slider (sld12)

**HTML Tanımı:**
```html
<div class="target-item cooling-target">
    <i class="fas fa-snowflake"></i>
    <div class="target-info">
        <span class="target-label" data-i18n="slider.cooling">Soğutma Hedefi</span>
        <span class="target-value" id="sld12_value">30.0°C</span>
    </div>
    <div class="target-controls">
        <button class="target-btn minus" data-slider="sld12">-</button>
        <button class="target-btn plus" data-slider="sld12">+</button>
    </div>
    <input type="hidden" id="sld12" value="30.0" data-min="20" data-max="35" data-step="0.5">
</div>
```

**Özellikler:**
- **Varsayılan:** 30.0°C
- **Minimum:** 20°C
- **Maksimum:** 35°C
- **Adım:** 0.5°C
- **Görünüm:** Mavi kar tanesi ikonu

### Soğutma Butonu (b9)

**HTML Tanımı:**
```html
<button class="control-btn" data-pin="12" data-name="b9" id="btn_b9">
    <i class="fas fa-snowflake"></i>
    <span data-i18n="button.cooling">Soğutma</span>
</button>
```

**Pozisyon:** İklim kontrol bölümünde (ısıtıcıların yanında)

### Çok Dilli Destek

#### Türkçe
```javascript
button: {
    cooling: 'Soğutma'
},
slider: {
    cooling: 'Soğutma Hedefi (°C)'
}
```

#### İngilizce
```javascript
button: {
    cooling: 'Cooling'
},
slider: {
    cooling: 'Cooling Target (°C)'
}
```

## Teknik Detaylar

### Backend (web_server.py)

#### Değişiklikler:
1. **GPIO Pins:** `outChannels` listesine pin 12 eklendi
2. **Button States:** b9 için state tracking eklendi
3. **Slider Values:** sld12 için hedef sıcaklık (varsayılan 30.0°C)
4. **Hysteresis:** `COOLING_HYSTERESIS = 0.5` eklendi
5. **Control Logic:** Soğutma kontrolü `control_logic()` metoduna eklendi

### Frontend (index.html, script.js, styles.css)

#### HTML:
- Hedef sıcaklık slider (sld12) eklendi
- Soğutma butonu (b9) eklendi

#### JavaScript:
- Türkçe/İngilizce çeviriler eklendi
- `updateSlider()` metodu sld12 için güncellendi (°C gösterimi)

#### CSS:
- `.cooling-target` stili eklendi (mavi tema)
- İkon renklendirmesi

## Kullanım Senaryoları

### Sıcak İklimler
Yaz aylarında veya sıcak bölgelerde ortam sıcaklığı yüksek olduğunda:
1. Soğutma hedefini ayarla (örn. 28°C)
2. Soğutma butonunu etkinleştir
3. Sistem otomatik olarak sıcaklığı hedef değere düşürür

### Ateş Düşürme (Hipertermi)
Hayvan yüksek ateşli ise:
1. Soğutma hedefini düşük ayarla (örn. 25-27°C)
2. **Önemli:** Isıtıcıların (b4, b5) kapalı olduğundan emin ol
3. Soğutma sistemini başlat
4. Hayvanın sıcaklığını izle

### Operasyon Sonrası Bakım
Post-operatif dönemde sıcaklık kontrolü:
1. Veteriner hekim tavsiyesine göre soğutma hedefini ayarla
2. Sistem otomatik olarak hysteresis kontrolü ile optimal sıcaklığı korur

## Bakım ve Sorun Giderme

### Log Mesajları

#### Normal Çalışma:
```
❄️  Cooling ON - Temperature: 32.1°C, Target: 30.0°C
❄️  Cooling OFF - Temperature: 29.3°C, Target: 30.0°C
```

#### Uyarılar:
```
❄️  Cooling disabled - Heaters are active (safety interlock)
⚠️  Temperature sensor unavailable - cooling disabled for safety
```

### Sorun Giderme

#### Problem: Soğutma çalışmıyor
**Kontrol Et:**
1. Isıtıcılar (b4 veya b5) açık mı? → Kapatın
2. Sıcaklık sensörü çalışıyor mu? → DHT/SCD41 durumunu kontrol edin
3. GPIO pin 12 donanım bağlantısı doğru mu?
4. Relay çalışıyor mu? → `gpio_test.mk` ile test edin

#### Problem: Sürekli açılıp kapanıyor
**Çözüm:**
- Hysteresis değerini artırın (varsayılan 0.5°C):
```python
self.COOLING_HYSTERESIS = 1.0  # Daha geniş tolerans
```

#### Problem: Yavaş tepki veriyor
**Normal Davranış:**
- Kontrol döngüsü 5 saniyede bir çalışır
- Sensör okuma 15 saniyede bir yapılır
- Fiziksel sıcaklık değişimi zaman alır (termal inersi)

## Gelecek Geliştirmeler

### Planlanan Özellikler:
1. **PID Kontrol:** Isıtma gibi PID algoritması ile daha hassas kontrol
2. **Zamanlayıcı:** Belirli saatlerde otomatik soğutma
3. **Grafik:** Soğutma aktivitesi geçmişi
4. **Alarm:** Hedef sıcaklığa ulaşılamadığında uyarı
5. **Duty Cycle:** Nebulizer gibi döngüsel çalışma modu

## Güvenlik Notları

⚠️ **ÖNEMLİ UYARILAR:**

1. **Isıtma-Soğutma Çakışması:** Sistem otomatik engeller ancak kullanıcı manuel olarak da kontrol etmelidir
2. **Aşırı Soğutma:** Minimum 20°C altına ayarlamayın (hipotermiye sebep olabilir)
3. **Sensör Kontrolü:** Soğutma kullanırken sıcaklık sensörünün çalıştığından emin olun
4. **Veteriner Gözetimi:** Soğutma tedavisi veteriner hekim gözetiminde uygulanmalıdır
5. **Nem Kontrolü:** Soğutma sırasında nem seviyesini de izleyin (yoğunlaşma riski)

## Referanslar

- Backend kodu: [web_server.py](web_server.py#L183-L1170)
- Frontend HTML: [web/index.html](web/index.html#L85-L135)
- Frontend JS: [web/script.js](web/script.js#L48-L156)
- CSS stilleri: [web/styles.css](web/styles.css#L994-L1016)

---

**Son Güncelleme:** 10 Ocak 2026
**Versiyon:** 1.0.0
**Durum:** Production-Ready ✅
