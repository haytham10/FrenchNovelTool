#!/bin/bash
# Railway-compatible Celery worker entrypoint
# This script waits for dependencies and starts the Celery worker

set -e

echo "🚀 Starting Celery worker for Railway deployment..."

# Function to wait for Redis with Python (no redis-cli needed)
wait_for_redis() {
    echo "⏳ Waiting for Redis connection..."
    python3 -c "
import os
import sys
import time
import redis

redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
max_attempts = 30
attempt = 0

while attempt < max_attempts:
    try:
        r = redis.from_url(redis_url, socket_connect_timeout=5)
        r.ping()
        print('✅ Redis is ready!')
        sys.exit(0)
    except Exception as e:
        attempt += 1
        if attempt < max_attempts:
            print(f'Redis not ready (attempt {attempt}/{max_attempts}): {e}')
            time.sleep(2)
        else:
            print(f'❌ Redis connection failed after {max_attempts} attempts')
            sys.exit(1)
"
    return $?
}

# Function to wait for database
wait_for_db() {
    echo "⏳ Waiting for database connection..."
    python3 -c "
import os
import sys
import time
from sqlalchemy import create_engine, text

db_url = os.getenv('DATABASE_URL')
if not db_url:
    print('⚠️  DATABASE_URL not set, skipping DB check')
    sys.exit(0)

# Handle postgres:// -> postgresql://
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)

max_attempts = 30
attempt = 0

while attempt < max_attempts:
    try:
        engine = create_engine(db_url, pool_pre_ping=True, connect_args={'connect_timeout': 10})
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        print('✅ Database is ready!')
        sys.exit(0)
    except Exception as e:
        attempt += 1
        if attempt < max_attempts:
            print(f'Database not ready (attempt {attempt}/{max_attempts}): {e}')
            time.sleep(2)
        else:
            print(f'❌ Database connection failed after {max_attempts} attempts')
            sys.exit(1)
"
    return $?
}

# Wait for services
if ! wait_for_redis; then
    echo "❌ Failed to connect to Redis. Exiting..."
    exit 1
fi

if ! wait_for_db; then
    echo "❌ Failed to connect to database. Exiting..."
    exit 1
fi

# Run database migrations (with retry logic)
echo "📦 Running database migrations..."
for i in {1..3}; do
    if flask db upgrade; then
        echo "✅ Migrations completed successfully"
        break
    else
        if [ $i -eq 3 ]; then
            echo "❌ Migrations failed after 3 attempts"
            exit 1
        fi
        echo "⚠️  Migration attempt $i failed, retrying..."
        sleep 5
    fi
done

# Start Celery worker with production settings and capture exit code
# Optimized for 8GB RAM / 8 vCPU Railway infrastructure
echo "🎯 Starting Celery worker (8GB RAM / 8 vCPU optimized)..."
celery -A celery_worker.celery worker \
    --loglevel=info \
    --concurrency=${CELERY_CONCURRENCY:-8} \
    --max-tasks-per-child=${CELERY_MAX_TASKS_PER_CHILD:-50} \
    --max-memory-per-child=${CELERY_MAX_MEMORY_PER_CHILD:-900000} \
    --prefetch-multiplier=${CELERY_PREFETCH_MULTIPLIER:-1} \
    --task-events \
    --time-limit=3600 \
    --soft-time-limit=3300

rc=$?
echo "Celery exited with code: $rc"
if [ $rc -ne 0 ]; then
    echo "Celery failed — exiting entrypoint to allow platform to surface the failure."
    exit $rc
fi
