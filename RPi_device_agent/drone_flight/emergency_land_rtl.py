import time
import logging
from dronekit import VehicleMode, LocationGlobalRelative

logger = logging.getLogger(__name__)

def emergency_land(drone_controller):
    logger.info("Initiating emergency land...")
    try:
        with drone_controller.vehicle_lock:
            if not drone_controller.vehicle:
                logger.warning("No vehicle connected, cannot perform emergency land")
                return
            drone_controller.vehicle.mode = VehicleMode("LAND")
            while drone_controller.vehicle.mode.name != "LAND":
                time.sleep(1)
            while drone_controller.vehicle.armed:
                time.sleep(1)
                logger.info(f"Altitude: {drone_controller.vehicle.location.global_relative_frame.alt:.2f} m")
            drone_controller.vehicle.mode = VehicleMode("STABILIZE")
        battery_percentage = drone_controller.get_battery_percentage()
        logger.info(f"Battery after emergency land: {battery_percentage or 'Unknown'}%")
        logger.info("Emergency land sequence completed.")
    except Exception as e:
        logger.error(f"Error during emergency land: {e}")
        cleanup_after_emergency(drone_controller)

def return_to_launch(drone_controller):
    logger.info("Initiating return_to_launch -> delegating to home_location_land")
    try:
        # Delegate to DroneController.home_location_land which manages flags/state
        drone_controller.home_location_land()
        logger.info("emergency return_to_launch completed")
    except Exception as e:
        logger.error(f"Error during return_to_launch via home_location_land: {e}", exc_info=True)
        cleanup_after_emergency(drone_controller)

def cleanup_after_emergency(drone_controller):
    drone_controller.is_available = True
    drone_controller.is_in_flight = False
    drone_controller.is_interrupted = False
    with drone_controller.vehicle_lock:
        if drone_controller.vehicle:
            drone_controller.vehicle.close()
            drone_controller.vehicle = None
    drone_controller.stop_drone_recording()
    time.sleep(5)
    drone_controller.stop_video_stream()
    drone_controller.notify_command_center()
    logger.info("Cleanup after emergency/RTL completed, drone status set to AVAILABLE")