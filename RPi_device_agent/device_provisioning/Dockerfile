# Use official Python base image
FROM python:3.10-slim

# Set work directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose Flask port
EXPOSE 5000

# Run Flask app
CMD ["python", "run.py"]
