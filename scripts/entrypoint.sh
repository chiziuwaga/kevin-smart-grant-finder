#!/bin/bash
set -e

echo "=== Running pre-deploy checks ==="
python scripts/pre_deploy.py

echo "=== Running database migrations ==="
alembic upgrade head

echo "=== Starting application ==="
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
