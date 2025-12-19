from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RecetaProductoViewSet, OrdenProduccionViewSet, DashboardProduccionView

router = DefaultRouter()
router.register(r'recetas', RecetaProductoViewSet, basename='receta')
router.register(r'ordenes', OrdenProduccionViewSet, basename='orden-produccion')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', DashboardProduccionView.as_view(), name='dashboard-produccion'),
]
