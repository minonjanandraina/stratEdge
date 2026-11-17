#!/usr/bin/env bash
# Arrêter tous les processus de l'application
# Usage : bash stop.sh

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

stop_service() {
    local SERVICE="$1"
    local PATTERN="$2"
    local PID_FILE="$PROJECT_DIR/logs/${SERVICE}.pid"

    # Tentative via PID file
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")

        if kill -0 "$PID" 2>/dev/null; then
            echo "  [stop] $SERVICE (PID $PID)"
            kill "$PID"

            sleep 2

            if kill -0 "$PID" 2>/dev/null; then
                echo "  [force] $SERVICE (PID $PID)"
                kill -9 "$PID"
            fi
        fi

        rm -f "$PID_FILE"
    fi

    # Recherche du processus réel si le PID file est faux
    PIDS=$(pgrep -f "$PATTERN")

    if [ -n "$PIDS" ]; then
        echo "  [cleanup] $SERVICE (PID(s): $PIDS)"

        for PID in $PIDS; do
            kill "$PID" 2>/dev/null
        done

        sleep 2

        for PID in $PIDS; do
            kill -9 "$PID" 2>/dev/null || true
        done
    fi
}

stop_service "uvicorn" "uvicorn.*config.asgi:application"
stop_service "celery-worker" "celery.*worker.*config"
stop_service "celery-beat" "celery.*beat.*config"

echo ""
echo "  ✓ Tous les processus arrêtés"
