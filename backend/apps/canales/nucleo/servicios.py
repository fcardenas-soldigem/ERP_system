"""
Servicios del núcleo (B5): entrada pydantic, salida dict compacta (va directa
al mensaje del bot). TODOS acotados a `usuario.empresa` por el servidor.

Los que ESCRIBEN no escriben: devuelven la propuesta con la que el orquestador
crea un BorradorAgente. El documento real solo nace en confirmar_borrador().
"""
import logging
import re
from decimal import Decimal, ROUND_HALF_UP
from types import SimpleNamespace

from django.db.models import F, Q
from django.utils import timezone
from django.utils.html import escape
import datetime as _dt

from apps.ventas.models import Cliente, Venta
from apps.inventario.models.producto import Producto

from . import busqueda
from . import esquemas as E

logger = logging.getLogger(__name__)

IGV = Decimal('1.18')


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


def _ultimas_compras(empresa, ids):
    """{producto_id: (costo, proveedor)} de la última compra NO borrador ni
    anulada; una sola consulta para todos los ids."""
    from apps.compras.models import CompraDetalle
    out = {}
    filas = (CompraDetalle.objects
             .filter(producto_id__in=ids, compra__empresa=empresa)
             .exclude(compra__estado__in=('borrador', 'anulada'))
             .order_by('producto_id', '-compra__fecha_emision', '-id')
             .values_list('producto_id', 'precio_unitario', 'compra__proveedor__razon_social'))
    for pid, costo, proveedor in filas:
        out.setdefault(pid, (costo, proveedor or ''))
    return out


def buscar_producto(usuario, entrada: E.BuscarProducto):
    """Una tool por intención: TODO lo que se pregunta de un producto (precio,
    stock, último costo, proveedor). Reemplaza a consultar_stock, que se
    solapaba con esta y confundía al modelo (#11 del eval)."""
    estado, encontrados = busqueda.resolver_producto(usuario.empresa, entrada.query)
    if not encontrados:
        return {'productos': []}
    ids = [pid for pid, _, _ in encontrados]
    productos = {p.id: p for p in Producto.objects.filter(empresa=usuario.empresa, pk__in=ids)}
    compras = _ultimas_compras(usuario.empresa, ids)
    salida = []
    for pid in ids:
        p = productos.get(pid)
        if not p:
            continue
        costo, proveedor = compras.get(pid, (p.precio_compra, ''))
        salida.append({
            'id': p.id, 'sku': p.sku, 'nombre': p.nombre,
            'precio_venta': str(p.precio_venta), 'moneda': p.moneda,
            'stock': str(p.stock_total), 'ultimo_costo': str(costo or ''),
            'proveedor': proveedor,
        })
    # sin coincidencia completa: son sugerencias, se dice
    return {'productos': salida, 'aproximado': estado == 'no_encontrado'}


def _resolver_venta(usuario, venta_id=None, venta_numero=None, cliente_query=None, extra_filtro=None):
    qs = Venta.objects.filter(empresa=usuario.empresa).exclude(estado='anulado')
    if extra_filtro:
        qs = qs.filter(**extra_filtro)
    if venta_id:
        return qs.filter(pk=venta_id).first(), None
    if venta_numero:
        return qs.filter(numero__iexact=venta_numero.strip()).first(), None
    if cliente_query:
        # misma búsqueda difusa que al cotizar («ferreteria union», «andino»);
        # si no hay coincidencia completa del cliente, no se adivina la venta
        estado, encontrados = busqueda.resolver_cliente(usuario.empresa, cliente_query)
        ids = [cid for cid, _, _ in encontrados] if estado in ('ok', 'ambiguo') else []
        candidatas = list(qs.filter(cliente_id__in=ids).order_by('-fecha_emision')[:3])
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


def resumen_ventas(usuario, entrada: E.ResumenVentas):
    """«¿Cuánto voy en ventas este mes?» — total del mes vs el anterior, número
    de ventas, top 3 clientes y por cobrar. Todo consolidado a S/ con el TC
    guardado por documento (desglose_pen). Solo lectura, scoped a la empresa."""
    from apps.core.services.tipo_cambio import desglose_pen, get_tc_actual

    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)
    if entrada.periodo == 'mes_anterior':
        inicio_mes = (inicio_mes - _dt.timedelta(days=1)).replace(day=1)
    fin_mes = (inicio_mes + _dt.timedelta(days=32)).replace(day=1) - _dt.timedelta(days=1)
    inicio_prev = (inicio_mes - _dt.timedelta(days=1)).replace(day=1)

    qs = Venta.objects.filter(empresa=usuario.empresa).exclude(estado__in=('borrador', 'anulado'))
    mes = qs.filter(fecha_emision__gte=inicio_mes, fecha_emision__lte=fin_mes)
    prev = qs.filter(fecha_emision__gte=inicio_prev, fecha_emision__lt=inicio_mes)

    # un solo lookup del TC de fallback (solo pesa si hay USD sin TC guardado)
    tc = get_tc_actual(usuario.empresa)
    total_mes = Decimal(str(desglose_pen(mes, 'total', fallback_tc=tc)['total_pen'] or 0))
    total_prev = Decimal(str(desglose_pen(prev, 'total', fallback_tc=tc)['total_pen'] or 0))
    por_cobrar = Decimal(str(desglose_pen(
        qs.filter(estado='pendiente').annotate(saldo=F('total') - F('pagos_total')), 'saldo',
        fallback_tc=tc,
    )['total_pen'] or 0))

    # top 3 clientes del mes en PEN (escala pyme: decenas de filas)
    por_cliente = {}
    for v in mes.select_related('cliente'):
        por_cliente.setdefault(v.cliente.nombre, Decimal('0'))
        por_cliente[v.cliente.nombre] += v.total_pen or Decimal('0')
    top = sorted(por_cliente.items(), key=lambda kv: -kv[1])[:3]

    return {
        'mes': inicio_mes.strftime('%Y-%m'),
        'total_mes': str(total_mes.quantize(Decimal('0.01'))),
        'n_ventas': mes.count(),
        'total_mes_anterior': str(total_prev.quantize(Decimal('0.01'))),
        'top_clientes': [{'nombre': n, 'total': str(t.quantize(Decimal("0.01")))} for n, t in top],
        'por_cobrar': str(por_cobrar.quantize(Decimal('0.01'))),
    }


# ── preparaciones (generan borrador; NUNCA escriben) ─────────────────────────

def _opcion(cid, extra, clave):
    return {'id': cid, 'nombre': extra['nombre'], clave: extra.get(clave, '')}


def _resolver_cliente_payload(usuario, entrada):
    """→ dict con cliente / cliente_estado / cliente_opciones / cliente_texto."""
    if entrada.cliente_id:
        c = Cliente.objects.filter(empresa=usuario.empresa, pk=entrada.cliente_id).first()
        if c:
            return {'cliente': c.id, 'cliente_nombre': c.nombre, 'cliente_estado': 'ok',
                    'cliente_texto': c.nombre, 'cliente_opciones': []}
    texto = (entrada.cliente or '').strip()
    estado, encontrados = busqueda.resolver_cliente(usuario.empresa, texto)
    if estado == 'ok':
        cid, _, extra = encontrados[0]
        return {'cliente': cid, 'cliente_nombre': extra['nombre'], 'cliente_estado': 'ok',
                'cliente_texto': texto, 'cliente_opciones': []}
    return {'cliente': None, 'cliente_nombre': '', 'cliente_estado': estado, 'cliente_texto': texto,
            'cliente_opciones': [_opcion(cid, extra, 'documento') for cid, _, extra in encontrados]}


# El caso real que motivó esto: «Ya te di los productos y cantidades» terminó
# como ítem de la cotización. Una referencia a la conversación no es un producto.
_META_FRASES = [
    r'^(el |los |la |las )?(producto|item|detalle)s?( y( las?)? cantidad(es)?)?$',
    r'^(la |las )?cantidad(es)?$',
    r'\b(ya )?te (lo|los|la|las )?(di|dije|pase|mande|envie|puse)\b',
    r'\blo (que te (dije|pase|mande)|de (antes|arriba))\b',
    r'^(los |las )?mism(o|a)s?( de antes)?$',
    r'^(lo|eso) (de arriba|anterior|mismo)$',
]


# Palabras que hablan DE productos sin nombrar ninguno: un ítem hecho solo de
# estas no es cotizable (el modelo llegó a inventar «productos pendientes» ×1).
_GENERICAS = {
    'producto', 'productos', 'item', 'items', 'articulo', 'articulos',
    'pendiente', 'pendientes', 'cantidad', 'cantidades', 'precio', 'precios',
    'unidad', 'unidades', 'cosa', 'cosas', 'varios', 'variados', 'generico',
    'general', 'cotizacion', 'cotizar', 'pedido', 'detalle', 'detalles',
    'anterior', 'anteriores', 'mismo', 'mismos', 'misma', 'mismas',
}


def _es_meta_frase(texto):
    t = busqueda.normalizar(texto)
    if any(re.search(p, t) for p in _META_FRASES):
        return True
    # sin contenido de producto: solo palabras genéricas o vacías
    toks = [p for p in t.split() if p not in busqueda._VACIAS]
    return bool(toks) and all(p in _GENERICAS for p in toks)


NO_VENDIBLES = ('RAW', 'SEMIFINISHED')   # materias primas/insumos


def _item_de_producto(p, it, base):
    """Ítem resuelto contra un producto del catálogo. Caso real 29/10: el
    precio de catálogo lleva SU moneda (nunca se copia el número a otra), y un
    insumo no bloquea la venta: entra como línea libre con nombre y precio."""
    if it.precio_unitario is not None:
        datos = {'precio_unitario': str(it.precio_unitario),
                 'precio_catalogo': False, 'moneda_precio': None}
    else:
        datos = {'precio_unitario': str(p.precio_venta),
                 'precio_catalogo': True,
                 'moneda_precio': getattr(p, 'moneda', None) or 'PEN'}
    if base.pop('_insumo_como_libre', False) and p.tipo_producto in NO_VENDIBLES:
        return {**base, **datos, 'estado': 'libre', 'producto': None, 'descripcion': p.nombre,
                'aviso': f'«{p.nombre}» está registrado como insumo; lo incluyo como línea libre'}
    return {**base, **datos, 'estado': 'ok', 'producto': p.id, 'descripcion': p.nombre, 'aviso': ''}


def _resolver_item(usuario, it, insumo_como_libre=False):
    base = {'texto': it.texto, 'cantidad': str(it.cantidad),
            'precio_unitario': str(it.precio_unitario) if it.precio_unitario is not None else None,
            'precio_incluye_igv': bool(it.precio_incluye_igv and it.precio_unitario is not None),
            'precio_catalogo': False, 'moneda_precio': None,
            'opciones': [], 'aviso': '', '_insumo_como_libre': insumo_como_libre}
    if it.producto_id:
        p = Producto.objects.filter(empresa=usuario.empresa, pk=it.producto_id).first()
        if p:
            return _item_de_producto(p, it, base)
    estado, encontrados = busqueda.resolver_producto(usuario.empresa, it.texto)
    if estado == 'ok':
        # umbral ALTO: todas las palabras del usuario coinciden con el producto
        p = Producto.objects.get(pk=encontrados[0][0], empresa=usuario.empresa)
        return _item_de_producto(p, it, base)
    base.pop('_insumo_como_libre', None)
    if estado == 'no_encontrado' and it.precio_unitario is not None:
        # sin match y CON precio → línea libre directa, sin botón intermedio
        # (la empresa cotiza cosas que no maneja en catálogo ni en stock)
        return {**base, 'estado': 'libre', 'producto': None, 'descripcion': it.texto}
    # match dudoso (ambiguo) o sin precio: se pregunta con botones; «usar como
    # texto libre» queda como salida manual
    return {**base, 'estado': estado, 'producto': None, 'descripcion': it.texto,
            'opciones': [_opcion(pid, extra, 'sku') for pid, _, extra in encontrados]}


def _normalizar_igv(payload):
    """Deja los precios del payload consistentes con cómo guarda la web.

    - Si TODOS los precios vienen del usuario con IGV incluido →
      precios_incluyen_igv=True y se guardan tal cual (el total cuadra al
      céntimo: 4×441 + 1750 = 3,514.00).
    - Si se mezclan con precios base (catálogo o usuario sin IGV) → los que
      incluían IGV se convierten a base (÷1.18, 2 decimales) y el flag queda
      en False, con aviso en la línea.
    """
    con_precio = [d for d in payload['detalles'] if d.get('precio_unitario') is not None]
    if con_precio and all(d.get('precio_incluye_igv') for d in con_precio):
        payload['precios_incluyen_igv'] = True
        return payload
    payload['precios_incluyen_igv'] = False
    for d in con_precio:
        if d.pop('precio_incluye_igv', False):
            base = (Decimal(d['precio_unitario']) / IGV).quantize(Decimal('0.01'), ROUND_HALF_UP)
            d['precio_unitario'] = str(base)
            d['aviso'] = (d.get('aviso') or 'precio convertido a base (dijiste IGV incluido)')
    return payload


def _moneda_documento(moneda_usuario, detalles):
    """Caso real 29/10: el catálogo tenía el producto en USD 39 y el documento
    salió en S/ 39. Regla: el número de un precio de catálogo NUNCA cambia de
    moneda. Si todo el catálogo usado coincide, el documento la adopta; si el
    usuario pidió otra (o el catálogo está mezclado), queda None → se pregunta."""
    monedas_catalogo = {d['moneda_precio'] for d in detalles if d.get('precio_catalogo')}
    if not monedas_catalogo:
        return moneda_usuario or 'PEN'
    if len(monedas_catalogo) == 1:
        (m,) = monedas_catalogo
        if moneda_usuario in (None, m):
            return m
    return None   # conflicto usuario↔catálogo o catálogo mezclado → preguntar


def _payload_documento(usuario, entrada, extra=None, es_venta=False):
    """Núcleo COMPARTIDO de cotización y venta: filtro de meta-frases, cliente
    difuso (o «falta»), ítems de catálogo/libres, moneda e IGV. → (payload, error)."""
    items = [it for it in entrada.items if it.producto_id or not _es_meta_frase(it.texto)]
    if not items:
        return None, {'error': 'No me quedó claro qué productos incluir. '
                               'Dímelos de nuevo, uno por línea, con cantidad y precio si lo tienes.'}
    if entrada.cliente_id or (entrada.cliente or '').strip():
        cliente_payload = _resolver_cliente_payload(usuario, entrada)
    else:
        # el usuario aún no dijo el cliente: NUNCA se descartan los ítems
        cliente_payload = {'cliente': None, 'cliente_nombre': '', 'cliente_estado': 'falta',
                           'cliente_texto': '', 'cliente_opciones': []}
    detalles = [_resolver_item(usuario, it, insumo_como_libre=es_venta) for it in items]
    payload = {
        **cliente_payload,
        'cliente_nuevo': None,
        'moneda': _moneda_documento(entrada.moneda, detalles),
        'moneda_usuario': entrada.moneda,
        'detalles': detalles,
        **(extra or {}),
    }
    _normalizar_igv(payload)
    return payload, None


def preparar_cotizacion(usuario, entrada: E.PrepararCotizacion):
    """UNA llamada del modelo basta: cliente e ítems llegan en texto y el
    SERVIDOR los resuelve con búsqueda difusa. Lo que no resuelve queda
    marcado en el borrador como pendiente; la respuesta ofrece botones.
    Sin cliente, el borrador se crea igual y se pregunta solo por él."""
    payload, error = _payload_documento(usuario, entrada, extra={
        'asunto': entrada.asunto or '',
        # 15 días de vigencia: el valor por defecto del negocio
        'fecha_vencimiento': (timezone.localdate() + _dt.timedelta(days=15)).isoformat(),
    })
    if error:
        return error
    return {'borrador': {'tipo': 'cotizacion', 'payload': payload,
                         'resumen': resumen_cotizacion(payload)}}


def preparar_venta(usuario, entrada: E.PrepararVenta):
    """Borrador de VENTA (feat/bot-ventas): mismo patrón que la cotización.
    La condición de pago NUNCA se asume: sin ella el borrador queda incompleto
    y se pregunta con botones (la ficha del Cliente no guarda condición/plazo,
    así que no hay valor previo que ofrecer). Al confirmar se crea con el
    MISMO servicio de la web (crear_venta)."""
    condicion = entrada.condicion_pago
    plazo = entrada.plazo_dias if condicion == 'credito' else None
    if condicion == 'credito' and not plazo:
        plazo = 30
    payload, error = _payload_documento(usuario, entrada, es_venta=True, extra={
        'condicion': condicion,
        'plazo_dias': plazo,
        'metodo_pago': entrada.metodo_pago,
    })
    if error:
        return error
    return {'borrador': {'tipo': 'venta', 'payload': payload,
                         'resumen': resumen_venta(payload)}}


def convertir_cotizacion_en_venta(usuario, entrada: E.ConvertirCotizacionEnVenta):
    """Borrador de CONVERSIÓN: al confirmar usa convertir_cotizacion_a_venta,
    el mismo servicio que el botón «Convertir a venta» de la web."""
    from apps.cotizaciones.models import Cotizacion

    qs = Cotizacion.objects.filter(empresa=usuario.empresa).select_related('cliente', 'venta')
    cot = None
    txt = (entrada.cotizacion_numero or '').strip()
    if txt:
        cot = qs.filter(numero__iexact=txt).first()
        if cot is None:
            # «COT-107», «cot 107» o «107» → COT-00000107
            digitos = re.sub(r'\D', '', txt)
            if digitos:
                cot = qs.filter(numero__iexact=f'COT-{int(digitos):08d}').first()
        if cot is None:
            return {'error': f'No encontré la cotización «{escape(txt)}».'}
    elif (entrada.cliente_query or '').strip():
        estado, encontrados = busqueda.resolver_cliente(usuario.empresa, entrada.cliente_query)
        ids = [cid for cid, _, _ in encontrados] if estado in ('ok', 'ambiguo') else []
        cot = (qs.filter(cliente_id__in=ids)
               .exclude(estado__in=('convertida', 'rechazada', 'vencida'))
               .order_by('-fecha_emision', '-id').first())
        if cot is None:
            return {'error': 'No encontré una cotización abierta de ese cliente.'}
    else:
        return {'error': 'Dime el número de la cotización (p. ej. COT-00000107) o el cliente.'}

    if cot.venta_id or cot.estado == 'convertida':
        venta = cot.venta.numero if cot.venta_id else ''
        return {'error': f'La {cot.numero} ya fue convertida{f" (venta {venta})" if venta else ""}.'}
    if cot.estado in ('rechazada', 'vencida'):
        return {'error': f'La {cot.numero} está {cot.get_estado_display().lower()}; no se puede convertir.'}
    if not cot.detalles.exists():
        return {'error': f'La {cot.numero} no tiene líneas.'}

    # misma regla que preparar_venta: la condición NUNCA se asume. Solo se
    # prellena si la cotización dice crédito EXPLÍCITO en forma_pago (el
    # default del modelo es «Contado», que no distingue elegido de omitido).
    fp = (cot.forma_pago or '').lower()
    if 'credito' in fp or 'crédito' in fp:
        condicion, plazo = 'credito', (60 if '60' in fp else 30)
    else:
        condicion, plazo = None, None

    payload = {'cotizacion': cot.id, 'numero': cot.numero,
               'cliente_nombre': cot.cliente.nombre,
               'total': str(cot.total), 'moneda': cot.moneda,
               'condicion': condicion, 'plazo_dias': plazo, 'metodo_pago': None}
    return {'borrador': {
        'tipo': 'conversion_venta',
        'payload': payload,
        'resumen': resumen_conversion(payload),
    }}


def resumen_conversion(payload):
    s = _simbolo(payload.get('moneda'))
    return (f'🔁 Convertir <b>{escape(payload.get("numero", ""))}</b> en VENTA\n'
            f'Cliente {escape(payload.get("cliente_nombre", ""))} · total {s} {_num(payload.get("total", 0))}'
            + _linea_condicion(payload))


# ── pendientes de una cotización (resolución por botones) ────────────────────

def pendientes_cotizacion(payload):
    """[('cliente', None) | ('item', idx) | ('condicion', None)] en el orden en
    que se preguntan. 'condicion' solo aplica a payloads de venta/conversión
    (los que traen la clave): PROHIBIDO asumir contado."""
    out = []
    if 'detalles' in payload and not payload.get('cliente'):
        nuevo = payload.get('cliente_nuevo') or {}
        if not nuevo.get('documento'):
            out.append(('cliente', None))
    for idx, d in enumerate(payload.get('detalles', [])):
        if d.get('estado') in ('ambiguo', 'no_encontrado'):
            out.append(('item', idx))
    if 'moneda' in payload and payload.get('moneda') is None:
        out.append(('moneda', None))
    if 'condicion' in payload and payload.get('condicion') is None:
        out.append(('condicion', None))
    return out


def totales_cotizacion(payload):
    """→ (subtotal, igv, total) con la misma aritmética que Cotizacion.calcular_totales."""
    suma = Decimal('0')
    for d in payload.get('detalles', []):
        if d.get('estado') in ('ambiguo', 'no_encontrado') or d.get('precio_unitario') is None:
            continue
        suma += Decimal(d['precio_unitario']) * Decimal(d['cantidad'])
    if payload.get('precios_incluyen_igv'):
        igv = (suma * Decimal('18') / Decimal('118')).quantize(Decimal('0.01'))
        return suma - igv, igv, suma
    igv = (suma * Decimal('18') / Decimal('100')).quantize(Decimal('0.01'))
    return suma, igv, suma + igv


def _linea_condicion(payload):
    """La condición SIEMPRE se muestra; crédito incluye el vencimiento."""
    cond = payload.get('condicion')
    if cond == 'contado':
        return f'\ncontado · {payload.get("metodo_pago") or "efectivo"}'
    if cond == 'credito':
        plazo = int(payload.get('plazo_dias') or 30)
        vence = timezone.localdate() + _dt.timedelta(days=plazo)
        return f'\ncrédito {plazo} días · vence {vence.strftime("%d/%m/%Y")}'
    return '\n❓ condición de pago por definir'


def resumen_venta(payload):
    return _resumen_documento(payload, '🧾 <b>Venta</b>', _linea_condicion(payload))


def resumen_cotizacion(payload):
    return _resumen_documento(payload, '📝 <b>Cotización</b>')


def _resumen_documento(payload, titulo, extra=''):
    s = _simbolo(payload.get('moneda'))
    if payload.get('cliente'):
        cliente = f'<b>{escape(payload.get("cliente_nombre", ""))}</b>'
    elif (payload.get('cliente_nuevo') or {}).get('documento'):
        n = payload['cliente_nuevo']
        cliente = f'<b>{escape(n["nombre"])}</b> (cliente nuevo, {n["tipo_documento"].upper()} {escape(n["documento"])})'
    elif payload.get('cliente_estado') == 'falta':
        cliente = '❓ (por definir)'
    else:
        cliente = f'❓ «{escape(payload.get("cliente_texto", ""))}»'
    lineas = []
    for d in payload.get('detalles', []):
        cant = Decimal(d['cantidad'])
        if d.get('estado') in ('ambiguo', 'no_encontrado'):
            lineas.append(f'  • ❓ «{escape(d["texto"])}» ×{cant:g}')
            continue
        if d.get('precio_unitario') is None:
            lineas.append(f'  • {escape(d["descripcion"])} ×{cant:g} — ⚠ precio por definir')
            continue
        precio = Decimal(d['precio_unitario'])
        aviso = f' ⚠ {escape(d["aviso"])}' if d.get('aviso') else ''
        lineas.append(f'  • {escape(d["descripcion"])} ×{cant:g} a {s} {_num(precio)}{aviso}')
    subtotal, igv, total = totales_cotizacion(payload)
    # sin «+ IGV» ambiguo: subtotal, IGV y total, siempre los tres
    return (f'{titulo} para {cliente}{extra}\n' + '\n'.join(lineas)
            + f'\nSubtotal: {s} {_num(subtotal)} · IGV (18%): {s} {_num(igv)}'
            + f'\n<b>Total: {s} {_num(total)}</b>')


def pregunta_pendiente(payload, borrador_id):
    """→ (texto, [(texto_boton, accion)]) para el PRIMER pendiente, o None.
    Máximo 3 opciones + la salida («cliente nuevo» / «texto libre»)."""
    pend = pendientes_cotizacion(payload)
    if not pend:
        return None
    tipo, idx = pend[0]
    if tipo == 'moneda':
        return ('Los precios del catálogo no coinciden con la moneda pedida. '
                '¿En qué moneda va el documento?', [
                    ('S/ Soles', f'r:{borrador_id}:mon:PEN'),
                    ('$ Dólares', f'r:{borrador_id}:mon:USD'),
                ])
    if tipo == 'condicion':
        # la ficha del Cliente no guarda condición/plazo: no hay valor previo
        # que ofrecer, se pregunta siempre con las tres opciones
        return '¿Condición de pago?', [
            ('📅 Crédito 30 días', f'r:{borrador_id}:cond:c30'),
            ('📅 Crédito 15 días', f'r:{borrador_id}:cond:c15'),
            ('💵 Contado', f'r:{borrador_id}:cond:cont'),
        ]
    if tipo == 'cliente':
        if payload.get('cliente_nuevo'):
            return (f'Envíame el RUC (11 dígitos) o DNI (8) de «{escape(payload["cliente_nuevo"]["nombre"])}».', [])
        if payload.get('cliente_estado') == 'falta':
            # el usuario aún no dijo cliente: pregunta abierta, sin botones
            return '¿Para qué cliente es la cotización?', []
        texto = escape(payload.get('cliente_texto', ''))
        botones = [(f'👤 {o["nombre"]}', f'r:{borrador_id}:c:{o["id"]}')
                   for o in payload.get('cliente_opciones', [])[:busqueda.MAX_OPCIONES]]
        botones.append((f'➕ Crear cliente nuevo «{payload.get("cliente_texto", "")[:30]}»', f'r:{borrador_id}:cn'))
        pregunta = (f'¿Cuál es el cliente «{texto}»?' if payload.get('cliente_estado') == 'ambiguo'
                    else f'No encontré al cliente «{texto}».')
        return pregunta, botones
    d = payload['detalles'][idx]
    botones = [(f'📦 {o["nombre"]}', f'r:{borrador_id}:i{idx}:{o["id"]}')
               for o in d.get('opciones', [])[:busqueda.MAX_OPCIONES]]
    botones.append((f'✍️ Usar «{d["texto"][:30]}» como texto libre', f'r:{borrador_id}:i{idx}:libre'))
    pregunta = (f'¿Cuál producto es «{escape(d["texto"])}»?' if d['estado'] == 'ambiguo'
                else f'No encontré el producto «{escape(d["texto"])}».')
    return pregunta, botones


def aplicar_resolucion(usuario, payload, objetivo, valor):
    """Aplica la opción elegida por botón. Solo acepta ids que el SERVIDOR
    ofreció (callback_data es forjable). → (payload, error|None)."""
    if objetivo == 'c':
        validas = {str(o['id']) for o in payload.get('cliente_opciones', [])}
        if valor not in validas:
            return payload, 'Esa opción no es válida.'
        c = Cliente.objects.filter(empresa=usuario.empresa, pk=int(valor)).first()
        if not c:
            return payload, 'Ese cliente ya no existe.'
        payload.update(cliente=c.id, cliente_nombre=c.nombre, cliente_estado='ok', cliente_nuevo=None)
        return payload, None
    if objetivo == 'cn':
        nombre = ' '.join(w.capitalize() for w in payload.get('cliente_texto', '').split()) or 'Cliente nuevo'
        payload['cliente_nuevo'] = {'nombre': nombre[:200], 'documento': None, 'tipo_documento': None}
        payload['cliente_estado'] = 'nuevo'
        return payload, None
    if objetivo == 'mon':
        if valor not in ('PEN', 'USD') or 'moneda' not in payload:
            return payload, 'Esa opción no es válida.'
        payload['moneda'] = valor
        for d in payload.get('detalles', []):
            # NUNCA copiar el número a otra moneda: el precio de catálogo que
            # no coincide se pide de nuevo en la moneda elegida
            if d.get('precio_catalogo') and d.get('moneda_precio') != valor:
                d['precio_unitario'] = None
                d['precio_catalogo'] = False
                d['aviso'] = (f'precio de catálogo en {d["moneda_precio"]}: '
                              f'dime el precio en {valor}')
        return payload, None
    if objetivo == 'cond':
        opciones = {'c30': ('credito', 30), 'c15': ('credito', 15), 'cont': ('contado', None)}
        if valor not in opciones or 'condicion' not in payload:
            return payload, 'Esa opción no es válida.'
        condicion, plazo = opciones[valor]
        payload.update(condicion=condicion, plazo_dias=plazo)
        return payload, None
    if objetivo.startswith('i') and objetivo[1:].isdigit():
        idx = int(objetivo[1:])
        detalles = payload.get('detalles', [])
        if idx >= len(detalles):
            return payload, 'Esa opción no es válida.'
        d = detalles[idx]
        if valor == 'libre':
            d.update(estado='libre', producto=None, descripcion=d['texto'])
            return payload, None
        if valor not in {str(o['id']) for o in d.get('opciones', [])}:
            return payload, 'Esa opción no es válida.'
        p = Producto.objects.filter(empresa=usuario.empresa, pk=int(valor)).first()
        if not p:
            return payload, 'Ese producto ya no existe.'
        es_venta = 'condicion' in payload
        if d.get('precio_unitario') is not None:
            datos = {'precio_unitario': d['precio_unitario'], 'precio_catalogo': False,
                     'moneda_precio': None, 'aviso': ''}
        elif (p.moneda or 'PEN') == payload.get('moneda'):
            datos = {'precio_unitario': str(p.precio_venta), 'precio_catalogo': True,
                     'moneda_precio': p.moneda or 'PEN', 'aviso': ''}
        else:
            # NUNCA copiar el número a otra moneda: se pide el precio
            datos = {'precio_unitario': None, 'precio_catalogo': False, 'moneda_precio': None,
                     'aviso': f'precio de catálogo en {p.moneda}: dime el precio en {payload.get("moneda")}'}
        if es_venta and p.tipo_producto in NO_VENDIBLES:
            d.update(estado='libre', producto=None, descripcion=p.nombre, **datos)
            d['aviso'] = (f'«{p.nombre}» está registrado como insumo; lo incluyo como línea libre'
                          + (f' · {datos["aviso"]}' if datos['aviso'] else ''))
        else:
            d.update(estado='ok', producto=p.id, descripcion=p.nombre, **datos)
        return payload, None
    return payload, 'Esa opción no es válida.'


def aplicar_documento(usuario, payload, texto):
    """RUC/DNI para «cliente nuevo». Si ya existe en la empresa, se usa ese
    cliente (no se duplica). Punto 5 (bot-ventas): consulta APIS.NET.PE con el
    MISMO servicio de la web (DocumentoService) y usa el nombre oficial; el
    borrador muestra «DNI xxxx → NOMBRE OFICIAL» para que el usuario confirme.
    → (payload, mensaje)."""
    doc = re.sub(r'\D', '', texto or '')
    if len(doc) not in (8, 11):
        return payload, 'Necesito un RUC de 11 dígitos o un DNI de 8. Inténtalo de nuevo.'
    existente = Cliente.objects.filter(empresa=usuario.empresa, documento=doc).first()
    if existente:
        payload.update(cliente=existente.id, cliente_nombre=existente.nombre,
                       cliente_estado='ok', cliente_nuevo=None)
        return payload, f'Ese documento ya es de «{escape(existente.nombre)}»: lo uso.'

    tipo = 'ruc' if len(doc) == 11 else 'dni'
    payload['cliente_nuevo'].update(documento=doc, tipo_documento=tipo)

    from apps.core.services.documento_service import DocumentoService
    try:
        res = DocumentoService.consultar_documento(doc, tipo)
    except Exception as e:  # red, credencial, proveedor caído
        res = {'success': False, 'error': f'{type(e).__name__}: {e}'}
    if res.get('success') and res.get('data'):
        data = res['data']
        oficial = (data.get('nombre_completo') or data.get('razon_social')
                   or data.get('nombre_comercial') or '').strip()
        if oficial:
            escrito = payload['cliente_nuevo'].get('nombre') or ''
            payload['cliente_nuevo']['nombre'] = oficial[:200]
            # el usuario SIEMPRE ve lo que devolvió RENIEC/SUNAT antes de confirmar
            aviso = f'✅ {tipo.upper()} {doc} → <b>{escape(oficial)}</b>'
            if escrito and busqueda.normalizar(escrito) != busqueda.normalizar(oficial):
                aviso += f' (escribiste «{escape(escrito)}»)'
            return payload, aviso
    # APIS falló: se avisa, queda registrado con ERROR y se usa el nombre tal
    # como lo escribió el usuario — igual que la web, que permite el ingreso
    # manual cuando la consulta no responde (no existe un flag «sin verificar»).
    logger.error('APIS.NET.PE no verificó %s %s: %s', tipo, doc,
                 str(res.get('error') or 'sin datos')[:200])
    return payload, ('⚠ No pude verificar el documento en RENIEC/SUNAT; '
                     'uso el nombre tal como lo escribiste.')


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
                f'({entrada.metodo_pago}) a {escape(venta.cliente.nombre)}\n'
                f'Venta {escape(venta.numero)} · saldo actual {_simbolo(venta.moneda)} {_num(saldo)}'
            ),
        },
    }


def cambiar_estado_operativo(usuario, entrada: E.CambiarEstadoOperativo):
    venta, candidatas = _resolver_venta(
        usuario, venta_id=entrada.venta_id, venta_numero=entrada.venta_numero,
        cliente_query=entrada.cliente_query,
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
                f'🚚 Venta <b>{escape(venta.numero)}</b> ({escape(venta.cliente.nombre)}): '
                f'{venta.get_estado_operativo_display()} → '
                f'<b>{dict(Venta.ESTADO_OPERATIVO_CHOICES)[entrada.nuevo_estado]}</b>'
            ),
        },
    }


# ── confirmación: el ÚNICO lugar donde el bot escribe en el ERP ──────────────

def _resolver_cliente_confirmacion(usuario, payload):
    """Cliente definitivo al confirmar (compartido cotización/venta): el id ya
    resuelto, o el cliente nuevo por documento (reutiliza si ya existe)."""
    if payload.get('cliente'):
        cliente = Cliente.objects.filter(pk=payload['cliente'], empresa=usuario.empresa).first()
        # REVIEW_BOT #4 — los serializers no siempre son scoped
        if not cliente:
            raise ValueError('El cliente no pertenece a tu empresa.')
        return cliente
    n = payload['cliente_nuevo']
    cliente, _ = Cliente.objects.get_or_create(
        empresa=usuario.empresa, documento=n['documento'],
        defaults={'nombre': n['nombre'], 'tipo_documento': n['tipo_documento'], 'usuario': usuario},
    )
    return cliente


def confirmar_borrador(borrador):
    """Crea el documento real usando los serializers/servicios existentes de la
    web (nunca una ruta paralela). Devuelve dict para el mensaje de éxito."""
    usuario = borrador.usuario
    contexto = {'request': SimpleNamespace(user=usuario)}

    # el rol también se exige AQUÍ (no solo al preparar): callback_data es
    # forjable y el rol pudo cambiar entre preparar y confirmar
    if getattr(usuario, 'rol', '') == 'solo_lectura':
        raise ValueError('Tu rol es de solo lectura: no puedo crear documentos.')

    if borrador.tipo == 'venta':
        from apps.ventas.services.creacion_venta import crear_venta
        payload = borrador.payload
        if pendientes_cotizacion(payload):
            raise ValueError('Faltan datos por resolver (cliente, productos o condición de pago).')
        detalles = payload.get('detalles', [])
        if any(d.get('precio_unitario') in (None, '', '0') for d in detalles):
            raise ValueError('Toda línea de una VENTA necesita precio. Dímelo y la rehago.')
        cliente = _resolver_cliente_confirmacion(usuario, payload)
        condicion = payload.get('condicion')
        plazo = int(payload.get('plazo_dias') or 30)
        # tipo_venta de la web más cercano al plazo pedido; el vencimiento
        # exacto (p. ej. 15 días) lo fija el servicio con plazo_dias
        tipo_venta = ('contado' if condicion == 'contado'
                      else ('credito_30' if plazo <= 30 else 'credito_60'))
        venta = crear_venta(usuario, {
            'cliente_id': cliente.id,
            'fecha_emision': timezone.localdate().isoformat(),
            # como la web: contado nace 'pagado'; el crédito lo fuerza a
            # 'pendiente' el propio servicio (con placeholder de pago)
            'estado': 'pagado' if tipo_venta == 'contado' else 'pendiente',
            'tipo_venta': tipo_venta,
            # sin medio dicho → el default de la web (efectivo); en contado la
            # venta nace pagada, igual que en el formulario web
            'metodo_pago': payload.get('metodo_pago') or 'efectivo',
            'moneda': payload.get('moneda', 'PEN'),
            'igv_incluido': bool(payload.get('precios_incluyen_igv')),
            'detalles': [
                {'producto': d.get('producto'), 'descripcion': d.get('descripcion') or d.get('texto'),
                 'cantidad': d['cantidad'], 'precio_unitario': d['precio_unitario']}
                for d in detalles
            ],
        }, plazo_dias=plazo if condicion == 'credito' else None)
        return {'documento_id': venta.id, 'numero': venta.numero, 'tipo': 'venta',
                'total': f'{_simbolo(venta.moneda)} {_num(venta.total)}'}

    if borrador.tipo == 'conversion_venta':
        from apps.cotizaciones.models import Cotizacion
        from apps.cotizaciones.services.conversion_service import convertir_cotizacion_a_venta
        from apps.ventas.services.creacion_venta import invalidar_caches_venta
        payload = borrador.payload
        if pendientes_cotizacion(payload):
            raise ValueError('Falta la condición de pago.')
        cot = Cotizacion.objects.get(pk=payload['cotizacion'], empresa=usuario.empresa)
        condicion = payload.get('condicion')
        plazo = int(payload.get('plazo_dias') or 30)
        # el MISMO servicio de la web, con la condición elegida en el chat
        venta = convertir_cotizacion_a_venta(
            cot,
            tipo_venta=('contado' if condicion == 'contado'
                        else ('credito_30' if plazo <= 30 else 'credito_60')),
            metodo_pago=payload.get('metodo_pago'),
            plazo_dias=plazo if condicion == 'credito' else None,
        )
        invalidar_caches_venta(usuario.empresa_id)
        return {'documento_id': venta.id, 'numero': venta.numero, 'tipo': 'conversion_venta',
                'cotizacion': cot.numero,
                'total': f'{_simbolo(venta.moneda)} {_num(venta.total)}'}

    if borrador.tipo == 'cotizacion':
        from apps.cotizaciones.serializers import CotizacionSerializer
        payload = borrador.payload
        # el botón Confirmar no se ofrece con pendientes, pero callback_data es
        # forjable: el servidor lo vuelve a exigir aquí
        if pendientes_cotizacion(payload):
            raise ValueError('Faltan datos por resolver (cliente o productos).')

        cliente = _resolver_cliente_confirmacion(usuario, payload)

        detalles = payload.get('detalles', [])
        ids_producto = [d['producto'] for d in detalles if d.get('producto')]
        if ids_producto and Producto.objects.filter(
                pk__in=ids_producto, empresa=usuario.empresa).count() != len(set(ids_producto)):
            raise ValueError('Hay productos que no pertenecen a tu empresa.')

        # datos LIMPIOS para el serializer: nada de las claves de trabajo del
        # borrador (texto, opciones, estado, aviso)
        data = {
            'cliente': cliente.id,
            'asunto': payload.get('asunto') or f'Cotización para {cliente.nombre}',
            'moneda': payload.get('moneda', 'PEN'),
            # igual que la web: si los precios ya incluyen IGV, se guardan tal
            # cual y el modelo lo extrae (el total cuadra al céntimo)
            'precios_incluyen_igv': bool(payload.get('precios_incluyen_igv')),
            'fecha_vencimiento': payload['fecha_vencimiento'],
            'detalles': [
                {'producto': d.get('producto'), 'descripcion': d['descripcion'],
                 'cantidad': d['cantidad'], 'precio_unitario': d.get('precio_unitario') or '0'}
                for d in detalles
            ],
            # empresa y usuario_creador los fija el SERVIDOR (nunca el payload del chat)
            'empresa': usuario.empresa_id, 'usuario_creador': usuario.id,
        }
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
