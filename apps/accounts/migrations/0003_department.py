import django.db.models.deletion
from django.db import migrations, models


def create_initial_departments(apps, schema_editor):
    Department = apps.get_model('accounts', 'Department')
    Department.objects.bulk_create([
        Department(name='DFS'),
        Department(name='IT'),
    ])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_emailconfirmation'),
    ]

    operations = [
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Nom')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Département',
                'verbose_name_plural': 'Départements',
                'ordering': ['name'],
            },
        ),
        migrations.RunPython(create_initial_departments, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='userprofile',
            name='department',
        ),
        migrations.AddField(
            model_name='userprofile',
            name='department',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='members',
                to='accounts.department',
                verbose_name='Département',
            ),
        ),
    ]
