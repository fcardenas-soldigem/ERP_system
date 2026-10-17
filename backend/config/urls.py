from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from apps.authentication.views import CookieTokenObtainPairView, CookieTokenRefreshView
from apps.agente.mcp import MCPView


def health_check(request):
    """Endpoint de salud para Cloud Run liveness/readiness probes."""
    return JsonResponse({'status': 'ok'}, status=200)


urlpatterns = [
    path('api/health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('api/token/', CookieTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/core/', include('apps.core.urls')),
    path('api/ai/', include('apps.ai_assistant.urls')),
    path('api/empresas/', include('apps.empresas.urls')),
    path('api/ventas/', include('apps.ventas.urls')),
    path('api/compras/', include('apps.compras.urls')),
    path('api/inventario/', include('apps.inventario.urls')),
    path('api/dashboard/', include('apps.dashboard.urls')),
    path('api/', include('apps.cotizaciones.urls')),  # Cotizaciones
    path('api/produccion/', include('apps.produccion.urls')),  # Producción
    path('api/finanzas/',   include('apps.finanzas.urls')),    # Finanzas
    path('api/importador/', include('apps.importador.urls')), # Importador Excel
    path('api/guias/', include('apps.guias.urls')),           # Guías de Remisión
    path('api/servicios/', include('apps.servicios.urls')),  # Órdenes de Servicio
    path('api/leads/', include('apps.leads.urls')),          # Landing: captura de leads
    path('api/mcp/', MCPView.as_view(), name='mcp'),         # MCP remoto (agente Fase 2)
    path('api/agente/', include('apps.agente.urls')),        # Tokens de API (UI "Conectar Claude")
]



def rutas_ml(enabled):
    """Rutas /api/ml/ solo con ML_ENABLED=true (default False → 404). El include es opcional:
    si faltan dependencias pesadas (joblib/sklearn) no debe romper el resto del URLconf."""
    if not enabled:
        return []
    try:
        return [path('api/ml/', include('apps.ml_models.urls'))]
    except Exception as _ml_exc:  # pragma: no cover
        import logging
        logging.getLogger(__name__).warning('ml_models URLs deshabilitadas: %s', _ml_exc)
        return []


urlpatterns += rutas_ml(settings.ML_ENABLED)

# Solo mapear estáticos vía Django si DEBUG=True. En producción usa WhiteNoise.
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# En producción, los estáticos los sirve WhiteNoise

