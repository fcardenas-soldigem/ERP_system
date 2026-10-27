"""
C11 — Eval del intérprete: 15 mensajes como los escribe un vendedor peruano
(jerga, tipeo de teléfono, sin tildes). Cada caso fija la herramienta esperada
y un SUBCONJUNTO de parámetros que deben aparecer (match laxo: contains para
strings, igualdad para números).

Se corre contra el LLM real con `manage.py eval_agente` (requiere credenciales
de Vertex). La suite solo valida la integridad del dataset y el comparador.
"""

CASOS = [
    {
        'id': 1,
        'texto': 'cotizale 3 jabra 750 a transportes lima porfa',
        'tool': 'preparar_cotizacion',
        'params': {'cliente_query': 'transportes lima', 'items.0.cantidad': 3},
    },
    {
        'id': 2,
        'texto': 'oe ya pago acme? la factura q le mandamos',
        'tool': 'consultar_venta',
        'params': {'cliente_query': 'acme'},
    },
    {
        'id': 3,
        'texto': 'registrame el cobro de la V-000012, me yapearon 500',
        'tool': 'preparar_cobro',
        'params': {'venta_numero': 'V-000012', 'monto': 500},
    },
    {
        'id': 4,
        'texto': 'ya se entrego lo de minera andes, marcalo',
        'tool': 'cambiar_estado_operativo',
        'params': {'nuevo_estado': 'entregado'},
    },
    {
        'id': 5,
        'texto': 'cuanto stock queda de teclados logitech',
        'tool': 'consultar_stock',
        'params': {'query': 'logitech'},
    },
    {
        'id': 6,
        'texto': 'q ventas estan trabadas?',
        'tool': 'ventas_detenidas',
        'params': {},
    },
    {
        'id': 7,
        'texto': 'buscame el ruc de constructora sol, creo q empieza con 2055',
        'tool': 'buscar_cliente',
        'params': {'query': 'constructora sol'},
    },
    {
        'id': 8,
        'texto': 'hazle cotizacion al cliente nuevo galvez: 10 cascos y 10 chalecos a 25 lucas en total no, 25 soles c/u',
        'tool': 'preparar_cotizacion',
        'params': {'cliente_query': 'galvez'},
    },
    {
        'id': 9,
        'texto': 'me pagaron en efectivo lo de ferreteria union, todito',
        'tool': 'preparar_cobro',
        'params': {'cliente_query': 'ferreteria union', 'metodo_pago': 'efectivo'},
    },
    {
        'id': 10,
        'texto': 'la venta de distribuidora norte ya llego al almacen, ponla recibida',
        'tool': 'cambiar_estado_operativo',
        'params': {'nuevo_estado': 'recibido'},
    },
    {
        'id': 11,
        'texto': 'tienes el precio del monitor lg 24? hay en stock?',
        'tool': 'consultar_stock',
        'params': {'query': 'lg 24'},
    },
    {
        'id': 12,
        'texto': 'saldo de la V-000003 xfa',
        'tool': 'consultar_venta',
        'params': {'venta_numero': 'V-000003'},
    },
    {
        'id': 13,
        'texto': 'cotiza pa inversiones ramirez 2 laptop hp 640 y 1 mouse inalambrico',
        'tool': 'preparar_cotizacion',
        'params': {'cliente_query': 'ramirez'},
    },
    {
        'id': 14,
        'texto': 'el cliente andino deposito 2 lucas a la cuenta, registralo',
        'tool': 'preparar_cobro',
        'params': {'cliente_query': 'andino', 'monto': 2000},
    },
    {
        'id': 15,
        'texto': 'factura de corporacion delta ya quedo facturada',
        'tool': 'cambiar_estado_operativo',
        'params': {'nuevo_estado': 'facturado'},
    },
]


def _obtener(d, ruta):
    """'items.0.cantidad' → d['items'][0]['cantidad'] (sobre dict del model_dump)."""
    actual = d
    for parte in ruta.split('.'):
        if isinstance(actual, list):
            actual = actual[int(parte)]
        elif isinstance(actual, dict):
            actual = actual.get(parte)
        else:
            actual = getattr(actual, parte, None)
        if actual is None:
            return None
    return actual


def comparar(caso, tool, entrada):
    """→ (ok, detalles). Match laxo de parámetros sobre la entrada pydantic."""
    if tool != caso['tool']:
        return False, f"tool: esperaba {caso['tool']}, llegó {tool}"
    datos = entrada.model_dump(mode='json') if entrada is not None else {}
    fallos = []
    for ruta, esperado in caso['params'].items():
        valor = _obtener(datos, ruta)
        if isinstance(esperado, str):
            ok = esperado.lower() in str(valor or '').lower()
        else:
            try:
                ok = float(valor) == float(esperado)
            except (TypeError, ValueError):
                ok = False
        if not ok:
            fallos.append(f'{ruta}: esperaba {esperado!r}, llegó {valor!r}')
    return not fallos, '; '.join(fallos) or 'ok'
