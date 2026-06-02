from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Usuario, Perfil
from apps.empresas.models import Empresa
from .serializers import EmpresaSerializer, UsuarioSerializer, PerfilSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from .permissions import ModulePermission
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from datetime import datetime
import json

from .services.documento_service import DocumentoService

class EmpresaViewSet(viewsets.ModelViewSet):
    serializer_class = EmpresaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Empresa.objects.all()
        if hasattr(user, 'empresa') and user.empresa:
            return Empresa.objects.filter(pk=user.empresa.pk)
        return Empresa.objects.none()

class UsuarioViewSet(viewsets.ModelViewSet):
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Usuario.objects.all()
        if hasattr(user, 'empresa') and user.empresa:
            return Usuario.objects.filter(usuario__empresa=user.empresa)
        return Usuario.objects.none()

class PerfilViewSet(viewsets.ModelViewSet):
    serializer_class = PerfilSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Perfil.objects.all()
        if hasattr(user, 'empresa') and user.empresa:
            return Perfil.objects.filter(usuario__empresa=user.empresa)
        return Perfil.objects.none()

class UsuarioPermisosView(APIView):
    permission_classes = [IsAuthenticated, ModulePermission]

    def get(self, request, modulo):
        try:
            # Verificar si el usuario es superusuario
            if request.user.is_superuser:
                return Response({
                    'ver': True,
                    'crear': True,
                    'editar': True,
                    'eliminar': True
                })

            # Aquí implementas la lógica para obtener los permisos específicos
            # del usuario según el módulo
            permisos = {
                'ver': self.check_permission(request.user, f'ver_{modulo}'),
                'crear': self.check_permission(request.user, f'crear_{modulo}'),
                'editar': self.check_permission(request.user, f'editar_{modulo}'),
                'eliminar': self.check_permission(request.user, f'eliminar_{modulo}')
            }
            
            return Response(permisos)
            
        except Exception as e:
            return Response(
                {'error': 'Error al obtener permisos'},
                status=500
            )

    def check_permission(self, user, permission_name):
        # Por ahora retornamos True para pruebas
        # Deberías implementar la lógica real según tus necesidades
        return True

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def consultar_dni(request):
    """
    Consulta datos de una persona por DNI
    """
    dni = request.GET.get('dni', '').strip()
    
    if not dni:
        return Response({
            'success': False,
            'error': 'El parámetro DNI es requerido'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    resultado = DocumentoService.consultar_dni(dni)
    
    if resultado['success']:
        return Response(resultado, status=status.HTTP_200_OK)
    else:
        return Response(resultado, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def consultar_ruc(request):
    """
    Consulta datos de una empresa por RUC
    """
    ruc = request.GET.get('ruc', '').strip()
    
    if not ruc:
        return Response({
            'success': False,
            'error': 'El parámetro RUC es requerido'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    resultado = DocumentoService.consultar_ruc(ruc)
    
    if resultado['success']:
        return Response(resultado, status=status.HTTP_200_OK)
    else:
        return Response(resultado, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def consultar_documento(request):
    """
    Consulta un documento (DNI o RUC) según su tipo
    """
    numero_documento = request.GET.get('numero', '').strip()
    tipo_documento = request.GET.get('tipo', '').strip().lower()
    
    if not numero_documento:
        return Response({
            'success': False,
            'error': 'El parámetro numero es requerido'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not tipo_documento:
        return Response({
            'success': False,
            'error': 'El parámetro tipo es requerido (dni o ruc)'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    resultado = DocumentoService.consultar_documento(numero_documento, tipo_documento)
    
    if resultado['success']:
        return Response(resultado, status=status.HTTP_200_OK)
    else:
        return Response(resultado, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def consultar_tipo_cambio(request):
    """
    Consulta el tipo de cambio de SUNAT
    Parámetros opcionales:
    - fecha: Fecha en formato YYYY-MM-DD (si no se proporciona, usa la fecha actual)
    """
    fecha = request.GET.get('fecha', '').strip()
    
    # Validar formato de fecha si se proporciona
    if fecha:
        try:
            datetime.strptime(fecha, '%Y-%m-%d')
        except ValueError:
            return Response({
                'success': False,
                'error': 'Formato de fecha inválido. Use YYYY-MM-DD'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    resultado = DocumentoService.consultar_tipo_cambio(fecha if fecha else None)
    
    if resultado['success']:
        return Response(resultado, status=status.HTTP_200_OK)
    else:
        return Response(resultado, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def consultar_tipo_cambio_mes(request):
    """
    Consulta los tipos de cambio de un mes específico
    Parámetros requeridos:
    - mes: Mes (1-12)
    - año: Año (YYYY)
    """
    try:
        mes = int(request.GET.get('mes', ''))
        año = int(request.GET.get('año', ''))
    except (ValueError, TypeError):
        return Response({
            'success': False,
            'error': 'Los parámetros mes y año son requeridos y deben ser números'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    resultado = DocumentoService.consultar_tipo_cambio_mes(mes, año)
    
    if resultado['success']:
        return Response(resultado, status=status.HTTP_200_OK)
    else:
        return Response(resultado, status=status.HTTP_400_BAD_REQUEST) 