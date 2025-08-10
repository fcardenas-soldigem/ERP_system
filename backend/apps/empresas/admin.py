from django.contrib import admin
from .models import Empresa

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'ruc', 'email', 'telefono', 'created_at']
    search_fields = ['nombre', 'ruc', 'email']
    list_filter = ['created_at']
    readonly_fields = ['created_at', 'updated_at'] 