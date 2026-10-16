"""
Capa propia sobre el proveedor de LLM (sustituye a la API de Assistants de OpenAI).

Dos adaptadores con el MISMO contrato (`LLMClient.chat`):

- "vertex": Gemini en Vertex AI vía `google-genai` (``vertexai=True``). Autenticación
  por ADC (cuenta de servicio de Cloud Run / `gcloud auth application-default` en
  local). SIN API key. Function calling nativo.
- "openai": cualquier API compatible con `chat.completions` + tools (OpenAI, DeepSeek,
  Groq, un proxy...). Se configura con LLM_BASE_URL + LLM_API_KEY.

Reglas:
- El historial vive en NUESTRA BD (Conversation/Message). El proveedor no guarda
  estado: cada llamada recibe el system prompt + últimas N interacciones.
- `empresa` y `usuario` los pone el servidor en el ejecutor de tools; el modelo
  nunca los ve ni los elige.
- Errores con nombre: `LLMNoConfigurado` (sin credenciales/permiso/modelo → 503),
  `LLMNoDisponible` (proveedor caído, 429, timeout de 30 s → 502). Nada más.
- NO se loguean prompts ni respuestas (solo modelo, tokens, duración).
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

PROVEEDORES = ('vertex', 'openai')


# ── Errores con nombre ───────────────────────────────────────────────────────

class LLMError(Exception):
    """Base. Un LLMError 'pelado' es un fallo inesperado (→ 500 genérico)."""


class LLMNoConfigurado(LLMError):
    """Faltan credenciales/permisos o el modelo/región no existe. → 503."""

    mensaje = ('El asistente de IA no está configurado en este servidor. '
               'Contacta al administrador.')

    def __init__(self, detalle: str = ''):
        super().__init__(self.mensaje)
        self.detalle = detalle  # solo para logs, nunca para el cliente


class LLMNoDisponible(LLMError):
    """El proveedor falló (5xx, 429) o no respondió en LLM_TIMEOUT s. → 502."""

    mensaje = 'El asistente de IA no está disponible en este momento. Intenta de nuevo.'

    def __init__(self, detalle: str = ''):
        super().__init__(self.mensaje)
        self.detalle = detalle


# ── Contrato ─────────────────────────────────────────────────────────────────

@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict  # JSON Schema (subconjunto OpenAPI 3.0, sin $ref)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class LLMMessage:
    """Mensaje del historial. role ∈ {user, assistant, tool}.

    `tool_calls` solo en assistant; `tool_call_id`/`name` solo en tool.
    `raw` guarda la representación nativa del proveedor del turno assistant con
    tool_calls (Gemini exige devolver sus `Part` tal cual, incluida la firma de
    razonamiento); vive solo en memoria durante el turno.
    """
    role: str
    content: Optional[str] = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    raw: Any = None


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[ToolCall]
    tokens_entrada: int
    tokens_salida: int
    modelo: str
    raw: Any = None  # partes nativas del turno (para re-enviar al proveedor)


class LLMClient:
    """Contrato común. Implementaciones: VertexClient, OpenAICompatClient."""

    proveedor = ''

    def __init__(self, modelo: str, timeout: float):
        self.modelo = modelo
        self.timeout = timeout

    def chat(self, system: str, messages: list[LLMMessage], tools: list[ToolSpec],
             temperature: float = 0.2) -> LLMResponse:
        raise NotImplementedError

    # Observabilidad sin contenido: modelo, duración, tokens, nº de tool calls.
    def _log_llamada(self, inicio: float, resp: LLMResponse):
        logger.info('llm_call proveedor=%s modelo=%s ms=%d tokens_in=%d tokens_out=%d tool_calls=%d',
                    self.proveedor, self.modelo, int((time.monotonic() - inicio) * 1000),
                    resp.tokens_entrada, resp.tokens_salida, len(resp.tool_calls))


# ── Vertex AI (Gemini) ───────────────────────────────────────────────────────

class VertexClient(LLMClient):
    proveedor = 'vertex'

    def __init__(self, modelo: str, timeout: float, project: str, location: str):
        super().__init__(modelo, timeout)
        self.project = project
        self.location = location
        self._client = None

    def _cliente(self):
        if self._client is not None:
            return self._client
        if not self.project:
            raise LLMNoConfigurado('LLM_PROJECT / GS_PROJECT_ID vacío')
        try:
            from google import genai
            from google.genai import types
        except ImportError as e:  # pragma: no cover - dependencia pineada
            raise LLMNoConfigurado(f'google-genai no instalado: {e}')
        try:
            self._client = genai.Client(
                vertexai=True, project=self.project, location=self.location,
                http_options=types.HttpOptions(timeout=int(self.timeout * 1000)),  # ms
            )
        except Exception as e:  # DefaultCredentialsError y similares
            raise self._traducir(e)
        return self._client

    @staticmethod
    def _traducir(e: Exception) -> LLMError:
        """Mapea excepciones del SDK/auth a nuestros errores con nombre."""
        nombre = type(e).__name__
        modulo = type(e).__module__ or ''
        if isinstance(e, LLMError):
            return e
        # google.auth
        if 'google.auth' in modulo:
            if nombre in ('DefaultCredentialsError', 'RefreshError', 'GoogleAuthError'):
                return LLMNoConfigurado(f'{nombre}')
            if nombre == 'TransportError':
                return LLMNoDisponible(nombre)
        # google.genai.errors.{ClientError,ServerError}
        codigo = getattr(e, 'code', None) or getattr(e, 'status_code', None)
        if 'google.genai' in modulo:
            if nombre == 'ServerError' or (isinstance(codigo, int) and codigo >= 500):
                return LLMNoDisponible(f'{nombre} {codigo}')
            if codigo in (401, 403, 404):
                return LLMNoConfigurado(f'{nombre} {codigo}')
            if codigo == 429:
                return LLMNoDisponible(f'{nombre} 429')
            return LLMError(f'{nombre} {codigo}')
        # httpx (transporte del SDK)
        if modulo.startswith('httpx') or nombre in ('TimeoutException', 'ReadTimeout', 'ConnectTimeout',
                                                    'ConnectError', 'RemoteProtocolError', 'PoolTimeout'):
            return LLMNoDisponible(nombre)
        if isinstance(e, TimeoutError):
            return LLMNoDisponible('TimeoutError')
        return LLMError(nombre)

    def chat(self, system, messages, tools, temperature=0.2):
        from google.genai import types
        client = self._cliente()
        contents = [self._a_content(m) for m in messages]
        config = types.GenerateContentConfig(
            system_instruction=system or None,
            temperature=temperature,
            tools=[types.Tool(function_declarations=[
                types.FunctionDeclaration(name=t.name, description=t.description, parameters=t.parameters)
                for t in tools])] if tools else None,
        )
        inicio = time.monotonic()
        try:
            resp = client.models.generate_content(model=self.modelo, contents=contents, config=config)
        except Exception as e:
            raise self._traducir(e)
        resultado = self._de_respuesta(resp)
        self._log_llamada(inicio, resultado)
        return resultado

    # -- conversión ---------------------------------------------------------
    @staticmethod
    def _a_content(m: LLMMessage):
        from google.genai import types
        if m.role == 'assistant':
            if m.raw is not None:
                return types.Content(role='model', parts=list(m.raw))
            parts = []
            if m.content:
                parts.append(types.Part.from_text(text=m.content))
            for tc in m.tool_calls:
                parts.append(types.Part.from_function_call(name=tc.name, args=tc.arguments))
            return types.Content(role='model', parts=parts or [types.Part.from_text(text='')])
        if m.role == 'tool':
            try:
                payload = json.loads(m.content) if isinstance(m.content, str) else m.content
            except ValueError:
                payload = {'result': m.content}
            if not isinstance(payload, dict):
                payload = {'result': payload}
            return types.Content(role='user', parts=[
                types.Part.from_function_response(name=m.name or 'tool', response=payload)])
        return types.Content(role='user', parts=[types.Part.from_text(text=m.content or '')])

    def _de_respuesta(self, resp) -> LLMResponse:
        texto, tool_calls, partes = [], [], []
        candidatos = getattr(resp, 'candidates', None) or []
        if candidatos and candidatos[0].content and candidatos[0].content.parts:
            partes = list(candidatos[0].content.parts)
            for i, p in enumerate(partes):
                fc = getattr(p, 'function_call', None)
                if fc is not None and getattr(fc, 'name', None):
                    tool_calls.append(ToolCall(id=getattr(fc, 'id', None) or f'call_{i}',
                                               name=fc.name, arguments=dict(fc.args or {})))
                elif getattr(p, 'text', None) and not getattr(p, 'thought', False):
                    texto.append(p.text)
        uso = getattr(resp, 'usage_metadata', None)
        t_in = int(getattr(uso, 'prompt_token_count', 0) or 0)
        t_out = int(getattr(uso, 'candidates_token_count', 0) or 0) + int(getattr(uso, 'thoughts_token_count', 0) or 0)
        return LLMResponse(text=''.join(texto).strip(), tool_calls=tool_calls,
                           tokens_entrada=t_in, tokens_salida=t_out, modelo=self.modelo, raw=partes)


# ── OpenAI-compatible (chat.completions + tools) ─────────────────────────────

class OpenAICompatClient(LLMClient):
    proveedor = 'openai'

    def __init__(self, modelo: str, timeout: float, base_url: Optional[str], api_key: Optional[str]):
        super().__init__(modelo, timeout)
        self.base_url = base_url or None
        self.api_key = api_key
        self._client = None

    def _cliente(self):
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise LLMNoConfigurado('LLM_API_KEY vacío')
        try:
            import openai
        except ImportError as e:  # pragma: no cover
            raise LLMNoConfigurado(f'openai no instalado: {e}')
        self._client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url,
                                     timeout=self.timeout, max_retries=0)
        return self._client

    @staticmethod
    def _traducir(e: Exception) -> LLMError:
        if isinstance(e, LLMError):
            return e
        nombre = type(e).__name__
        if nombre in ('AuthenticationError', 'PermissionDeniedError', 'NotFoundError'):
            return LLMNoConfigurado(nombre)
        if nombre in ('APITimeoutError', 'APIConnectionError', 'InternalServerError',
                      'RateLimitError', 'APIStatusError'):
            codigo = getattr(e, 'status_code', None)
            if nombre == 'APIStatusError' and isinstance(codigo, int) and 400 <= codigo < 500 and codigo != 429:
                return LLMError(f'{nombre} {codigo}')
            return LLMNoDisponible(f'{nombre} {codigo or ""}'.strip())
        return LLMError(nombre)

    def chat(self, system, messages, tools, temperature=0.2):
        client = self._cliente()
        msgs = []
        if system:
            msgs.append({'role': 'system', 'content': system})
        for m in messages:
            if m.role == 'assistant':
                d = {'role': 'assistant', 'content': m.content or None}
                if m.tool_calls:
                    d['tool_calls'] = [{'id': tc.id, 'type': 'function', 'function': {
                        'name': tc.name, 'arguments': json.dumps(tc.arguments, ensure_ascii=False)}}
                        for tc in m.tool_calls]
                msgs.append(d)
            elif m.role == 'tool':
                msgs.append({'role': 'tool', 'tool_call_id': m.tool_call_id, 'content': m.content or ''})
            else:
                msgs.append({'role': 'user', 'content': m.content or ''})
        kwargs = {}
        if tools:
            kwargs['tools'] = [{'type': 'function', 'function': {
                'name': t.name, 'description': t.description, 'parameters': t.parameters}} for t in tools]
        inicio = time.monotonic()
        try:
            resp = client.chat.completions.create(model=self.modelo, messages=msgs,
                                                  temperature=temperature, **kwargs)
        except Exception as e:
            raise self._traducir(e)
        choice = resp.choices[0].message
        tool_calls = []
        for tc in (choice.tool_calls or []):
            try:
                args = json.loads(tc.function.arguments or '{}')
            except ValueError:
                args = {}
            tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))
        uso = getattr(resp, 'usage', None)
        resultado = LLMResponse(text=(choice.content or '').strip(), tool_calls=tool_calls,
                                tokens_entrada=int(getattr(uso, 'prompt_tokens', 0) or 0),
                                tokens_salida=int(getattr(uso, 'completion_tokens', 0) or 0),
                                modelo=self.modelo)
        self._log_llamada(inicio, resultado)
        return resultado


# ── Fábrica ──────────────────────────────────────────────────────────────────

def get_llm_client(modelo: Optional[str] = None, proveedor: Optional[str] = None) -> LLMClient:
    proveedor = (proveedor or getattr(settings, 'LLM_PROVIDER', 'vertex') or 'vertex').lower()
    modelo = modelo or getattr(settings, 'LLM_MODEL', '')
    timeout = float(getattr(settings, 'LLM_TIMEOUT', 30))
    if not modelo:
        raise LLMNoConfigurado('LLM_MODEL vacío')
    if proveedor == 'vertex':
        return VertexClient(modelo, timeout,
                            project=getattr(settings, 'LLM_PROJECT', '') or '',
                            location=getattr(settings, 'LLM_LOCATION', 'global') or 'global')
    if proveedor == 'openai':
        return OpenAICompatClient(modelo, timeout,
                                  base_url=getattr(settings, 'LLM_BASE_URL', None),
                                  api_key=getattr(settings, 'LLM_API_KEY', None))
    raise LLMNoConfigurado(f'LLM_PROVIDER desconocido: {proveedor}')
