from django.db import models
from apps.projects.models import Project
from apps.baselines.models import Baseline


class ProjectKPI(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='kpis')
    baseline = models.ForeignKey(Baseline, on_delete=models.SET_NULL, null=True)
    calculated_at = models.DateTimeField(auto_now_add=True)
    status_date = models.DateField()

    # Planning KPIs
    total_tasks = models.PositiveIntegerField(default=0)
    completed_tasks = models.PositiveIntegerField(default=0)
    overdue_tasks = models.PositiveIntegerField(default=0)
    milestones_reached = models.PositiveIntegerField(default=0)
    milestones_total = models.PositiveIntegerField(default=0)
    critical_tasks_count = models.PositiveIntegerField(default=0)
    overall_percent_complete = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # SPI planning
    spi = models.DecimalField(max_digits=8, decimal_places=4, default=1)
    sv = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Resource KPIs
    total_resources = models.PositiveIntegerField(default=0)
    overallocated_resources = models.PositiveIntegerField(default=0)
    resource_utilization_avg = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Health
    schedule_health = models.CharField(max_length=10, default='green')
    resource_health = models.CharField(max_length=10, default='green')

    class Meta:
        ordering = ['-calculated_at']
        get_latest_by = 'calculated_at'
        verbose_name = 'KPI Projet'
        verbose_name_plural = 'KPIs Projets'

    def __str__(self):
        return f'KPI {self.project.name} — {self.status_date}'
