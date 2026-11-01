FROM python:3.11-slim

WORKDIR /app

# Install system dependencies + ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY command_center/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY command_center /app/command_center
COPY common /app/common