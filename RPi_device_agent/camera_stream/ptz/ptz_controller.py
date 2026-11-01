import math
import logging

from .. import config
# import RPi.GPIO as GPIO  # Uncomment when using actual hardware


logger = logging.getLogger(__name__)

class PTZController:
    """Handles Pan-Tilt-Zoom (PTZ) operations for a single camera."""

    def __init__(self, camera_id):
        self.camera_id = camera_id
        self.config = config
        self.current_pan = config.INITIAL_PAN
        self.current_tilt = config.INITIAL_TILT

    # ---------- PTZ LOGIC ---------- #

    def focus_on_location(self, target_lat, target_long, target_alt=2):
        """
        Rotate camera toward target coordinates (stop at mechanical limits).
        """
        pan, tilt = self._calculate_ptz_angles(target_lat, target_long, target_alt)
        pan, tilt = self._apply_limits(pan, tilt)
        self._rotate(pan, tilt)
        logger.info(f"[PTZController] Camera {self.camera_id} focusing on ({target_lat}, {target_long}) | pan={pan:.1f}, tilt={tilt:.1f}")

    def reset_to_initial_position(self):
        """
        Return the camera to its initial position.
        """
        self._rotate(self.config.INITIAL_PAN, self.config.INITIAL_TILT, self.config.INITIAL_ZOOM)
        logger.info(f"[PTZController] Camera {self.camera_id} returned to initial position.")

    # ---------- MATH CORE ---------- #

    def _calculate_ptz_angles(self, target_lat, target_long, target_alt):
        """
        Compute the desired pan and tilt based on target coordinates.
        """
        lat1, lon1, lat2, lon2 = map(math.radians, [self.config.CAMERA_LAT, self.config.CAMERA_LONG, target_lat, target_long])
        dlon = lon2 - lon1
        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1)*math.sin(lat2) - math.sin(lat1)*math.cos(lat2)*math.cos(dlon)
        bearing = (math.degrees(math.atan2(x, y)) + 360) % 360

        # Relative pan rotation (based on how camera was mounted)
        relative_pan = (bearing - self.config.CAMERA_FACING_AZIMUTH + 360) % 360
        servo_pan = (relative_pan / 360) * (self.config.PAN_MAX - self.config.PAN_MIN) + self.config.PAN_MIN

        # Distance for tilt calculation
        dist = self._haversine_distance(self.config.CAMERA_LAT, self.config.CAMERA_LONG, target_lat, target_long)
        delta_h = target_alt - self.config.CAMERA_ALT
        tilt_angle = math.degrees(math.atan2(delta_h, dist))
        servo_tilt = (tilt_angle + 45) / 90 * (self.config.TILT_MAX - self.config.TILT_MIN) + self.config.TILT_MIN

        return servo_pan, servo_tilt

    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        """
        Finds the distance between two points on the Earth.
        """
        R = 6371000 # Earth radius in meters
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # ---------- MOTOR LOGIC ---------- #

    def _apply_limits(self, pan, tilt):
        """
        Ensure PTZ angles stay within hardware-safe range.
        """
        pan = max(self.config.PAN_MIN, min(self.config.PAN_MAX, pan))
        tilt = max(self.config.TILT_MIN, min(self.config.TILT_MAX, tilt))
        return pan, tilt

    def _rotate(self, pan, tilt, zoom=None):
        """
        Simulate sending PTZ movement commands.
        """
        # In real code, here you'd output PWM or send REST to Flask PTZ simulator
        # We can implement if we have specific hardware components.
        self.current_pan = pan
        self.current_tilt = tilt
        logger.info(f"[PTZController] Camera {self.camera_id} rotated to pan={pan:.1f}, tilt={tilt:.1f}, zoom={zoom or 10}")


# Singleton instance for global use
ptz_controller = PTZController(camera_id=config.DEVICE_ID)