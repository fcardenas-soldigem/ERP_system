"""Autenticación y permiso del MCP: SOLO vía ApiToken (Bearer), nunca sesión/JWT.

Se usa EXCLUSIVAMENTE en /api/mcp/. Garantiza que cada token vea solo su empresa:
`request.empresa` y `request.auth` (el ApiToken) se fijan aquí y las herramientas
filtran por esa empresa; jamás se acepta `empresa` como entrada.
"""
from django.utils import timezone
from rest_framework import authentication, exceptions, permissions

from .models import ApiToken, _hash_token


class ApiTokenAuthentication(authentication.BaseAuthentication):
    keyword = b'bearer'

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).split()
        if not header or header[0].lower() != self.keyword:
            return None  # sin Bearer → el permiso responde 401
        if len(header) != 2:
            raise exceptions.AuthenticationFailed('Encabezado Authorization inválido.')

        raw = header[1].decode('utf-8', errors='ignore')
        try:
            token = ApiToken.objects.select_related('empresa', 'creado_por').get(
                token_hash=_hash_token(raw))
        except ApiToken.DoesNotExist:
            raise exceptions.AuthenticationFailed('Token inválido.')

        if not token.activo:
            raise exceptions.AuthenticationFailed('Token revocado o expirado.')

        # Marca de uso (update directo para no disparar señales ni validación).
        ApiToken.objects.filter(pk=token.pk).update(last_used_at=timezone.now())
        request.empresa = token.empresa
        request.api_token = token
        # request.user = el creador (para helpers que lo usen); la autoridad es el token.
        return (token.creado_por, token)

    def authenticate_header(self, request):
        return 'Bearer'


class EsTokenMCP(permissions.BasePermission):
    """Autoriza solo si la petición llegó con un ApiToken válido (no sesión/JWT)."""
    message = 'Se requiere un token de API válido (Bearer).'

    def has_permission(self, request, view):
        return isinstance(getattr(request, 'auth', None), ApiToken)
