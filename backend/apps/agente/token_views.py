"""CRUD de ApiToken para la UI del ERP ("Conectar Claude"). Auth de usuario (JWT/sesión).

El token en claro se devuelve UNA sola vez, al crearlo. Después solo se ve el prefijo.
Scoped por empresa: cada usuario ve/gestiona solo los tokens de su empresa.
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import HasEmpresaPermission

from .models import ApiToken
from .serializers import ApiTokenSerializer


class ApiTokenViewSet(viewsets.ModelViewSet):
    serializer_class = ApiTokenSerializer
    permission_classes = [IsAuthenticated, HasEmpresaPermission]
    http_method_names = ['get', 'post']  # list, retrieve, create, revocar (no hard-delete)

    def get_queryset(self):
        return ApiToken.objects.filter(empresa=self.request.user.empresa)

    def create(self, request, *args, **kwargs):
        nombre = (request.data.get('nombre') or '').strip() or 'Token MCP'
        try:
            dias = int(request.data.get('dias') or 90)
        except (TypeError, ValueError):
            dias = 90
        dias = max(1, min(dias, 365))  # siempre expira (1..365 días)
        token, raw = ApiToken.generar(
            empresa=request.user.empresa, nombre=nombre, creado_por=request.user, dias=dias)
        data = ApiTokenSerializer(token).data
        data['token'] = raw  # se muestra UNA vez; no se vuelve a poder leer
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def revocar(self, request, pk=None):
        token = self.get_object()
        token.revocar()
        return Response(ApiTokenSerializer(token).data)
