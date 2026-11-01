import json
import logging
import threading
from typing import List, Dict, Any
from RPi_device_agent.drone_flight.drone_rec import send_recordings_to_command_center

logger = logging.getLogger(__name__)

def handle_signal_drone(msg):
    try:
        from RPi_device_agent.drone_flight.drone import drone_controller
        payload = json.loads(msg.payload.decode())
        logger.info(f"Received MQTT drone signal payload: {payload}")
        if drone_controller is None:
            logger.error("DroneController instance not initialized")
            return

        # Mission injection protocol
        if isinstance(payload, dict) and payload.get("command") == "mission_inject":
            waypoints = payload.get("waypoints")
            sensor_alert_id = payload.get("sensor_alert_id")
            sensor_name = payload.get("sensor_name", "Unknown Sensor")
            # Only allow override if hovering at last waypoint
            if drone_controller.is_hovering and drone_controller.current_waypoint == drone_controller.last_waypoint:
                drone_controller.injected_waypoints = waypoints
                # Preserve any provided home_location so the drone can use it after approval
                if payload.get('home_location'):
                    try:
                        drone_controller.injected_home_location = payload.get('home_location')
                    except Exception:
                        logger.warning("Invalid injected home_location; ignoring")
                drone_controller.mission_inject_requested = True # Signal the main loop
                if waypoints and len(waypoints) > 0:
                    lat = waypoints[-1].get('latitude')
                    long = waypoints[-1].get('longitude')
                    hover_duration = waypoints[-1].get('hover_duration')
                    message = f"received the coordinates {lat}, {long}, hover duration {hover_duration}, and sensor {sensor_name} for the new mission, should i override ?"
                else:
                    message = f"received sensor {sensor_name} for the new mission, should i override ?"
                drone_controller.notify_command_center_inject_state(message, sensor_name)
                return
            else:
                sensor_name = payload.get("sensor_name", "Unknown Sensor")
                drone_controller.notify_command_center_inject_state("Mission inject received, but not hovering at last waypoint. Navigating to target waypoint.", sensor_name)
                return

        if isinstance(payload, list):
            # Only start mission if not interrupted and not in mission inject waiting state
            if drone_controller.mission_inject:
                logger.warning("Drone interrupted or waiting for mission inject approval, ignoring new mission.")
                return
            if not drone_controller.is_available and not drone_controller.is_in_flight:
                logger.warning("Drone busy, ignoring new signal.")
                return
            # Pass full payload, assuming payload = [flight_id, waypoints]
            mission_thread = threading.Thread(target=run_mission, args=(drone_controller, payload))
            mission_thread.start()
            logger.info("Mission started in background thread.")
        elif isinstance(payload, dict):
            command = payload.get("command")
            if command == "emergency_land":
                
                emergency_thread = threading.Thread(target=drone_controller.emergency_land)
                emergency_thread.start()
                drone_controller.notify_command_center()
                logger.info("Emergency land initiated in background thread")
            elif command == "return_to_launch":
          
                rtl_thread = threading.Thread(target=drone_controller.return_to_launch)
                rtl_thread.start()
                drone_controller.notify_command_center()
                logger.info("Return to launch initiated in background thread")
            else:
                logger.warning(f"Unknown command: {command}")
        else:
            logger.warning("Invalid payload format")
    except Exception as e:
        logger.error(f"Error handling signal drone MQTT message: {e}", exc_info=True)

def handle_inject_approval(msg):
    try:
        from RPi_device_agent.drone_flight.drone import drone_controller
        if not drone_controller:
            logger.error("DroneController not initialized, cannot handle inject approval.")
            return
        payload = json.loads(msg.payload.decode())
        approved = payload.get("approved")
        logger.info(f"Inject approval received: {approved}")
        drone_controller.set_inject_approval(approved)

    except Exception as e:
        logger.error(f"Error handling inject approval: {e}")

def run_mission(drone_controller, waypoints: List[Dict[str, Any]]):
    try:
        result = drone_controller.signal_drone(waypoints)
        logger.info(f"Mission result: {result}")
        if result:
            drone_controller.notify_command_center()
            logger.info("Informed command center, mission completed.")
        # Send recordings in a background thread after the mission flow is complete.
        # This allows the drone to disarm immediately without waiting for the upload.
        upload_thread = threading.Thread(target=send_recordings_to_command_center, args=(drone_controller,))
        upload_thread.start()
    except Exception as e:
        logger.error(f"Error running mission: {e}")
        drone_controller.reset_mission_state()
        with drone_controller.vehicle_lock:
            if drone_controller.vehicle:
                drone_controller.vehicle.close()
                drone_controller.vehicle = None
        drone_controller.notify_command_center()

# Add these methods to DroneController (drone.py):
# - notify_command_center_inject_state(message)
# - wait_for_inject_approval()
