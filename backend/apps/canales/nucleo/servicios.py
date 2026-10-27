"""
Servicios del núcleo (B5): entrada pydantic, salida dict compacta (va directa
al mensaje del bot). TODOS acotados a `usuario.empresa` por el servidor.

Los que ESCRIBEN no escriben: devuelven la propuesta con la que el orquestador
crea un BorradorAgente. El documento real solo nace en confirmar_borrador().
"""
import logging
from decimal import Decimal
from types import SimpleNamespace

from django.db.models import Q
from django.utils import timezone
import datetime as _dt

from apps.ventas.models import Cliente, Venta
from apps.inventario.models.producto import Producto

from . import esquemas as E

logger = logging.getLogger(__name__)


def _num(n):
    return f'{Decimal(n):,.2f}'


def _simbolo(moneda):
    return 'S/' if (moneda or 'PEN') == 'PEN' else '$'


# ── búsquedas ─────────────────────────────────────────────────────────────────

def buscar_cliente(usuario, entrada: E.BuscarCliente):
    q = entrada.query.strip()
    qs = Cliente.objects.filter(empresa=usuario.empresa).filter(
        Q(nombre__icontains=q) | Q(documento__icontains=q)
    )[:5]
    return {
        'clientes': [
            {'id': c.id, 'nombre': c.nombre, 'documento': c.documento, 'telefono': c.telefono or ''}
            for c in qs
        ],
    }


def buscar_producto(usuario, entrada: E.BuscarProducto):
    """Fuzzy simple y robusto: cada palabra debe aparecer en nombre o SKU
    («jabra 750» encuentra «Auricular Jabra Evolve2 750»)."""
    qs = Producto.objects.filter(empresa=usuario.empresa, is_active=True)
    for palabra in entrada.query.split():
        qs = qs.filter(Q(nombre__icontains=palabra) | Q(sku__icontains=palabra))
    return {
        'productos': [
            {
                'id': p.id, 'sku': p.sku, 'nombre': p.nombre,
                'precio_venta': str(p.precio_venta), 'stock': str(getattr(p, 'stock_total', '') or ''),
            }
            for p in qs[:5]
        ],
    }


def _resolver_venta(usuario, venta_id=None, venta_numero=None, cliente_query=None, extra_filtro=None):
    qs = Venta.objects.filter(empresa=usuario.empresa).exclude(estado='anulado')
    if extra_filtro:
        qs = qs.filter(**extra_filtro)
    if venta_id:
        return qs.filter(pk=venta_id).first(), None
    if venta_numero:
        return qs.filter(numero__iexact=venta_numero.strip()).first(), None
    if cliente_query:
        candidatas = list(qs.filter(cliente__nombre__icontains=cliente_query.strip()).order_by('-fecha_emision')[:3])
        if len(candidatas) == 1:
            return candidatas[0], None
        if candidatas:
            return None, [{'id': v.id, 'numero': v.numero, 'cliente': v.cliente.nombre, 'total': str(v.total)} for v in candidatas]
    return None, None


# ── consultas ────────────────────────────────────────────────────────────────

def consultar_venta(usuario, entrada: E.ConsultarVenta):
    venta, candidatas = _resolver_venta(
        usuario, venta_numero=entrada.venta_numero, cliente_query=entrada.cliente_query,
    )
    if candidatas:
        return {'ambiguo': True, 'candidatas': candidatas}
    if not venta:
        return {'error': 'No encontré esa venta.'}
    saldo = venta.get_saldo_pendiente() if hasattr(venta, 'get_saldo_pendiente') else venta.total - venta.pagos_total
    return {
        'numero': venta.numero,
        'cliente': venta.cliente.nombre,
        'total': str(venta.total),
        'moneda': venta.moneda,
        'estado_pago': venta.estado,
        'cobrado': str(venta.pagos_total),
        'saldo': str(saldo),
        'estado_operativo': venta.get_estado_operativo_display(),
    }


def consultar_stock(usuario, entrada: E.ConsultarStock):
    res = buscar_producto(usuario, E.BuscarProducto(query=entrada.query))
    if not res['productos']:
        return {'error': 'No encontré ese producto.'}
    return {'stock': res['productos']}


def ventas_detenidas(usuario, entrada: E.VentasDetenidas):
    """Ventas con SLA operativo vencido, CON motivo (lo que la review móvil
    encontró imposible de responder en el teléfono)."""
    detenidas = []
    qs = Venta.objects.filter(empresa=usuario.empresa).exclude(
        estado='anulado').exclude(estado_operativo='cobrado').order_by('-fecha_emision')[:100]
    for v in qs:
        if v.estado_sla_operativo == 'vencido':
            detenidas.append({
                'numero': v.numero,
                'cliente': v.cliente.nombre,
                'total': f'{_simbolo(v.moneda)} {_num(v.total)}',
                'motivo': f'{v.get_estado_operativo_display()} hace {v.dias_en_estado_operativo} días '
                          f'(límite {Venta.SLA_OPERATIVO_DIAS.get(v.estado_operativo, "?")})',
            })
    return {'detenidas': detenidas[:10], 'total': len(detenidas)}


# ── preparaciones (generan borrador; NUNCA escriben) ─────────────────────────

def preparar_cotizacion(usuario, entrada: E.PrepararCotizacion):
    cliente = None
    if entrada.cliente_id:
        cliente = Cliente.objects.filter(empresa=usuario.empresa, pk=entrada.cliente_id).first()
    elif entrada.cliente_query:
        res = buscar_cliente(usuario, E.BuscarCliente(query=entrada.cliente_query))['clientes']
        if len(res) == 1:
            cliente = Cliente.objects.get(pk=res[0]['id'], empresa=usuario.empresa)
        elif res:
            return {'ambiguo': True, 'clientes': res}
    if not cliente:
        return {'error': 'No ubico al cliente. Dime su nombre o RUC.'}

    items, faltantes = [], []
    for it in entrada.items:
        item = {'cantidad': str(it.cantidad)}
        if it.producto_id:
            p = Producto.objects.filter(empresa=usuario.empresa, pk=it.producto_id).first()
            if not p:
                faltantes.append(str(it.producto_id))
                continue
            item.update(producto=p.id, descripcion=it.descripcion or p.nombre,
                        precio_unitario=str(it.precio_unitario if it.precio_unitario is not None else p.precio_venta))
        else:
            item.update(descripcion=it.descripcion, precio_unitario=str(it.precio_unitario or 0))
        items.append(item)
    if faltantes or not items:
        return {'error': f'No encontré los productos: {", ".join(faltantes)}' if faltantes else 'Sin ítems válidos.'}

    total_aprox = sum(Decimal(i['precio_unitario']) * Decimal(i['cantidad']) for i in items)
    return {
        'borrador': {
            'tipo': 'cotizacion',
            'payload': {
                'cliente': cliente.id,
                'asunto': entrada.asunto or f'Cotización para {cliente.nombre}',
                'moneda': entrada.moneda,
                # 15 días de vigencia: el valor por defecto del negocio
                'fecha_vencimiento': (timezone.localdate() + _dt.timedelta(days=15)).isoformat(),
                'detalles': items,
            },
            'resumen': (
                f'📝 <b>Cotización</b> para <b>{cliente.nombre}</b>\n'
                + '\n'.join(f'  • {i["descripcion"]} ×{Decimal(i["cantidad"]):g} '
                            f'a {_simbolo(entrada.moneda)} {_num(i["precio_unitario"])}' for i in items)
                + f'\nSubtotal aprox.: {_simbolo(entrada.moneda)} {_num(total_aprox)} + IGV'
            ),
        },
    }


def preparar_cobro(usuario, entrada: E.PrepararCobro):
    venta, candidatas = _resolver_venta(
        usuario, venta_id=entrada.venta_id, venta_numero=entrada.venta_numero,
        cliente_query=entrada.cliente_query, extra_filtro={'estado': 'pendiente'},
    )
    if candidatas:
        return {'ambiguo': True, 'candidatas': candidatas}
    if not venta:
        return {'error': 'No encontré una venta pendiente que coincida.'}
    saldo = venta.get_saldo_pendiente() if hasattr(venta, 'get_saldo_pendiente') else venta.total - venta.pagos_total
    saldo = Decimal(saldo)
    # hereda la moneda de la venta y precarga el saldo (QW4, ahora en el bot)
    monto = entrada.monto if entrada.monto is not None else saldo
    if monto > saldo:
        return {'error': f'El monto supera el saldo pendiente ({_simbolo(venta.moneda)} {_num(saldo)}).'}
    return {
        'borrador': {
            'tipo': 'cobro',
            'payload': {
                'venta': venta.id,
                'venta_numero': venta.numero,
                'monto': str(monto),
                'metodo_pago': entrada.metodo_pago,
                'fecha': timezone.localdate().isoformat(),
            },
            'resumen': (
                f'💰 <b>Cobro</b> de <b>{_simbolo(venta.moneda)} {_num(monto)}</b> '
                f'({entrada.metodo_pago}) a {venta.cliente.nombre}\n'
                f'Venta {venta.numero} · saldo actual {_simbolo(venta.moneda)} {_num(saldo)}'
            ),
        },
    }


def cambiar_estado_operativo(usuario, entrada: E.CambiarEstadoOperativo):
    venta, candidatas = _resolver_venta(
        usuario, venta_id=entrada.venta_id, venta_numero=entrada.venta_numero,
    )
    if candidatas:
        return {'ambiguo': True, 'candidatas': candidatas}
    if not venta:
        return {'error': 'No encontré esa venta.'}
    if venta.estado_operativo == entrada.nuevo_estado:
        return {'error': f'La venta {venta.numero} ya está en {venta.get_estado_operativo_display()}.'}
    # el modelo permite saltar estados (p. ej. directo a 'entregado'); solo
    # 'cobrado' está vetado como destino manual
    if entrada.nuevo_estado == 'cobrado':
        return {'error': 'El estado "cobrado" lo pone el sistema al registrar el cobro.'}
    return {
        'borrador': {
            'tipo': 'estado_operativo',
            'payload': {
                'venta': venta.id,
                'venta_numero': venta.numero,
                'desde': venta.estado_operativo,
                'nuevo_estado': entrada.nuevo_estado,
            },
            'resumen': (
                f'🚚 Venta <b>{venta.numero}</b> ({venta.cliente.nombre}): '
                f'{venta.get_estado_operativo_display()} → '
                f'<b>{dict(Venta.ESTADO_OPERATIVO_CHOICES)[entrada.nuevo_estado]}</b>'
            ),
        },
    }


# ── confirmación: el ÚNICO lugar donde el bot escribe en el ERP ──────────────

def confirmar_borrador(borrador):
    """Crea el documento real usando los serializers/modelos existentes.
    Devuelve dict con lo necesario para el mensaje de éxito."""
    usuario = borrador.usuario
    contexto = {'request': SimpleNamespace(user=usuario)}

    if borrador.tipo == 'cotizacion':
        from apps.cotizaciones.serializers import CotizacionSerializer
        # empresa y usuario_creador los fija el SERVIDOR (nunca el payload del chat)
        data = {**borrador.payload, 'empresa': usuario.empresa_id, 'usuario_creador': usuario.id}
        ser = CotizacionSerializer(data=data, context=contexto)
        ser.is_valid(raise_exception=True)
        cot = ser.save(empresa=usuario.empresa, usuario_creador=usuario)
        return {'documento_id': cot.id, 'numero': cot.numero, 'tipo': 'cotizacion'}

    if borrador.tipo == 'cobro':
        from apps.ventas.models import PagoVenta
        venta = Venta.objects.get(pk=borrador.payload['venta'], empresa=usuario.empresa)
        saldo = Decimal(venta.get_saldo_pendiente() if hasattr(venta, 'get_saldo_pendiente') else venta.total - venta.pagos_total)
        monto = Decimal(borrador.payload['monto'])
        if monto > saldo:
            raise ValueError(f'El saldo cambió: ahora es {saldo}.')
        pago = PagoVenta.objects.create(
            venta=venta, monto=monto,
            metodo_pago=borrador.payload['metodo_pago'],
            # el payload viaja como JSON: la fecha vuelve a date para clean()
            fecha=_dt.date.fromisoformat(borrador.payload['fecha']),
            notas=f'Registrado por {borrador.canal} (agente)',
        )
        venta.refresh_from_db()
        return {'documento_id': pago.id, 'numero': venta.numero, 'tipo': 'cobro',
                'saldo_restante': str(venta.total - venta.pagos_total)}

    if borrador.tipo == 'estado_operativo':
        venta = Venta.objects.get(pk=borrador.payload['venta'], empresa=usuario.empresa)
        venta.cambiar_estado_operativo(
            borrador.payload['nuevo_estado'], usuario=usuario,
            nota=f'Vía {borrador.canal} (agente)',
        )
        return {'documento_id': venta.id, 'numero': venta.numero, 'tipo': 'estado_operativo',
                'estado': venta.get_estado_operativo_display()}

    raise ValueError(f'Tipo de borrador desconocido: {borrador.tipo}')
