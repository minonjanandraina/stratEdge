from django.apps import AppConfig


class MeetingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.meetings'
    verbose_name = 'Réunions'

    def ready(self):
        from auditlog.registry import auditlog
        from .models import Meeting
        auditlog.register(Meeting)
