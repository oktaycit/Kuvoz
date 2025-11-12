# MQTT Broker Kurulum ve Yapılandırma

**Tarih:** 2025-11-12
**Durum:** Aktif
**Broker:** Eclipse Mosquitto 2.0.21

## Özet

Kuvoz inkübatör sistemi için Raspberry Pi üzerine Mosquitto MQTT broker kuruldu. Hem TCP (port 1883) hem de WebSocket (port 9001) bağlantılarını desteklemektedir.

## Kurulum

### 1. Mosquitto Broker Kurulumu

```bash
# Paket deposunu güncelle
sudo apt update

# Mosquitto broker ve client araçlarını kur
sudo apt install -y mosquitto mosquitto-clients
```

**Kurulu Paketler:**
- `mosquitto` (2.0.21-1): MQTT broker servisi
- `mosquitto-clients`: Komut satırı test araçları (pub/sub)
- `libmosquitto1`: Mosquitto kütüphanesi
- `libwebsockets19t64`: WebSocket desteği

### 2. Yapılandırma

**Yapılandırma Dosyası:** `/etc/mosquitto/conf.d/kuvoz.conf`

```ini
# Kuvoz MQTT Broker Configuration

# MQTT listener (TCP port 1883)
listener 1883 0.0.0.0

# WebSocket listener (port 9001)
listener 9001 0.0.0.0
protocol websockets

# Allow anonymous connections
allow_anonymous true
```

**Açıklamalar:**
- `listener 1883 0.0.0.0`: Tüm network arayüzlerinde MQTT protokolü dinle
- `listener 9001 0.0.0.0`: WebSocket bağlantıları için (web tarayıcılardan erişim)
- `allow_anonymous true`: Kimlik doğrulama olmadan bağlantılara izin ver (yerel ağ için)

> **Güvenlik Notu:** `allow_anonymous true` ayarı yerel ağ kullanımı içindir. Üretim ortamında kullanıcı/şifre veya TLS sertifikası kullanılmalıdır.

### 3. Servis Yönetimi

```bash
# Servisi başlat
sudo systemctl start mosquitto

# Servisi durdur
sudo systemctl stop mosquitto

# Servisi yeniden başlat
sudo systemctl restart mosquitto

# Servis durumunu kontrol et
sudo systemctl status mosquitto

# Otomatik başlatmayı etkinleştir (açılışta)
sudo systemctl enable mosquitto

# Otomatik başlatmayı devre dışı bırak
sudo systemctl disable mosquitto
```

### 4. Log Kontrolü

```bash
# Mosquitto loglarını göster
sudo tail -f /var/log/mosquitto/mosquitto.log

# Systemd journal logları
journalctl -u mosquitto -f

# Son 50 satır
journalctl -u mosquitto -n 50
```

## Test

### 1. Yerel Bağlantı Testi

**Terminal 1 - Subscribe (Mesaj Dinle):**
```bash
mosquitto_sub -h localhost -t test/topic
```

**Terminal 2 - Publish (Mesaj Gönder):**
```bash
mosquitto_pub -h localhost -t test/topic -m "Hello MQTT"
```

Terminal 1'de "Hello MQTT" mesajını göreceksiniz.

### 2. Network Bağlantı Testi

**Raspberry Pi IP adresi:**
```bash
hostname -I
# Output: 192.168.1.132
```

**Başka bir bilgisayardan test:**
```bash
# MQTT TCP bağlantısı
mosquitto_pub -h 192.168.1.132 -t kuvoz/test -m "Remote test"

# Debug modu ile
mosquitto_pub -h 192.168.1.132 -t kuvoz/test -m "Test message" -d
```

### 3. Port Kontrolü

```bash
# MQTT portlarını kontrol et
ss -tlnp | grep -E "(1883|9001)"

# Beklenen çıktı:
# LISTEN 0.0.0.0:1883  (MQTT TCP)
# LISTEN 0.0.0.0:9001  (WebSocket)
```

### 4. WebSocket Testi (JavaScript)

```javascript
// Tarayıcı konsolunda veya Node.js ile test
const client = mqtt.connect('ws://192.168.1.132:9001');

client.on('connect', () => {
  console.log('Bağlantı başarılı!');
  client.subscribe('kuvoz/#');
  client.publish('kuvoz/test', 'WebSocket test mesajı');
});

client.on('message', (topic, message) => {
  console.log(`Topic: ${topic}, Message: ${message.toString()}`);
});
```

## Topic Yapısı (Önerilen)

```
kuvoz/
├── sensors/
│   ├── temperature      # Sıcaklık sensörü (°C)
│   ├── humidity         # Nem sensörü (%)
│   └── oxygen           # Oksijen sensörü (%)
├── controls/
│   ├── b1              # Aydınlatma
│   ├── b2              # Nemlendirici
│   ├── b3              # Nem Kontrol
│   ├── b4              # Karbon Isıtıcı
│   ├── b5              # IR Isıtıcı
│   ├── b6              # Fan
│   ├── b7              # UV Sterilizasyon
│   └── b8              # Ozon Sterilizasyon
├── settings/
│   ├── temperature_target
│   ├── humidity_target
│   └── mode            # Hafif/Orta/Yoğun
├── status/
│   ├── online          # Cihaz çevrimiçi durumu
│   └── last_seen       # Son görülme zamanı
└── system/
    ├── restart         # Sistem yeniden başlatma
    └── error           # Hata mesajları
```

### Topic Örnekleri

**Sensör Verileri (Publish):**
```bash
mosquitto_pub -h localhost -t kuvoz/sensors/temperature -m "25.5"
mosquitto_pub -h localhost -t kuvoz/sensors/humidity -m "65"
mosquitto_pub -h localhost -t kuvoz/sensors/oxygen -m "21.0"
```

**Kontrol Komutları (Subscribe/Publish):**
```bash
# Aydınlatmayı aç
mosquitto_pub -h localhost -t kuvoz/controls/b1 -m "ON"

# Nemlendiriciyi kapat
mosquitto_pub -h localhost -t kuvoz/controls/b2 -m "OFF"

# Sıcaklık hedefini ayarla
mosquitto_pub -h localhost -t kuvoz/settings/temperature_target -m "28"
```

**Tüm Kuvoz Topic'lerini Dinle:**
```bash
mosquitto_sub -h localhost -t "kuvoz/#" -v
```

## Entegrasyon

### Python (Paho MQTT)

```python
import paho.mqtt.client as mqtt

# Callback fonksiyonları
def on_connect(client, userdata, flags, rc):
    print(f"Bağlandı: {rc}")
    client.subscribe("kuvoz/#")

def on_message(client, userdata, msg):
    print(f"{msg.topic}: {msg.payload.decode()}")

# Client oluştur
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# Raspberry Pi'ye bağlan
client.connect("192.168.1.132", 1883, 60)

# Mesaj yayınla
client.publish("kuvoz/sensors/temperature", "25.5")

# Mesaj dinlemeye başla (blocking)
client.loop_forever()
```

**Python MQTT Kütüphanesi Kurulum:**
```bash
pip install paho-mqtt
```

### Node.js (MQTT.js)

```javascript
const mqtt = require('mqtt');

// Raspberry Pi'ye bağlan
const client = mqtt.connect('mqtt://192.168.1.132:1883');

client.on('connect', () => {
  console.log('Bağlandı!');

  // Topic'e abone ol
  client.subscribe('kuvoz/#');

  // Mesaj yayınla
  client.publish('kuvoz/sensors/temperature', '25.5');
});

client.on('message', (topic, message) => {
  console.log(`${topic}: ${message.toString()}`);
});
```

**Node.js MQTT Kütüphanesi Kurulum:**
```bash
npm install mqtt
```

### ESP32/Arduino (PubSubClient)

```cpp
#include <WiFi.h>
#include <PubSubClient.h>

const char* ssid = "WiFi_SSID";
const char* password = "WiFi_Password";
const char* mqtt_server = "192.168.1.132";

WiFiClient espClient;
PubSubClient client(espClient);

void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Mesaj: [");
  Serial.print(topic);
  Serial.print("] ");
  for (int i = 0; i < length; i++) {
    Serial.print((char)payload[i]);
  }
  Serial.println();
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("MQTT'ye bağlanıyor...");
    if (client.connect("ESP32Client")) {
      Serial.println("bağlandı");
      client.subscribe("kuvoz/controls/#");
    } else {
      Serial.print("hata, rc=");
      Serial.print(client.state());
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Sensör verisini yayınla
  float temperature = 25.5;
  char temp_str[8];
  dtostrf(temperature, 1, 2, temp_str);
  client.publish("kuvoz/sensors/temperature", temp_str);

  delay(10000);
}
```

## Güvenlik

### 1. Kullanıcı/Şifre Koruması

**Şifre dosyası oluştur:**
```bash
# Şifre dosyası oluştur
sudo mosquitto_passwd -c /etc/mosquitto/passwd kuvoz_user

# Yeni kullanıcı ekle
sudo mosquitto_passwd /etc/mosquitto/passwd another_user
```

**Yapılandırmayı güncelle:**
```bash
sudo nano /etc/mosquitto/conf.d/kuvoz.conf
```

Ekle:
```ini
# Şifre dosyası
password_file /etc/mosquitto/passwd

# Anonim erişimi kapat
allow_anonymous false
```

**Servisi yeniden başlat:**
```bash
sudo systemctl restart mosquitto
```

**Şifreli bağlantı testi:**
```bash
mosquitto_pub -h localhost -t test -m "secure" -u kuvoz_user -P your_password
```

### 2. TLS/SSL Şifreleme

**Self-signed sertifika oluştur:**
```bash
# CA sertifikası
openssl req -new -x509 -days 365 -extensions v3_ca -keyout ca.key -out ca.crt

# Sunucu sertifikası
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 365
```

**Yapılandırma:**
```ini
listener 8883
protocol mqtt
cafile /etc/mosquitto/ca_certificates/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile /etc/mosquitto/certs/server.key
require_certificate false
```

### 3. Firewall Kuralları

```bash
# UFW firewall kullanıyorsanız
sudo ufw allow 1883/tcp   # MQTT
sudo ufw allow 9001/tcp   # WebSocket

# Sadece yerel ağdan erişim
sudo ufw allow from 192.168.1.0/24 to any port 1883
sudo ufw allow from 192.168.1.0/24 to any port 9001
```

## Sorun Giderme

### Servis Başlatma Hataları

**Problem:** `mosquitto.service failed`

**Çözüm 1 - Log kontrolü:**
```bash
sudo journalctl -u mosquitto -n 50
```

**Çözüm 2 - Yapılandırma test:**
```bash
mosquitto -c /etc/mosquitto/mosquitto.conf -v
```

**Çözüm 3 - Port çakışması:**
```bash
# Port 1883'ü kullanan prosesleri kontrol et
sudo lsof -i :1883
```

### Bağlantı Hataları

**Problem:** `Connection refused`

**Kontroller:**
```bash
# 1. Servis çalışıyor mu?
sudo systemctl status mosquitto

# 2. Port açık mı?
ss -tlnp | grep 1883

# 3. Firewall engellemiyor mu?
sudo ufw status
```

### Yapılandırma Hataları

**Problem:** `Duplicate "log_dest file" value`

**Çözüm:** Ana `mosquitto.conf` dosyasında tanımlı ayarları `conf.d/` dosyalarında tekrar tanımlamayın.

**Problem:** `Invalid bridge configuration`

**Çözüm:** Listener tanımlamalarında `protocol` anahtar kelimesini doğru kullanın:
```ini
# Doğru
listener 9001 0.0.0.0
protocol websockets

# Yanlış
listener 9001 websockets
```

## Performans

### Bağlantı Limitleri

**Varsayılan Değerler:**
- Maksimum bağlantı: Sınırsız (`max_connections -1`)
- Keepalive süresi: 60 saniye
- Max paket boyutu: 10 MB

**Optimizasyon (yüksek yük için):**
```ini
# /etc/mosquitto/conf.d/performance.conf
max_connections 1000
max_keepalive 65535
message_size_limit 10485760
max_inflight_messages 20
max_queued_messages 1000
```

### Monitoring

**Bağlantı sayısını kontrol et:**
```bash
sudo netstat -an | grep :1883 | grep ESTABLISHED | wc -l
```

**Log boyutunu kontrol et:**
```bash
du -h /var/log/mosquitto/mosquitto.log
```

**Bellek kullanımı:**
```bash
ps aux | grep mosquitto
```

## Bakım

### Log Rotation

Mosquitto logları `/var/log/mosquitto/mosquitto.log` dosyasına yazılır ve otomatik olarak rotate edilir.

**Manuel log temizleme:**
```bash
sudo truncate -s 0 /var/log/mosquitto/mosquitto.log
sudo systemctl restart mosquitto
```

### Yedekleme

**Yapılandırma dosyalarını yedekle:**
```bash
sudo tar -czf mosquitto-config-backup.tar.gz /etc/mosquitto/
```

**Persistence verilerini yedekle:**
```bash
sudo systemctl stop mosquitto
sudo cp -r /var/lib/mosquitto/ /backup/mosquitto/
sudo systemctl start mosquitto
```

### Güncelleme

```bash
# Paket güncellemelerini kontrol et
sudo apt update
sudo apt list --upgradable | grep mosquitto

# Mosquitto'yu güncelle
sudo apt upgrade mosquitto

# Servis durumunu kontrol et
sudo systemctl status mosquitto
```

## Referanslar

- **Resmi Dokümantasyon:** https://mosquitto.org/documentation/
- **MQTT Protokolü:** https://mqtt.org/
- **Mosquitto Config:** https://mosquitto.org/man/mosquitto-conf-5.html
- **Paho Python:** https://www.eclipse.org/paho/index.php?page=clients/python/index.php
- **MQTT.js:** https://github.com/mqttjs/MQTT.js

## Sistem Bilgileri

**Kurulum Ortamı:**
- İşletim Sistemi: Raspberry Pi OS Trixie (Debian 13.1)
- Raspberry Pi: 3B+/4
- Mosquitto Versiyonu: 2.0.21
- Kurulum Tarihi: 2025-11-12

**Network Bilgileri:**
- Raspberry Pi IP: 192.168.1.132
- MQTT Port: 1883 (TCP)
- WebSocket Port: 9001 (WS)

**Servis Durumu:**
```
● mosquitto.service - Mosquitto MQTT Broker
     Loaded: loaded (/usr/lib/systemd/system/mosquitto.service; enabled)
     Active: active (running)
```

## İletişim ve Destek

Sorun yaşarsanız:
1. Log dosyalarını kontrol edin (`journalctl -u mosquitto`)
2. Yapılandırma dosyasını test edin (`mosquitto -c /etc/mosquitto/mosquitto.conf -v`)
3. GitHub Issues: https://github.com/eclipse/mosquitto/issues
4. Kuvoz Proje Deposu: (proje repo linki)

---

**Son Güncelleme:** 2025-11-12
**Durum:** Aktif ve Çalışıyor ✅
