from django.db import migrations


def backfill(apps, schema_editor):
    from apps.core.services.tipo_cambio import backfill_tipo_cambio
    Cotizacion = apps.get_model('cotizaciones', 'Cotizacion')
    backfill_tipo_cambio(Cotizacion)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('cotizaciones', '0007_cotizacion_tipo_cambio'),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
