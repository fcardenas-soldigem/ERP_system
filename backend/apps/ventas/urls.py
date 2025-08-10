from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import (
    OrdenVentaViewSet, 
    ClienteViewSet, 
    VentaViewSet,
    FacturaViewSet,
    ResumenVentasMensual,
    PagoVentaViewSet
)

router = DefaultRouter()
# Estas rutas se prefijan con /api/ventas/ desde config/urls.py
router.register(r'clientes', ClienteViewSet, basename='cliente')
router.register(r'ordenes', OrdenVentaViewSet, basename='orden-venta')
router.register(r'facturas', FacturaViewSet, basename='factura')
router.register(r'', VentaViewSet, basename='venta')  # Ruta base para ventas

# Crear router anidado para pagos
ventas_router = routers.NestedDefaultRouter(router, r'', lookup='venta')
ventas_router.register(r'pagos', PagoVentaViewSet, basename='venta-pagos')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(ventas_router.urls)),
    path('resumen/', ResumenVentasMensual.as_view(), name='resumen-ventas'),
] 