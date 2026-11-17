def notify(user, notif_type, title, message, task=None, project=None, send_email=False):
    """
    Create a deduped internal notification and optionally send an email.

    Dedup key: (user, notification_type, related_task) or (user, notification_type, related_project).
    Returns True if the notification was newly created, False if it already existed.
    """
    from .models import Notification

    lookup = {'user': user, 'notification_type': notif_type}
    if task is not None:
        lookup['related_task'] = task
    elif project is not None:
        lookup['related_project'] = project

    _, created = Notification.objects.get_or_create(
        **lookup,
        defaults={'title': title, 'message': message},
    )

    if send_email and created and user.email:
        try:
            from config.mail import send_notification_email
            send_notification_email(user.email, title, message, notif_type)
        except Exception:
            pass

    return created
