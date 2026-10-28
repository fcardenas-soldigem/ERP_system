from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate, get_user_model
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .serializers import LoginSerializer, UserSerializer
from rest_framework import generics
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

_MAX_LOGIN_ATTEMPTS = 5
_LOCKOUT_SECONDS = 300  # 5 minutes

_REFRESH_COOKIE_MAX_AGE = int(
    settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()
)


# 0.3 — MISMO ORIGEN: el navegador llama a erp.soldigem.com.pe/api/… y Vercel
# reenvía a Cloud Run (rewrite en frontend/vercel.json). La cookie la emite,
# a ojos del navegador, erp.soldigem.com.pe → first-party: Safari iOS ya no la
# descarta al reabrir la PWA (con None + Cloud Run cross-site la bloqueaba).
# Sin Domain (host-only), SameSite=Lax, Secure, y solo viaja a /api/.
REFRESH_COOKIE_PATH = '/api/'


def _cookie_kwargs():
    return dict(
        httponly=True,
        secure=not settings.DEBUG,
        samesite='Lax',
        path=REFRESH_COOKIE_PATH,
    )


def _set_refresh_cookie(response, refresh_token_str):
    response.set_cookie(
        'refresh_token',
        refresh_token_str,
        max_age=_REFRESH_COOKIE_MAX_AGE,
        **_cookie_kwargs(),
    )


def _delete_refresh_cookie(response):
    # mismo path/samesite que al crearla; si difieren, el navegador no la borra
    kw = _cookie_kwargs()
    response.delete_cookie('refresh_token', path=kw['path'], samesite=kw['samesite'])
    # (la cookie de la sesión anterior vivía en el host *.run.app: el
    # navegador nunca la envía a erp.soldigem.com.pe, no hay que borrarla)


class CookieTokenObtainPairView(TokenObtainPairView):
    """Override SimpleJWT login: refresh token goes to httpOnly cookie, not body."""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            refresh_token_str = response.data.pop('refresh', None)
            if refresh_token_str:
                _set_refresh_cookie(response, refresh_token_str)
        return response


class CookieTokenRefreshView(APIView):
    """Read refresh token from httpOnly cookie, return new access token."""
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        refresh_token_str = request.COOKIES.get('refresh_token')
        if not refresh_token_str:
            return Response(
                {'error': 'No se encontró el refresh token'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            token = RefreshToken(refresh_token_str)
            access_token = str(token.access_token)
            response = Response({'access': access_token})

            if settings.SIMPLE_JWT.get('ROTATE_REFRESH_TOKENS', False):
                if settings.SIMPLE_JWT.get('BLACKLIST_AFTER_ROTATION', False):
                    token.blacklist()
                user_id_claim = settings.SIMPLE_JWT.get('USER_ID_CLAIM', 'user_id')
                user = User.objects.get(id=token[user_id_claim])
                new_refresh = RefreshToken.for_user(user)
                _set_refresh_cookie(response, str(new_refresh))

            return response

        except TokenError:
            response = Response(
                {'error': 'Token inválido o expirado'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            _delete_refresh_cookie(response)
            return response
        except User.DoesNotExist:
            response = Response(
                {'error': 'Usuario no encontrado'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            _delete_refresh_cookie(response)
            return response


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown')).split(',')[0].strip()
        cache_key = f'login_attempts:{ip}'
        attempts = cache.get(cache_key, 0)

        if attempts >= _MAX_LOGIN_ATTEMPTS:
            logger.warning('Login bloqueado por brute force — ip=%s', ip)
            return Response(
                {'error': 'Demasiados intentos fallidos. Intente en 5 minutos.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        user = authenticate(email=email, password=password)

        if user is None:
            cache.set(cache_key, attempts + 1, _LOCKOUT_SECONDS)
            logger.warning('Login fallido — ip=%s', ip)  # sin email en logs (dato personal)
            return Response({'error': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

        # Reset counter on success
        cache.delete(cache_key)

        # SEGURIDAD multi-tenant: un usuario sin empresa NUNCA se asigna automáticamente
        # a la primera empresa (antes caía en Empresa.objects.first() = tenant 1 y veía
        # sus datos). Debe provisionarse con `crear_tenant` o asignarse en el admin.
        if not user.empresa_id:
            logger.warning('Login rechazado: usuario sin empresa — user_id=%s', user.id)
            return Response(
                {'error': 'Tu usuario no tiene una empresa asignada. Contacta al administrador.'},
                status=status.HTTP_403_FORBIDDEN
            )

        logger.info('Login exitoso — user_id=%s empresa_id=%s', user.id, user.empresa_id)
        refresh = RefreshToken.for_user(user)
        return Response({
            'token': str(refresh.access_token),
            'user': UserSerializer(user).data
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token_str = request.data.get('refresh') or request.COOKIES.get('refresh_token')

        response = Response({'message': 'Sesión cerrada correctamente'})
        _delete_refresh_cookie(response)

        if not refresh_token_str:
            return response

        try:
            token = RefreshToken(refresh_token_str)
            token.blacklist()
            logger.info('Logout exitoso — user_id=%s', request.user.id)
        except TokenError:
            pass  # Token ya inválido, cookie ya eliminada

        return response

class UserProfileView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def get(self, request, *args, **kwargs):
        try:
            
            user = self.get_object()
            serializer = self.get_serializer(user)
            data = serializer.data
            
            # Agregar información adicional
            data['has_empresa'] = bool(user.empresa)
            if user.empresa:
                data['empresa_status'] = {
                    'is_active': user.empresa.is_active,
                    'created_at': user.empresa.created_at.isoformat() if hasattr(user.empresa, 'created_at') else None,
                }
            
            return Response(data)
        except Exception:
            logger.exception('Error en UserProfileView')
            return Response(
                {'error': 'Error interno'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
