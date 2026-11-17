from django.db import models
from django.contrib.auth.models import User
from apps.projects.models import Project


class Meeting(models.Model):
    STATUS_CHOICES = [
        ('planned', 'Planifiée'),
        ('held', 'Tenue'),
        ('cancelled', 'Annulée'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='meetings')
    title = models.CharField(max_length=255)
    date = models.DateTimeField()
    location = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    participants = models.ManyToManyField(User, blank=True, related_name='project_meetings')
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='created_meetings'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        verbose_name = 'Réunion'
        verbose_name_plural = 'Réunions'

    def __str__(self):
        return f'{self.title} ({self.date.date()})'


class MeetingMinute(models.Model):
    meeting = models.OneToOneField(Meeting, on_delete=models.CASCADE, related_name='minutes')
    content = models.TextField(blank=True)
    written_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='written_minutes'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Compte rendu'
        verbose_name_plural = 'Comptes rendus'


class MeetingDecision(models.Model):
    STATUS_CHOICES = [
        ('open', 'Ouverte'),
        ('done', 'Réalisée'),
        ('cancelled', 'Annulée'),
    ]

    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='decisions')
    description = models.TextField()
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_decisions'
    )
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Décision'
        verbose_name_plural = 'Décisions'

    def __str__(self):
        return self.description[:80]
