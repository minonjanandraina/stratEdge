import os
from django.db import models
from django.contrib.auth.models import User


def _attachment_upload_path(instance, filename):
    if instance.task_id:
        return f'attachments/tasks/{instance.task_id}/{filename}'
    return f'attachments/projects/{instance.project_id}/{filename}'


class Project(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('active', 'Actif'),
        ('on_hold', 'En pause'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé'),
    ]



    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    color = models.CharField(max_length=7, blank=True, null=True, help_text="Couleur du projet (format hexadécimal)")
    manager = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='managed_projects'
    )
    members = models.ManyToManyField(User, through='ProjectMembership', related_name='projects')

    start_date = models.DateField()
    end_date = models.DateField()
    actual_start = models.DateField(null=True, blank=True)
    actual_end = models.DateField(null=True, blank=True)

    working_days = models.JSONField(default=list)  # [1,2,3,4,5] = lundi-vendredi
    working_hours_per_day = models.DecimalField(max_digits=4, decimal_places=1, default=8)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Projet'
        verbose_name_plural = 'Projets'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.working_days:
            self.working_days = [1, 2, 3, 4, 5]
        super().save(*args, **kwargs)

    @property
    def duration_days(self):
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days
        return 0

    @property
    def progress(self):
        from django.db.models import Avg
        tasks = self.tasks.filter(is_summary=False)
        if not tasks.exists():
            return 0
        avg = tasks.aggregate(avg=Avg('percent_complete'))['avg']
        return round(float(avg or 0), 2)


class ProjectMembership(models.Model):
    ROLE_CHOICES = [
        ('pm', 'Chef de projet'),
        ('member', 'Membre'),
        ('viewer', 'Observateur'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['project', 'user']
        ordering = ['joined_at']
        verbose_name = 'Membre du projet'
        verbose_name_plural = 'Membres du projet'

    def __str__(self):
        return f'{self.user.username} — {self.project.name} ({self.get_role_display()})'


class Folder(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='folders')
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='children'
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='created_folders'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Dossier'
        verbose_name_plural = 'Dossiers'

    def __str__(self):
        return f'{self.name} — {self.project.name}'


class Attachment(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='attachments',
        null=True, blank=True,
    )
    task = models.ForeignKey(
        'tasks.Task', on_delete=models.CASCADE, related_name='attachments',
        null=True, blank=True,
    )
    folder = models.ForeignKey(
        Folder, on_delete=models.SET_NULL, null=True, blank=True, related_name='attachments'
    )
    file = models.FileField(upload_to=_attachment_upload_path)
    name = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='attachments'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    size = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Pièce jointe'
        verbose_name_plural = 'Pièces jointes'

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        storage, path = self.file.storage, self.file.path
        super().delete(*args, **kwargs)
        try:
            storage.delete(path)
        except Exception:
            pass


class Note(models.Model):
    """Note personnelle : privée à chaque utilisateur au sein d'un projet."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='notes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='project_notes')
    content = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['project', 'user']
        verbose_name = 'Note personnelle'
        verbose_name_plural = 'Notes personnelles'

    def __str__(self):
        return f'Note de {self.user.username} — {self.project.name}'


class Holiday(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='holidays')
    date = models.DateField()
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ['project', 'date']
        ordering = ['date']
        verbose_name = 'Jour férié'
        verbose_name_plural = 'Jours fériés'

    def __str__(self):
        return f'{self.name} ({self.date}) — {self.project.name}'


class ProjectSettings(models.Model):
    lock_on_completion = models.BooleanField(
        default=True,
        verbose_name='Verrouiller les projets terminés/annulés',
        help_text=(
            "Si activé, les tâches et membres d'un projet dont le statut est "
            "« Terminé » ou « Annulé » ne peuvent plus être modifiés."
        ),
    )
    admin_see_all_projects = models.BooleanField(
        default=True,
        verbose_name='Les admins voient tous les projets',
        help_text=(
            "Si activé, les administrateurs voient tous les projets de la plateforme. "
            "Si désactivé, ils ne voient que les projets auxquels ils sont assignés."
        ),
    )

    class Meta:
        verbose_name = 'Paramètres projet'
        verbose_name_plural = 'Paramètres projet'

    def __str__(self):
        return 'Paramètres projet'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
