#!/bin/bash
# ============================================================
# RPi Device Agent Auto Installer (Ubuntu-only)
# ============================================================

set -e

# -------------------------------
# Logging function
# -------------------------------
log() {
    echo ""
    echo "============================================================"
    echo "[*] $1"
    echo "============================================================"
    echo ""
}

# -------------------------------
# Fail-safe functions
# -------------------------------
fail_if_present() {
    local pattern="$1"
    local file="$2"
    local message="$3"
    if grep -q "$pattern" "$file"; then
        echo "❌ FAIL: $message"
        echo "➡ File: $file"
        exit 1
    fi
}

fail_if_missing() {
    local pattern="$1"
    local file="$2"
    local message="$3"
    if ! grep -q "$pattern" "$file"; then
        echo "❌ FAIL: $message"
        echo "➡ File: $file"
        exit 1
    fi
}

# -------------------------------
# Step 1: Raspberry Pi connection
# -------------------------------
read -p "Enter Raspberry Pi username [default: pi]: " PI_USER
PI_USER=${PI_USER:-pi}
read -p "Enter Raspberry Pi IP address: " PI_IP
[ -z "$PI_IP" ] && echo "❌ IP required" && exit 1
read -s -p "Enter Raspberry Pi password: " PI_PASS
echo ""
PI_HOST="${PI_USER}@${PI_IP}"

# -------------------------------
# Step 2: PTZ & Camera coordinates
# -------------------------------
read -p "Initial PAN [0]: " PAN_POSITION; PAN_POSITION=${PAN_POSITION:-0}
read -p "Initial TILT [0]: " TILT_POSITION; TILT_POSITION=${TILT_POSITION:-0}
read -p "Initial ZOOM [1]: " ZOOM_LEVEL; ZOOM_LEVEL=${ZOOM_LEVEL:-1}
read -p "Camera X coordinate: " CAMERA_X
read -p "Camera Y coordinate: " CAMERA_Y
read -p "Camera Z coordinate: " CAMERA_Z

# -------------------------------
# Step 3: Detect certificate folder
# -------------------------------
CERT_FOLDER=$(ls -d */ 2>/dev/null | grep -Ei ".*_device/?$" | head -n1 | tr -d '/')
[ -z "$CERT_FOLDER" ] && echo "❌ Cert folder not found" && exit 1

SERIAL_NO=$(echo "$CERT_FOLDER" | awk -F_ '{print $1"_"$2}')
LOG_FILE="provision_${SERIAL_NO}.log"
exec > >(tee -a "$LOG_FILE") 2>&1
log "Starting provisioning for $SERIAL_NO"

# -------------------------------
# Step 4: Test SSH connection
# -------------------------------
log "Testing SSH connection..."
sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$PI_HOST" "echo Connected" >/dev/null || {
    echo "❌ SSH connection failed"
    exit 1
}

# -------------------------------
# Step 5: Cleanup previous files
# -------------------------------
log "Removing old files on Raspberry Pi..."
sshpass -p "$PI_PASS" ssh "$PI_HOST" "rm -rf ~/RPi_device_agent ~/utils"

# -------------------------------
# Step 6: Read metadata
# -------------------------------
META_FILE="$CERT_FOLDER/metadata.json"
[ ! -f "$META_FILE" ] && echo "❌ metadata.json missing" && exit 1

DEVICE_ID=$(sed -n 's/.*"device_id":[[:space:]]*"\([^"]*\)".*/\1/p' "$META_FILE")
DEVICE_NAME=$(sed -n 's/.*"name":[[:space:]]*"\([^"]*\)".*/\1/p' "$META_FILE")
DEVICE_TYPE=$(sed -n 's/.*"type":[[:space:]]*"\([^"]*\)".*/\1/p' "$META_FILE" | tr '[:lower:]' '[:upper:]')

[ -z "$DEVICE_ID" ] && echo "❌ DEVICE_ID missing" && exit 1

log "DEVICE_NAME=$DEVICE_NAME"
log "DEVICE_TYPE=$DEVICE_TYPE"
log "DEVICE_ID=$DEVICE_ID"

# --- Step 7: Update .env ---
ENV_FILE="RPi_device_agent/.env"
[ ! -f "$ENV_FILE" ] && echo "❌ .env file not found" && exit 1

read -p "Enter APP_USERNAME: " APP_USERNAME
read -s -p "Enter APP_PASSWORD: " APP_PASSWORD
echo ""

# Remove old DEVICE_ID, DEVICE_TYPE lines (including placeholders)
sed -i '/^DEVICE_ID/d' "$ENV_FILE"
sed -i '/^DEVICE_TYPE/d' "$ENV_FILE"
sed -i '/^<Device_name>/d' "$ENV_FILE"

# Replace <user> and <password>
sed -i "s|<user>|$APP_USERNAME|g" "$ENV_FILE"
sed -i "s|<password>|$APP_PASSWORD|g" "$ENV_FILE"

# Append correct DEVICE_ID, DEVICE_TYPE, DEVICE_NAME at the top
sed -i "1i DEVICE_ID=$DEVICE_ID" "$ENV_FILE"
sed -i "2i DEVICE_TYPE=$DEVICE_TYPE" "$ENV_FILE"
sed -i "3i DEVICE_NAME=$DEVICE_NAME" "$ENV_FILE"

# Fail-safe checks
grep -q "DEVICE_ID=$DEVICE_ID" "$ENV_FILE" || { echo "❌ FAIL: DEVICE_ID not updated"; exit 1; }
grep -q "DEVICE_TYPE=$DEVICE_TYPE" "$ENV_FILE" || { echo "❌ FAIL: DEVICE_TYPE not updated"; exit 1; }
grep -q "$APP_USERNAME" "$ENV_FILE" || { echo "❌ FAIL: APP_USERNAME not replaced"; exit 1; }
grep -q "$APP_PASSWORD" "$ENV_FILE" || { echo "❌ FAIL: APP_PASSWORD not replaced"; exit 1; }
grep -q "$DEVICE_NAME" "$ENV_FILE" || { echo "❌ FAIL: DEVICE_NAME not replaced"; exit 1; }

echo ".env updated successfully ✅"

# -------------------------------
# Step 8: Move certificates
# -------------------------------
rm -rf RPi_device_agent/client_certs
mv "$CERT_FOLDER" RPi_device_agent/client_certs

# -------------------------------
# Step 9: Update payload JSON
# -------------------------------

# Determine Pi IP (Tailscale preferred)
RPi_IP=$(sshpass -p "$PI_PASS" ssh "$PI_HOST" "hostname -I 2>/dev/null | tr ' ' '\n' | grep '^100\.' | head -n1")
if [ -z "$RPi_IP" ]; then
    RPi_IP=$(sshpass -p "$PI_PASS" ssh "$PI_HOST" "hostname -I | awk '{print \$1}'")
    echo "⚠️  Tailscale IP not found, using primary IP: $RPi_IP"
else
    echo "✅ Using Tailscale IP: $RPi_IP"
fi

PAYLOAD_FILE="RPi_device_agent/field_unit_payloads/$(echo "$DEVICE_TYPE" | tr '[:upper:]' '[:lower:]').json"
[ ! -f "$PAYLOAD_FILE" ] && echo "❌ Payload file missing" && exit 1

SYSTEM_DATE=$(date +"%Y-%m-%d")
DEVICE_NAME_UNDERSCORE=$(echo "$DEVICE_NAME" | tr ' ' '_')

# Replace placeholders
sed -i "s|<Device_name>|$DEVICE_NAME_UNDERSCORE|g" "$PAYLOAD_FILE"
sed -i "s|<SL-NO>|$SERIAL_NO|g" "$PAYLOAD_FILE"
sed -i "s|<device-ip>|$RPi_IP|g" "$PAYLOAD_FILE"
sed -i "s|\"installation_date\"[[:space:]]*:[[:space:]]*\"date\"|\"installation_date\": \"$SYSTEM_DATE\"|g" "$PAYLOAD_FILE"

# Fail-safe checks
fail_if_present "<Device_name>" "$PAYLOAD_FILE" "Device name not replaced in JSON"
fail_if_present "<SL-NO>" "$PAYLOAD_FILE" "Serial number not replaced in JSON"
fail_if_present "<device-ip>" "$PAYLOAD_FILE" "Device IP not replaced in JSON"
fail_if_present "\"installation_date\": \"date\"" "$PAYLOAD_FILE" "Installation date not replaced in JSON"

log "✅ Payload JSON updated successfully"

# -------------------------------
# Step 10: Upload to Raspberry Pi
# -------------------------------
log "Uploading files to Raspberry Pi..."
sshpass -p "$PI_PASS" scp -r RPi_device_agent utils "$PI_HOST:~/"

# Verify upload
sshpass -p "$PI_PASS" ssh "$PI_HOST" bash -s <<'EOF'
set -e
[ -d "$HOME/RPi_device_agent" ] || { echo "❌ RPi_device_agent missing"; exit 1; }
[ -d "$HOME/utils" ] || { echo "❌ utils missing"; exit 1; }
[ -f "$HOME/RPi_device_agent/.env" ] || { echo "❌ .env missing"; exit 1; }
echo "✅ Upload verified"
EOF

# -------------------------------
# Step 11: Update /etc/hosts
# -------------------------------
log "Updating /etc/hosts on Raspberry Pi..."
UBUNTU_IP=$(hostname -I | awk '{print $1}')
sshpass -p "$PI_PASS" ssh "$PI_HOST" bash -s <<EOF
set -e
echo "$PI_PASS" | sudo -S bash -c '
sed -i "/appliedsni/d" /etc/hosts
echo "$UBUNTU_IP    appliedsni" >> /etc/hosts
grep appliedsni /etc/hosts
'
EOF
log "/etc/hosts updated successfully"

# -------------------------------
# Step 12: Python environment setup & runtime check
# -------------------------------
log "Setting up Python environment & validating agent startup..."
sshpass -p "$PI_PASS" ssh -t "$PI_HOST" bash -s <<'EOF'
set -e
cd ~/RPi_device_agent
sudo chown -R $USER:$USER ~/RPi_device_agent
python3 -m venv --system-site-packages objvenv
source objvenv/bin/activate
pip install --upgrade pip
[ -f requirements.txt ] && pip install -r requirements.txt
pip uninstall -y numpy simplejpeg opencv-python opencv-python-headless || true
pip install --no-cache-dir --force-reinstall simplejpeg
pip install numpy==1.26.4
pip install opencv-python
python RPI_main.py > agent_output.log 2>&1 &
PID=$!
for i in {1..30}; do
  if grep -q "=== Starting Camera Stream ===" agent_output.log || \
     grep -q "=== Starting Drone Stream ===" agent_output.log || \
     grep -q "=== Starting Sensor ===" agent_output.log; then
      echo "✅ Agent started successfully"
      kill $PID
      exit 0
  fi
  sleep 2
done
echo "❌ Agent failed to start"
exit 1
EOF
log "Agent runtime validation successful"

# -------------------------------
# Step 13: systemd service creation
# -------------------------------
log "Creating and enabling systemd service..."
sshpass -p "$PI_PASS" ssh -t "$PI_HOST" bash -s <<'EOF'
set -e
SERVICE_FILE=/etc/systemd/system/rpi-device-agent.service
echo "[Unit]
Description=RPi Device Agent
After=network-online.target
Wants=network-online.target

[Service]
User=$USER
WorkingDirectory=/home/$USER/RPi_device_agent
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/$USER/RPi_device_agent/objvenv/bin/python /home/$USER/RPi_device_agent/RPI_main.py
Restart=always
RestartSec=5
StandardOutput=append:/home/$USER/RPi_device_agent/agent_output.log
StandardError=append:/home/$USER/RPi_device_agent/agent_error.log

[Install]
WantedBy=multi-user.target" | sudo tee $SERVICE_FILE > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable rpi-device-agent.service
sudo systemctl restart rpi-device-agent.service
sudo systemctl is-active rpi-device-agent.service
EOF
log "systemd service installed and running"

# -------------------------------
# Done
# -------------------------------
log "✅ PROVISIONING COMPLETED SUCCESSFULLY"
echo "Device ID   : $DEVICE_ID"
echo "Device Type : $DEVICE_TYPE"
echo "Serial No   : $SERIAL_NO"
echo "IP Address  : $PI_IP"
echo "Log File    : $LOG_FILE"
