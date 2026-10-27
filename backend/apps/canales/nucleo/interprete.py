"""
Intérprete (B5/B8): un mensaje de texto → (servicio, parámetros) usando la
capa LLM existente (ai_assistant.services.llm_client) con tool-calling.

Es un bot de TAREAS: si el modelo no elige herramienta, la respuesta es fija
(B8), nunca conversación abierta.
"""
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import pydantic

from apps.ai_assistant.services.llm_client import LLMMessage, ToolSpec, get_llm_client
from apps.ai_assistant.services.tool_specs import schema_de_pydantic

from . import esquemas as E

logger = logging.getLogger(__name__)

# servicio → (esquema pydantic, descripción para el modelo)
CATALOGO = {
    # una tool por intención; cada descripción dice cuándo NO usarla
    'preparar_cotizacion': (E.PrepararCotizacion, 'Cotizar / hacer una proforma. Pasa el cliente y cada producto en TEXTO, tal como los dijo el usuario («3 jabra 750 a transportes lima» → cliente "transportes lima", producto "jabra 750", cantidad 3): el servidor los busca. NO busques clientes ni productos antes. Cantidades en palabras a número («una docena» = 12). Si dicen precio por unidad, ponlo en precio_unitario con su moneda.'),
    'preparar_cobro': (E.PrepararCobro, 'Registrar un pago o cobro RECIBIDO de un cliente («me pagaron», «depositó», «me yapearon»). Yape/Plin = transferencia. Sin monto → se cobra el saldo completo.'),
    'cambiar_estado_operativo': (E.CambiarEstadoOperativo, 'Marcar el avance de una venta: comprado, recibido (llegó al almacén), entregado, facturado. Por número de venta o por cliente.'),
    'consultar_venta': (E.ConsultarVenta, 'Saber si un cliente ya pagó una venta: estado de pago, cobrado y saldo pendiente.'),
    'buscar_producto': (E.BuscarProducto, 'Consultar UN producto: precio de venta, stock, último costo y proveedor. NO la uses para cotizar (preparar_cotizacion ya busca los productos).'),
    'buscar_cliente': (E.BuscarCliente, 'Consultar los datos de un cliente (RUC/DNI, teléfono). NO la uses para cotizar ni para cobrar.'),
    'ventas_detenidas': (E.VentasDetenidas, 'Listar las ventas detenidas o atrasadas y por qué.'),
}

SYSTEM = (
    'Eres el asistente operativo de un ERP para una pyme peruana. El usuario es un '
    'vendedor que escribe desde el teléfono, con jerga y errores de tipeo. Tu ÚNICO '
    'trabajo es elegir UNA herramienta y sus parámetros. No converses. Montos: '
    '"lucas" = soles; "2 lucas" = 2000 PEN. "Factura/venta de X" se busca por '
    'cliente_query. Si el pedido no corresponde a ninguna herramienta, no llames ninguna.'
)

FUERA_DE_ALCANCE = (
    'Puedo ayudarte con: cotizar, registrar cobros, cambiar el estado de una venta, '
    'consultar ventas, stock o ventas detenidas. Por ejemplo: '
    '«cotízale 3 jabra 750 a Transportes Lima» o «¿ya pagó Acme?».'
)


def _tools():
    return [
        # mismo sanitizador que el asistente web: un solo lugar decide qué
        # JSON Schema acepta Gemini (antes el bot tenía uno propio que dejaba
        # pasar exclusiveMinimum → eval_agente 0/15 contra Vertex real)
        ToolSpec(name=nombre, description=desc, parameters=schema_de_pydantic(esquema))
        for nombre, (esquema, desc) in CATALOGO.items()
    ]


MAX_RONDAS = 5

# Preparan un borrador: cortan el bucle y NO se ejecutan aquí (el orquestador
# exige rol de escritura antes; el eval las ejecuta sin persistir nada).
PREPARACIONES = ('preparar_cotizacion', 'preparar_cobro', 'cambiar_estado_operativo')
# Lecturas que SON la respuesta: se ejecutan y cortan el bucle.
LECTURAS_TERMINALES = ('consultar_venta', 'ventas_detenidas')
# Lecturas que pueden ser un paso previo: se ejecutan y su resultado vuelve
# al modelo (compacto) para que decida el siguiente paso.
LECTURAS_INTERMEDIAS = ('buscar_cliente', 'buscar_producto')


@dataclass
class Resolucion:
    """Lo que decidió el bucle. tipo ∈ preparacion | lectura | fuera | faltan_datos."""
    tipo: str
    nombre: Optional[str] = None
    entrada: Any = None
    resultado: Any = None          # solo lecturas (ya ejecutadas)
    rondas: int = 0
    tokens_entrada: int = 0
    tokens_salida: int = 0
    ms: int = 0
    llamadas: list = field(default_factory=list)   # [(ronda, tool)] para el eval


def _para_modelo(nombre, resultado):
    """Lo MÍNIMO que el modelo necesita para seguir: ids y nombres. Costos,
    proveedores, teléfonos y stock no salen hacia Vertex por esta vía."""
    if nombre == 'buscar_cliente':
        datos = [{'id': c['id'], 'nombre': c['nombre']} for c in resultado.get('clientes', [])]
    elif nombre == 'buscar_producto':
        datos = [{'id': p['id'], 'nombre': p['nombre'], 'sku': p['sku']} for p in resultado.get('productos', [])]
    else:
        datos = resultado
    return json.dumps({'resultado': datos}, ensure_ascii=False, default=str)[:4000]


def resolver(usuario, texto: str, historial: list[LLMMessage] | None = None,
             cliente=None, max_rondas: int = MAX_RONDAS) -> Resolucion:
    """Bucle de tools (máx. 5 rondas) compartido por el bot y eval_agente: el
    eval mide exactamente lo que hace producción.

    Lanza LLMNoConfigurado/errores del proveedor hacia quien llama.
    """
    from . import servicios  # import tardío: servicios no depende de esto

    lecturas = {
        'consultar_venta': servicios.consultar_venta,
        'ventas_detenidas': servicios.ventas_detenidas,
        'buscar_cliente': servicios.buscar_cliente,
        'buscar_producto': servicios.buscar_producto,
    }
    cliente = cliente or get_llm_client()
    tools = _tools()
    mensajes = list(historial or []) + [LLMMessage(role='user', content=texto)]
    res = Resolucion(tipo='fuera')
    ultima_lectura = None
    hubo_args_invalidos = False
    t0 = time.monotonic()

    try:
        for ronda in range(1, max_rondas + 1):
            resp = cliente.chat(system=SYSTEM, messages=mensajes, tools=tools, temperature=0.0)
            res.rondas = ronda
            res.tokens_entrada += resp.tokens_entrada
            res.tokens_salida += resp.tokens_salida
            if not resp.tool_calls:
                break
            mensajes.append(LLMMessage(role='assistant', content=resp.text or None,
                                       tool_calls=resp.tool_calls, raw=resp.raw))
            for tc in resp.tool_calls:
                res.llamadas.append((ronda, tc.name))
                esquema = CATALOGO.get(tc.name, (None, None))[0]
                if esquema is None:
                    logger.warning('LLM eligió herramienta desconocida: %s', tc.name)
                    mensajes.append(LLMMessage(role='tool', tool_call_id=tc.id, name=tc.name,
                                               content='{"error": "herramienta desconocida"}'))
                    continue
                try:
                    entrada = esquema.model_validate(tc.arguments or {})
                except pydantic.ValidationError as e:
                    hubo_args_invalidos = True
                    # el modelo puede corregirse en la ronda siguiente
                    mensajes.append(LLMMessage(role='tool', tool_call_id=tc.id, name=tc.name,
                                               content=json.dumps({'error': 'argumentos inválidos',
                                                                   'detalle': str(e)[:500]},
                                                                  ensure_ascii=False)))
                    continue
                if tc.name in PREPARACIONES:
                    res.tipo, res.nombre, res.entrada = 'preparacion', tc.name, entrada
                    return res
                resultado = lecturas[tc.name](usuario, entrada)
                if tc.name in LECTURAS_TERMINALES:
                    res.tipo, res.nombre, res.entrada, res.resultado = 'lectura', tc.name, entrada, resultado
                    return res
                ultima_lectura = (tc.name, entrada, resultado)
                mensajes.append(LLMMessage(role='tool', tool_call_id=tc.id, name=tc.name,
                                           content=_para_modelo(tc.name, resultado)))
        # el modelo dejó de pedir tools (o se agotaron las rondas)
        if ultima_lectura:
            res.tipo = 'lectura'
            res.nombre, res.entrada, res.resultado = ultima_lectura
        elif hubo_args_invalidos:
            res.tipo = 'faltan_datos'
        return res
    finally:
        res.ms = int((time.monotonic() - t0) * 1000)
