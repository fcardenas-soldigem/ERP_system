from django.db import migrations

# H1 — Backfill de DetalleVenta.origen para líneas históricas.
# Regla: líneas de ventas de empresas 'sin_stock' -> 'pedido_proveedor'.
# Las líneas de empresas 'con_stock' (y legacy) quedan en NULL, que la regla
# defensiva (Venta._debe_saltar_stock) trata como movible (fail-open), sin
# cambiar el comportamiento actual.


def backfill_origen(apps, schema_editor):
    DetalleVenta = apps.get_model('ventas', 'DetalleVenta')
    DetalleVenta.objects.filter(
        venta__empresa__modo_inventario='sin_stock'
    ).update(origen='pedido_proveedor')


def revert(apps, schema_editor):
    # No re-derivable con seguridad: el estado previo era NULL. No-op.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0017_detalleventa_descripcion_detalleventa_origen_and_more'),
        ('empresas', '0007_soldigem_sin_stock'),
    ]

    operations = [
        migrations.RunPython(backfill_origen, revert),
    ]
