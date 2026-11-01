import os
import logging
import shutil
import zipfile
import subprocess
import tempfile
import re

from io import BytesIO
from django.conf import settings
from django.core.files import File
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.timezone import make_aware, is_naive

from mediahub.models import MediaFile
from cc_alerts.models import Alert, AlertDevice, AlertStatus
from inference_engine.models import InferenceVideoStatus

from datetime import timedelta, datetime
from inference_engine.logging_config import setup_logging
from inference_engine.modify_analysis import modify_analysis
from inference_engine.check_detections import check_person_in_video

from inference_engine.tasks import (
    append_and_save_message, run_analysis_on_video, 
    merge_videos, fetch_video_clip, infer_status
)

from device_configuration.device_services import update_device_status

from sensegrid.config import send_ws_update

logger = logging.getLogger(__name__)
setup_logging()


def reassemble_and_process_alert_zip(alert_device_id, total_chunks):
    alert_device = None
    try:
        alert_device = AlertDevice.objects.get(id=alert_device_id)
        alert = alert_device.alert
        
        chunk_dir_name = f'alert_{alert.id}_device_{alert_device.device.id}'

        chunk_dir = os.path.join(settings.MEDIA_ROOT, 'alert_chunks', chunk_dir_name)
        zip_buffer = bytearray()

        # Reassemble in order
        for i in range(total_chunks):
            chunk_path = os.path.join(chunk_dir, f'chunk_{i}.bin')
            if not os.path.exists(chunk_path):
                raise FileNotFoundError(f"Missing chunk {i}")
            with open(chunk_path, 'rb') as f:
                zip_buffer.extend(f.read())

        # Validate ZIP
        try:
            with zipfile.ZipFile(BytesIO(zip_buffer)) as zf:
                zf.testzip()
        except Exception as e:
            raise ValueError(f"Alert {alert.id}, Invalid ZIP after reassembly: {e}")

        merge_and_trim_alert(alert_device, zip_buffer)

        # Cleanup chunks
        for f in os.listdir(chunk_dir):
            os.remove(os.path.join(chunk_dir, f))
        os.rmdir(chunk_dir)
        
        message = f'''The start of the alert: {str(alert.start_time)}, the end of the alert: {str(alert.end_time)}.
        Camera name: {alert_device.device.name}. 
        Detection class: {alert.detection_class}.
        Duration: {alert.duration}
        Location: [Longitude: {alert.longitude}, Latitude: {alert.latitude}]
        '''
        
        if alert_device.primary_device:
            append_and_save_message(alert, message)
            
            if check_person_in_video(alert_device.video_file.file.path):
                alert.alert_analysis = AlertStatus.HUMAN_VERIFICATION
                alert.save()
                
                send_ws_update(
                    group_name="alert_updates",
                    type="alert.verify",
                    message={
                        "alert_id": str(alert.id),
                        "status": alert.alert_analysis,
                        "is_camera": True,
                    }
                )
            else:
                alert.alert_analysis = AlertStatus.COMPLETE
                alert.save()
            
            modify_analysis(alert, alert.message, alert.inference_analysis)
                
        return {"message": f"Alert {alert.id} reassembled and processed."}

    except Exception as e:
        logger.error(f"Alert {alert.id}, Chunk reassembly failed for alert device {alert_device_id}: {e}", exc_info=True)
        if alert_device:
            failure_reason = "Chunk reassembly failed"
            update_device_status(alert_device, failed=True, failure_reason=failure_reason)
        return {"error": f"Failed to reassemble chunks for alert device {alert_device_id}.", "message": str(e)}


def merge_and_trim_alert(alert_device, zip_buffer):
    try:
        alert = alert_device.alert

        with tempfile.TemporaryDirectory(prefix=f"extract_alert_{alert.id}_") as temp_dir:
            with zipfile.ZipFile(BytesIO(zip_buffer), 'r') as zf:
                zf.extractall(temp_dir)
                clip_paths = [
                    os.path.join(temp_dir, name)
                    for name in zf.namelist()
                    if name.lower().endswith('.mp4') and not name.endswith('/')
                ]

            if not clip_paths:
                logger.warning(f"No MP4 files in ZIP for alert {alert.id}")
                raise ValueError(f"No MP4 files in ZIP for alert {alert.id}")

            merged_path = _merge_and_trim_clips(clip_paths, alert)
            
            logger.info(f"Finished merging and trimming clips for alert {alert.id}")

            if not merged_path:
                logger.error(f"Failed to merge and trim clips for alert {alert.id}.")
                raise FileNotFoundError(f"Failed to merge and trim clips for alert {alert.id}.")
            
            # Save final video
            media_file = MediaFile(
                title=f"Video for Alert {alert.id} from Device {alert_device.device.name}",
                description=f"Alert video clips for alert {alert.id} from device {alert_device.device.name} "
                            f"from {alert.start_time} to {alert.end_time}",
                media_type='video',
                mime_type='video/mp4',
                is_public=False
            )

            safe_camera_name = re.sub(r'[^\w\-_\.]', '_', alert_device.device.name)
            video_filename = f"alert_{alert.id}_device_{safe_camera_name}.mp4"
            with open(merged_path, 'rb') as f:
                media_file.file.save(video_filename, File(f), save=True)
            
            media_file.file_size = os.path.getsize(merged_path)
            media_file.save()
            
            with transaction.atomic():
                alert_device.video_file = media_file
                alert_device.save()
                
                update_device_status(alert_device)

            logger.info(f"Saved final video for alert {alert.id}")

            try:
                os.remove(merged_path)
            except OSError:
                pass
    except Exception as e:
        logger.error(f"Alert {alert_device.alert.id}, failed to merge and trim: {e}", exc_info=True)
        with transaction.atomic():
            failure_reason = "Video merge and trim failed"
            update_device_status(alert_device, failed=True, failure_reason=failure_reason)

            alert = alert_device.alert
            alert.alert_analysis = AlertStatus.FAILED
            alert.save()


def _parse_timestamp_from_filename(filename: str):
    """Extract datetime from '20250908_122705.mp4' → datetime(2025, 9, 8, 12, 27, 5)"""
    basename = os.path.splitext(filename)[0]
    match = re.match(r'(\d{8})_(\d{6})', basename)
    if not match:
        return None
    date_str, time_str = match.groups()
    try:
        dt = datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
        return make_aware(dt)
    except ValueError:
        return None


def _merge_and_trim_clips(clip_paths, alert):
    """
    Merge and trim clips based on alert.start_time and alert.end_time.
    
    Args:
        clip_paths: List of paths to .mp4 files (e.g., ['/tmp/.../20250908_122705.mp4', ...])
        alert: Alert model instance (must have start_time, end_time as datetime)
    
    Returns:
        Path to final merged/trimmed video file (inside a temp dir), or None on failure.
    """
    start_time = alert.start_time  # datetime
    end_time = alert.end_time      # datetime
    
    if is_naive(start_time):
        start_time = make_aware(start_time)
    if is_naive(end_time):
        end_time = make_aware(end_time)
    
    # Ensure start_time is at least 2 seconds before alert start for context
    start_time = start_time - timedelta(seconds=2)

    if not start_time or not end_time:
        logger.error(f"Alert {alert.id} missing start_time or end_time")
        return None

    # Parse clips with timestamps
    clip_info = []
    for path in clip_paths:
        ts = _parse_timestamp_from_filename(os.path.basename(path))
        if ts:
            clip_info.append({
                'path': path,
                'start': ts,
                'end': ts + timedelta(seconds=30)  # each clip is 30s
            })
        else:
            logger.warning(f"Skipping invalid filename: {path}")

    if not clip_info:
        logger.error(f"No valid clips to process for alert {alert.id}")
        return None

    clip_info.sort(key=lambda x: x['start'])

    # Find overlapping clips
    relevant = [
        clip for clip in clip_info
        if clip['start'] < end_time and clip['end'] > start_time
    ]

    if not relevant:
        logger.warning(f"No clips overlap time window for alert {alert.id}")
        return None

    output_temp_dir = tempfile.mkdtemp(prefix=f"merged_alert_{alert.id}_")
    output_path = os.path.join(output_temp_dir, "merged_alert.mp4")

    try:
        # Step 1: Prepare trimmed segments
        segment_list = []
        for i, clip in enumerate(relevant):
            seg_path = os.path.join(output_temp_dir, f"seg_{i:03d}.mp4")
            
            # Calculate trim start (in seconds from clip start)
            trim_start = max(0, (start_time - clip['start']).total_seconds())
            # Calculate duration to keep
            clip_end_for_alert = min(clip['end'], end_time)
            duration = (clip_end_for_alert - max(clip['start'], start_time)).total_seconds()
            duration = max(0.1, duration)  # avoid zero/negative

            # Build ffmpeg command
            cmd = [
                'ffmpeg',
                '-y',
                '-ss', str(trim_start),
                '-i', clip['path'],
                '-t', str(duration),
                '-c:v', 'libx264',          # H.264 video
                '-movflags', '+faststart',  # Web streaming support
                '-preset', 'fast',
                '-crf', '23',
                seg_path
            ]
            logger.debug(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                logger.error(f"FFmpeg failed for {clip['path']}: {result.stderr.decode()}")
                return None
            segment_list.append(seg_path)

        # Step 2: Merge segments
        if len(segment_list) == 1:
            # Only one segment → just rename
            os.rename(segment_list[0], output_path)
        else:
            # Create concat list
            concat_file = os.path.join(output_temp_dir, "concat.txt")
            with open(concat_file, 'w') as f:
                for seg in segment_list:
                    # Escape backslashes for Windows (ffmpeg requires forward slashes or escaped paths)
                    f.write(f"file '{os.path.abspath(seg).replace(os.sep, '/')}'\n")

            # Run concat
            cmd = [
                'ffmpeg',
                '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c:v', 'libx264',
                '-movflags', '+faststart',
                '-preset', 'fast',
                '-crf', '23',
                output_path
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                logger.error(f"FFmpeg concat failed: {result.stderr.decode()}")
                return None

        logger.info(f"Successfully merged {len(relevant)} clips for alert {alert.id} → {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Alert {alert.id}, Error during ffmpeg processing: {e}")
        return None


def run_inference_for_event(event_id):
    """
    Run inference on pending alerts.
    """
    
    try:
        alert_device = AlertDevice.objects.get(id=event_id)
    except AlertDevice.DoesNotExist:
        return {"error": f"Alert with ID {event_id} not found."}
    
    status = InferenceVideoStatus.objects.filter(alert_device=alert_device).first()
    alert = alert_device.alert
    
    start_timestamp = alert.start_time
    state = 'initial'
    
    if status:
        start_timestamp = status.start_time
        state = status.state
    else:
        status = InferenceVideoStatus.objects.create(alert_device=alert_device, start_time=start_timestamp, state=state)
    
    if not alert_device.video_file_for_process:
        return save_status_for_next_clip(alert_device, status, alert.start_time, status.start_frame, status.end_frame, status.fps, status.frame_width, status.frame_height, 'post')
        
    append_and_save_message(alert, f"The safety issue began on :  {start_timestamp.strftime('%B %d, %Y at %I:%M %p')} and was recorded at : {alert.start_time.strftime('%B %d, %Y at %I:%M %p')} from camera: {alert_device.device.name}.")
    
    if is_naive(start_timestamp):
        start_timestamp = make_aware(start_timestamp)
        
    logger.info(f"Started inferencing for alert {alert.id} alert device {event_id} at {start_timestamp} from camera: {alert_device.device.name}")
    
    # Initial call to the recursive function with an empty state
    return continue_event_inference(alert_device=alert_device, alert=alert, status=status, start_timestamp=start_timestamp, start_frame=status.start_frame, end_frame=status.end_frame, state=state)


def continue_event_inference(alert_device: AlertDevice, alert: Alert, status: InferenceVideoStatus, start_timestamp: datetime, start_frame=None, end_frame=None, state: str=''):
    
    if not alert_device.video_file_for_process or not alert_device.video_file_for_process.file.path:
        if status.state != 'initial':
            update_device_status(alert_device)
            return merge_video_clips(status=status)
        alert_device.failure_reason = "Initial video not found for inference."
        alert_device.save()
        logger.critical("Inference started but no initial video found. Cannot proceed.")
        return merge_video_clips(status=status, video_status='failed')

    video_path = alert_device.video_file_for_process.file.path
    if not os.path.exists(video_path):
        failure_reason = "Video file not found"
        update_device_status(alert_device, failed=True, failure_reason=failure_reason)
        logger.critical(f"Inference started but video file not found at path: {video_path}. Cannot proceed.")
        return merge_video_clips(status=status, video_status='failed')
    
    logger.info(f"Analyzing current video segment: {video_path}")
    try:
        person_violation_map_segment, fps, total_frames, frame_width, frame_height = run_analysis_on_video(video_path=video_path, alert=alert)
    except Exception as e:
        logger.error(f"Alert {alert.id}, Error during video analysis: {e}", exc_info=True)
        failure_reason = "Video analysis failed"
        update_device_status(alert_device, failed=True, failure_reason=failure_reason)
        return {"status": "inference_failed", "event_id": str(alert.id)}

    if not person_violation_map_segment:
        logger.info(f"No safety violations detected in the current video segment ({state} state).")
        
        if state == 'initial':
            with transaction.atomic():
                alert_device.video_file = alert_device.video_file_for_process
                update_device_status(alert_device)
                alert.alert_analysis = AlertStatus.COMPLETE
                alert_device.save()
                status.save()
            append_and_save_message(alert, "Inference completed. No safety violations were detected in the video.")
            return {"status": "No violation detected in the video."}
        
        else:
            return merge_video_clips(status)

    all_starts = [v[0] for v in person_violation_map_segment.values()]
    all_ends = [v[1] for v in person_violation_map_segment.values()]
    
    # Calculate the start and end frames for the current segment's analysis.
    segment_start_frame = min(all_starts)
    segment_end_frame = max(all_ends)
    
    total_frames = segment_end_frame if segment_end_frame > total_frames else total_frames

    # Update the overall event boundaries
    if start_frame == 0:
        start_frame = segment_start_frame if segment_start_frame else 1
        
    if end_frame == 0 and (total_frames - segment_end_frame) > 0:
        end_frame = segment_end_frame
        
    status.clip_count = status.clip_count + 1
    status.total_frames = status.total_frames + total_frames
    
    logger.info(f"Start frame: {start_frame}, End frame: {end_frame}, Total frames: {total_frames} after finding segment frames. Segment frames: {segment_start_frame} to {segment_end_frame}.")
    

    status.add_clip_at_end(alert_device.video_file_for_process)
    logger.info("---------------------Added clip at the end of the list")

    logger.info(f"Violations detected in current clip. Segment frames: {segment_start_frame} to {segment_end_frame}. Overall event frames: {start_frame} to {end_frame}.")

    if start_frame and end_frame:
        status.start_frame = start_frame
        status.end_frame = end_frame
        status.save()
        return merge_video_clips(status=status)

    # Case: We need to find the end of the event.
    if not end_frame:
        logger.info("Violation continued to the end of the clip. Fetching post-event video.")
        
        save_status_for_next_clip(alert_device, status, start_timestamp, start_frame, end_frame, fps, frame_width, frame_height, "post")
        return {"status": "fetching_post_clip", "event_id": str(alert.id)}
    
    logger.warning(f"Unhandled case in continue_event_inference. "
               f"State={state}, segment_start={segment_start_frame}, segment_end={segment_end_frame}, total_frames={total_frames}")
    
    append_and_save_message(alert, f"Unhandled case in continue_event_inference. State={state}, segment_start={segment_start_frame}, segment_end={segment_end_frame}, total_frames={total_frames}")

    alert_device.status = "failed"
    alert_device.save()
    status.save()
    
    return {
        "status": "inference_failed",
        "event_id": str(alert.id),
        "state": state,
        "start_frame": start_frame,
        "end_frame": end_frame,
    }


def finalize_event(alert_device: AlertDevice, status: InferenceVideoStatus, video_path, start_timestamp: datetime, start_frame, end_frame, fps, video_status='uploaded'):

    alert = alert_device.alert
    if status.start_frame is None or status.end_frame is None:
        logger.error("Missing frame boundaries for finalize_event.")
        alert_device.status = 'failed'
        alert_device.failure_reason = "Missing frame boundaries for finalize_event."
        alert_device.save()
        return {"status": "failed", "reason": "missing frame boundaries"}

    logger.info(f"Finalizing event. Alert {alert.id} alert device {alert_device.id}, total_frames: {status.total_frames}, clip_count: {status.clip_count}")

    # Save the trimmed video to the database
    with open(video_path, "rb") as f:
        file_data = f.read()
        safe_name = f"event_{str(alert.id)[:8]}_final.mp4"
        mediafile = MediaFile.objects.create(file=ContentFile(file_data, name=safe_name), 
            media_type="video",
            title=safe_name,
            file_size=os.path.getsize(video_path),
            mime_type="video/mp4",
        )
        alert_device.video_file = mediafile

        enforce_media_storage_limit()

    os.remove(video_path)

    with transaction.atomic():
        update_device_status(alert_device)
        alert_device.save()

        end = max(0, status.total_frames - status.start_frame)

        if end:
            end *= 2

        alert.end_time = alert.start_time + timedelta(seconds=end / fps)
        alert.save()
    
    if video_status == 'uploaded':
        append_and_save_message(alert, "The final event video has been saved successfully and is ready to watch.")
        append_and_save_message(alert, f"The safety incident started at: {start_timestamp.strftime('%B %d, %Y at %I:%M %p')}. It ended at: {alert.end_time.strftime('%B %d, %Y at %I:%M %p')}. The total duration was {alert.end_time - alert.start_time}.")
    elif video_status == 'failed':
        append_and_save_message(alert, "Video failed to be saved due to missing footage.")
    
    modify_analysis(alert)
    
    alert_device.video_file_for_process.delete()
    alert_device.video_file_for_process = None
    alert_device.save()

    logger.info(f"Final event video saved. Status: {infer_status(start_frame, end_frame)}.")

    return {
        "event_id": str(alert.id),
        "start_time": (start_frame / fps),
        "end_time": (end_frame / fps),
        "video_duration": (alert.end_time - alert.start_time).total_seconds(),
        "status": infer_status(start_frame, end_frame),
        "clip_path": mediafile.file.url if mediafile else None
    }


def merge_video_clips(status: InferenceVideoStatus, video_status='uploaded'):
    
    logger.info(f"Merging video clips for alert {status.alert_device.alert.id} alert device {status.alert_device.id}")
    
    media_files = status.get_clips()   # ordered MediaFile objects
    video_paths = [mf.file.path for mf in media_files]
    
    output_dir = f'{settings.MEDIA_ROOT}/clips'
    os.makedirs(output_dir, exist_ok=True) # Ensure output directory exists
    output_file = f"output{str(status.id)[:8]}.mp4"
    output_path = os.path.join(output_dir, output_file)
    
    if video_paths:
        try:
            output_path = merge_videos(video_paths=video_paths, output_path=output_path)
            return finalize_event(alert_device=status.alert_device, status=status, video_path=output_path, start_timestamp=status.start_time, start_frame=status.start_frame, end_frame=status.end_frame, fps=status.fps, video_status=video_status)  
        except Exception as e:
            logger.error(f"Alert {status.alert_device.alert.id}, Error merging video clips: {e}", exc_info=True)
            failure_reason = "Video merging failed"
            update_device_status(status.alert_device, failed=True, failure_reason=failure_reason)
            return {"status": "inference_failed", "event_id": str(status.alert_device.alert.id)}
    
    failure_reason = "No video paths provided for merging."
    update_device_status(status.alert_device, failed=True, failure_reason=failure_reason)
    return {"status": "inference_failed", "event_id": str(status.alert_device.alert.id)}  


def save_status_for_next_clip(alert_device: AlertDevice, status: InferenceVideoStatus, start_timestamp, start_frame, end_frame, fps, frame_width, frame_height, state):
    
    if isinstance(start_timestamp, str):
        start_timestamp = datetime.strptime(start_timestamp, settings.TIMESTAMP_FORMAT)

    offset = timedelta(seconds=30)
    if state == "post":
        start_timestamp += offset
    else:
        raise ValueError(f"Unknown state: {state}")
    
    formatted_timestamp = start_timestamp.strftime(settings.TIMESTAMP_FORMAT)
    
    status.start_time = start_timestamp
    status.start_frame = start_frame
    status.end_frame = end_frame
    status.fps = fps
    status.frame_width = frame_width
    status.frame_height = frame_height
    status.state = state
    status.save()

    logger.info(f"Saving status for next clip. Alert {alert_device.alert.id} alert device {alert_device.id}, Timestamp: {formatted_timestamp}, State: {state}")
    
    fetch_video_clip(alert_device.alert.id, alert_device.device.id, formatted_timestamp, 30)
    
    
def enforce_media_storage_limit(threshold: float = 0.7):
    total, used, free = shutil.disk_usage(settings.MEDIA_ROOT)
    usage_ratio = used / total

    logger.info(f"Disk usage check: {usage_ratio:.2%} (limit {threshold:.0%})")

    if usage_ratio < threshold:
        return

    old_files = MediaFile.objects.order_by("uploaded_at")

    for media in old_files:
        file_path = media.file.path

        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.warning(f"Deleted old media file: {file_path}")
            else:
                logger.warning(f"File missing, removing DB entry: {file_path}")

            media.delete()

        except Exception as e:
            logger.error(f"Cleanup error for {file_path}: {e}")
            continue

        total, used, free = shutil.disk_usage(settings.MEDIA_ROOT)
        usage_ratio = used / total
        if usage_ratio < threshold:
            logger.info("Disk usage back under threshold.")
            break
