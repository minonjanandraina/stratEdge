from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0003_folder_attachment_folder'),
    ]

    operations = [
        migrations.AddField(
            model_name='folder',
            name='parent',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='children', to='projects.folder',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='folder',
            unique_together=set(),
        ),
    ]
