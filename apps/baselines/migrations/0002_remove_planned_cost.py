from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('baselines', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(model_name='baselinetask', name='planned_cost'),
    ]
