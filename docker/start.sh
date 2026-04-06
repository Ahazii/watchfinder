#!/usr/bin/env sh
set -eu

echo "Starting WatchFinder..."
PORT="${APP_PORT:-8080}"

echo "Waiting for PostgreSQL..."
python <<'PY'
import os
import time

import psycopg

raw = os.environ["DATABASE_URL"]
url = raw.replace("postgresql+psycopg://", "postgresql://", 1)

for attempt in range(60):
    try:
        with psycopg.connect(url) as conn:
            conn.execute("SELECT 1")
        print("PostgreSQL is ready")
        break
    except Exception as exc:
        print(f"Attempt {attempt + 1}/60 failed: {exc}")
        time.sleep(2)
else:
    raise SystemExit("PostgreSQL did not become ready in time")
PY

MEDIA_ROOT="${LOCAL_MEDIA_ROOT:-./data/media}"
mkdir -p "$MEDIA_ROOT" 2>/dev/null || true

echo "Running Alembic migrations..."
cd /app
export PYTHONPATH=/app/backend
alembic upgrade head

echo "Starting uvicorn on port ${PORT}..."
exec uvicorn watchfinder.main:app --host 0.0.0.0 --port "${PORT}"
