import os
import cv2
import time
import threading
import logging
from .config import RECORDINGS_DIR, TIMESTAMP_FORMAT, DEVICE_ID
from .video_processor_utils import check_storage_and_cleanup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s")
logger = logging.getLogger("drone_recorder")

class DroneRecorder:
    def __init__(self, camera):

        if not self.__class__._initialized:
            self.__class__._initialized = True
            self.camera = camera
            self.record_dir = RECORDINGS_DIR
            self.fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = None
            self.record_start_time = 0
            self.is_recording = False
            self.recording_thread = None
            self.stop_event = threading.Event()

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance 
    
    def start_recording(self):
        if self.is_recording:
            logger.info("Drone recording is already active.")
            return False
        self.is_recording = True
        self.stop_event.clear()
        self.recording_thread = threading.Thread(target=self._record_loop, daemon=True)
        self.recording_thread.start()
        logger.info("Drone recording started.")
        return True

    def stop_recording(self):
        if not self.is_recording:
            logger.info("Drone recording is already inactive.")
            return False
        self.is_recording = False
        self.stop_event.set()
        if self.recording_thread:
            self.recording_thread.join(timeout=5)
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        logger.info("Drone recording stopped.")
        return True

    def _record_loop(self):
        while not self.stop_event.is_set():
            now = time.time()
            if self.video_writer is None or (now - self.record_start_time >= 30):
                if self.video_writer:
                    self.video_writer.release()
                    logger.info("Released previous drone video writer.")

                check_storage_and_cleanup()
                filename = os.path.join(self.record_dir, f"{time.strftime(TIMESTAMP_FORMAT)}_{DEVICE_ID}.mp4")

                frame = self.camera.capture_array()
                if frame is not None and frame.shape[0] > 0 and frame.shape[1] > 0:
                    h, w = frame.shape[:2]
                    self.video_writer = cv2.VideoWriter(filename, self.fourcc, 20.0, (w, h))
                    if not self.video_writer.isOpened():
                        logger.error(f"Drone video writer failed to open for {filename}. Dimensions: ({w}, {h}) Codec: {self.fourcc}")
                        self.video_writer = None
                        time.sleep(1)
                        continue
                    else:
                        logger.info(f"Started drone recording: {filename} with dimensions ({w}, {h})")
                else:
                    logger.warning("Attempted to start drone recording but frame was invalid. Skipping this segment.")
                    time.sleep(1)
                    continue

                self.record_start_time = now

            if self.video_writer:
                frame = self.camera.capture_array()
                if frame is not None:
                    try:
                        self.video_writer.write(frame)
                        logger.debug("Frame written to drone video")
                    except Exception as e:
                        logger.error(f"Error writing frame to drone video: {e}")
                        if self.video_writer:
                            self.video_writer.release()
                        self.video_writer = None
                else:
                    logger.debug("No frame available for drone recording.")

            # Control fps
            frame_write_time = time.time() - now
            expected_interval = 1.0 / self.camera.fps_limit
            if frame_write_time < expected_interval:
                time.sleep(expected_interval - frame_write_time)
