"""
registrar_factura — convierte una OC en Compra al llegar la factura del
proveedor. Reemplaza al viejo convertir_a_compra (deshabilitado, nunca copió
líneas).

Efectos de negocio:
- Nace el crédito fiscal: la Compra entra al IGV del mes (devengo).
- Nace la cuenta por pagar: tipo crédito 30 → estado 'pendiente'.
- La utilidad de la venta vinculada pasa a fuente 'factura' (prioridad 1).

Reglas:
- UNA factura por OC (OneToOne Compra.orden_compra). Reintento → error claro.
- Copia moneda y tipo_cambio de la OC (el TC histórico del documento origen).
- Los totales de la Compra se fijan con los de la OC (sin IGV + 18%), lo que
  cubre también las líneas de texto libre que no pueden ir a CompraDetalle
  (producto es NOT NULL ahí).
"""
import logging

from django.db import transaction

from apps.compras.models import Compra, CompraDetalle, OrdenCompra, OrdenCompraDetalle
from apps.inventario.models.almacen import Almacen

logger = logging.getLogger(__name__)


class FacturaError(Exception):
    """Error de negocio al registrar la factura (mapear a 400)."""


@transaction.atomic
def registrar_factura(oc: OrdenCompra, *, numero_factura: str, fecha_factura,
                      archivo=None) -> Compra:
    if Compra.objects.filter(orden_compra=oc).exists():
        raise FacturaError(
            f'La OC {oc.numero} ya tiene una factura registrada. '
            'Una OC admite una sola factura.'
        )
    if not numero_factura or not str(numero_factura).strip():
        raise FacturaError('numero_factura es obligatorio.')
    if oc.estado in ('borrador', 'rechazada'):
        raise FacturaError(
            f'No se puede facturar una OC en estado "{oc.estado}". Apruébala primero.'
        )
    if oc.proveedor_id is None:
        raise FacturaError('La OC no tiene proveedor asignado.')

    detalles_oc = list(OrdenCompraDetalle.objects.filter(orden=oc))
    if not detalles_oc or not oc.total or oc.total <= 0:
        raise FacturaError('La OC no tiene líneas con montos; nada que facturar.')

    # Almacén: NOT NULL en Compra. En empresas sin_stock es solo un campo
    # administrativo (las líneas pedido_proveedor nunca mueven stock).
    almacen = Almacen.objects.filter(empresa=oc.empresa).first()
    if almacen is None:
        almacen = Almacen.objects.create(
            empresa=oc.empresa, nombre='Almacén Principal', direccion='—',
        )

    compra = Compra.objects.create(
        empresa=oc.empresa,
        proveedor=oc.proveedor,
        almacen=almacen,
        orden_compra=oc,
        fecha_emision=fecha_factura,
        tipo_compra='credito_30',     # factura de proveedor = cuenta por pagar
        moneda=oc.moneda,
        igv_incluido=False,           # líneas de OC son costos SIN IGV
        referencia=str(numero_factura).strip(),
        comprobante=archivo,
        notas=f'Factura de proveedor sobre OC {oc.numero}',
    )

    # Líneas con producto → CompraDetalle (trazabilidad). Las de texto libre
    # no caben (producto NOT NULL): quedan cubiertas por los totales pineados.
    for d in detalles_oc:
        if d.producto_id:
            CompraDetalle.objects.create(
                compra=compra,
                producto=d.producto,
                cantidad=d.cantidad,
                precio_unitario=d.precio_unitario,
            )

    # Pinear moneda/TC/totales exactos de la OC (CompraDetalle.save recalcula;
    # este update final deja los montos = OC aunque haya texto libre).
    Compra.objects.filter(id=compra.id).update(
        tipo_cambio=oc.tipo_cambio,
        subtotal=oc.subtotal, igv=oc.igv, total=oc.total,
    )
    compra.refresh_from_db()

    logger.info('Factura registrada sobre OC %s → Compra %s', oc.numero, compra.numero)
    return compra
