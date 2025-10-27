# DHT_Native.py - Fonksiyon Analizi ve Kullanım Kılavuzu

**Dosya:** `lib/DHT_Native.py`  
**Amaç:** Platform bağımsız DHT11/DHT22 sensör sürücüsü  
**GPIO Pin:** 15 (Physical Pin 10)  
**Tarih:** 27 Ekim 2025  

---

## 📋 İçindekiler

1. [Genel Bakış](#-genel-bakış)
2. [Sınıf Yapısı](#-sınıf-yapısı) 
3. [Fonksiyon Analizi](#-fonksiyon-analizi)
4. [Global Fonksiyonlar](#-global-fonksiyonlar)
5. [Kullanım Örnekleri](#-kullanım-örnekleri)
6. [Hata Yönetimi](#-hata-yönetimi)
7. [Performans Optimizasyonları](#-performans-optimizasyonları)
8. [Sorun Giderme](#-sorun-giderme)

---

## 🎯 Genel Bakış

DHT_Native kütüphanesi, Raspberry Pi üzerinde DHT11 ve DHT22 sensörlerini okumak için geliştirilmiş platform bağımsız bir sürücüdür. Adafruit_DHT kütüphanesine alternatif olarak oluşturulmuş ve otomatik sensör algılama özelliği içerir.

### 🔧 Temel Özellikler

- ✅ **Otomatik Algılama**: DHT11/DHT22 sensörlerini otomatik tanır
- ✅ **Platform Bağımsız**: Raspberry Pi tüm versiyonlarında çalışır
- ✅ **GPIO Kontrolü**: Donanım seviyesinde GPIO protokolü
- ✅ **Hata Kurtarma**: Okuma hatalarında otomatik iyileştirme
- ✅ **Web Server Uyumlu**: Thread-safe GPIO yönetimi
- ✅ **Adafruit Uyumlu API**: Drop-in replacement

### 📊 Desteklenen Sensörler

| Sensör | Sıcaklık Aralığı | Nem Aralığı | Hassasiyet | GPIO Pin |
|--------|------------------|-------------|------------|----------|
| **DHT11** | 0-50°C | 20-100% | ±1°C, ±1% | GPIO 15 |
| **DHT22** | -40-80°C | 0-100% | ±0.1°C, ±0.1% | GPIO 15 |

---

## 🏗️ Sınıf Yapısı

### `class DHT_Native`

Ana sınıf yapısı ve özellikler:

```python
class DHT_Native:
    def __init__(self, pin=DHT_PIN):
        self.pin = pin                    # GPIO pin numarası
        self.last_temp = 25.0            # Son bilinen sıcaklık
        self.last_hum = 50.0             # Son bilinen nem
        self.read_count = 0              # Okuma sayacı
        self.detected_sensor_type = None # Algılanan sensör tipi
```

#### 🔧 Sınıf Özellikleri

- **`pin`**: GPIO pin numarası (varsayılan: 15)
- **`last_temp`**: Son başarılı sıcaklık okuması (fallback için)
- **`last_hum`**: Son başarılı nem okuması (fallback için)
- **`read_count`**: Toplam başarılı okuma sayısı
- **`detected_sensor_type`**: Otomatik algılanan sensör tipi (DHT11=11, DHT22=22)

---

## 🔍 Fonksiyon Analizi

### 1. `__init__(self, pin=DHT_PIN)`

**Amaç:** Sınıf başlatıcısı  
**Parametreler:**
- `pin` (int): GPIO pin numarası (varsayılan: 15)

**Kullanım:**
```python
# Varsayılan GPIO 15 ile
dht = DHT_Native()

# Özel pin ile
dht = DHT_Native(pin=18)
```

**Özellikleri:**
- Varsayılan değerleri ayarlar
- GPIO pin konfigürasyonu yapmaz (lazy loading)
- Thread-safe başlatma

---

### 2. `detect_sensor_type(self, pin=None)`

**Amaç:** DHT11 vs DHT22 otomatik algılama  
**Parametreler:**
- `pin` (int, opsiyonel): GPIO pin (varsayılan: self.pin)

**Dönüş:** 
- `int`: 11 (DHT11), 22 (DHT22), None (algılanamadı)

**Algoritma:**
```
1. DHT22 protokolü ile okuma dene
   ├── Başarılı → DHT22 olarak kaydet
   └── Başarısız → Adım 2'ye geç

2. DHT11 protokolü ile okuma dene  
   ├── Başarılı → DHT11 olarak kaydet
   └── Başarısız → None döndür

3. Değer aralığı kontrolü
   ├── DHT22: -40°C ile 80°C, 0-100%
   └── DHT11: 0°C ile 50°C, 20-100%
```

**Kullanım:**
```python
dht = DHT_Native()
sensor_type = dht.detect_sensor_type()

if sensor_type == 11:
    print("DHT11 sensörü algılandı")
elif sensor_type == 22:
    print("DHT22 sensörü algılandı")  
else:
    print("Sensör algılanamadı")
```

**Debug Çıktısı:**
```
DHT Sensor detection on GPIO 15...
DHT22 detected on GPIO 15
```

---

### 3. `read_dht_gpio(self, sensor_type, pin)`

**Amaç:** Donanım seviyesinde DHT protokolü okuma  
**Parametreler:**
- `sensor_type` (int): 11 (DHT11) veya 22 (DHT22)
- `pin` (int): GPIO pin numarası

**Dönüş:** 
- `tuple`: (humidity, temperature) veya (None, None)

**GPIO Protokolü:**
```
DHT Protokolü Timing:
├── 1. Başlatma sinyali (Host → Sensor)
│   ├── HIGH: 100ms (stabilizasyon)
│   ├── LOW: 18ms (DHT11) / 0.8ms (DHT22)
│   └── RELEASE: INPUT moda geç
├── 2. Sensör yanıtı (Sensor → Host)  
│   ├── LOW: 80μs (yanıt)
│   └── HIGH: 80μs (hazır)
└── 3. Veri aktarımı (40 bit)
    ├── Her bit: LOW (50μs) + HIGH (değişken)
    ├── Bit '0': HIGH 26-28μs
    └── Bit '1': HIGH ~70μs
```

**Veri Formatı:**
```
40 Bit Veri Paketi:
├── Byte 1: Nem tam kısmı
├── Byte 2: Nem ondalık kısmı  
├── Byte 3: Sıcaklık tam kısmı
├── Byte 4: Sıcaklık ondalık kısmı
└── Byte 5: Checksum (1+2+3+4)
```

**Kullanım:**
```python
dht = DHT_Native()
humidity, temperature = dht.read_dht_gpio(11, 15)

if humidity is not None:
    print(f"DHT11: {temperature}°C, {humidity}%rH")
else:
    print("Okuma başarısız")
```

**Hata Kurtarma Özellikleri:**
- **Signal Change Detection**: 200'e kadar sinyal değişikliği takibi
- **Multiple Start Position**: Farklı başlangıç pozisyonları deneme
- **Bit Shift Correction**: Bit kaydırma hatalarını düzeltme
- **Checksum Validation**: Veri bütünlüğü kontrolü
- **Value Range Check**: Geçerli değer aralığı kontrolü

---

### 4. `_alternative_parse(self, changes, sensor_type)`

**Amaç:** Alternatif veri parsing yöntemi  
**Parametreler:**
- `changes` (list): GPIO sinyal değişiklikleri
- `sensor_type` (int): Sensör tipi

**Dönüş:** 
- `tuple`: (humidity, temperature) veya (None, None)

**Özellikler:**
- Başarısız okmalarda devreye girer
- Basitleştirilmiş timing analizi
- Her 2 transition = 1 bit mantığı
- Kısmi veri ile çalışabilme

**Algoritma:**
```
Alternatif Parsing:
├── 1. İlk 4 transition'ı atla
├── 2. Her 2 transition = 1 bit
├── 3. Duration bazlı bit tespiti
│   ├── Uzun süre (>50μs) → Bit '1'
│   └── Kısa süre (≤50μs) → Bit '0'
├── 4. 32+ bit ile çalışmayı dene
└── 5. Basit byte dönüşümü
```

**Kullanım:** (Otomatik çağrılır)
```python
# read_dht_gpio içinde otomatik kullanım
if len(changes) < 82:
    return self._alternative_parse(changes, sensor_type)
```

---

### 5. `read_retry(self, sensor_type=None, pin=None, retries=3, delay=2)`

**Amaç:** Otomatik yeniden deneme ile okuma  
**Parametreler:**
- `sensor_type` (int, opsiyonel): Sensör tipi (None=otomatik algıla)
- `pin` (int, opsiyonel): GPIO pin (varsayılan: self.pin)  
- `retries` (int): Deneme sayısı (varsayılan: 3)
- `delay` (int): Denemeler arası gecikme (saniye)

**Dönüş:** 
- `tuple`: (humidity, temperature) veya (None, None)

**Özellikler:**
- Otomatik sensör algılama
- Configurable retry logic
- Başarısız denemeler arası bekleme
- İlerleme logları

**Kullanım:**
```python
dht = DHT_Native()

# Otomatik algılama ile
humidity, temperature = dht.read_retry()

# Belirli sensör tipi ile  
humidity, temperature = dht.read_retry(sensor_type=11)

# Özel parametreler ile
humidity, temperature = dht.read_retry(
    sensor_type=22, 
    pin=18, 
    retries=5, 
    delay=1
)
```

**Debug Çıktısı:**
```
DHT11 reading successful: 24.0°C, 65%
DHT11 attempt 1/3 failed
DHT11 attempt 2/3 failed  
DHT11 all attempts failed
```

---

### 6. `read(self, sensor_type=None, pin=None)`

**Amaç:** Tek seferlik okuma (retry yok)  
**Parametreler:**
- `sensor_type` (int, opsiyonel): Sensör tipi (None=otomatik algıla)
- `pin` (int, opsiyonel): GPIO pin (varsayılan: self.pin)

**Dönüş:** 
- `tuple`: (humidity, temperature) veya (None, None)

**Kullanım:**
```python
dht = DHT_Native()

# Tek okuma denemesi
humidity, temperature = dht.read()

if humidity is not None:
    print(f"Sıcaklık: {temperature}°C")
    print(f"Nem: {humidity}%")
else:
    print("Okuma başarısız")
```

**Ne Zaman Kullanılır:**
- Hızlı test okumaları için
- Performans kritik uygulamalarda
- Manuel hata yönetimi yapılacaksa

---

## 🌐 Global Fonksiyonlar

### Global Instance

```python
# Varsayılan GPIO 15 ile global instance
dht_native = DHT_Native(pin=DHT_PIN)
```

### 1. `read_retry(sensor_type=None, pin=DHT_PIN, retries=3, delay=2)`

**Amaç:** Global Adafruit_DHT.read_retry replacement  
**Parametreler:** Sınıf metodu ile aynı

**Kullanım:**
```python
from DHT_Native import read_retry

# Adafruit_DHT.read_retry yerine
humidity, temperature = read_retry(11, 15)

# Otomatik algılama ile  
humidity, temperature = read_retry(pin=15)
```

**Adafruit Uyumluluğu:**
```python
# Eski kod (Adafruit_DHT)
import Adafruit_DHT
humidity, temperature = Adafruit_DHT.read_retry(11, 15)

# Yeni kod (DHT_Native) - API uyumlu
from DHT_Native import read_retry  
humidity, temperature = read_retry(11, 15)
```

---

### 2. `read(sensor_type=None, pin=DHT_PIN)`

**Amaç:** Global Adafruit_DHT.read replacement  
**Parametreler:** Sınıf metodu ile aynı

**Kullanım:**
```python
from DHT_Native import read

# Tek okuma denemesi
humidity, temperature = read(11, 15)
```

---

### 3. `detect_sensor(pin=DHT_PIN)`

**Amaç:** Global sensör algılama fonksiyonu  
**Parametreler:**
- `pin` (int): GPIO pin numarası

**Kullanım:**
```python
from DHT_Native import detect_sensor

sensor_type = detect_sensor(15)
print(f"Algılanan sensör: DHT{sensor_type}")
```

---

## 💡 Kullanım Örnekleri

### Örnek 1: Basit Okuma

```python
#!/usr/bin/env python3
from DHT_Native import read_retry

# GPIO 15'ten otomatik algılama ile okuma
humidity, temperature = read_retry(pin=15)

if humidity is not None:
    print(f"Sıcaklık: {temperature:.1f}°C")
    print(f"Nem: {humidity:.1f}%")
else:
    print("Sensör okunamadı")
```

### Örnek 2: Sınıf Tabanlı Kullanım

```python
#!/usr/bin/env python3
from DHT_Native import DHT_Native

# Sensör instance oluştur
dht = DHT_Native(pin=15)

# Sensör tipini algıla
sensor_type = dht.detect_sensor_type()
print(f"Algılanan sensör: DHT{sensor_type}")

# Sürekli okuma
import time
while True:
    humidity, temperature = dht.read_retry()
    
    if humidity is not None:
        print(f"DHT{sensor_type}: {temperature:.1f}°C, {humidity:.1f}%rH")
    else:
        print("Okuma hatası")
    
    time.sleep(5)
```

### Örnek 3: Web Server Entegrasyonu

```python
#!/usr/bin/env python3
from DHT_Native import DHT_Native
import threading
import time

class SensorManager:
    def __init__(self):
        self.dht = DHT_Native(pin=15)
        self.last_temp = None
        self.last_hum = None
        self.running = False
    
    def start_monitoring(self):
        self.running = True
        thread = threading.Thread(target=self._monitor_loop, daemon=True)
        thread.start()
    
    def _monitor_loop(self):
        while self.running:
            hum, temp = self.dht.read_retry()
            if hum is not None and temp is not None:
                self.last_temp = temp
                self.last_hum = hum
                print(f"Sensor update: {temp:.1f}°C, {hum:.1f}%")
            time.sleep(5)
    
    def get_current_data(self):
        return {
            'temperature': self.last_temp,
            'humidity': self.last_hum,
            'sensor_type': self.dht.detected_sensor_type
        }

# Kullanım
sensor_manager = SensorManager()
sensor_manager.start_monitoring()
```

### Örnek 4: Hata Yönetimi

```python
#!/usr/bin/env python3
from DHT_Native import DHT_Native
import time

class RobustDHTReader:
    def __init__(self, pin=15):
        self.dht = DHT_Native(pin=pin)
        self.error_count = 0
        self.max_errors = 10
        
    def read_with_fallback(self):
        try:
            # Ana okuma
            hum, temp = self.dht.read_retry(retries=3)
            
            if hum is not None and temp is not None:
                # Başarılı okuma
                self.error_count = 0
                return hum, temp
            else:
                # Okuma başarısız - fallback
                self.error_count += 1
                
                if self.error_count < self.max_errors:
                    # Son bilinen değerleri kullan
                    if hasattr(self.dht, 'last_temp'):
                        return self.dht.last_hum, self.dht.last_temp
                
                # Maksimum hata sayısına ulaşıldı
                print(f"DHT sensör hatası: {self.error_count} başarısız deneme")
                return None, None
                
        except Exception as e:
            print(f"DHT okuma istisnası: {e}")
            return None, None

# Kullanım
reader = RobustDHTReader()
humidity, temperature = reader.read_with_fallback()
```

### Örnek 5: Kalibrasyonlu Okuma

```python
#!/usr/bin/env python3
from DHT_Native import DHT_Native

class CalibratedDHT:
    def __init__(self, pin=15):
        self.dht = DHT_Native(pin=pin)
        # Kalibrasyon değerleri
        self.temp_offset = 0.0
        self.temp_scale = 1.0
        self.hum_offset = 0.0
        self.hum_scale = 1.0
    
    def set_calibration(self, temp_offset=0, temp_scale=1, hum_offset=0, hum_scale=1):
        """Kalibrasyon parametrelerini ayarla"""
        self.temp_offset = temp_offset  
        self.temp_scale = temp_scale
        self.hum_offset = hum_offset
        self.hum_scale = hum_scale
    
    def read_calibrated(self):
        """Kalibre edilmiş okuma"""
        hum, temp = self.dht.read_retry()
        
        if hum is not None and temp is not None:
            # Kalibrasyon uygula
            temp_cal = (temp * self.temp_scale) + self.temp_offset
            hum_cal = (hum * self.hum_scale) + self.hum_offset
            
            # Değer sınırları
            temp_cal = max(-40, min(80, temp_cal))
            hum_cal = max(0, min(100, hum_cal))
            
            return hum_cal, temp_cal
        
        return None, None

# Kullanım
dht_cal = CalibratedDHT()
dht_cal.set_calibration(temp_offset=-2.0, hum_scale=0.95)

humidity, temperature = dht_cal.read_calibrated()
print(f"Kalibre edilmiş: {temperature:.1f}°C, {humidity:.1f}%")
```

---

## ⚠️ Hata Yönetimi

### Yaygın Hatalar ve Çözümleri

#### 1. GPIO Bağlantı Hataları

**Belirtiler:**
```
DHT11: No signal changes detected - check sensor connection
DHT11: Very few changes - sensor may not be responding
```

**Çözümler:**
```python
# Bağlantı kontrolü
def check_gpio_connection(pin):
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.HIGH)
        
        # Pin durumunu kontrol et
        GPIO.setup(pin, GPIO.IN)
        state = GPIO.input(pin)
        print(f"GPIO {pin} durumu: {'HIGH' if state else 'LOW'}")
        
        return state == 1  # HIGH bekleniyor
    except Exception as e:
        print(f"GPIO kontrol hatası: {e}")
        return False

# Kullanım
if not check_gpio_connection(15):
    print("GPIO 15 bağlantı sorunu")
```

#### 2. Timing Hataları

**Belirtiler:**
```
DHT11: Insufficient signal changes: 45
DHT11: Checksum error: 67 != 89
```

**Çözümler:**
```python
# Gelişmiş okuma parametreleri
def robust_read(pin=15, max_attempts=5):
    dht = DHT_Native(pin=pin)
    
    for attempt in range(max_attempts):
        try:
            # Her denemede biraz farklı timing
            time.sleep(0.1 * (attempt + 1))
            
            hum, temp = dht.read_retry(retries=1)
            if hum is not None:
                return hum, temp
                
        except Exception as e:
            print(f"Deneme {attempt+1}: {e}")
            continue
    
    return None, None
```

#### 3. Çoklu Instance Sorunları

**Problem:** Web server'da GPIO mode konflikti

**Çözüm:**
```python
# Singleton pattern ile
class DHT_SingletonManager:
    _instance = None
    _dht = None
    
    def __new__(cls, pin=15):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._dht = DHT_Native(pin=pin)
        return cls._instance
    
    def read(self):
        return self._dht.read_retry()

# Kullanım - her yerde aynı instance
dht_manager = DHT_SingletonManager()
humidity, temperature = dht_manager.read()
```

---

## 🚀 Performans Optimizasyonları

### 1. Okuma Frekansı Optimizasyonu

```python
import time

class OptimizedDHTReader:
    def __init__(self, pin=15, min_interval=2.0):
        self.dht = DHT_Native(pin=pin)
        self.min_interval = min_interval  # Minimum okuma aralığı
        self.last_read_time = 0
        self.cached_data = (None, None)
    
    def read(self):
        current_time = time.time()
        
        # Minimum aralık kontrolü
        if current_time - self.last_read_time < self.min_interval:
            # Cache'den döndür
            return self.cached_data
        
        # Yeni okuma
        hum, temp = self.dht.read_retry()
        if hum is not None:
            self.cached_data = (hum, temp)
            self.last_read_time = current_time
        
        return self.cached_data
```

### 2. Asenkron Okuma

```python
import asyncio
import threading
from DHT_Native import DHT_Native

class AsyncDHTReader:
    def __init__(self, pin=15):
        self.dht = DHT_Native(pin=pin)
        self.latest_data = (None, None)
        self.reading = False
    
    async def start_background_reading(self, interval=5):
        """Arkaplanda sürekli okuma"""
        while True:
            if not self.reading:
                self.reading = True
                try:
                    # Blocking I/O'yu thread'de çalıştır
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None, 
                        self.dht.read_retry
                    )
                    if result[0] is not None:
                        self.latest_data = result
                finally:
                    self.reading = False
            
            await asyncio.sleep(interval)
    
    def get_latest(self):
        """En son veriyi döndür (anında)"""
        return self.latest_data

# Kullanım
async def main():
    reader = AsyncDHTReader()
    
    # Arkaplanda okuma başlat
    asyncio.create_task(reader.start_background_reading())
    
    # Ana uygulama döngüsü
    while True:
        hum, temp = reader.get_latest()
        if hum is not None:
            print(f"Async: {temp:.1f}°C, {hum:.1f}%")
        
        await asyncio.sleep(1)

# asyncio.run(main())
```

---

## 🔧 Sorun Giderme

### Debug Modu Aktifleştirme

```python
import logging

# DHT_Native debug logging
logging.basicConfig(level=logging.DEBUG)

# Veya manual debug
def debug_dht_read(pin=15):
    """Detaylı debug okuma"""
    dht = DHT_Native(pin=pin)
    
    print(f"=== DHT Debug - GPIO {pin} ===")
    
    # 1. Sensör algılama
    sensor_type = dht.detect_sensor_type(pin)
    print(f"Algılanan sensör: {sensor_type}")
    
    # 2. Manuel okuma
    if sensor_type:
        hum, temp = dht.read_dht_gpio(sensor_type, pin)
        print(f"Okuma sonucu: {temp}°C, {hum}%")
        
        # 3. Sistem bilgileri
        print(f"Son bilinen: {dht.last_temp}°C, {dht.last_hum}%")
        print(f"Okuma sayısı: {dht.read_count}")
    
    return sensor_type, (hum if 'hum' in locals() else None, 
                        temp if 'temp' in locals() else None)

# Kullanım
debug_dht_read(15)
```

### Donanım Test Fonksiyonları

```python
def hardware_test():
    """Tam donanım testi"""
    print("🔧 DHT Donanım Testi")
    print("=" * 40)
    
    # GPIO kontrolü
    try:
        import RPi.GPIO as GPIO
        print("✅ RPi.GPIO import OK")
        
        GPIO.setmode(GPIO.BCM)
        print("✅ GPIO.setmode OK")
        
        # Pin testi
        test_pin = 15
        GPIO.setup(test_pin, GPIO.OUT)
        GPIO.output(test_pin, GPIO.HIGH)
        
        GPIO.setup(test_pin, GPIO.IN)
        state = GPIO.input(test_pin)
        print(f"✅ GPIO {test_pin} durumu: {'HIGH' if state else 'LOW'}")
        
    except Exception as e:
        print(f"❌ GPIO hatası: {e}")
        return False
    
    # DHT okuma testi
    try:
        from DHT_Native import DHT_Native
        dht = DHT_Native(pin=15)
        
        print("\n📊 Sensör Algılama:")
        sensor_type = dht.detect_sensor_type()
        if sensor_type:
            print(f"✅ DHT{sensor_type} algılandı")
            
            print("\n📊 Okuma Testi:")
            for i in range(3):
                hum, temp = dht.read_retry(retries=1)
                if hum is not None:
                    print(f"✅ Okuma {i+1}: {temp:.1f}°C, {hum:.1f}%")
                else:
                    print(f"❌ Okuma {i+1}: Başarısız")
                time.sleep(2)
        else:
            print("❌ Sensör algılanamadı")
            return False
            
    except Exception as e:
        print(f"❌ DHT hatası: {e}")
        return False
    
    print("\n🎉 Donanım testi tamamlandı")
    return True

# Test çalıştır
if __name__ == "__main__":
    hardware_test()
```

### Performans Profiling

```python
import time
import statistics

def performance_test(pin=15, test_count=20):
    """DHT performans testi"""
    print(f"⚡ DHT Performans Testi ({test_count} okuma)")
    print("=" * 50)
    
    dht = DHT_Native(pin=pin)
    
    # Timing verileri
    read_times = []
    success_count = 0
    error_count = 0
    
    start_time = time.time()
    
    for i in range(test_count):
        test_start = time.time()
        hum, temp = dht.read_retry(retries=1)
        test_end = time.time()
        
        read_time = test_end - test_start
        read_times.append(read_time)
        
        if hum is not None:
            success_count += 1
            print(f"✅ #{i+1:2d}: {temp:.1f}°C {hum:.1f}% ({read_time:.3f}s)")
        else:
            error_count += 1
            print(f"❌ #{i+1:2d}: HATA ({read_time:.3f}s)")
        
        time.sleep(0.5)  # Sensör dinlenmesi
    
    total_time = time.time() - start_time
    
    # İstatistikler
    print(f"\n📊 SONUÇLAR:")
    print(f"Toplam süre: {total_time:.1f}s")
    print(f"Başarılı: {success_count}/{test_count} (%{success_count/test_count*100:.1f})")
    print(f"Hatalı: {error_count}/{test_count} (%{error_count/test_count*100:.1f})")
    
    if read_times:
        print(f"Ortalama okuma süresi: {statistics.mean(read_times):.3f}s")
        print(f"En hızlı okuma: {min(read_times):.3f}s")
        print(f"En yavaş okuma: {max(read_times):.3f}s")
        print(f"Standart sapma: {statistics.stdev(read_times):.3f}s")

# Performans testi çalıştır
if __name__ == "__main__":
    performance_test()
```

---

## 📚 Referanslar ve Kaynaklar

### İlgili Dosyalar

- `web_server.py` - Web server entegrasyonu
- `test_dht_real.py` - Test script'i
- `analyze_ozone_control.py` - Sistem analizi

### DHT Protokol Referansları

- [DHT11 Datasheet](https://www.mouser.com/datasheet/2/758/DHT11-Technical-Data-Sheet-Translated-Version-1143054.pdf)
- [DHT22 Datasheet](https://www.sparkfun.com/datasheets/Sensors/Temperature/DHT22.pdf)
- [GPIO Timing Requirements](https://www.raspberrypi.org/documentation/hardware/gpio/)

### Alternatif Kütüphaneler

```python
# Kütüphane karşılaştırması
alternatives = {
    'Adafruit_DHT': {
        'pros': ['Stabil', 'Yaygın kullanım'],
        'cons': ['Platform bağımlı', 'C extension gerekli']
    },
    'DHT_Native': {
        'pros': ['Platform bağımsız', 'Otomatik algılama', 'Thread-safe'],
        'cons': ['Yeni kütüphane', 'Python-only']
    },
    'pigpio': {
        'pros': ['Çok hassas timing', 'Daemon tabanlı'],
        'cons': ['Karmaşık kurulum', 'Ek servis gerekli']
    }
}
```

---

## ✅ Özet

DHT_Native kütüphanesi, Raspberry Pi'da DHT11/DHT22 sensörlerini okumak için geliştirilmiş modern bir sürücüdür:

### 🎯 Ana Avantajlar

- ✅ **Plug & Play**: Otomatik sensör algılama
- ✅ **Drop-in Replacement**: Adafruit_DHT API uyumlu
- ✅ **Platform Bağımsız**: Tüm RPi modellerinde çalışır
- ✅ **Web Server Ready**: Thread-safe GPIO yönetimi
- ✅ **Robust**: Gelişmiş hata kurtarma algoritmaları

### 🔧 Kullanım Senaryoları

1. **Web Tabanlı Uygulamalar**: Kuvoz web server entegrasyonu
2. **IoT Projeleri**: Uzaktan sensör izleme
3. **Veri Logger**: Sürekli sıcaklık/nem kaydı
4. **Otomasyon Sistemleri**: HVAC kontrol sistemleri
5. **Prototipleme**: Hızlı DHT sensör testleri

### 🚀 Başlangıç için Minimum Kod

```python
#!/usr/bin/env python3
from DHT_Native import read_retry

# GPIO 15'ten okuma (otomatik algılama)
humidity, temperature = read_retry(pin=15)

if humidity is not None:
    print(f"🌡️  {temperature:.1f}°C")
    print(f"💧 {humidity:.1f}%rH")
else:
    print("❌ Sensör okunamadı")
```

**Son Güncelleme:** 27 Ekim 2025  
**Versiyon:** Platform Independent DHT Driver  
**GPIO:** 15 (Physical Pin 10)