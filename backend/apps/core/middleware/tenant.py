"""
Middleware para Multi-Tenant con Row Level Security (RLS)

Configura las variables de sesión PostgreSQL que RLS usa
para filtrar datos por empresa automáticamente.

Soporta tanto empresa_id (bigint) como empresa_uuid (UUID).

Debe ir DESPUÉS de AuthenticationMiddleware en MIDDLEWARE.
"""
import logging
from django.db import connection
from django.core.cache import cache

logger = logging.getLogger(__name__)


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        empresa_id, empresa_uuid = self._get_empresa_context(request)

        if empresa_id:
            self._set_tenant_context(empresa_id, empresa_uuid, request)

        try:
            response = self.get_response(request)
        finally:
            self._clear_tenant_context()

        return response

    def _get_empresa_context(self, request):
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None, None

        empresa_id = getattr(request.user, 'empresa_id', None)
        if not empresa_id:
            return None, None

        empresa_uuid = self._resolve_empresa_uuid(empresa_id)
        logger.debug(
            f"Tenant context: empresa_id={empresa_id}, "
            f"empresa_uuid={empresa_uuid}, user={request.user.username}"
        )
        return empresa_id, empresa_uuid

    def _resolve_empresa_uuid(self, empresa_id):
        cache_key = f'empresa_uuid_{empresa_id}'
        empresa_uuid = cache.get(cache_key)
        if empresa_uuid:
            return empresa_uuid

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT uuid FROM empresas_empresa WHERE id = %s",
                    [empresa_id]
                )
                row = cursor.fetchone()
                if row:
                    empresa_uuid = str(row[0])
                    cache.set(cache_key, empresa_uuid, timeout=3600)
                    return empresa_uuid
        except Exception as e:
            logger.warning(f"No se pudo resolver empresa_uuid para id={empresa_id}: {e}")
        return None

    def _set_tenant_context(self, empresa_id, empresa_uuid, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET app.current_empresa = %s", [str(empresa_id)])

                if empresa_uuid:
                    cursor.execute("SET app.current_empresa_uuid = %s", [empresa_uuid])

                if hasattr(request, 'user') and request.user.is_authenticated:
                    cursor.execute("SET app.current_user_id = %s", [str(request.user.id)])

        except Exception as e:
            logger.error(f"Error configurando tenant context: {e}")
            raise

    def _clear_tenant_context(self):
        try:
            if connection.connection and not connection.connection.closed:
                with connection.cursor() as cursor:
                    cursor.execute("RESET app.current_empresa")
                    cursor.execute("RESET app.current_empresa_uuid")
                    cursor.execute("RESET app.current_user_id")
        except Exception:
            pass
