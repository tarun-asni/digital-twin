import os
import cv2
import logging
from ultralytics import YOLO

logger = logging.getLogger(__name__)

def check_person_in_video(
    video_path,
    required_seconds=2,
    conf_threshold=0.5,
    fps=20
):
    """
    Returns True only if a person is detected continuously
    for `required_seconds`.
    """

    model_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "ai_task",
        "models",
        "yolov8n.pt",
    )

    if not os.path.exists(model_path):
        logger.error(f"Model not found at {model_path}")
        return False

    # Load YOLO
    model = YOLO(model_path)

    # Read FPS safely
    cap = cv2.VideoCapture(video_path)
    cap.release()

    if fps <= 0:
        logger.error("Invalid FPS detected")
        return False

    required_frames = int(fps * required_seconds)
    logger.info(
        f"FPS={fps:.2f}, Required frames={required_frames}"
    )

    results = model(video_path, stream=True, verbose=False)

    consecutive_frames = 0

    for frame_idx, r in enumerate(results):

        person_detected = False

        if r.boxes is not None:
            for box in r.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])

                if model.names[cls] == "person" and conf >= conf_threshold:
                    person_detected = True
                    break

        if person_detected:
            consecutive_frames += 1
        else:
            consecutive_frames = 0  # reset on break

        if consecutive_frames >= required_frames:
            logger.info(
                "Person detected in the video."
            )
            return True

    logger.info("Person not detected for required duration")
    return False
