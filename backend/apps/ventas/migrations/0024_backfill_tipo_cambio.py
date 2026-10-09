from django.db import migrations


def backfill(apps, schema_editor):
    from apps.core.services.tipo_cambio import backfill_tipo_cambio
    Venta = apps.get_model('ventas', 'Venta')
    backfill_tipo_cambio(Venta)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0023_venta_tipo_cambio'),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
