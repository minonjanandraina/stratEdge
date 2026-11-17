from datetime import date, timedelta
from celery import shared_task


# ── Helpers ──────────────────────────────────────────────────────────────────

def _task_recipients(task):
    recipients = set()
    if task.project.manager:
        recipients.add(task.project.manager)
    for assignment in task.assignments.all():
        if assignment.resource.user:
            recipients.add(assignment.resource.user)
    return recipients


def _project_recipients(project):
    recipients = set()
    if project.manager:
        recipients.add(project.manager)
    for m in project.memberships.all():
        recipients.add(m.user)
    return recipients


# ── KPI recalculation ─────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3)
def recalculate_project_kpis(self, project_id: int):
    try:
        from apps.projects.models import Project
        from apps.kpis.services import KPICalculator
        project = Project.objects.get(pk=project_id)
        baseline = project.baselines.filter(is_active=True).first()
        if not baseline:
            return
        KPICalculator(project, baseline, date.today()).calculate()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)


@shared_task
def recalculate_all_kpis():
    from apps.projects.models import Project
    for project in Project.objects.filter(status='active'):
        recalculate_project_kpis.delay(project.id)


# ── Notification #1 / #2 / #3 — Deadline J-3, J-1, J-0 ──────────────────────

@shared_task
def send_deadline_reminders():
    from apps.tasks.models import Task
    from apps.notifications.utils import notify

    today = date.today()
    schedule = {
        3: ('deadline_j3', False),
        1: ('deadline_j1', True),
        0: ('deadline_j0', False),
    }
    labels = {3: 'dans 3 jours', 1: 'demain', 0: "aujourd'hui"}

    for days, (notif_type, with_email) in schedule.items():
        target_date = today + timedelta(days=days)
        tasks = Task.objects.filter(
            planned_end=target_date,
            is_summary=False,
            status__in=['not_started', 'in_progress'],
        ).select_related('project__manager').prefetch_related('assignments__resource__user')

        label = labels[days]
        for task in tasks:
            for user in _task_recipients(task):
                notify(
                    user=user,
                    notif_type=notif_type,
                    title=f'Échéance {label} : {task.name}',
                    message=(
                        f'La tâche "{task.name}" du projet "{task.project.name}" '
                        f'arrive à échéance {label} ({task.planned_end}).'
                    ),
                    task=task,
                    send_email=with_email,
                )


# ── Notification #4 — Tâche en retard (une seule fois) ───────────────────────

@shared_task
def send_overdue_notifications():
    from apps.tasks.models import Task
    from apps.notifications.utils import notify

    today = date.today()
    tasks = Task.objects.filter(
        planned_end__lt=today,
        is_summary=False,
        status__in=['not_started', 'in_progress'],
    ).select_related('project__manager').prefetch_related('assignments__resource__user')

    for task in tasks:
        for user in _task_recipients(task):
            notify(
                user=user,
                notif_type='task_overdue',
                title=f'Tâche en retard : {task.name}',
                message=(
                    f'La tâche "{task.name}" du projet "{task.project.name}" '
                    f'est en retard (échéance : {task.planned_end}).'
                ),
                task=task,
                send_email=True,
            )


# ── Notification #6 — Fin de projet J-7 ──────────────────────────────────────

@shared_task
def send_project_deadline_reminders():
    from apps.projects.models import Project
    from apps.notifications.utils import notify

    target = date.today() + timedelta(days=7)
    projects = Project.objects.filter(
        end_date=target,
        status__in=['active', 'draft'],
    ).prefetch_related('memberships__user')

    for project in projects:
        for user in _project_recipients(project):
            notify(
                user=user,
                notif_type='project_deadline_j7',
                title=f'Fin de projet dans 7 jours : {project.name}',
                message=f'Le projet "{project.name}" se termine dans 7 jours ({project.end_date}).',
                project=project,
                send_email=True,
            )


# ── Notification #7 — Alerte SPI < 0.8 (max 1×/semaine) ─────────────────────

@shared_task
def send_kpi_alerts():
    from django.utils import timezone
    from apps.projects.models import Project
    from apps.notifications.models import Notification
    from config.mail import send_notification_email

    threshold_date = timezone.now() - timedelta(days=7)
    projects = Project.objects.filter(status='active').select_related('manager').prefetch_related('kpis')

    for project in projects:
        kpi = project.kpis.first()
        if not kpi or float(kpi.spi) >= 0.8 or not project.manager:
            continue

        already = Notification.objects.filter(
            user=project.manager,
            notification_type='kpi_spi_alert',
            related_project=project,
            created_at__gte=threshold_date,
        ).exists()
        if already:
            continue

        title = f'Alerte SPI : {project.name}'
        message = (
            f'Le SPI du projet "{project.name}" est de {float(kpi.spi):.2f} '
            f'(seuil : 0.80). Le planning dérape significativement.'
        )
        Notification.objects.create(
            user=project.manager,
            notification_type='kpi_spi_alert',
            related_project=project,
            title=title,
            message=message,
        )
        if project.manager.email:
            send_notification_email(project.manager.email, title, message, 'kpi_spi_alert')


# ── Notification #9 — Rappel réunion J-1 ─────────────────────────────────────

@shared_task
def send_meeting_reminders():
    from django.utils import timezone
    from apps.meetings.models import Meeting
    from apps.notifications.models import Notification
    from config.mail import send_notification_email

    tomorrow_start = (timezone.now() + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    tomorrow_end = tomorrow_start + timedelta(days=1)

    meetings = Meeting.objects.filter(
        date__gte=tomorrow_start,
        date__lt=tomorrow_end,
        status='planned',
    ).select_related('project').prefetch_related('participants')

    for meeting in meetings:
        title = f'Réunion demain : {meeting.title}'
        msg = (
            f'Rappel : la réunion "{meeting.title}" du projet "{meeting.project.name}" '
            f'est prévue demain à {meeting.date.strftime("%H:%M")}.'
        )
        if meeting.location:
            msg += f' Lieu : {meeting.location}.'

        for user in meeting.participants.all():
            _, created = Notification.objects.get_or_create(
                user=user,
                notification_type='meeting_reminder',
                related_project=meeting.project,
                title=title,
                defaults={'message': msg},
            )
            if created and user.email:
                send_notification_email(user.email, title, msg, 'meeting_reminder')
