# Copilot instructions for Stratedge

## Project overview

Stratedge is a Django 5 project-management platform modeled on Microsoft Project: tasks, CPM scheduling, baselines, resources, assignments, costs, KPIs, reports, meetings, discussions, and notifications. It exposes a DRF API under `/api/v1/` and also serves server-rendered Django views.

Key repository conventions:
- The app is configured for French (`LANGUAGE_CODE = 'fr-fr'`) and the `Indian/Antananarivo` timezone.
- PostgreSQL is the default database, Redis is required for Celery and Channels, and Celery is configured in `config/settings/base.py`.
- Local configuration is read from `.env` via `python-decouple`; see `.env.example`.
- The default `manage.py`, `config/asgi.py`, and `config/celery.py` target `config.settings.production` unless `DJANGO_SETTINGS_MODULE=config.settings.development` is set explicitly.

## Build, run, and test commands

Install dependencies:
```bash
pip install -r requirements/development.txt
pip install -r requirements/production.txt
```

Local setup / startup:
```bash
cp .env.example .env
python manage.py migrate
python manage.py runserver
# or, for HTTP + WebSockets:
uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --lifespan off
```

Celery workers and beat:
```bash
celery -A config worker -l info
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Docker:
```bash
docker compose up
```

App management scripts already included in the repo:
```bash
bash start_pid.sh
bash stop_pid.sh
bash reset_db.sh
```

Tests:
- The repo includes `pytest-django` and `pytest-cov` in `requirements/development.txt`.
- There is no project-level pytest configuration; for local runs, pass `--ds=config.settings.development`.
- Single-test example:
```bash
pytest apps/objectives/tests.py::TestName --ds=config.settings.development
```
- Full suite example:
```bash
pytest --ds=config.settings.development
```

No dedicated lint/format tool configuration is present in the repo (`ruff`, `black`, `flake8`, `pre-commit`, `pyproject.toml`, etc. were not found). Prefer the project’s existing Django/Python conventions and test commands unless a tool is explicitly added.

## High-level architecture

The main routing table is in `config/urls.py`:
- `/api/v1/auth/` mounts account and JWT auth endpoints.
- Project-scoped APIs are nested under `/api/v1/projects/<project_id>/...` for tasks, resources, assignments, baselines, KPIs, reports, objectives, and meetings.
- Notifications live under `/api/v1/notifications/` and are not project-scoped.
- Server-rendered pages are split between accounts, discussions, and the project frontend entrypoints.

Domain app structure:
- `apps/projects`: project core models and membership-based access control.
- `apps/tasks`: tasks, dependencies, and scheduling logic.
- `apps/resources`, `apps/assignments`, `apps/costs`: project resources and cost tracking.
- `apps/baselines`, `apps/kpis`, `apps/reports`: baseline comparison and reporting.
- `apps/meetings`, `apps/discussions`, `apps/notifications`: collaboration and alerts.
- `apps/accounts`: users, profiles, email confirmation, and session cleanup.

Most apps follow the same shape: `models.py`, `serializers.py`, `views.py`, `urls.py`, and sometimes `services.py` or `signals.py`.

Core implementation conventions:
- Business logic belongs in `services.py`, not in views.
- Permission checks for project-scoped APIs are centralized in `apps/projects/permissions.py` and should be reused for new endpoints.
- `apps/tasks/services.py` contains the CPM logic (`CPMCalculator`) and `apps/kpis/services.py` contains KPI calculations (`KPICalculator`).
- Celery tasks live in each app’s `tasks.py` and are scheduled from `CELERY_BEAT_SCHEDULE` in `config/settings/base.py`.
- Side effects often appear via Django signals (`signals.py` in accounts, assignments, and tasks); check these when behavior seems to happen “by magic”.
- Real-time interactions use Channels (Redis as the channel layer) and WebSocket routes from `apps.notifications.routing` and `apps.discussions.routing`.

## Key conventions specific to this codebase

- Keep project-scoped API endpoints aligned with the project structure in `config/urls.py`; `project_id` is usually read from `self.kwargs` in the view layer.
- Prefer reusing `apps.projects.permissions` and project membership checks instead of inventing new access control patterns.
- For local development, set `DJANGO_SETTINGS_MODULE=config.settings.development` because both the default Django and ASGI/Celery entrypoints use production settings.
- Environment values are loaded from `.env` using `python-decouple`; when adding settings, follow the same pattern instead of hardcoding values.
- For anything that changes business behavior, check existing service-layer code before implementing a view-only patch.
- HTML templates live in the top-level `templates/` directory, organized by app, and server-rendered frontend URLs are defined through `*frontend_urls` modules.
- The project is intentionally French-locale and time-zone aware; keep user-facing strings and scheduling behavior consistent with that convention.
- Use Redis + PostgreSQL as the default local infrastructure, because Celery tasks, Channels, and the app database are all expected to be available together.
