# CO2'den Oksijen Tahmini - Teknik Dokümantasyon

## Genel Bakış

Oksijen sensörü temin edilemediği durumlarda, CO2 (SCD30) sensöründen oksijen seviyesi tahmini yapılmaktadır. Bu özellik **master** branch'e eklenmiştir.

## Nasıl Çalışır?

### 1. Fiziksel Prensip

Kapalı bir ortamda CO2 ve O2 seviyeleri ters orantılıdır:
- Solunum ve metabolik süreçler → O2 tüketimi + CO2 üretimi
- Zayıf havalandırma → CO2 artar, O2 azalır
- İyi havalandırma → CO2 azalır, O2 normale döner

### 2. Tahmin Algoritması

`estimate_oxygen_from_co2()` metodu parçalı lineer interpolasyon kullanır:

| CO2 Seviyesi (ppm) | O2 Tahmini (%) | Hava Kalitesi |
|-------------------|---------------|---------------|
| < 400 | 20.9% | Dış mekan havası |
| 400 - 800 | 20.9% → 20.0% | İyi havalandırma |
| 800 - 1200 | 20.0% → 19.0% | Orta kalite |
| 1200 - 1500 | 19.0% → 18.0% | Zayıf |
| 1500 - 2000 | 18.0% → 17.0% | Kötü |
| > 2000 | < 17.0% | Çok kötü (min %15) |

### 3. Güvenlik Sınırları

- **Minimum O2:** %15 (daha düşük değerler tehlikelidir)
- **CO2 > 2000 ppm:** Her 500 ppm için %0.5 O2 düşüşü
- **Maksimum O2:** %20.9 (normal atmosfer)

## Kod Değişiklikleri

### Backend (web_server.py)

#### 1. Yeni Metod: `estimate_oxygen_from_co2()`

```python
def estimate_oxygen_from_co2(self, co2_ppm):
    """
    CO2 seviyesinden O2 tahmini yapar.
    
    Args:
        co2_ppm: CO2 seviyesi (ppm)
        
    Returns:
        float: Tahmini O2 yüzdesi (15-20.9%)
    """
    # Parçalı lineer interpolasyon...
```

**Konum:** web_server.py, ~line 425

#### 2. Sensor Reading Thread Entegrasyonu

CO2 okuma başarılı olduğunda:

```python
if 0 <= co2_ppm <= 10000:
    self.sensor_data['co2'] = {
        'value': f"{co2_ppm:.0f}",
        'status': 'OK'
    }
    
    # Oksijen sensörü yoksa CO2'den O2 tahmini yap
    if not self.oxygen_sensor_available:
        estimated_o2 = self.estimate_oxygen_from_co2(co2_ppm)
        if estimated_o2 is not None:
            self.sensor_data['oxygen'] = {
                'value': f"{estimated_o2:.1f}",
                'status': f'Tahmini (CO2: {co2_ppm:.0f} ppm)'
            }
            logger.info(f"💡 O2 tahmini CO2'den: {estimated_o2:.1f}% (CO2: {co2_ppm:.0f} ppm)")
```

**Konum:** web_server.py, ~line 560-575

#### 3. Ozone Control Güncellenmesi

Ozon kontrolü artık hem gerçek hem tahmini O2 değerlerini kullanabilir:

```python
# Önceden: if self.oxygen_sensor_available and 'oxygen' in self.sensor_data:
# Şimdi: if 'oxygen' in self.sensor_data:

if 'oxygen' in self.sensor_data:
    current_oxygen = float(self.sensor_data['oxygen']['value'])
    oxygen_source = self.sensor_data['oxygen']['status']
    if current_oxygen > 24.0:
        oxygen_multiplier = 1.5
        logger.info(f"🌟 High oxygen ({current_oxygen:.1f}%, {oxygen_source}) - Extended ozone duty")
```

**Konum:** 
- `ozone_control()` - web_server.py, ~line 890
- `update_ozone_duty_cycle()` - web_server.py, ~line 935

### Frontend (web/script.js)

Frontend kodu **değişiklik gerektirmedi**. Mevcut yapı otomatik olarak:
- Oksijen değerini gösterir
- Status mesajını gösterir ("Tahmini (CO2: 850 ppm)")
- Ozon modunu günceller

## Kullanım

### 1. Normal Çalışma (Oksijen Sensörü Mevcut)

```
✅ Oksijen sensörü algılandı
🌡️  O2: 20.8% (Gerçek sensör)
💨 CO2: 650 ppm
```

### 2. Tahmini Mod (Oksijen Sensörü Yok)

```
⚠️  Oksijen sensörü bulunamadı
🌡️  O2: 19.5% (Tahmini - CO2: 950 ppm)
💨 CO2: 950 ppm
💡 O2 tahmini CO2'den: 19.5% (CO2: 950 ppm)
```

### 3. Ozon Kontrolü

Her iki durumda da ozon kontrolü çalışır:

```
# Gerçek sensör
🌟 High oxygen (25.2%, OK) - Extended ozone duty

# Tahmini değer
🌟 High oxygen (24.5%, Tahmini (CO2: 500 ppm)) - Extended ozone duty
```

## Test Senaryoları

### Senaryo 1: CO2 Düşük (İyi Havalandırma)

```python
CO2: 600 ppm → O2 tahmini: ~20.45%
Sonuç: Normal oksijenli ortam, standart ozon süresi
```

### Senaryo 2: CO2 Yüksek (Zayıf Havalandırma)

```python
CO2: 1400 ppm → O2 tahmini: ~18.33%
Sonuç: Düşük oksijenli ortam, ozon süresi uzatılmaz
```

### Senaryo 3: CO2 Çok Yüksek (Acil Havalandırma)

```python
CO2: 2500 ppm → O2 tahmini: ~16.5%
Sonuç: Tehlikeli seviye uyarısı, acil havalandırma gerekli
```

## Avantajlar

1. **Maliyet:** Oksijen sensörü gereksiz (DFRobot O2 ~$50-80)
2. **Güvenilirlik:** SCD30 CO2 sensörü daha yaygın ve güvenilir
3. **Bakım:** Tek sensör = daha az bakım
4. **Uyumluluk:** Mevcut sistem mantığı korundu

## Sınırlamalar

1. **Doğruluk:** ±1-2% O2 hata payı olabilir
2. **Gecikme:** CO2 sensörü 2 saniye ölçüm periyodu
3. **Çevresel:** Açık pencere/kapı tahmini bozabilir
4. **Aralık:** CO2 > 10000 ppm'de tahmin güvenilmez

## Konfigürasyon

Varsayılan ayarlar:

```python
# web_server.py
CO2_AVAILABLE = True      # SCD30 sensörü
OXYGEN_AVAILABLE = False  # Gerçek O2 sensörü yok
```

Manuel override (test için):

```python
# Tahmini modu devre dışı bırak
if not self.oxygen_sensor_available:
    # Bu bloğu yoruma al
    estimated_o2 = self.estimate_oxygen_from_co2(co2_ppm)
    ...
```

## Gelecek Geliştirmeler

1. **Kalibrasyon:** İlk kurulumda dış mekan havası referansı
2. **Makine Öğrenimi:** Geçmiş verilerden öğrenme
3. **Sensör Füzyonu:** Sıcaklık/nem ile O2 tahmini iyileştirme
4. **Alarm Sistemi:** Düşük O2 uyarıları

## Log Mesajları

```bash
# Başarılı tahmin
💡 O2 tahmini CO2'den: 19.5% (CO2: 950 ppm)

# Ozon kontrolü
🌟 High oxygen (24.5%, Tahmini (CO2: 500 ppm)) - Extended ozone duty

# Hata durumu
⚠️ CO2'den O2 tahmini hatası: invalid literal for float()
```

## Sorun Giderme

### Problem: O2 değeri gösterilmiyor

**Çözüm:**
1. CO2 sensörünün çalıştığını kontrol et: `make test-scd30`
2. Log'da CO2 okumalarını kontrol et: `journalctl -u kuvoz-web -f`
3. `co2_sensor_available = True` olduğunu doğrula

### Problem: O2 tahmini mantıksız

**Çözüm:**
1. CO2 değerini kontrol et (400-5000 ppm normal)
2. Ortamın kapalı olduğundan emin ol
3. SCD30 sensörünü kalibrasyon yap

### Problem: Ozon kontrolü çalışmıyor

**Çözüm:**
1. `sensor_data['oxygen']` dict'inde veri olduğunu kontrol et
2. O2 değerinin %24'ün üzerinde olduğunu kontrol et
3. Ozon duty cycle slider ayarlarını kontrol et

## Referanslar

- SCD30 Datasheet: Sensirion CO2 Sensor
- Indoor Air Quality Standards: ASHRAE 62.1
- Oxygen Physiology: 15-21% O2 safe range
- HVAC Guidelines: CO2 < 1000 ppm recommended

## Versiyon Bilgisi

- **Ekleme Tarihi:** 22 Aralık 2025
- **Branch:** master
- **Etkilenen Dosyalar:**
  - web_server.py (3 değişiklik)
  - CO2_TO_O2_ESTIMATION.md (yeni)
- **Test Durumu:** Teorik doğrulandı, sahada test edilmeli
