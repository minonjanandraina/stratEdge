"""
Management command: create a sample project with tasks for testing.
Usage: python manage.py create_sample_project --name "Test" --tasks 20
"""
import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.projects.models import Project, ProjectMembership
from apps.tasks.models import Task, TaskDependency
from apps.resources.models import Resource
from apps.assignments.models import Assignment
from apps.baselines.models import Baseline, BaselineTask
from apps.kpis.services import KPICalculator


class Command(BaseCommand):
    help = 'Create a sample project with tasks for testing'

    def add_arguments(self, parser):
        parser.add_argument('--name', type=str, default='Projet Exemple')
        parser.add_argument('--tasks', type=int, default=20)
        parser.add_argument('--username', type=str, default='admin')

    def handle(self, *args, **options):
        name = options['name']
        task_count = options['tasks']
        username = options['username']

        user, _ = User.objects.get_or_create(
            username=username,
            defaults={'is_staff': True, 'is_superuser': True, 'email': f'{username}@example.com'}
        )
        if not user.has_usable_password():
            user.set_password('admin1234')
            user.save()

        start = date.today()
        end = start + timedelta(days=task_count * 3)

        project = Project.objects.create(
            name=name,
            description='Projet de démonstration généré automatiquement.',
            status='active',
            manager=user,
            start_date=start,
            end_date=end,
        )
        ProjectMembership.objects.get_or_create(
            project=project, user=user, defaults={'role': 'pm'}
        )

        # Resources
        res1 = Resource.objects.create(
            project=project, name='Développeur senior', resource_type='work', max_units=100,
        )
        res2 = Resource.objects.create(
            project=project, name='Designer UX', resource_type='work', max_units=100,
        )

        # Summary tasks (phases)
        phases = ['Phase 1 - Analyse', 'Phase 2 - Conception', 'Phase 3 - Développement', 'Phase 4 - Tests']
        created_tasks = []
        order = 0

        tasks_per_phase = max(2, task_count // 4)
        current_start = start
        prev_task = None

        for phase_name in phases:
            summary = Task.objects.create(
                project=project, name=phase_name, is_summary=True,
                planned_start=current_start,
                planned_end=current_start + timedelta(days=tasks_per_phase * 3),
                planned_duration=tasks_per_phase * 3, order=order,
            )
            order += 1

            for i in range(tasks_per_phase):
                dur = random.randint(2, 7)
                t_start = current_start + timedelta(days=i * dur)
                t = Task.objects.create(
                    project=project,
                    parent=summary,
                    name=f'{phase_name} — Tâche {i+1}',
                    planned_start=t_start,
                    planned_end=t_start + timedelta(days=dur),
                    planned_duration=dur,
                    order=order,
                    percent_complete=random.randint(0, 100) if phase_name in phases[:2] else 0,
                )
                order += 1
                created_tasks.append(t)

                if prev_task and random.random() > 0.4:
                    TaskDependency.objects.get_or_create(
                        predecessor=prev_task, successor=t,
                        defaults={'dependency_type': 'FS', 'lag': 0}
                    )

                Assignment.objects.create(
                    task=t, resource=random.choice([res1, res2]),
                    units=100, planned_work=dur * 8,
                )
                prev_task = t

            current_start = current_start + timedelta(days=tasks_per_phase * 3 + 1)

        # Add a milestone
        Task.objects.create(
            project=project,
            name='Livraison finale',
            is_milestone=True,
            planned_start=end,
            planned_end=end,
            planned_duration=0,
            order=order,
        )

        # Create initial baseline
        baseline = Baseline.objects.create(
            project=project,
            name='Baseline 1 - Lancement',
            created_by=user,
            notes='Baseline initiale créée automatiquement.',
            is_active=True,
        )
        leaf_tasks = Task.objects.filter(project=project, is_summary=False)
        bt_list = []
        for task in leaf_tasks:
            bt_list.append(BaselineTask(
                baseline=baseline,
                task=task,
                planned_start=task.planned_start,
                planned_end=task.planned_end,
                planned_duration=task.planned_duration,
                planned_work=task.planned_duration * 8,
                percent_complete=task.percent_complete,
            ))
        BaselineTask.objects.bulk_create(bt_list)

        # Calculate initial KPIs
        kpi = KPICalculator(project, baseline, start).calculate()

        self.stdout.write(self.style.SUCCESS(
            f'Projet "{project.name}" créé avec succès (ID: {project.id}).\n'
            f'Tâches: {len(created_tasks)} | Ressources: 2\n'
            f'Baseline: "{baseline.name}" ({len(bt_list)} tâches)\n'
            f'KPIs: SPI={kpi.spi:.2f}  Avancement={kpi.overall_percent_complete:.1f}%\n'
            f'Accès: http://localhost:8000/projects/{project.id}/'
        ))
