"""
Interfaz abstracta de un canal de mensajería (A1).

Un canal sabe dos cosas: convertir lo que llega del proveedor en un
MensajeEntrante y responderle a un usuario (texto + botones). Todo lo demás
—vinculación, NLU, borradores, límites— vive en el núcleo y es común.
"""
from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel, Field


class Boton(BaseModel):
    """Botón inline: `texto` visible y `accion` que vuelve en el callback."""
    texto: str
    accion: str = Field(max_length=64)  # límite de callback_data de Telegram


class MensajeEntrante(BaseModel):
    """Lo único que el núcleo necesita saber de un mensaje, venga de donde venga."""
    canal: str
    id_externo: str                      # chat_id (Telegram) / wa_id (WhatsApp)
    texto: Optional[str] = None
    audio_file_id: Optional[str] = None  # id del archivo de voz en el proveedor
    foto_file_id: Optional[str] = None
    callback: Optional[str] = None       # accion de un botón pulsado
    callback_id: Optional[str] = None    # para ack (answerCallbackQuery)
    nombre_remitente: str = ''


class Canal(ABC):
    """Contrato mínimo. TelegramCanal hoy; WhatsAppCanal sobre la misma interfaz."""

    nombre = ''

    @abstractmethod
    def recibir(self, payload: dict) -> Optional[MensajeEntrante]:
        """Convierte el update crudo del proveedor en MensajeEntrante (o None si no aplica)."""

    @abstractmethod
    def responder(self, id_externo: str, texto: str, botones: Optional[list[Boton]] = None) -> Optional[int]:
        """Envía UN mensaje (B7: siempre una sola respuesta) con botones opcionales.
        Devuelve el id del mensaje enviado si el proveedor lo da (para poder
        desactivar sus botones después), o None."""

    def editar_botones(self, id_externo: str, mensaje_id: int, botones: Optional[list[Boton]] = None) -> None:
        """Reemplaza (o quita, con None) los botones de un mensaje ya enviado.
        Best-effort: un canal sin soporte lo ignora."""

    def descargar_archivo(self, file_id: str) -> bytes:  # audio/foto (A4)
        raise NotImplementedError
