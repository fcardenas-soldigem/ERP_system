"""
Servicio de conversión de Cotización a Venta.

Centraliza la lógica para mapear correctamente los campos entre ambos modelos
y manejar las diferencias de esquema (descuentos, IGV, líneas de servicio, etc).
"""
import logging
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


def _normalizar_forma_pago(forma_pago_texto):
    """
    Convierte el texto libre de forma_pago a un par (tipo_venta, metodo_pago).
    Soporta variantes como "Contado", "CREDITO 30 DIAS", "crédito_60", etc.
    """
    if not forma_pago_texto:
        return ('contado', 'efectivo')

    key = forma_pago_texto.strip().lower()
    key = key.replace('é', 'e').replace('á', 'a').replace('í', 'i')

    if 'credito' in key:
        if '60' in key:
            return ('credito_60', None)
        return ('credito_30', None)

    mapping = {
        'contado': ('contado', 'efectivo'),
        'efectivo': ('contado', 'efectivo'),
        'transferencia': ('contado', 'transferencia'),
        'tarjeta': ('contado', 'tarjeta'),
        'cheque': ('contado', 'cheque'),
    }
    return mapping.get(key, ('contado', 'efectivo'))


def _cuantizar(valor):
    return Decimal(str(valor)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class CotizacionNoConvertibleError(ValidationError):
    pass


class ProductosFaltantesError(Exception):
    """Raised when detalle lines lack a linked product."""

    def __init__(self, productos_faltantes):
        self.productos_faltantes = productos_faltantes
        super().__init__(f'{len(productos_faltantes)} producto(s) sin registrar en inventario.')


def validar_conversion(cotizacion):
    if cotizacion.estado == 'convertida':
        raise CotizacionNoConvertibleError(
            'Esta cotización ya fue convertida a venta.'
        )
    if cotizacion.estado == 'rechazada':
        raise CotizacionNoConvertibleError(
            'No se puede convertir una cotización rechazada.'
        )
    if cotizacion.estado == 'vencida':
        raise CotizacionNoConvertibleError(
            'No se puede convertir una cotización vencida.'
        )
    if not cotizacion.detalles.exists():
        raise CotizacionNoConvertibleError(
            'La cotización no tiene líneas de detalle.'
        )
    return True


def detectar_productos_faltantes(cotizacion):
    """
    Returns a list of dicts describing detalle lines that have no linked producto.
    If the list is empty, all lines are ready for conversion.
    """
    faltantes = []
    for detalle in cotizacion.detalles.all():
        if detalle.producto_id is None:
            faltantes.append({
                'detalle_id': detalle.id,
                'descripcion': detalle.descripcion,
                'codigo': detalle.codigo or '',
                'cantidad': str(detalle.cantidad),
                'precio_unitario': str(detalle.precio_unitario),
            })
    return faltantes


@transaction.atomic
def convertir_cotizacion_a_venta(cotizacion, *, marcar_convertida=True):
    """
    Convierte una cotización a una venta. Operación atómica.

    Raises:
        CotizacionNoConvertibleError: estado inválido o sin detalles.
        ProductosFaltantesError: si alguna línea no tiene producto asociado.
    """
    from apps.ventas.models import Venta, DetalleVenta

    validar_conversion(cotizacion)

    if cotizacion.venta_id:
        logger.info(
            'Cotización %s ya tiene venta enlazada (%s); reutilizando.',
            cotizacion.numero, cotizacion.venta_id,
        )
        return cotizacion.venta

    faltantes = detectar_productos_faltantes(cotizacion)
    if faltantes:
        raise ProductosFaltantesError(faltantes)

    tipo_venta, metodo_pago = _normalizar_forma_pago(cotizacion.forma_pago)

    detalles = list(cotizacion.detalles.all().select_related('producto'))

    if cotizacion.precios_incluyen_igv:
        igv_incluido = True
    elif cotizacion.incluye_igv:
        igv_incluido = False
    else:
        igv_incluido = True

    notas_parts = [f'Generada desde cotización {cotizacion.numero}']
    if cotizacion.notas:
        notas_parts.append(cotizacion.notas)

    venta = Venta.objects.create(
        empresa=cotizacion.empresa,
        cliente=cotizacion.cliente,
        fecha_emision=timezone.now().date(),
        estado='pendiente',
        tipo_venta=tipo_venta,
        metodo_pago=metodo_pago,
        moneda=cotizacion.moneda,
        igv_incluido=igv_incluido,
        notas='\n'.join(notas_parts),
        referencia=cotizacion.numero,
    )

    subtotal_lineas = sum(
        (d.cantidad * d.precio_unitario - (d.descuento_item or 0)) for d in detalles
    ) or Decimal('0.01')

    descuento_global = Decimal(str(cotizacion.descuento or 0))
    factor_descuento = (
        (subtotal_lineas - descuento_global) / subtotal_lineas
        if descuento_global > 0 and subtotal_lineas > 0
        else Decimal('1')
    )

    for detalle in detalles:
        cantidad = Decimal(str(detalle.cantidad))
        precio_bruto = Decimal(str(detalle.precio_unitario))
        descuento_item = Decimal(str(detalle.descuento_item or 0))

        if cantidad > 0:
            precio_neto = (precio_bruto * cantidad - descuento_item) / cantidad
        else:
            precio_neto = precio_bruto

        precio_final = _cuantizar(precio_neto * factor_descuento)
        if precio_final <= 0:
            precio_final = Decimal('0.01')

        DetalleVenta.objects.create(
            venta=venta,
            producto=detalle.producto,
            cantidad=cantidad,
            precio_unitario=precio_final,
        )

    venta.refresh_from_db()
    venta.actualizar_totales()

    if marcar_convertida:
        cotizacion.estado = 'convertida'
        cotizacion.venta = venta
        if not cotizacion.fecha_aceptacion:
            cotizacion.fecha_aceptacion = timezone.now().date()
        cotizacion.save(update_fields=['estado', 'venta', 'fecha_aceptacion', 'fecha_modificacion'])

    logger.info(
        'Cotización %s convertida a venta %s (total %s %s)',
        cotizacion.numero, venta.numero, venta.total, venta.moneda,
    )
    return venta
