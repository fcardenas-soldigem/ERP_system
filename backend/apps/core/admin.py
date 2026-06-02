from django.contrib import admin
from .models import Usuario, PermisoUsuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'empresa', 'rol', 'activo')
    list_filter = ('rol', 'activo', 'empresa')
    search_fields = ('usuario__username', 'usuario__email')


@admin.register(PermisoUsuario)
class PermisoUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'modulo', 'puede_ver', 'puede_crear', 'puede_editar', 'puede_eliminar')
    list_filter = ('modulo', 'puede_ver', 'puede_crear')
    search_fields = ('usuario__email',)
    list_editable = ('puede_ver', 'puede_crear', 'puede_editar', 'puede_eliminar')
