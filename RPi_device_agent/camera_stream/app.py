import os
import cv2
import sys
import time
import logging
import traceback
from . import config
from dotenv import load_dotenv
from datetime import datetime
from .mqtt.mqtt_subscriber import MqttSubscriber
from .mqtt.clip_handler import handle_clip_request, upload_full_clip
from .mqtt.detection_handler import handle_detection_trigger

# NEW: Import MQTT handlers for multi-camera alerts
from .mqtt.mqtt_handlers import handle_control_message, handle_recording_message
from drone_flight.handle_signal_drone import handle_signal_drone, handle_inject_approval
from .rpi_utils.file_utils import find_recording_files
from flask import Flask, Response, request, jsonify, send_file

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils.Encryption_utils import Encryption_utils

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s")
logger = logging.getLogger("flask_app")

load_dotenv()

# --- Camera only for raw feed ---
from camera_stream.camera import Camera
shared_camera = Camera()

def start_mqtt_subscriber():
    subscriber = MqttSubscriber()
    device_id = config.DEVICE_ID
    try:
        # Camera topics
        clip_topic = f"device/{device_id}/clip/request"
        detection_topic = f"device/{device_id}/trigger-detection"
        
        full_clip = f"device/{device_id}/clip/full-clip"
        
        # Drone topics
        signal_topic = f"drones/{device_id}/signal"
        inject_approval_topic = f"drones/{device_id}/inject_approval"
        
        # NEW: Multi-camera alert topics        
        control_topic = f"device/{device_id}/control"
        recording_topic = f"drones/{device_id}/recording"  
        
        # Register existing topics
        subscriber.register_topic(clip_topic, handle_clip_request)
        subscriber.register_topic(full_clip, upload_full_clip)
        subscriber.register_topic(detection_topic, handle_detection_trigger)
        subscriber.register_topic(signal_topic, handle_signal_drone)
        subscriber.register_topic(inject_approval_topic, handle_inject_approval)
        subscriber.register_topic(control_topic, handle_control_message)
        subscriber.register_topic(recording_topic, handle_recording_message)
        
        subscriber.start()
    except Exception as e:
        logger.error(f"MQTT TLS connection failed: {e}")

app = Flask(__name__)


# --- Lazy VideoProcessor initialization for detection/recording endpoints ---
def get_video_processor():
    if not hasattr(get_video_processor, "instance"):
        from camera_stream.video_processor import VideoProcessor
        APP_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(APP_BASE_DIR, 'models', 'construction-model.pt')
        example_zone = (100, 100, 500, 400)
        get_video_processor.instance = VideoProcessor(
            shared_camera,
            model_path,
            frame_size=(640, 480),
            zone=example_zone
        )
        logger.info("VideoProcessor initialized and running in background threads.")
    return get_video_processor.instance

# --- Lazy DroneRecorder initialization for drone recording endpoints ---
def get_drone_recorder():
    if not hasattr(get_drone_recorder, "instance"):
        from camera_stream.drone_recorder import DroneRecorder
        get_drone_recorder.instance = DroneRecorder(shared_camera)
        logger.info("DroneRecorder initialized.")
    return get_drone_recorder.instance

# --- RAW FEED: No detection, no torch required ---
@app.route('/drone_raw_feed')
def drone_raw_feed():
    def generate_camera_feed():
        while True:
            frame = shared_camera.capture_array()
            if frame is None:
                time.sleep(0.1)
                continue
            ok, buf = cv2.imencode('.jpg', frame)
            if not ok:
                continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
    return Response(generate_camera_feed(), mimetype='multipart/x-mixed-replace; boundary=frame')

# --- Detection/Recording endpoints (require VideoProcessor/torch) ---
@app.route('/video_feed')
def raw_video():
    
    return Response(generate_raw_feed(), mimetype='multipart/x-mixed-replace; boundary=frame')

def generate_raw_feed(): 
    aes_key, aesgcm = Encryption_utils.generate_aes_key()
    logger.info("Edge stream started for client.")
    try:
        while True:
            if config.DEVICE_TYPE == "DRONE":
                frame=shared_camera.capture_array()
            else:  
                vp = get_video_processor()  
                frame = vp.get_current_raw_frame()
            if frame is None:
                time.sleep(0.1) 
                continue
            ok, buf = cv2.imencode(".jpg", frame)
            if not ok:
                continue        
            data, enc_key= Encryption_utils.process_and_encrypt_data(buf.tobytes(), aes_key, aesgcm)
            yield (b"--frame\r\n"
                b"Device-ID: " + config.DEVICE_ID.encode() + b"\r\n"
                b"Key: " + enc_key + b"\r\n"
                b"Content-Type: text/plain\r\n\r\n" +
                data + b"\r\n")
    except GeneratorExit:
        logger.info("Server disconnected — stopping edge stream.")
        return 
    except Exception as e:
        logger.error("Edge stream error: %s", e)

@app.route('/video_feed_light')
def video_feed_light():
    vp = get_video_processor()
    return Response(prepare_transmission(vp), mimetype='multipart/x-mixed-replace; boundary=frame')

def prepare_transmission(vp):
    while True:
        frame = vp.get_current_raw_frame()
        if frame is None:
            time.sleep(0.1)
            continue
        ok, buf = cv2.imencode('.jpg', frame)
        if not ok:
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')

@app.route('/annotated_feed')
def annotated_video():
    vp = get_video_processor()
    return Response(generate_annotated_feed(vp), mimetype='multipart/x-mixed-replace; boundary=frame')

def generate_annotated_feed(vp):   
    aes_key, aesgcm = Encryption_utils.generate_aes_key()
    while True:
        frame = vp.get_current_annotated_frame()
        if frame is None:
            time.sleep(0.1)
            continue
        height, width = frame.shape[:2]
        if config.IS_RESTRICTED:
            cv2.putText(frame, "RESTRICTED ZONE ACTIVE", (10, height - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        ok, buf = cv2.imencode(".jpg", frame)
        if not ok:
            continue
        data, enc_key= Encryption_utils.process_and_encrypt_data(buf.tobytes(), aes_key, aesgcm)
        yield (b"--frame\r\n"
               b"Device-ID: " + config.DEVICE_ID.encode() + b"\r\n"
               b"Key: " + enc_key + b"\r\n"
               b"Content-Type: text/plain\r\n\r\n" +
               data + b"\r\n")

@app.route("/clip", methods=["GET"])
def get_clip():
    try:
        start_str = request.args.get("start")
        duration_sec = request.args.get("duration", type=int)
        if not start_str or not duration_sec:
            logger.error('Missing timestamp or duration.')
            return jsonify({"error": "Missing 'start' or 'duration'"}), 400
        try:
            start_time = datetime.strptime(start_str, config.TIMESTAMP_FORMAT)
        except ValueError:
            logger.error(f"Invalid timestamp format. Expected {config.TIMESTAMP_FORMAT}")
            return jsonify({"error": f"Invalid timestamp format. Expected {config.TIMESTAMP_FORMAT}"}), 400
        matching_files = find_recording_files(start_time, duration_sec)
        if not matching_files:
            logger.error("No recordings found in the specified time range.")
            return jsonify({"error": "No recordings found in the specified time range"}), 404
        return send_file(
            matching_files[0],
            mimetype="video/mp4",
            as_attachment=False,
            download_name=os.path.basename(matching_files[0])
        )
    except Exception as e:
        logger.error(f"UNHANDLED ERROR in /clip: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/trigger-detection', methods=['GET'])
def trigger_detection():
    state_param = request.args.get('state', 'false').lower()
    config.IS_RESTRICTED = state_param == 'true'
    logger.info(f"Triggered restricted zone: {config.IS_RESTRICTED}")
    return jsonify({
        "status": "success",
        "IS_RESTRICTED": config.IS_RESTRICTED,
        "message": "Object Detection is now ACTIVE" if config.IS_RESTRICTED else "Object Detection is now INACTIVE",
        "timestamp": time.time()
    }), 200

@app.route('/get-config', methods=['POST'])
def get_configuration_for_detection():
    """
    Change the configuration of detection classes
    """
    
    payload = request.get_json()
    config.DETECTION_CLASSES = payload.get('detection_classes', [])
    
    return jsonify({
        "status": "success",
        "message": "Configurations are changes."
    }), 201

@app.route('/alert/trigger', methods=['POST'])
def trigger_alert():
    vp = get_video_processor()
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Invalid JSON payload."}), 400
    alert_type = data.get('alert_type')
    message = data.get('message')
    severity = data.get('severity')
    confidence = data.get('confidence', 1.0)
    if not all([alert_type, message, severity]):
        return jsonify({"status": "error", "message": "Missing required fields: alert_type, message, severity."}), 400
    if vp.trigger_manual_alert(alert_type, message, severity, confidence):
        return jsonify({"status": "success", "message": "Manual alert triggered."}), 200
    else:
        return jsonify({"status": "error", "message": "Failed to trigger manual alert (no frame available)."}), 500


if __name__ == '__main__':
    try:
        start_mqtt_subscriber()
        config.device_alive()
        get_video_processor() # Initialize VideoProcessor
        app.run(host='0.0.0.0', port=5001, threaded=True)
    except Exception as e:
        logger.error(f"An error occurred while running the Flask application: {e}")