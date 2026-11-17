from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg

from apps.projects.models import Project
from apps.tasks.models import Task


class Objective(models.Model):
    LEVEL_CHOICES = [
        ('impact',  'Objectif Global (Impact)'),
        ('outcome', 'Objectif Spécifique (Outcome)'),
        ('output',  'Résultat Attendu (Output)'),
    ]
    STATUS_CHOICES = [
        ('not_started', 'Non démarré'),
        ('in_progress', 'En cours'),
        ('achieved',    'Atteint'),
        ('at_risk',     'À risque'),
        ('cancelled',   'Annulé'),
    ]

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='objectives'
    )
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='children',
    )

    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    responsible = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='responsible_objectives',
    )
    target_date = models.DateField(null=True, blank=True)

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='not_started')
    order = models.PositiveIntegerField(default=0)

    tasks = models.ManyToManyField(
        Task, blank=True, related_name='objectives',
    )

    assumptions = models.TextField(blank=True, help_text='Hypothèses / conditions de succès')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['project', 'order']
        verbose_name = 'Objectif'
        verbose_name_plural = 'Objectifs'

    def __str__(self):
        return f'[{self.get_level_display()}] {self.title}'

    @property
    def progress(self):
        """Average percent_complete of directly linked tasks (non-summary only)."""
        tasks = self.tasks.filter(is_summary=False)
        if not tasks.exists():
            return 0
        avg = tasks.aggregate(avg=Avg('percent_complete'))['avg']
        return round(float(avg or 0), 1)

    @property
    def cascade_progress(self):
        """
        If this objective has children, progress = avg of children cascade_progress.
        Otherwise = self.progress (from directly linked tasks).
        """
        children = list(self.children.all())
        if children:
            vals = [c.cascade_progress for c in children]
            return round(sum(vals) / len(vals), 1)
        return self.progress


class Indicator(models.Model):
    """Indicateur Objectivement Vérifiable (IOV) attached to an objective."""

    UNIT_CHOICES = [
        ('number',  'Nombre'),
        ('percent', 'Pourcentage (%)'),
        ('boolean', 'Oui / Non'),
        ('text',    'Texte'),
    ]

    objective = models.ForeignKey(
        Objective, on_delete=models.CASCADE, related_name='indicators'
    )

    label = models.CharField(max_length=255)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='number')

    baseline_value = models.CharField(max_length=100, blank=True, help_text='Valeur de référence (t0)')
    target_value   = models.CharField(max_length=100, blank=True, help_text='Valeur cible à atteindre')
    current_value  = models.CharField(max_length=100, blank=True, help_text='Valeur actuelle mesurée')

    verification_source = models.CharField(
        max_length=255, blank=True,
        help_text='Source de vérification (rapport, base de données, enquête…)',
    )

    measurement_frequency = models.CharField(
        max_length=50, blank=True,
        help_text='Fréquence de mesure (mensuelle, trimestrielle…)',
    )

    measured_at = models.DateField(null=True, blank=True, help_text='Date de la dernière mesure')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['objective', 'id']
        verbose_name = 'Indicateur (IOV)'
        verbose_name_plural = 'Indicateurs (IOV)'

    def __str__(self):
        return f'{self.label} — {self.objective.title}'
