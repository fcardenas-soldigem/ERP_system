from django.contrib import admin

from .models import Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'empresa', 'email', 'telefono', 'rubro',
                    'tamano', 'usa_inventario', 'utm_source', 'fecha')
    list_filter = ('tamano', 'usa_inventario', 'utm_source', 'fecha')
    search_fields = ('nombre', 'empresa', 'email', 'telefono', 'rubro')
    readonly_fields = ('fecha', 'ip')
    date_hierarchy = 'fecha'
    ordering = ('-fecha',)
