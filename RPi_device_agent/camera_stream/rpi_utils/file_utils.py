import os
from datetime import datetime, timedelta
from ..config import (RECORDINGS_DIR, TIMESTAMP_FORMAT)


def find_recording_files(start_time: datetime, duration_sec: int):
    end_time = start_time + timedelta(seconds=duration_sec)
    found_files = []

    for fname in os.listdir(RECORDINGS_DIR):
        if not fname.endswith(".mp4"):
            continue

        try:
            ts_str = fname.replace(".mp4", "")
            file_time = datetime.strptime(ts_str, TIMESTAMP_FORMAT) 
        except ValueError:
            continue


        file_end_time = file_time + timedelta(seconds=30)
        if (start_time < file_end_time) and (end_time > file_time):
            fname = os.path.join(RECORDINGS_DIR, fname)
            found_files.append(fname)

    found_files.sort(key=lambda path: datetime.strptime(os.path.basename(path).replace(".mp4", ""), TIMESTAMP_FORMAT))
    return found_files