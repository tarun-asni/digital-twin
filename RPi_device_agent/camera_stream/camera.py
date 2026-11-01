import cv2
import threading
import logging
import os
import time

from .config import CAMERA_FPS

from .video_processor_utils import is_raspberry_pi

try:
    from picamera2 import Picamera2
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s")
logger = logging.getLogger("Camera")

class Camera:
    def __init__(self):
        self.lock = threading.Lock()
        self.use_picamera = is_raspberry_pi()
        self.zoom_factor = 1.0
        self.rotate_angle = 0
        self._apply_zoom = False
        self._apply_rotate = False
        self._rotate_code = None
        self.last_capture_time = 0
        self.fps_limit = CAMERA_FPS
        if self.use_picamera:
            try:
                self.picam2 = Picamera2()
                config = self.picam2.create_still_configuration(main={"size": (640, 480)})
                config = self.picam2.create_preview_configuration({'format': 'RGB888'}) # For natural colors
                self.picam2.configure(config)
                self.picam2.start()
                logger.info("PiCamera2 initialized and in use.")
            except Exception as e:
                logger.warning(f"Failed to initialize PiCamera2: {e}. Falling back to OpenCV webcam.")
                self._init_opencv()
        else:
            logger.info("Picamera2 not available. Using OpenCV webcam.")
            self._init_opencv()
            
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance        

    def _init_opencv(self):
         # /videos directory path relative to camera.py
        videos_dir = os.path.join(os.path.dirname(__file__), "videos")

        # Make sure the /videos dir exists (in case it's missing)
        os.makedirs(videos_dir, exist_ok=True)

        video_path = None
        if os.path.isdir(videos_dir):
            files = [f for f in os.listdir(videos_dir) if f.lower().endswith(".mp4")]
            if files:
                video_path = os.path.join(videos_dir, files[0])

        if video_path and os.path.exists(video_path):
            self.cap = cv2.VideoCapture(video_path)
            logger.info(f"Using video file: {video_path}")
        else:
            self.cap = cv2.VideoCapture(0)
            logger.info("No video file found in /videos, using webcam (device 0)")

        if not self.cap.isOpened():
            raise RuntimeError("Could not open video source. Check permissions or if another app is using it.")
        logger.info("OpenCV video source initialized.")

    def capture_array(self):
        # Step 1: Fast capture (no lock)
        now = time.time()
        min_interval = 1.0 / self.fps_limit
        if now - self.last_capture_time < min_interval:
            time.sleep(min_interval - (now - self.last_capture_time))
        self.last_capture_time = time.time()

        # Step 1: Fast capture
        frame = self._get_frame()

        # Step 2: Transformations
        with self.lock:
            if self._apply_zoom:
                frame = self._zoom_frame(frame, self.zoom_factor)
            if self._apply_rotate:
                frame = cv2.rotate(frame, self._rotate_code)

        return frame

    def release(self):
        with self.lock:
            if not self.use_picamera and self.cap.isOpened():
                self.cap.release()
                logger.info("Webcam released.")

    def update_zoom(self, zoom):
        with self.lock:
            self.zoom_factor = zoom
            self._apply_zoom = zoom != 1.0
    
    def update_rotation(self, angle):
        with self.lock:
            self.rotate_angle = angle
            self._apply_rotate = angle in (90, 180, 270)
            self._rotate_code = {
                90: cv2.ROTATE_90_CLOCKWISE,
                180: cv2.ROTATE_180,
                270: cv2.ROTATE_90_COUNTERCLOCKWISE
            }.get(angle, None)
    
    def _get_frame(self):
        if self.use_picamera:
            try:
                return self.picam2.capture_array()
            except Exception as e:
                logger.error(f"Failed to capture from PiCamera2: {e}")
                raise RuntimeError("Failed to read from PiCamera2.")
        else:
            if not self.cap.isOpened():
                logger.warning("Webcam is not open. Attempting to reopen.")
                self.cap = cv2.VideoCapture(0)
                if not self.cap.isOpened():
                    raise RuntimeError("Webcam failed to reopen.")

            ret, frame = self.cap.read()
            if not ret or frame is None:
                logger.warning("Frame not captured. Retrying...")
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    logger.error("Failed to read from video even after retry.")
                    raise RuntimeError("Failed to read from video.")
            return frame