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
]


def umbral(n_casos):
    """13/15 correctos (≈ 87 %), proporcional si cambia el número de casos."""
    return -(-n_casos * 13 // 15)  # techo
