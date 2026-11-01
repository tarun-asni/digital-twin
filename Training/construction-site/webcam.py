import cv2
import math
import cvzone
from ultralytics import YOLO

def run_web_cam() -> None:

    cap = cv2.VideoCapture(0)
    cap.set(3, 1080)
    cap.set(4, 720)

    model = YOLO("runs/constr_train_nano/weights/best.pt")

    try:
        while True:
            success, img = cap.read()
            if not success:
                print("❌ Failed to read from webcam.")
                break

            results = model(img, stream=True)

            for r in results:
                boxes = r.boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0]
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                    w, h = x2 - x1, y2 - y1
                    conf = math.ceil(box.conf[0] * 100) / 100
                    cls_id = int(box.cls[0])
                    cls_name = model.names[cls_id]

                    cvzone.cornerRect(img, (x1, y1, w, h))
                    cvzone.putTextRect(img, f'{cls_name} {conf}', (x1 + 5, y1 - 15), 1, 2)

            cv2.imshow("Webcam Detection", img)

            key = cv2.waitKey(1) & 0xFF
            if key == 27 or key == ord('q'):
                print("👋 Exiting webcam (key press)...")
                break

    except KeyboardInterrupt:
        print("\n🛑 Keyboard interruption received.")

    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("✅ Webcam and windows released.")

if __name__ == "__main__":
    run_web_cam()