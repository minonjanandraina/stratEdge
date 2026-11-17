from celery import shared_task


@shared_task
def notify_task_note(note_id: int):
    from .models import TaskNote
    from config.mail import send_task_note_email

    try:
        note = TaskNote.objects.select_related(
            'task__project__manager', 'created_by'
        ).get(pk=note_id)
    except TaskNote.DoesNotExist:
        return

    task = note.task
    project = task.project
    author = note.created_by

    recipients = set()
    if project.manager and project.manager != author and project.manager.email:
        recipients.add(project.manager.email)
    for m in project.memberships.select_related('user').all():
        if m.user != author and m.user.email:
            recipients.add(m.user.email)

    if recipients:
        try:
            send_task_note_email(list(recipients), project, task, note)
        except Exception:
            pass
