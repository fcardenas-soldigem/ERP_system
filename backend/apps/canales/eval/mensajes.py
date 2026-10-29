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

# ── fix V2: el caso real del piloto (cotización libre + contexto) ─────────────
# El mensaje 1 EXACTO: multilínea, dos productos fuera de catálogo, precios con
# IGV incluido y sin cliente. Los textos se comparten con los tests del oráculo.
MENSAJE_PILOTO = (
    'Crea una cotización de 4 PEDESTAL CON INCLINACIÓN 90° TV 32 A 75 PULG / VESA MAX\n'
    '600X400MM / CARGA 75KG  precio S/. 441.00 incluido IGV\n\n'
    '1 Gabinete de Piso para Servidores / 32 RU / 60x80x150 cm (AnchoxProf.xAlt.) /\n'
    'Puerta Frontal Microperforadas y Posterior doble Microperforadas  precio S/. 1750 incluido IGV'
)
SEGUIMIENTO_CLIENTE = 'Cliente Uhman Perú sac\nYa te di los productos y cantidades'
EDITA_CANTIDAD = 'cámbiale la cantidad del pedestal a 6'

# Un caso `critico` no admite fallo: si crea datos incorrectos (ítem basura,
# precio mal, ítems perdidos), el eval NO pasa aunque el % global alcance.
CASOS += [
    # el mensaje 1 exacto → borrador con 2 líneas libres y pregunta por el cliente
    {'id': 21, 'critico': True, 'texto': MENSAJE_PILOTO,
     'final': 'preparar_cotizacion',
     'checks': {'cliente_pendiente': True, 'precios_incluyen_igv': True,
                'items': [{'producto': 'PEDESTAL', 'cantidad': 4, 'precio': 441, 'estado': 'libre'},
                          {'producto': 'Gabinete', 'cantidad': 1, 'precio': 1750, 'estado': 'libre'}]}},
    # el seguimiento con el cliente completa el MISMO borrador (ítems intactos)
    {'id': 22, 'critico': True, 'turnos': [MENSAJE_PILOTO, SEGUIMIENTO_CLIENTE],
     'final': 'preparar_cotizacion',
     'checks': {'cliente_texto': 'uhman', 'precios_incluyen_igv': True,
                'items': [{'producto': 'PEDESTAL', 'cantidad': 4, 'precio': 441},
                          {'producto': 'Gabinete', 'cantidad': 1, 'precio': 1750}]}},
    # «ya te di los productos» SIN borrador previo: pide aclaración, nada de ítems basura
    {'id': 23, 'critico': True, 'texto': 'ya te di los productos',
     'final': 'aclaracion',
     'checks': {}},
    # resumen de ventas: antes caía al mensaje de ayuda
    {'id': 24, 'texto': 'cuánto voy en ventas este mes',
     'final': 'resumen_ventas',
     'checks': {'contiene': ['total_mes', 'por_cobrar']}},
    # edición por mensaje: cambia UNA cantidad y conserva el resto
    {'id': 25, 'critico': True,
     'turnos': [MENSAJE_PILOTO, 'Cliente Uhman Perú sac', EDITA_CANTIDAD],
     'final': 'preparar_cotizacion',
     'checks': {'items': [{'producto': 'PEDESTAL', 'cantidad': 6},
                          {'producto': 'Gabinete', 'cantidad': 1}]}},
    # producto que SÍ está en catálogo: usa el producto, no una línea libre
    {'id': 26, 'critico': True, 'texto': 'cotiza 2 teclados logitech k120 a acme a 35 soles',
     'final': 'preparar_cotizacion',
     'checks': {'cliente': 'Acme',
                'items': [{'producto': 'Teclado Logitech K120', 'cantidad': 2, 'estado': 'ok'}]}},
]


# ── feat/bot-ventas: ventas, conversión y honestidad ──────────────────────────
# El caso REAL: pidió una VENTA y el bot creó la cotización COT-00000107 sin
# avisar. El bot nunca cambia en silencio el tipo de documento pedido.
MENSAJE_VENTA_BRUNO = ('crea venta para bruno perez 10 headsets jabra evolve 20 '
                       '$39 la unidad mas igv')
SEGUIMIENTO_BRUNO = 'Cliente Bruno Perez Quispe'

CASOS += [
    # el caso real: VENTA (no cotización), USD, precio base («mas igv»), línea libre
    {'id': 27, 'critico': True, 'texto': MENSAJE_VENTA_BRUNO,
     'final': 'preparar_venta',
     'checks': {'cliente_texto': 'bruno', 'moneda': 'USD', 'precios_incluyen_igv': False,
                'items': [{'producto': 'jabra evolve 20', 'cantidad': 10,
                           'precio': 39, 'estado': 'libre'}]}},
    # multi-turno de venta: el seguimiento completa el MISMO borrador de venta
    {'id': 28, 'critico': True, 'turnos': [MENSAJE_VENTA_BRUNO, SEGUIMIENTO_BRUNO],
     'final': 'preparar_venta',
     'checks': {'cliente_texto': 'bruno',
                'items': [{'producto': 'jabra evolve 20', 'cantidad': 10, 'precio': 39}]}},
    # conversión de una cotización existente (COT-00000107 del fixture)
    {'id': 29, 'critico': True, 'texto': 'convierte la COT-107 en venta',
     'final': 'convertir_cotizacion_en_venta',
     'checks': {'contiene': ['COT-00000107']}},
    # honestidad: operación no soportada → ninguna tool, respuesta honesta fija
    {'id': 30, 'critico': True, 'texto': 'anula la factura 5',
     'final': None,
     'checks': {}},
    # cliente nuevo por DNI: queda pendiente (el flujo pide/verifica el documento)
    {'id': 31, 'texto': 'crea una venta de 1 teclado k120 a 35 soles para el cliente nuevo con DNI 70771234',
     'final': 'preparar_venta',
     'checks': {'cliente_pendiente': True,
                'items': [{'producto': 'Teclado', 'cantidad': 1, 'estado': 'ok'}]}},
    # condición de pago NUNCA asumida: sin decirla, el borrador queda incompleto
    # y el bot pregunta con botones [Crédito 30] [Crédito 15] [Contado]
    {'id': 32, 'critico': True, 'texto': 'crea venta para Interbank 2 jabra a 500 soles',
     'final': 'preparar_venta',
     'checks': {'condicion_pendiente': True,
                'items': [{'producto': 'jabra', 'cantidad': 2, 'precio': 500}]}},
]


def umbral(n_casos):
    """Fix V2: al menos 90 % de los casos correctos (techo), y además ningún
    caso `critico` puede fallar (lo exige eval_agente aparte)."""
    return -(-n_casos * 9 // 10)  # techo
