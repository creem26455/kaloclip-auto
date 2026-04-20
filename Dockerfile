FROM mcr.microsoft.com/playwright/python:v1.58.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium browser
RUN playwright install chromium

COPY . .

# สร้างโฟลเดอร์ data
RUN mkdir -p /data/downloads

EXPOSE 8080

COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
