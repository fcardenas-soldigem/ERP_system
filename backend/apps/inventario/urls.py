from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AlmacenViewSet, 
    CategoriaViewSet, 
    ProductoViewSet, 
    StockViewSet, 
    AjusteInventarioViewSet, 
    KardexViewSet,
    ResumenInventario,
    ProductoEstadisticasView,
    ValorInventarioViewSet,
    ImportarProductosAPIView,
    descargar_template,
    # Nuevas vistas para inventarios separados
    InventarioMateriasPrimasViewSet,
    InventarioProductosTerminadosViewSet,
    ResumenInventariosSeparadosView,
    ValidarStockProduccionView,
    # Carga masiva
    descargar_plantilla_inventario,
    cargar_inventario_masivo,
    validar_archivo_inventario,
)

# Crear el router
router = DefaultRouter()

# Registrar las vistas existentes
router.register(r'almacenes', AlmacenViewSet, basename='almacen')
router.register(r'categorias', CategoriaViewSet, basename='categoria')
router.register(r'productos', ProductoViewSet, basename='producto')
router.register(r'stocks', StockViewSet, basename='stock')
router.register(r'ajustes', AjusteInventarioViewSet, basename='ajuste')
router.register(r'kardex', KardexViewSet, basename='kardex')
router.register(r'valor-inventario', ValorInventarioViewSet, basename='valor-inventario')

# Nuevos ViewSets para inventarios separados
router.register(r'materias-primas', InventarioMateriasPrimasViewSet, basename='materias-primas')
router.register(r'productos-terminados', InventarioProductosTerminadosViewSet, basename='productos-terminados')

# Definir las URLs
urlpatterns = [
    # URLs existentes
    path('productos/importar/', ImportarProductosAPIView.as_view(), name='importar-productos'),
    path('productos/check-sku/', ProductoViewSet.as_view({'get': 'check_sku'}), name='check-sku'),
    path('resumen/', ResumenInventario.as_view(), name='resumen-inventario'),
    path('productos/estadisticas/', ProductoEstadisticasView.as_view(), name='producto-estadisticas'),
    path('productos/template/descargar/', descargar_template, name='descargar-template'),
    
    # Nuevas URLs para inventarios separados
    path('resumen-separado/', ResumenInventariosSeparadosView.as_view(), name='resumen-inventarios-separados'),
    path('validar-stock-produccion/', ValidarStockProduccionView.as_view(), name='validar-stock-produccion'),
    
    # Carga masiva de inventario
    path('carga-masiva/plantilla/', descargar_plantilla_inventario, name='plantilla-carga-masiva'),
    path('carga-masiva/cargar/', cargar_inventario_masivo, name='cargar-inventario-masivo'),
    path('carga-masiva/validar/', validar_archivo_inventario, name='validar-archivo-inventario'),
    
    # Router URLs
    path('', include(router.urls)),
]
