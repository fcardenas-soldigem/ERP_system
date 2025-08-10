from django.contrib import admin
from .models import Usuario

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'empresa', 'rol', 'activo')
    list_filter = ('rol', 'activo', 'empresa')
    search_fields = ('usuario__username', 'usuario__email')
