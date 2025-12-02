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
                    self.anomalies.append("Isıtıcı açık ama sıcaklık düşüyor!")

        # 2. Check Oxygen Drop
        o2_levels = list(self.history['oxygen'])
        if len(o2_levels) > 5:
            # Sudden drop check
            if o2_levels[-1] < o2_levels[-5] * 0.95: # %5 drop in short time
                self.anomalies.append("Oksijen seviyesinde ani düşüş!")

        return self.anomalies

    def get_status(self):
        return {
            "anomalies": self.anomalies,
            "data_points": {k: len(v) for k, v in self.history.items()}
        }
