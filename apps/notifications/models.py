from django.db import models
from django.contrib.auth.models import User
from apps.tasks.models import Task


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        # Tâches
        ('deadline_j3',         'Échéance dans 3 jours'),
        ('deadline_j1',         'Échéance demain'),
        ('deadline_j0',         "Échéance aujourd'hui"),
        ('task_overdue',        'Tâche en retard'),
        ('task_assigned',       'Tâche assignée'),
        ('task_completed',      'Tâche terminée'),
        # Projet
        ('project_deadline_j7', 'Fin de projet dans 7 jours'),
        ('kpi_spi_alert',       'Alerte SPI'),
        ('project_weekly_update', 'Rappel hebdomadaire de mise à jour'),
        ('member_added',        'Ajout au projet'),
        ('pm_assigned',         'Nommé chef de projet'),
        # Réunions
        ('meeting_reminder',    'Rappel réunion'),
        # Anciens types conservés
        ('overdue_task',        'Tâche en retard (legacy)'),
        ('project_update',      'Mise à jour projet'),
        ('kpi_alert',           'Alerte KPI'),
        ('mention',             'Mention'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    related_task = models.ForeignKey(
        Task, on_delete=models.SET_NULL, null=True, blank=True
    )
    related_project = models.ForeignKey(
        'projects.Project', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='notifications',
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f'{self.title} → {self.user.username}'
