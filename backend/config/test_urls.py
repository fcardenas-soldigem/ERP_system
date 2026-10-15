"""URLconf mínima para tests.

Evita importar apps.ml_models.urls (que carga el stack de ML: joblib/sklearn),
no instalado en el entorno de desarrollo. Los tests de servicios/modelos no
necesitan las rutas HTTP.

Se montan solo las rutas que algún test ejerce vía HTTP.
"""
from django.urls import path, include

urlpatterns = [
    path('api/leads/', include('apps.leads.urls')),  # tests de captura de leads
    path('api/auth/', include('apps.authentication.urls')),  # aislamiento (perfil) + /profile/ (hotfix)
    path('api/compras/', include('apps.compras.urls')),  # escritura multipart (comprobante)
    path('api/ventas/', include('apps.ventas.urls')),  # aislamiento + escritura (comprobante)
    path('api/empresas/', include('apps.empresas.urls')),  # escritura multipart (logo)
]
