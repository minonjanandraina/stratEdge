from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('discussions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='message_type',
            field=models.CharField(
                choices=[('text', 'Texte'), ('file', 'Fichier')],
                default='text',
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name='message',
            name='content',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='message',
            name='file',
            field=models.FileField(blank=True, null=True, upload_to='discussions/'),
        ),
    ]
