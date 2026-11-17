from django.core.management.base import BaseCommand
from apps.accounts.models import Department, UserProfile


class Command(BaseCommand):
    help = 'Assigne le département DFS à tous les utilisateurs sans département.'

    def handle(self, *args, **options):
        try:
            dfs = Department.objects.get(name='DFS')
        except Department.DoesNotExist:
            self.stderr.write(self.style.ERROR('Département "DFS" introuvable. Lancez d\'abord les migrations.'))
            return

        profiles = UserProfile.objects.filter(department__isnull=True)
        count = profiles.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('Aucun utilisateur sans département.'))
            return

        profiles.update(department=dfs)
        self.stdout.write(self.style.SUCCESS(
            f'{count} utilisateur(s) assigné(s) au département DFS.'
        ))
