from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0003_add_tasknote_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='critical_override',
            field=models.BooleanField(
                blank=True, null=True,
                help_text="None = automatique (CPM), True = forcée critique, False = forcée non critique",
            ),
        ),
    ]
