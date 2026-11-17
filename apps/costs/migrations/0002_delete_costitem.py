from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('costs', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(name='CostItem'),
    ]
