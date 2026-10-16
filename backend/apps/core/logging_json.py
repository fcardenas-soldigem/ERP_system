"""
Logging estructurado (B3): una línea JSON por evento en stdout, con los campos que
Cloud Logging indexa (severity, message) y el contexto de la petición
(request_id, path, empresa_id, user_id) para filtrar por tenant/usuario.

Regla: NUNCA datos personales (email, nombre, DNI/RUC, teléfono) ni montos en los
mensajes; solo ids. El contexto se guarda en contextvars (seguro con gthread).

Piezas:
- RequestContextMiddleware (apps.core.middleware.request_context): fija request_id y path
  al entrar; user/empresa si la sesión ya autenticó.
- set_usuario_actual(user) / set_empresa_actual(empresa_id): lo llaman las clases de
  autenticación de DRF (JWT y ApiToken del MCP) al autenticar.
- RequestContextFilter: copia el contexto en cada LogRecord.
- JSONFormatter: serializa el record (+ traceback si lo hay).
"""
import contextvars
import json
import logging
import traceback
from datetime import datetime, timezone

_request_id = contextvars.ContextVar('request_id', default=None)
_path = contextvars.ContextVar('path', default=None)
_user_id = contextvars.ContextVar('user_id', default=None)
_empresa_id = contextvars.ContextVar('empresa_id', default=None)
_trace = contextvars.ContextVar('trace', default=None)

CAMPOS_CONTEXTO = ('request_id', 'path', 'user_id', 'empresa_id')

# Nombres de severidad de Cloud Logging.
_SEVERIDAD = {'DEBUG': 'DEBUG', 'INFO': 'INFO', 'WARNING': 'WARNING',
              'ERROR': 'ERROR', 'CRITICAL': 'CRITICAL'}


def iniciar_contexto(request_id, path, trace=None):
    _request_id.set(request_id)
    _path.set(path)
    _trace.set(trace)
    _user_id.set(None)
    _empresa_id.set(None)


def limpiar_contexto():
    for var in (_request_id, _path, _user_id, _empresa_id, _trace):
        var.set(None)


def set_usuario_actual(user):
    """Registra user_id y empresa_id del usuario autenticado (solo ids)."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return
    _user_id.set(getattr(user, 'id', None))
    _empresa_id.set(getattr(user, 'empresa_id', None))


def set_empresa_actual(empresa_id):
    _empresa_id.set(empresa_id)


def contexto_actual():
    return {
        'request_id': _request_id.get(),
        'path': _path.get(),
        'user_id': _user_id.get(),
        'empresa_id': _empresa_id.get(),
    }


class RequestContextFilter(logging.Filter):
    """Añade request_id/path/user_id/empresa_id a cada record (siempre, aunque sean None)."""

    def filter(self, record):
        for campo, valor in contexto_actual().items():
            if not hasattr(record, campo):
                setattr(record, campo, valor)
        if not hasattr(record, 'trace'):
            record.trace = _trace.get()
        return True


class JSONFormatter(logging.Formatter):
    def format(self, record):
        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover — args mal formados
            message = str(record.msg)
        doc = {
            'severity': _SEVERIDAD.get(record.levelname, record.levelname),
            'message': message,
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'logger': record.name,
        }
        for campo in CAMPOS_CONTEXTO:
            doc[campo] = getattr(record, campo, None)
        trace = getattr(record, 'trace', None)
        if trace:
            doc['logging.googleapis.com/trace'] = trace
        if record.exc_info:
            doc['exception'] = ''.join(traceback.format_exception(*record.exc_info))[-8000:]
        elif record.exc_text:
            doc['exception'] = record.exc_text[-8000:]
        return json.dumps(doc, ensure_ascii=False, default=str)
