"""JWTAuthentication que, al autenticar, publica user_id/empresa_id en el contexto de
logging (apps.core.logging_json). Sustituye a la de SimpleJWT en REST_FRAMEWORK."""
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.logging_json import set_usuario_actual


class JWTAuthenticationConContexto(JWTAuthentication):
    def authenticate(self, request):
        resultado = super().authenticate(request)
        if resultado is not None:
            set_usuario_actual(resultado[0])
        return resultado
