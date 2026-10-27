"""
Intérprete (B5/B8): un mensaje de texto → (servicio, parámetros) usando la
capa LLM existente (ai_assistant.services.llm_client) con tool-calling.

Es un bot de TAREAS: si el modelo no elige herramienta, la respuesta es fija
(B8), nunca conversación abierta.
"""
import logging

from apps.ai_assistant.services.llm_client import LLMMessage, ToolSpec, get_llm_client
from apps.ai_assistant.services.tool_specs import schema_de_pydantic

from . import esquemas as E

logger = logging.getLogger(__name__)

# servicio → (esquema pydantic, descripción para el modelo)
CATALOGO = {
    'buscar_cliente': (E.BuscarCliente, 'Busca un cliente por alias, parte del nombre o RUC/DNI.'),
    'buscar_producto': (E.BuscarProducto, 'Busca un producto por nombre aproximado o SKU (tolera errores de tipeo).'),
    'preparar_cotizacion': (E.PrepararCotizacion, 'Prepara una cotización (borrador que la persona confirma). Usa cliente_query con el nombre que dio el usuario y un ítem por producto con cantidad.'),
    'preparar_cobro': (E.PrepararCobro, 'Prepara el registro de un cobro/pago recibido de un cliente. Si no dan monto, se cobra el saldo completo.'),
    'cambiar_estado_operativo': (E.CambiarEstadoOperativo, 'Prepara el cambio de estado operativo de una venta (comprado, recibido, entregado, facturado…). "Ya se entregó" → entregado.'),
    'consultar_venta': (E.ConsultarVenta, 'Consulta una venta: estado de pago, cuánto se cobró y saldo pendiente. Sirve para "¿ya pagó X?".'),
    'consultar_stock': (E.ConsultarStock, 'Consulta el stock disponible de un producto.'),
    'ventas_detenidas': (E.VentasDetenidas, 'Lista las ventas detenidas/atrasadas y por qué.'),
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


def interpretar(texto: str, historial: list[LLMMessage] | None = None):
    """→ (nombre_servicio, entrada_pydantic) | (None, None) si está fuera de alcance.

    Lanza LLMNoConfigurado/errores del proveedor hacia el orquestador (que
    responde con un mensaje de error honesto).
    """
    cliente = get_llm_client()
    mensajes = list(historial or []) + [LLMMessage(role='user', content=texto)]
    resp = cliente.chat(system=SYSTEM, messages=mensajes, tools=_tools(), temperature=0.0)
    if not resp.tool_calls:
        return None, None, resp
    llamada = resp.tool_calls[0]
    esquema, _ = CATALOGO.get(llamada.name, (None, None))
    if esquema is None:
        logger.warning('LLM eligió herramienta desconocida: %s', llamada.name)
        return None, None, resp
    entrada = esquema.model_validate(llamada.arguments)  # pydantic valida/convierte
    return llamada.name, entrada, resp
