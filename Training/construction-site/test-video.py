import cv2
from ultralytics import YOLO

# Load your trained model
model = YOLO('./runs/constr_train_nano/weights/best.pt')  # Replace with your actual path to trained YOLOv8 model

# Load video
video_path = './runs/test_images/construction_site.mp4'  # Path to input video
cap = cv2.VideoCapture(video_path)

# Get video info for saving output
width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps    = cap.get(cv2.CAP_PROP_FPS)

# Output video writer
# Manually construct fourcc for 'mp4v'
fourcc = (ord('m') & 255) | ((ord('p') & 255) << 8) | ((ord('4') & 255) << 16) | ((ord('v') & 255) << 24)
out = cv2.VideoWriter('./runs/result_images/pred_construction_site.mp4', fourcc, fps, (width, height))

def main() -> None:
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        # Inference
        results = model.predict(source=frame, imgsz=640, conf=0.3)

        # Visualize predictions on the frame
        annotated_frame = results[0].plot()

        # Show frame (optional)
        cv2.imshow("Construction site prediction", annotated_frame)

        # Save to output file
        out.write(annotated_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Cleanup
    cap.release()
    out.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
