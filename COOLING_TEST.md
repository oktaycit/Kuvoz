# Soğutma Sistemi Test Rehberi

## 🧊 İki Çalışma Modu

Soğutma sistemi artık **iki modda** çalışabilir:

### 1. **MANUEL MOD** (Slider = 0 veya sensör yok)
- Soğutma butonu açık → Sürekli çalışır
- Sıcaklık kontrolü YOK
- Test için idealdir
- Slider'a gerek yok

### 2. **OTO MOD** (Slider > 0 ve sensör var)
- Hedef sıcaklığa göre otomatik açılır/kapanır
- Hysteresis kontrolü var (±0.5°C)
- Normal kullanım için

---

## 🔧 Test Senaryoları

### Senaryo 1: Manuel Test (Slider'sız)

```bash
# 1. Web arayüzünü aç
# 2. Soğutma hedefini 0°C yap (veya slider'ı kullanma)
# 3. Soğutma butonuna (b9) tıkla
# 4. Relay aktif olmalı (sürekli AÇIK)
```

**Beklenen Davranış:**
- Buton AÇIK → GPIO 12 LOW (relay çalışır)
- Buton KAPALI → GPIO 12 HIGH (relay durur)
- Sıcaklık kontrolü yapılmaz

**Log mesajı:**
```
❄️ Cooling MANUAL mode - Always ON
GPIO 12 -> LOW (relay ON)
```

### Senaryo 2: Düşük Sıcaklık Testi

```bash
# 1. Soğutma hedefini 18°C yap (ortam 20°C)
# 2. Soğutma butonunu aç
# 3. Ortam zaten soğuk olduğu için kapalı kalmalı
```

**Beklenen Davranış:**
- Sıcaklık 20°C > Hedef 18°C + Hysteresis 0.5°C
- GPIO 12 LOW (soğutma AÇIK)
- Sıcaklık 17.5°C'ye düşünce kapanır

### Senaryo 3: Yüksek Sıcaklık Testi

```bash
# 1. Soğutma hedefini 25°C yap
# 2. Ortamı ısıt (örn. ısıtıcı ile 27°C'ye)
# 3. Soğutma butonunu aç
# 4. Otomatik devreye girmeli
```

**Beklenen Davranış:**
- Sıcaklık 27°C > Hedef 25.5°C → Soğutma AÇIK
- Sıcaklık 24.5°C'ye düşünce → Soğutma KAPALI

---

## 📊 Yeni Özellikler

### Minimum Sıcaklık: 15°C
- **Eski:** 20-35°C arası
- **Yeni:** 15-35°C arası
- Test için düşük sıcaklıkları deneyebilirsiniz

### Varsayılan Değer: 25°C
- **Eski:** 30°C
- **Yeni:** 25°C
- Daha makul bir başlangıç değeri

### Opsiyonel Slider
- Slider 0 ise → Manuel mod
- Slider > 0 ise → Oto mod
- Sensör yoksa → Otomatik manuel moda geçer

---

## 🧪 Hızlı Test Komutları

### GPIO Doğrudan Test
```bash
# Manuel ON/OFF test
gpio -g mode 12 out
gpio -g write 12 0  # AÇIK - relay tıklamalı
sleep 2
gpio -g write 12 1  # KAPALI
```

### Web Arayüzünden Manuel Test

1. **Tarayıcı Console Aç** (F12)

2. **Manuel Mod İçin:**
```javascript
// Slider'ı 0 yap (manuel mod)
document.getElementById('sld12').value = 0;
kuvozController.updateSlider('sld12', 0);

// Soğutmayı aç
kuvozController.toggleButton('b9', '12');

// Log izle - "Cooling MANUAL mode" görmeli
```

3. **Oto Mod İçin:**
```javascript
// Slider'ı 18°C yap (ortam 20°C ise test için)
document.getElementById('sld12').value = 18;
kuvozController.updateSlider('sld12', 18);

// Soğutmayı aç
kuvozController.toggleButton('b9', '12');
```

---

## 🐛 Sorun Giderme

### Sorun: "Soğutma butonunu test edemiyorum, ortam 20°C"

✅ **Çözüldü!** Artık 3 yöntem var:

1. **Manuel mod kullan:**
   - Slider'ı 0 yap veya hiç dokunma
   - Soğutma butonu sürekli açık kalır

2. **Düşük hedef ayarla:**
   - Slider minimum artık 15°C
   - 18°C'ye ayarla, ortam 20°C ise çalışır

3. **Ortamı ısıt:**
   - Oda ısıtıcısı veya kuvoz ısıtıcıları ile
   - 25-27°C'ye çıkar, sonra test et

### Sorun: "Slider gerekli mi?"

❌ **Hayır!** Slider opsiyonel:

- **Slider VAR ve > 0:** Otomatik sıcaklık kontrolü
- **Slider YOK veya = 0:** Manuel ON/OFF kontrolü
- **Sensör YOK:** Otomatik manuel moda geçer

Manuel mod özellikle **test** ve **acil durumlar** için kullanışlıdır.

---

## 📋 Test Checklist

Dosyaları güncelledikten sonra:

- [ ] `git pull` veya dosyaları tekrar yükle
- [ ] `sudo systemctl restart kuvoz-web`
- [ ] Browser cache temizle (Ctrl+Shift+R)
- [ ] Slider'ı 18°C'ye ayarla (min artık 15°C)
- [ ] Soğutma butonuna tıkla
- [ ] Log izle: `sudo journalctl -u kuvoz-web -f`
- [ ] GPIO 12'yi izle veya relay sesini dinle

---

## 💡 İpuçları

### Manuel Mod Ne Zaman Kullanılır?

1. **Test Aşaması:** Relay çalışıyor mu kontrol et
2. **Sensör Arızası:** Sıcaklık sensörü çalışmıyorsa
3. **Acil Durum:** Hızlıca manuel müdahale gerek
4. **Donanım Testi:** GPIO pin'i test et

### Oto Mod Ne Zaman Kullanılır?

1. **Normal Kullanım:** Günlük operasyon
2. **Hassas Kontrol:** Belirli sıcaklık korunmalı
3. **Enerji Tasarrufu:** Gereksiz çalışmayı önler
4. **Hayvan Bakımı:** Veteriner hekim tarafından belirlenen sıcaklık

---

## 🎯 Önerilen Test Sırası

```bash
# 1. Manuel Mod Testi
echo "TEST 1: Manuel Mod"
# Slider'ı 0 yap, butona bas, GPIO izle

# 2. Düşük Sıcaklık Testi  
echo "TEST 2: Düşük Sıcaklık (18°C)"
# Slider 18°C, ortam 20°C, çalışmalı

# 3. Yüksek Sıcaklık Testi
echo "TEST 3: Yüksek Sıcaklık (27°C)"
# Ortamı ısıt, soğutma devreye girmeli

# 4. Hysteresis Testi
echo "TEST 4: Hysteresis (±0.5°C)"
# Hedef 25°C, sıcaklık 25.3°C olunca açılmamalı

# 5. Güvenlik Kilidi Testi
echo "TEST 5: Isıtıcı Güvenlik Kilidi"
# Isıtıcı aç, soğutma kapanmalı
```

---

**Güncellenme:** 10 Ocak 2026
**Versiyon:** 1.1.0
**Yenilikler:**
- ✅ Minimum sıcaklık 15°C
- ✅ Manuel mod eklendi (slider opsiyonel)
- ✅ Varsayılan 25°C
- ✅ Test için iyileştirildi
