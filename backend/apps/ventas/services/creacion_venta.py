"""Creación de ventas — ÚNICO camino de dominio (feat/bot-ventas punto 1).

La web crea ventas así: POST /api/ventas/ → VentaSerializer (valida, crea la
Venta + DetalleVenta y recalcula totales con igv_incluido) → pasos posteriores
que vivían en VentaViewSet.perform_create. Este módulo extrae esos pasos para
que la vista Y el bot usen exactamente lo mismo; no existe una ruta paralela.

Efectos de crear una venta (documentados para el bot):
- Numeración: V-xxxxxxxx por empresa (Venta.save → guardar_con_numero).
- Stock/kárdex: NO se mueven al crear; se descuentan al entrar al estado
  operativo 'entregado' (aplicar_entrega_stock, con guarda estricta: solo
  líneas origen='stock' CON producto — las libres jamás mueven stock).
- CxC: crédito_30/60 → estado 'pendiente', fecha de vencimiento y un PagoVenta
  placeholder 'pendiente' por el total (así aparece en por-cobrar).
- Contado: la web la crea con estado 'pagado' (default del formulario).
- Cachés: listas de ventas y KPIs del dashboard se invalidan.
"""
from types import SimpleNamespace

from django.core.cache import cache
from django.utils import timezone

from apps.ventas.models import PagoVenta


def completar_creacion_venta(usuario, venta, *, entrega_inmediata=False, plazo_dias=None):
    """Pasos post-serializer, idénticos para la web y el bot.

    plazo_dias (solo lo pasa el bot): vencimiento a N días exactos («a 15
    días» → 15) manteniendo el tipo_venta de la web más cercano. La web no lo
    pasa y conserva su comportamiento de siempre (30/60 según el tipo)."""
    if venta.tipo_venta in ('credito_30', 'credito_60'):
        venta.estado = 'pendiente'
        dias_credito = plazo_dias or (30 if venta.tipo_venta == 'credito_30' else 60)
        venta.fecha_vencimiento = venta.fecha_emision + timezone.timedelta(days=dias_credito)
        venta.save()
        PagoVenta.objects.create(
            venta=venta, fecha=venta.fecha_emision, monto=venta.total,
            metodo_pago='pendiente',
            notas=f'Pago pendiente para venta a crédito de {dias_credito} días',
        )

    # §4.4 — el stock no se toca aquí; solo se sincroniza cobrado↔pago
    if venta.estado == 'pagado':
        venta._sincronizar_estado_operativo_pago()

    # B3 — entrega inmediata: nace en 'entregado' (misma guarda estricta)
    if entrega_inmediata and venta.empresa.modo_inventario == 'con_stock':
        venta.cambiar_estado_operativo('entregado', usuario=usuario, nota='Entrega inmediata')

    invalidar_caches_venta(venta.empresa_id)
    return venta


def invalidar_caches_venta(empresa_id):
    cache.delete(f'ventas_list_{empresa_id}')
    cache.delete(f'dashboard_mes_{empresa_id}')
    cache.delete(f'dashboard_historico_{empresa_id}')
    cache.delete(f'dashboard_simple_stats_{empresa_id}')


def crear_venta(usuario, data, *, entrega_inmediata=False, plazo_dias=None):
    """Crea una venta COMPLETA con el mismo serializer y post-pasos de la web.
    Lo usa el bot al confirmar un borrador de venta. Lanza ValidationError de
    DRF si los datos no pasan (el caller la traduce a mensaje)."""
    from apps.ventas.serializers import VentaSerializer

    ser = VentaSerializer(data=data, context={'request': SimpleNamespace(user=usuario)})
    ser.is_valid(raise_exception=True)
    venta = ser.save()
    return completar_creacion_venta(usuario, venta, entrega_inmediata=entrega_inmediata,
                                    plazo_dias=plazo_dias)
