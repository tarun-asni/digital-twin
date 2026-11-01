import numpy as np
from .sort import Sort

class BYTETracker:
    def __init__(self):
        self.sort_tracker = Sort()

    def update(self, detections):
        if len(detections) == 0:
            return []

        dets_for_sort = np.array([[*det[:4], det[4]] for det in detections], dtype=np.float32)

        cls_ids = [int(det[5]) for det in detections]
        confs = [float(det[4]) for det in detections]

        tracked = self.sort_tracker.update(dets_for_sort)

        output_tracks = []
        for trk, cls_id, conf in zip(tracked, cls_ids, confs):
            x1, y1, x2, y2, track_id = map(int, trk)
            output_tracks.append([x1, y1, x2, y2, track_id, cls_id, conf])

        return output_tracks
