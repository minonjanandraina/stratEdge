# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Stratedge is a Django 5 project-management platform (MS Project–style: tasks, CPM scheduling, baselines, resources, costs, KPIs, reports, meetings, discussions). It exposes a DRF REST API (JWT) under `/api/v1/` and also serves server-rendered Django templates. UI language is French (`LANGUAGE_CODE='fr-fr'`, timezone `Indian/Antananarivo`). The Celery app is named `msproject` and the default DB name is `msproject`, which is the project's former name.

## Commands

The repo is not a git repository and ships a `venv/` (Linux-style, `venv/bin/...`). Scripts are bash.

```bash
pip install -r requirements/development.txt   # dev (pytest-django, factory-boy, debug-toolbar)
pip install -r requirements/production.txt    # prod (adds uvicorn, whitenoise, sentry)

python manage.py migrate
python manage.py runserver                    # HTTP only: WebSockets need ASGI (see below)
uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --lifespan off   # HTTP + WebSockets
celery -A config worker -l info
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

bash start_pid.sh   # starts uvicorn + celery worker + beat in background, writes logs/*.pid (refuses if already running)
bash stop_pid.sh    # stops them (stop.sh / start.sh are the older variants without the already-running guard)
bash reset_db.sh    # DESTRUCTIVE: wipes the PostgreSQL DB (uses .env, config.settings.production)
docker compose up   # postgres 16 + redis 7 + web + celery + celery-beat
```

Tests: `pytest-django` is in the dev requirements, but there is no pytest config and only `apps/objectives/tests.py` exists. Run with `pytest apps/objectives/tests.py::TestName --ds=config.settings.development` (pass `--ds` since no config file sets it).

## Settings

`config/settings/{base,development,production}.py`. **`manage.py`, `asgi.py` and `celery.py` all default to `config.settings.production`**, not development. Set `DJANGO_SETTINGS_MODULE=config.settings.development` for local dev. Config is read with `python-decouple` from `.env` (see `.env.example`). PostgreSQL and Redis are required (Redis is both the Celery broker and the Channels layer).

## Architecture

**Entry points**
- `config/urls.py` is the single routing table. Project-scoped APIs are nested as `api/v1/projects/<project_id>/{tasks,resources,assignments,baselines,kpis,reports,objectives,meetings}/`, so views in those apps read `project_id` from `self.kwargs`. `notifications/` is under `api/v1/` but not project-scoped. `apps.accounts.urls` is mounted at `api/v1/auth/`, next to the simplejwt token endpoints.
- Server-rendered pages come from `accounts/` (`accounts.frontend_urls`), `discussions/`, and the root `''` (`projects.frontend_urls`). Templates live in the top-level `templates/`, one folder per app. `media/` is served through Django's `serve` view even in production.
- `config/asgi.py` wraps Django in a Channels `ProtocolTypeRouter`. WebSocket routes come from `apps.notifications.routing` and `apps.discussions.routing` (consumers in each app's `consumers.py`). Running under plain `runserver`/WSGI loses real-time notifications and discussions.

**Domain apps** (`apps/`): `accounts` (users, profiles, email confirmation, signals/tasks), `projects` (core `Project`, `ProjectMembership`, DRF permissions in `permissions.py`), `tasks`, `resources`, `assignments`, `costs`, `baselines`, `kpis`, `reports`, `objectives`, `meetings`, `discussions`, `notifications`. Most apps follow the `models / serializers / views / urls` layout.

**Business logic lives in `services.py`, not in views**
- `apps/tasks/services.py`: `CPMCalculator`, a Critical Path Method calculation (networkx graph, topological sort, forward/backward pass) over non-summary tasks and `TaskDependency`.
- `apps/kpis/services.py`: `KPICalculator(project, baseline, status_date)`, which computes `ProjectKPI` (earned-value and schedule metrics) by comparing tasks against a `Baseline`.
- `apps/reports/exporters.py`: report exports (openpyxl for Excel, reportlab for PDF, python-docx for Word).

**Permissions**: project access is membership-based. `apps/projects/permissions.py` resolves the project from `project_id`/`pk` in view kwargs and checks `ProjectMembership`. Reuse these classes for new project-scoped endpoints.

**Async/scheduled work**: Celery tasks live in each app's `tasks.py` (autodiscovered). The beat schedule is defined in `CELERY_BEAT_SCHEDULE` in `config/settings/base.py`: KPI recalculation, task and project deadline reminders, overdue notifications, KPI alerts, meeting reminders, and expired-session cleanup. The Docker setup runs beat with the `DatabaseScheduler`, so schedules can also be edited in the admin through django-celery-beat. Signals (`signals.py` in accounts, assignments, tasks) trigger side effects such as notifications. Check them when behavior seems to happen "by magic".

**Other**: `django-auditlog` for audit trails; Sentry is enabled in production when `SENTRY_DSN` is set; email goes through SMTP settings in `production.py` (`config/mail.py`, `test_send_mail.py` at the root is a manual SMTP check).
