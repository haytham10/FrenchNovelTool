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


# Create and switch to a dedicated non-root user for running the worker
if [ "$(id -u)" -eq 0 ] && [ -z "$RUN_AS_WORKER_USER" ]; then
	CELERY_USER="${CELERY_USER:-celery}"
	CELERY_UID="${CELERY_UID:-1001}"
	CELERY_GID="${CELERY_GID:-1001}"
	PROJECT_DIR="${PROJECT_DIR:-/app}"

	echo "🔐 Creating non-root user '${CELERY_USER}' (uid:${CELERY_UID} gid:${CELERY_GID})..."

	# Create group if missing
	if ! getent group "${CELERY_USER}" >/dev/null 2>&1; then
		groupadd -g "${CELERY_GID}" "${CELERY_USER}" >/dev/null 2>&1 || true
	fi

	# Create user if missing
	if ! id -u "${CELERY_USER}" >/dev/null 2>&1; then
		if command -v useradd >/dev/null 2>&1; then
			useradd -m -u "${CELERY_UID}" -g "${CELERY_GID}" -s /bin/sh "${CELERY_USER}" >/dev/null 2>&1 || true
		else
			# fallback for busybox/adduser minimal images
			addgroup -g "${CELERY_GID}" "${CELERY_USER}" >/dev/null 2>&1 || true
			adduser -D -u "${CELERY_UID}" -G "${CELERY_USER}" -s /bin/sh "${CELERY_USER}" >/dev/null 2>&1 || true
		fi
	fi

	# Ensure project dir and common runtime dirs are writable by the worker user
	for d in "${PROJECT_DIR}" /tmp /var/tmp /var/run; do
		[ -e "$d" ] && chown -R "${CELERY_USER}:${CELERY_USER}" "$d" >/dev/null 2>&1 || true
	done

	# Mark that we've switched to avoid infinite recursion and re-exec the script as the non-root user
	export RUN_AS_WORKER_USER=1

	if command -v gosu >/dev/null 2>&1; then
		exec gosu "${CELERY_USER}" "$0" "$@"
	elif command -v su-exec >/dev/null 2>&1; then
		exec su-exec "${CELERY_USER}" "$0" "$@"
	elif command -v runuser >/dev/null 2>&1; then
		exec runuser -u "${CELERY_USER}" -- "$0" "$@"
	elif command -v sudo >/dev/null 2>&1; then
		exec sudo -E -u "${CELERY_USER}" "$0" "$@"
	else
		# Last-resort with su (may not preserve environment)
		exec su -s /bin/sh - "${CELERY_USER}" -c "RUN_AS_WORKER_USER=1 exec \"$0\" $*"
	fi
fi


# Start Celery worker with production settings
echo "🎯 Starting Celery worker..."
exec celery -A celery_worker.celery worker \
    --loglevel=info \
    --concurrency=${CELERY_CONCURRENCY:-4} \
    --max-tasks-per-child=50 \
    --task-events \
    --time-limit=1800 \
    --soft-time-limit=1500
