"""
Runner del eval de punta a punta (punto 3).

- preparar_datos(): clientes, productos y ventas que nombran los casos, sobre
  la empresa de seed_demo. El comando lo llama dentro de una transacción que
  SIEMPRE se revierte: nada queda en la BD.
- evaluar(): por caso ejecuta el MISMO bucle de tools que el bot
  (interprete.resolver, máx. 3 rondas), ejecuta la preparación final (que no
  escribe: devuelve el borrador) y evalúa el resultado.
  correcto = tool final + todos los chequeos; parcial = tool final correcta
  pero algún chequeo falla; incorrecto = otra tool, ninguna o error.
"""
import datetime as dt
import json
import time
from dataclasses import dataclass, field
from decimal import Decimal

from django.utils import timezone

from apps.canales.nucleo import servicios
from apps.canales.nucleo.busqueda import normalizar
from apps.canales.nucleo.interprete import resolver

# Una consulta que pasa de esto es un fallo de eficiencia (eval #5/#7/#11
# llegaron a 5 rondas): cuenta como parcial y bloquea el umbral.
MAX_RONDAS_CONSULTA = 2

PREPARACIONES = {
    'preparar_cotizacion': servicios.preparar_cotizacion,
    'preparar_cobro': servicios.preparar_cobro,
    'cambiar_estado_operativo': servicios.cambiar_estado_operativo,
}

CLIENTES = [
    ('Transportes Lima SAC', '20600000001'),
    ('Acme Peru SAC', '20600000002'),
    ('Constructora Sol del Peru SAC', '20600000003'),
    ('Comercial Galvez SAC', '20600000004'),
    ('Ferreteria Union SAC', '20600000005'),
    ('Distribuidora Norte EIRL', '20600000006'),
    ('Inversiones Ramirez SAC', '20600000007'),
    ('Comercializadora Andino SAC', '20600000008'),
    ('Corporacion Delta SAC', '20600000009'),
    ('Minera Andes SAC', '20600000010'),
]

PRODUCTOS = [  # sku, nombre, precio_venta, stock, precio_compra
    ('EV-750', 'Auricular Jabra Evolve2 750', '450', '15', '300'),
    ('K120', 'Teclado Logitech K120', '35', '40', '22'),
    ('LG24', 'Monitor LG 24MK430 24 pulgadas', '520', '8', '380'),
    ('LG27', 'Monitor LG 27UL500 27 pulgadas', '890', '5', '650'),
    ('CASCO-3M', 'Casco de seguridad 3M H-700', '25', '100', '14'),
    ('CHALECO', 'Chaleco reflectivo naranja', '25', '80', '12'),
    ('HP640', 'Laptop HP ProBook 640 G8', '3200', '6', '2600'),
    ('M170', 'Mouse inalambrico Logitech M170', '30', '50', '18'),
]

# numero, cliente, total, estado_operativo, dias en el estado
VENTAS = [
    ('V-090002', 'Acme Peru SAC', '1500', 'pendiente_compra', 0),
    ('V-090012', 'Constructora Sol del Peru SAC', '1200', 'pendiente_compra', 0),
    ('V-090004', 'Minera Andes SAC', '2500', 'recibido', 0),
    ('V-090005', 'Ferreteria Union SAC', '800', 'entregado', 0),
    ('V-090006', 'Distribuidora Norte EIRL', '4300', 'comprado', 30),   # detenida
    ('V-090003', 'Inversiones Ramirez SAC', '1500', 'entregado', 0),
    ('V-090008', 'Comercializadora Andino SAC', '3000', 'entregado', 0),
    ('V-090009', 'Corporacion Delta SAC', '5200', 'esperando_oc_nr', 0),
]


def preparar_datos(empresa):
    from apps.inventario.models.producto import Producto
    from apps.ventas.models import Cliente, Venta

    clientes = {}
    for nombre, ruc in CLIENTES:
        clientes[nombre], _ = Cliente.objects.update_or_create(
            empresa=empresa, documento=ruc,
            defaults={'nombre': nombre, 'tipo_documento': 'ruc', 'activo': True})
    for sku, nombre, pv, stock, pc in PRODUCTOS:
        p, _ = Producto.objects.update_or_create(
            empresa=empresa, sku=sku,
            defaults={'nombre': nombre, 'precio_venta': Decimal(pv), 'precio_compra': Decimal(pc),
                      'moneda': 'PEN', 'is_active': True})
        # stock_total lo recalcula save(); se fija directo para el eval
        Producto.objects.filter(pk=p.pk).update(stock_total=Decimal(stock))
    hoy = timezone.localdate()
    for numero, cliente, total, estado_op, dias in VENTAS:
        Venta.objects.filter(empresa=empresa, numero=numero).delete()
        v = Venta.objects.create(empresa=empresa, cliente=clientes[cliente], tipo_venta='credito_30',
                                 fecha_emision=hoy, metodo_pago='transferencia', moneda='PEN')
        # pre_save pone totales en 0 al crear: se fijan con update()
        Venta.objects.filter(pk=v.pk).update(
            numero=numero, total=Decimal(total), subtotal=Decimal(total), estado='pendiente',
            pagos_total=0, estado_operativo=estado_op,
            estado_operativo_actualizado=timezone.now() - dt.timedelta(days=dias))


# ── evaluación ───────────────────────────────────────────────────────────────

@dataclass
class ResultadoCaso:
    id: int
    texto: str
    esperado: str
    final: str
    estado: str                  # correcto | parcial | incorrecto
    rondas: int = 0
    ms: int = 0
    tokens: int = 0
    fallos: list = field(default_factory=list)
    llamadas: list = field(default_factory=list)


def _contiene(a, b):
    return normalizar(b) in normalizar(a)


def _chequear_cotizacion(payload, checks, fallos):
    if 'cliente' in checks and not _contiene(payload.get('cliente_nombre') or '', checks['cliente']):
        fallos.append(f'cliente: esperaba «{checks["cliente"]}», quedó '
                      f'«{payload.get("cliente_nombre") or payload.get("cliente_texto")}» ({payload.get("cliente_estado")})')
    if checks.get('cliente_pendiente') and payload.get('cliente'):
        fallos.append(f'cliente: esperaba PENDIENTE, se resolvió a «{payload.get("cliente_nombre")}»')
    if 'moneda' in checks and payload.get('moneda') != checks['moneda']:
        fallos.append(f'moneda: esperaba {checks["moneda"]}, quedó {payload.get("moneda")}')
    detalles = payload.get('detalles', [])
    esperados = checks.get('items', [])
    if esperados and len(detalles) != len(esperados):
        fallos.append(f'ítems: esperaba {len(esperados)}, quedaron {len(detalles)}')
    for esp in esperados:
        d = next((d for d in detalles
                  if _contiene(d.get('descripcion') or '', esp['producto'])
                  or _contiene(d.get('texto') or '', esp['producto'])), None)
        if d is None:
            fallos.append(f'ítem «{esp["producto"]}»: no está en el borrador')
            continue
        if 'cantidad' in esp and Decimal(d['cantidad']) != Decimal(str(esp['cantidad'])):
            fallos.append(f'ítem «{esp["producto"]}»: cantidad {d["cantidad"]} ≠ {esp["cantidad"]}')
        if 'precio' in esp and (d.get('precio_unitario') is None
                                or Decimal(d['precio_unitario']) != Decimal(str(esp['precio']))):
            fallos.append(f'ítem «{esp["producto"]}»: precio {d.get("precio_unitario")} ≠ {esp["precio"]}')
        if 'estado' in esp and d.get('estado') != esp['estado']:
            fallos.append(f'ítem «{esp["producto"]}»: estado {d.get("estado")} ≠ {esp["estado"]}')
        if 'opciones_min' in esp and len(d.get('opciones') or []) < esp['opciones_min']:
            fallos.append(f'ítem «{esp["producto"]}»: {len(d.get("opciones") or [])} opciones '
                          f'(se esperaban ≥ {esp["opciones_min"]})')


def _chequear_venta(usuario, payload, checks, fallos):
    from apps.ventas.models import Venta
    venta = Venta.objects.filter(pk=payload.get('venta'), empresa=usuario.empresa).select_related('cliente').first()
    if 'venta_cliente' in checks and not (venta and _contiene(venta.cliente.nombre, checks['venta_cliente'])):
        fallos.append(f'venta: esperaba cliente «{checks["venta_cliente"]}», quedó '
                      f'«{venta.cliente.nombre if venta else "—"}»')
    if 'venta_numero' in checks and payload.get('venta_numero') != checks['venta_numero']:
        fallos.append(f'venta: esperaba {checks["venta_numero"]}, quedó {payload.get("venta_numero")}')
    if 'monto' in checks and Decimal(payload.get('monto', '-1')) != Decimal(str(checks['monto'])):
        fallos.append(f'monto: {payload.get("monto")} ≠ {checks["monto"]}')
    for clave in ('metodo_pago', 'nuevo_estado'):
        if clave in checks and payload.get(clave) != checks[clave]:
            fallos.append(f'{clave}: {payload.get(clave)} ≠ {checks[clave]}')


def chequear(usuario, final, resultado, checks):
    """→ lista de fallos (vacía = correcto)."""
    fallos = []
    if final in PREPARACIONES:
        if 'borrador' not in resultado:
            return [f'sin borrador: {resultado.get("error") or resultado}']
        payload = resultado['borrador']['payload']
        if final == 'preparar_cotizacion':
            _chequear_cotizacion(payload, checks, fallos)
        else:
            _chequear_venta(usuario, payload, checks, fallos)
    plano = json.dumps(resultado, ensure_ascii=False, default=str)
    for dato in checks.get('contiene', []):
        if dato not in plano:
            fallos.append(f'falta «{dato}» en el resultado')
    return fallos


def evaluar_caso(usuario, caso, cliente_llm=None):
    rc = ResultadoCaso(id=caso['id'], texto=caso['texto'], esperado=caso['final'] or '—',
                       final='—', estado='incorrecto')
    t0 = time.monotonic()
    try:
        r = resolver(usuario, caso['texto'], cliente=cliente_llm)
    except Exception as e:  # credenciales, red, proveedor…
        rc.fallos = [f'error: {type(e).__name__}: {str(e)[:150]}']
        rc.ms = int((time.monotonic() - t0) * 1000)
        return rc
    rc.rondas, rc.tokens, rc.llamadas = r.rondas, r.tokens_entrada + r.tokens_salida, r.llamadas
    final = r.nombre if r.tipo in ('preparacion', 'lectura') else None
    rc.final = final or '—'
    resultado = None
    if r.tipo == 'preparacion':
        resultado = PREPARACIONES[final](usuario, r.entrada)   # no escribe: devuelve el borrador
    elif r.tipo == 'lectura':
        resultado = r.resultado
    rc.ms = int((time.monotonic() - t0) * 1000)

    if final != caso['final']:
        rc.fallos = [f'tool final: esperaba {caso["final"] or "ninguna"}, llegó {final or "ninguna"}']
        return rc
    if final is None:
        rc.estado = 'correcto'
        return rc
    rc.fallos = chequear(usuario, final, resultado, caso.get('checks', {}))
    if es_consulta(final) and rc.rondas > MAX_RONDAS_CONSULTA:
        rc.fallos.append(f'consulta con {rc.rondas} rondas (máx. {MAX_RONDAS_CONSULTA})')
    rc.estado = 'parcial' if rc.fallos else 'correcto'
    return rc


def es_consulta(final):
    return final is not None and final not in PREPARACIONES


def evaluar(usuario, casos, cliente_llm=None):
    return [evaluar_caso(usuario, c, cliente_llm) for c in casos]
