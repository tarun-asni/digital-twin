import os
import cv2
import time
import torch
import logging
import subprocess
import platform
import cpuinfo

from django.conf import settings

from cc_alerts.models import Alert

from dotenv import load_dotenv
from cc_alerts.tasks import publish_clip_request

from ultralytics import YOLO

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ai_task", "models", "construction-model.pt"))

model = YOLO(MODEL_PATH)


try:
    if torch.cuda.is_available():
        model = YOLO(MODEL_PATH).to('cuda')
        logger.info("YOLO model initialized on CUDA (GPU).")

    elif torch.backends.mps.is_available() and torch.backends.mps.is_built():
        model = YOLO(MODEL_PATH).to('mps')
        logger.info("YOLO model initialized on MPS (Apple Silicon GPU).")

    else:
        system = platform.system().lower()
        cpu = cpuinfo.get_cpu_info().get("brand_raw", "").lower()
        distro = " ".join(platform.version().lower().split())

        if "intel" in cpu and "linux" in system and "ubuntu" in distro:
            try:
                openvino_path = MODEL_PATH.replace(".pt", "_openvino_model")
                model = YOLO(openvino_path)
                logger.info(f"YOLO model initialized with OpenVINO: {openvino_path}")
            except Exception as ov_err:
                logger.warning(f"OpenVINO load failed: {ov_err}. Falling back to CPU.")
                model = YOLO(MODEL_PATH)
                logger.warning("YOLO model initialized on CPU. Expect slower performance.")
        else:
            model = YOLO(MODEL_PATH)
            logger.info("YOLO model initialized on CPU (OpenVINO skipped).")

except Exception as e:
    logger.error(f"Error initializing YOLO model: {e}. Falling back to CPU.")
    model = YOLO(MODEL_PATH)


"""
Retry mechanism to fetch a video clip.
"""
def fetch_video_clip(alert_id, camera_id, start_time, duration):

    publish_clip_request(alert_id, camera_id, start_time, duration)
    

"""
Merge two videos.
video_2 is appended to video_1.
"""
def merge_videos(video_paths, output_path):
    # Make a temporary list.txt for ffmpeg
    list_file = output_path + "_list.txt"
    
    os.makedirs(os.path.dirname(list_file), exist_ok=True)
    
    with open(list_file, "w") as f:
        for path in video_paths:
            f.write(f"file '{path}'\n")

    cmd = [
        "ffmpeg",
        "-y",  # overwrite
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-c:v", "libx264", 
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        output_path,
    ]
    
    subprocess.run(cmd, check=True)

    os.remove(list_file)
    return output_path


"""
Safely delete a file with retries.
"""
def safe_delete(dir, path_list, retries=3, delay=0.2):

    for path in path_list:
        deleted = False

        for _ in range(retries):
            try:
                if os.path.exists(path):
                    os.remove(path)
                deleted = True
                break
            except PermissionError:
                time.sleep(delay)

        if not deleted and os.path.exists(path):
            logger.warning(f"Could not delete locked file: {path}")
    
    try:
        if os.path.exists(dir):
            os.rmdir(dir)
    except OSError:
        logger.warning(f"Could not remove directory (not empty?): {dir}")


"""
Append a new context message to the alert's message field.
"""
def append_and_save_message(alert: Alert, new_context: str):
    current_message = alert.inference_analysis or ""

    existing_lines = [line.strip() for line in current_message.splitlines()]
    if new_context.strip() in existing_lines:
        return

    if current_message and not current_message.endswith('\n'):
        current_message += "\n"

    alert.inference_analysis = current_message + new_context
    alert.save()
        

"""
Runs analysis on the provided video file.
Returns a dictionary mapping person IDs to their violation frames.
"""
def run_analysis_on_video(video_path, person_violation_map={}, alert=None):
    
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0 or fps is None:
        fps = 20.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    frame_index = 0

    frame_skip_interval = 2
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_index % frame_skip_interval == 0:
            results = model.track(frame, persist=True, stream=True)

        for r in results:
            if not hasattr(r, "boxes") or not hasattr(r.boxes, "id") or r.boxes.id is None:
                continue

            ids = r.boxes.id.cpu().numpy().astype(int)
            cls_ids = r.boxes.cls.cpu().numpy().astype(int)
            cls_names = [model.names[i] for i in cls_ids]

            for track_id, cls_name in zip(ids, cls_names):
                if cls_name in alert.detection_class:
                    logger.debug(f"Violation: ID={track_id}, Class={cls_name}, Frame={frame_index}")
                    if track_id not in person_violation_map:
                        person_violation_map[track_id] = [frame_index, frame_index]
                    else:
                        person_violation_map[track_id][1] = frame_index
            
        frame_index += 1

    cap.release()
    
    return person_violation_map, fps, total_frames, frame_width, frame_height


"""
Writes a trimmed video segment to local storage.
"""
def write_video(event_id, video_path, start_frame, end_frame, fps, frame_width, frame_height):
    
    cap = cv2.VideoCapture(video_path)
    output_dir = f'{settings.MEDIA_ROOT}/clips'
    os.makedirs(output_dir, exist_ok=True)

    trimmed_filename = f"event_{str(event_id)[:8]}_trimmed.mp4"
    trimmed_path = os.path.join(output_dir, trimmed_filename)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(trimmed_path, fourcc, fps, (frame_width, frame_height))
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    for i in range(start_frame, end_frame + 1):
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)

    cap.release()
    out.release()
    
    return trimmed_path


def infer_status(sf, ef):
    if sf and ef:
        return "start and end of the event is well established"
    elif not sf and ef:
        return "end of the event is established, start is uncertain. Requires prior video feed"
    elif sf and not ef:
        return "start of the event is established, end is uncertain. Requires post video feed"
    else:
        return "neither start nor end established. Requires prior and post video feed"

