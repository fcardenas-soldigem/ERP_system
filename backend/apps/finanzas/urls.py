from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    FinanzasDashboardView,
    CategoriaGastoViewSet,
    GastoOperativoViewSet,
    GastoRecurrenteViewSet,
)

router = DefaultRouter()
router.register(r'categorias', CategoriaGastoViewSet, basename='categoria-gasto')
router.register(r'gastos', GastoOperativoViewSet, basename='gasto-operativo')
router.register(r'recurrentes', GastoRecurrenteViewSet, basename='gasto-recurrente')

urlpatterns = [
    path('dashboard/', FinanzasDashboardView.as_view(), name='finanzas-dashboard'),
    path('', include(router.urls)),
]
