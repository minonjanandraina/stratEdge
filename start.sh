#!/usr/bin/env bash
# Démarrer tous les processus de l'application
# Usage : bash start.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

mkdir -p logs

echo "  [start] uvicorn..."
nohup venv/bin/uvicorn config.asgi:application \
    --host 0.0.0.0 --port 8000 \
    --lifespan off \
    > logs/uvicorn.log 2>&1 &
echo $! > logs/uvicorn.pid

echo "  [start] celery worker..."
nohup venv/bin/celery -A config worker --loglevel=info \
    > logs/celery-worker.log 2>&1 &
echo $! > logs/celery-worker.pid

echo "  [start] celery beat..."
nohup venv/bin/celery -A config beat --loglevel=info \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler \
    > logs/celery-beat.log 2>&1 &
echo $! > logs/celery-beat.pid

echo ""
echo "  ✓ Application démarrée sur http://0.0.0.0:8000"
echo "  Logs : tail -f logs/uvicorn.log"
