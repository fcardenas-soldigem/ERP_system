from django.contrib import admin
from .models import Producto, Stock, Categoria, Almacen

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['sku', 'nombre', 'categoria', 'precio_compra', 'precio_venta', 'stock_total', 'is_active']
    list_filter = ['categoria', 'is_active', 'empresa']
    search_fields = ['nombre', 'sku', 'codigo_barra']
    readonly_fields = ['stock_total', 'margen']
    autocomplete_fields = ['categoria']
    
    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if not request.user.is_superuser:
            queryset = queryset.filter(empresa=request.user.empresa)
        return queryset, use_distinct

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(empresa=request.user.empresa)
        return qs

    class Media:
        js = ('admin/js/vendor/jquery/jquery.min.js', 'admin/js/jquery.init.js')
        css = {
            'all': ('admin/css/vendor/select2/select2.min.css',)
        }

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('producto', 'almacen', 'cantidad')
    list_filter = ('almacen',)
    search_fields = ('producto__nombre', 'producto__sku')

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'descripcion', 'empresa')
    search_fields = ('nombre',)
    list_filter = ('empresa',)

@admin.register(Almacen)
class AlmacenAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'direccion', 'empresa')
    search_fields = ('nombre',)
    list_filter = ('empresa',)
