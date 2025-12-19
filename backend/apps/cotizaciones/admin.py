from django.contrib import admin
from .models import Cotizacion, DetalleCotizacion


class DetalleCotizacionInline(admin.TabularInline):
    model = DetalleCotizacion
    extra = 1
    fields = ['producto', 'codigo', 'descripcion', 'cantidad', 'precio_unitario', 'descuento_item', 'subtotal']
    readonly_fields = ['subtotal']


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = [
        'numero', 'cliente', 'asunto', 'fecha_emision',
        'fecha_vencimiento', 'estado', 'total', 'moneda'
    ]
    list_filter = ['estado', 'moneda', 'fecha_emision', 'empresa']
    search_fields = ['numero', 'asunto', 'cliente__nombre', 'cliente__documento']
    readonly_fields = ['numero', 'fecha_emision', 'subtotal', 'igv', 'total', 'fecha_creacion', 'fecha_modificacion']
    inlines = [DetalleCotizacionInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('numero', 'empresa', 'cliente', 'usuario_creador', 'asunto', 'descripcion')
        }),
        ('Fechas', {
            'fields': ('fecha_emision', 'fecha_vencimiento', 'fecha_aceptacion')
        }),
        ('Estado y Moneda', {
            'fields': ('estado', 'moneda')
        }),
        ('Valores', {
            'fields': ('subtotal', 'descuento', 'incluye_igv', 'porcentaje_igv', 'igv', 'total')
        }),
        ('Condiciones Comerciales', {
            'fields': ('forma_pago', 'tiempo_entrega', 'lugar_entrega', 'validez_oferta')
        }),
        ('Notas y Observaciones', {
            'fields': ('notas', 'terminos_condiciones'),
            'classes': ('collapse',)
        }),
        ('Relaciones', {
            'fields': ('venta',),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DetalleCotizacion)
class DetalleCotizacionAdmin(admin.ModelAdmin):
    list_display = [
        'cotizacion', 'codigo', 'descripcion', 'cantidad',
        'precio_unitario', 'subtotal'
    ]
    list_filter = ['cotizacion__empresa']
    search_fields = ['descripcion', 'codigo', 'cotizacion__numero']
    readonly_fields = ['subtotal']

