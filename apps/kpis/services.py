from datetime import date
from decimal import Decimal

from django.db.models import Avg

from apps.projects.models import Project
from apps.baselines.models import Baseline
from apps.tasks.models import Task
from .models import ProjectKPI


class KPICalculator:
    def __init__(self, project: Project, baseline: Baseline, status_date: date):
        self.project = project
        self.baseline = baseline
        self.status_date = status_date

    def calculate(self) -> ProjectKPI:
        tasks = Task.objects.filter(project=self.project, is_summary=False)

        total_tasks = tasks.count()
        completed_tasks = tasks.filter(status='completed').count()
        overdue_tasks = tasks.filter(
            planned_end__lt=self.status_date,
            percent_complete__lt=100,
            status__in=['not_started', 'in_progress'],
        ).count()
        milestones = tasks.filter(is_milestone=True)
        milestones_reached = milestones.filter(status='completed').count()
        milestones_total = milestones.count()
        critical_count = tasks.filter(is_critical=True).count()
        overall_pct = tasks.aggregate(avg=Avg('percent_complete'))['avg'] or Decimal('0')

        # SPI based on baseline schedule progress
        baseline_tasks = {bt.task_id: bt for bt in self.baseline.tasks.all()} if self.baseline else {}
        bcws = Decimal('0')
        bcwp = Decimal('0')
        for task in tasks:
            bt = baseline_tasks.get(task.id)
            if not bt:
                continue
            if bt.planned_end <= self.status_date:
                bcws += Decimal('1')
            elif bt.planned_start <= self.status_date:
                days_total = (bt.planned_end - bt.planned_start).days or 1
                days_elapsed = (self.status_date - bt.planned_start).days
                bcws += Decimal(str(min(1, days_elapsed / days_total)))
            bcwp += task.percent_complete / Decimal('100')

        spi = (bcwp / bcws) if bcws > 0 else Decimal('1')
        sv = bcwp - bcws

        # Resource KPIs
        from apps.resources.models import Resource
        resources = Resource.objects.filter(project=self.project)
        total_res = resources.count()
        overalloc = 0
        util_sum = 0
        for res in resources:
            daily = res.get_utilization(self.project.start_date, self.status_date)
            if daily:
                util_sum += sum(daily.values()) / len(daily)
                if max(daily.values()) > float(res.max_units):
                    overalloc += 1
        res_util_avg = (util_sum / total_res) if total_res else 0

        schedule_health = 'green' if spi >= Decimal('0.95') else ('orange' if spi >= Decimal('0.85') else 'red')
        resource_health = 'red' if overalloc > 0 else 'green'

        return ProjectKPI.objects.create(
            project=self.project,
            baseline=self.baseline,
            status_date=self.status_date,
            spi=spi,
            sv=sv,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            overdue_tasks=overdue_tasks,
            milestones_reached=milestones_reached,
            milestones_total=milestones_total,
            critical_tasks_count=critical_count,
            overall_percent_complete=overall_pct,
            total_resources=total_res,
            overallocated_resources=overalloc,
            resource_utilization_avg=Decimal(str(round(res_util_avg, 2))),
            schedule_health=schedule_health,
            resource_health=resource_health,
        )
