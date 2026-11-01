# 🏃‍♂️ Raspberry Pi Motion Sensor Client  

This guide explains how to set up a **Raspberry Pi PIR Motion Sensor** that detects movement and sends periodic location data to a **Flask server**.  

---

## 🧰 Hardware Requirements  

- **Raspberry Pi 3 / 4 / 5**  
- **PIR Motion Sensor (HC-SR501 or similar)**  
- **Jumper wires**  
- **MicroSD card (32GB or more)**  
- **Stable internet (Wi-Fi or Ethernet)**  

Optional:  
- GPIO extension board  
- Breadboard for easy wiring  

---

## 📀 Software Requirements  

- **Raspberry Pi OS (64-bit preferred)**  
- **Python 3.11+**  
- Required Python libraries:  
  - `requests`  
  - `RPi.GPIO`  

---

## 🔌 Wiring the PIR Motion Sensor  

| PIR Sensor Pin | Connect to Raspberry Pi |  
|----------------|-------------------------|  
| **VCC**        | **5V (Pin 2 or 4)**     |  
| **GND**        | **GND (Pin 6)**         |  
| **OUT**        | **GPIO 17 (Pin 11)**    |  

✅ **Double-check orientation** before powering the Pi.  

---

## ⚙️ Prepare Raspberry Pi  

1. **Update & upgrade OS**  
   ```bash
   sudo apt update && sudo apt upgrade -y

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

---

## 🔄 Optional: Run on Boot
You can make this script auto-start using systemd:

1. sudo nano /etc/systemd/system/motion-client.service

2. copy the below to the motion-client.service file
   [Unit]
   Description=Raspberry Pi Motion Client
   After=network.target

   [Service]
   ExecStart=/usr/bin/python3 /home/pi/motion-sensor-client/motion_sensor_client.py
   Restart=always
   User=pi

   [Install]
   WantedBy=multi-user.target

3. Then enable and start service:
   sudo systemctl enable motion-client
   sudo systemctl start motion-client