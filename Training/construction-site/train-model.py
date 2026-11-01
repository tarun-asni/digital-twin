from ultralytics import YOLO

def main():
    model = YOLO("../yolo-weights/yolov8m.pt")

    model.train(
        data="dataset/ppe_data.yaml",
        epochs=20,
        imgsz=480,
        device=0,
        batch=10,
        name="constr_train_medium",
        project="runs"
    )

if __name__ == "__main__":
    main()
