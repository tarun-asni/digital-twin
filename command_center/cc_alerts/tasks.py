import os
import json
import base64
import logging
import requests
import shutil
import subprocess
import tempfile

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from datetime import datetime, timedelta

from django.utils import timezone
from django.utils.timezone import make_aware, is_naive
from rest_framework.response import Response

from device_configuration.models import Key, Device
from mediahub.models import MediaFile
from field_units.models import Camera
from sensegrid import settings
from sensegrid.config import publish_mqtt_message

logger = logging.getLogger(__name__)


def get_private_key(device_id: str):
    try:
        device = Device.objects.get(id=device_id)
        key = Key.objects.get(device=device)
        
        if key.private_key:
            private_key = serialization.load_pem_private_key(
                key.private_key.encode(),
                password=None
            )
            return private_key

    except Exception as e:
        logger.error(f"❌ Error fetching private key: {e}, device_id: {device_id}")
    return None

def decrypt_aes_session_key(encrypted_key_b64: str, private_key) -> AESGCM | None:
    try:
        encrypted_key = base64.b64decode(encrypted_key_b64)
        aes_key = private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return AESGCM(aes_key)
    except Exception as e:
        logger.error("Key decrypt failed: %s", e)
        return None


def decrypt_payload_data(aesgcm: AESGCM, payload_b64: bytes) -> bytes | None:

    try:
        blob = base64.b64decode(payload_b64)
        nonce = blob[:12]
        cipher = blob[12:]
        return aesgcm.decrypt(nonce, cipher, None)
    except Exception as e:
        logger.debug("Payload decrypt error: %s", e)
        return None


def stream_proxy(camera_url: str):
    
    boundary = b"--frame"
    buffer = b""
    aesgcm = None
    private_key = None

    logger.info(f"▶️ Streaming from {camera_url}")
    try:
        with requests.get(camera_url, stream=True, timeout=(10, 30), verify=False) as resp:
            resp.raise_for_status()

            for chunk in resp.iter_content(4096):
                buffer += chunk

                while True:
                    start = buffer.find(boundary)
                    if start == -1:
                        break
                    end = buffer.find(boundary, start + len(boundary))
                    if end == -1:
                        break

                    segment = buffer[start + len(boundary):end]
                    buffer = buffer[end:]

                    try:
                        header_block, body_b64 = segment.split(b"\r\n\r\n", 1)
                        body_b64 = body_b64.strip(b"\r\n")

                        # Extract key from first frame only
                        if aesgcm is None or private_key is None:
                            for line in header_block.split(b"\r\n"):
                                if line.startswith(b"Device-ID:"):
                                    device_id = line.split(b":", 1)[1].strip().decode()
                                    private_key = get_private_key(device_id=device_id)
                                if line.startswith(b"Key:"):
                                    key_b64 = line.split(b":", 1)[1].strip()
                                    aesgcm = decrypt_aes_session_key(key_b64, private_key)

                        jpeg = decrypt_payload_data(aesgcm, body_b64)
                        yield (b"--frame\r\n"
                               b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n")

                    except Exception as frame_err:
                        logger.warning(f"Skipping corrupted frame: {frame_err}, device_id: {device_id}")
                        # Skip bad frame — don't break the whole stream
                        continue

    except GeneratorExit:
        logger.info("Client disconnected")
        return
    except Exception as e:
        logger.error("Stream proxy failed: %s", e)
        return


def publish_clip_request(alert_id, camera_id, start, duration):
    logger.info("Entered publish_clip_request method to publish message")
    topic = f"device/{camera_id}/clip/request"
    logger.info(f"publishing to topic name : {topic}")
    payload = json.dumps({"start": start, "duration": duration, "alert_id": str(alert_id)})

    publish_mqtt_message(topic, payload, qos=2)
    
    logger.info("Message published")

"""
    Requests video clip from the edge device.
    Expects: start (ISO timestamp), duration (in seconds)
"""
def request_clip_use_later(camera_id, start, duration: int) -> MediaFile:
    try:
        logger.info("Started request_clip(...)")
        camera = Camera.objects.get(id=camera_id)

        private_key = get_private_key(str(camera.id))
    except Camera.DoesNotExist:
        return Response({"error": "Camera not found"}, status=404)

    try:
        start_dt = datetime.fromisoformat(start)
        duration_int = max(int(duration), 1)
    except Exception:
        return Response({"error": "Invalid 'start' or 'duration'"}, status=400)

    try:
        response = requests.get(
            f"{camera.edge_url}/clip",
            params={"start": start_dt.strftime(settings.TIMESTAMP_FORMAT), "duration": duration_int},
        )
        if response.status_code != 200:
            return Response({"error": "Edge response not OK"}, status=502)
    except Exception as e:
        return Response({"error": "Edge fetch failed", "details": str(e)}, status=500)

    try:
        payload = response.json()
    except Exception as e:
        return Response({"error": "Invalid JSON from edge", "details": str(e)}, status=500)

    clips = payload.get("clips", [])

    if not clips:
        return Response({"error": "No clips returned"}, status=404)

    # Prepare workspace
    temp_dir = tempfile.mkdtemp()
    decrypted_files = []

    earliest_ts = min([datetime.strptime(c['timestamp'], settings.TIMESTAMP_FORMAT) for c in clips])

    if is_naive(earliest_ts):
        earliest_ts = make_aware(earliest_ts)
    if is_naive(start_dt):
        start_dt = make_aware(start_dt)    
    offset_seconds = abs((start_dt - earliest_ts).total_seconds())

    start_offset_str = str(timedelta(seconds=int(offset_seconds)))

    for clip in sorted(clips, key=lambda c: c["timestamp"]):
        aesgcm = decrypt_aes_session_key(clip["key"], private_key=private_key)
        if not aesgcm:
            continue

        decrypted_data = decrypt_payload_data(aesgcm, clip["enc"])
        if not decrypted_data:
            continue

        out_file = os.path.join(temp_dir, f"{clip['timestamp']}.h264")
        with open(out_file, "wb") as f:
            f.write(decrypted_data)
        decrypted_files.append(out_file)

    if not decrypted_files:
        return Response({"error": "No files decrypted"}, status=500)

    # Merge all h264 files to mp4
    input_txt_path = os.path.join(temp_dir, "input.txt")
    with open(input_txt_path, "w") as f:
        for file_path in decrypted_files:
            f.write(f"file '{file_path}'\n")

    merged_mp4_path = os.path.join(temp_dir, "merged.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", input_txt_path,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", merged_mp4_path
    ], check=True)

    trimmed_mp4_path = os.path.join(temp_dir, "trimmed.mp4")
    subprocess.run([
        "ffmpeg", "-y",
        "-ss", start_offset_str,
        "-i", merged_mp4_path,
        "-t", str(duration_int),
        "-c:v", "libx264", "-c:a", "aac", "-strict", "experimental",
        trimmed_mp4_path
    ], check=True)

    # Move to media hub directory
    final_filename = f"clip_{camera.id}_{start_dt.strftime('%Y%m%d_%H%M')}_dur{duration_int}.mp4"
    save_dir = os.path.join(settings.MEDIA_ROOT, "requested_clips")
    os.makedirs(save_dir, exist_ok=True)
    final_path = os.path.join(save_dir, final_filename)
    shutil.move(trimmed_mp4_path, final_path)

    # Save entry in MediaFile model
    relative_path = os.path.join("requested_clips", final_filename)
    media_file = MediaFile.objects.create(
        file=relative_path,
        media_type="video",
        title=f"Requested Clip - Camera {camera.id}",
        description=f"Requested from edge at {start} for {duration} secs",
        file_size=os.path.getsize(final_path),
        mime_type="video/mp4",
        is_public=False,
    )

    logger.info(f"Final clip saved: {relative_path}")
    return media_file


def handle_alert_video_upload(alert, alert_file):
    title = f"Alert Video - {alert.detection_class or 'Event'}"
    description = f"Uploaded for alert #{alert.id} on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
    media_type = 'video'
    mime_type = alert_file.content_type or 'video/x-msvideo'

    media_file = MediaFile(
        title=title,
        description=description,
        media_type=media_type,
        mime_type=mime_type,
        is_public=False
    )
    media_file.file.save(alert_file.name, alert_file, save=False)
    media_file.file_size = alert_file.size
    media_file.save()
    return media_file
