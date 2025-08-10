from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

class HasEmpresaPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        print(f'Verificando permisos para usuario: {request.user.username}')
        
        # Verificar si el usuario está autenticado
        if not request.user.is_authenticated:
            print('Usuario no autenticado')
            return False
            
        # Verificar si el usuario tiene empresa asignada
        if not hasattr(request.user, 'empresa'):
            print(f'Usuario {request.user.username} no tiene empresa asignada')
            raise PermissionDenied('Usuario no tiene empresa asignada')
            
        print(f'Usuario {request.user.username} tiene empresa asignada: {request.user.empresa.nombre}')
        return True

    def has_object_permission(self, request, view, obj):
        print(f'Verificando permisos de objeto para usuario: {request.user.username}')
        
        # Verificar si el objeto tiene atributo empresa
        if not hasattr(obj, 'empresa'):
            print(f'Objeto {obj} no tiene atributo empresa')
            return False
            
        # Verificar si la empresa del objeto coincide con la del usuario
        tiene_permiso = obj.empresa == request.user.empresa
        print(f'Usuario {request.user.username} {"tiene" if tiene_permiso else "no tiene"} permiso para acceder al objeto {obj}')
        return tiene_permiso

class ModulePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        # Obtener el módulo del path de la URL
        module = view.kwargs.get('modulo', '')
        
        # Si es superusuario, tiene todos los permisos
        if request.user.is_superuser:
            return True
            
        # Verificar si el usuario está autenticado
        if not request.user.is_authenticated:
            return False

        # Aquí puedes implementar tu lógica de permisos específica
        # Por ejemplo, verificar grupos o permisos específicos del usuario
        permisos_modulos = {
            'compras': ['ver_compras', 'crear_compras', 'editar_compras', 'eliminar_compras'],
            'ventas': ['ver_ventas', 'crear_ventas', 'editar_ventas', 'eliminar_ventas'],
            'inventario': ['ver_inventario', 'crear_inventario', 'editar_inventario', 'eliminar_inventario'],
            # Agrega más módulos según necesites
        }

        # Por ahora, retornamos True para pruebas
        # Deberías implementar la lógica real según tus necesidades
        return True 