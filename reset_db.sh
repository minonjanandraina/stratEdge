#!/usr/bin/env bash
# Réinitialisation complète de la base de données
# Usage : bash reset_db.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$PROJECT_DIR/venv/bin/python"
SETTINGS="config.settings.production"

# ── Charger les variables d'environnement ─────────────────────────────────────
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
else
    echo "Erreur : fichier .env introuvable dans $PROJECT_DIR"
    exit 1
fi

DB_NAME="${DB_NAME:-msproject}"
DB_USER="${DB_USER:-msproject_user}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

# ── Confirmation ──────────────────────────────────────────────────────────────
echo ""
echo "  ╔══════════════════════════════════════════════════════╗"
echo "  ║   RÉINITIALISATION DE LA BASE DE DONNÉES             ║"
echo "  ║   Toutes les données seront SUPPRIMÉES définitivement ║"
echo "  ╚══════════════════════════════════════════════════════╝"
echo ""
echo "  Base    : $DB_NAME"
echo "  Hôte    : $DB_HOST:$DB_PORT"
echo "  Schéma  : supprimé et recréé"
echo ""
read -rp "  Confirmer ? Tapez 'oui' pour continuer : " CONFIRM

if [ "$CONFIRM" != "oui" ]; then
    echo "Annulé."
    exit 0
fi

echo ""

# ── Arrêter les processus si en cours ─────────────────────────────────────────
for SERVICE in uvicorn celery-worker celery-beat; do
    PID_FILE="$PROJECT_DIR/logs/${SERVICE}.pid"
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "  [stop] $SERVICE (PID $PID)"
            kill "$PID"
            rm -f "$PID_FILE"
        fi
    fi
done

# ── Supprimer et recréer la base ───────────────────────────────────────────────
echo "  [db] Suppression de la base '$DB_NAME'..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U postgres \
    -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>/dev/null \
    || sudo -u postgres psql -c "DROP DATABASE IF EXISTS $DB_NAME;"

echo "  [db] Création de la base '$DB_NAME'..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U postgres \
    -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null \
    || sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

# ── Migrations ────────────────────────────────────────────────────────────────
echo "  [django] Migrations..."
cd "$PROJECT_DIR"
"$PYTHON" manage.py migrate --settings="$SETTINGS"

# ── Fichiers statiques ────────────────────────────────────────────────────────
echo "  [django] Collectstatic..."
"$PYTHON" manage.py collectstatic --noinput --settings="$SETTINGS"

# ── Superuser ─────────────────────────────────────────────────────────────────
echo ""
read -rp "  Créer un superutilisateur ? (o/n) : " CREATE_SU
if [ "$CREATE_SU" = "o" ]; then
    "$PYTHON" manage.py createsuperuser --settings="$SETTINGS"
fi

# ── Résumé ────────────────────────────────────────────────────────────────────
echo ""
echo "  ✓ Base réinitialisée avec succès."
echo "  Relancer l'application : bash start.sh"
echo ""
