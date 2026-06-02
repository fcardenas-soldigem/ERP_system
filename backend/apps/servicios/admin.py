from django.contrib import admin
from .models import OrdenServicio, ItemOrdenServicio, SeguimientoProveedor, HistorialEstadoOS


class ItemOrdenServicioInline(admin.TabularInline):
    model = ItemOrdenServicio
    extra = 0


class SeguimientoProveedorInline(admin.TabularInline):
    model = SeguimientoProveedor
    extra = 0
    readonly_fields = ['created_at']


class HistorialEstadoOSInline(admin.TabularInline):
    model = HistorialEstadoOS
    extra = 0
    readonly_fields = ['fecha']


@admin.register(OrdenServicio)
class OrdenServicioAdmin(admin.ModelAdmin):
    list_display = ['numero', 'empresa', 'cliente', 'proveedor_reparacion',
                    'estado', 'prioridad', 'fecha_ingreso', 'fecha_entrega_estimada']
    list_filter = ['empresa', 'estado', 'prioridad']
    search_fields = ['numero', 'cliente__nombre']
    inlines = [ItemOrdenServicioInline, SeguimientoProveedorInline, HistorialEstadoOSInline]
    readonly_fields = ['numero', 'created_at', 'updated_at']
