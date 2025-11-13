# Kuvoz Mobil Uygulama - MQTT Kontrol Sistemi Planı

## 📱 Proje Genel Bakış

**Platform:** React Native (iOS & Android)  
**Backend İletişim:** MQTT Protocol  
**MQTT Broker:** Mosquitto (Raspberry Pi üzerinde)  
**Mevcut Sistem:** Flask Web Server + Socket.IO  
**Hedef:** Veteriner hekimlerin uzaktan hasta takibi ve cihaz kontrolü

---

## 🏗️ Mimari Tasarım

### Sistem Bileşenleri

```
┌─────────────────────────────────────────────────────────────┐
│                    Mobil Uygulama (React Native)            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Dashboard   │  │   Controls   │  │   Settings   │      │
│  │  (Sensörler) │  │  (Butonlar)  │  │  (Ayarlar)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│           │                 │                 │             │
│           └─────────────────┴─────────────────┘             │
│                            │                                │
│                     MQTT Client                             │
│                    (react-native-mqtt)                      │
└─────────────────────────────┬───────────────────────────────┘
                              │ TLS/SSL
                              │ QoS 1-2
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              MQTT Broker (Mosquitto @ Raspberry Pi)         │
│  ┌──────────────────────────────────────────────────┐       │
│  │  Topics:                                          │       │
│  │  - kuvoz/sensors/+       (temp, hum, oxygen)     │       │
│  │  - kuvoz/controls/+      (buttons, sliders)      │       │
│  │  - kuvoz/status          (system status)         │       │
│  │  - kuvoz/timers/+        (nebulizer, ozone)      │       │
│  │  - kuvoz/commands        (remote commands)       │       │
│  └──────────────────────────────────────────────────┘       │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│         MQTT Bridge Service (Python @ Raspberry Pi)         │
│  ┌──────────────────────────────────────────────────┐       │
│  │  - MQTT Subscriber/Publisher                     │       │
│  │  - GPIO Controller                               │       │
│  │  - Sensor Reader (DHT22, Oxygen)                 │       │
│  │  - Settings Manager (Failure.dat)                │       │
│  │  - State Synchronization                         │       │
│  └──────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Geliştirme Aşamaları

### **Faz 1: MQTT Broker Kurulumu (1-2 gün)**

#### Mosquitto Kurulum

```bash
# Raspberry Pi üzerinde Mosquitto kurulumu
sudo apt update
sudo apt install mosquitto mosquitto-clients -y
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

#### MQTT Konfigürasyonu

**Dosya:** `/etc/mosquitto/conf.d/kuvoz.conf`

```conf
# Listener ayarları
listener 1883 0.0.0.0
protocol mqtt

# WebSocket desteği (web arayüzü için)
listener 9001
protocol websockets

# Authentication
allow_anonymous false
password_file /etc/mosquitto/passwd

# Persistence
persistence true
persistence_location /var/lib/mosquitto/

# Logging
log_dest file /var/log/mosquitto/mosquitto.log
log_type all

# QoS ayarları
max_qos 2
```

#### SSL/TLS Güvenlik (Opsiyonel - Üretim için zorunlu)

```bash
# Self-signed sertifika oluştur
sudo openssl req -new -x509 -days 365 -extensions v3_ca \
  -keyout /etc/mosquitto/certs/ca.key \
  -out /etc/mosquitto/certs/ca.crt

# Server sertifikası
sudo openssl genrsa -out /etc/mosquitto/certs/server.key 2048
sudo openssl req -new -key /etc/mosquitto/certs/server.key \
  -out /etc/mosquitto/certs/server.csr
sudo openssl x509 -req -in /etc/mosquitto/certs/server.csr \
  -CA /etc/mosquitto/certs/ca.crt \
  -CAkey /etc/mosquitto/certs/ca.key \
  -CAcreateserial -out /etc/mosquitto/certs/server.crt -days 365
```

#### Kullanıcı Oluşturma

```bash
# MQTT kullanıcıları
sudo mosquitto_passwd -c /etc/mosquitto/passwd veteriner
sudo mosquitto_passwd /etc/mosquitto/passwd mobile_app
sudo mosquitto_passwd /etc/mosquitto/passwd web_interface
```

---

### **Faz 2: MQTT Bridge Service (Python) (3-5 gün)**

#### Servis Yapısı

**Dosya:** `mqtt_bridge.py`

```python
#!/usr/bin/env python3
"""
Kuvoz MQTT Bridge Service
Connects MQTT broker with GPIO hardware and sensors
"""

import paho.mqtt.client as mqtt
import json
import time
import logging
from threading import Thread
import RPi.GPIO as GPIO
from lib.DHT_Native import read_dht_sensor
from lib.DFRobot_Oxygen import DFRobot_Oxygen_IIC

# MQTT Configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_USER = "web_interface"
MQTT_PASSWORD = "your_secure_password"
MQTT_CLIENT_ID = "kuvoz_bridge"

# MQTT Topics
TOPIC_SENSORS_TEMP = "kuvoz/sensors/temperature"
TOPIC_SENSORS_HUM = "kuvoz/sensors/humidity"
TOPIC_SENSORS_OXY = "kuvoz/sensors/oxygen"
TOPIC_CONTROLS_BUTTON = "kuvoz/controls/button/#"
TOPIC_CONTROLS_SLIDER = "kuvoz/controls/slider/#"
TOPIC_STATUS = "kuvoz/status"
TOPIC_TIMERS = "kuvoz/timers/#"
TOPIC_COMMANDS = "kuvoz/commands"

# GPIO Pin Mapping
BUTTON_PINS = {
    'b1': 5,   # Lighting
    'b2': 6,   # Nebulizer
    'b3': 13,  # Humidity Control
    'b4': 16,  # Carbon Heater
    'b5': 19,  # IR Heater
    'b6': 20,  # Fan
    'b7': 21,  # UV Light
    'b8': 26   # Ozone
}

DHT_PIN = 15

class KuvozMQTTBridge:
    def __init__(self):
        self.client = mqtt.Client(MQTT_CLIENT_ID)
        self.client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        self.button_states = {k: False for k in BUTTON_PINS.keys()}
        self.gpio_outputs = {k: None for k in BUTTON_PINS.keys()}
        self.slider_values = {}
        self.sensor_data = {}
        
        self.init_gpio()
        
    def init_gpio(self):
        """Initialize GPIO pins"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        for button, pin in BUTTON_PINS.items():
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.HIGH)  # Relay OFF (active LOW)
            
        logging.info("GPIO initialized")
        
    def on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            logging.info("Connected to MQTT Broker")
            # Subscribe to control topics
            client.subscribe(TOPIC_CONTROLS_BUTTON)
            client.subscribe(TOPIC_CONTROLS_SLIDER)
            client.subscribe(TOPIC_COMMANDS)
            
            # Publish initial status
            self.publish_status()
        else:
            logging.error(f"MQTT Connection failed: {rc}")
            
    def on_message(self, client, userdata, msg):
        """MQTT message callback"""
        topic = msg.topic
        payload = msg.payload.decode()
        
        try:
            data = json.loads(payload)
            
            # Button control
            if topic.startswith("kuvoz/controls/button/"):
                button_name = topic.split("/")[-1]
                self.handle_button_control(button_name, data)
                
            # Slider control
            elif topic.startswith("kuvoz/controls/slider/"):
                slider_name = topic.split("/")[-1]
                self.handle_slider_control(slider_name, data)
                
            # Remote commands
            elif topic == "kuvoz/commands":
                self.handle_command(data)
                
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON: {payload}")
            
    def handle_button_control(self, button_name, data):
        """Handle button toggle command"""
        if button_name in BUTTON_PINS:
            state = data.get('state', False)
            pin = BUTTON_PINS[button_name]
            
            # Update state
            self.button_states[button_name] = state
            
            # Control GPIO (active LOW)
            gpio_value = GPIO.LOW if state else GPIO.HIGH
            GPIO.output(pin, gpio_value)
            self.gpio_outputs[button_name] = state
            
            logging.info(f"Button {button_name}: {state}")
            
            # Publish confirmation
            self.client.publish(
                f"kuvoz/controls/button/{button_name}/status",
                json.dumps({'state': state, 'gpio': state}),
                qos=1,
                retain=True
            )
            
    def handle_slider_control(self, slider_name, data):
        """Handle slider value change"""
        value = data.get('value')
        self.slider_values[slider_name] = value
        
        logging.info(f"Slider {slider_name}: {value}")
        
        # Publish confirmation
        self.client.publish(
            f"kuvoz/controls/slider/{slider_name}/status",
            json.dumps({'value': value}),
            qos=1,
            retain=True
        )
        
    def handle_command(self, data):
        """Handle system commands"""
        cmd = data.get('command')
        
        if cmd == 'get_status':
            self.publish_status()
        elif cmd == 'restart':
            logging.info("Restart command received")
            # Implement restart logic
        elif cmd == 'save_settings':
            logging.info("Save settings command received")
            # Implement settings save
            
    def read_sensors(self):
        """Read sensor data and publish"""
        while True:
            try:
                # Read DHT22
                dht_result = read_dht_sensor(DHT_PIN)
                if dht_result['success']:
                    temp = dht_result['temperature']
                    hum = dht_result['humidity']
                    
                    # Publish temperature
                    self.client.publish(
                        TOPIC_SENSORS_TEMP,
                        json.dumps({
                            'value': temp,
                            'status': 'DHT22 GPIO15',
                            'timestamp': time.time()
                        }),
                        qos=1
                    )
                    
                    # Publish humidity
                    self.client.publish(
                        TOPIC_SENSORS_HUM,
                        json.dumps({
                            'value': hum,
                            'status': 'DHT22 GPIO15',
                            'timestamp': time.time()
                        }),
                        qos=1
                    )
                    
                # Read Oxygen sensor (if available)
                try:
                    oxygen_sensor = DFRobot_Oxygen_IIC(1, 0x70)
                    oxy_value = oxygen_sensor.get_oxygen_data(20)
                    
                    self.client.publish(
                        TOPIC_SENSORS_OXY,
                        json.dumps({
                            'value': round(oxy_value, 1),
                            'status': 'OK',
                            'timestamp': time.time()
                        }),
                        qos=1
                    )
                except:
                    pass
                    
            except Exception as e:
                logging.error(f"Sensor read error: {e}")
                
            time.sleep(5)  # Read every 5 seconds
            
    def publish_status(self):
        """Publish system status"""
        status = {
            'buttons': self.button_states,
            'gpio_outputs': self.gpio_outputs,
            'sliders': self.slider_values,
            'timestamp': time.time(),
            'online': True
        }
        
        self.client.publish(
            TOPIC_STATUS,
            json.dumps(status),
            qos=1,
            retain=True
        )
        
    def run(self):
        """Start MQTT bridge"""
        # Connect to MQTT broker
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        # Start sensor reading thread
        sensor_thread = Thread(target=self.read_sensors, daemon=True)
        sensor_thread.start()
        
        # Start MQTT loop
        self.client.loop_forever()
        
    def cleanup(self):
        """Cleanup on exit"""
        GPIO.cleanup()
        self.client.disconnect()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    bridge = KuvozMQTTBridge()
    
    try:
        bridge.run()
    except KeyboardInterrupt:
        logging.info("Shutting down...")
        bridge.cleanup()
```

#### Systemd Service

**Dosya:** `/etc/systemd/system/kuvoz-mqtt.service`

```ini
[Unit]
Description=Kuvoz MQTT Bridge Service
After=network.target mosquitto.service
Requires=mosquitto.service

[Service]
Type=simple
User=oktay
WorkingDirectory=/home/oktay/kuvoz
ExecStart=/usr/bin/python3 /home/oktay/kuvoz/mqtt_bridge.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

---

### **Faz 3: React Native Mobil Uygulama (7-10 gün)**

#### Proje Yapısı

```
kuvoz-mobile/
├── src/
│   ├── components/
│   │   ├── SensorCard.tsx
│   │   ├── ControlButton.tsx
│   │   ├── SliderControl.tsx
│   │   ├── TimerDisplay.tsx
│   │   └── StatusIndicator.tsx
│   ├── screens/
│   │   ├── DashboardScreen.tsx
│   │   ├── ControlsScreen.tsx
│   │   ├── SettingsScreen.tsx
│   │   ├── LoginScreen.tsx
│   │   └── HistoryScreen.tsx
│   ├── services/
│   │   ├── MQTTService.ts
│   │   ├── AuthService.ts
│   │   └── StorageService.ts
│   ├── store/
│   │   ├── slices/
│   │   │   ├── sensorsSlice.ts
│   │   │   ├── controlsSlice.ts
│   │   │   └── authSlice.ts
│   │   └── store.ts
│   ├── types/
│   │   ├── mqtt.types.ts
│   │   ├── sensor.types.ts
│   │   └── control.types.ts
│   ├── utils/
│   │   ├── constants.ts
│   │   └── helpers.ts
│   ├── navigation/
│   │   └── AppNavigator.tsx
│   └── App.tsx
├── android/
├── ios/
├── package.json
└── tsconfig.json
```

#### Temel Paketler

**package.json**

```json
{
  "name": "kuvoz-mobile",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.2.0",
    "react-native": "^0.72.0",
    "@react-navigation/native": "^6.1.0",
    "@react-navigation/bottom-tabs": "^6.5.0",
    "@react-navigation/stack": "^6.3.0",
    "@reduxjs/toolkit": "^1.9.0",
    "react-redux": "^8.1.0",
    "paho-mqtt": "^1.1.0",
    "@react-native-async-storage/async-storage": "^1.19.0",
    "react-native-vector-icons": "^10.0.0",
    "react-native-gesture-handler": "^2.12.0",
    "react-native-reanimated": "^3.4.0",
    "react-native-safe-area-context": "^4.7.0",
    "react-native-screens": "^3.25.0",
    "axios": "^1.5.0",
    "date-fns": "^2.30.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-native": "^0.72.0",
    "typescript": "^5.0.0",
    "@typescript-eslint/eslint-plugin": "^6.0.0",
    "@typescript-eslint/parser": "^6.0.0"
  }
}
```

#### MQTT Service

**src/services/MQTTService.ts**

```typescript
import Paho from 'paho-mqtt';

interface MQTTConfig {
  host: string;
  port: number;
  username: string;
  password: string;
  clientId: string;
  useSSL: boolean;
}

type MessageCallback = (topic: string, payload: any) => void;

class MQTTService {
  private client: Paho.Client | null = null;
  private config: MQTTConfig | null = null;
  private messageCallbacks: MessageCallback[] = [];
  private connected: boolean = false;

  connect(config: MQTTConfig): Promise<void> {
    return new Promise((resolve, reject) => {
      this.config = config;
      
      this.client = new Paho.Client(
        config.host,
        config.port,
        config.clientId
      );

      this.client.onConnectionLost = this.onConnectionLost.bind(this);
      this.client.onMessageArrived = this.onMessageArrived.bind(this);

      const connectOptions = {
        userName: config.username,
        password: config.password,
        useSSL: config.useSSL,
        onSuccess: () => {
          console.log('MQTT Connected');
          this.connected = true;
          this.subscribeToTopics();
          resolve();
        },
        onFailure: (error: any) => {
          console.error('MQTT Connection failed:', error);
          this.connected = false;
          reject(error);
        },
      };

      this.client.connect(connectOptions);
    });
  }

  private subscribeToTopics() {
    if (!this.client) return;

    const topics = [
      'kuvoz/sensors/#',
      'kuvoz/controls/#',
      'kuvoz/status',
      'kuvoz/timers/#',
    ];

    topics.forEach(topic => {
      this.client!.subscribe(topic, {
        qos: 1,
        onSuccess: () => console.log(`Subscribed to ${topic}`),
        onFailure: (err) => console.error(`Subscribe failed: ${topic}`, err),
      });
    });
  }

  private onConnectionLost(response: any) {
    console.log('MQTT Connection lost:', response.errorMessage);
    this.connected = false;
    
    // Auto-reconnect
    setTimeout(() => {
      if (this.config) {
        this.connect(this.config).catch(console.error);
      }
    }, 5000);
  }

  private onMessageArrived(message: Paho.Message) {
    const topic = message.destinationName;
    const payloadString = message.payloadString;
    
    try {
      const payload = JSON.parse(payloadString);
      this.messageCallbacks.forEach(callback => {
        callback(topic, payload);
      });
    } catch (error) {
      console.error('Invalid JSON payload:', payloadString);
    }
  }

  onMessage(callback: MessageCallback) {
    this.messageCallbacks.push(callback);
  }

  publish(topic: string, payload: any, qos: number = 1) {
    if (!this.client || !this.connected) {
      console.error('MQTT not connected');
      return;
    }

    const message = new Paho.Message(JSON.stringify(payload));
    message.destinationName = topic;
    message.qos = qos;
    
    this.client.send(message);
  }

  toggleButton(buttonName: string, state: boolean) {
    this.publish(`kuvoz/controls/button/${buttonName}`, { state });
  }

  updateSlider(sliderName: string, value: number) {
    this.publish(`kuvoz/controls/slider/${sliderName}`, { value });
  }

  sendCommand(command: string, params?: any) {
    this.publish('kuvoz/commands', { command, ...params });
  }

  disconnect() {
    if (this.client && this.connected) {
      this.client.disconnect();
      this.connected = false;
    }
  }

  isConnected(): boolean {
    return this.connected;
  }
}

export default new MQTTService();
```

#### Dashboard Screen

**src/screens/DashboardScreen.tsx**

```typescript
import React, { useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
} from 'react-native';
import { useSelector, useDispatch } from 'react-redux';
import SensorCard from '../components/SensorCard';
import StatusIndicator from '../components/StatusIndicator';
import { RootState } from '../store/store';
import MQTTService from '../services/MQTTService';

const DashboardScreen: React.FC = () => {
  const dispatch = useDispatch();
  const { temperature, humidity, oxygen } = useSelector(
    (state: RootState) => state.sensors
  );
  const { connected } = useSelector((state: RootState) => state.mqtt);
  const [refreshing, setRefreshing] = React.useState(false);

  const onRefresh = React.useCallback(() => {
    setRefreshing(true);
    MQTTService.sendCommand('get_status');
    setTimeout(() => setRefreshing(false), 1000);
  }, []);

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      <View style={styles.header}>
        <Text style={styles.title}>Kuvoz Veteriner Ünitesi</Text>
        <StatusIndicator connected={connected} />
      </View>

      <View style={styles.sensorGrid}>
        <SensorCard
          title="Sıcaklık"
          value={temperature.value}
          unit="°C"
          status={temperature.status}
          icon="thermometer"
        />
        <SensorCard
          title="Nem"
          value={humidity.value}
          unit="%"
          status={humidity.status}
          icon="water"
        />
        <SensorCard
          title="Oksijen"
          value={oxygen.value}
          unit="%"
          status={oxygen.status}
          icon="wind"
        />
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    padding: 20,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  sensorGrid: {
    padding: 10,
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
});

export default DashboardScreen;
```

---

### **Faz 4: Entegrasyon ve Test (3-4 gün)**

#### Test Senaryoları

1. **MQTT Bağlantı Testi**
   - Broker bağlantısı
   - Topic subscription
   - Mesaj publish/subscribe

2. **Sensör Veri Testi**
   - Real-time sensor updates
   - Data accuracy
   - Update frequency

3. **Kontrol Testi**
   - Button toggle
   - Slider control
   - GPIO response

4. **Güvenlik Testi**
   - Authentication
   - SSL/TLS encryption
   - Authorization

5. **Network Testi**
   - Connection loss/recovery
   - Offline mode
   - Data persistence

---

## 📊 MQTT Topic Yapısı

### Topic Hierarchy

```
kuvoz/
├── sensors/
│   ├── temperature          # Sıcaklık sensörü
│   ├── humidity             # Nem sensörü
│   └── oxygen               # Oksijen sensörü
├── controls/
│   ├── button/
│   │   ├── b1/              # Aydınlatma
│   │   ├── b2/              # Nebülizatör
│   │   ├── b3/              # Nem Kontrol
│   │   ├── b4/              # Karbon Isıtıcı
│   │   ├── b5/              # IR Isıtıcı
│   │   ├── b6/              # Fan
│   │   ├── b7/              # UV Işığı
│   │   └── b8/              # Ozon
│   └── slider/
│       ├── sld1/            # Slider değerleri
│       └── ...
├── status                   # Sistem durumu
├── timers/
│   ├── nebulizer/           # Nebülizatör timer
│   └── ozone/               # Ozon timer
└── commands                 # Uzaktan komutlar
```

### Mesaj Formatları

#### Sensor Data

```json
{
  "value": 22.5,
  "status": "DHT22 GPIO15",
  "timestamp": 1699876543.123
}
```

#### Button Control

```json
{
  "state": true,
  "timestamp": 1699876543.123
}
```

#### Slider Control

```json
{
  "value": 28,
  "min": 20,
  "max": 40,
  "timestamp": 1699876543.123
}
```

#### System Status

```json
{
  "buttons": {
    "b1": true,
    "b2": false,
    ...
  },
  "gpio_outputs": {
    "b1": true,
    ...
  },
  "sliders": {
    "sld1": 30,
    ...
  },
  "timestamp": 1699876543.123,
  "online": true
}
```

---

## 🔐 Güvenlik

### Authentication & Authorization

1. **MQTT Username/Password**
   - Unique credentials per device/user
   - Strong password policy
   - Regular password rotation

2. **SSL/TLS Encryption**
   - Certificate-based authentication
   - Encrypted data transmission
   - Certificate pinning in mobile app

3. **Access Control**
   - Topic-based permissions
   - Role-based access (veteriner, teknisyen, admin)
   - Action logging

### Önerilen Güvenlik Katmanları

```
┌─────────────────────────────────────┐
│   Application Layer Security       │
│   - User authentication             │
│   - Session management              │
│   - Input validation                │
└─────────────────────────────────────┘
           ▼
┌─────────────────────────────────────┐
│   MQTT Layer Security               │
│   - Username/Password auth          │
│   - SSL/TLS encryption              │
│   - ACL (Access Control Lists)      │
└─────────────────────────────────────┘
           ▼
┌─────────────────────────────────────┐
│   Network Layer Security            │
│   - Firewall rules                  │
│   - VPN (for remote access)         │
│   - Port restrictions               │
└─────────────────────────────────────┘
```

---

## 📱 Mobil Uygulama Özellikleri

### Must-Have Features (MVP)

- ✅ Real-time sensör gösterimi (sıcaklık, nem, oksijen)
- ✅ Cihaz kontrolleri (8 buton)
- ✅ Slider kontrolleri (hedef değerler)
- ✅ Bağlantı durumu göstergesi
- ✅ Push notifications (kritik alarmlar)
- ✅ Login/Authentication
- ✅ Offline mode support

### Nice-to-Have Features (V2)

- 📊 Grafik ve trendler (24 saat geçmiş)
- 📝 Hasta kayıt sistemi
- 🔔 Alarm konfigürasyonu
- 📸 Kamera entegrasyonu
- 📍 Multi-ünite yönetimi
- 🌐 Cloud sync
- 🔊 Sesli komutlar

---

## 🚀 Deployment Stratejisi

### Development Environment

```bash
# Mosquitto test broker (local)
mosquitto -v

# MQTT Bridge (development)
python3 mqtt_bridge.py

# React Native (development)
npx react-native run-android
npx react-native run-ios
```

### Production Environment

```bash
# Mosquitto with SSL
sudo systemctl start mosquitto

# MQTT Bridge service
sudo systemctl start kuvoz-mqtt

# Mobile app deployment
# - Android: Google Play Store
# - iOS: Apple App Store
```

---

## 📈 Performans Metrikleri

### Hedef Değerler

- **MQTT Latency:** < 100ms (local network)
- **Sensor Update Frequency:** 5 saniye
- **Button Response Time:** < 200ms
- **App Launch Time:** < 3 saniye
- **Battery Consumption:** < 5% per hour (background)

### Monitoring

```python
# MQTT mesaj istatistikleri
{
  "messages_published": 12543,
  "messages_received": 8921,
  "average_latency_ms": 45,
  "connection_uptime": "99.8%"
}
```

---

## 🔧 Bakım ve Güncellemeler

### MQTT Broker Bakımı

```bash
# Log kontrolü
sudo tail -f /var/log/mosquitto/mosquitto.log

# Bağlı client'ları görüntüle
mosquitto_sub -h localhost -t '$SYS/broker/clients/active' -u admin -P password

# Mesaj istatistikleri
mosquitto_sub -h localhost -t '$SYS/#' -u admin -P password
```

### Mobil Uygulama Güncellemeleri

- **OTA Updates:** CodePush (React Native)
- **Version Control:** Semantic versioning
- **Beta Testing:** TestFlight (iOS), Google Play Beta (Android)

---

## 📚 Dokümantasyon

### API Dokümantasyonu

- MQTT Topic Reference
- Message Format Specifications
- Error Codes
- Integration Guide

### Kullanıcı Kılavuzu

- Kurulum adımları
- Ekran görüntüleri
- Troubleshooting
- SSS

---

## 💰 Maliyet Tahmini

### Geliştirme Maliyeti (Zaman)

| Faz | Süre | Açıklama |
|-----|------|----------|
| MQTT Broker Kurulum | 1-2 gün | Mosquitto, SSL, config |
| MQTT Bridge Service | 3-5 gün | Python service, GPIO |
| React Native App | 7-10 gün | UI, MQTT client, features |
| Test & Debug | 3-4 gün | Integration, performance |
| Deployment | 1-2 gün | Store submission, docs |
| **TOPLAM** | **15-23 gün** | **~3-5 hafta** |

### İşletme Maliyeti

- **MQTT Broker:** $0 (self-hosted)
- **Cloud Backup (opsiyonel):** $5-10/ay
- **SSL Certificates:** $0 (Let's Encrypt) veya $50-100/yıl
- **App Store Fees:** $99/yıl (Apple), $25 one-time (Google)

---

## ✅ Kontrol Listesi

### Başlamadan Önce

- [ ] Raspberry Pi hazır ve çalışıyor
- [ ] Mevcut web interface çalışıyor
- [ ] Network yapılandırması tamamlandı
- [ ] Geliştirme araçları kuruldu (Node.js, React Native CLI)

### Geliştirme Aşaması

- [ ] Mosquitto kuruldu ve yapılandırıldı
- [ ] MQTT Bridge servisi tamamlandı
- [ ] React Native proje oluşturuldu
- [ ] MQTT client entegrasyonu yapıldı
- [ ] UI componentleri geliştirildi
- [ ] State management (Redux) kuruldu

### Test Aşaması

- [ ] Unit testler yazıldı
- [ ] Integration testler tamamlandı
- [ ] Performance testler yapıldı
- [ ] Security audit tamamlandı
- [ ] Beta test kullanıcıları test etti

### Deployment Aşaması

- [ ] Production MQTT broker yapılandırıldı
- [ ] SSL sertifikaları kuruldu
- [ ] Mobile app build alındı
- [ ] App store submission yapıldı
- [ ] Dokümantasyon tamamlandı

---

## 🎯 Sonuç

Bu plan, Kuvoz veteriner rehabilitasyon ünitesi için MQTT tabanlı mobil kontrol sisteminin tüm aşamalarını kapsamaktadır. Güvenli, ölçeklenebilir ve kullanıcı dostu bir çözüm sunmayı hedeflemektedir.

**İletişim:** Oktay Çit (@oktaycit)  
**Tarih:** 13 Kasım 2025  
**Versiyon:** 1.0
