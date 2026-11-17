from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Assignment


@receiver(post_save, sender=Assignment)
def assignment_created(sender, instance, created, **kwargs):
    """Notification #5 — Tâche assignée → ressource (interne + email)."""
    if not created:
        return
    user = instance.resource.user
    if not user:
        return

    from apps.notifications.utils import notify
    notify(
        user=user,
        notif_type='task_assigned',
        title=f'Tâche assignée : {instance.task.name}',
        message=(
            f'Vous avez été assigné(e) à la tâche "{instance.task.name}" '
            f'du projet "{instance.task.project.name}" '
            f'(échéance : {instance.task.planned_end}).'
        ),
        task=instance.task,
        send_email=True,
    )
