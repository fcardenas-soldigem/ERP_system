"""
Respuestas de error uniformes para la API (B2).

Regla: el cliente NUNCA recibe `str(e)` ni tracebacks de errores inesperados.
- Error de negocio/validación (ValidationError de Django o DRF, ValueError,
  InvalidOperation de Decimal) → 400 y el mensaje útil se conserva.
- No encontrado → 404 'No encontrado'. Sin permiso → 403.
- Cualquier otra excepción → {"error": "<mensaje de negocio>"} con 500 y
  `logger.exception` (el detalle queda en Cloud Logging, no en la respuesta).

Uso en vistas:
    except Exception as e:
        return respuesta_error(e, 'Error al registrar el pago')   # 400 si es de negocio, si no 500 genérico
        return error_interno(e, 'Error al exportar')               # siempre 500 genérico
    errores.append(f'Fila {n}: {mensaje_seguro(e)}')               # mensajes por fila en importaciones
"""
import logging
import sys
from decimal import InvalidOperation

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError as DRFValidationError
from rest_framework.response import Response

MENSAJE_INTERNO = 'Error interno'
ERRORES_DE_NEGOCIO = (DjangoValidationError, DRFValidationError, ValueError, InvalidOperation)


def _logger_del_llamador(profundidad=2):
    try:
        nombre = sys._getframe(profundidad).f_globals.get('__name__', __name__)
    except Exception:  # pragma: no cover
        nombre = __name__
    return logging.getLogger(nombre)


def _no_encontrado(exc):
    """'Proveedor no encontrado' a partir de Proveedor.DoesNotExist; genérico si no."""
    nombre = type(exc).__qualname__
    if nombre.endswith('.DoesNotExist'):
        return f"{nombre.split('.')[0]} no encontrado"
    return 'No encontrado'


def es_error_de_negocio(exc):
    return isinstance(exc, ERRORES_DE_NEGOCIO)


def mensaje_de_negocio(exc):
    """Mensaje/detalle apto para el cliente si `exc` es de negocio; None si no lo es."""
    if isinstance(exc, DRFValidationError):
        return exc.detail
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, 'message_dict'):
            return exc.message_dict
        return ' '.join(str(m) for m in exc.messages) or 'Datos inválidos.'
    if isinstance(exc, InvalidOperation):
        return 'Valor numérico inválido.'
    if isinstance(exc, ValueError):
        return str(exc) or 'Valor inválido.'
    return None


def mensaje_seguro(exc, fallback=MENSAJE_INTERNO):
    """str para mensajes por fila/ítem: el de negocio si lo es; si no, genérico + log."""
    detalle = mensaje_de_negocio(exc)
    if detalle is not None:
        return detalle if isinstance(detalle, str) else str(detalle)
    if isinstance(exc, (ObjectDoesNotExist, Http404)):
        return _no_encontrado(exc)
    _logger_del_llamador().error('%s: %s', fallback, type(exc).__name__, exc_info=exc)
    return fallback


def error_interno(exc, mensaje=MENSAJE_INTERNO, *, clave='error', extra=None, _logger=None):
    """Siempre 500 con mensaje genérico de negocio; el detalle (traceback) va al log."""
    (_logger or _logger_del_llamador()).error('%s (%s)', mensaje, type(exc).__name__, exc_info=exc)
    cuerpo = {clave: mensaje}
    if extra:
        cuerpo.update(extra)
    return Response(cuerpo, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def respuesta_error(exc, mensaje=MENSAJE_INTERNO, *, clave='error', extra=None):
    """400 con mensaje útil si `exc` es de negocio; 404/403 si aplica; si no, 500 genérico."""
    detalle = mensaje_de_negocio(exc)
    if detalle is not None:
        cuerpo = {clave: detalle} if isinstance(detalle, str) else detalle
        if extra and isinstance(cuerpo, dict):
            cuerpo = {**cuerpo, **extra}
        return Response(cuerpo, status=status.HTTP_400_BAD_REQUEST)
    if isinstance(exc, (ObjectDoesNotExist, Http404)):
        return Response({clave: _no_encontrado(exc), **(extra or {})}, status=status.HTTP_404_NOT_FOUND)
    if isinstance(exc, DjangoPermissionDenied):
        return Response({clave: 'No tienes permiso para esta acción', **(extra or {})}, status=status.HTTP_403_FORBIDDEN)
    if isinstance(exc, APIException):
        return Response({clave: str(exc.detail), **(extra or {})}, status=exc.status_code)
    return error_interno(exc, mensaje, clave=clave, extra=extra, _logger=_logger_del_llamador())
