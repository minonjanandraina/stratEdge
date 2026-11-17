from django.core.management.base import BaseCommand

from apps.notifications.tasks import send_weekly_project_update_reminders


class Command(BaseCommand):
    help = 'Send the weekly project task-update reminder to all active project members.'

    def handle(self, *args, **options):
        send_weekly_project_update_reminders()
        self.stdout.write(
            self.style.SUCCESS('Weekly project update reminders sent successfully.')
        )
