from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('assignments', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(model_name='assignment', name='planned_cost'),
        migrations.RemoveField(model_name='assignment', name='actual_cost'),
        migrations.RemoveField(model_name='assignment', name='overtime_work'),
    ]
