from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0004_folder_parent'),
    ]

    operations = [
        migrations.RemoveField(model_name='project', name='budget'),
        migrations.RemoveField(model_name='project', name='currency'),
    ]
