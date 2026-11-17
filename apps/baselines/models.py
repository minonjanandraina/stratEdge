from django.db import models
from django.contrib.auth.models import User
from apps.projects.models import Project
from apps.tasks.models import Task


class Baseline(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='baselines')
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Ligne de base'
        verbose_name_plural = 'Lignes de base'

    def __str__(self):
        return f'{self.name} — {self.project.name}'

    def save(self, *args, **kwargs):
        if self.is_active:
            Baseline.objects.filter(project=self.project, is_active=True).update(is_active=False)
        super().save(*args, **kwargs)


class BaselineTask(models.Model):
    baseline = models.ForeignKey(Baseline, on_delete=models.CASCADE, related_name='tasks')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='baseline_snapshots')

    planned_start = models.DateField()
    planned_end = models.DateField()
    planned_duration = models.DecimalField(max_digits=8, decimal_places=2)
    planned_work = models.DecimalField(max_digits=10, decimal_places=2)
    percent_complete = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        unique_together = ['baseline', 'task']
        verbose_name = 'Tâche baseline'
        verbose_name_plural = 'Tâches baseline'

    def __str__(self):
        return f'{self.baseline.name} — {self.task.name}'
