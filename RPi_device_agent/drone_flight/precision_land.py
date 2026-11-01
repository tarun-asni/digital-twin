# precisionland.py
# FINAL VERSION: Accurate alignment + live annotations (NO recording)

import time
import math
import threading
import logging
import numpy as np
import cv2

from pymavlink import mavutil
from pupil_apriltags import Detector

logger = logging.getLogger(__name__)
# Use shared camera from camera_stream.app (do not instantiate Picamera2 here)

# ================= CONFIG =================
CAM_WIDTH = 640
CAM_HEIGHT = 480

HFOV = math.radians(62)
VFOV = math.radians(48)

SEND_RATE_HZ = 12          # detection + control
DISPLAY_RATE_HZ = 4        # drawing only (low CPU)

MIN_TAG_AREA = 800
EMA_ALPHA = 0.25
DEADBAND = 0.03
# =========================================


def polygon_area(corners):
    x = corners[:, 0]
    y = corners[:, 1]
    return 0.5 * abs(
        np.dot(x, np.roll(y, 1)) -
        np.dot(y, np.roll(x, 1))
    )


class PrecisionLander:
    def __init__(self, vehicle, camera):
        self.vehicle = vehicle
        self.camera = camera  # shared camera instance (do not manage lifecycle)
        self.running = False
        self.frame_count = 0

        # EMA filter state
        self.dx_f = 0.0
        self.dy_f = 0.0

        # AprilTag detector
        self.detector = Detector(
            families="tag36h11",
            quad_decimate=1.0,
            refine_edges=True
        )

        # MAVLink
        self.master = mavutil.mavlink_connection(
            vehicle._master.address
        )

    def start(self):
        self.running = True
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self.running = False
        # cv2.destroyAllWindows() removed - no windows created in headless mode

    def execute(self, timeout=60):
        """Start precision landing and block until landing completes or timeout."""
        self.start()
        start_t = time.time()
        try:
            while self.running and getattr(self.vehicle, 'armed', True):
                if time.time() - start_t > timeout:
                    break
                time.sleep(0.5)
        finally:
            self.running = False

    def cleanup(self):
        self.running = False
        # Do not stop the shared camera here (owned by camera server)

    def _run(self):
        cx = CAM_WIDTH // 2
        cy = CAM_HEIGHT // 2

        draw_interval = max(1, int(SEND_RATE_HZ / DISPLAY_RATE_HZ))

        while self.running:
            # Snapshot altitude safely (vehicle may be modified from another thread)
            try:
                alt = None
                if hasattr(self.vehicle, 'location') and getattr(self.vehicle.location, 'global_relative_frame', None) is not None:
                    alt = getattr(self.vehicle.location.global_relative_frame, 'alt', None)
            except Exception:
                alt = None

            frame = self.camera.capture_array()
            if frame is None:
                time.sleep(0.05)
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

            # Initialize draw-related locals so they are always defined
            corners = None
            tx = None
            ty = None
            dx = 0.0
            dy = 0.0
            angle_x = None
            angle_y = None
            send_cmd = False

            tags = self.detector.detect(gray)

            if tags:
                tag = max(tags, key=lambda t: polygon_area(t.corners))
                area = polygon_area(tag.corners)

                if area >= MIN_TAG_AREA:
                    corners = tag.corners.astype(int)
                    tx, ty = map(int, tag.center)

                    # Normalized offsets
                    dx_raw = (tx - cx) / cx
                    dy_raw = (ty - cy) / cy

                    # EMA filtering
                    self.dx_f = EMA_ALPHA * dx_raw + (1 - EMA_ALPHA) * self.dx_f
                    self.dy_f = EMA_ALPHA * dy_raw + (1 - EMA_ALPHA) * self.dy_f

                    dx = 0.0 if abs(self.dx_f) < DEADBAND else self.dx_f
                    dy = 0.0 if abs(self.dy_f) < DEADBAND else self.dy_f

                    angle_x = dx * (HFOV / 2)
                    angle_y = dy * (VFOV / 2)

                    send_cmd = True

                    # Log tag detection details for debugging
                    logger.info(
                        f"[PL][TAG] alt={alt if alt is not None else float('nan'):.2f}m "
                        f"dx={dx:.3f} dy={dy:.3f} area={int(area)}"
                    )

            if send_cmd and (angle_x is not None and angle_y is not None):
                self._send_landing_target(angle_x, angle_y)

            # ---------- DRAW (THROTTLED) - DISABLED FOR HEADLESS OPERATION ----------
            # Drawing and display logic removed to prevent OpenCV memory corruption
            # on headless Raspberry Pi. cv2.waitKey() without cv2.imshow() causes SIGABRT.
            # All detection/control logic above remains active and functional.

            time.sleep(1 / SEND_RATE_HZ)

    def _send_landing_target(self, angle_x, angle_y):
        self.master.mav.landing_target_send(
            int(time.time() * 1e6),          # time_usec
            0,                               # target_num
            mavutil.mavlink.MAV_FRAME_BODY_FRD,
            angle_x,                         # angle_x (rad)
            angle_y,                         # angle_y (rad)
            0,                               # distance (unused)
            0,                               # size_x (required)
            0                                # size_y (required)
        )