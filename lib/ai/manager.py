import logging
import threading
import time
from .vision import VisionEngine
from .analytics import AnalyticsEngine

logger = logging.getLogger(__name__)

class AIManager:
    def __init__(self):
        self.vision = VisionEngine()
        self.analytics = AnalyticsEngine()
        self.running = False
        self.started = False  # Track if AI has been started
        self.thread = None

    def start(self):
        if self.started:
            logger.warning("AI Manager already started, skipping")
            return True
        
        self.running = True
        # Start vision engine
        vision_started = self.vision.start()
        if vision_started:
            # Start a background thread to process frames periodically
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()
            self.started = True
            logger.info("✅ AI Manager started with camera")
            return True
        else:
            logger.error("❌ AI Manager failed to start - Camera not available")
            self.running = False
            return False

    def stop(self):
        if not self.started:
            logger.warning("AI Manager not started, skipping stop")
            return
        
        self.running = False
        self.started = False
        self.vision.stop()
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
        logger.info("✅ AI Manager stopped.")

    def _loop(self):
        while self.running:
            self.vision.process_frame()
            # Sleep to maintain target FPS (approximate)
            time.sleep(1.0 / self.vision.target_fps)

    def update_sensors(self, sensor_data, actuator_state):
        """
        Feed new sensor data to analytics engine.
        sensor_data: dict {'temperature': 25.0, ...}
        actuator_state: dict {'heater_on': True, ...}
        """
        if 'temperature' in sensor_data:
            self.analytics.add_reading('temperature', sensor_data['temperature'])
        if 'humidity' in sensor_data:
            self.analytics.add_reading('humidity', sensor_data['humidity'])
        if 'oxygen' in sensor_data:
            self.analytics.add_reading('oxygen', sensor_data['oxygen'])

        # Run analysis
        self.analytics.analyze(actuator_state)

    def get_update(self):
        """
        Get combined status for frontend.
        """
        vision_status = self.vision.get_status()
        analytics_status = self.analytics.get_status()
        
        return {
            "vision": vision_status,
            "analytics": analytics_status,
            "vitals": self.vision.get_vitals(),
            "frame": self.vision.get_frame() # Base64 encoded JPEG
        }
