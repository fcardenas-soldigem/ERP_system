"""URLconf mínima para tests.

Evita importar apps.ml_models.urls (que carga el stack de ML: joblib/sklearn),
no instalado en el entorno de desarrollo. Los tests de servicios/modelos no
necesitan las rutas HTTP.

Se montan solo las rutas que algún test ejerce vía HTTP.
"""
from django.urls import path, include

from apps.agente.mcp import MCPView

urlpatterns = [
    path('api/leads/', include('apps.leads.urls')),  # tests de captura de leads
    path('api/auth/', include('apps.authentication.urls')),  # aislamiento (perfil) + /profile/ (hotfix)
    path('api/compras/', include('apps.compras.urls')),  # escritura multipart (comprobante)
    path('api/ventas/', include('apps.ventas.urls')),  # aislamiento + escritura (comprobante)
    path('api/empresas/', include('apps.empresas.urls')),  # escritura multipart (logo)
    path('api/mcp/', MCPView.as_view(), name='mcp'),  # tests del MCP
    path('api/agente/', include('apps.agente.urls')),  # tests de tokens
]
