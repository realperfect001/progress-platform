#!/bin/sh
set -e
mkdir -p "$UPLOAD_DIR"
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-10000}" --workers 1 --proxy-headers --forwarded-allow-ips='*'
