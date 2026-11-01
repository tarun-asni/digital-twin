from ultralytics import YOLO
import cv2
import os

def main() -> None:
    # Load model
    model = YOLO('runs/constr_train_nano/weights/best.pt')

    # Custom folder to save results
    save_dir = './runs/result_images'
    os.makedirs(save_dir, exist_ok=True) #

    # Run inference and save results
    for x in range(6):
        img_path = f'./runs/test_images/{x}.jpg'
        results = model(img_path)

        # Get annotated image
        annotated_img = results[0].plot()

        # Save with OpenCV
        save_path = os.path.join(save_dir, f'{x}_pred.jpg')
        cv2.imwrite(save_path, annotated_img)

        print(f"Saved: {save_path}")


if __name__ == "__main__":
    main()
