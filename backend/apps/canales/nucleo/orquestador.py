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
import threading
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils.html import escape
from django.core.signing import TimestampSigner
from django.urls import reverse
from django.utils import timezone

from apps.agente.models import AgenteAccionLog
from apps.canales.base import Boton, Canal, MensajeEntrante
from apps.canales.models import BorradorAgente, VinculacionTelegram

from . import contexto as ctx
from . import servicios
from .interprete import FUERA_DE_ALCANCE, resolver

logger = logging.getLogger(__name__)

LIMITE_USUARIO_HORA = 60
LIMITE_EMPRESA_DIA = int(getattr(settings, 'CANALES_LIMITE_MENSAJES_EMPRESA_DIA', 1000))
LIMITE_TOKENS_EMPRESA_DIA = int(getattr(settings, 'CANALES_LIMITE_TOKENS_EMPRESA_DIA', 300_000))

SERVICIOS_PREPARACION = {
    'preparar_cotizacion': servicios.preparar_cotizacion,
    'preparar_venta': servicios.preparar_venta,
    'convertir_cotizacion_en_venta': servicios.convertir_cotizacion_en_venta,
    'preparar_cobro': servicios.preparar_cobro,
    'cambiar_estado_operativo': servicios.cambiar_estado_operativo,
}

MSG_NO_VINCULADO = (
    'Hola 👋 Este es el asistente del ERP. Para usarlo, entra al ERP → '
    'Configuración → «Vincular Telegram» y abre el enlace que te da. '
    'Hasta entonces no puedo atenderte por aquí.'
)
MSG_SOLO_LECTURA = 'Tu rol es de solo lectura: puedo darte información, pero no crear ni cambiar nada.'


def esc(v):
    """REVIEW_BOT #13 — parse_mode=HTML: un cliente llamado «<b>Acme» no debe
    romper el sendMessage."""
    return escape(str(v))


class _CanalConMemoria:
    """Envuelve el canal para que cada respuesta del bot quede en la memoria
    corta del chat (fix V2 punto 3). Todo lo demás pasa directo al canal."""

    def __init__(self, canal, usuario, id_externo):
        self._canal, self._usuario, self._id_externo = canal, usuario, id_externo

    def responder(self, id_externo, texto, botones=None):
        try:
            ctx.guardar_mensaje(self._usuario, self._canal.nombre, self._id_externo,
                                'assistant', texto)
        except Exception:
            logger.exception('no se pudo guardar la respuesta del bot en el historial')
        return self._canal.responder(id_externo, texto, botones=botones)

    def __getattr__(self, atributo):
        return getattr(self._canal, atributo)


class _Escribiendo:
    """«escribiendo…» mientras el LLM procesa (A1): la indicación de Telegram
    dura ~5 s, así que se renueva cada 4 s hasta que haya respuesta."""

    INTERVALO = 4

    def __init__(self, canal, id_externo):
        self._canal, self._id_externo = canal, id_externo
        self._alto = threading.Event()
        self._hilo = None

    def __enter__(self):
        if not hasattr(self._canal, 'enviar_accion'):
            return self

        def _latir():
            while not self._alto.is_set():
                try:
                    self._canal.enviar_accion(self._id_externo, 'typing')
                except Exception:
                    logger.warning('sendChatAction falló', exc_info=True)
                self._alto.wait(self.INTERVALO)

        self._hilo = threading.Thread(target=_latir, daemon=True)
        self._hilo.start()
        return self

    def __exit__(self, *exc):
        self._alto.set()
        if self._hilo:
            self._hilo.join(timeout=0.5)


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
    # A1 — el bot registra UsoLLM igual que el asistente web (empresa, día,
    # modelo); antes el consumo del bot era invisible en la contabilidad
    if resp.tokens_entrada or resp.tokens_salida:
        try:
            from apps.ai_assistant.models import UsoLLM
            UsoLLM.registrar(usuario.empresa,
                             resp.modelo or getattr(settings, 'LLM_MODEL', ''),
                             resp.tokens_entrada, resp.tokens_salida)
        except Exception:
            logger.exception('no se pudo registrar UsoLLM del bot')


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


def _guardar_mensaje_bot_id(borrador, mensaje_id):
    """Recuerda qué mensaje del chat ofrece los botones de este borrador: si lo
    reemplaza otro, a ese mensaje se le quitan los botones, y un callback desde
    otro mensaje se detecta como desactualizado (fix V2 punto 4 + tanda 4)."""
    if isinstance(mensaje_id, int):
        borrador.mensaje_bot_id = mensaje_id
        borrador.save(update_fields=['mensaje_bot_id'])


def _resumen_payload(borrador):
    """Resumen para REENVIAR un borrador vigente (cotización/venta/conversión
    se recalculan en _responder_borrador; cobro y estado, desde su payload)."""
    if borrador.tipo in ('cotizacion', 'venta', 'conversion_venta'):
        return None
    p = borrador.payload or {}
    if borrador.tipo == 'cobro':
        return (f'💰 <b>Cobro</b> de {esc(p.get("monto"))} ({esc(p.get("metodo_pago"))}) '
                f'— venta {esc(p.get("venta_numero"))}')
    return f'🚚 Venta <b>{esc(p.get("venta_numero"))}</b> → {esc(p.get("nuevo_estado"))}'


def _responder_borrador(canal, id_externo, borrador, resumen=None, prefijo=''):
    """B7 — SIEMPRE un solo mensaje. Cotización con pendientes: resumen +
    la primera pregunta con sus opciones (máx. 3) + Cancelar. Sin pendientes:
    resumen + Confirmar/Editar/Cancelar."""
    if borrador.tipo in ('cotizacion', 'venta', 'conversion_venta'):
        resumen = {'cotizacion': servicios.resumen_cotizacion,
                   'venta': servicios.resumen_venta,
                   'conversion_venta': servicios.resumen_conversion}[borrador.tipo](borrador.payload)
        pregunta = servicios.pregunta_pendiente(borrador.payload, borrador.id)
        if pregunta:
            texto, opciones = pregunta
            botones = [Boton(texto=t[:60], accion=a) for t, a in opciones]
            botones.append(Boton(texto='❌ Cancelar', accion=f'b:{borrador.id}:no'))
            mid = canal.responder(id_externo, f'{prefijo}{resumen}\n\n{texto}', botones=botones)
            _guardar_mensaje_bot_id(borrador, mid)
            return
    mid = canal.responder(
        id_externo,
        f'{prefijo}{resumen}\n\n¿Confirmo? (expira en 30 min)',
        botones=_botones_borrador(borrador),
    )
    _guardar_mensaje_bot_id(borrador, mid)


def _borrador_esperando_documento(usuario, id_externo):
    return BorradorAgente.objects.filter(
        usuario=usuario, empresa=usuario.empresa, estado='pendiente',
        tipo__in=('cotizacion', 'venta'),
        id_externo=id_externo, payload__cliente_estado='nuevo',
        payload__cliente_nuevo__documento=None,  # null en el JSON (no «clave ausente»)
    ).order_by('-created_at').first()


def _firma_payload(tipo, payload):
    """Huella del CONTENIDO del borrador (sin claves volátiles): dos payloads
    iguales son el mismo pedido, venga de un reenvío del usuario o de un
    reintento del proveedor."""
    import hashlib
    import json as _json
    base = {k: v for k, v in (payload or {}).items() if k not in ('en_edicion', 'mensaje_bot_id')}
    return hashlib.sha1(_json.dumps([tipo, base], sort_keys=True, default=str).encode()).hexdigest()


def _crear_borrador(canal, usuario, mensaje, tipo, payload):
    """fix V2 punto 4 + tanda 4 — UN solo borrador pendiente por chat y UNA
    mutación como máximo por pedido:

    - lock por chat (select_for_update): dos turnos simultáneos del mismo chat
      no crean dos borradores (evidencia de prod: ids 2 y 3 con 2 s de
      diferencia, hilos del webhook congelados por Cloud Run).
    - dedup por CONTENIDO: si el pendiente vigente tiene el mismo payload y es
      reciente (<2 min), se devuelve ese en vez de crear otro (el usuario
      reenvió el mismo mensaje al no ver respuesta).
    - si hay que crear, el anterior pasa a «reemplazado» y pierde sus botones.
    """
    from datetime import timedelta

    firma = _firma_payload(tipo, payload)
    desactivar = []
    with transaction.atomic():
        pendientes = list(BorradorAgente.objects.select_for_update().filter(
            usuario=usuario, empresa=usuario.empresa, estado='pendiente',
            id_externo=mensaje.id_externo))
        for viejo in pendientes:
            if (_firma_payload(viejo.tipo, viejo.payload) == firma
                    and viejo.created_at >= timezone.now() - timedelta(seconds=120)):
                logger.warning('borrador duplicado evitado (chat %s): mismo contenido que #%s',
                               mensaje.id_externo, viejo.id)
                return viejo
        for viejo in pendientes:
            viejo.marcar('reemplazado')
            mensaje_id = viejo.mensaje_bot_id or (viejo.payload or {}).get('mensaje_bot_id')
            if mensaje_id:
                desactivar.append(mensaje_id)
        nuevo = BorradorAgente.objects.create(
            empresa=usuario.empresa, usuario=usuario, tipo=tipo, payload=payload,
            canal=mensaje.canal, id_externo=mensaje.id_externo,
        )
    # fuera de la transacción: tocar Telegram no debe alargar el lock
    for mensaje_id in desactivar:
        try:
            canal.editar_botones(mensaje.id_externo, mensaje_id)
        except Exception:
            logger.exception('no se pudieron desactivar los botones (mensaje %s)', mensaje_id)
    return nuevo


def _link_pdf_firmado(cotizacion_id, empresa_id):
    """Link temporal (7 días) al PDF, sin sesión: se comparte por el chat.
    El token firma documento+empresa: manipular cualquiera de los dos → 403."""
    firma = TimestampSigner(salt='canales.pdf').sign(f'{cotizacion_id}:{empresa_id}')
    base = getattr(settings, 'API_BASE_URL', '') or 'https://erp.soldigem.com.pe'
    return f'{base}{reverse("canales:pdf_cotizacion")}?t={firma}'


# ── formateo de resultados de lectura ─────────────────────────────────────────

def _formatear_lectura(nombre, res):
    if 'error' in res:
        return res['error']
    if res.get('ambiguo'):
        lineas = [f'  • {esc(c["numero"])} — {esc(c["cliente"])} ({esc(c["total"])})' for c in res.get('candidatas', [])]
        if res.get('clientes'):
            lineas = [f'  • {esc(c["nombre"])} ({esc(c["documento"])})' for c in res['clientes']]
        return 'Encontré varios. ¿Cuál es?\n' + '\n'.join(lineas)
    if nombre == 'consultar_venta':
        s = 'S/' if res['moneda'] == 'PEN' else '$'
        pagado = '✅ PAGADA' if res['estado_pago'] == 'pagado' else f'🔶 Pendiente · saldo {s} {res["saldo"]}'
        return (f'Venta <b>{esc(res["numero"])}</b> — {esc(res["cliente"])}\n'
                f'Total {s} {res["total"]} · cobrado {s} {res["cobrado"]}\n'
                f'{pagado}\nOperativo: {res["estado_operativo"]}')
    if nombre == 'resumen_ventas':
        def soles(v):
            return f'S/ {Decimal(v):,.2f}'
        actual, anterior = Decimal(res['total_mes']), Decimal(res['total_mes_anterior'])
        if anterior > 0:
            delta = (actual - anterior) / anterior * 100
            comparacion = f'{"▲" if delta >= 0 else "▼"} {abs(delta):.0f}% vs mes anterior ({soles(anterior)})'
        else:
            comparacion = f'mes anterior: {soles(anterior)}'
        lineas = [f'📊 Ventas de {res["mes"]}: <b>{soles(actual)}</b> ({res["n_ventas"]} venta(s))',
                  comparacion]
        if res['top_clientes']:
            lineas.append('Top clientes:')
            lineas += [f'  {i}. {esc(c["nombre"])} — {soles(c["total"])}'
                       for i, c in enumerate(res['top_clientes'], 1)]
        lineas.append(f'Por cobrar: <b>{soles(res["por_cobrar"])}</b>')
        return '\n'.join(lineas)
    if nombre == 'ventas_detenidas':
        if not res['detenidas']:
            return '✅ No hay ventas detenidas. Todo al día.'
        cuerpo = '\n'.join(f'  • <b>{esc(d["numero"])}</b> {esc(d["cliente"])} — {esc(d["motivo"])}' for d in res['detenidas'])
        extra = f'\n(+{res["total"] - len(res["detenidas"])} más en el ERP)' if res['total'] > len(res['detenidas']) else ''
        return f'🔴 {res["total"]} venta(s) detenida(s):\n{cuerpo}{extra}'
    if nombre == 'buscar_producto':
        prods = res.get('productos') or []
        if not prods:
            return 'No encontré productos con ese nombre.'
        def linea(p):
            s = 'S/' if p.get('moneda', 'PEN') == 'PEN' else '$'
            costo = f' · últ. costo {s} {esc(p["ultimo_costo"])}' if p.get('ultimo_costo') else ''
            prov = f' ({esc(p["proveedor"])})' if p.get('proveedor') else ''
            return (f'  • <b>{esc(p["nombre"])}</b> ({esc(p["sku"])})\n'
                    f'    venta {s} {esc(p["precio_venta"])} · stock {esc(p["stock"])}{costo}{prov}')
        cabecera = 'No hay coincidencia exacta; ¿es alguno de estos?\n' if res.get('aproximado') else ''
        return cabecera + '\n'.join(linea(p) for p in prods)
    if nombre == 'buscar_cliente':
        if not res['clientes']:
            return 'No encontré clientes con ese nombre o documento.'
        return 'Clientes:\n' + '\n'.join(f'  • {esc(c["nombre"])} ({esc(c["documento"])})' for c in res['clientes'])
    return str(res)


# ── entrada principal ─────────────────────────────────────────────────────────

def procesar(canal: Canal, mensaje: MensajeEntrante):
    """Procesa un mensaje YA deduplicado. Siempre termina en UNA respuesta."""
    vinc = VinculacionTelegram.objects.filter(chat_id=int(mensaje.id_externo)).select_related(
        'usuario', 'usuario__empresa').first() if mensaje.id_externo.lstrip('-').isdigit() else None

    # REVIEW_BOT #10 — tope por chat_id ANTES de cualquier trabajo, también
    # para no vinculados y /start (fuerza bruta de códigos, ruido barato)
    hora = timezone.now().strftime('%Y%m%d%H')
    k_chat = f'canales:msj:chat{mensaje.id_externo}:{hora}'
    cache.get_or_set(k_chat, 0, 3700)
    try:
        if cache.incr(k_chat) > LIMITE_USUARIO_HORA:
            return  # silencio: responder también alimenta el abuso
    except ValueError:
        pass

    # /start CODIGO — canje de vinculación (A3)
    if mensaje.texto and mensaje.texto.startswith('/start'):
        return _manejar_start(canal, mensaje)

    if not vinc or not vinc.usuario.is_active or not vinc.usuario.empresa:
        canal.responder(mensaje.id_externo, MSG_NO_VINCULADO)
        return

    usuario = vinc.usuario
    # memoria corta (punto 3): las respuestas del bot quedan en el historial
    canal = _CanalConMemoria(canal, usuario, mensaje.id_externo)

    if mensaje.texto and mensaje.texto.split('@')[0] in ('/desvincular', '/stop'):
        vinc.delete()
        canal.responder(mensaje.id_externo, 'Listo, desvinculé este chat. Puedes volver a vincularlo desde el ERP.')
        return

    aviso = _excede_limites(usuario, mensaje.canal)
    if aviso:
        canal.responder(mensaje.id_externo, aviso)
        return

    # C3 — mensaje EDITADO: no se reinterpreta (duplicaba borradores); se avisa
    # UNA sola vez por mensaje editado (ediciones sucesivas no spamean).
    if mensaje.editado:
        if cache.add(f'canales:edit:{mensaje.id_externo}:{mensaje.mensaje_id}', 1, 3600):
            canal.responder(mensaje.id_externo,
                            'Vi que editaste el mensaje. Para cambios, escríbeme uno nuevo.')
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

    # REVIEW_BOT #11 — nadie dicta una cotización de 100 KB: tope antes del LLM
    texto = texto[:1000]

    # punto 3 — historial ANTES de guardar el mensaje actual (que va aparte)
    historial = ctx.historial_chat(usuario, mensaje.id_externo)
    ctx.guardar_mensaje(usuario, mensaje.canal, mensaje.id_externo, 'user', texto)

    # punto 1 — «Crear cliente nuevo» pidió RUC/DNI: este mensaje es la respuesta
    esperando = _borrador_esperando_documento(usuario, mensaje.id_externo)
    if esperando and not esperando.expirado and not texto.startswith('/'):
        if usuario.rol == 'solo_lectura':
            canal.responder(mensaje.id_externo, MSG_SOLO_LECTURA)
            return
        payload, aviso = servicios.aplicar_documento(usuario, esperando.payload, texto)
        # documento inválido (no quedó registrado): se pide de nuevo. Un aviso
        # CON documento (verificación APIS, nombre oficial) sigue al borrador.
        if (aviso and payload.get('cliente_estado') == 'nuevo'
                and not (payload.get('cliente_nuevo') or {}).get('documento')):
            canal.responder(mensaje.id_externo, aviso)
            return
        esperando.payload = payload
        esperando.save(update_fields=['payload'])
        _responder_borrador(canal, mensaje.id_externo, esperando,
                            prefijo=f'{aviso}\n\n' if aviso else '')
        return

    # punto 3 — cualquier borrador pendiente del chat es contexto: un mensaje
    # de seguimiento («cliente X», «que sean 6») lo completa o corrige en vez
    # de crear otro desde cero (ya no hace falta pulsar «Editar» antes)
    borrador_pendiente = BorradorAgente.objects.filter(
        usuario=usuario, estado='pendiente', id_externo=mensaje.id_externo,
    ).order_by('-created_at').first()
    if borrador_pendiente and borrador_pendiente.expirado:
        borrador_pendiente = None

    try:
        contexto = historial + ([ctx.contexto_borrador(borrador_pendiente)]
                                if borrador_pendiente else [])
        # bucle de tools compartido con eval_agente (máx. 3 rondas):
        # las lecturas ya vienen ejecutadas; las preparaciones, no.
        # «escribiendo…» mientras tanto (A1), renovado cada 4 s.
        with _Escribiendo(canal, mensaje.id_externo):
            r = resolver(usuario, texto, contexto or None)
        _registrar_tokens(usuario, mensaje.canal, r)
    except Exception:
        # severity ERROR con la causa (stack) — nunca el mensaje de ayuda
        logger.exception('intérprete falló (chat %s)', mensaje.id_externo)
        canal.responder(mensaje.id_externo, 'El asistente tuvo un problema. Inténtalo de nuevo en un momento.')
        return

    # A1 — todo fallback queda en el log con su causa (sin contenido del chat)
    if r.tipo == 'fuera':
        logger.warning('fallback ayuda (chat %s): %s · rondas=%s llamadas=%s len=%s',
                       mensaje.id_externo, r.motivo or 'sin herramienta',
                       r.rondas, [t for _, t in r.llamadas], len(texto))
        canal.responder(mensaje.id_externo, FUERA_DE_ALCANCE)
        return
    if r.tipo == 'faltan_datos':
        logger.warning('fallback faltan_datos (chat %s): %s · rondas=%s llamadas=%s',
                       mensaje.id_externo, r.motivo or 'argumentos inválidos',
                       r.rondas, [t for _, t in r.llamadas])
        canal.responder(mensaje.id_externo, 'Me faltan datos para eso. ¿Me das más detalle (cliente, producto, cantidad)?')
        return
    nombre, entrada = r.nombre, r.entrada

    # lecturas: para todos los roles
    if r.tipo == 'lectura':
        _log(usuario, nombre, entrada.model_dump(mode='json'), r.resultado)
        canal.responder(mensaje.id_externo, _formatear_lectura(nombre, r.resultado))
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

    b = res['borrador']
    # _crear_borrador reemplaza cualquier pendiente del chat (uno a la vez)
    borrador = _crear_borrador(canal, usuario, mensaje, b['tipo'], b['payload'])
    _responder_borrador(canal, mensaje.id_externo, borrador, resumen=b['resumen'])


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
        f'✅ Listo, {esc(vinc.usuario.nombre or vinc.usuario.email)}. Este chat quedó vinculado a '
        f'<b>{esc(vinc.usuario.empresa.nombre)}</b>.\n\n{FUERA_DE_ALCANCE}',
    )


def _traducir_error_confirmacion(e):
    """Errores de validación CONOCIDOS → frase en español con acción sugerida.
    Desconocidos → None (el caller responde «error interno» y loguea ERROR)."""
    texto = str(getattr(e, 'detail', None) or e).lower()
    if 'materia prima' in texto or 'insumo' in texto:
        return ('Uno de los productos está registrado como insumo y no se vende '
                'directo. Pídeme la venta de nuevo: lo incluiré como línea libre.')
    if 'cliente' in texto and ('válido' in texto or 'valido' in texto or 'empresa' in texto):
        return 'El cliente del borrador ya no es válido para tu empresa. Pídeme el documento de nuevo.'
    if 'stock' in texto:
        return 'No hay stock suficiente para una de las líneas. Ajusta la cantidad y vuelve a pedírmelo.'
    if 'producto' in texto and ('no existe' in texto or 'no pertenece' in texto):
        return 'Un producto del borrador ya no existe o no es de tu empresa. Pídeme el documento de nuevo.'
    return None


def _manejar_callback(canal, mensaje, usuario):
    # fix V2 punto 4 — idempotencia también por callback_query.id: si el
    # proveedor reenvía el mismo callback (reintento), no se procesa dos veces.
    if mensaje.callback_id and not cache.add(
            f'canales:cb:{mensaje.canal}:{mensaje.callback_id}', 1, 3600):
        return
    if hasattr(canal, 'ack_callback') and mensaje.callback_id:
        canal.ack_callback(mensaje.callback_id)
    partes = mensaje.callback.split(':')
    # REVIEW_BOT #12 — callback_data es forjable: id no numérico → fuera
    if len(partes) == 3 and not partes[1].isdigit():
        canal.responder(mensaje.id_externo, FUERA_DE_ALCANCE)
        return

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
        # REVIEW_BOT #5 — solo desde borrador: una aceptada/convertida no retrocede
        if cot.estado not in ('borrador', 'enviada'):
            canal.responder(mensaje.id_externo,
                            f'La cotización ya está {esc(cot.get_estado_display().lower())}; no la muevo.')
            return
        cot.estado = 'enviada'
        cot.save(update_fields=['estado'])
        _log(usuario, 'cotizacion_enviada', {'id': cot.id}, cot.numero)
        canal.responder(mensaje.id_externo, f'📨 {cot.numero} marcada como enviada.')
        return

    if partes[0] == 'r' and len(partes) in (3, 4) and partes[1].isdigit():
        return _manejar_resolucion(canal, mensaje, usuario, partes)

    if partes[0] != 'b' or len(partes) != 3:
        canal.responder(mensaje.id_externo, FUERA_DE_ALCANCE)
        return
    borrador = BorradorAgente.objects.filter(pk=partes[1], usuario=usuario, empresa=usuario.empresa).first()
    if not borrador:
        canal.responder(mensaje.id_externo, 'Ese borrador ya no existe.')
        return
    # tanda 4 — el botón debe venir del mensaje que MUESTRA este borrador. Si el
    # borrador sigue pendiente y el mensaje difiere, es el mismo contenido
    # reenviado (dedup): se procede. Pero un botón de un borrador REEMPLAZADO
    # (evidencia de prod: Confirmar sobre el id 4 ya desplazado por el 5) no se
    # queda en «ya está reemplazado»: se reenvía el borrador vigente.
    if (borrador.mensaje_bot_id and mensaje.mensaje_id
            and borrador.mensaje_bot_id != mensaje.mensaje_id and borrador.estado == 'pendiente'):
        logger.warning('callback desde un mensaje viejo del MISMO borrador %s (chat %s): se procede',
                       borrador.id, mensaje.id_externo)
    if borrador.estado == 'reemplazado':
        if isinstance(mensaje.mensaje_id, int):
            try:
                canal.editar_botones(mensaje.id_externo, mensaje.mensaje_id)
            except Exception:
                logger.exception('no se pudieron desactivar los botones del mensaje %s', mensaje.mensaje_id)
        vigente = BorradorAgente.objects.filter(
            usuario=usuario, empresa=usuario.empresa, estado='pendiente',
            id_externo=mensaje.id_externo).order_by('-created_at').first()
        if vigente and not vigente.expirado:
            _responder_borrador(canal, mensaje.id_externo, vigente,
                                resumen=_resumen_payload(vigente),
                                prefijo='Ese mensaje quedó desactualizado; este es el borrador vigente:\n\n')
        else:
            canal.responder(mensaje.id_externo,
                            'Ese borrador fue reemplazado y ya no hay uno vigente. Pídemelo de nuevo.')
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
        # REVIEW_BOT #3 — cada toque del botón es un update_id distinto: sin
        # lock, dos hilos confirmaban dos veces (cobro doble). El estado se
        # re-chequea CON select_for_update dentro de la transacción; el
        # perdedor del lock ve 'confirmado' y no ejecuta nada.
        class _YaResuelto(Exception):
            pass

        try:
            with transaction.atomic():
                bloqueado = BorradorAgente.objects.select_for_update().get(pk=borrador.pk)
                if bloqueado.estado != 'pendiente':
                    raise _YaResuelto(bloqueado.get_estado_display().lower())
                resultado = servicios.confirmar_borrador(bloqueado)
                bloqueado.documento_id = resultado['documento_id']
                bloqueado.documento_numero = resultado.get('numero', '')
                # marcar() solo persiste estado/resuelto_at: el documento va aparte
                bloqueado.save(update_fields=['documento_id', 'documento_numero'])
                bloqueado.marcar('confirmado')
        except _YaResuelto as ya:
            canal.responder(mensaje.id_externo, f'Ese borrador ya está {ya}.')
            return
        except ValueError as e:
            # nuestras validaciones: ya vienen como frase en español
            _log(usuario, f'confirmar_{borrador.tipo}', {'borrador': borrador.id}, str(e), ok=False)
            canal.responder(mensaje.id_externo, f'No pude crearlo: {esc(e)}')
            return
        except Exception as e:
            # caso real 29/10: el detalle crudo del serializer ({'detalles':
            # [ErrorDetail(...)]}) llegaba al chat. Se traduce lo conocido; lo
            # desconocido va al log con ERROR y el usuario recibe una frase.
            # La transacción revierte: el borrador SIGUE pendiente para reintentar.
            _log(usuario, f'confirmar_{borrador.tipo}', {'borrador': borrador.id}, str(e)[:300], ok=False)
            amable = _traducir_error_confirmacion(e)
            if amable:
                logger.warning('confirmar_%s rechazado (borrador %s): %s',
                               borrador.tipo, borrador.id, str(e)[:300])
            else:
                logger.exception('confirmar_%s falló sin traducción (borrador %s)',
                                 borrador.tipo, borrador.id)
                amable = ('No pude crear la venta por un error interno; '
                          'el equipo ya fue notificado. El borrador sigue pendiente: '
                          'puedes volver a tocar Confirmar en un momento.')
            canal.responder(mensaje.id_externo, amable)
            return
        borrador = bloqueado
        _log(usuario, f'confirmar_{borrador.tipo}', {'borrador': borrador.id}, resultado)
        if borrador.tipo == 'cotizacion':
            canal.responder(
                mensaje.id_externo,
                f'✅ Cotización <b>{resultado["numero"]}</b> creada.\n'
                f'📄 PDF: {_link_pdf_firmado(resultado["documento_id"], usuario.empresa_id)}',
                botones=[Boton(texto='📨 Marcar como enviada', accion=f'cot:{resultado["documento_id"]}:enviada')],
            )
        elif borrador.tipo == 'venta':
            canal.responder(mensaje.id_externo,
                            f'✅ Venta <b>{resultado["numero"]}</b> creada '
                            f'(total {resultado["total"]}).')
        elif borrador.tipo == 'conversion_venta':
            canal.responder(mensaje.id_externo,
                            f'✅ {resultado["cotizacion"]} convertida: venta '
                            f'<b>{resultado["numero"]}</b> (total {resultado["total"]}).')
        elif borrador.tipo == 'cobro':
            canal.responder(mensaje.id_externo,
                            f'✅ Cobro registrado en {resultado["numero"]}. '
                            f'Saldo restante: {resultado["saldo_restante"]}.')
        else:
            canal.responder(mensaje.id_externo,
                            f'✅ {resultado["numero"]} ahora está en <b>{resultado["estado"]}</b>.')
        return

    canal.responder(mensaje.id_externo, FUERA_DE_ALCANCE)


def _manejar_resolucion(canal, mensaje, usuario, partes):
    """r:<borrador>:c:<cliente> | r:<borrador>:cn | r:<borrador>:i<idx>:<producto|libre>.
    Solo acepta opciones que el servidor ofreció (aplicar_resolucion)."""
    if usuario.rol == 'solo_lectura':
        canal.responder(mensaje.id_externo, MSG_SOLO_LECTURA)
        return
    with transaction.atomic():
        borrador = BorradorAgente.objects.select_for_update().filter(
            pk=partes[1], usuario=usuario, empresa=usuario.empresa,
            tipo__in=('cotizacion', 'venta', 'conversion_venta')).first()
        if not borrador:
            canal.responder(mensaje.id_externo, 'Ese borrador ya no existe.')
            return
        if borrador.estado != 'pendiente':
            canal.responder(mensaje.id_externo, f'Ese borrador ya está {esc(borrador.get_estado_display().lower())}.')
            return
        if borrador.expirado:
            borrador.marcar('expirado')
            canal.responder(mensaje.id_externo, '⌛ Ese borrador expiró (30 min). Vuelve a pedírmelo.')
            return
        valor = partes[3] if len(partes) == 4 else ''
        payload, error = servicios.aplicar_resolucion(usuario, borrador.payload, partes[2], valor)
        if error:
            canal.responder(mensaje.id_externo, error)
            return
        borrador.payload = payload
        borrador.save(update_fields=['payload'])
    _responder_borrador(canal, mensaje.id_externo, borrador)


def _manejar_foto(canal, mensaje, usuario):
    """Foto suelta: si hay un cobro recién preparado/confirmado, es su comprobante."""
    import uuid
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage

    if usuario.rol == 'solo_lectura':
        canal.responder(mensaje.id_externo, MSG_SOLO_LECTURA)
        return
    try:
        contenido = canal.descargar_archivo(mensaje.foto_file_id)
    except Exception:
        logger.exception('descarga de foto falló')
        canal.responder(mensaje.id_externo, 'No pude descargar la foto. Inténtalo de nuevo.')
        return
    if len(contenido) > 10 * 1024 * 1024:  # mismo tope que validate_upload
        canal.responder(mensaje.id_externo, 'La foto pesa más de 10 MB; mándala más liviana.')
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
            if pago.comprobante:
                canal.responder(mensaje.id_externo,
                                f'El cobro de {esc(reciente.documento_numero)} ya tiene comprobante; no lo piso.')
                return
            # REVIEW_BOT #7 — update() y no save(): clean() compara el monto
            # contra el saldo YA reducido y revienta justo cuando el cobro
            # saldó la venta (el caso más común del piloto).
            PagoVenta.objects.filter(pk=pago.pk).update(comprobante=ruta)
            _log(usuario, 'foto_comprobante', {'pago': pago.id}, ruta)
            canal.responder(mensaje.id_externo, f'📎 Foto adjuntada como comprobante del cobro de {esc(reciente.documento_numero)}.')
            return
    _log(usuario, 'foto_sin_contexto', {}, ruta)
    canal.responder(mensaje.id_externo,
                    'Guardé la foto, pero no sé a qué cobro pertenece. '
                    'Regístrame primero el cobro y mándala de nuevo.')
