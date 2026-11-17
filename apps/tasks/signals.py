from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .models import Task, TaskDependency


def _recalculate_schedule(project):
    """Recompute WBS, CPM dates and summary rollups synchronously so the
    Gantt, the task table and the detail modal all read the same,
    up-to-date dates before the API response is sent."""
    from .services import recalculate_schedule
    recalculate_schedule(project)


@receiver(pre_save, sender=Task)
def track_task_completion(sender, instance, **kwargs):
    """Flag tasks that transition to 'completed' so post_save can notify."""
    if not instance.pk:
        return
    try:
        old = Task.objects.get(pk=instance.pk)
        instance._just_completed = (old.status != 'completed' and instance.status == 'completed')
    except Task.DoesNotExist:
        instance._just_completed = False


@receiver(post_save, sender=Task)
def task_saved(sender, instance, created, **kwargs):
    _recalculate_schedule(instance.project)

    # Notification #10 — Tâche terminée → PM (interne uniquement)
    if not created and getattr(instance, '_just_completed', False):
        if instance.project.manager and instance.project.manager != _current_user(instance):
            from apps.notifications.utils import notify
            notify(
                user=instance.project.manager,
                notif_type='task_completed',
                title=f'Tâche terminée : {instance.name}',
                message=(
                    f'La tâche "{instance.name}" du projet "{instance.project.name}" '
                    f'vient d\'être marquée comme terminée.'
                ),
                task=instance,
                send_email=False,
            )


@receiver(post_delete, sender=Task)
def task_deleted(sender, instance, **kwargs):
    _recalculate_schedule(instance.project)


@receiver(post_save, sender=TaskDependency)
@receiver(post_delete, sender=TaskDependency)
def dependency_changed(sender, instance, **kwargs):
    _recalculate_schedule(instance.predecessor.project)


def _current_user(instance):
    """Return None — placeholder; signals don't have request context."""
    return None
