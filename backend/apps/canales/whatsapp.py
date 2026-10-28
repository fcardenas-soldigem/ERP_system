"""
WhatsAppCanal — esqueleto (A1). WhatsApp llega DESPUÉS del piloto de Telegram,
sobre esta misma interfaz; el núcleo (orquestador/servicios) no cambia.
"""
from typing import Optional

from .base import Boton, Canal, MensajeEntrante


class WhatsAppCanal(Canal):
    nombre = 'whatsapp'

    def recibir(self, payload: dict) -> Optional[MensajeEntrante]:
        # TODO(whatsapp): mapear el webhook de WhatsApp Cloud API
        # (entry[].changes[].value.messages[]) a MensajeEntrante: text.body,
        # audio.id, image.id, interactive.button_reply.id → callback.
        raise NotImplementedError('WhatsApp llega después del piloto de Telegram')

    def responder(self, id_externo: str, texto: str, botones: Optional[list[Boton]] = None) -> None:
        # TODO(whatsapp): POST /{phone_number_id}/messages con type=interactive
        # (reply buttons, máx. 3) o type=text. Requiere plantillas aprobadas
        # fuera de la ventana de 24 h.
        raise NotImplementedError('WhatsApp llega después del piloto de Telegram')

    def descargar_archivo(self, file_id: str) -> bytes:
        # TODO(whatsapp): GET /{media_id} → url firmada → descarga con bearer.
        raise NotImplementedError('WhatsApp llega después del piloto de Telegram')
