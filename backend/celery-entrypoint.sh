#!/bin/bash
# Entrypoint script for Celery worker

set -e

echo "Starting Celery worker..."

# Wait for Redis to be ready
echo "Waiting for Redis..."
while ! redis-cli -h redis ping > /dev/null 2>&1; do
  sleep 1
done
echo "Redis is ready!"

# Run database migrations
echo "Running database migrations..."
flask db upgrade

# Start Celery worker (enable task events so Flower can inspect workers)
exec celery -A app.celery_app:celery worker \
  --loglevel=info \
  --concurrency=4 \
  --max-tasks-per-child=50 \
  --task-events \
  --time-limit=1800 \
  --soft-time-limit=1500
