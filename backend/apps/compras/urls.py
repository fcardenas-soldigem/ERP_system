from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CompraViewSet,
    ProveedorViewSet,
    OrdenCompraViewSet,
    RecepcionCompraViewSet,
    ResumenComprasMensual,
    PagoCompraViewSet,
    descargar_template_compras
)

router = DefaultRouter()
router.register(r'compras', CompraViewSet, basename='compra')
router.register(r'proveedores', ProveedorViewSet, basename='proveedor')
router.register(r'ordenes', OrdenCompraViewSet, basename='orden')
router.register(r'recepciones', RecepcionCompraViewSet, basename='recepcion')
router.register(r'pagos', PagoCompraViewSet, basename='pago')
router.register(r'resumen', ResumenComprasMensual, basename='resumen-compras')

urlpatterns = [
    path('template/descargar/', descargar_template_compras, name='descargar-template-compras'),
    path('', include(router.urls)),
] 