FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Flower default port
EXPOSE 5555

# Run Flower monitoring UI
CMD ["celery", "-A", "app.celery", "flower", "--port=5555"]
