"""
Orquestador del chat: historial en BD + bucle de function calling sobre `LLMClient`.

Flujo de `enviar(contenido)`:
  1. guarda el mensaje del usuario (Message)
  2. arma el contexto: system prompt del perfil + últimas N interacciones de la BD
  3. llama al modelo; si pide tools, las ejecuta en el servidor (empresa/usuario del
     ejecutor, nunca del modelo), añade los resultados y vuelve a llamar (máx. 5 rondas)
  4. guarda la respuesta (Message) y registra tokens en UsoLLM (empresa, día, modelo)

`ejecutar_tools=False` (eval): registra las tool calls de la primera ronda sin
ejecutarlas ni escribir en BD más allá de la conversación dada.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from ..models import Conversation, Message, UsoLLM
from .llm_client import LLMClient, LLMMessage, LLMNoConfigurado, LLMResponse, get_llm_client
from .perfiles import Perfil, get_perfil

logger = logging.getLogger(__name__)

MAX_RONDAS_TOOLS = 5
MAX_CHARS_RESULTADO_TOOL = 12_000


@dataclass
class TrazaTool:
    name: str
    arguments: dict
    ronda: int
    ejecutada: bool
    duracion_ms: int = 0


@dataclass
class Traza:
    tool_calls: list[TrazaTool] = field(default_factory=list)
    tokens_entrada: int = 0
    tokens_salida: int = 0
    rondas: int = 0
    latencia_primera_ms: int = 0
    latencia_total_ms: int = 0
    modelo: str = ''


def nuevo_thread_id() -> str:
    return f'conv_{uuid.uuid4().hex}'


def crear_conversacion(user, perfil: Perfil, titulo: str | None = None) -> Conversation:
    return Conversation.objects.create(
        empresa=user.empresa, usuario=user, perfil=perfil.clave,
        thread_id=nuevo_thread_id(), title=titulo or perfil.titulo,
    )


def _json_seguro(obj) -> str:
    try:
        s = json.dumps(obj, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        s = json.dumps({'result': str(obj)}, ensure_ascii=False)
    if len(s) > MAX_CHARS_RESULTADO_TOOL:
        s = s[:MAX_CHARS_RESULTADO_TOOL] + '…(truncado)'
    return s


class AsistenteChat:
    def __init__(self, conversation: Conversation, perfil: Perfil | None = None,
                 cliente: LLMClient | None = None, ejecutar_tools: bool = True):
        self.conversation = conversation
        self.user = conversation.usuario
        self.perfil = perfil or get_perfil(conversation.perfil)
        self.cliente = cliente or get_llm_client()
        self.ejecutar_tools = ejecutar_tools
        self.traza = Traza(modelo=self.cliente.modelo)
        self._ejecutor = None

    # ── API ───────────────────────────────────────────────────────────────
    def enviar(self, contenido: str) -> str:
        if not self.user.empresa_id:
            raise LLMNoConfigurado('usuario sin empresa')
        Message.objects.create(conversation=self.conversation, role='user', content=contenido)
        system = self._system_prompt()
        historial = self._historial()
        inicio = time.monotonic()
        texto = self._bucle(system, historial)
        self.traza.latencia_total_ms = int((time.monotonic() - inicio) * 1000)
        if not texto:
            texto = 'No pude generar una respuesta. ¿Puedes reformular la pregunta?'
        Message.objects.create(conversation=self.conversation, role='assistant', content=texto)
        Conversation.objects.filter(pk=self.conversation.pk).update(updated_at=timezone.now())
        UsoLLM.registrar(self.user.empresa, self.traza.modelo, self.traza.tokens_entrada, self.traza.tokens_salida)
        return texto

    # ── internos ──────────────────────────────────────────────────────────
    def _system_prompt(self) -> str:
        return self.perfil.system_prompt.format(
            fecha=timezone.localdate().isoformat(),
            empresa=self.user.empresa.nombre,
        )

    def _historial(self) -> list[LLMMessage]:
        n = int(getattr(settings, 'LLM_HISTORIAL_N', 20))
        ultimos = list(Message.objects.filter(conversation=self.conversation)
                       .order_by('-created_at', '-id')[:n])[::-1]
        return [LLMMessage(role='assistant' if m.role == 'assistant' else 'user', content=m.content)
                for m in ultimos]

    def _ejecutor_tools(self):
        if self._ejecutor is None:
            self._ejecutor = self.perfil.executor_factory(self.user)
        return self._ejecutor

    def _bucle(self, system: str, historial: list[LLMMessage]) -> str:
        mensajes = list(historial)
        for ronda in range(1, MAX_RONDAS_TOOLS + 1):
            t0 = time.monotonic()
            resp: LLMResponse = self.cliente.chat(system, mensajes, list(self.perfil.tools_activas()))
            ms = int((time.monotonic() - t0) * 1000)
            self.traza.rondas = ronda
            self.traza.tokens_entrada += resp.tokens_entrada
            self.traza.tokens_salida += resp.tokens_salida
            if ronda == 1:
                self.traza.latencia_primera_ms = ms
            if not resp.tool_calls:
                return resp.text
            mensajes.append(LLMMessage(role='assistant', content=resp.text or None,
                                       tool_calls=resp.tool_calls, raw=resp.raw))
            for tc in resp.tool_calls:
                resultado, dur = self._ejecutar(tc.name, tc.arguments)
                self.traza.tool_calls.append(TrazaTool(tc.name, tc.arguments, ronda, self.ejecutar_tools, dur))
                mensajes.append(LLMMessage(role='tool', tool_call_id=tc.id, name=tc.name,
                                           content=_json_seguro(resultado)))
            if not self.ejecutar_tools:
                # Modo eval: nos basta con saber qué pidió el modelo.
                return resp.text or ''
        return ('Necesité demasiados pasos para responder. Intenta una pregunta más específica.')

    def _ejecutar(self, name: str, arguments: dict):
        if not self.ejecutar_tools:
            return {'eval': 'tool no ejecutada'}, 0
        t0 = time.monotonic()
        try:
            resultado = self._ejecutor_tools().execute_function(name, arguments or {})
        except TypeError as e:
            # argumentos inesperados del modelo: se lo decimos, no reventamos el turno
            resultado = {'success': False, 'error': f'Argumentos inválidos para {name}: {type(e).__name__}'}
        except Exception as e:  # noqa: BLE001 - el detalle va al log, no al modelo
            logger.warning('tool_error perfil=%s tool=%s tipo=%s', self.perfil.clave, name, type(e).__name__)
            resultado = {'success': False, 'error': 'La herramienta falló. Informa al usuario.'}
        return resultado, int((time.monotonic() - t0) * 1000)


def registrar_uso(empresa, modelo: str, tokens_entrada: int, tokens_salida: int):
    """Acumula tokens por (empresa, día, modelo). Idempotente ante carreras."""
    hoy = timezone.localdate()
    for _ in range(2):
        try:
            with transaction.atomic():
                obj, creado = UsoLLM.objects.get_or_create(
                    empresa=empresa, fecha=hoy, modelo=modelo,
                    defaults={'tokens_entrada': tokens_entrada, 'tokens_salida': tokens_salida, 'llamadas': 1})
            if creado:
                return
            UsoLLM.objects.filter(pk=obj.pk).update(
                tokens_entrada=F('tokens_entrada') + tokens_entrada,
                tokens_salida=F('tokens_salida') + tokens_salida,
                llamadas=F('llamadas') + 1)
            return
        except IntegrityError:
            continue
