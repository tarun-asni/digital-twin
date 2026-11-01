from flask import Flask, Response, render_template
import cv2
from ultralytics import YOLO

app = Flask(__name__)

# Load YOLOv8 model
model = YOLO("yolov8n.pt")  # Replace with 'yolov8s.pt' or custom model if needed

# Initialize webcam
cap = cv2.VideoCapture(0)


def annotated_live_feed_transmission():
    while True:
        success, frame = cap.read()
        if not success:
            break

        # Run YOLO inference
        results = model(frame, verbose=False)
        annotated_frame = results[0].plot()

        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


def live_feed_transmission():
    while True:
        success, frame = cap.read()
        if not success:
            break

        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/annotated_feed')
def annotated_feed():
    return Response(annotated_live_feed_transmission(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/live_feed')
def live_feed():
    return Response(live_feed_transmission(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True)
