from django.contrib import admin
from .models import (
    RecetaProducto, RecetaDetalle, OrdenProduccion, ConsumoReal,
    ProductionOutput, ProductionWaste, ProductionCost
)


class RecetaDetalleInline(admin.TabularInline):
    model = RecetaDetalle
    extra = 1
    fields = ['insumo', 'cantidad', 'unidad_medida', 'costo_unitario', 'notas']


@admin.register(RecetaProducto)
class RecetaProductoAdmin(admin.ModelAdmin):
    list_display = [
        'nombre', 'producto_terminado', 'cantidad_producida',
        'version', 'is_active', 'empresa', 'created_at'
    ]
    list_filter = ['is_active', 'empresa', 'created_at']
    search_fields = ['nombre', 'producto_terminado__nombre', 'producto_terminado__sku']
    inlines = [RecetaDetalleInline]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('empresa', 'producto_terminado', 'nombre', 'cantidad_producida')
        }),
        ('Costos Estimados', {
            'fields': ('costo_mano_obra', 'costo_indirecto', 'tiempo_estimado')
        }),
        ('Control de Versión', {
            'fields': ('version', 'is_active', 'notas')
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RecetaDetalle)
class RecetaDetalleAdmin(admin.ModelAdmin):
    list_display = [
        'receta', 'insumo', 'cantidad', 'unidad_medida',
        'costo_unitario', 'costo_total'
    ]
    list_filter = ['receta__empresa', 'unidad_medida']
    search_fields = ['receta__nombre', 'insumo__nombre', 'insumo__sku']
    readonly_fields = ['created_at', 'updated_at', 'costo_total']


class ConsumoRealInline(admin.TabularInline):
    model = ConsumoReal
    extra = 0
    fields = [
        'insumo', 'cantidad_teorica', 'cantidad_real',
        'merma', 'costo_unitario', 'notas'
    ]
    readonly_fields = ['cantidad_teorica', 'costo_unitario']


@admin.register(OrdenProduccion)
class OrdenProduccionAdmin(admin.ModelAdmin):
    list_display = [
        'numero', 'receta', 'estado', 'cantidad_planificada',
        'cantidad_producida', 'fecha_programada', 'responsable', 'empresa'
    ]
    list_filter = ['estado', 'empresa', 'fecha_programada', 'created_at']
    search_fields = [
        'numero', 'receta__nombre',
        'receta__producto_terminado__nombre'
    ]
    inlines = [ConsumoRealInline]
    readonly_fields = ['numero', 'created_at', 'updated_at', 'created_by']
    
    fieldsets = (
        ('Información Básica', {
            'fields': (
                'numero', 'empresa', 'receta', 'estado',
                'responsable', 'created_by'
            )
        }),
        ('Planificación', {
            'fields': (
                'cantidad_planificada', 'fecha_programada',
                'almacen_insumos', 'almacen_destino'
            )
        }),
        ('Ejecución', {
            'fields': (
                'cantidad_producida', 'fecha_inicio', 'fecha_fin',
                'tiempo_real', 'observaciones'
            )
        }),
        ('Costos Reales', {
            'fields': ('costo_mano_obra_real', 'costo_indirecto_real')
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # Si es nuevo
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ConsumoReal)
class ConsumoRealAdmin(admin.ModelAdmin):
    list_display = [
        'orden_produccion', 'insumo', 'cantidad_teorica',
        'cantidad_real', 'diferencia', 'merma',
        'costo_total', 'costo_merma'
    ]
    list_filter = ['orden_produccion__empresa', 'orden_produccion__estado']
    search_fields = [
        'orden_produccion__numero', 'insumo__nombre', 'insumo__sku'
    ]
    readonly_fields = [
        'diferencia', 'porcentaje_diferencia', 'porcentaje_merma',
        'costo_total', 'costo_merma', 'created_at', 'updated_at'
    ]


@admin.register(ProductionOutput)
class ProductionOutputAdmin(admin.ModelAdmin):
    list_display = [
        'orden_produccion', 'numero_lote', 'cantidad_producida',
        'fecha_produccion', 'created_at'
    ]
    list_filter = ['fecha_produccion', 'orden_produccion__empresa']
    search_fields = ['orden_produccion__numero', 'numero_lote']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ProductionWaste)
class ProductionWasteAdmin(admin.ModelAdmin):
    list_display = [
        'orden_produccion', 'producto', 'cantidad_desperdiciada',
        'motivo', 'costo_total_merma', 'created_at'
    ]
    list_filter = ['motivo', 'orden_produccion__empresa', 'created_at']
    search_fields = [
        'orden_produccion__numero', 'producto__nombre', 'producto__sku'
    ]
    readonly_fields = ['costo_total_merma', 'created_at']


@admin.register(ProductionCost)
class ProductionCostAdmin(admin.ModelAdmin):
    list_display = [
        'orden_produccion', 'costo_materiales', 'costo_mano_obra',
        'costo_indirecto', 'costo_mermas', 'costo_total',
        'costo_unitario', 'cantidad_producida'
    ]
    list_filter = ['orden_produccion__empresa', 'created_at']
    search_fields = ['orden_produccion__numero']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Orden', {
            'fields': ('orden_produccion',)
        }),
        ('Costos Detallados', {
            'fields': (
                'costo_materiales', 'costo_mano_obra',
                'costo_indirecto', 'costo_mermas'
            )
        }),
        ('Totales', {
            'fields': ('costo_total', 'costo_unitario', 'cantidad_producida')
        }),
        ('Notas', {
            'fields': ('notas',)
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
