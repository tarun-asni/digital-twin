import cv2
import os
import time
import json
import logging
import asyncio
import threading
import requests
import platform
import subprocess
import numpy as np
from collections import deque
import onnxruntime as ort
from shapely.geometry import box
from RPiCam.performance_utils import draw_performance_overlay
from .byte_tracker import BYTETracker

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Detection")

TARGET_SIZE = 480
PERSON_CLASS = "person"
UNSAFE_CLASSES = ["no-hardhat", "no-mask", "no-safety vest"]
COLORS = {"safe": (0, 255, 0), "unsafe": (0, 0, 255), "zone": (0, 165, 255)}

MIN_VIDEO_SIZE_KB = 500
ALERT_VIDEO_DURATION = 30  # seconds


class SafetyMonitor:
    def __init__(self, model_path, zone=None):
        self.session = ort.InferenceSession(model_path)
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [o.name for o in self.session.get_outputs()]
        self.classes = ['hardhat', 'mask', 'no-hardhat', 'no-mask', 'no-safety vest',
                        'person', 'safety cone', 'safety vest', 'machinery', 'vehicle']

        self.zone = self._validate_zone(zone) if zone else None
        self.inside_zone_ids = set()
        self.zone_writer_map = {}
        self.zone_start_time = {}
        self.safety_writer_map = {}
        self.safety_start_time = {}
        self.alert_folder = "alerts"
        os.makedirs(self.alert_folder, exist_ok=True)

        self.pre_entry_buffer = deque(maxlen=150)
        self.tracker = BYTETracker()
        self.current_person_ids = set()
        self.last_seen = {}
        self.max_disappear_time = 2.0

    def _validate_zone(self, zone):
        zx1, zy1, zx2, zy2 = zone
        if abs(zx2 - zx1) < 20 or abs(zy2 - zy1) < 20:
            raise ValueError("Restricted zone is too small (min 20px width/height)")
        return (min(zx1, zx2), min(zy1, zy2), max(zx1, zx2), max(zy1, zy2))

    def _preprocess_frame(self, frame):
        resized = cv2.resize(frame, (TARGET_SIZE, TARGET_SIZE))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        tensor = np.transpose(rgb, (2, 0, 1))[np.newaxis, ...]
        return tensor, resized

    def _postprocess_output(self, outputs, shape, threshold=0.25):
        preds = outputs[0]
        detections = []
        for pred in preds[0]:
            x1, y1, x2, y2, score, cls = pred
            if score > threshold:
                x1 = int(x1 * shape[1] / TARGET_SIZE)
                y1 = int(y1 * shape[0] / TARGET_SIZE)
                x2 = int(x2 * shape[1] / TARGET_SIZE)
                y2 = int(y2 * shape[0] / TARGET_SIZE)
                detections.append([x1, y1, x2, y2, float(score), int(cls)])
        return detections

    def _iou_overlap(self, a, b):
        box_a = box(*a)
        box_b = box(*b)
        return box_a.intersection(box_b).area / box_a.union(box_b).area

    def _filter_duplicate_persons(self, tracks):
        person_tracks = [t for t in tracks if self.classes[t[5]] == PERSON_CLASS]
        unique = []
        while person_tracks:
            base = person_tracks.pop(0)
            base_box = base[:4]
            unique.append(base)
            person_tracks = [t for t in person_tracks if self._iou_overlap(base_box, t[:4]) < 0.9]
        others = [t for t in tracks if self.classes[t[5]] != PERSON_CLASS]
        return unique + others

    def _start_writer(self, track_id, alert_type, frame):
        timestamp = int(time.time())
        folder = os.path.join(self.alert_folder, f"{alert_type}_{track_id}_{timestamp}")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"{alert_type}.mp4")
        h, w = frame.shape[:2]
        writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'mp4v'), 25, (w, h))

        if alert_type == "restricted_zone":
            self.zone_writer_map[track_id] = writer
            self.zone_start_time[track_id] = time.time()
        else:
            self.safety_writer_map[track_id] = writer
            self.safety_start_time[track_id] = time.time()

        logger.info(f"Started {alert_type} video: {path}")
        for f in self.pre_entry_buffer:
            writer.write(f)

        threading.Thread(
            target=lambda: asyncio.run(self._handle_alert_async(alert_type, path)),
            daemon=True
        ).start()

    async def _handle_alert_async(self, alert_type, video_path):
        await asyncio.sleep(ALERT_VIDEO_DURATION)

        if not os.path.exists(video_path):
            logger.warning(f"Video not found: {video_path}")
            return

        size_kb = os.path.getsize(video_path) / 1024
        if size_kb < MIN_VIDEO_SIZE_KB:
            logger.warning(f"Skipping {video_path} — too small ({size_kb:.2f} KB)")
            return

        data = {
            "message": "🚨 Restricted Zone Breach!" if alert_type == "restricted_zone" else "⚠️ Unsafe Worker!",
            "severity": "high" if alert_type == "restricted_zone" else "medium",
            "detection_class": alert_type,
            "confidence": 1.0,
            "serial_number": self._get_serial_number()
        }

        logger.warning(f"🔁 Payload:\n{json.dumps(data, indent=2)}")

        try:
            response = requests.post("http://127.0.0.1:8000/api/command-center/alerts/", data=data)
            if response.status_code == 201:
                alert_id = response.json()["id"]
                with open(video_path, "rb") as f:
                    files = {"alert_file": f}
                    put_url = f"http://127.0.0.1:8000/api/command-center/alerts/{alert_id}/upload_video/"
                    put_resp = requests.put(put_url, files=files)
                    logger.warning(f"📤 Video uploaded: {put_resp.status_code} - {put_resp.text}")
            else:
                logger.error(f"POST failed: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Send failed: {e}")

    def _get_serial_number(self):
        try:
            if platform.system() == "Linux":
                serial = subprocess.check_output("cat /proc/cpuinfo | grep Serial", shell=True).decode()
                return serial.strip().split(":")[-1].strip()
            return "e5bfc14693f61957"
        except Exception as e:
            logger.warning(f"Serial fetch failed: {e}")
            return "UNKNOWN"

    def _cleanup_stale_ids(self):
        now = time.time()
        for tid in list(self.last_seen):
            if now - self.last_seen[tid] > self.max_disappear_time:
                self.last_seen.pop(tid, None)
                if tid in self.zone_writer_map:
                    self.zone_writer_map[tid].release()
                    self.zone_writer_map.pop(tid, None)
                if tid in self.safety_writer_map:
                    self.safety_writer_map[tid].release()
                    self.safety_writer_map.pop(tid, None)

    def process_frame(self, frame):
        start = time.perf_counter()
        tensor, _ = self._preprocess_frame(frame)
        try:
            output = self.session.run(self.output_names, {self.input_name: tensor})
        except Exception as e:
            logger.error(f"Inference error: {e}")
            return frame, False, False

        detections = self._postprocess_output(output, frame.shape[:2])
        tracks = self.tracker.update([d for d in detections if len(d) == 6])
        tracks = self._filter_duplicate_persons(tracks)
        person_in_zone, unsafe_detected = False, False
        new_ids = set()

        for x1, y1, x2, y2, tid, cls_id, conf in tracks:
            cls_name = self.classes[cls_id]
            color = COLORS["unsafe"] if cls_name in UNSAFE_CLASSES else COLORS["safe"]

            if cls_name == PERSON_CLASS:
                new_ids.add(tid)
                self.last_seen[tid] = time.time()
                if self.zone:
                    zx1, zy1, zx2, zy2 = self.zone
                    if x1 < zx2 and x2 > zx1 and y1 < zy2 and y2 > zy1:
                        person_in_zone = True
                        if tid not in self.inside_zone_ids:
                            logger.warning(f"⚠️ ALERT: Person {tid} entered restricted zone")
                            self.inside_zone_ids.add(tid)
                            self._start_writer(tid, "restricted_zone", frame)
                    if tid in self.zone_writer_map:
                        self.zone_writer_map[tid].write(frame)

            if cls_name in UNSAFE_CLASSES:
                unsafe_detected = True
                if tid not in self.safety_writer_map:
                    logger.warning(f"⚠️ ALERT: Person {tid} unsafe - {cls_name}")
                    self._start_writer(tid, "safety_violation", frame)
                self.safety_writer_map[tid].write(frame)

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{cls_name} ID:{tid}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        self._cleanup_stale_ids()
        self.current_person_ids = new_ids

        if not person_in_zone and not unsafe_detected:
            self.pre_entry_buffer.append(frame.copy())

        if self.zone:
            zx1, zy1, zx2, zy2 = self.zone
            cv2.rectangle(frame, (zx1, zy1), (zx2, zy2), COLORS["zone"], 2)
            cv2.putText(frame, "Restricted Area", (zx1, zy1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS["zone"], 2)

        draw_performance_overlay(frame, start)
        return frame, person_in_zone, unsafe_detected


def run_detection(zone):
    MODEL_PATH = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "models", "construction-model.onnx"
    ))
    monitor = SafetyMonitor(MODEL_PATH, zone)
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        logger.error("Cannot open webcam")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        processed, zone_alert, safety_alert = monitor.process_frame(frame)
        status = []
        if zone_alert:
            status.append("ZONE ALERT!")
        if safety_alert:
            status.append("SAFETY ALERT!")
        if status:
            cv2.putText(processed, " | ".join(status), (10, processed.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        cv2.imshow("Safety Monitor", processed)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
