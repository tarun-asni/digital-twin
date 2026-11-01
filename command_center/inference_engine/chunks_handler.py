import os
import logging
import zipfile
import subprocess
import tempfile

from io import BytesIO
from django.conf import settings
from django.core.files import File
from cc_alerts.models import DroneFlight, AlertStatus, AlertDevice
from device_configuration.models import Device
from mediahub.models import MediaFile
from sensegrid.config import send_ws_update

from inference_engine.check_detections import check_person_in_video
from inference_engine.modify_analysis import modify_analysis


logger = logging.getLogger(__name__)

def reassemble_and_process_chunks(id, total_chunks):
    try:
        drone_flight = DroneFlight.objects.get(id=id)

        chunk_dir = os.path.join(settings.MEDIA_ROOT, 'chunks', str(drone_flight.id))
        zip_buffer = bytearray()

        for i in range(total_chunks):
            chunk_path = os.path.join(chunk_dir, f'chunk_{i}.bin')
            if not os.path.exists(chunk_path):
                raise FileNotFoundError(f"Missing chunk {i}")
            with open(chunk_path, 'rb') as f:
                zip_buffer.extend(f.read())

        try:
            with zipfile.ZipFile(BytesIO(zip_buffer)) as zf:
                if zf.testzip():
                    raise ValueError("Corrupted file in ZIP")
        except Exception as e:
            raise ValueError(f"Invalid ZIP: {e}")

        with tempfile.TemporaryDirectory(prefix=f"drone_flight_{drone_flight.id}_") as temp_dir:
            with zipfile.ZipFile(BytesIO(zip_buffer)) as zf:
                mp4_files = [
                    name for name in zf.namelist()
                    if name.lower().endswith('.mp4') and not name.endswith('/')
                ]
                if not mp4_files:
                    raise ValueError("No .mp4 files found in ZIP")
                zf.extractall(temp_dir, members=mp4_files)

            clip_paths = [os.path.join(temp_dir, name) for name in mp4_files]
            clip_paths.sort(key=lambda p: os.path.basename(p))

            merged_path = _merge_mp4_clips(clip_paths, temp_dir)
            if not merged_path:
                raise RuntimeError("Failed to merge video clips")

            # Save to MediaFile
            video_filename = f"drone_flight_{drone_flight.id}.mp4"
            media_file = MediaFile(
                title=f"Video for Drone Flight {drone_flight.id}",
                description=f"Merged video clips for drone flight {drone_flight.id}",
                media_type='video',
                mime_type='video/mp4',
                is_public=False
            )
            with open(merged_path, 'rb') as f:
                media_file.file.save(video_filename, File(f), save=True)

            media_file.file_size = os.path.getsize(merged_path)
            media_file.save()

            drone_flight.video_file = media_file
            drone_flight.sensor_alert.status = AlertStatus.COMPLETE
            drone_flight.sensor_alert.save()
            drone_flight.save()
            
            sensor_alert = drone_flight.sensor_alert
            
            alert_device = None
            
            if sensor_alert.alert:
                alert_device =AlertDevice.objects.filter(
                    alert=sensor_alert.alert,
                    device=Device.objects.get(id=drone_flight.drone.id),
                ).first()
            else:
                alert_device =AlertDevice.objects.filter(
                    sensor_alert=sensor_alert,
                    device=Device.objects.get(id=drone_flight.drone.id),
                ).first()
                sensor_alert_device = AlertDevice.objects.filter(
                    sensor_alert=sensor_alert,
                    device=Device.objects.get(id=sensor_alert.sensor.id)
                ).first()
                sensor_alert_device.recording_end = drone_flight.end_time
                sensor_alert_device.status = 'uploaded'
                sensor_alert_device.save()

            alert_device.video_file = media_file
            alert_device.status = 'uploaded'
            alert_device.recording_end = drone_flight.end_time
            alert_device.save()
            
            payload = {}
            if not sensor_alert.alert:
                
                if check_person_in_video(media_file.file.path):
                    
                    sensor_alert.status = AlertStatus.HUMAN_VERIFICATION
                    
                    sensor_alert.llm_response = f'''
                    Person detected in drone footage. 
                    start time: {drone_flight.start_time},
                    end time: {drone_flight.end_time}
                    '''
                    sensor_alert.save()
                    
                    modify_analysis(alert=sensor_alert, message=sensor_alert.llm_response)
                    
                    payload = {
                        "alert_id": str(sensor_alert.id),
                        "status": sensor_alert.status,
                        "is_camera": False
                    }
                    
                    # Websocket message for approval.
                    send_ws_update(
                        message=payload,
                        group_name="alert_updates",
                        type="alert.verify"
                    )
                else:
                    sensor_alert.llm_response = f"""
                    Object detected in drone footage.
                    No person found.
                    start time: {drone_flight.start_time},
                    end time: {drone_flight.end_time}
                    """
                    sensor_alert.save()
                    
                    modify_analysis(alert=sensor_alert, message=sensor_alert.llm_response)
            else:
                payload = {
                        "alert_id": str(sensor_alert.alert.id) if sensor_alert.alert else None,
                        "status": sensor_alert.alert.alert_analysis if sensor_alert.alert else None
                    }
                
                sensor_alert.status = AlertStatus.COMPLETE
                sensor_alert.save()
                
                send_ws_update(
                    group_name="alert_updates",
                    type="alert.complete",
                    message=payload
                )
                

        # Cleanup chunks
        if os.path.exists(chunk_dir):
            for filename in os.listdir(chunk_dir):
                os.remove(os.path.join(chunk_dir, filename))
            os.rmdir(chunk_dir)

        logger.info(f"Successfully processed DroneFlight {drone_flight.id}")
        return {"success": True, "media_file_id": media_file.id}

    except DroneFlight.DoesNotExist:
        error_msg = f"DroneFlight with id {id} does not exist."
        logger.error(error_msg)
        return {"error": error_msg}
    except Exception as e:
        drone_flight.sensor_alert.status = AlertStatus.FAILED
        drone_flight.sensor_alert.save()
        logger.error(f"Failed to process DroneFlight {id}: {e}", exc_info=True)
        return {"error": f"Processing failed for DroneFlight {id}.", "message": str(e)}


def _merge_mp4_clips(clip_paths, temp_dir):
    """
    Merge clips into a file inside `temp_dir`.
    """
    if not clip_paths:
        return None

    output_path = os.path.join(temp_dir, "merged_flight.mp4")

    try:
        if len(clip_paths) == 1:
            cmd = [
                'ffmpeg',
                '-y',
                '-i', clip_paths[0],
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-movflags', '+faststart',
                '-preset', 'fast',
                '-crf', '23',
                output_path
            ]
        else:
            concat_file = os.path.join(temp_dir, "concat.txt")
            with open(concat_file, 'w') as f:
                for path in clip_paths:
                    abs_path = os.path.abspath(path).replace('\\', '/')
                    f.write(f"file '{abs_path}'\n")

            cmd = [
                'ffmpeg',
                '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-movflags', '+faststart',
                '-preset', 'fast',
                '-crf', '23',
                output_path
            ]

        logger.debug(f"Running FFmpeg: {' '.join(cmd)}")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            logger.error(f"FFmpeg failed: {result.stderr}")
            return None

        return output_path

    except Exception as e:
        logger.error(f"Error merging clips in temp_dir {temp_dir}: {e}")
        return None