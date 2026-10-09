from django.db import migrations


def backfill(apps, schema_editor):
    from apps.core.services.tipo_cambio import backfill_tipo_cambio
    for modelo in ('Compra', 'OrdenCompra', 'OrdenServicioCompra'):
        Model = apps.get_model('compras', modelo)
        backfill_tipo_cambio(Model)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0020_compra_tipo_cambio_ordencompra_tipo_cambio_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
