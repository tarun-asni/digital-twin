import cv2

class MockCamera:
    def __init__(self, video_path):
        self.cap = cv2.VideoCapture(video_path)

    def capture_array(self):
        if not self.cap.isOpened():
            return None

        ret, frame = self.cap.read()
        if not ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Loop video
            ret, frame = self.cap.read()
        return frame

    def release(self):
        self.cap.release()
