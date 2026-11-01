import time
import psutil
import cv2
import logging

def draw_performance_overlay(frame, start_time):
    end_time = time.perf_counter()
    fps = 1 / (end_time - start_time)
    cpu_usage = psutil.cpu_percent(interval=None)

    logging.info(f"FPS: {fps:.2f} | CPU: {cpu_usage:.0f}%")

    text = f"FPS: {fps:.2f} | CPU: {cpu_usage:.0f}%"
    cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                0.7, (0, 255, 255), 2)
