import logging
import json
import uuid
from datetime import timedelta, datetime
from django.utils import timezone
from math import sqrt, sin, cos, atan2, radians

from django.db.models import Q, F
from cc_alerts.models import (
    Path, WayPoint, SensorAlert, DroneFlight, AlertDevice
)
from field_units.models import Drone, Sensor, Camera
from field_units.serializers import DroneSerializer
from sensegrid.config import publish_mqtt_message
from django.db import transaction
from cc_alerts.serializers import DroneFlightSerializer
from device_configuration.models import Device
from common.device import DeviceStatus

from sensegrid.config import send_ws_update

logger = logging.getLogger(__name__)

@transaction.atomic
def signal_to_drone(sensor_alert: SensorAlert, sensor: Sensor=None, camera: Camera=None, max_injection_distance: float = 1000.0, alert_id=None):
    """
    Assign a mission to the nearest drone (available or in-flight within injection distance).
    If nearest is available, assign directly. If in-flight, trigger mission injection protocol.
    """

    # Get all drones
    available_drones = Drone.objects.filter(is_available=True)
    in_flight_drones = Drone.objects.filter(is_in_flight=True, is_available=False)
    available_drones = Drone.objects.filter(is_available=True, is_active=True)
    in_flight_drones = Drone.objects.filter(
        (Q(is_in_flight=True) & Q(is_available=False)) |
        (Q(is_hovering=True) & Q(current_waypoint=F('last_waypoint')) & Q(last_waypoint__gt=0)),
        is_active=True
    ).distinct()

    # Compute distances for available drones (home point)
    available_distances = []
    for drone in available_drones:
        if drone.battery_percentage is not None and drone.battery_percentage >= 60:
            distance = get_distance_meters(drone, sensor_alert)
            if distance is not None:
                available_distances.append((distance, drone))

    # Compute distances for in-flight drones (latest point, within max_injection_distance)
    in_flight_distances = []
    for drone in in_flight_drones:
        latest_flight = DroneFlight.objects.filter(drone=drone).order_by('-start_time').first()
        if latest_flight:
            # For in-flight drones, calculate distance from their last mission target
            distance = get_distance_meters(latest_flight, sensor_alert)
            if distance is not None:
                in_flight_distances.append((distance, drone))

    # Combine all candidates
    all_candidates = available_distances + in_flight_distances

    if not all_candidates:
        logger.warning("No suitable drones found for assignment.")
        return None

    # Select the nearest drone overall
    nearest = min(all_candidates, key=lambda x: x[0])
    target_drone = nearest[1]
    distance = nearest[0]

    # Check if nearest is available or in-flight
    if target_drone.is_available:
        # Assign to available drone directly
        logger.info(f"Assigning mission to available drone {target_drone.id}, distance: {distance:.2f}m")
        
        if sensor:
            lat = sensor.latitude
            long = sensor.longitude
            alt = sensor.altitude
            AlertDevice.objects.create(
                sensor_alert=sensor_alert,
                device=Device.objects.get(id=target_drone.id),
                status='recording',
                recording_start=sensor_alert.timestamp,
            )
        elif camera:
            lat = camera.latitude
            long = camera.longitude
            alt = camera.altitude
            
            AlertDevice.objects.get_or_create(
                alert=sensor_alert.alert,
                device=Device.objects.get(id=target_drone.id),
                defaults={
                    'status': 'recording',
                    'recording_start': sensor_alert.alert.start_time,
                }
            )
            
            from cc_alerts.services.alert_management_service import AlertManagementService
            alert_data = AlertManagementService().alert_with_devices(sensor_alert.alert)
            send_ws_update(
                message=alert_data,
                group_name="alert_updates",
                type="alert.update"
            )
        
        sensor_alert.drone = target_drone
        sensor_alert.save()

        if sensor:
            path = Path.objects.filter(sensor=sensor).first()
        elif camera:
            path = Path.objects.filter(camera=camera).first()

        waypoints = WayPoint.objects.filter(path=path)
        logger.info(f"Found path for drone. path_id: {path.id}")

        waypoints_payload = []
        total_hover_duration = timedelta(seconds=0)
        for waypoint in waypoints:
            waypoints_payload.append({
                "latitude": float(waypoint.latitude),
                "longitude": float(waypoint.longitude),
                "altitude": float(waypoint.altitude),
                "hover_duration": float(waypoint.hover_duration) 
            })
            total_hover_duration += timedelta(seconds=float(waypoint.hover_duration))

        start_time = timezone.now()
        drone_flight = DroneFlight.objects.create(
            drone=target_drone,
            latitude=lat,
            longitude=long,
            altitude=alt,
            sensor_alert=sensor_alert,
            distance_to_target=distance,
            hovering_duration=total_hover_duration,
            start_time=start_time,
        )

        # Mark drone as in flight
        target_drone.is_in_flight = True
        target_drone.is_available = False
        target_drone.save()
        flight_id = {'id': str(drone_flight.id), 'start_time': start_time.isoformat()}
        
        # Get sensor/camera name
        sensor_name = sensor.name if sensor else (camera.name if camera else "Unknown Sensor")

        # Include drone home location (from field unit record) so the device can use it for RTL
        try:
            home_location = {
                "latitude": float(target_drone.latitude) if getattr(target_drone, 'latitude', None) is not None else None,
                "longitude": float(target_drone.longitude) if getattr(target_drone, 'longitude', None) is not None else None,
            }
        except Exception:
            home_location = {"latitude": None, "longitude": None}

        payload = [
            flight_id,
            waypoints_payload,
            {"sensor_alert_id": str(sensor_alert.id), "sensor_name": sensor_name, "home_location": home_location}
        ]
        
        def send_notifications():
            logger.info(f"Assigning mission to drone {target_drone.id} via MQTT")
            topic = f"drones/{target_drone.id}/signal"
            mqtt_payload = json.dumps(payload)
            publish_mqtt_message(topic, mqtt_payload, qos=2)
            logger.info(f"Mission assigned to drone {target_drone.id}")
            drone_data = get_drone_payload(target_drone, drone_flight, alert_id=alert_id)
            send_ws_update(
                message=drone_data,
                group_name="alert_updates",
                type="drone.alert"
            )
            logger.debug(f'WS update sent for drone {target_drone.id}.')
        
        transaction.on_commit(send_notifications)
        
        device = Device.objects.get(id=drone_flight.drone.id)
        device.status = DeviceStatus.STREAMING.value
        device.save(update_fields=["status"])

        return {"ui_approval_required": False, "drone_id": str(target_drone.id), "distance": distance}
    else:
        # The nearest drone is already in-flight, so we trigger mission injection.
        if distance > max_injection_distance:
            logger.warning(f"Nearest in-flight drone {target_drone.id} is too far for mission injection ({distance:.2f}m > {max_injection_distance}m). No drone assigned.")
            return None
            
        # Nearest is in-flight, send mission inject request
        logger.info(f"Mission inject requested for in-flight drone (id={target_drone.id}), distance: {distance:.2f}m, waiting for drone state/approval.")
        topic = f"drones/{target_drone.id}/signal"
        
        if sensor:
            path = Path.objects.filter(sensor=sensor).first()
        elif camera:
            path = Path.objects.filter(camera=camera).first()
        # Get sensor/camera name
        sensor_name = sensor.name if sensor else (camera.name if camera else "Unknown Sensor")
        
        # include home_location in mission inject payload as well
        try:
            home_location = {
                "latitude": float(target_drone.latitude) if getattr(target_drone, 'latitude', None) is not None else None,
                "longitude": float(target_drone.longitude) if getattr(target_drone, 'longitude', None) is not None else None,
            }
        except Exception:
            home_location = {"latitude": None, "longitude": None}

        payload = json.dumps({
            "command": "mission_inject",
            "waypoints": get_waypoints_payload(path),
            "sensor_alert_id": str(sensor_alert.id),
            "sensor_name": sensor_name,
            "home_location": home_location
        })
        publish_mqtt_message(topic, payload, qos=2)
        
        drone_data = get_drone_payload(target_drone, alert_id=alert_id)
            
        send_ws_update(
            message=drone_data,
            group_name="alert_updates",
            type="drone.alert"
        )
        return {
            "ui_approval_required": True,
            "drone_id": str(target_drone.id),
            "distance": distance,
            "detail": "Mission inject requested for in-flight drone. Awaiting drone state and UI approval."
        }

def send_emergency_land(drone_id):
    topic = f"drones/{drone_id}/signal"
    payload = json.dumps({"command": "emergency_land"})
    publish_mqtt_message(topic, payload, qos=2)
    logger.info(f"Emergency land command sent to drone {drone_id}")

def send_return_to_launch(drone_id):
    topic = f"drones/{drone_id}/signal"
    payload = json.dumps({"command": "return_to_launch"})
    publish_mqtt_message(topic, payload, qos=2)
    logger.info(f"Return to launch command sent to drone {drone_id}")

def get_distance_meters(homeloc, targetloc):
    try:
        lat1 = float(targetloc.latitude)
        lon1 = float(targetloc.longitude)
        lat2 = float(homeloc.latitude)
        lon2 = float(homeloc.longitude)
        R = 6371000
        lat1 = radians(lat1)
        lat2 = radians(lat2)
        lon1 = radians(lon1)
        lon2 = radians(lon2)
        dlat = lat1 - lat2
        dlon = lon1 - lon2
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance = R * c
        if distance < 0.1:
            distance = 0.0
        return distance
    except (ValueError, TypeError, AttributeError) as e:
        logger.warning(f"Distance calculation failed: {str(e)}")
        return None

def get_waypoints_payload(path):
    waypoints = WayPoint.objects.filter(path=path)
    payload = []
    for waypoint in waypoints:
        payload.append({
            "latitude": float(waypoint.latitude),
            "longitude": float(waypoint.longitude),
            "altitude": float(waypoint.altitude),
            "hover_duration": float(waypoint.hover_duration)
        })
    return payload

def get_drone_payload(drone: Drone, drone_flight: DroneFlight = None, alert_id=None):
    droneflight_data = None
    if drone_flight:
        droneflight_data = DroneFlightSerializer(drone_flight).data
        sensor_alert = drone_flight.sensor_alert
        droneflight_data['drone'] = str(drone.id)
        if alert_id:
            droneflight_data['alert_id'] = str(alert_id)
            droneflight_data['is_camera'] = True
            droneflight_data['device_id'] = str(sensor_alert.camera.id) if sensor_alert.camera else None
            droneflight_data['device_name'] = sensor_alert.camera.name if sensor_alert.camera else None
        else:
            droneflight_data['alert_id'] = str(sensor_alert.id)
            droneflight_data['is_camera'] = False
            droneflight_data['device_id'] = str(sensor_alert.sensor.id) if sensor_alert.sensor else None
            droneflight_data['device_name'] = sensor_alert.sensor.name if sensor_alert.sensor else None
    
    drone_data = DroneSerializer(drone).data
    
    payload = {
        "drone": drone_data,
        "drone_flight": droneflight_data
    }
    return payload