"""
TelegramCanal (A1/A4): parseo de updates y envío por la Bot API.

Todo el tráfico saliente pasa por `requests` hacia api.telegram.org; en tests
se mockea este módulo (NUNCA se llama a Telegram desde la suite).
"""
import logging
from typing import Optional

import requests
from django.conf import settings

from .base import Boton, Canal, MensajeEntrante

logger = logging.getLogger(__name__)

_TIMEOUT = 15


def _api(metodo: str) -> str:
    return f'https://api.telegram.org/bot{settings.TG_BOT_TOKEN}/{metodo}'


class TelegramCanal(Canal):
    nombre = 'telegram'

    # ── entrada ──────────────────────────────────────────────────────────────
    def recibir(self, payload: dict) -> Optional[MensajeEntrante]:
        if 'callback_query' in payload:
            cb = payload['callback_query']
            chat = cb.get('message', {}).get('chat', {})
            return MensajeEntrante(
                canal=self.nombre,
                id_externo=str(chat.get('id', cb.get('from', {}).get('id', ''))),
                callback=cb.get('data', ''),
                callback_id=str(cb.get('id', '')),
                nombre_remitente=cb.get('from', {}).get('first_name', ''),
            )
        # fix V2 punto 4 / C3 — un mensaje EDITADO llega como update nuevo
        # (update_id distinto), así que la idempotencia por update_id no lo
        # frena: tratarlo como mensaje volvía a procesar el texto completo y
        # duplicaba borradores. No se reinterpreta: el orquestador avisa UNA
        # vez («escríbeme uno nuevo») y nada más.
        editado = payload.get('edited_message')
        if editado:
            return MensajeEntrante(
                canal=self.nombre,
                id_externo=str(editado.get('chat', {}).get('id', '')),
                editado=True,
                mensaje_id=editado.get('message_id'),
                nombre_remitente=editado.get('from', {}).get('first_name', ''),
            )
        msg = payload.get('message')
        if not msg:
            return None
        chat_id = str(msg.get('chat', {}).get('id', ''))
        voz = msg.get('voice') or msg.get('audio')
        fotos = msg.get('photo') or []
        return MensajeEntrante(
            canal=self.nombre,
            id_externo=chat_id,
            texto=msg.get('text') or msg.get('caption'),
            audio_file_id=voz.get('file_id') if voz else None,
            # Telegram manda la foto en varias resoluciones; la última es la mayor
            foto_file_id=fotos[-1]['file_id'] if fotos else None,
            nombre_remitente=msg.get('from', {}).get('first_name', ''),
        )

    # ── salida ───────────────────────────────────────────────────────────────
    def responder(self, id_externo, texto, botones=None):
        data = {'chat_id': id_externo, 'text': texto, 'parse_mode': 'HTML'}
        if botones:
            data['reply_markup'] = {
                'inline_keyboard': [[{'text': b.texto, 'callback_data': b.accion}] for b in botones],
            }
        try:
            r = requests.post(_api('sendMessage'), json=data, timeout=_TIMEOUT)
            if not r.ok:
                logger.error('telegram sendMessage %s: %s', r.status_code, r.text[:200])
                return None
            # message_id: para poder desactivar los botones si el borrador se reemplaza
            mid = (r.json() or {}).get('result', {}).get('message_id')
            return mid if isinstance(mid, int) else None
        except (requests.RequestException, ValueError):
            logger.exception('telegram sendMessage falló (chat %s)', id_externo)
            return None

    def editar_botones(self, id_externo, mensaje_id, botones=None):
        """Quita (o cambia) los botones de un mensaje viejo: un borrador
        reemplazado no debe seguir ofreciendo «Confirmar». Best-effort."""
        markup = {'inline_keyboard': [[{'text': b.texto, 'callback_data': b.accion}]
                                      for b in botones]} if botones else {'inline_keyboard': []}
        try:
            requests.post(_api('editMessageReplyMarkup'),
                          json={'chat_id': id_externo, 'message_id': mensaje_id,
                                'reply_markup': markup}, timeout=_TIMEOUT)
        except requests.RequestException:
            logger.exception('telegram editMessageReplyMarkup falló (chat %s)', id_externo)

    def enviar_accion(self, id_externo, accion='typing'):
        """sendChatAction: «escribiendo…» mientras el LLM piensa (A1). La
        indicación dura ~5 s, así que el orquestador la renueva cada 4 s."""
        try:
            requests.post(_api('sendChatAction'),
                          json={'chat_id': id_externo, 'action': accion}, timeout=_TIMEOUT)
        except requests.RequestException:
            logger.warning('telegram sendChatAction falló (chat %s)', id_externo)

    def ack_callback(self, callback_id: str):
        """Quita el relojito del botón pulsado."""
        try:
            requests.post(_api('answerCallbackQuery'), json={'callback_query_id': callback_id}, timeout=_TIMEOUT)
        except requests.RequestException:
            logger.exception('telegram answerCallbackQuery falló')

    def descargar_archivo(self, file_id):
        r = requests.get(_api('getFile'), params={'file_id': file_id}, timeout=_TIMEOUT)
        r.raise_for_status()
        ruta = r.json()['result']['file_path']
        r = requests.get(
            f'https://api.telegram.org/file/bot{settings.TG_BOT_TOKEN}/{ruta}', timeout=60,
        )
        r.raise_for_status()
        return r.content
