FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY RPi_device_agent/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY RPi_device_agent /app/RPi_device_agent
COPY utils /app/utils
COPY RPi_device_agent/.env /app/RPi_device_agent/.env

WORKDIR /app/RPi_device_agent

EXPOSE 5001

CMD ["python", "RPI_main.py"]