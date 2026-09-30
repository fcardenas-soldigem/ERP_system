"""
Servicio de conversión de Cotización a Venta (+ generación de Órdenes de Compra).

Centraliza la lógica para mapear campos entre modelos, decidir el origen de cada
línea (stock vs pedido a proveedor) según el modo de inventario de la empresa, y
generar una OC en borrador por proveedor. Operación atómica e idempotente.

NUNCA mueve inventario: las líneas 'stock' solo se RESERVAN (con degradación
segura); el descuento real ocurre en la entrega (Parte 2B).
"""
import logging
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

# D5 — constante global en Fase 1 (configurable por empresa en Fase 2).
N_DIAS_ENTREGA_OC = 7


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
    """
    Conservada por compatibilidad de imports. Desde D1 ya NO se lanza:
    producto y proveedor son opcionales; las líneas sin producto se convierten
    igual como 'pedido_proveedor'.
    """

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
    Conservada por compatibilidad. Devuelve las líneas sin producto vinculado.
    Ya no bloquea la conversión (D1).
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


def _reservas_activas(empresa, producto):
    """Suma de cantidad_reservada del producto (OD-A: descontar reservas ajenas)."""
    from apps.inventario.models.inventario_productos_terminados import InventarioProductosTerminados
    agg = InventarioProductosTerminados.objects.filter(
        empresa=empresa, producto=producto
    ).aggregate(r=Sum('cantidad_reservada'))
    return agg['r'] or Decimal('0')


def _disponible_efectivo(empresa, producto, reservado_local):
    """
    OD-A (ajustada): disponible = stock_total − reservas activas del producto
    − lo ya comprometido en ESTA conversión. Evita sobreventa cuando otra venta
    ya reservó.
    """
    stock_total = Decimal(str(producto.stock_total or 0))
    reservada = _reservas_activas(empresa, producto)
    local = reservado_local.get(producto.id, Decimal('0'))
    return stock_total - reservada - local


def _almacen_para(empresa, producto):
    almacen = getattr(producto, 'almacen', None)
    if almacen:
        return almacen
    return empresa.almacenes.first()


def _decidir_origen(empresa, producto, cantidad, reservado_local):
    """
    Decisión automática de origen (§4.3 + OD-A).

    - empresa sin_stock  -> siempre 'pedido_proveedor'
    - empresa con_stock:
        producto controla stock Y disponible_efectivo >= cantidad -> 'stock'
        (stock insuficiente / no controla stock / sin producto) -> 'pedido_proveedor'
          (la línea completa va a OC; no se divide)
    """
    if empresa.modo_inventario == 'sin_stock':
        return 'pedido_proveedor'

    if (producto is not None
            and getattr(producto, 'controla_stock', True)
            and _disponible_efectivo(empresa, producto, reservado_local) >= cantidad):
        return 'stock'

    return 'pedido_proveedor'


def _reservar_con_degradacion(empresa, producto, cantidad):
    """
    OD-B: intenta reservar; si no hay infra de inventario para el producto,
    degrada de forma segura (no revienta la conversión). La línea sigue siendo
    'stock'; el descuento real se resolverá en la entrega (Parte 2B).
    Devuelve True si se reservó en firme, False si se degradó.
    """
    from apps.inventario.models.inventario_productos_terminados import InventarioProductosTerminados
    almacen = _almacen_para(empresa, producto)
    if almacen is None:
        logger.warning('Reserva degradada: sin almacén para %s', producto.nombre)
        return False
    try:
        InventarioProductosTerminados.reservar_para_venta(
            empresa=empresa, producto=producto, almacen=almacen, cantidad=cantidad
        )
        return True
    except (ValidationError, Exception) as e:  # noqa: BLE001 — degradación explícita
        logger.warning('Reserva degradada para %s: %s', producto.nombre, e)
        return False


@transaction.atomic
def convertir_cotizacion_a_venta(cotizacion, *, marcar_convertida=True):
    """
    Convierte una cotización a una venta y genera OC(s) por proveedor.
    Atómica e idempotente. NUNCA llama actualizar_stock().

    Adjunta `venta.conversion_info` con:
        { reused, ocs_creadas, lineas_stock_reservadas, lineas_sin_proveedor }

    Raises:
        CotizacionNoConvertibleError: estado inválido o sin detalles.
    """
    from apps.ventas.models import Venta, DetalleVenta
    from apps.compras.models import OrdenCompra, OrdenCompraDetalle

    empresa = cotizacion.empresa

    # ── Idempotencia PRIMERO: si ya existe venta (incl. estado 'convertida'),
    # reutilizar sin recrear nada. Debe ir antes de validar_conversion, que
    # rechazaría el estado 'convertida'.
    if cotizacion.venta_id:
        venta = cotizacion.venta
        ocs_existentes = []
        for oc in OrdenCompra.objects.filter(venta=venta):
            ocs_existentes.append({
                'id': oc.id, 'numero': oc.numero,
                'proveedor': oc.proveedor_nombre or (oc.proveedor.razon_social if oc.proveedor_id else ''),
                'lineas': OrdenCompraDetalle.objects.filter(orden=oc).count(),
            })
        venta.conversion_info = {
            'reused': True,
            'ocs_creadas': ocs_existentes,
            'lineas_stock_reservadas': venta.detalles.filter(origen='stock').count(),
            'lineas_sin_proveedor': [],
        }
        logger.info('Cotización %s ya tenía venta %s; reutilizando (idempotente).',
                    cotizacion.numero, venta.numero)
        return venta

    # Validar solo cuando vamos a crear (rechazada / vencida / sin detalles).
    validar_conversion(cotizacion)

    tipo_venta, metodo_pago = _normalizar_forma_pago(cotizacion.forma_pago)
    detalles = list(cotizacion.detalles.all().select_related('producto', 'proveedor'))

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
        empresa=empresa,
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

    reservado_local = defaultdict(lambda: Decimal('0'))
    lineas_stock_reservadas = 0
    pedido_por_proveedor = defaultdict(list)   # proveedor_id -> [detalle_cot]
    lineas_sin_proveedor = []

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

        origen = _decidir_origen(empresa, detalle.producto, cantidad, reservado_local)

        if origen == 'stock':
            # Reserva (con degradación). La línea queda 'stock' aunque degrade.
            _reservar_con_degradacion(empresa, detalle.producto, cantidad)
            reservado_local[detalle.producto.id] += cantidad
            lineas_stock_reservadas += 1
        else:
            # pedido_proveedor: agrupar para OC o avisar si no tiene proveedor.
            if detalle.proveedor_id:
                pedido_por_proveedor[detalle.proveedor_id].append(detalle)
            else:
                lineas_sin_proveedor.append({
                    'detalle_id': detalle.id,
                    'descripcion': detalle.descripcion,
                    'cantidad': str(detalle.cantidad),
                })

        DetalleVenta.objects.create(
            venta=venta,
            producto=detalle.producto,
            descripcion=detalle.descripcion,
            cantidad=cantidad,
            precio_unitario=precio_final,
            origen=origen,
            stock_descontado=False,
        )

    venta.refresh_from_db()
    venta.actualizar_totales()

    # ── Órdenes de Compra: una por proveedor (idempotente por venta+proveedor).
    hoy = timezone.now().date()
    ocs_creadas = []
    for prov_id, lineas in pedido_por_proveedor.items():
        if OrdenCompra.objects.filter(venta=venta, proveedor_id=prov_id).exists():
            continue
        proveedor = lineas[0].proveedor
        oc = OrdenCompra.objects.create(
            empresa=empresa,
            proveedor=proveedor,
            proveedor_nombre=proveedor.razon_social,
            venta=venta,
            cotizacion_origen=cotizacion,
            fecha_emision=hoy,
            fecha_entrega=hoy + timedelta(days=N_DIAS_ENTREGA_OC),
            moneda=cotizacion.moneda,
            estado='borrador',
        )
        for d in lineas:
            costo = d.costo_unitario if d.costo_unitario and d.costo_unitario > 0 else d.precio_unitario
            if not costo or costo <= 0:
                costo = Decimal('0.01')
            OrdenCompraDetalle.objects.create(
                orden=oc,
                producto=d.producto,
                descripcion=d.descripcion,
                cantidad=d.cantidad,
                precio_unitario=costo,
            )
        ocs_creadas.append({
            'id': oc.id, 'numero': oc.numero,
            'proveedor': proveedor.razon_social, 'lineas': len(lineas),
        })

    if marcar_convertida:
        cotizacion.estado = 'convertida'
        cotizacion.venta = venta
        if not cotizacion.fecha_aceptacion:
            cotizacion.fecha_aceptacion = timezone.now().date()
        cotizacion.save(update_fields=['estado', 'venta', 'fecha_aceptacion', 'fecha_modificacion'])

    venta.conversion_info = {
        'reused': False,
        'ocs_creadas': ocs_creadas,
        'lineas_stock_reservadas': lineas_stock_reservadas,
        'lineas_sin_proveedor': lineas_sin_proveedor,
    }

    logger.info(
        'Cotización %s → venta %s (total %s %s): %s OC(s), %s línea(s) stock, %s sin proveedor',
        cotizacion.numero, venta.numero, venta.total, venta.moneda,
        len(ocs_creadas), lineas_stock_reservadas, len(lineas_sin_proveedor),
    )
    return venta
