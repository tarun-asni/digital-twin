import math

from ..config import CAMERA_LAT, CAMERA_LONG

def estimate_alert_gps(frame, bbox):
    """
    Estimate approximate GPS coordinates of the detected object 
    based on its position in the video frame.
    """
    frame_h, frame_w = frame.shape[:2]
    x1, y1, x2, y2 = bbox
    x_center = (x1 + x2) / 2
    y_center = (y1 + y2) / 2

    # Normalized center (-0.5 to +0.5)
    nx = (x_center / frame_w) - 0.5
    ny = (y_center / frame_h) - 0.5

    # Approximate scale: assume camera covers ~20m (width) × 15m (height)
    meters_per_pixel_x = 20 / frame_w
    meters_per_pixel_y = 15 / frame_h
    offset_x = nx * frame_w * meters_per_pixel_x
    offset_y = ny * frame_h * meters_per_pixel_y

    # Convert meter offset → GPS offset
    meters_per_deg_lat = 111320
    meters_per_deg_lon = 111320 * math.cos(math.radians(CAMERA_LAT))

    new_lat = CAMERA_LAT + (offset_y / meters_per_deg_lat)
    new_lon = CAMERA_LONG + (offset_x / meters_per_deg_lon)

    return round(new_lat, 8), round(new_lon, 8)