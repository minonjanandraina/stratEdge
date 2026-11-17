#!/usr/bin/env bash
# Exemple de crontab (chaque lundi à 09:00):
# 0 9 * * 1 /chemin/vers/stratedge_prod/weekly_project_update_reminder.sh >> /chemin/vers/stratedge_prod/logs/weekly_project_update_reminder.log 2>&1
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

if [ -f "venv/bin/activate" ]; then
  . "venv/bin/activate"
elif [ -f "venv/Scripts/activate" ]; then
  . "venv/Scripts/activate"
fi

python manage.py send_weekly_project_update_reminders --settings=config.settings.production
