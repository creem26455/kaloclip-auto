FROM python:3.11-slim

# FFmpeg สำหรับ merge clips
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway volume mounts at /data/
RUN mkdir -p /data/downloads /data/temp

EXPOSE 5000

CMD ["python", "app.py"]
