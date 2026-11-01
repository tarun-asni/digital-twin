# Flask YOLO Video Streamer

This project sets up a Flask server to access a webcam feed, process each frame using a YOLOv8 model, and stream the annotated video over HTTP.

## 📦 Requirements

- Python 3.11
- macOS/Linux (tested on macOS)
- Internet access for model download

## 🔧 Setup Instructions

### 1. Clone the Repo & Setup Environment

```bash
git clone git@github.com:prashantmp/digital-twin.git
cd camera-ai-mac
python3 -m venv ~/camera-ai
source ~/camera-ai/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Server
#### 3.1 Development
```bash
python app.py
```
#### 3.2 Production
```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```
