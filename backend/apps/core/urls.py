from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EmpresaViewSet, 
    UsuarioViewSet, 
    PerfilViewSet, 
    UsuarioPermisosView, 
    consultar_dni, 
    consultar_ruc, 
    consultar_documento,
    consultar_tipo_cambio,
    consultar_tipo_cambio_mes
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)

router = DefaultRouter()
router.register(r'empresas', EmpresaViewSet, basename='empresa')
router.register(r'usuarios', UsuarioViewSet, basename='usuario')
router.register(r'perfiles', PerfilViewSet, basename='perfil')

urlpatterns = [
    # === AUTENTICACIÓN JWT ===
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # === PERMISOS DE USUARIO ===
    path('usuarios/permisos/<str:modulo>/', UsuarioPermisosView.as_view(), name='usuario-permisos'),
    
    # === API CONSULTAS RENIEC/SUNAT (apis.net.pe) ===
    # Consultas de documentos de identidad
    path('consultar-dni/', consultar_dni, name='consultar-dni'),  # GET ?dni=12345678
    path('consultar-ruc/', consultar_ruc, name='consultar-ruc'),  # GET ?ruc=12345678901
    path('consultar-documento/', consultar_documento, name='consultar-documento'),  # GET ?numero=123&tipo=dni
    
    # Consultas de tipo de cambio SUNAT
    path('tipo-cambio/', consultar_tipo_cambio, name='tipo-cambio'),  # GET ?fecha=2024-01-15 (opcional)
    path('tipo-cambio/mes/', consultar_tipo_cambio_mes, name='tipo-cambio-mes'),  # GET ?mes=1&año=2024
    
    # === RUTAS DEL ROUTER ===
    path('', include(router.urls)),
] 