from django.urls import path
from .views import (
    DashboardResumen, 
    DashboardStatsView, 
    UtilityDashboardView, 
    IGVDashboardView, 
    DashboardResumenView,
    VentasAnualView,
    ComprasAnualView,
    UtilidadAnualView,
    VentasMensualView
)

urlpatterns = [
    # Ruta para el resumen del dashboard
    path('resumen/', DashboardResumen.as_view(), name='dashboard-resumen'),
    
    # Ruta para el resumen histórico
    path('resumen-historico/', DashboardResumenView.as_view(), name='dashboard-resumen-historico'),
    
    # Ruta para las estadísticas de cualquier número de días
    path('stats/<int:days>/', DashboardStatsView.as_view(), name='dashboard-stats'),

    path('utility/', UtilityDashboardView.as_view(), name='dashboard-utility'),
    path('igv/', IGVDashboardView.as_view(), name='dashboard-igv'),
    
    # Nuevas rutas para datos anuales
    path('ventas/anual/', VentasAnualView.as_view(), name='dashboard-ventas-anual'),
    path('compras/anual/', ComprasAnualView.as_view(), name='dashboard-compras-anual'),
    path('utilidad/anual/', UtilidadAnualView.as_view(), name='dashboard-utilidad-anual'),
    path('ventas/mensual/', VentasMensualView.as_view(), name='dashboard-ventas-mensual'),
] 