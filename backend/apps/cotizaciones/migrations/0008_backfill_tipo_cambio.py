from django.db import migrations


def noop(apps, schema_editor):
    """
    No-op deliberado. El backfill de tipo_cambio depende de una API externa
    (apis.net.pe/SBS): una migración no debe poder bloquear un deploy por una
    falla de red. El backfill real es idempotente y reintentable:

        python manage.py backfill_tipo_cambio
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('cotizaciones', '0007_cotizacion_tipo_cambio'),
    ]

    operations = [
        migrations.RunPython(noop, noop),
    ]
