from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('projects', '0002_attachment'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Meeting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('date', models.DateTimeField()),
                ('location', models.CharField(blank=True, max_length=255)),
                ('status', models.CharField(
                    choices=[('planned', 'Planifiée'), ('held', 'Tenue'), ('cancelled', 'Annulée')],
                    default='planned', max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_meetings', to=settings.AUTH_USER_MODEL,
                )),
                ('participants', models.ManyToManyField(
                    blank=True, related_name='project_meetings', to=settings.AUTH_USER_MODEL,
                )),
                ('project', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='meetings', to='projects.project',
                )),
            ],
            options={
                'verbose_name': 'Réunion',
                'verbose_name_plural': 'Réunions',
                'ordering': ['-date'],
            },
        ),
        migrations.CreateModel(
            name='MeetingMinute',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(blank=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('meeting', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='minutes', to='meetings.meeting',
                )),
                ('written_by', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='written_minutes', to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Compte rendu',
                'verbose_name_plural': 'Comptes rendus',
            },
        ),
        migrations.CreateModel(
            name='MeetingDecision',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.TextField()),
                ('due_date', models.DateField(blank=True, null=True)),
                ('status', models.CharField(
                    choices=[('open', 'Ouverte'), ('done', 'Réalisée'), ('cancelled', 'Annulée')],
                    default='open', max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('assigned_to', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='assigned_decisions', to=settings.AUTH_USER_MODEL,
                )),
                ('meeting', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='decisions', to='meetings.meeting',
                )),
            ],
            options={
                'verbose_name': 'Décision',
                'verbose_name_plural': 'Décisions',
                'ordering': ['created_at'],
            },
        ),
    ]
