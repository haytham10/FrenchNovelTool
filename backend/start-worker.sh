#!/bin/bash

# Start Celery worker for French Novel Tool
# Usage: ./start-worker.sh

set -e

echo "Starting Celery worker..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set default concurrency if not set
WORKER_CONCURRENCY=${MAX_WORKERS:-4}

# Start worker with configuration
celery -A celery_app.celery_app worker \
    --loglevel=info \
    --concurrency=$WORKER_CONCURRENCY \
    --max-tasks-per-child=50 \
    --max-memory-per-child=${WORKER_MEMORY_LIMIT_MB:-2048000} \
    --time-limit=${TASK_TIMEOUT_SECONDS:-3600} \
    --soft-time-limit=$((${TASK_TIMEOUT_SECONDS:-3600} - 300))
