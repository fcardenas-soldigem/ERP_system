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
        ('compras', '0020_compra_tipo_cambio_ordencompra_tipo_cambio_and_more'),
    ]

    operations = [
        migrations.RunPython(noop, noop),
    ]
