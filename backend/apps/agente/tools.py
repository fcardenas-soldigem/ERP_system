"""
Herramientas de LECTURA del MCP (Fase 2 base).

Cada herramienta recibe `(empresa, arguments)` y SIEMPRE filtra por `empresa` (la del
token). Nunca aceptan `empresa` como parámetro → aislamiento multi-tenant garantizado.
Ninguna escribe, aprueba, convierte, factura, borra ni envía correos.

El registro `TOOLS` expone nombre, descripción (en español, para orientar al agente) y
`inputSchema` (JSON Schema), que alimenta `tools/list` y `tools/call` del endpoint MCP.
"""
from django.db.models import Q


def _buscar_cliente(empresa, args):
    from apps.ventas.models import Cliente
    texto = (args.get('texto') or '').strip()
    if not texto:
        return {'clientes': []}
    qs = Cliente.objects.filter(empresa=empresa).filter(
        Q(nombre__icontains=texto) | Q(documento__icontains=texto) | Q(email__icontains=texto)
    ).order_by('nombre')[:20]
    return {'clientes': [{
        'id': c.id,
        'razon_social': c.nombre,
        'ruc': c.documento,
        'tipo_documento': c.tipo_documento,
        'email': c.email or '',
        'telefono': c.telefono or '',
    } for c in qs]}


def _historial_precios_item(empresa, args):
    from apps.cotizaciones.models import DetalleCotizacion
    from apps.compras.models import CompraDetalle
    producto_id = args.get('producto_id')
    descripcion = (args.get('descripcion') or '').strip()

    cot = DetalleCotizacion.objects.filter(cotizacion__empresa=empresa)
    com = CompraDetalle.objects.filter(compra__empresa=empresa)
    if producto_id:
        cot = cot.filter(producto_id=producto_id)
        com = com.filter(producto_id=producto_id)
    elif descripcion:
        cot = cot.filter(Q(producto__nombre__icontains=descripcion) | Q(descripcion__icontains=descripcion))
        com = com.filter(producto__nombre__icontains=descripcion)
    else:
        return {'entradas': [], 'nota': 'Indica producto_id o descripcion.'}

    entradas = []
    for d in cot.select_related('cotizacion', 'producto').order_by('-cotizacion__fecha_emision')[:10]:
        entradas.append({
            'fuente': 'cotizacion',
            'fecha': str(d.cotizacion.fecha_emision),
            'item': (d.producto.nombre if d.producto else d.descripcion) or '',
            'precio': str(d.precio_unitario),
            'costo': str(d.costo_unitario) if d.costo_unitario is not None else None,
            'moneda': d.cotizacion.moneda,
            'proveedor': None,
        })
    for d in com.select_related('compra', 'compra__proveedor', 'producto').order_by('-compra__fecha_emision')[:10]:
        compra = d.compra
        entradas.append({
            'fuente': 'compra',
            'fecha': str(compra.fecha_emision),
            'item': d.producto.nombre,
            'precio': str(d.precio_unitario),
            'costo': str(d.precio_unitario),  # en compras el precio pagado ES el costo
            'moneda': getattr(compra, 'moneda', 'PEN'),
            'proveedor': getattr(getattr(compra, 'proveedor', None), 'nombre', None),
        })
    entradas.sort(key=lambda e: e['fecha'], reverse=True)
    return {'entradas': entradas[:15]}


def _ventas_esperando_oc_nr(empresa, args):
    from apps.ventas.models import Venta
    qs = (Venta.objects.filter(empresa=empresa, estado_operativo='esperando_oc_nr')
          .select_related('cliente')
          .prefetch_related('detalles', 'detalles__producto')
          .order_by('-fecha_emision')[:50])
    ventas = []
    for v in qs:
        items = [{
            'descripcion': (d.producto.nombre if d.producto else d.descripcion) or '',
            'cantidad': str(d.cantidad),
            'precio': str(d.precio_unitario),
        } for d in v.detalles.all()]
        ventas.append({
            'venta_id': v.id,
            'numero': v.numero,
            'cliente': v.cliente.nombre,
            'total': str(v.total),
            'moneda': v.moneda,
            'items': items,
        })
    return {'ventas': ventas}


def _listar_propuestas_pendientes(empresa, args):
    # La creación de propuestas (cotizaciones borrador_agente, OC/NR, discrepancias)
    # llega en una fase posterior. Por ahora, vacío.
    return {'propuestas': []}


TOOLS = {
    'buscar_cliente': {
        'handler': _buscar_cliente,
        'description': (
            'Busca clientes de tu empresa por nombre o razón social, RUC/DNI o email. '
            'Úsala cuando un correo menciona a un cliente y necesitas ubicar su ficha antes de '
            'cotizar. Devuelve una lista de coincidencias con id, razón social, RUC/DNI, tipo de '
            'documento, email y teléfono.'
        ),
        'inputSchema': {
            'type': 'object',
            'properties': {
                'texto': {'type': 'string', 'description': 'Texto a buscar: nombre, RUC/DNI o email.'},
            },
            'required': ['texto'],
        },
    },
    'historial_precios_item': {
        'handler': _historial_precios_item,
        'description': (
            'Devuelve el historial de precios de un ítem a partir de cotizaciones y compras previas '
            'de tu empresa. Úsala para sugerir un precio y un costo al armar una cotización. Pasa '
            'producto_id si lo conoces, o una descripción de texto. Devuelve entradas con fuente '
            '(cotizacion/compra), fecha, ítem, precio, costo, moneda y proveedor.'
        ),
        'inputSchema': {
            'type': 'object',
            'properties': {
                'producto_id': {'type': 'integer', 'description': 'Id del producto del catálogo (si se conoce).'},
                'descripcion': {'type': 'string', 'description': 'Descripción o nombre del ítem a buscar.'},
            },
        },
    },
    'ventas_esperando_oc_nr': {
        'handler': _ventas_esperando_oc_nr,
        'description': (
            'Lista las ventas de tu empresa que están esperando la Orden de Compra y/o la Nota de '
            'Recepción del cliente (estado operativo "esperando_oc_nr"). Úsala para conciliar un '
            'correo que trae una OC/NR del cliente. Devuelve cada venta con id, número, cliente, '
            'total, moneda e ítems resumidos.'
        ),
        'inputSchema': {'type': 'object', 'properties': {}},
    },
    'listar_propuestas_pendientes': {
        'handler': _listar_propuestas_pendientes,
        'description': (
            'Lista las propuestas que el agente dejó pendientes de confirmación humana en el ERP '
            '(cotizaciones borrador, OC/NR asociadas, discrepancias). Úsala para revisar qué queda '
            'por confirmar. Por ahora devuelve una lista vacía: la creación de propuestas llega en '
            'una fase posterior.'
        ),
        'inputSchema': {'type': 'object', 'properties': {}},
    },
}


def tools_list():
    """Formato de `tools/list` del protocolo MCP."""
    return [
        {'name': name, 'description': spec['description'], 'inputSchema': spec['inputSchema']}
        for name, spec in TOOLS.items()
    ]


def run_tool(name, empresa, arguments):
    """Ejecuta la herramienta. Devuelve (result_dict, resumen_str). Lanza KeyError si no existe."""
    spec = TOOLS[name]
    result = spec['handler'](empresa, arguments or {})
    # Resumen corto para el log: longitud de la primera lista del resultado.
    resumen = ''
    for k, v in result.items():
        if isinstance(v, list):
            resumen = f'{len(v)} {k}'
            break
    return result, resumen
