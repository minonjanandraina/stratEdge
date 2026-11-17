from pathlib import Path
from decouple import config, Csv
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'django_celery_beat',
    'django_celery_results',
    'channels',
    'auditlog',
]

LOCAL_APPS = [
    'apps.accounts',
    'apps.projects',
    'apps.tasks',
    'apps.resources',
    'apps.assignments',
    'apps.costs',
    'apps.baselines',
    'apps.kpis',
    'apps.reports',
    'apps.notifications',
    'apps.objectives',
    'apps.meetings',
    'apps.discussions',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'auditlog.middleware.AuditlogMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='msproject'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='postgres'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Indian/Antananarivo'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# DRF
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}

# JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Celery
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'django-cache'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    # KPI recalculation — every day at 06:00
    'daily-kpis': {
        'task': 'apps.kpis.tasks.recalculate_all_kpis',
        'schedule': crontab(hour=6, minute=0),
    },
    # Notifs #1/#2/#3 — deadline J-3 / J-1 / J-0 — every day at 07:00
    'deadline-reminders': {
        'task': 'apps.kpis.tasks.send_deadline_reminders',
        'schedule': crontab(hour=7, minute=0),
    },
    # Notif #4 — overdue tasks (once per task) — every day at 07:15
    'overdue-notifications': {
        'task': 'apps.kpis.tasks.send_overdue_notifications',
        'schedule': crontab(hour=7, minute=15),
    },
    # Notif #6 — project deadline J-7 — every day at 07:30
    'project-deadline-reminders': {
        'task': 'apps.kpis.tasks.send_project_deadline_reminders',
        'schedule': crontab(hour=7, minute=30),
    },
    # Notif #7 — SPI alert (max 1×/week) — every Monday at 08:00
    'kpi-spi-alerts': {
        'task': 'apps.kpis.tasks.send_kpi_alerts',
        'schedule': crontab(hour=8, minute=0, day_of_week=1),
    },
    # Notif #9 — meeting reminder J-1 — every day at 17:00
    'meeting-reminders': {
        'task': 'apps.kpis.tasks.send_meeting_reminders',
        'schedule': crontab(hour=17, minute=0),
    },
    # Rappel hebdomadaire aux membres des projets — chaque lundi à 09:00
    'weekly-project-update-reminders': {
        'task': 'apps.notifications.tasks.send_weekly_project_update_reminders',
        'schedule': crontab(hour=9, minute=0, day_of_week=1),
    },
    # Nettoyage sessions expirées — chaque nuit à 03:00
    'clear-expired-sessions': {
        'task': 'apps.accounts.tasks.clear_expired_sessions',
        'schedule': crontab(hour=3, minute=0),
    },
}

# Channels
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [config('REDIS_URL', default='redis://localhost:6379/0')],
        },
    },
}

# CORS
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:3000', cast=Csv())

DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@stratedge.com')
SITE_URL = config('SITE_URL', default='http://localhost:8000')
EMAIL_CONFIRMATION_EXPIRY_HOURS = 24

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Sessions
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 28800          # 8 heures
SESSION_SAVE_EVERY_REQUEST = True   # renouvelle l'expiration à chaque requête
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

SESSION_COOKIE_NAME = 'stratedge_sessionid'
CSRF_COOKIE_NAME = 'stratedge_csrftoken'
