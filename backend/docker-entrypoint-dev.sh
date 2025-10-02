#!/bin/bash
set -e

# Function to wait for database to be ready
wait_for_db() {
    if [[ "$DATABASE_URL" == sqlite* ]]; then
        echo "Using SQLite database"
        return 0
    elif [[ "$DATABASE_URL" == postgresql* ]]; then
        echo "Waiting for PostgreSQL to be ready..."
        # Extract host and port from DATABASE_URL
        # This is a simplified extraction - adjust as needed
        DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\).*/\1/p')
        DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
        
        if [ -z "$DB_PORT" ]; then
            DB_PORT=5432
        fi
        
        until nc -z $DB_HOST $DB_PORT; do
            echo "PostgreSQL is unavailable - sleeping"
            sleep 1
        done
        echo "PostgreSQL is up - continuing"
    fi
}

# Check if we should run in debug mode
if [ "${ENABLE_DEBUGGER}" = "True" ] || [ "${ENABLE_DEBUGGER}" = "1" ]; then
    echo "Running with debugpy enabled on port 5678"
    python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m flask run --host=0.0.0.0 --port=5000 --reload
else
    # Wait for database
    wait_for_db
    
    # Run database migrations if needed
    if [ "${AUTO_MIGRATE}" = "True" ] || [ "${AUTO_MIGRATE}" = "1" ]; then
        echo "Running database migrations..."
        flask db upgrade
    fi
    
    # Execute the CMD
    exec "$@"
fi