from decimal import Decimal

from django.db import migrations


def backfill(apps, schema_editor):
    """
    OCs creadas mientras actualizar_totales() era un pass quedaron con
    subtotal/total = 0.00 aunque sus líneas tienen montos. Recalcular desde
    las líneas (costos SIN IGV). Idempotente: solo toca OCs en 0 con líneas.
    Sin red — seguro en deploy.
    """
    # Modelos REALES, no históricos: OrdenCompraDetalle es managed=False (R4)
    # y su estado histórico en Django está recortado (sin FK 'orden').
    from apps.compras.models import OrdenCompra, OrdenCompraDetalle

    for oc in OrdenCompra.objects.filter(subtotal=0):
        bruto = sum(
            (Decimal(str(d.cantidad or 0)) * Decimal(str(d.precio_unitario or 0)))
            for d in OrdenCompraDetalle.objects.filter(orden=oc)
        )
        if bruto <= 0:
            continue
        subtotal = Decimal(str(bruto)).quantize(Decimal('0.01'))
        igv = (subtotal * Decimal('0.18')).quantize(Decimal('0.01'))
        OrdenCompra.objects.filter(id=oc.id).update(
            subtotal=subtotal, igv=igv, total=subtotal + igv,
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0022_compra_orden_compra'),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
