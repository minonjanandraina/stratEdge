from datetime import timedelta

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.projects.models import Project
from apps.notifications.models import Notification
from config.mail import send_notification_email

User = get_user_model()


@shared_task
def send_weekly_project_update_reminders():
    """Send a weekly reminder to each project member to update their tasks."""
    now = timezone.now()
    start_of_week = now - timedelta(days=now.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

    projects = Project.objects.filter(status='active').prefetch_related('memberships__user')

    for project in projects:
        recipients = set()
        if project.manager:
            recipients.add(project.manager)
        memberships = project.memberships.filter(role__in=['pm', 'member']).select_related('user')
        for membership in memberships:
            if membership.user:
                recipients.add(membership.user)

        for user in recipients:
            if not user or not user.email:
                continue

            already_sent = Notification.objects.filter(
                user=user,
                notification_type='project_weekly_update',
                related_project=project,
                created_at__gte=start_of_week,
            ).exists()
            if already_sent:
                continue

            title = f"Mise à jour hebdomadaire : {project.name}"
            message = (
                f"Bonjour {user.first_name or user.username},\n\n"
                f"Ce rappel hebdomadaire vise à vous rappeler de mettre à jour les tâches du projet "
                f"\"{project.name}\". Vérifiez les échéances, le statut et l'avancement avant la prochaine revue."
            )

            Notification.objects.create(
                user=user,
                notification_type='project_weekly_update',
                title=title,
                message=message,
                related_project=project,
            )
            send_notification_email(user.email, title, message, 'project_weekly_update')
