"""Fija el contexto de la petición para el logging JSON (ver apps.core.logging_json).

Debe ir PRIMERO en MIDDLEWARE para cubrir el resto. user/empresa quedan aquí solo si la
sesión ya autenticó (admin); para JWT/ApiToken los fija la clase de autenticación de DRF.
"""
import os
import uuid

from apps.core.logging_json import iniciar_contexto, limpiar_contexto, set_usuario_actual


class RequestContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.project = os.getenv('GS_PROJECT_ID') or os.getenv('GOOGLE_CLOUD_PROJECT')

    def __call__(self, request):
        request_id = request.META.get('HTTP_X_REQUEST_ID') or uuid.uuid4().hex[:16]
        trace = None
        cloud_trace = request.META.get('HTTP_X_CLOUD_TRACE_CONTEXT')
        if cloud_trace and self.project:
            trace = f"projects/{self.project}/traces/{cloud_trace.split('/')[0]}"
            request_id = cloud_trace.split('/')[0][:32]
        iniciar_contexto(request_id, request.path, trace)
        request.request_id = request_id
        try:
            user = getattr(request, 'user', None)
            if user is not None and user.is_authenticated:
                set_usuario_actual(user)
            response = self.get_response(request)
            response['X-Request-ID'] = request_id
            return response
        finally:
            limpiar_contexto()
