from django.db import migrations, models, connection


def add_spi_if_not_exists(apps, schema_editor):
    columns = [col.name for col in connection.introspection.get_table_description(
        schema_editor.connection.cursor(), 'kpis_projectkpi'
    )]
    if 'spi' not in columns:
        schema_editor.execute(
            "ALTER TABLE kpis_projectkpi ADD COLUMN spi numeric(8,4) NOT NULL DEFAULT 1"
        )
    if 'sv' not in columns:
        schema_editor.execute(
            "ALTER TABLE kpis_projectkpi ADD COLUMN sv numeric(15,2) NOT NULL DEFAULT 0"
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('kpis', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(model_name='projectkpi', name='bcws'),
        migrations.RemoveField(model_name='projectkpi', name='bcwp'),
        migrations.RemoveField(model_name='projectkpi', name='acwp'),
        migrations.RemoveField(model_name='projectkpi', name='cv'),
        migrations.RemoveField(model_name='projectkpi', name='cpi'),
        migrations.RemoveField(model_name='projectkpi', name='bac'),
        migrations.RemoveField(model_name='projectkpi', name='eac'),
        migrations.RemoveField(model_name='projectkpi', name='etc'),
        migrations.RemoveField(model_name='projectkpi', name='vac'),
        migrations.RemoveField(model_name='projectkpi', name='cost_health'),
        migrations.RunPython(add_spi_if_not_exists, noop),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='projectkpi',
                    name='spi',
                    field=models.DecimalField(max_digits=8, decimal_places=4, default=1),
                ),
                migrations.AddField(
                    model_name='projectkpi',
                    name='sv',
                    field=models.DecimalField(max_digits=15, decimal_places=2, default=0),
                ),
            ],
            database_operations=[],
        ),
    ]
