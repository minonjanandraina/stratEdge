from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.projects'

    def ready(self):
        from auditlog.registry import auditlog
        from .models import Project, ProjectMembership
        auditlog.register(Project)
        auditlog.register(ProjectMembership)
