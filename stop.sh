#!/usr/bin/env bash
# Arrêter tous les processus de l'application
# Usage : bash stop.sh

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

for SERVICE in uvicorn celery-worker celery-beat; do
    PID_FILE="$PROJECT_DIR/logs/${SERVICE}.pid"
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "  [stop] $SERVICE (PID $PID)"
            kill "$PID"
        else
            echo "  [skip] $SERVICE — processus déjà arrêté"
        fi
        rm -f "$PID_FILE"
    else
        echo "  [skip] $SERVICE — pas de fichier PID"
    fi
done

echo ""
echo "  ✓ Tous les processus arrêtés."
