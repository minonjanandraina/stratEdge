from django.apps import AppConfig


class ObjectivesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.objectives'
    verbose_name = 'Cadre Logique'

    def ready(self):
        from auditlog.registry import auditlog
        from .models import Objective
        auditlog.register(Objective)
