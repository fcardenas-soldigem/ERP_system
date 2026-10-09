from django.db import migrations


def noop(apps, schema_editor):
    """
    No-op deliberado. El backfill de tipo_cambio depende de una API externa
    (apis.net.pe/SBS): una migración no debe poder bloquear un deploy por una
    falla de red. El backfill real es idempotente y reintentable:

        python manage.py backfill_tipo_cambio

    (Localmente esta migración ya corrió con la versión anterior; cambiar su
    contenido es seguro porque Django solo registra el nombre.)
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0023_venta_tipo_cambio'),
    ]

    operations = [
        migrations.RunPython(noop, noop),
    ]
