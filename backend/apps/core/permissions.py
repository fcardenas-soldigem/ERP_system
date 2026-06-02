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


class ModulePermission(permissions.BasePermission):
    """
    Verifica permisos por módulo basándose en el rol del usuario.
    
    Roles soportados:
    - superuser: acceso total
    - admin: acceso total dentro de su empresa
    - comercial: ventas, clientes, cotizaciones (lectura inventario)
    - produccion: producción, inventario (lectura)
    - almacen: inventario completo (lectura ventas/compras)
    - contador: dashboard, reportes, cuentas (solo lectura)
    - readonly: solo lectura en todos los módulos
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
        'comercial': {
            'ventas': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
            'cotizaciones': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
            'inventario': ['GET'],
            'compras': ['GET'],
            'dashboard': ['GET'],
            'ai_assistant': ['GET', 'POST'],
        },
        'produccion': {
            'produccion': ['GET', 'POST', 'PUT', 'PATCH'],
            'inventario': ['GET', 'POST', 'PUT', 'PATCH'],
            'compras': ['GET'],
            'dashboard': ['GET'],
        },
        'almacen': {
            'inventario': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
            'compras': ['GET'],
            'ventas': ['GET'],
            'produccion': ['GET'],
            'dashboard': ['GET'],
        },
        'contador': {
            'dashboard': ['GET'],
            'ventas': ['GET'],
            'compras': ['GET'],
            'inventario': ['GET'],
            'cotizaciones': ['GET'],
            'produccion': ['GET'],
        },
        'readonly': {
            'dashboard': ['GET'],
            'ventas': ['GET'],
            'compras': ['GET'],
            'inventario': ['GET'],
            'cotizaciones': ['GET'],
            'produccion': ['GET'],
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

        if role == 'personalizado':
            return self._check_granular_permission(request.user, module, request.method)

        allowed_methods = self.ROLE_PERMISSIONS.get(role, {}).get(module, [])

        if request.method not in allowed_methods:
            logger.info(
                "Permiso denegado: user=%s role=%s module=%s method=%s",
                request.user.email, role, module, request.method
            )
            return False

        return True

    def _check_granular_permission(self, user, module, method):
        """Verifica permisos granulares de PermisoUsuario para rol 'personalizado'."""
        try:
            from apps.core.models import PermisoUsuario
            permiso = PermisoUsuario.objects.get(usuario=user, modulo=module)

            if method in ('GET', 'HEAD', 'OPTIONS'):
                return permiso.puede_ver
            elif method == 'POST':
                return permiso.puede_crear
            elif method in ('PUT', 'PATCH'):
                return permiso.puede_editar
            elif method == 'DELETE':
                return permiso.puede_eliminar

            return False
        except Exception:
            return False

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
        if user.is_staff and getattr(user, 'rol', '') != 'personalizado':
            return 'admin'

        rol = getattr(user, 'rol', None)
        if rol and rol in self.ROLE_PERMISSIONS:
            return rol
        if rol == 'personalizado':
            return 'personalizado'

        try:
            from apps.core.models import Usuario
            usuario = Usuario.objects.filter(usuario=user).first()
            if usuario and usuario.rol:
                role = usuario.rol.lower()
                if role in self.ROLE_PERMISSIONS:
                    return role
                if role in ('vendedor',):
                    return 'comercial'
                if role in ('almacén', 'almacen'):
                    return 'almacen'
        except Exception:
            pass

        return 'readonly'
