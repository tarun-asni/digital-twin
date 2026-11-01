import time
import os
import logging
import ssl
import threading
from typing import List, Dict, Any
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from utils.RestUtil import RestUtil
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from RPi_device_agent.camera_stream.mqtt.mqtt_subscriber import MqttSubscriber 
import logging
import psutil
from drone_flight.handle_signal_drone import handle_signal_drone, handle_inject_approval
from flask import Flask, jsonify, Response
import cv2
from drone_flight.config import DEVICE_ID, SERIAL_PORT, BAUD_RATE, COMMAND_CENTER_URL, MQTT_HOST, MQTT_PORT, CA_CERT, SERVER_CERT, SERVER_KEY
from dronekit import connect, VehicleMode, LocationGlobalRelative
from math import sqrt, sin, cos, radians, atan2
from datetime import datetime
from .emergency_land_rtl import emergency_land as perform_emergency_land, return_to_launch as perform_return_to_launch, cleanup_after_emergency as perform_cleanup_after_emergency

from camera_stream.camera import Camera
from camera_stream.rpi_utils.time_converter import time_converter
from camera_stream.drone_recorder import DroneRecorder
from camera_stream.app import shared_camera, app as camera_app
from .precision_land import PrecisionLander
from .drone_rec import send_recordings_to_command_center
from .gimbal_controller import GimbalController
from werkzeug.serving import make_server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def start_mqtt_subscriber():
    subscriber = MqttSubscriber()
    device_id = os.getenv("DEVICE_ID")
    try:
        signal_drone_topic = f"drones/{device_id}/signal"
        inject_approval_topic = f"drones/{device_id}/inject_approval"
        subscriber.register_topic(signal_drone_topic, handle_signal_drone)
        subscriber.register_topic(inject_approval_topic, handle_inject_approval)
        client = mqtt.Client()
        client.tls_set(ca_certs=CA_CERT,
                       certfile=SERVER_CERT,
                       keyfile=SERVER_KEY,
                       tls_version=ssl.PROTOCOL_TLSv1_2)
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        client.disconnect()
        logger.info("message published")
        subscriber.start()
    except Exception as e:
        logger.error(f"MQTT TLS connection failed: {e}")

class DroneController:
    def __init__(self):
        self.current_script_dir = os.path.dirname(os.path.abspath(__file__))
        self.PROJECT_ROOT_DIR = os.path.dirname(self.current_script_dir)
        self.dotenv_path = os.path.join(self.PROJECT_ROOT_DIR, '.env')
        load_dotenv(self.dotenv_path)
        self.COMMAND_CENTER_URL = os.getenv("COMMAND_CENTER_BASE_URL", COMMAND_CENTER_URL)
        self.DEVICE_ID = os.getenv("DEVICE_ID", DEVICE_ID)
        self.app = Flask(__name__)
        self.vehicle = None
        self.is_available = True
        self.is_in_flight = False
        self.is_interrupted = False
        self.mission_inject_requested = False
        self.mission_inject = False
        self.vehicle_lock = threading.RLock()
        self._camera_process = None
        self.home_location = None
        self.inject_approval_event = threading.Event()
        self.inject_approved = None
        self.last_battery_percentage = None
        self.is_hovering = False
        self.current_waypoint = 0
        self.last_waypoint = 0
        self.injected_waypoints = None
        self.injected_home_location = None
        self.drone_flight_id = None
        self._drone_recorder = None
        self._camera_server_thread = None
        self.gimbal = None
        self._camera_server = None

    def connect_vehicle(self, connection_string=SERIAL_PORT, baud=BAUD_RATE, retries=3):
        logger.info(f"Connecting to vehicle on: {connection_string}")
        for attempt in range(retries):
            try:
                with self.vehicle_lock:
                    if self.vehicle:
                        self.vehicle.close()
                        self.vehicle = None
                        time.sleep(2)
                    self.vehicle = connect(connection_string, wait_ready=True, baud=baud, heartbeat_timeout=120)
                    try:
                        vr = self.vehicle.location.global_relative_frame
                        self.home_location = LocationGlobalRelative(vr.lat, vr.lon, getattr(vr, 'alt', None))
                    except Exception:
                        self.home_location = None
                logger.info("Connected to vehicle.")
                self.is_available = True
                self.is_in_flight = False
                self.gimbal = GimbalController(self.vehicle)
                logger.info("Gimbal controller initialized with vehicle")
                return self.vehicle
            except Exception as e:
                logger.error(f"Connection attempt {attempt + 1}/{retries} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(2)
        logger.error("All connection attempts failed")
        self.vehicle = None
        self.reset_mission_state()
        return None

    def get_battery_percentage(self):
        if not self.vehicle:
            return self.last_battery_percentage
        try:
            with self.vehicle_lock:
                # battery = self.vehicle.battery.level
                battery = 100
                self.last_battery_percentage = battery
                return battery
        except Exception as e:
            logger.error(f"Error retrieving battery: {e}")
            return self.last_battery_percentage

    def arm_vehicle(self):
        logger.info("Setting mode to GUIDED...")
        with self.vehicle_lock:
            if not self.vehicle:
                logger.error("No vehicle connected")
                return False
            self.vehicle.mode = VehicleMode("GUIDED")
            while self.vehicle.mode.name != "GUIDED":
                time.sleep(1)
            logger.info("Arming...")
            self.vehicle.armed = True
            while not self.vehicle.armed:
                time.sleep(1)
        logger.info("Vehicle armed.")
        self.is_in_flight = True
        self.is_available = False
        return True

    def takeoff_vehicle(self, target_altitude):
        logger.info(f"Taking off to {target_altitude} m...")
        with self.vehicle_lock:
            if not self.vehicle:
                logger.error("No vehicle connected")
                return False
            self.vehicle.simple_takeoff(target_altitude)
            try:
                vr = self.vehicle.location.global_relative_frame
                self.home_location = LocationGlobalRelative(vr.lat, vr.lon, getattr(vr, 'alt', None))
            except Exception:
                self.home_location = None
        while True:
            with self.vehicle_lock:
                if not self.vehicle:
                    logger.error("Vehicle disconnected during takeoff")
                    return False
                alt = self.vehicle.location.global_relative_frame.alt
            logger.info(f"Altitude: {alt:.2f} m, Battery: {self.get_battery_percentage() or 'Unknown'}%")
            if alt >= target_altitude * 0.95:
                logger.info("Target altitude reached")
                self.gimbal.handle_flight_phase('takeoff')
                return True
            time.sleep(1)

    def get_distance_meters(self, aLocation1, aLocation2):
        """Calculate distance between two points using haversine formula."""
        R = 6371000  # Earth's radius in meters
        lat1, lon1 = radians(aLocation1.lat), radians(aLocation1.lon)
        lat2, lon2 = radians(aLocation2.lat), radians(aLocation2.lon)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c

    def home_location_land(self):
        logger.info("Initiating home-location landing (home_location_land)")
        try:
            # Use only the home_location provided with the mission payload
            if not self.home_location:
                logger.error("Home coordinates not provided via mission payload; cannot perform home landing")
                self.is_available = True
                self.is_in_flight = False
                return

            try:
                target_lat = float(self.home_location.lat)
                target_lon = float(self.home_location.lon)
                logger.info(f"Using home_location from payload: lat={target_lat}, lon={target_lon}")
            except Exception as e:
                logger.error(f"Invalid home_location stored on device: {e}")
                self.is_available = True
                self.is_in_flight = False
                return
            # Snapshot vehicle state and issue goto while holding lock briefly to avoid races
            with self.vehicle_lock:
                if not self.vehicle:
                    logger.warning("No vehicle connected, cannot perform home landing")
                    return
                # set gimbal to rtl pose if available
                try:
                    self.gimbal.handle_flight_phase('rtl')
                except Exception:
                    pass
                try:
                    vr = self.vehicle.location.global_relative_frame
                    curr_alt = getattr(vr, 'alt', None) or 10.0
                except Exception:
                    curr_alt = 10.0
                approach_alt = curr_alt
                target = LocationGlobalRelative(target_lat, target_lon, approach_alt)
                try:
                    self.vehicle.groundspeed = 3
                except Exception:
                    pass
                try:
                    self.vehicle.simple_goto(target)
                except Exception as e:
                    logger.error(f"Failed to start navigation to home target: {e}")

            # navigate to home point, hover, then land; trigger precision landing once after switching to LAND
            while True:
                # snapshot vehicle reference and location safely
                with self.vehicle_lock:
                    veh = self.vehicle
                    if veh is None or not getattr(veh, 'armed', True):
                        break
                    try:
                        current_location = getattr(veh.location, 'global_relative_frame', None)
                    except Exception:
                        current_location = None
                if current_location is None:
                    time.sleep(1)
                    continue
                distance = self.get_distance_meters(current_location, target)
                logger.info(f"Altitude: {getattr(current_location, 'alt', 0):.2f} m, Distance to home target: {distance:.2f} m, Battery: {self.get_battery_percentage() or 'Unknown'}%")

                if distance <= 1.0:
                    logger.info("Reached home coordinate, hovering for 2 seconds before landing")
                    time.sleep(2)
                    with self.vehicle_lock:
                        if not self.vehicle:
                            break
                        try:
                            self.vehicle.mode = VehicleMode("LAND")
                        except Exception as e:
                            logger.error(f"Failed to set LAND mode: {e}")

                    # Immediately attempt precision landing once after switching to LAND
                    try:
                        target_for_precision = LocationGlobalRelative(target_lat, target_lon, 0)
                        if self._execute_precision_land_if_ready(target_location=target_for_precision):
                            logger.info("Precision landing executed successfully")
                        else:
                            logger.info("Precision landing not initiated; proceeding with normal LAND")
                    except Exception as e:
                        logger.error(f"Precision landing attempt failed: {e}")

                    with self.vehicle_lock:
                        if self.vehicle:
                            try:
                                self.vehicle.mode = VehicleMode("STABILIZE")
                                logger.info("Set mode to STABILIZE after home landing")
                            except Exception as e:
                                logger.error(f"Failed to set STABILIZE mode: {e}")
                    battery_percentage = self.get_battery_percentage()
                    logger.info(f"Battery after home landing: {battery_percentage or 'Unknown'}%")
                    logger.info("Home landing sequence completed.")
                    break

            # Final state and cleanup
            self.reset_mission_state()
            self.notify_command_center()
            try:
                self.gimbal.cleanup()
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Error during home_location_land: {e}", exc_info=True)
            self.reset_mission_state()
            self.notify_command_center()

    def _execute_precision_land_if_ready(self, target_location=None):
        """Checks conditions and executes precision landing.

        Simpler trigger: attempt precision landing when near the target horizontally
        (within `max_distance`) and above a small minimum altitude, or when the
        vehicle is actively descending.

        Returns:
            True if precision landing was executed, False otherwise
        """
        try:
            # Snapshot necessary vehicle attributes under lock to avoid races
            with self.vehicle_lock:
                veh = self.vehicle
                if veh is None:
                    return False
                try:
                    current_loc = getattr(veh.location, 'global_relative_frame', None)
                    current_alt = getattr(current_loc, 'alt', None) if current_loc is not None else None
                    vel = getattr(veh, 'velocity', None)
                except Exception:
                    current_loc = None
                    current_alt = None
                    vel = None

            # Use provided target or fall back to home_location
            if target_location is None:
                target_location = self.home_location
            if target_location is None:
                logger.warning("No target location provided and home_location not set")
                return False

            distance_to_target = self.get_distance_meters(current_loc, target_location)

            # Parameters for simple trigger
            min_alt = 0.5        # don't attempt if practically on ground
            max_distance = 10.0  # horizontal tolerance in meters

            if current_alt is None:
                logger.debug("Current altitude unknown, skipping precision landing check")
                return False

            # Try to detect descent using the velocity snapshot
            descending = False
            try:
                if vel and len(vel) >= 3 and vel[2] is not None:
                    vz = float(vel[2])
                    # treat negative vz as descending (MAV uses NED frame where down is positive in some configs)
                    descending = vz < -0.2
                    logger.info(f"Detected vertical speed vz={vz:.2f} m/s, descending={descending}")
            except Exception:
                logger.debug("Unable to read vehicle velocity for descent detection")

            within_distance = (distance_to_target is not None) and (distance_to_target <= max_distance)

            # Condition: near target and above min_alt OR actively descending
            if (within_distance and current_alt >= min_alt) or descending:
                logger.info(f"Conditions met for precision landing (alt={current_alt:.2f}m, dist={distance_to_target:.2f}m, descending={descending}). Initiating...")
                # Ensure camera is available before attempting precision landing
                try:
                    if shared_camera is None:
                        logger.warning("Shared camera not available; skipping precision landing")
                        return False
                except NameError:
                    logger.warning("Shared camera symbol not available; skipping precision landing")
                    return False
                
                # CRITICAL: Stop recording to prevent h264 encoder conflicts
                # Recording will capture everything up to precision landing phase
                if self._drone_recorder is not None and self._drone_recorder.is_recording:
                    logger.info("Stopping drone recording before precision landing to prevent h264 corruption")
                    self.stop_drone_recording()
                    time.sleep(1.0)
                    logger.info("Recording stopped, camera ready for precision landing")
                
                time.sleep(1)
                lander = PrecisionLander(self.vehicle, shared_camera)
                try:
                    lander.execute()
                finally:
                    lander.cleanup()
                return True

            # Debug reasons
            if not within_distance:
                logger.debug(f"Precision landing skipped: target too far (dist={distance_to_target})")
            if current_alt < min_alt and not descending:
                logger.debug(f"Precision landing skipped: too close to ground (alt={current_alt:.2f}m)")
        except Exception as e:
            logger.error(f"Error during precision landing check: {e}")
        return False

    def emergency_land(self):
        try:
            self.gimbal.handle_flight_phase('land')
            perform_emergency_land(self)
            perform_cleanup_after_emergency(self)
            self.notify_command_center()
        except Exception as e:
            logger.error(f"Emergency land error: {e}")
            self.reset_mission_state()

    def return_to_launch(self):
        try:
            self.gimbal.handle_flight_phase('rtl')
            perform_return_to_launch(self)
            perform_cleanup_after_emergency(self)
        except Exception as e:
            logger.error(f"RTL error: {e}")
            self.reset_mission_state()

    def cleanup_after_emergency(self):
        perform_cleanup_after_emergency(self)

    def reset_mission_state(self):
        self.is_available = True
        self.is_in_flight = False
        self.mission_inject = False
        self.mission_inject_requested = False
        logger.info("Mission state reset: is_available=True, is_in_flight=False, mission_inject=False")

    def signal_drone(self, payload) -> Dict[str, Any]:
        # Allow mission injection if in flight and mission_inject is True
        if not self.is_available and not self.mission_inject:
            logger.warning("New missions blocked as drone is not available and not in mission inject mode.")
            return {"status": "error", "message": "Drone not available for new mission", "battery_percentage": self.get_battery_percentage(), "is_available": self.is_available, "is_in_flight": self.is_in_flight, "is_interrupted": self.is_interrupted}
        if not self.is_connected():
            logger.info("Vehicle not connected or heartbeat lost, attempting to connect...")
            self.vehicle = self.connect_vehicle()
        if self.vehicle is None:
            logger.error("Vehicle connection failed")
            self.reset_mission_state()
            self.notify_command_center()
            return {"status": "error", "message": "Failed to connect to vehicle", "battery_percentage": self.get_battery_percentage(), "is_available": self.is_available, "is_in_flight": self.is_in_flight, "is_interrupted": self.is_interrupted}
        # Log home location at the start of the mission
        if self.home_location:
            logger.info(f"[MISSION START] Drone home location: lat={self.home_location.lat}, lon={self.home_location.lon}, alt={self.home_location.alt}")
        else:
            logger.warning("[MISSION START] Home location not set.")

        # Only override mission if mission_inject is True and drone is in flight
        if self.is_in_flight and not self.mission_inject:
            logger.info("Drone is in flight and mission_inject is not set, cannot override mission.")
            return {"status": "error", "message": "Drone is in flight, mission inject not approved", "battery_percentage": self.get_battery_percentage(), "is_available": self.is_available, "is_in_flight": self.is_in_flight, "is_interrupted": self.is_interrupted}
        # Set both flags to True for injected mission
        if self.mission_inject:
            self.is_in_flight = True
        else:
            self.is_in_flight = True
            self.is_available = False

        if not payload:
            return {"status": "error", "message": "Invalid payload", "battery_percentage": self.get_battery_percentage(), "is_available": self.is_available, "is_in_flight": self.is_in_flight, "is_interrupted": self.is_interrupted}

        # If payload contains meta information (index 2) with home_location, persist it
        try:
            if isinstance(payload, (list, tuple)) and len(payload) >= 3 and isinstance(payload[2], dict):
                meta = payload[2]
                home = meta.get('home_location')
                if home and home.get('latitude') is not None and home.get('longitude') is not None:
                    try:
                        lat = float(home.get('latitude'))
                        lon = float(home.get('longitude'))
                        alt = float(home.get('altitude')) if home.get('altitude') is not None else None
                        # store as LocationGlobalRelative so later code can use .lat/.lon/.alt
                        if alt is None:
                            alt = getattr(self.home_location, 'alt', 0) if self.home_location else 0
                        self.home_location = LocationGlobalRelative(lat, lon, alt)
                        logger.info(f"Set home_location from payload: lat={lat}, lon={lon}, alt={alt}")
                    except Exception:
                        logger.warning("Invalid home_location values in payload; ignoring")
        except Exception:
            pass

        self.drone_flight_id = payload[0].get('id')
        
        waypoints = payload[1]    
        if not isinstance(waypoints, list) or not waypoints:
            logger.error("Invalid or empty waypoints")
            self.reset_mission_state()
            self.notify_command_center()
            return {"status": "error", "message": "Invalid or empty waypoints", "battery_percentage": self.get_battery_percentage(), "is_available": self.is_available, "is_in_flight": self.is_in_flight, "is_interrupted": self.is_interrupted}
        logger.info(f"Received waypoints: {waypoints}")
        self.start_video_stream()
        self.start_drone_recording()
        mission_aborted = False
        try:
            for idx, waypoint in enumerate(waypoints):
                self.current_waypoint = idx + 1
                self.last_waypoint = len(waypoints)
                self.is_hovering = False
                self.notify_command_center()
                if not self.vehicle:
                    logger.warning("Emergency/RTL triggered or vehicle disconnected, aborting mission")
                    mission_aborted = True
                    break
                latitude = float(waypoint.get('latitude', 0))
                longitude = float(waypoint.get('longitude', 0))
                altitude = float(waypoint.get('altitude', 0))
                hover_duration = float(waypoint.get('hover_duration', 0))
                if not all([latitude, longitude, altitude, hover_duration > 0]):
                    logger.error(f"Invalid parameters in waypoint {idx + 1}")
                    self.reset_mission_state()
                    self.notify_command_center()
                    return {"status": "error", "message": f"Invalid parameters in waypoint {idx + 1}", "battery_percentage": self.get_battery_percentage(), "is_available": self.is_available, "is_in_flight": self.is_in_flight, "is_interrupted": self.is_interrupted}
                logger.info(f"Processing waypoint {idx + 1}: lat={latitude}, lon={longitude}, alt={altitude}, hover={hover_duration}s")
                if idx == 0 and not self.mission_inject:
                    if not self.arm_vehicle() or not self.takeoff_vehicle(altitude):
                        self.reset_mission_state()
                        self.notify_command_center()
                        return {"status": "error", "message": "Failed to arm or takeoff", "battery_percentage": self.get_battery_percentage(), "is_available": self.is_available, "is_in_flight": self.is_in_flight, "is_interrupted": self.is_interrupted}
                elif idx == 0 and self.mission_inject:
                    logger.info("Mission injected, skipping arm and takeoff, proceeding to first waypoint")
                target_location = LocationGlobalRelative(latitude, longitude, altitude)
                with self.vehicle_lock:
                    if not self.vehicle:
                        logger.error("Vehicle disconnected during mission")
                        break
                    self.vehicle.groundspeed = 2
                    self.vehicle.simple_goto(target_location)
                while True:
                    if not self.vehicle:
                        logger.warning("Emergency/RTL triggered or vehicle disconnected, stopping navigation")
                        mission_aborted = True
                        break
                    with self.vehicle_lock:
                        if not self.vehicle:
                            break
                        current_location = self.vehicle.location.global_relative_frame
                    distance = self.get_distance_meters(current_location, target_location)
                    logger.info(f"Distance: {distance:.2f} m, Battery: {self.get_battery_percentage() or 'Unknown'}%")
                    if distance <= 1:
                        logger.info("Reached target location")
                        break
                    time.sleep(2)
                if mission_aborted:
                    break
                # Hover logic
                logger.info(f"Hovering for {hover_duration} seconds...")
                self.is_hovering = True
                self.notify_command_center()
                # Set gimbal to 90° if this is the last waypoint
                if idx == len(waypoints) - 1:
                    self.gimbal.handle_flight_phase('targetpoint')
                    logger.info("Gimbal set to 90° at last waypoint hover")
                hover_time = 0
                inject_checked = False
                self.mission_inject_requested = False # Reset before hover

                while hover_time < hover_duration:
                    if not self.vehicle:
                        logger.warning("Emergency/RTL triggered or vehicle disconnected, stopping hover")
                        mission_aborted = True
                        break

                    # If an inject has been requested, continuously check for approval.
                    if self.mission_inject_requested:
                        if not inject_checked:
                            logger.info("Mission inject requested, waiting for approval...")
                            self.inject_approval_event.clear() # Ensure event is clear before waiting
                            inject_checked = True

                        # Non-blocking check for the approval event on each loop iteration.
                        if self.inject_approval_event.is_set() and self.inject_approved:
                            self.mission_inject = True
                            logger.info("Mission inject approved, breaking hover to start new mission.")
                            self.is_hovering = False
                            self.notify_command_center()
                            injected = self.injected_waypoints
                            injected_meta = None
                            # Preserve any injected home_location provided by the command center
                            if getattr(self, 'injected_home_location', None):
                                injected_meta = {"home_location": self.injected_home_location}
                            id = {'id': self.drone_flight_id}
                            # Include meta as third element so signal_drone can persist home_location
                            payload = [id, injected, injected_meta] if injected_meta is not None else [id, injected]
                            # clear injected state
                            self.injected_waypoints = None
                            self.injected_home_location = None
                            return self.signal_drone(payload)

                    if hover_time % 5 == 0:
                        logger.info(f"Battery during hover: {self.get_battery_percentage() or 'Unknown'}%")
                    time.sleep(1)
                    hover_time += 1
                self.is_hovering = False
                self.notify_command_center()
            if mission_aborted or not self.vehicle:
                # If mission was aborted during hover after an inject was requested but not approved, reset the flag.
                if self.mission_inject_requested and not self.mission_inject:
                    self.mission_inject_requested = False

                logger.info("Mission aborted due to emergency/RTL or disconnection")
                self.reset_mission_state()
                self.stop_video_stream()  
                self.stop_drone_recording() 
                self.notify_command_center()
                return {"status": "aborted", "message": "Mission aborted", "battery_percentage": self.get_battery_percentage(), "is_available": self.is_available, "is_in_flight": self.is_in_flight, "is_interrupted": self.is_interrupted}
            else:
                # Reset mission_inject after mission completion and final hover, before RTL
                self.mission_inject = False
                self.gimbal.handle_flight_phase('waypoint')
                self.home_location_land()
                self.stop_video_stream()  
                self.stop_drone_recording()  
                # Log home location after RTL
                if self.home_location:
                    logger.info(f"[MISSION END] Drone home location after RTL: lat={self.home_location.lat}, lon={self.home_location.lon}, alt={self.home_location.alt}")
                else:
                    logger.warning("[MISSION END] Home location not set after RTL.")
            logger.info(f"Post-mission battery: {self.get_battery_percentage() or 'Unknown'}%")
            logger.info("Mission completed successfully")
            # Update end_time in DroneFlight
            if self.drone_flight_id:
                try:
                    url = f"{self.COMMAND_CENTER_URL}/cc-alerts/drone-flight/{self.drone_flight_id}/end-mission/"
                    end_time = datetime.now()
                    end_time = time_converter.to_iso_format(time_converter.local_to_utc(end_time))
                    payload = {"end_time": end_time}
                    response = RestUtil.send_data(url, body=payload, method="PATCH")
                    if response.ok:
                        logger.info(f"Updated end_time for DroneFlight {self.drone_flight_id}")
                    else:
                        logger.error(f"Failed to update end_time: {response.status_code} {response.text}")
                except Exception as e:
                    logger.error(f"Exception updating end_time: {e}")
            return {"status": "completed", "is_available": self.is_available, "is_in_flight": self.is_in_flight, "is_interrupted": self.is_interrupted}
        except Exception as e:
            logger.error(f"Mission error: {e}")
            self.reset_mission_state()
            self.stop_video_stream()
            self.stop_drone_recording()
            with self.vehicle_lock:
                if self.vehicle:
                    self.vehicle.close()
                    self.vehicle = None
            self.notify_command_center()
            return {"status": "error", "message": str(e), "battery_percentage": None, "is_available": self.is_available, "is_in_flight": self.is_in_flight, "is_interrupted": self.is_interrupted}

    def health(self):
        try:
            return jsonify({
                "connection_status": "ok" if self.vehicle else "not_connected",
                "device_id": self.DEVICE_ID,
                "battery_percentage": self.get_battery_percentage(),
                "is_available": self.is_available,
                "is_in_flight": self.is_in_flight,
                "is_interrupted": self.is_interrupted,
            })
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return jsonify({"status": "error", "message": str(e), "battery_percentage": None, "is_available": self.is_available, "is_in_flight": self.is_in_flight, "is_interrupted": self.is_interrupted}), 500

    def run(self):
        try:
            self.vehicle = self.connect_vehicle()
            self.app.route('/signal-drone', methods=['POST'])(self.signal_drone)
            self.app.route('/health', methods=['GET'])(self.health)
            self.app.run(host="0.0.0.0", port=6000, threaded=True)
        except Exception as e:
            logger.error(f"Fatal error in drone controller run: {e}")
        finally:
            self.stop_video_stream()
            with self.vehicle_lock:
                if self.vehicle:
                    self.vehicle.close()
                    self.vehicle = None
                    logger.info("Vehicle connection closed.")

    def run_camera_server(self):
        """Runs the camera Flask app in a separate daemon thread."""
        try:
            logger.info("Starting camera stream server on port 5001.")
            self._camera_server = make_server('0.0.0.0', 5001, camera_app, threaded=True)
            self._camera_server.serve_forever()
        except Exception as e:
            logger.error(f"Fatal error: {e}")

    def start_video_stream(self):
        if self._camera_server_thread and self._camera_server_thread.is_alive():
            logger.info("Camera stream already running. Skipping start.")
            return
        try:
            logger.info("Starting camera stream thread.")
            self._camera_server_thread = threading.Thread(target=self.run_camera_server, daemon=True)
            self._camera_server_thread.start()
        except Exception as e:
            logger.error(f"Failed to start camera stream: {e}")

    def kill_zombie_camera_processes(self):
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                if 'python' in proc.name().lower() and 'run_camera_stream' in cmdline:
                    logger.warning(f"Killing old camera process: PID {proc.pid}, CMD: {cmdline}")
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        proc.kill()
                        logger.warning(f"Had to force kill process {proc.pid}")
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.warning(f"Process access error: {e}")
                continue

    def stop_video_stream(self):
        if self._camera_server:
            self._camera_server.shutdown()
            self._camera_server = None
            logger.info("Camera server stopped.")
        else:
            logger.info("Camera server is not running.")

    def start_drone_recording(self):
        if self._drone_recorder is not None and self._drone_recorder.is_recording:
            logger.info("Drone recording already running. Skipping start.")
            return
        try:
            if self._drone_recorder is None:
                self._drone_recorder = DroneRecorder(shared_camera)
            self._drone_recorder.start_recording()
            logger.info("Drone recording started.")
        except Exception as e:
            logger.error(f"Failed to start drone recording: {e}")

    def stop_drone_recording(self):
        if self._drone_recorder is not None and self._drone_recorder.is_recording:
            self._drone_recorder.stop_recording()
            logger.info("Drone recording stopped.")
        else:
            logger.info("Drone recording is not running.")

    def notify_command_center(self):
        try:
            url = f"{self.COMMAND_CENTER_URL}/field-units/drones/{self.DEVICE_ID}/"
            payload = {
                "is_available": self.is_available,
                "is_in_flight": self.is_in_flight,
                "is_interrupted": self.is_interrupted,
                "mission_inject": self.mission_inject,
                "battery_percentage": round(float(self.get_battery_percentage()), 2) if self.get_battery_percentage() is not None else None,
                "current_waypoint": getattr(self, "current_waypoint", 0),
                "last_waypoint": getattr(self, "last_waypoint", 0),
                "is_hovering": getattr(self, "is_hovering", False),
            }
            response = RestUtil.send_data(url, body=payload, method="PATCH")
            if response.ok:
                logger.info("Notified Command Center successfully")
            else:
                logger.error(f"Failed to notify Command Center: {response.status_code} {response.text}")
        except Exception as e:
            logger.error(f"Exception notifying Command Center: {e}")

    def notify_command_center_inject_state(self, message, sensor_name="Unknown Sensor"):
        # Send state to command center
        try:
            url = f"{self.COMMAND_CENTER_URL}/field-units/drones/{self.DEVICE_ID}/inject_state/"
            payload = {"inject_state": message, "device_name": sensor_name}
            RestUtil.send_data(url, body=payload, method="POST")
            logger.info(f"Sent inject state to command center: {message}")
        except Exception as e:
            logger.error(f"Failed to notify command center of inject state: {e}")

    def wait_for_inject_approval(self, timeout=60):
        # This should be called after notify_command_center_inject_state
        # The command center should call back (e.g., via MQTT or REST) to set self.inject_approved
        logger.info("Waiting for inject approval from command center...")
        self.inject_approval_event.clear()
        return self.inject_approval_event.wait(timeout=timeout)

    def set_inject_approval(self, approved: bool):
        self.inject_approved = approved
        self.inject_approval_event.set()

    def is_connected(self):
        if self.vehicle is None:
            return False
        if self.vehicle.last_heartbeat is None:
            return False
        return time.time() - self.vehicle.last_heartbeat < 120

drone_controller = DroneController()

if __name__ == "__main__":
    start_mqtt_subscriber()
    drone_controller.run()