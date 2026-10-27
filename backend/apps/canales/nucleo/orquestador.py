"""
Orquestador: recibe un MensajeEntrante ya deduplicado y decide todo lo demás.

Reglas duras:
- No vinculado → UNA respuesta con instrucciones y silencio (A3).
- solo_lectura consulta; cualquier preparación/confirmación de escritura se
  rechaza (respeta 0.1).
- La IA solo PREPARA; el documento nace al pulsar Confirmar (B6).
- SIEMPRE una sola respuesta por mensaje, con botones si hay borrador (B7).
- 60 mensajes/usuario/hora + límites por empresa y canal (B9).
"""
import logging

import pydantic
from django.conf import settings
from django.core.cache import cache
from django.core.signing import TimestampSigner
from django.urls import reverse
from django.utils import timezone

from apps.agente.models import AgenteAccionLog
from apps.canales.base import Boton, Canal, MensajeEntrante
from apps.canales.models import BorradorAgente, VinculacionTelegram

from . import servicios
from .interprete import FUERA_DE_ALCANCE, interpretar

logger = logging.getLogger(__name__)

LIMITE_USUARIO_HORA = 60
LIMITE_EMPRESA_DIA = int(getattr(settings, 'CANALES_LIMITE_MENSAJES_EMPRESA_DIA', 1000))
LIMITE_TOKENS_EMPRESA_DIA = int(getattr(settings, 'CANALES_LIMITE_TOKENS_EMPRESA_DIA', 300_000))

SERVICIOS_LECTURA = {
    'buscar_cliente': servicios.buscar_cliente,
    'buscar_producto': servicios.buscar_producto,
    'consultar_venta': servicios.consultar_venta,
    'consultar_stock': servicios.consultar_stock,
    'ventas_detenidas': servicios.ventas_detenidas,
}
SERVICIOS_PREPARACION = {
    'preparar_cotizacion': servicios.preparar_cotizacion,
    'preparar_cobro': servicios.preparar_cobro,
    'cambiar_estado_operativo': servicios.cambiar_estado_operativo,
}

MSG_NO_VINCULADO = (
    'Hola 👋 Este es el asistente del ERP. Para usarlo, entra al ERP → '
    'Configuración → «Vincular Telegram» y abre el enlace que te da. '
    'Hasta entonces no puedo atenderte por aquí.'
)
MSG_SOLO_LECTURA = 'Tu rol es de solo lectura: puedo darte información, pero no crear ni cambiar nada.'


def _log(usuario, herramienta, argumentos, resultado_resumen, ok=True):
    AgenteAccionLog.objects.create(
        empresa=usuario.empresa, token=None, herramienta=f'canal:{herramienta}',
        argumentos=argumentos, resultado_resumen=str(resultado_resumen)[:300], ok=ok,
    )


# ── límites (B9): contadores en caché, clave por ventana ─────────────────────

def _excede_limites(usuario, canal_nombre):
    hora = timezone.now().strftime('%Y%m%d%H')
    dia = timezone.now().strftime('%Y%m%d')
    k_usuario = f'canales:msj:u{usuario.id}:{hora}'
    k_empresa = f'canales:msj:e{usuario.empresa_id}:{canal_nombre}:{dia}'
    n_u = cache.get_or_set(k_usuario, 0, 3700)
    n_e = cache.get_or_set(k_empresa, 0, 90000)
    if n_u >= LIMITE_USUARIO_HORA:
        return 'Llegaste al límite de 60 mensajes por hora. Dame un respiro ⏳'
    if n_e >= LIMITE_EMPRESA_DIA:
        return 'Tu empresa llegó al límite diario de mensajes del asistente.'
    try:
        cache.incr(k_usuario)
        cache.incr(k_empresa)
    except ValueError:
        pass
    return None


def _registrar_tokens(usuario, canal_nombre, resp):
    if not resp:
        return
    dia = timezone.now().strftime('%Y%m%d')
    k = f'canales:tok:e{usuario.empresa_id}:{canal_nombre}:{dia}'
    cache.get_or_set(k, 0, 90000)
    try:
        cache.incr(k, int(resp.tokens_entrada + resp.tokens_salida))
    except ValueError:
        pass


def _tokens_agotados(usuario, canal_nombre):
    dia = timezone.now().strftime('%Y%m%d')
    return (cache.get(f'canales:tok:e{usuario.empresa_id}:{canal_nombre}:{dia}') or 0) >= LIMITE_TOKENS_EMPRESA_DIA


# ── respuesta de borrador (B7) ────────────────────────────────────────────────

def _botones_borrador(borrador):
    return [
        Boton(texto='✅ Confirmar', accion=f'b:{borrador.id}:ok'),
        Boton(texto='✏️ Editar', accion=f'b:{borrador.id}:editar'),
        Boton(texto='❌ Cancelar', accion=f'b:{borrador.id}:no'),
    ]


def _crear_borrador(usuario, mensaje, tipo, payload):
    return BorradorAgente.objects.create(
        empresa=usuario.empresa, usuario=usuario, tipo=tipo, payload=payload,
        canal=mensaje.canal, id_externo=mensaje.id_externo,
    )


def _link_pdf_firmado(cotizacion_id):
    """Link temporal (72 h) al PDF, sin sesión: se comparte por el chat."""
    firma = TimestampSigner(salt='canales.pdf').sign(str(cotizacion_id))
    base = getattr(settings, 'API_BASE_URL', '') or 'https://api.soldigem.com.pe'
    return f'{base}{reverse("canales:pdf_cotizacion")}?t={firma}'


# ── formateo de resultados de lectura ─────────────────────────────────────────

def _formatear_lectura(nombre, res):
    if 'error' in res:
        return res['error']
    if res.get('ambiguo'):
        lineas = [f'  • {c["numero"]} — {c["cliente"]} ({c["total"]})' for c in res.get('candidatas', [])]
        if res.get('clientes'):
            lineas = [f'  • {c["nombre"]} ({c["documento"]})' for c in res['clientes']]
        return 'Encontré varios. ¿Cuál es?\n' + '\n'.join(lineas)
    if nombre == 'consultar_venta':
        s = 'S/' if res['moneda'] == 'PEN' else '$'
        pagado = '✅ PAGADA' if res['estado_pago'] == 'pagado' else f'🔶 Pendiente · saldo {s} {res["saldo"]}'
        return (f'Venta <b>{res["numero"]}</b> — {res["cliente"]}\n'
                f'Total {s} {res["total"]} · cobrado {s} {res["cobrado"]}\n'
                f'{pagado}\nOperativo: {res["estado_operativo"]}')
    if nombre == 'ventas_detenidas':
        if not res['detenidas']:
            return '✅ No hay ventas detenidas. Todo al día.'
        cuerpo = '\n'.join(f'  • <b>{d["numero"]}</b> {d["cliente"]} — {d["motivo"]}' for d in res['detenidas'])
        extra = f'\n(+{res["total"] - len(res["detenidas"])} más en el ERP)' if res['total'] > len(res['detenidas']) else ''
        return f'🔴 {res["total"]} venta(s) detenida(s):\n{cuerpo}{extra}'
    if nombre in ('buscar_producto', 'consultar_stock'):
        prods = res.get('productos') or res.get('stock') or []
        if not prods:
            return 'No encontré productos con ese nombre.'
        return 'Encontré:\n' + '\n'.join(
            f'  • {p["nombre"]} ({p["sku"]}) — S/ {p["precio_venta"]}'
            + (f' · stock {p["stock"]}' if p.get('stock') else '') for p in prods)
    if nombre == 'buscar_cliente':
        if not res['clientes']:
            return 'No encontré clientes con ese nombre o documento.'
        return 'Clientes:\n' + '\n'.join(f'  • {c["nombre"]} ({c["documento"]})' for c in res['clientes'])
    return str(res)


# ── entrada principal ─────────────────────────────────────────────────────────

def procesar(canal: Canal, mensaje: MensajeEntrante):
    """Procesa un mensaje YA deduplicado. Siempre termina en UNA respuesta."""
    vinc = VinculacionTelegram.objects.filter(chat_id=int(mensaje.id_externo)).select_related(
        'usuario', 'usuario__empresa').first() if mensaje.id_externo.lstrip('-').isdigit() else None

    # /start CODIGO — canje de vinculación (A3)
    if mensaje.texto and mensaje.texto.startswith('/start'):
        return _manejar_start(canal, mensaje)

    if not vinc or not vinc.usuario.is_active or not vinc.usuario.empresa:
        canal.responder(mensaje.id_externo, MSG_NO_VINCULADO)
        return

    usuario = vinc.usuario

    if mensaje.texto and mensaje.texto.split('@')[0] in ('/desvincular', '/stop'):
        vinc.delete()
        canal.responder(mensaje.id_externo, 'Listo, desvinculé este chat. Puedes volver a vincularlo desde el ERP.')
        return

    aviso = _excede_limites(usuario, mensaje.canal)
    if aviso:
        canal.responder(mensaje.id_externo, aviso)
        return

    # botones (callback) no gastan LLM
    if mensaje.callback:
        return _manejar_callback(canal, mensaje, usuario)

    if mensaje.texto and mensaje.texto.split('@')[0] in ('/ayuda', '/help', '/start'):
        canal.responder(mensaje.id_externo, FUERA_DE_ALCANCE)
        return

    texto = mensaje.texto

    # audio → texto (A4); la transcripción también es mockeable en tests
    if not texto and mensaje.audio_file_id:
        from apps.canales.transcripcion import transcribir
        try:
            audio = canal.descargar_archivo(mensaje.audio_file_id)
            texto = transcribir(audio)
            if not texto:
                canal.responder(mensaje.id_externo, 'No entendí el audio 🙉 ¿Me lo escribes?')
                return
        except Exception:
            logger.exception('transcripción falló')
            canal.responder(mensaje.id_externo, 'No pude procesar el audio. ¿Me lo escribes?')
            return

    # foto → comprobante del último cobro pendiente (A4)
    if not texto and mensaje.foto_file_id:
        return _manejar_foto(canal, mensaje, usuario)

    if not texto:
        canal.responder(mensaje.id_externo, FUERA_DE_ALCANCE)
        return

    if _tokens_agotados(usuario, mensaje.canal):
        canal.responder(mensaje.id_externo, 'Tu empresa agotó el presupuesto diario del asistente.')
        return

    # ¿es una corrección a un borrador pendiente en modo edición?
    borrador_en_edicion = BorradorAgente.objects.filter(
        usuario=usuario, estado='pendiente', id_externo=mensaje.id_externo,
        payload__en_edicion=True,
    ).order_by('-created_at').first()

    try:
        contexto = None
        if borrador_en_edicion and not borrador_en_edicion.expirado:
            from apps.ai_assistant.services.llm_client import LLMMessage
            contexto = [LLMMessage(
                role='user',
                content=('Borrador pendiente de tipo '
                         f'{borrador_en_edicion.tipo}: {borrador_en_edicion.payload}. '
                         'El siguiente mensaje lo corrige: vuelve a llamar la herramienta '
                         'correspondiente con los datos corregidos completos.'),
            )]
        nombre, entrada, resp = interpretar(texto, contexto)
        _registrar_tokens(usuario, mensaje.canal, resp)
    except pydantic.ValidationError:
        logger.exception('argumentos inválidos del LLM')
        canal.responder(mensaje.id_externo, 'Me faltan datos para eso. ¿Me das más detalle (cliente, producto, cantidad)?')
        return
    except Exception:
        logger.exception('intérprete falló')
        canal.responder(mensaje.id_externo, 'El asistente tuvo un problema. Inténtalo de nuevo en un momento.')
        return

    if nombre is None:
        canal.responder(mensaje.id_externo, FUERA_DE_ALCANCE)
        return

    # lecturas: para todos los roles
    if nombre in SERVICIOS_LECTURA:
        res = SERVICIOS_LECTURA[nombre](usuario, entrada)
        _log(usuario, nombre, entrada.model_dump(mode='json'), res)
        canal.responder(mensaje.id_externo, _formatear_lectura(nombre, res))
        return

    # preparaciones: exigen rol de escritura (0.1 también aplica al bot)
    if usuario.rol == 'solo_lectura':
        canal.responder(mensaje.id_externo, MSG_SOLO_LECTURA)
        return

    res = SERVICIOS_PREPARACION[nombre](usuario, entrada)
    _log(usuario, nombre, entrada.model_dump(mode='json'), res.get('borrador', res).get('resumen', res) if isinstance(res, dict) else res)
    if 'error' in res:
        canal.responder(mensaje.id_externo, res['error'])
        return
    if res.get('ambiguo'):
        canal.responder(mensaje.id_externo, _formatear_lectura(nombre, res))
        return

    # al preparar uno nuevo, el anterior en edición queda cancelado (uno a la vez)
    if borrador_en_edicion:
        borrador_en_edicion.marcar('cancelado')
    b = res['borrador']
    borrador = _crear_borrador(usuario, mensaje, b['tipo'], b['payload'])
    canal.responder(
        mensaje.id_externo,
        b['resumen'] + '\n\n¿Confirmo? (expira en 30 min)',
        botones=_botones_borrador(borrador),
    )


# ── /start, callbacks, foto ──────────────────────────────────────────────────

def _manejar_start(canal, mensaje):
    partes = (mensaje.texto or '').split(maxsplit=1)
    codigo = partes[1].strip().upper() if len(partes) > 1 else ''
    if not codigo:
        canal.responder(mensaje.id_externo, MSG_NO_VINCULADO)
        return
    vinc = VinculacionTelegram.objects.filter(codigo=codigo).select_related('usuario').first()
    if not vinc or vinc.vinculado or not vinc.codigo_vigente:
        canal.responder(mensaje.id_externo, 'Ese código no es válido o ya venció. Genera uno nuevo desde el ERP (dura 10 min).')
        return
    # un chat ↔ un usuario: si este chat estaba ligado a otro usuario, se libera
    VinculacionTelegram.objects.filter(chat_id=int(mensaje.id_externo)).exclude(pk=vinc.pk).delete()
    vinc.chat_id = int(mensaje.id_externo)
    vinc.vinculado_at = timezone.now()
    vinc.codigo_expira = timezone.now()  # el código ya no sirve
    vinc.save(update_fields=['chat_id', 'vinculado_at', 'codigo_expira'])
    _log(vinc.usuario, 'vincular', {}, f'chat {mensaje.id_externo}')
    canal.responder(
        mensaje.id_externo,
        f'✅ Listo, {vinc.usuario.nombre or vinc.usuario.email}. Este chat quedó vinculado a '
        f'<b>{vinc.usuario.empresa.nombre}</b>.\n\n{FUERA_DE_ALCANCE}',
    )


def _manejar_callback(canal, mensaje, usuario):
    if hasattr(canal, 'ack_callback') and mensaje.callback_id:
        canal.ack_callback(mensaje.callback_id)
    partes = mensaje.callback.split(':')

    # cot:<id>:enviada — marcar cotización como enviada tras compartir el PDF
    if partes[0] == 'cot' and len(partes) == 3 and partes[2] == 'enviada':
        from apps.cotizaciones.models import Cotizacion
        cot = Cotizacion.objects.filter(pk=partes[1], empresa=usuario.empresa).first()
        if not cot:
            canal.responder(mensaje.id_externo, 'No encontré esa cotización.')
            return
        if usuario.rol == 'solo_lectura':
            canal.responder(mensaje.id_externo, MSG_SOLO_LECTURA)
            return
        cot.estado = 'enviada'
        cot.save(update_fields=['estado'])
        _log(usuario, 'cotizacion_enviada', {'id': cot.id}, cot.numero)
        canal.responder(mensaje.id_externo, f'📨 {cot.numero} marcada como enviada.')
        return

    if partes[0] != 'b' or len(partes) != 3:
        canal.responder(mensaje.id_externo, FUERA_DE_ALCANCE)
        return
    borrador = BorradorAgente.objects.filter(pk=partes[1], usuario=usuario, empresa=usuario.empresa).first()
    if not borrador:
        canal.responder(mensaje.id_externo, 'Ese borrador ya no existe.')
        return
    if borrador.estado != 'pendiente':
        canal.responder(mensaje.id_externo, f'Ese borrador ya está {borrador.get_estado_display().lower()}.')
        return
    if borrador.expirado:
        borrador.marcar('expirado')
        canal.responder(mensaje.id_externo, '⌛ Ese borrador expiró (30 min). Vuelve a pedírmelo.')
        return

    accion = partes[2]
    if accion == 'no':
        borrador.marcar('cancelado')
        _log(usuario, 'borrador_cancelado', {'id': borrador.id}, borrador.tipo)
        canal.responder(mensaje.id_externo, 'Cancelado. No se creó nada.')
        return

    if accion == 'editar':
        borrador.payload['en_edicion'] = True
        borrador.save(update_fields=['payload'])
        canal.responder(mensaje.id_externo, 'Dime qué corrijo (p. ej. «que sean 5 unidades» o «mejor al cliente Acme»).')
        return

    if accion == 'ok':
        if usuario.rol == 'solo_lectura':
            canal.responder(mensaje.id_externo, MSG_SOLO_LECTURA)
            return
        try:
            resultado = servicios.confirmar_borrador(borrador)
        except Exception as e:
            logger.exception('confirmar_borrador falló')
            _log(usuario, f'confirmar_{borrador.tipo}', {'borrador': borrador.id}, str(e), ok=False)
            canal.responder(mensaje.id_externo, f'No pude crearlo: {e}')
            return
        borrador.documento_id = resultado['documento_id']
        borrador.documento_numero = resultado.get('numero', '')
        borrador.marcar('confirmado')
        _log(usuario, f'confirmar_{borrador.tipo}', {'borrador': borrador.id}, resultado)
        if borrador.tipo == 'cotizacion':
            canal.responder(
                mensaje.id_externo,
                f'✅ Cotización <b>{resultado["numero"]}</b> creada.\n'
                f'📄 PDF: {_link_pdf_firmado(resultado["documento_id"])}',
                botones=[Boton(texto='📨 Marcar como enviada', accion=f'cot:{resultado["documento_id"]}:enviada')],
            )
        elif borrador.tipo == 'cobro':
            canal.responder(mensaje.id_externo,
                            f'✅ Cobro registrado en {resultado["numero"]}. '
                            f'Saldo restante: {resultado["saldo_restante"]}.')
        else:
            canal.responder(mensaje.id_externo,
                            f'✅ {resultado["numero"]} ahora está en <b>{resultado["estado"]}</b>.')
        return

    canal.responder(mensaje.id_externo, FUERA_DE_ALCANCE)


def _manejar_foto(canal, mensaje, usuario):
    """Foto suelta: si hay un cobro recién preparado/confirmado, es su comprobante."""
    import uuid
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage

    try:
        contenido = canal.descargar_archivo(mensaje.foto_file_id)
    except Exception:
        logger.exception('descarga de foto falló')
        canal.responder(mensaje.id_externo, 'No pude descargar la foto. Inténtalo de nuevo.')
        return
    if usuario.rol == 'solo_lectura':
        canal.responder(mensaje.id_externo, MSG_SOLO_LECTURA)
        return
    ruta = default_storage.save(
        f'canales/empresa_{usuario.empresa_id}/{uuid.uuid4().hex}.jpg', ContentFile(contenido),
    )
    # contexto: el último cobro confirmado hace poco por este chat
    reciente = BorradorAgente.objects.filter(
        usuario=usuario, id_externo=mensaje.id_externo, tipo='cobro', estado='confirmado',
        resuelto_at__gte=timezone.now() - BorradorAgente.VIGENCIA,
    ).order_by('-resuelto_at').first()
    if reciente and reciente.documento_id:
        from apps.ventas.models import PagoVenta
        pago = PagoVenta.objects.filter(pk=reciente.documento_id, venta__empresa=usuario.empresa).first()
        if pago:
            pago.comprobante.name = ruta
            pago.save(update_fields=['comprobante'])
            _log(usuario, 'foto_comprobante', {'pago': pago.id}, ruta)
            canal.responder(mensaje.id_externo, f'📎 Foto adjuntada como comprobante del cobro de {reciente.documento_numero}.')
            return
    _log(usuario, 'foto_sin_contexto', {}, ruta)
    canal.responder(mensaje.id_externo,
                    'Guardé la foto, pero no sé a qué cobro pertenece. '
                    'Regístrame primero el cobro y mándala de nuevo.')
