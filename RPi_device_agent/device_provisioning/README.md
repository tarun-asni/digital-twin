
# 📦 Device Provisioning System with mTLS Support

This project provisions edge devices (like cameras) securely using RSA certificates signed by a Root CA. It enables secure communication via mTLS using NGINX as a reverse proxy.

---

## 🏁 Setup Instructions

### 🔐 Generate Root Certificate

```bash
python -m cli.generate_root_ca --country IN --org MyCompany --cn RootCA --key-size 4096 --public-exponent 65537 --days 3650 --hostname Sujit --ip 192.168.0.103
```

---

## 🐳 Docker Setup

```bash
docker-compose down
docker-compose build
docker-compose up -d
```

---

## 📦 Device Order

```bash
python -m cli.issue_device_cert device123
```

---

## ✅ TLS Certificate Rotation Flow

1. Load old private key (from DB) to decrypt the incoming data.
2. Delete old keypair from DB.
3. Generate new RSA keypair.
4. Issue new TLS certificate (signed by Root CA).
5. Save new keypair + cert in DB.
6. Send new public key and cert to device.

---

## 📡 APIs

### `/register`

Use `generate_payload.py` to simulate encrypted payload:

```bash
python generate_payload.py
```

---

### `/device/<device_id>/heartbeat`

- Marks device as **active** in DB.
- Deletes old cert files from disk (if any).
- Replies over HTTPS using NGINX TLS.
- SQLAlchemy handles DB updates and file deletions.

---

### `/device_order`

Creates new device with certificate:

Steps:
1. Generate UUID-based device_id.
2. Load Root CA cert and key.
3. Generate RSA 2048-bit keypair.
4. Sign device TLS certificate (valid for 365 days).
5. Save device, cert, and keypair to DB.
6. Store PEM files under `certs/`.
7. Returns `device_id`, `public_key`, and `signed_cert` as JSON.

---

## 🔧 Full Provisioning Steps

### 📁 Pre-requisites

- Pull latest changes
- Update `.env` with correct DB configurations

### 🧪 Virtual Environment Setup

```bash
python -m venv twin_env
.	win_env\Scriptsctivate
cd ..
pip install -r requirements.txt
```

### 🔐 Generate Root Certificate (again for server)

```bash
python -m cli.generate_root_ca --country IN --org MyCompany --cn RootCA --key-size 4096 --public-exponent 65537 --days 3650 --hostname Sujit --ip 192.168.0.103
```

---

### 🚀 Start Provision Server

```bash
python run.py
```

---

## 🛡️ Setup NGINX with TLS

1. Download NGINX: [http://nginx.org/en/download.html](http://nginx.org/en/download.html)
2. Extract inside project folder.
3. Create `certs/` folder inside NGINX directory.
4. Copy these files:
   - `hostname_key.pem`
   - `hostname.pem`
   - `rootCA.pem`
   - `rootCA.key`

5. Replace config inside `nginx/conf/nginx.conf`:

```nginx
events {}

http {
    server {
        listen 443 ssl;

        ssl_certificate           E:/.../nginx/certs/hostname_cert.pem;
        ssl_certificate_key       E:/.../nginx/certs/hostname_cert_key.pem;

        ssl_client_certificate    E:/.../nginx/certs/rootCA.pem;
        ssl_verify_client         on;

        location / {
            proxy_pass http://localhost:5000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

6. Start NGINX (as Admin):

```bash
start nginx
```

---

## 📩 Trigger `/device_order`

Use Postman or curl:

```bash
curl --location 'http://localhost:5000/device_order' \
--header 'Content-Type: application/json' \
--data '{
    "name": "Camera2",
    "type": "SECURITY"
}'
```

---

## 🗂️ Device Client Setup

1. Update `.env` in `rpiprovisioning` and `provisioning server` with:
   - `device_id`
   - local IP

2. Create `client_certs/` inside `rpiprovisioning/device_clients/`

3. Copy generated cert files into it:
   - `cert_key.pem`
   - `cert.pem`
   - `pub.pem`
   - `rootCA.pem`

4. Run device client:

```bash
python main.py
```

---

## 📹 After Provisioning: Connect to Camera Feed

### 1. Add Camera to Database

```http
POST http://localhost:8000/api/field-units/cameras/
```

#### Headers:
- Authorization: Basic Auth 
	createuseranme by executing command: python manage.py createsuperuser

#### Body (JSON):
```json
{
    "id": "device_id",
    "name": "Field Camera",
    "model": "CR-N300",
    "manufacturer": "Sony",
    "serial_number": 101,
    "edge_url": "http://localhost:5001",
    "latitude": 1.52,
    "longitude": 1.25,
    "altitude": 10,
    "camera_type": "SECURITY",
    "resolution": "640x480",
    "power_source": "AC",
    "installation_date": "2025-07-08"
}
```

---

### 2. Configure RPiCam

In `RPiCam/app.py`, set:

```python
DEVICE_ID = "your_device_id"
```

Install dependencies:

```bash
cd RPiCam
pip install -r requirements.txt
python app.py
```

---

### 3. Run Command Center

```bash
cd command_center
pip install -r requirements.txt
python manage.py runserver
```

---

## 🔍 View Live Feed

Visit:

```
http://localhost:8000/api/command-center/live-feeds/
```

- Use `stream_url` to view live video.
- To view annotated feed:  
  Append `?annotate=True` to the URL:

```
/<camera_id>/stream/?annotate=True
```

---

## ✅ Summary

| Component        | Role                                      |
|------------------|-------------------------------------------|
| Provision Server | Issues certs & manages device keys        |
| Device Client    | Sends encrypted data using TLS            |
| NGINX            | mTLS gateway for secure HTTPS             |
| Command Center   | Consumes feed and provides video view API |
