from django.db import migrations


def backfill(apps, schema_editor):
    Venta = apps.get_model('ventas', 'Venta')
    DetalleVenta = apps.get_model('ventas', 'DetalleVenta')

    # #8 — origen de líneas históricas sin valor.
    #   con_stock  -> 'stock'
    #   sin_stock  -> 'pedido_proveedor' (ya hecho en 0018; se re-asegura idempotente)
    DetalleVenta.objects.filter(
        origen__isnull=True, venta__empresa__modo_inventario='con_stock',
    ).update(origen='stock')
    DetalleVenta.objects.filter(
        origen__isnull=True, venta__empresa__modo_inventario='sin_stock',
    ).update(origen='pedido_proveedor')

    # #9 (R7) — toda línea de una venta ya 'pagado' ya descontó con la regla vieja;
    #   marcar stock_descontado=True para que NO vuelva a descontar al entregar.
    DetalleVenta.objects.filter(venta__estado='pagado').update(stock_descontado=True)

    # #10 (H3) — estado_operativo histórico, SIN crear historial:
    #   ventas 'pagado' -> 'cobrado'; el resto queda en el default 'pendiente_compra'.
    Venta.objects.filter(estado='pagado').update(estado_operativo='cobrado')


def reverse_noop(apps, schema_editor):
    # No se puede re-derivar el estado previo con seguridad.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0020_venta_estado_operativo_and_more'),
        ('empresas', '0007_soldigem_sin_stock'),
    ]

    operations = [
        migrations.RunPython(backfill, reverse_noop),
        # Prod-safety (igual que 0019): Django dropea el DEFAULT tras AddField;
        # lo restauramos para que el código viejo pueda INSERTar sin esta columna.
        migrations.RunSQL(
            sql="ALTER TABLE ventas_venta ALTER COLUMN estado_operativo SET DEFAULT 'pendiente_compra';",
            reverse_sql="ALTER TABLE ventas_venta ALTER COLUMN estado_operativo DROP DEFAULT;",
        ),
    ]
