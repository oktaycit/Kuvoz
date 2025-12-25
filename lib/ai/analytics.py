import logging
import collections
import numpy as np

logger = logging.getLogger(__name__)

class AnalyticsEngine:
    def __init__(self, window_size=60):
        # Keep last N readings (e.g., 60 readings * 5s = 5 mins history)
        self.window_size = window_size
        self.history = {
            'temperature': collections.deque(maxlen=window_size),
            'humidity': collections.deque(maxlen=window_size),
            'oxygen': collections.deque(maxlen=window_size)
        }
        self.anomalies = []

    def add_reading(self, sensor_type, value):
        if value is not None and isinstance(value, (int, float)):
            self.history[sensor_type].append(value)

    def analyze(self, current_state):
        """
        Analyze current data for anomalies.
        current_state: dict containing current actuator states (e.g., {'heater': True})
        """
        self.anomalies = []
        
        # 1. Check Temperature vs Heater
        if current_state.get('heater_on', False):
            # If heater is on, temperature should be stable or rising
            temps = list(self.history['temperature'])
            if len(temps) > 10:
                # Check trend of last 10 readings
                recent_trend = np.polyfit(range(10), temps[-10:], 1)[0]
                if recent_trend < -0.05: # Dropping significantly while heater is ON
                    self.anomalies.append("⚠️ Isıtıcı açık ama sıcaklık düşüyor! Sistem kontrolü gerekli.")
                elif recent_trend > 0.2: # Rising too fast
                    self.anomalies.append("⚠️ Sıcaklık çok hızlı yükseliyor! Isıtıcı kontrolü önerilir.")
        
        # 2. Check Temperature Range
        temps = list(self.history['temperature'])
        if len(temps) > 0:
            current_temp = temps[-1]
            if current_temp > 40:
                self.anomalies.append("🔥 KRİTİK: Sıcaklık 40°C'nin üzerinde! Acil müdahale gerekli!")
            elif current_temp < 15:
                self.anomalies.append("❄️ UYARI: Sıcaklık 15°C'nin altında! Isıtma sistemi kontrolü önerilir.")
            elif current_temp > 35:
                self.anomalies.append("⚠️ Sıcaklık yüksek (>35°C). İzleme önerilir.")

        # 3. Check Oxygen Drop
        o2_levels = list(self.history['oxygen'])
        if len(o2_levels) > 5:
            current_o2 = o2_levels[-1]
            # Sudden drop check
            if current_o2 < o2_levels[-5] * 0.95: # %5 drop in short time
                self.anomalies.append("🌬️ Oksijen seviyesinde ani düşüş tespit edildi!")
            
            # Critical oxygen level
            if current_o2 < 18:
                self.anomalies.append("❗ KRİTİK: Oksijen seviyesi %18'in altında! Hemen havalandırma yapın!")
            elif current_o2 < 19.5:
                self.anomalies.append("⚠️ Oksijen seviyesi düşük (<%19.5). Ventilasyon kontrolü önerilir.")

        # 4. Check Humidity
        humidity_levels = list(self.history['humidity'])
        if len(humidity_levels) > 0:
            current_humidity = humidity_levels[-1]
            if current_humidity > 80:
                self.anomalies.append("💧 Nem seviyesi çok yüksek (>%80). Havalandırma önerilir.")
            elif current_humidity < 30:
                self.anomalies.append("🏜️ Nem seviyesi çok düşük (<%30). Nemlendirme gerekebilir.")
        
        # 5. Check for unstable readings (high variance)
        if len(temps) > 10:
            recent_temps = temps[-10:]
            variance = np.var(recent_temps)
            if variance > 4.0: # Temperature varying more than ±2°C
                self.anomalies.append("📊 Sıcaklık değerleri dengesiz. Isıtma sistemi ayarları kontrol edilmeli.")

        # 6. Check humidity stability
        if len(humidity_levels) > 10:
            recent_humidity = humidity_levels[-10:]
            hum_variance = np.var(recent_humidity)
            if hum_variance > 100: # Humidity varying significantly
                self.anomalies.append("💦 Nem seviyesi dengesiz. Nem kontrol sistemi ayarları gözden geçirilmeli.")

        return self.anomalies

    def get_status(self):
        return {
            "anomalies": self.anomalies,
            "data_points": {k: len(v) for k, v in self.history.items()}
        }
