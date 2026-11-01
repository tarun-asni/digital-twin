# 🛰️ Digital-Twin: Distributed Smart Surveillance and Monitoring System

Digital-Twin is a modular, privacy-conscious, edge-powered surveillance and monitoring framework designed for large-scale deployments such as construction sites, public infrastructure zones, and critical surveillance areas. The system leverages AI, IoT sensors, and live video analytics to provide real-time insights, event detection, and secure data handling — all without relying on cloud infrastructure.

---

## 📦 Repository Structure

This repository contains the following major components:

### 🔹 `command-center/`
The central processing and coordination engine responsible for:

- Receiving image/video feed and sensor event data from edge devices
- Managing device registry and health (camera heartbeat, drone status, etc.)
- Triggering AI inference pipelines and storing insights in a local database
- Powering a dashboard for real-time and historical insights

🔗 [See detailed setup](command-center/README.md)

---

### 🔹 `edge-device/`
Software stack to be deployed on Raspberry Pi (or equivalent edge processor) connected with cameras and/or IoT sensor modules. Key features include:

- Capturing live video feeds with Picamera2 + OpenCV
- Lightweight on-device inference for basic alert generation
- Local storage management (circular recording buffer)
- Secure streaming to the command center over HTTP/SRTP

🔗 [See detailed setup](edge-device/README.md)

---

### 🔹 `ai-models/`
Collection of pretrained and custom-trained AI models for:

- Object detection (YOLO-based)
- PPE compliance (e.g., hardhat, vest)
- Activity recognition and event segmentation

Also includes scripts for ONNX conversion and edge inference.

🔗 [See detailed setup](ai-models/README.md)

---

### 🔹 `sensor-network/`
Integration framework for vibration, acoustic, and motion sensors used to trigger surveillance actions. Includes:

- Sensor-to-event processing logic
- Drone dispatch decisions based on sensor triangulation
- Configuration templates for sensor-to-camera mapping

🔗 [See detailed setup](sensor-network/README.md)

---

## 🛠️ Technologies Used

- Raspberry Pi OS / Ubuntu (edge)
- Python 3.11, Flask, OpenCV, Picamera2
- FastAPI (command center APIs)
- PostgreSQL + PostGIS (insight storage)
- YOLOv8 / ONNX Runtime (AI processing)
- Optional: Redis + Celery (async pipeline)
- Optional: TPM / Serial + MAC-based device identity

---

## 🚀 Getting Started

Each subfolder contains its own `README.md` with:
- Hardware specs
- Software installation
- Deployment instructions

Start with `edge-device/` to bring up a test camera → then connect it with `command-center/` for full pipeline testing.

---

## 🧪 Demo Kit (Recommended Initial Setup)

- 1× Raspberry Pi 5 + Camera Module 3
- 1× Edge device setup with Flask stream + model overlay
- 1× Command center backend + dashboard running on local server
- Optional: sensor triggers to simulate alerts

---

## 📄 License

This project is licensed under the MIT License. Please review `LICENSE` file for details.

---

## 🙋 Contact

For questions or collaborations, contact: `youremail@domain.com`
