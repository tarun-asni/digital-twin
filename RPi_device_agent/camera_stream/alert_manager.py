import os
import sys
import uuid
import time
import logging
import zipfile
import threading
import concurrent.futures

from io import BytesIO
from math import ceil
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from utils.RestUtil import RestUtil

from .config import (
    RECORDINGS_DIR, TIMESTAMP_FORMAT,
    ALERT_URL, RECORD_DURATION, DEVICE_ID, 
    is_alert_enabled
)

from .rpi_utils.time_converter import time_converter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s")
logger = logging.getLogger(__name__)


class AlertManager:
    def __init__(self):
        self.is_alert_active = False
        self.active_alert_data = None
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self._lock = threading.Lock()

    def create_alert(self, start_time, confidence, detection_class: str, lat, lon):

        """Non-blocking: starts alert creation in background."""
        if not is_alert_enabled():
            logger.info("[ALERT] Alert creation disabled, skipping.")
            return
        self._executor.submit(
            self._create_alert_sync,
            start_time=start_time,
            confidence=confidence,
            detection_class=detection_class,
            lat=lat,
            lon=lon
        )
    
    def update_alert_on_exit(self, end_time):
        """Non-blocking: updates alert in background."""
        if not is_alert_enabled():
            logger.info("[ALERT] Alert update disabled, skipping.")
            return
        self._executor.submit(
            self._update_alert_on_exit_sync,
            end_time=end_time
        )
    
    def _create_alert_sync(self, start_time, confidence, detection_class: str, lat, lon):
        """Create and send a new alert. Return alert ID."""
        with self._lock:
            if self.is_alert_active:
                logger.info("[ALERT] Alert already active, skipping new one.")
                return

            alert_id = str(uuid.uuid4())
            alert_data = {
                "id": alert_id,
                "message": None,
                "severity": None,
                "detection_class": detection_class,
                "confidence": confidence,
                "camera_id": DEVICE_ID,
                "latitude": lat,
                "longitude": lon,
                "start_time": time_converter.to_iso_format(start_time),
            }
            
            self._update_alert_data(alert_data, detection_class)
            active_data = self.active_alert_data.copy()

        try:
            logger.info(f"[ALERT SENT] Created alert {alert_id} at {start_time}")
            self._send_to_endpoint(active_data)
        except Exception as e:
            logger.error(f"[ALERT ERROR] Failed to send alert: {e}")
            with self._lock:
                if self.active_alert_data and self.active_alert_data["id"] == alert_id:
                    self.is_alert_active = False
                    self.active_alert_data = None

    def _update_alert_on_exit_sync(self, end_time):
        """Update the active alert with exit time."""
        with self._lock:
            if not self.is_alert_active or self.active_alert_data is None:
                logger.warning("[ALERT] No active alert to update on exit!")
                return

            # Make a copy to avoid race conditions
            alert_data = self.active_alert_data.copy()
            self.is_alert_active = False
            self.active_alert_data = None

        # Release lock before I/O
        alert_data["end_time"] = time_converter.to_iso_format(end_time)
        start_time = time_converter.from_iso_format(alert_data['start_time'])
        end_time = time_converter.from_iso_format(alert_data['end_time'])
        alert_data["duration"] = (end_time - start_time).total_seconds()
        
        logger.info(f"[ALERT UPDATE] Updating alert {alert_data['id']} with exit at {end_time}")
        
        clips = self.get_clips_in_range(start_time=start_time, end_time=end_time, path=RECORDINGS_DIR)
        print(clips)
        if not clips:
            logger.warning("[ALERT] No clips found for alert range.")
            self._send_to_endpoint(alert_data, clips=[], update=True)
            return

        last_clip_name = clips[-1] 
        last_clip_start = datetime.strptime(last_clip_name[:-4], TIMESTAMP_FORMAT)
        last_clip_end = last_clip_start + timedelta(seconds=RECORD_DURATION + 2) # Add 2s buffer

        # Current time in UTC
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if last_clip_end > now:
            sleep_seconds = (last_clip_end - now).total_seconds()
            logger.info(f"[ALERT] Waiting {sleep_seconds:.1f}s for last clip to finish recording...")
            time.sleep(sleep_seconds)
        else:
            logger.info("[ALERT] Last clip already complete. Proceeding immediately.")

        try:
            logger.info(f"[ALERT UPDATE] Updating alert {alert_data['id']} with exit at {end_time}")
            self._send_to_endpoint(alert_data, clips=clips, update=True)
        except Exception as e:
            logger.error(f"[ALERT ERROR] Failed to update alert: {e}")
    
    def _update_alert_data(self, alert_data, detection_class: str):
        
        if detection_class == 'person':
            alert_data['message'] = 'Person entered in a restricted area.'
            alert_data['severity'] = 'high'
        else:
            alert_data['message'] = 'Person detected with no safety equipment.'
            alert_data['severity'] = 'medium'
        
        self.is_alert_active = True
        self.active_alert_data = alert_data
    
    def get_clips_in_range(self, start_time: datetime, end_time: datetime, path: str = None):
        """
        Find all 30s clip files that overlap with [start_time, end_time].
        Return the list of clips available in the range.
        """
        
        start_time = start_time.replace(tzinfo=None)
        end_time = end_time.replace(tzinfo=None)
        
        if not os.path.exists(path):
            logger.error(f"[ERROR] Video folder not found: {path}")
            return []
        
        relevant_clips = []
        for filename in os.listdir(path):
            if not filename.endswith(".mp4"):
                continue

            try:
                base_name = filename[:-4] # remove .mp4
                clip_start = datetime.strptime(base_name, TIMESTAMP_FORMAT)
                clip_end = clip_start + timedelta(seconds=RECORD_DURATION)

                if start_time < clip_end and clip_start < end_time:
                    relevant_clips.append(filename)
            except ValueError:
                logger.warning(f"[WARNING] Filename {filename} does not match timestamp format.")
                continue

        relevant_clips.sort()
        return relevant_clips

    def _send_to_endpoint(self, data, clips: list = None, update=False):
        
        clips = clips or []
        if clips and update:
            return self.send_clips_as_zip_chunks(url=ALERT_URL,path=RECORDINGS_DIR, payload=data, clips=clips)
        else:
            return RestUtil.send_data(url=ALERT_URL, body=data, method='POST', payload_type='plain')
    
    def send_clips_as_zip_chunks(self, url: str, path: str, payload, clips: list):

        # Step 1: Create full ZIP in memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for filename in clips:
                file_path = os.path.join(path, filename)
                if os.path.exists(file_path):
                    zf.write(file_path, arcname=filename)
        full_zip_data = zip_buffer.getvalue()
        total_size = len(full_zip_data)
        
        payload["device_id"] = DEVICE_ID
        
        logger.info(f"[CHUNK] Full ZIP size: {total_size / (1024*1024):.2f} MB")

        # Step 2: Split into chunks (max 19 MB to be safe)
        MAX_CHUNK_SIZE = 19 * 1024 * 1024  # 19 MB
        total_chunks = ceil(total_size / MAX_CHUNK_SIZE)
        
        id = payload["id"]
        chunk_upload_url = f"{url.rstrip('/')}/{id}/chunks/"

        # Step 3: Upload each chunk
        for i in range(total_chunks):
            start = i * MAX_CHUNK_SIZE
            end = min(start + MAX_CHUNK_SIZE, total_size)
            chunk_data = full_zip_data[start:end]

            chunk_files = {
                'chunk': (f'chunk_{i}.bin', chunk_data, 'application/octet-stream')
            }
            chunk_form = {
                'id': id,
                'chunk_index': str(i),
                'total_chunks': str(total_chunks),
                'device_id': DEVICE_ID
            }

            logger.info(f"[CHUNK] Uploading chunk {i+1}/{total_chunks} ({len(chunk_data) / 1e6:.2f} MB)")
            
            try:
                RestUtil.send_data(
                    url=chunk_upload_url,
                    method='POST',
                    files=chunk_files,
                    body=chunk_form
                )
            except Exception as e:
                logger.error(f"[CHUNK] Failed to upload chunk {i}: {e}")
                raise

        # Step 4: Finalize upload
        logger.info(f"[CHUNK] Finalizing upload for [record]: {id}")
        finalize_url = f"{url.rstrip('/')}/{id}/"
        finalize_data = payload
        finalize_data['upload_complete'] = 'true'
        finalize_data['total_chunks'] = str(total_chunks)
        finalize_data['zip_size_bytes'] = str(total_size)

        # Convert all values to string for form data
        form_data = {k: str(v) if v is not None else '' for k, v in finalize_data.items()}
        
        return RestUtil.send_data(
            url=finalize_url,
            method='PATCH',
            body=form_data
        )
    
    def upload_camera_recordings(self, alert_data, start_time, end_time):
        """Upload recordings from nearby cameras for the given alert."""
        # Implementation would be similar to _send_clips_as_zip_chunks,

        start_time = time_converter.from_iso_format(start_time)
        end_time = time_converter.from_iso_format(end_time)
        
        clips = self.get_clips_in_range(start_time, end_time, path=RECORDINGS_DIR)
        
        if not clips:
            logger.warning("[ALERT] No clips found for alert range.")
            # Still send alert without clips
            self._send_to_endpoint(alert_data, clips=[], update=True)
            return

        last_clip_name = clips[-1] 
        last_clip_start = datetime.strptime(last_clip_name[:-4], TIMESTAMP_FORMAT)
        last_clip_end = last_clip_start + timedelta(seconds=RECORD_DURATION + 2) # Add 2s buffer

        # Current time
        now = datetime.now()

        if last_clip_end > now:
            sleep_seconds = (last_clip_end - now).total_seconds()
            logger.info(f"[ALERT] Waiting {sleep_seconds:.1f}s for last clip to finish recording...")
            time.sleep(sleep_seconds)
        else:
            logger.info("[ALERT] Last clip already complete. Proceeding immediately.")

        try:
            logger.info(f"[ALERT UPDATE] Updating alert {alert_data['id']} with exit at {end_time}")
            self._send_to_endpoint(alert_data, clips=clips, update=True)
        except Exception as e:
            logger.error(f"[ALERT ERROR] Failed to update alert: {e}")