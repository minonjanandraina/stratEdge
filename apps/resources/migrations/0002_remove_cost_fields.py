from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(model_name='resource', name='standard_rate'),
        migrations.RemoveField(model_name='resource', name='overtime_rate'),
        migrations.RemoveField(model_name='resource', name='cost_per_use'),
    ]
