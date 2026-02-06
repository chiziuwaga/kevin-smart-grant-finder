#!/bin/bash

echo "=== Running pre-deploy checks ==="
python scripts/pre_deploy.py || echo "WARNING: Pre-deploy checks had issues (continuing anyway)"

echo "=== Running database migrations ==="
alembic upgrade head || echo "WARNING: Migration had issues (continuing anyway)"

echo "=== Starting application ==="
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
