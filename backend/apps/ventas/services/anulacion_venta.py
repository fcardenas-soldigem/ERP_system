"""Anulación de ventas — ÚNICO camino de dominio (fix/anular-venta).

ANULAR ≠ ELIMINAR: la venta conserva su número (los correlativos nunca se
reutilizan) y queda con estado='anulado', anulado_por, anulado_en y motivo.

Reglas:
- Motivo obligatorio; anular dos veces → error «ya está anulada».
- Pagos REALES registrados → bloquea: «Primero revierte los pagos» (la
  reversión existe: DELETE /api/ventas/{id}/pagos/{pago_id}/).
- Placeholder 'pendiente' de crédito → se marca anulado (no se borra).
- Stock: cada línea con stock_descontado (entregada) se reintegra al
  inventario y deja un movimiento 'devolucion_venta' en el kárdex; el
  movimiento original NUNCA se borra. Movimientos legados 'salida_venta' de
  esta venta también se revierten. Las líneas libres no se tocan.
- Guías de remisión (vinculadas por texto: «…desde Venta V-xxx»): en borrador
  se cancelan en cascada; emitidas/en proceso/entregadas BLOQUEAN (ya son un
  documento de traslado en circulación; se cancelan en su módulo).
- Cotización de origen: vuelve a 'aceptada' y se desliga de la venta, para
  poder convertirla de nuevo (la conversión es idempotente por venta_id: con
  el vínculo intacto devolvería la venta ANULADA). La traza queda en la venta
  anulada (referencia = número de la cotización).
- OCs vinculadas: no se tocan (son compromisos con proveedores); se avisan.
- Cachés de listas y KPIs se invalidan.
"""
import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class AnulacionNoPermitida(Exception):
    """Regla de negocio que impide anular (→ 400 con este mensaje)."""


def _guias_de(venta):
    from apps.guias.models import GuiaRemision
    return (GuiaRemision.objects
            .filter(empresa=venta.empresa, tipo='venta',
                    observaciones__contains=f'Venta {venta.numero}')
            .exclude(estado='cancelada'))


def _movimiento_reversa(venta, producto, almacen, cantidad, costo_unitario, usuario, origen):
    """Entrada 'devolucion_venta' en el kárdex (mismo cálculo de saldo que
    MovimientoInventario.registrar_entrada, que fija tipo 'entrada')."""
    from apps.inventario.models.movimiento_inventario import MovimientoInventario
    ultimo = MovimientoInventario.objects.filter(
        empresa=venta.empresa, producto=producto, almacen=almacen).first()
    saldo_ant = ultimo.cantidad_saldo if ultimo else Decimal('0')
    costo_saldo_ant = ultimo.costo_saldo if ultimo else Decimal('0')
    costo_total = Decimal(cantidad) * Decimal(costo_unitario or 0)
    nuevo_saldo = saldo_ant + Decimal(cantidad)
    nuevo_costo = costo_saldo_ant + costo_total
    MovimientoInventario.objects.create(
        empresa=venta.empresa, producto=producto, almacen=almacen,
        fecha=timezone.now(),
        tipo_movimiento='devolucion_venta', tipo_documento='devolucion_venta',
        tipo_inventario='producto_terminado' if producto.tipo_producto == 'FINISHED' else 'general',
        numero_documento=venta.numero,
        cantidad_entrada=cantidad, cantidad_saldo=nuevo_saldo,
        costo_unitario=costo_unitario or 0, costo_total_entrada=costo_total,
        costo_saldo=nuevo_costo,
        costo_promedio=(nuevo_costo / nuevo_saldo) if nuevo_saldo > 0 else Decimal('0'),
        inventario_anterior=saldo_ant, inventario_actual=nuevo_saldo,
        venta_id=venta.id,
        observaciones=f'Reversa por anulación de {venta.numero} ({origen})',
        created_by=getattr(usuario, 'email', '') or '',
    )


def _revertir_stock(venta, usuario):
    """→ número de líneas revertidas. Nunca borra movimientos."""
    from apps.inventario.models.inventario_productos_terminados import InventarioProductosTerminados
    from apps.inventario.models.movimiento_inventario import MovimientoInventario

    revertidos = set()
    n = 0
    # 1) líneas entregadas (§4.4): stock_descontado → reintegro + kárdex
    for detalle in venta.detalles.select_related('producto').all():
        if not detalle.stock_descontado or detalle.producto_id is None:
            continue   # líneas libres y no entregadas: nada que revertir
        producto = detalle.producto
        almacen = producto.almacen or venta.empresa.almacenes.first()
        costo = Decimal('0')
        if almacen:
            inv = (InventarioProductosTerminados.objects.select_for_update()
                   .filter(empresa=venta.empresa, producto=producto, almacen=almacen).first())
            if inv:
                inv.cantidad_disponible += detalle.cantidad
                inv.save()
                costo = inv.costo_produccion_unitario or Decimal('0')
            _movimiento_reversa(venta, producto, almacen, detalle.cantidad, costo, usuario, 'entrega')
        detalle.stock_descontado = False
        detalle.save(update_fields=['stock_descontado'])
        producto.actualizar_stock_total()
        revertidos.add(producto.id)
        n += 1

    # 2) kárdex legado ('salida_venta' del camino viejo actualizar_stock)
    for mov in MovimientoInventario.objects.filter(
            empresa=venta.empresa, venta_id=venta.id, tipo_movimiento='salida_venta'):
        if mov.producto_id in revertidos:
            continue
        from apps.inventario.models.stock import Stock
        stock, _ = Stock.objects.get_or_create(
            producto=mov.producto, empresa=venta.empresa, almacen=mov.almacen,
            defaults={'cantidad': 0})
        stock.cantidad += mov.cantidad_salida
        stock.save()
        _movimiento_reversa(venta, mov.producto, mov.almacen, mov.cantidad_salida,
                            mov.costo_unitario, usuario, 'salida legada')
        mov.producto.actualizar_stock_total()
        revertidos.add(mov.producto_id)
        n += 1
    return n


def anular_venta(venta, usuario, motivo):
    """→ (venta, avisos). Lanza AnulacionNoPermitida con el motivo en español."""
    from apps.compras.models import OrdenCompra
    from apps.cotizaciones.models import Cotizacion
    from apps.ventas.models import Venta
    from apps.ventas.services.creacion_venta import invalidar_caches_venta

    motivo = (motivo or '').strip()
    if not motivo:
        raise AnulacionNoPermitida('El motivo de anulación es obligatorio.')

    avisos = []
    with transaction.atomic():
        v = Venta.objects.select_for_update().get(pk=venta.pk)
        if v.estado == 'anulado':
            raise AnulacionNoPermitida(f'La venta {v.numero} ya está anulada.')

        pagos_reales = v.pagos.exclude(metodo_pago='pendiente').filter(anulado=False)
        if pagos_reales.exists():
            total = sum((p.monto for p in pagos_reales), Decimal('0'))
            raise AnulacionNoPermitida(
                f'La venta {v.numero} tiene {pagos_reales.count()} pago(s) registrado(s) '
                f'por {total:,.2f}. Primero revierte los pagos.')

        guias = list(_guias_de(v))
        emitidas = [g for g in guias if g.estado != 'borrador']
        if emitidas:
            numeros = ', '.join(g.numero or f'#{g.id}' for g in emitidas)
            raise AnulacionNoPermitida(
                f'La venta {v.numero} tiene guía(s) de remisión emitidas ({numeros}). '
                'Cancélalas primero en Guías de remisión.')
        for g in guias:   # solo borradores: cascada
            g.estado = 'cancelada'
            g.save(update_fields=['estado'])
            avisos.append(f'Guía en borrador {g.numero or g.id} cancelada.')

        if _revertir_stock(v, usuario):
            avisos.append('Stock reintegrado con su reversa en el kárdex.')

        placeholders = v.pagos.filter(metodo_pago='pendiente', anulado=False)
        for p in placeholders:
            p.anulado = True
            p.notas = (p.notas + '\n' if p.notas else '') + f'Anulado con la venta: {motivo}'
            p.save(update_fields=['anulado', 'notas'])

        for cot in Cotizacion.objects.filter(venta=v, empresa=v.empresa):
            cot.estado = 'aceptada'
            cot.venta = None
            cot.save(update_fields=['estado', 'venta', 'fecha_modificacion'])
            avisos.append(f'La cotización {cot.numero} volvió a «aceptada»: puedes convertirla de nuevo.')

        ocs = list(OrdenCompra.objects.filter(venta=v).values_list('numero', 'estado'))
        if ocs:
            avisos.append('Órdenes de compra vinculadas (no se tocan; revísalas): '
                          + ', '.join(f'{n} ({e})' for n, e in ocs))

        # update(): sin pasar por save() (que recalcula TC/numeración)
        ahora = timezone.now()
        Venta.objects.filter(pk=v.pk).update(
            estado='anulado', anulado_por=usuario if getattr(usuario, 'pk', None) else None,
            anulado_en=ahora, motivo_anulacion=motivo[:2000])
        v.refresh_from_db()

    invalidar_caches_venta(v.empresa_id)
    logger.info('venta %s anulada por %s', v.numero, getattr(usuario, 'pk', None))
    return v, avisos
