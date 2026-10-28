"""
Memoria corta del chat (fix V2 punto 3), compartida por el orquestador y el eval.

El agente recibe: los últimos N mensajes del chat (N = CANALES_HISTORIAL_MENSAJES,
con tope de caracteres como proxy de tokens) y, si existe, el borrador pendiente
en versión compacta. Con eso «Cliente Uhman» o «cámbiale la cantidad a 6»
completan o corrigen el borrador en vez de perderse o crear ítems basura.
"""
from django.conf import settings

from apps.ai_assistant.services.llm_client import LLMMessage

# tope por mensaje: un historial es contexto, no un archivo
MAX_CHARS_MENSAJE = 600


def guardar_mensaje(usuario, canal_nombre, id_externo, rol, texto):
    from apps.canales.models import MensajeConversacion
    if not (texto or '').strip():
        return
    MensajeConversacion.objects.create(
        empresa=usuario.empresa, usuario=usuario, canal=canal_nombre,
        id_externo=id_externo, rol=rol, texto=texto[:2000],
    )


def historial_chat(usuario, id_externo):
    """→ [LLMMessage] de los últimos N mensajes del chat, en orden cronológico,
    recortados al tope global de caracteres (los más recientes pesan más)."""
    from apps.canales.models import MensajeConversacion
    n = int(getattr(settings, 'CANALES_HISTORIAL_MENSAJES', 10))
    max_chars = int(getattr(settings, 'CANALES_HISTORIAL_MAX_CHARS', 4000))
    if n <= 0:
        return []
    filas = list(MensajeConversacion.objects.filter(
        usuario=usuario, id_externo=id_externo,
    ).order_by('-created_at')[:n])
    mensajes, usados = [], 0
    for f in filas:  # del más nuevo al más viejo: lo reciente entra primero
        texto = f.texto[:MAX_CHARS_MENSAJE]
        if usados + len(texto) > max_chars:
            break
        usados += len(texto)
        mensajes.append(LLMMessage(role=f.rol, content=texto))
    mensajes.reverse()
    return mensajes


def payload_compacto(tipo, payload):
    """Versión del payload para el prompt: sin opciones, avisos ni claves de
    trabajo; solo lo que el modelo necesita para reconstruirlo completo."""
    if tipo != 'cotizacion':
        return {k: v for k, v in payload.items() if k != 'en_edicion'}
    return {
        'cliente': payload.get('cliente_nombre') or payload.get('cliente_texto') or '(por definir)',
        'moneda': payload.get('moneda'),
        'precios_incluyen_igv': payload.get('precios_incluyen_igv', False),
        'items': [
            {'descripcion': d.get('descripcion') or d.get('texto'),
             'cantidad': d.get('cantidad'),
             'precio_unitario': d.get('precio_unitario')}
            for d in payload.get('detalles', [])
        ],
    }


def contexto_borrador(borrador):
    """→ LLMMessage que ancla el borrador pendiente: el mensaje siguiente suele
    completarlo o corregirlo; el modelo debe re-llamar la tool con TODO."""
    return LLMMessage(
        role='user',
        content=(f'[contexto del sistema] Hay un borrador pendiente de tipo {borrador.tipo}: '
                 f'{payload_compacto(borrador.tipo, borrador.payload)}. '
                 'Si el siguiente mensaje lo completa o corrige (cliente, cantidades, '
                 'quitar o agregar ítems), vuelve a llamar la herramienta correspondiente '
                 'con TODOS los datos completos ya corregidos: los del borrador más lo '
                 'nuevo. Si pide otra cosa, atiende lo nuevo e ignora el borrador.'),
    )


def construir_contexto(usuario, id_externo, borrador=None):
    """Historial + borrador pendiente → lista para interprete.resolver()."""
    contexto = historial_chat(usuario, id_externo)
    if borrador is not None:
        contexto.append(contexto_borrador(borrador))
    return contexto
