from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


def health_check(request):
    """Endpoint de salud para Cloud Run liveness/readiness probes."""
    return JsonResponse({'status': 'ok'}, status=200)


urlpatterns = [
    path('api/health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/core/', include('apps.core.urls')),
    path('api/ai/', include('apps.ai_assistant.urls')),
    path('api/empresas/', include('apps.empresas.urls')),
    path('api/ventas/', include('apps.ventas.urls')),
    path('api/compras/', include('apps.compras.urls')),
    path('api/inventario/', include('apps.inventario.urls')),
    path('api/dashboard/', include('apps.dashboard.urls')),
    path('api/ml/', include('apps.ml_models.urls')),  # Machine Learning APIs
    path('api/', include('apps.cotizaciones.urls')),  # Cotizaciones
    path('api/produccion/', include('apps.produccion.urls')),  # Producción
    path('api/finanzas/',   include('apps.finanzas.urls')),    # Finanzas
    path('api/importador/', include('apps.importador.urls')), # Importador Excel
    path('api/guias/', include('apps.guias.urls')),           # Guías de Remisión
    path('api/servicios/', include('apps.servicios.urls')),  # Órdenes de Servicio
]

# Solo mapear estáticos vía Django si DEBUG=True. En producción usa WhiteNoise.
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# En producción, los estáticos los sirve WhiteNoise

