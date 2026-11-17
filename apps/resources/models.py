from django.db import models
from django.contrib.auth.models import User
from apps.projects.models import Project


class Resource(models.Model):
    RESOURCE_TYPES = [
        ('work', 'Travail (Humain)'),
        ('material', 'Matériel'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='resources')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255)
    resource_type = models.CharField(max_length=10, choices=RESOURCE_TYPES, default='work')

    max_units = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    availability_start = models.DateField(null=True, blank=True)
    availability_end = models.DateField(null=True, blank=True)

    material_unit = models.CharField(max_length=50, blank=True)

    working_days = models.JSONField(default=list)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['project', 'name']
        verbose_name = 'Ressource'
        verbose_name_plural = 'Ressources'

    def __str__(self):
        return f'{self.name} ({self.project.name})'

    def save(self, *args, **kwargs):
        if not self.working_days:
            self.working_days = self.project.working_days or [1, 2, 3, 4, 5]
        super().save(*args, **kwargs)

    def get_utilization(self, start_date, end_date):
        """Returns daily utilization % for a given period."""
        from apps.assignments.models import Assignment
        from datetime import timedelta
        assignments = self.assignments.filter(
            task__planned_start__lte=end_date,
            task__planned_end__gte=start_date,
        ).select_related('task')
        daily = {}
        for assignment in assignments:
            task_start = max(assignment.task.planned_start, start_date)
            task_end = min(assignment.task.planned_end, end_date)
            current = task_start
            while current <= task_end:
                daily[current] = daily.get(current, 0) + float(assignment.units)
                current += timedelta(days=1)
        return daily
