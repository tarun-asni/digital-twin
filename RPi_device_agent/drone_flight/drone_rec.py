import os
import zipfile
import logging
import math
from io import BytesIO
from utils.RestUtil import RestUtil
from camera_stream.config import RECORDINGS_DIR

logger = logging.getLogger(__name__)

CHUNK_SIZE = 19 * 1024 * 1024  # 19MB chunks

def send_recordings_to_command_center(drone_controller):
    """
    Collects MP4 recordings from RECORDINGS_DIR, zips them, splits into chunks,
    sends to command center via chunks endpoint, and cleans up local files.
    """
    if not drone_controller.drone_flight_id:
        logger.warning("No drone_flight_id set, skipping sending recordings.")
        return

    # Collect MP4 files
    mp4_files = [f for f in os.listdir(RECORDINGS_DIR) if f.lower().endswith('.mp4')]
    if not mp4_files:
        logger.info("No MP4 recordings found to send.")
        return

    logger.info(f"Found {len(mp4_files)} MP4 files to send.")

    # Create ZIP in memory
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for mp4_file in mp4_files:
            file_path = os.path.join(RECORDINGS_DIR, mp4_file)
            zf.write(file_path, mp4_file)
    zip_data = zip_buffer.getvalue()

    # Calculate chunks
    total_chunks = math.ceil(len(zip_data) / CHUNK_SIZE)
    logger.info(f"Sending {total_chunks} chunks for drone flight {drone_controller.drone_flight_id}.")

    url = f"{drone_controller.COMMAND_CENTER_URL}/cc-alerts/drone-flight/{drone_controller.drone_flight_id}/chunks/"

    for chunk_index in range(total_chunks):
        start = chunk_index * CHUNK_SIZE
        end = min(start + CHUNK_SIZE, len(zip_data))
        chunk = zip_data[start:end]

        # Prepare payload as multipart/form-data
        data = {
            'chunk_index': str(chunk_index),
            'total_chunks': str(total_chunks)
        }
        files = {
            'chunk': ('chunk.bin', BytesIO(chunk), 'application/octet-stream')
        }

        try:
            response = RestUtil.send_data(url, body=data, files=files, method="POST")
            if response.ok:
                logger.info(f"Sent chunk {chunk_index + 1}/{total_chunks} successfully.")
            else:
                logger.error(f"Failed to send chunk {chunk_index + 1}: {response.status_code} {response.text}")
                return  # Stop on failure
        except Exception as e:
            logger.error(f"Exception sending chunk {chunk_index + 1}: {e}")
            return

    # Cleanup: delete local MP4 files
    for mp4_file in mp4_files:
        file_path = os.path.join(RECORDINGS_DIR, mp4_file)
        try:
            os.remove(file_path)
            logger.info(f"Deleted local file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete {file_path}: {e}")

    logger.info("All recordings sent and local files cleaned up.")
