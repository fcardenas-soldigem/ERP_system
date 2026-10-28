"""
Eval de punta a punta del bot (puntos 3 y 4).

Cada caso fija la tool FINAL esperada (o None si está fuera de alcance) y
chequeos sobre el RESULTADO: lo que quedaría en el borrador (cliente
resuelto, ítems, cantidades, precios, moneda, venta, monto…) o el dato que
devuelve una consulta. No se mira la primera llamada del modelo: se ejecuta
el bucle de tools completo (como en producción) y se evalúa a dónde llegó.

Los nombres de clientes, productos y ventas que usan los textos los crea
eval/runner.py::preparar_datos() en una transacción que se revierte.
"""

CASOS = [
    # ── los 15 mensajes de vendedor del piloto ────────────────────────────────
    {'id': 1, 'texto': 'cotizale 3 jabra 750 a transportes lima porfa',
     'final': 'preparar_cotizacion',
     'checks': {'cliente': 'Transportes Lima',
                'items': [{'producto': 'Jabra Evolve2 750', 'cantidad': 3, 'precio': 450}]}},
    {'id': 2, 'texto': 'oe ya pago acme? la factura q le mandamos',
     'final': 'consultar_venta',
     'checks': {'contiene': ['V-090002', 'Acme']}},
    {'id': 3, 'texto': 'registrame el cobro de la V-090012, me yapearon 500',
     'final': 'preparar_cobro',
     'checks': {'venta_numero': 'V-090012', 'monto': 500, 'metodo_pago': 'transferencia'}},
    {'id': 4, 'texto': 'ya se entrego lo de minera andes, marcalo',
     'final': 'cambiar_estado_operativo',
     'checks': {'venta_cliente': 'Minera Andes', 'nuevo_estado': 'entregado'}},
    {'id': 5, 'texto': 'cuanto stock queda de teclados logitech',
     'final': 'buscar_producto',
     'checks': {'contiene': ['Teclado Logitech K120', '"stock": "40.00"']}},
    {'id': 6, 'texto': 'q ventas estan trabadas?',
     'final': 'ventas_detenidas',
     'checks': {'contiene': ['V-090006', 'Distribuidora Norte']}},
    {'id': 7, 'texto': 'buscame el ruc de constructora sol, creo q empieza con 2060',
     'final': 'buscar_cliente',
     'checks': {'contiene': ['20600000003']}},
    {'id': 8, 'texto': 'hazle cotizacion al cliente nuevo galvez: 10 cascos y 10 chalecos a 25 lucas en total no, 25 soles c/u',
     'final': 'preparar_cotizacion',
     'checks': {'cliente': 'Comercial Galvez', 'moneda': 'PEN',
                'items': [{'producto': 'Casco', 'cantidad': 10, 'precio': 25},
                          {'producto': 'Chaleco', 'cantidad': 10, 'precio': 25}]}},
    {'id': 9, 'texto': 'me pagaron en efectivo lo de ferreteria union, todito',
     'final': 'preparar_cobro',
     'checks': {'venta_cliente': 'Ferreteria Union', 'monto': 800, 'metodo_pago': 'efectivo'}},
    {'id': 10, 'texto': 'la venta de distribuidora norte ya llego al almacen, ponla recibida',
     'final': 'cambiar_estado_operativo',
     'checks': {'venta_cliente': 'Distribuidora Norte', 'nuevo_estado': 'recibido'}},
    {'id': 11, 'texto': 'tienes el precio del monitor lg 24? hay en stock?',
     'final': 'buscar_producto',
     'checks': {'contiene': ['24MK430', '"precio_venta": "520.00"', '"stock": "8.00"']}},
    {'id': 12, 'texto': 'saldo de la V-090003 xfa',
     'final': 'consultar_venta',
     'checks': {'contiene': ['V-090003', '"saldo": "1500.00"']}},
    {'id': 13, 'texto': 'cotiza pa inversiones ramirez 2 laptop hp 640 y 1 mouse inalambrico',
     'final': 'preparar_cotizacion',
     'checks': {'cliente': 'Inversiones Ramirez',
                'items': [{'producto': 'ProBook 640', 'cantidad': 2, 'precio': 3200},
                          {'producto': 'Mouse', 'cantidad': 1, 'precio': 30}]}},
    {'id': 14, 'texto': 'el cliente andino deposito 2 lucas a la cuenta, registralo',
     'final': 'preparar_cobro',
     'checks': {'venta_cliente': 'Andino', 'monto': 2000, 'metodo_pago': 'transferencia'}},
    {'id': 15, 'texto': 'factura de corporacion delta ya quedo facturada',
     'final': 'cambiar_estado_operativo',
     'checks': {'venta_cliente': 'Corporacion Delta', 'nuevo_estado': 'facturado'}},

    # ── punto 4: casos difíciles ──────────────────────────────────────────────
    # producto ambiguo: hay dos monitores LG → el borrador lo marca y ofrece opciones
    {'id': 16, 'texto': 'cotiza 2 monitores lg a transportes lima',
     'final': 'preparar_cotizacion',
     'checks': {'cliente': 'Transportes Lima',
                'items': [{'producto': 'lg', 'cantidad': 2, 'estado': 'ambiguo', 'opciones_min': 2}]}},
    # cliente inexistente: queda pendiente (se ofrecerá «Crear cliente nuevo»)
    {'id': 17, 'texto': 'cotiza 1 jabra 750 a ferreteria el sol',
     'final': 'preparar_cotizacion',
     'checks': {'cliente_pendiente': True,
                'items': [{'producto': 'Jabra Evolve2 750', 'cantidad': 1, 'precio': 450}]}},
    # cantidad en palabras
    {'id': 18, 'texto': 'cotiza una docena de chalecos reflectivos a comercial galvez',
     'final': 'preparar_cotizacion',
     'checks': {'cliente': 'Comercial Galvez',
                'items': [{'producto': 'Chaleco', 'cantidad': 12, 'precio': 25}]}},
    # moneda mezclada: el precio lo da en dólares
    {'id': 19, 'texto': 'cotizale a minera andes 2 monitores lg 27 a 420 dolares c/u',
     'final': 'preparar_cotizacion',
     'checks': {'cliente': 'Minera Andes', 'moneda': 'USD',
                'items': [{'producto': '27UL500', 'cantidad': 2, 'precio': 420}]}},
    # fuera de alcance: ninguna tool, respuesta fija
    {'id': 20, 'texto': 'que hora es?',
     'final': None,
     'checks': {}},
]


def umbral(n_casos):
    """13/15 correctos (≈ 87 %), proporcional si cambia el número de casos."""
    return -(-n_casos * 13 // 15)  # techo
