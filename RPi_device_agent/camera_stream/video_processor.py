import os
import cv2
import time
import logging
import threading
import json
import queue

import numpy as np
from motpy import Detection, MultiObjectTracker

from datetime import datetime, timezone
from collections import deque
from .alert_manager import AlertManager
from .ptz.geo import estimate_alert_gps

from .config import (
    RECORDINGS_DIR, TIMESTAMP_FORMAT,
    check_object_detection, get_detection_classes, is_alert_enabled,
    get_time_zone
)
from .video_processor_utils import (
    check_storage_and_cleanup, 
    is_raspberry_pi, load_yolo_model
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s")
logger = logging.getLogger("video_processor")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PAYLOAD_PATH = os.path.join(BASE_DIR, "..", "field_unit_payloads", "camera.json")
DEVICE_NAME = os.getenv("DEVICE_NAME")

class VideoProcessor:
    def __init__(self, camera, model_path, frame_size=(640, 480), detection_size=256, zone=None):
        self.camera = camera
        self.is_rpi = is_raspberry_pi()
        self.model = load_yolo_model(model_path)
        self.classes = list(self.model.names.values())
        logger.info(f"Loaded classes: {self.classes}")
        self.frame_size = frame_size
        self.detection_size = detection_size
        
        self.session_active = False
        self.entry_time = None
        self.last_seen_time = None
        self.person_detected_start = None
        self.bbox = (0,)
        
        self.confidence_threshold = 0.45
        self.confidence_detected = 0
        self.entry_confirm_duration = 2.0
        self.exit_grace_duration = 8.0
        
        self.current_person_detected = False
        
        self.alert_manager = AlertManager()
        
        self.record_dir = RECORDINGS_DIR
        self.fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.video_writer = None
        self.record_start_time = time.time()
        self.raw_frame = None
        self.annotated_display_frame = None
        self.last_write_time = 0
        
        self.is_continuous_recording_active = threading.Event()
        self.is_continuous_recording_active.set()

        self.UNSAFE_CLASSES = get_detection_classes()
        self.detection_class = None

        self.ALERT_FPS = self.camera.fps_limit
        self.PRE_ENTRY_BUFFER_DURATION = 30
        self.RESTRICTED_ZONE_POST_EXIT_DURATION = 30
        self.SAFETY_MIN_DURATION = 5

        # Initialize the motpy tracker
        self.tracker = MultiObjectTracker(
            dt=1/30,
            model_spec={'order_pos': 1, 'dim_pos': 2, 'order_size': 0}
        )

        # Track history per person
        self.history = {}
        self.BUFFER_SIZE = 10

        self.pre_entry_buffer = deque(maxlen=int(self.PRE_ENTRY_BUFFER_DURATION * self.ALERT_FPS)) # Buffer for frames before an alert

        self.capture_queue = queue.Queue(maxsize=5)
        self.frame_lock = threading.Lock()

        threading.Thread(target=self._capture_loop, daemon=True).start()
        threading.Thread(target=self.capture_and_process_frames, daemon=True).start()
        threading.Thread(target=self.record_continuous_video, daemon=True).start()


    def capture_and_process_frames(self):
        frame_count = 0
        while True:
            frame = self.capture_queue.get()
            frame_count += 1
 
            if frame_count % 3 != 0:
                continue
            try:

                if frame.shape[2] == 4:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

                annotated_frame_for_display = frame.copy() 
                if check_object_detection() or self.session_active:
                    self._process_frames(annotated_frame_for_display)
 
                final_frame = draw_overlay(annotated_frame_for_display) 
                with self.frame_lock:
                    self.annotated_display_frame = final_frame
                self.pre_entry_buffer.append(self.annotated_display_frame)

            except Exception as e:
                logger.error(f"Error in capture_and_process_frames: {e}")
                import traceback
                logger.error(traceback.format_exc())

    def _process_frames(self, annotated):
        results = self.model.predict(annotated, imgsz=self.detection_size, verbose=False)[0]

        # Prepare detections for the tracker
        detections = []
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            cls_name = self.classes[cls_id]

            if cls_name == "Person" and conf > self.confidence_threshold:  # Only track people
                detections.append(Detection(
                    box=[x1, y1, x2-x1, y2-y1],  # Convert to [x, y, w, h] format for tracker
                    score=float(conf),
                    class_id=cls_id
                ))

        # Update tracker with detections
        self.tracker.step(detections)
        tracks = self.tracker.active_tracks()

        # Collect safety equipment boxes
        safety_boxes = {cls: [] for cls in self.UNSAFE_CLASSES if cls != "Person"}
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            cls_name = self.classes[cls_id]

            if cls_name in self.UNSAFE_CLASSES and cls_name != "Person" and conf > self.confidence_threshold:
                safety_boxes[cls_name].append((x1, y1, x2, y2))
                # Draw equipment boxes
                color = (0, 0, 255)  # Red color for safety violations
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                cv2.putText(annotated, cls_name,
                            (x1, y1-6),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, color, 2)

        # Update history for each track
        for t in tracks:
            tid = t.id
            px, py, pw, ph = t.box
            pbox = (px, py, px+pw, py+ph)

            for cls in self.UNSAFE_CLASSES:
                if cls != "Person" and cls in safety_boxes:  # Only check non-Person classes that exist in safety_boxes
                    seen = any(self.iou(pbox, sb) > 0.1 for sb in safety_boxes[cls])
                    self.update_track(tid, cls, seen)

        # Draw person boxes and check compliance
        for t in tracks:
            tid = t.id
            px, py, pw, ph = t.box
            px, py, p2x, p2y = int(px), int(py), int(px+pw), int(py+ph)

            # Check compliance for each person
            comp = self.check_compliance(tid)
            missing_violations = [c for c, v in comp.items() if v]  # Safety violations that occurred

            if missing_violations:  # There are violations
                self.current_person_detected = True
                self.bbox = (px, py, p2x, p2y)
                self.detection_class = missing_violations[0]  # Use first violation for alert
                self.confidence_detected = 0.9  # High confidence for safety violation

                color = (0, 0, 255)  # Red for violations
                cv2.rectangle(annotated, (px, py), (p2x, p2y), color, 2)
                cv2.putText(annotated, f"ID:{tid} VIOLATION", (px, py-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            else:
                color = (0, 255, 0)  # Green for compliant
                cv2.rectangle(annotated, (px, py), (p2x, p2y), color, 2)
                cv2.putText(annotated, f"ID:{tid} OK", (px, py-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        current_time = datetime.now(timezone.utc)
        
        if self.session_active and not is_alert_enabled():
            logger.info("[VIDEO_PROCESSOR] Alerts disabled during active session — clearing local session state.")
            # Do not call update_alert_on_exit when alerts are disabled
            self.session_active = False
            self.entry_time = None
            self.last_seen_time = None
            self.person_detected_start = None
            return

        # Check if we have any tracked persons with violations (current_person_detected equivalent)
        tracked_persons_with_violations = [t for t in tracks if any(self.check_compliance(t.id).values())]
        self.current_person_detected = bool(tracked_persons_with_violations)

        if self.session_active:
            if self.current_person_detected:
                self.last_seen_time = current_time
            else:
                if self.last_seen_time and (current_time - self.last_seen_time).total_seconds() >= self.exit_grace_duration:
                    # Log exit and update alert
                    exit_time = current_time
                    print(f"[EXIT] Person exited at: {exit_time}")
                    if is_alert_enabled():
                        if self.alert_manager.is_alert_active:
                            self.alert_manager.update_alert_on_exit(exit_time)
                    self.session_active = False
                    self.entry_time = None
                    self.last_seen_time = None
                    self.person_detected_start = None
        
        if not is_alert_enabled():
            # Do not accumulate entry timer when alerts turned off
            self.person_detected_start = None
            return

        else:
            # Use the first tracked person with violations as the trigger for session
            self.current_person_detected = bool(tracked_persons_with_violations)

            if self.current_person_detected:
                if self.person_detected_start is None:
                    self.person_detected_start = current_time
                else:
                    if (current_time - self.person_detected_start).total_seconds() >= self.entry_confirm_duration:
                        # Start session and create alert - use the first person with violations
                        for t in tracks:
                            if any(self.check_compliance(t.id).values()):
                                self.session_active = True
                                self.entry_time = current_time
                                self.last_seen_time = current_time
                                self.person_detected_start = None
                                print(f"[ENTRY] Person confirmed at: {self.entry_time}")
                                if is_alert_enabled():
                                    if not self.alert_manager.is_alert_active:
                                        px, py, pw, ph = t.box
                                        self.bbox = (int(px), int(py), int(px+pw), int(py+ph))
                                        lat, lon = estimate_alert_gps(annotated, self.bbox)
                                        self.alert_manager.create_alert(start_time=self.entry_time,
                                                                       confidence=self.confidence_detected,
                                                                       detection_class=self.detection_class,
                                                                       lat=lat, lon=lon)
                                break
            else:
                self.person_detected_start = None

    def init_track(self, tid):
        if tid not in self.history:
            self.history[tid] = {cls: [] for cls in self.UNSAFE_CLASSES if cls != "Person"}

    def update_track(self, tid, cls, seen):
        if tid not in self.history:
            self.init_track(tid)
        buff = self.history[tid][cls]
        buff.append(seen)
        if len(buff) > self.BUFFER_SIZE:
            buff.pop(0)

    def check_compliance(self, tid):
        if tid not in self.history:
            self.init_track(tid)
        return {cls: any(self.history[tid].get(cls, [])) for cls in self.UNSAFE_CLASSES if cls != "Person"}

    def iou(self, boxA, boxB):
        # Convert boxes to format: [x1, y1, x2, y2]
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])
        interArea = max(0, xB-xA)*max(0, yB-yA)
        boxAArea = (boxA[2]-boxA[0])*(boxA[3]-boxA[1])
        boxBArea = (boxB[2]-boxB[0])*(boxB[3]-boxB[1])
        denom = float(boxAArea + boxBArea - interArea)
        return interArea/denom if denom > 0 else 0

    def _capture_loop(self):
        while True:
            try:
                frame = self.camera.capture_array()
                if frame is None:
                    continue
                with self.frame_lock:
                    self.raw_frame = draw_overlay(frame.copy())
                try:
                    self.capture_queue.put_nowait(self.raw_frame)
                except queue.Full:
                    _ = self.capture_queue.get_nowait()
                    self.capture_queue.put_nowait(self.raw_frame)
            except Exception as e:
                logger.error(f"Error in capture loop: {e}")

    def record_continuous_video(self): 

        while True:
            self.is_continuous_recording_active.wait()

            frame_to_record = None
            with self.frame_lock:
                if self.raw_frame is not None:
                    frame_to_record = self.raw_frame.copy()
                else:
                    logger.debug("No frame available for continuous recording. Waiting...")
                    time.sleep(0.2) 
                    continue 

            now = time.time()
            if self.video_writer is None or (now - self.record_start_time >= 30):
                if self.video_writer:
                    self.video_writer.release()
                    logger.info("Released previous continuous video writer.")

                check_storage_and_cleanup() 
                filename = os.path.join(self.record_dir, f"{datetime.now(timezone.utc).strftime(TIMESTAMP_FORMAT)}.mp4")

                if frame_to_record is not None and frame_to_record.shape[0] > 0 and frame_to_record.shape[1] > 0:
                    h, w = frame_to_record.shape[:2]
                    self.video_writer = cv2.VideoWriter(filename, self.fourcc, 20.0, (w, h))
                    if not self.video_writer.isOpened():
                        logger.error(f"Continuous video writer failed to open for {filename}. Dimensions: ({w}, {h}) Codec: {self.fourcc}")
                        self.video_writer = None
                        time.sleep(1)
                        continue
                    else:
                        logger.info(f"Started continuous recording: {filename} with dimensions ({w}, {h})")
                else:
                    logger.warning("Attempted to start continuous recording but frame_to_record was invalid. Skipping this segment.")
                    time.sleep(1) 
                    continue

                self.record_start_time = now

            if self.video_writer and frame_to_record is not None:
                try:
                    self.video_writer.write(frame_to_record)
                    logger.debug(f"Frame written to continuous video {self.video_writer.getBackendName()}")
                except Exception as e:
                    logger.error(f"Error writing frame to continuous video: {e}")
                    if self.video_writer:
                        self.video_writer.release()
                    self.video_writer = None
            elif self.video_writer is None:
                logger.warning("Continuous video writer is None, cannot write frame.")

            # Control fps on video writing
            now = time.time()
            frame_write_time = now - self.last_write_time
            expected_interval = 1.0 / self.camera.fps_limit
            if frame_write_time < expected_interval:
                time.sleep(expected_interval - frame_write_time)
            self.last_write_time = time.time()

    def get_current_raw_frame(self):
        with self.frame_lock:
            return self.raw_frame if self.raw_frame is not None else None

    def get_current_annotated_frame(self):
        with self.frame_lock:
            return self.annotated_display_frame if self.annotated_display_frame is not None else None

    def start_continuous_recording(self):
        if not self.is_continuous_recording_active.is_set():
            self.is_continuous_recording_active.set()
            logger.info("Continuous recording started.")
            return True
        logger.info("Continuous recording is already active.")
        return False

    def stop_continuous_recording(self):
        if self.is_continuous_recording_active.is_set():
            self.is_continuous_recording_active.clear()
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
                logger.info("Released current continuous video writer.")
            logger.info("Continuous recording stopped.")
            return True
        logger.info("Continuous recording is already inactive.")
        return False


def load_camera_name():
    try:
        with open(PAYLOAD_PATH, "r") as f:
            data = json.load(f)
            return data.get("name", "Unknown Camera")
    except Exception as e:
        logger.error(f"[Overlay] Error reading camera payload: {e}")
        return "Unknown Camera"


CAMERA_NAME = load_camera_name()


def _get_inverted_color(avg_color):
    # avg_color is (B, G, R)
    inv = (255 - int(avg_color[0]),
           255 - int(avg_color[1]),
           255 - int(avg_color[2]))
    return inv

def draw_overlay(frame):
    camera_name = CAMERA_NAME
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    tz = get_time_zone()
    timestamp_text = f"{timestamp} - ({tz})"

    x, y, w, h = 10, 10, 300, 80
    roi = frame[y:y+h, x:x+w]

    avg_color = np.mean(roi.reshape(-1, 3), axis=0)

    text_color = _get_inverted_color(avg_color)

    cv2.putText(frame, timestamp_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)
    cv2.putText(frame, camera_name, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)

    return frame