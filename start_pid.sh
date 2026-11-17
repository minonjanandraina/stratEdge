#!/usr/bin/env bash
# Démarrer tous les processus de l'application
# Usage : bash start.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

mkdir -p logs

# Vérification qu'aucune instance n'est déjà lancée

if pgrep -f "uvicorn.*config.asgi:application" >/dev/null; then
    echo "  ✗ Uvicorn est déjà démarré"
    exit 1
fi

if pgrep -f "celery.*worker.*config" >/dev/null; then
    echo "  ✗ Celery worker est déjà démarré"
    exit 1
fi

if pgrep -f "celery.*beat.*config" >/dev/null; then
    echo "  ✗ Celery beat est déjà démarré"
    exit 1
fi

echo "  [start] uvicorn..."
nohup venv/bin/uvicorn config.asgi:application \
    --host 0.0.0.0 \
    --port 8000 \
    --lifespan off \
    > logs/uvicorn.log 2>&1 &

UVICORN_PID=$!
echo "$UVICORN_PID" > logs/uvicorn.pid

sleep 3

if ! kill -0 "$UVICORN_PID" 2>/dev/null; then
    echo "  ✗ Échec du démarrage d'Uvicorn"
    tail -20 logs/uvicorn.log
    exit 1
fi

echo "  [start] celery worker..."
nohup venv/bin/celery -A config worker --loglevel=info \
    > logs/celery-worker.log 2>&1 &

echo $! > logs/celery-worker.pid

echo "  [start] celery beat..."
nohup venv/bin/celery -A config beat \
    --loglevel=info \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler \
    > logs/celery-beat.log 2>&1 &

echo $! > logs/celery-beat.pid

echo ""
echo "  ✓ Application démarrée sur http://0.0.0.0:8000"
