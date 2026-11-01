import logging
import time
from typing import Optional
from dronekit import Vehicle

logger = logging.getLogger(__name__)

class GimbalController:
    """Automated gimbal control for different flight phases"""
    
    def __init__(self, vehicle: Vehicle):
        self.vehicle = vehicle
        self.current_angle = None
        self.servo_channel = '7'
        logger.info("Gimbal controller initialized")

    def set_gimbal_angle(self, angle_deg: float, transition_time: float = 0.5) -> bool:
        """
        Automatically set gimbal angle with smooth transition
        
        Args:
            angle_deg: Target angle (0-90 degrees)
            transition_time: Time to move to new position in seconds
        """
        try:
            if not 0 <= angle_deg <= 90:
                logger.error(f"Invalid angle {angle_deg}°")
                return False

            if self.current_angle == angle_deg:
                return True

            pwm_value = int(1000 + (angle_deg / 90) * 1000)
            self.vehicle.channels.overrides[self.servo_channel] = pwm_value
            
            # Wait for movement to complete
            time.sleep(transition_time)
            
            self.current_angle = angle_deg
            logger.info(f"Gimbal automatically set to {angle_deg}°")
            return True

        except Exception as e:
            logger.error(f"Gimbal adjustment failed: {e}")
            return False

    def handle_flight_phase(self, phase: str) -> None:
        """
        Automatically adjust gimbal based on flight phase
        
        Args:
            phase: Current flight phase ('takeoff', 'waypoint', 'rtl', 'land')
        """
        phase_angles = {
            'targetpoint': 90,  # Straight down at target point
            'takeoff': 0,    # Straight ahead after takeoff
            'waypoint': 45,  # 45° at last waypoint
            'rtl': 90,      # Straight down during RTL
            'land': 90      # Maintain downward view during landing
        }
        
        if phase in phase_angles:
            self.set_gimbal_angle(phase_angles[phase])
        else:
            logger.warning(f"Unknown flight phase: {phase}")

    def cleanup(self) -> None:
        """Release gimbal control on shutdown"""
        try:
            if self.servo_channel in self.vehicle.channels.overrides:
                del self.vehicle.channels.overrides[self.servo_channel]
            logger.info("Gimbal control released")
        except Exception as e:
            logger.error(f"Gimbal cleanup error: {e}")