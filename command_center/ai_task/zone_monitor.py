import cv2
import logging

zone_points = []

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ZoneSelector")

def click_event(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN and len(zone_points) < 2:
        zone_points.append((x, y))
        logger.info(f"Point selected: {x}, {y}")

def select_restricted_zone():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logger.error("Cannot open webcam")
        return None

    print("Select two points for restricted zone or press 'q' to skip.")
    _, frame = cap.read()
    cv2.imshow("Select Zone", frame)
    cv2.setMouseCallback("Select Zone", click_event)

    while True:
        _, frame = cap.read()
        for pt in zone_points:
            cv2.circle(frame, pt, 5, (0, 0, 255), -1)
        cv2.imshow("Select Zone", frame)
        key = cv2.waitKey(1) & 0xFF
        if (len(zone_points) == 2 and key == ord('q')) or key == ord('q'):
            break

    cv2.destroyWindow("Select Zone")
    cap.release()

    if len(zone_points) == 2:
        zx1, zy1 = zone_points[0]
        zx2, zy2 = zone_points[1]
        return [zx1, zy1, zx2, zy2]
    return None