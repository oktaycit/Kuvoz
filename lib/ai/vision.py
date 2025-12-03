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

# Try to import picamera2 for Raspberry Pi native camera support
try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False


class VisionEngine:
    def __init__(self, resolution=(640, 480), fps=5):
        self.resolution = resolution
        self.target_fps = fps
        self.running = False
        self.camera = None
        self.camera_type = None  # 'picamera2' or 'opencv'
        self.last_frame = None
        self.status = "IDLE"
        self.activity_level = 0.0
        self.latest_jpeg = None
        self.lock = threading.Lock()

    def start(self):
        if not OPENCV_AVAILABLE:
            return False
        
        # Strategy 1: Try picamera2 (Raspberry Pi native, modern approach)
        if PICAMERA2_AVAILABLE:
            try:
                logger.info("Attempting to initialize camera with picamera2...")
                picam = Picamera2()
                
                # Configure camera: main stream for capture
                config = picam.create_still_configuration(
                    main={"size": self.resolution, "format": "BGR888"},
                    buffer_count=2
                )
                picam.configure(config)
                picam.start()
                
                # Test capture
                time.sleep(1)  # Allow camera to warm up
                test_frame = picam.capture_array()
                
                if test_frame is not None and test_frame.shape[0] > 0:
                    logger.info(f"✅ Camera initialized successfully with picamera2")
                    logger.info(f"   Resolution: {self.resolution}, FPS: {self.target_fps}")
                    self.camera = picam
                    self.camera_type = 'picamera2'
                    self.running = True
                    logger.info("🎥 Vision Engine started (picamera2).")
                    return True
                else:
                    logger.warning("picamera2 opened but failed to capture test frame")
                    picam.stop()
                    picam.close()
                    
            except Exception as e:
                logger.warning(f"picamera2 initialization failed: {e}")
                logger.info("Falling back to OpenCV VideoCapture...")
        
        # Strategy 2: Fallback to OpenCV VideoCapture (for non-RPi or if picamera2 fails)
        try:
            logger.info("Initializing camera with OpenCV VideoCapture...")
            
            # Camera indices and backends to try
            strategies = [
                # (Name, Index, Backend)
                ("Index 0 with V4L2", 0, cv2.CAP_V4L2),
                ("Index 0 with default backend", 0, cv2.CAP_ANY),
                ("Index 1 with V4L2", 1, cv2.CAP_V4L2),
                ("Index 1 with default backend", 1, cv2.CAP_ANY),
            ]
            
            # Configurations to try: (FourCC, Width, Height)
            configs = [
                ('MJPG', 640, 480),
                ('YUYV', 640, 480),
                ('MJPG', 320, 240),
                (None, 640, 480) # Default
            ]

            for name, idx, backend in strategies:
                logger.info(f"Attempting: {name}...\"")
                
                try:
                    cap = cv2.VideoCapture(idx, backend)
                    if not cap.isOpened():
                        logger.warning(f"  ❌ Could not open camera {name}")
                        continue
                    
                    # Try different format configurations
                    for fourcc, w, h in configs:
                        config_desc = f"{name} - {fourcc if fourcc else 'Default'} {w}x{h}"
                        logger.info(f"  Testing: {config_desc}")
                        
                        # Set camera properties
                        if fourcc:
                            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
                        cap.set(cv2.CAP_PROP_FPS, self.target_fps)
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer
                        
                        # Test if we can actually read frames
                        if self._test_camera_read(cap):
                            logger.info(f"✅ Camera initialized successfully: {config_desc}")
                            self.camera = cap
                            self.camera_type = 'opencv'
                            self.running = True
                            logger.info("🎥 Vision Engine started (OpenCV).")
                            return True
                        else:
                            logger.debug(f"  ❌ Could not read frames from {config_desc}")
                    
                    # If no config worked, release and try next strategy
                    cap.release()
                    logger.debug(f"  No working configuration for {name}")
                    
                except Exception as e:
                    logger.error(f"  Exception with {name}: {e}")

            logger.error("Could not open any camera after trying all configurations.")
            return False
        except Exception as e:
            logger.error(f"Error starting Vision Engine: {e}")
            return False

    def _test_camera_read(self, cap):
        """Helper to test if camera can actually read frames"""
        for _ in range(5):
            ret, _ = cap.read()
            if ret:
                return True
            time.sleep(0.1)
        return False

    def stop(self):
        self.running = False
        if self.camera:
            if self.camera_type == 'picamera2':
                try:
                    self.camera.stop()
                    self.camera.close()
                except:
                    pass
            else:  # opencv
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

        # Capture frame based on camera type
        try:
            if self.camera_type == 'picamera2':
                frame = self.camera.capture_array()
                if frame is None or frame.shape[0] == 0:
                    logger.warning("Failed to capture frame from picamera2")
                    return
            else:  # opencv
                ret, frame = self.camera.read()
                if not ret:
                    logger.warning("Failed to grab frame from OpenCV")
                    return
        except Exception as e:
            logger.error(f"Error capturing frame: {e}")
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
