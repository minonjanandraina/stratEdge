from django.db import models
from apps.tasks.models import Task
from apps.resources.models import Resource


class Assignment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='assignments')
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='assignments')
    units = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    planned_work = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    actual_work = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    remaining_work = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['task', 'resource']
        verbose_name = 'Affectation'
        verbose_name_plural = 'Affectations'

    def __str__(self):
        return f'{self.resource.name} → {self.task.name}'

    def save(self, *args, **kwargs):
        if not self.start_date:
            self.start_date = self.task.planned_start
        if not self.end_date:
            self.end_date = self.task.planned_end
        super().save(*args, **kwargs)


class TimeEntry(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='time_entries')
    date = models.DateField()
    hours = models.DecimalField(max_digits=6, decimal_places=2)
    is_overtime = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name = 'Saisie de temps'
        verbose_name_plural = 'Saisies de temps'

    def __str__(self):
        return f'{self.assignment} — {self.date} ({self.hours}h)'
