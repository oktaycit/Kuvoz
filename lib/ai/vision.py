import logging
import time
import threading
import base64

logger = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    logger.warning("OpenCV/Numpy not found. Vision features disabled.")
    OPENCV_AVAILABLE = False

class VisionEngine:
    def __init__(self, resolution=(320, 240), fps=5):
        self.resolution = resolution
        self.target_fps = fps
        self.running = False
        self.camera = None
        self.last_frame = None
        self.status = "IDLE"
        self.activity_level = 0.0
        self.latest_jpeg = None
        self.lock = threading.Lock()

    def start(self):
        if not OPENCV_AVAILABLE:
            return False
        
        try:
            # Try to open camera (iterate indices if default fails)
            # Priority: Index 0 with V4L2, then Index 0 with ANY, then Index 1...
            
            camera_configs = [
                (0, cv2.CAP_V4L2, "Index 0 (V4L2)"),
                (0, cv2.CAP_ANY, "Index 0 (Default)"),
                (1, cv2.CAP_V4L2, "Index 1 (V4L2)"),
                (1, cv2.CAP_ANY, "Index 1 (Default)")
            ]

            for idx, backend, desc in camera_configs:
                logger.info(f"Attempting to open camera: {desc}")
                try:
                    self.camera = cv2.VideoCapture(idx, backend)
                    if self.camera.isOpened():
                        # Test read
                        ret, _ = self.camera.read()
                        if ret:
                            logger.info(f"Camera opened and verified successfully: {desc}")
                            break
                        else:
                            logger.warning(f"Camera opened but failed to read frame: {desc}")
                            self.camera.release()
                            self.camera = None
                    else:
                        logger.warning(f"Failed to open camera: {desc}")
                        if self.camera:
                            self.camera.release()
                            self.camera = None
                except Exception as e:
                    logger.error(f"Exception opening camera {desc}: {e}")
                    if self.camera:
                        self.camera.release()
                        self.camera = None
            
            if not self.camera or not self.camera.isOpened():
                logger.error("Could not open any camera after multiple attempts.")
                # Log diagnostic info
                try:
                    import subprocess
                    ls_video = subprocess.getoutput("ls -l /dev/video*")
                    logger.info(f"Available video devices:\n{ls_video}")
                except:
                    pass
                return False
            
            # Set camera properties for performance
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            self.camera.set(cv2.CAP_PROP_FPS, self.target_fps)
            
            self.running = True
            logger.info("Vision Engine started.")
            return True
        except Exception as e:
            logger.error(f"Error starting Vision Engine: {e}")
            return False

    def stop(self):
        self.running = False
        if self.camera:
            self.camera.release()
        logger.info("Vision Engine stopped.")

    def get_frame(self):
        with self.lock:
            return self.latest_jpeg

    def get_status(self):
        return {
            "status": self.status,
            "activity": round(self.activity_level, 2),
            "available": OPENCV_AVAILABLE and self.running
        }

    def process_frame(self):
        if not self.running or not self.camera:
            return

        ret, frame = self.camera.read()
        if not ret:
            logger.warning("Failed to grab frame")
            return

        # Resize for consistent processing speed
        frame = cv2.resize(frame, self.resolution)
        
        # Convert to grayscale for motion detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.last_frame is None:
            self.last_frame = gray
            return

        # Compute difference
        frame_delta = cv2.absdiff(self.last_frame, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        # Calculate movement score
        non_zero_count = cv2.countNonZero(thresh)
        total_pixels = self.resolution[0] * self.resolution[1]
        movement_ratio = (non_zero_count / total_pixels) * 100

        # Update status based on movement
        self.activity_level = movement_ratio
        if movement_ratio > 1.0: # Threshold %1
            self.status = "HAREKETLI"
        else:
            self.status = "DURGUN"

        self.last_frame = gray

        # Encode frame for web streaming (low quality for speed)
        _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
        with self.lock:
            self.latest_jpeg = base64.b64encode(buffer).decode('utf-8')
