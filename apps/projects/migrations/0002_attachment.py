from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import apps.projects.models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0001_initial'),
        ('tasks', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Attachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to=apps.projects.models._attachment_upload_path)),
                ('name', models.CharField(max_length=255)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('size', models.PositiveIntegerField(default=0)),
                ('project', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='attachments',
                    to='projects.project',
                )),
                ('task', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='attachments',
                    to='tasks.task',
                    db_constraint=True,
                )),
                ('uploaded_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='attachments',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Pièce jointe',
                'verbose_name_plural': 'Pièces jointes',
                'ordering': ['-uploaded_at'],
            },
        ),
    ]
