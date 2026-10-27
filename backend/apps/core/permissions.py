import logging
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

logger = logging.getLogger(__name__)


class HasEmpresaPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if not hasattr(request.user, 'empresa') or not request.user.empresa:
            raise PermissionDenied('Usuario no tiene empresa asignada')

        return True

    def has_object_permission(self, request, view, obj):
        if not hasattr(obj, 'empresa'):
            return False
        return obj.empresa_id == request.user.empresa_id


class RolEscritura(permissions.BasePermission):
    """
    Permiso central por rol. Métodos seguros (GET/HEAD/OPTIONS) pasan;
    cualquier escritura —incluidas las @action custom con POST/PUT/PATCH/
    DELETE: convertir, anular, cobrar, cambiar estado— exige rol admin u
    operador. solo_lectura recibe 403 en toda escritura.

    Se compone con IsAuthenticated + HasEmpresaPermission en todos los
    viewsets de negocio (ventas, cotizaciones, compras, pagos, guías,
    órdenes de servicio, inventario, clientes, proveedores, finanzas,
    producción).
    """

    message = 'Tu rol es de solo lectura: no puede crear ni modificar datos.'

    ROLES_ESCRITURA = ('admin', 'operador')

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return getattr(request.user, 'rol', None) in self.ROLES_ESCRITURA


class ModulePermission(permissions.BasePermission):
    """
    Verifica permisos por módulo basándose en el rol del usuario.
    
    Roles soportados: admin (todo), operador (documentos de negocio),
    solo_lectura (GET en todos los módulos).
    """

    ROLE_PERMISSIONS = {
        'admin': {
            'ventas': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
            'compras': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
            'inventario': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
            'produccion': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
            'cotizaciones': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
            'dashboard': ['GET'],
            'configuracion': ['GET', 'POST', 'PUT', 'PATCH'],
            'ai_assistant': ['GET', 'POST'],
            'ml_models': ['GET', 'POST'],
            'empresas': ['GET', 'PUT', 'PATCH'],
            'core': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
        },
        'operador': {
            'ventas': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
            'compras': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
            'inventario': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
            'produccion': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
            'cotizaciones': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
            'dashboard': ['GET'],
            'configuracion': ['GET'],
            'ai_assistant': ['GET', 'POST'],
            'ml_models': ['GET'],
            'empresas': ['GET'],
            'core': ['GET'],
        },
        'solo_lectura': {
            'dashboard': ['GET'],
            'ventas': ['GET'],
            'compras': ['GET'],
            'inventario': ['GET'],
            'cotizaciones': ['GET'],
            'produccion': ['GET'],
            'configuracion': ['GET'],
            'ai_assistant': ['GET'],
            'empresas': ['GET'],
            'core': ['GET'],
        },
    }

    MODULE_MAP = {
        'venta': 'ventas',
        'cliente': 'ventas',
        'factura': 'ventas',
        'ordenventa': 'ventas',
        'pagoventa': 'ventas',
        'compra': 'compras',
        'proveedor': 'compras',
        'ordencompra': 'compras',
        'pagocompra': 'compras',
        'recepcioncompra': 'compras',
        'producto': 'inventario',
        'almacen': 'inventario',
        'categoria': 'inventario',
        'stock': 'inventario',
        'kardex': 'inventario',
        'movimiento': 'inventario',
        'materias-primas': 'inventario',
        'productos-terminados': 'inventario',
        'receta': 'produccion',
        'orden': 'produccion',
        'cotizacion': 'cotizaciones',
        'dashboard': 'dashboard',
        'empresa': 'empresas',
        'usuario': 'core',
        'perfil': 'core',
        'conversation': 'ai_assistant',
        'assistant': 'ai_assistant',
        'mlmodel': 'ml_models',
    }

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        module = self._resolve_module(view)
        if not module:
            return True

        role = self._get_user_role(request.user)

        allowed_methods = self.ROLE_PERMISSIONS.get(role, {}).get(module, [])

        if request.method not in allowed_methods:
            logger.info(
                "Permiso denegado: user=%s role=%s module=%s method=%s",
                request.user.email, role, module, request.method
            )
            return False

        return True

    def _resolve_module(self, view):
        basename = getattr(view, 'basename', '') or ''
        for key, module in self.MODULE_MAP.items():
            if key in basename.lower():
                return module

        url_path = getattr(view, 'request', None)
        if url_path and hasattr(url_path, 'path'):
            path = url_path.path.lower()
            for segment in ['ventas', 'compras', 'inventario', 'produccion',
                            'cotizaciones', 'dashboard', 'empresas', 'ai', 'ml']:
                if f'/api/{segment}/' in path:
                    if segment == 'ai':
                        return 'ai_assistant'
                    if segment == 'ml':
                        return 'ml_models'
                    return segment

        return None

    def _get_user_role(self, user):
        if user.is_staff:
            return 'admin'

        rol = getattr(user, 'rol', None)
        if rol in self.ROLE_PERMISSIONS:
            return rol
        # Nombres legados (pre-0003_simplificar_roles) por si llega un valor viejo.
        legados = {
            'readonly': 'solo_lectura',
            'comercial': 'operador', 'produccion': 'operador',
            'almacen': 'operador', 'contador': 'operador',
            'personalizado': 'operador',
        }
        if rol in legados:
            return legados[rol]

        return 'solo_lectura'
