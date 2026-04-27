#!/bin/bash
set -e

# -------------------------------------------------------
# NeuroTwin Container Entrypoint
# Waits for DB, runs migrations, collects static files,
# then hands off to the CMD (Gunicorn / Celery / Beat).
# -------------------------------------------------------

MAX_RETRIES=30
RETRY_INTERVAL=2

# --- 1. Wait for database ---
echo "[$(date)] Waiting for database..."
retries=0
until python -c "import django; django.setup(); from django.db import connection; connection.ensure_connection()" 2>/dev/null; do
    retries=$((retries + 1))
    if [ "$retries" -ge "$MAX_RETRIES" ]; then
        echo "[$(date)] ERROR: Could not connect to database after ${MAX_RETRIES} attempts. Exiting."
        exit 1
    fi
    echo "[$(date)] Database not ready (attempt ${retries}/${MAX_RETRIES}). Retrying in ${RETRY_INTERVAL}s..."
    sleep "$RETRY_INTERVAL"
done
echo "[$(date)] Database is ready."

# --- 2. Run migrations ---
echo "[$(date)] Running database migrations..."
python manage.py migrate --noinput
echo "[$(date)] Migrations complete."

# --- 3. Collect static files ---
echo "[$(date)] Collecting static files..."
python manage.py collectstatic --noinput
echo "[$(date)] Static files collected."

# --- 4. Hand off to CMD ---
echo "[$(date)] Starting application: $@"
exec "$@"
