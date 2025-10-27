# DHT Sensor GPIO Migration: GPIO 22 → GPIO 15

## 🔄 Değişiklik Özeti

### GPIO Pin Değişikliği
- **Eski:** GPIO 22 (Physical Pin 15)
- **Yeni:** GPIO 15 (Physical Pin 10)

### ✅ Güncellenmiş Dosyalar

#### 1. `lib/DHT_Native.py`
- ✅ `DHT_PIN = 15` (GPIO 15 varsayılan pin)
- ✅ Otomatik DHT11/DHT22 algılama fonksiyonu eklendi
- ✅ `detect_sensor_type()` fonksiyonu
- ✅ Pin parametresi opsiyonel hale getirildi
- ✅ Auto-detection desteği

#### 2. `web_server.py` 
- ✅ `self.pinDht = 15` (GPIO 22'den değiştirildi)
- ✅ Otomatik algılama ile sensör okuma
- ✅ Sensör tipini algılayarak log mesajlarında gösterme

#### 3. `test_dht_native.py`
- ✅ GPIO 15 pin kullanımı
- ✅ Otomatik DHT11/DHT22 algılama testi
- ✅ Physical pin 10 referansı güncellendi

## 🔌 Bağlantı Şeması (Güncellenmiş)

```
DHT11/DHT22 Sensor → Raspberry Pi
┌─────────────────┬─────────────────┐
│ DHT Pin         │ Raspberry Pi    │
├─────────────────┼─────────────────┤
│ VCC (+)         │ 3.3V (Pin 1)    │
│ DATA            │ GPIO 15 (Pin 10)│
│ GND (-)         │ GND (Pin 6)     │
└─────────────────┴─────────────────┘
```

## 🚀 Kullanım

### Otomatik Algılama
```python
from lib.DHT_Native import read_retry, detect_sensor

# Sensör tipini otomatik algıla
sensor_type = detect_sensor()  # DHT11=11 veya DHT22=22
print(f"Detected: DHT{sensor_type}")

# Otomatik algılama ile okuma
humidity, temperature = read_retry()  # Pin ve sensör tipi otomatik
```

### Manuel Kullanım
```python
from lib.DHT_Native import read_retry, DHT11, DHT22

# DHT11 ile okuma
humidity, temperature = read_retry(DHT11, 15)

# DHT22 ile okuma  
humidity, temperature = read_retry(DHT22, 15)
```

## 🧪 Test Komutları

```bash
# DHT sensor testi (otomatik algılama)
make dht-test

# Manuel test
python3 test_dht_native.py

# Web server başlatma
python3 web_server.py
```

## 🎯 Özellikler

- ✅ **Otomatik DHT11/DHT22 Algılama**: Sensör tipi otomatik tespit edilir
- ✅ **Backward Compatibility**: Eski API'ler hala çalışır
- ✅ **GPIO 15 Default**: Physical pin 10 kullanımı
- ✅ **Error Handling**: Gelişmiş hata yönetimi
- ✅ **Debug Logging**: Detaylı debug çıktıları
- ✅ **Flexible Pin**: Pin numarası değiştirilebilir

## 📝 Notlar

1. **Fiziksel Bağlantı**: DHT sensörünü GPIO 15 (Physical Pin 10)'a bağlayın
2. **Sensör Desteği**: Hem DHT11 hem DHT22 desteklenir
3. **Otomatik Algılama**: İlk okumada sensör tipi tespit edilir ve saklanır
4. **Performans**: Algılanan sensör tipi cache'lenir, tekrar algılama yapılmaz

## 🔧 Troubleshooting

Sensör okunamazsa:
```bash
# GPIO pin kontrolü
gpio readall

# Bağlantı testi
python3 test_dht_native.py

# Manuel sensör tipi testi
python3 -c "from lib.DHT_Native import detect_sensor; print(detect_sensor(15))"
```