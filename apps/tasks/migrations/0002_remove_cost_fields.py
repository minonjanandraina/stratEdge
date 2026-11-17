from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(model_name='task', name='fixed_cost'),
        migrations.RemoveField(model_name='task', name='planned_work'),
        migrations.RemoveField(model_name='task', name='actual_work'),
    ]
