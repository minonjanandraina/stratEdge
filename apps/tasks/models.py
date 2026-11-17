from django.db import models
from django.contrib.auth import get_user_model
from apps.projects.models import Project

User = get_user_model()


class Task(models.Model):
    DEPENDENCY_TYPES = [
        ('FS', 'Fin-Début'),
        ('SS', 'Début-Début'),
        ('FF', 'Fin-Fin'),
        ('SF', 'Début-Fin'),
    ]
    CONSTRAINT_TYPES = [
        ('ASAP', 'Dès que possible'),
        ('ALAP', 'Le plus tard possible'),
        ('MSO', 'Doit commencer le'),
        ('MFO', 'Doit finir le'),
        ('SNLT', 'Ne peut pas commencer avant le'),
        ('FNLT', 'Ne peut pas finir avant le'),
    ]
    STATUS_CHOICES = [
        ('not_started', 'Non commencée'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminée'),
        ('on_hold', 'En pause'),
        ('cancelled', 'Annulée'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subtasks'
    )

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    wbs_code = models.CharField(max_length=50, blank=True)
    order = models.PositiveIntegerField(default=0)
    level = models.PositiveIntegerField(default=0)

    is_milestone = models.BooleanField(default=False)
    is_summary = models.BooleanField(default=False)
    is_recurring = models.BooleanField(default=False)
    recurrence_rule = models.JSONField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')

    planned_start = models.DateField()
    planned_end = models.DateField()
    planned_duration = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    actual_start = models.DateField(null=True, blank=True)
    actual_end = models.DateField(null=True, blank=True)
    actual_duration = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    percent_complete = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    constraint_type = models.CharField(max_length=10, choices=CONSTRAINT_TYPES, default='ASAP')
    constraint_date = models.DateField(null=True, blank=True)

    is_critical = models.BooleanField(default=False)
    critical_override = models.BooleanField(
        null=True, blank=True,
        help_text="None = automatique (CPM), True = forcée critique, False = forcée non critique",
    )
    early_start = models.DateField(null=True, blank=True)
    early_finish = models.DateField(null=True, blank=True)
    late_start = models.DateField(null=True, blank=True)
    late_finish = models.DateField(null=True, blank=True)
    total_float = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    free_float = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['project', 'order']
        verbose_name = 'Tâche'
        verbose_name_plural = 'Tâches'

    def save(self, *args, **kwargs):
        if self.is_milestone:
            # Jalons : durée nulle, statut binaire
            self.planned_duration = 0
            if self.status not in ('completed', 'cancelled', 'not_started'):
                self.status = 'not_started'
            self.percent_complete = 100 if self.status == 'completed' else 0
            if self.status == 'completed' and not self.actual_end:
                from datetime import date
                self.actual_end = date.today()
        elif not self.is_summary:
            pct = int(self.percent_complete or 0)
            if pct == 100 and self.status not in ('completed', 'cancelled'):
                self.status = 'completed'
                if not self.actual_end:
                    from datetime import date
                    self.actual_end = date.today()
            elif 0 < pct < 100 and self.status == 'not_started':
                self.status = 'in_progress'
                if not self.actual_start:
                    from datetime import date
                    self.actual_start = date.today()
            elif pct == 0 and self.status == 'completed':
                self.status = 'not_started'
        super().save(*args, **kwargs)
        if self.parent_id:
            self._update_parent_status()

    def _update_parent_status(self):
        """Propagate child status/progress/dates up to the parent summary task."""
        children = list(Task.objects.filter(parent_id=self.parent_id).values(
            'status', 'percent_complete', 'planned_start', 'planned_end'
        ))
        if not children:
            return
        statuses = [c['status'] for c in children]
        pcts = [float(c['percent_complete']) for c in children]

        if all(s == 'cancelled' for s in statuses):
            new_status, new_pct = 'cancelled', 0
        elif all(s in ('not_started', 'cancelled') for s in statuses):
            new_status, new_pct = 'not_started', 0
        elif all(s in ('completed', 'cancelled') for s in statuses):
            non_cancelled = [p for s, p in zip(statuses, pcts) if s != 'cancelled']
            new_status = 'completed'
            new_pct = sum(non_cancelled) / len(non_cancelled) if non_cancelled else 100
        elif all(s in ('on_hold', 'cancelled') for s in statuses):
            new_status, new_pct = 'on_hold', sum(pcts) / len(pcts)
        else:
            new_status = 'in_progress'
            new_pct = sum(pcts) / len(pcts)

        starts = [c['planned_start'] for c in children if c['planned_start']]
        ends = [c['planned_end'] for c in children if c['planned_end']]
        update_fields = dict(status=new_status, percent_complete=round(new_pct, 2))
        if starts:
            update_fields['planned_start'] = min(starts)
        if ends:
            update_fields['planned_end'] = max(ends)
        if starts and ends:
            update_fields['planned_duration'] = (max(ends) - min(starts)).days + 1

        Task.objects.filter(pk=self.parent_id).update(**update_fields)
        # Propagate further up without triggering full save()
        parent = Task.objects.filter(pk=self.parent_id).only('parent_id').first()
        if parent and parent.parent_id:
            parent._update_parent_status()

    def __str__(self):
        return f'[{self.wbs_code}] {self.name}' if self.wbs_code else self.name

    @property
    def health_indicator(self):
        from datetime import date
        if self.status == 'completed':
            return 'green'
        today = date.today()
        if self.planned_end < today and self.percent_complete < 100:
            return 'red'
        days_total = (self.planned_end - self.planned_start).days or 1
        days_elapsed = (today - self.planned_start).days
        expected_pct = min(100, (days_elapsed / days_total) * 100)
        if self.percent_complete < expected_pct - 20:
            return 'orange'
        return 'green'


class TaskDependency(models.Model):
    predecessor = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='successors')
    successor = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='predecessors')
    dependency_type = models.CharField(max_length=2, choices=Task.DEPENDENCY_TYPES, default='FS')
    lag = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    class Meta:
        unique_together = ['predecessor', 'successor']
        ordering = ['predecessor', 'successor']
        verbose_name = 'Dépendance'
        verbose_name_plural = 'Dépendances'

    def __str__(self):
        return f'{self.predecessor} → {self.successor} ({self.dependency_type})'


class TaskNote(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='task_notes')
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='task_notes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Note de tâche'
        verbose_name_plural = 'Notes de tâche'

    def __str__(self):
        return f'Note sur {self.task} par {self.created_by}'
