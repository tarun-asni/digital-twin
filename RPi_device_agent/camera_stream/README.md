# 📸 Raspberry Pi Camera Setup Guide

This guide outlines the steps to set up a Raspberry Pi with a camera module for live streaming, local video recording, and computer vision applications.

## 🧰 Hardware Requirements

- RPI PI 5 MODEL 8GB
- RPI PI 5 27W USB - C POWER SUPPLY
- CAMERA MODULE 3 NoIR
- MicroSD card (A2 Class, 64GB or more)
- RPI PI Camera Cable Standard Mini-200mm
- Internet connectivity (Wi-Fi or Ethernet)
- Optional: Heat sink or fan for sustained camera usage

---

### ⚙️ 1. Flash Raspberry Pi OS

#### Hardware Requirements

- Micro SD Card reader
- Laptop

#### Instructions

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Choose:
   - OS: **Raspberry Pi OS (64-bit)**
   - Storage: Your SD card
3. (Optional) Enable:
   - Account setup
   - SSH
   - Wi-Fi credentials
4. Flash and insert the card into the Pi

---

### 🔌 2. Connect and Enable Camera

1. Disconnect the 22 pin to 22 pi connector that came with camera
2. Connect the 22 pin to 15 pin connector, 22 pin side to camera and 15 pi side to either of the **CSI ports** on the Pi.
3. Boot the RPi and run to test the camera connection:
   ```bash
   rpicam-hello -t 0


## 📀 Software Requirements

- Raspberry Pi OS (64-bit preferred)
- Python 3.11
- `libcamera` stack
- `picamera2` (for Python-based applications)
- Flask (for streaming via web browser)
- FFmpeg (for encoding/processing)

---

#### Instructions

1. Install virtual environment
    ```bash
    sudo apt install python3-venv
2. Create new virtual environment
    ```bash
    python3 -m venv --system-site-packages ~/camera-ai
3. Activate  new environment
    ```bash
    source ~/camera-ai/bin/activate

