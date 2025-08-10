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
    descargar_template
)

# Crear el router
router = DefaultRouter()

# Registrar las vistas
router.register(r'almacenes', AlmacenViewSet, basename='almacen')
router.register(r'categorias', CategoriaViewSet, basename='categoria')
router.register(r'productos', ProductoViewSet, basename='producto')
router.register(r'stocks', StockViewSet, basename='stock')
router.register(r'ajustes', AjusteInventarioViewSet, basename='ajuste')
router.register(r'kardex', KardexViewSet, basename='kardex')
router.register(r'valor-inventario', ValorInventarioViewSet, basename='valor-inventario')

# Definir las URLs
urlpatterns = [
    path('productos/importar/', ImportarProductosAPIView.as_view(), name='importar-productos'),
    path('productos/check-sku/', ProductoViewSet.as_view({'get': 'check_sku'}), name='check-sku'),
    path('resumen/', ResumenInventario.as_view(), name='resumen-inventario'),
    path('productos/estadisticas/', ProductoEstadisticasView.as_view(), name='producto-estadisticas'),
    path('productos/template/descargar/', descargar_template, name='descargar-template'),
    path('', include(router.urls)),
]
