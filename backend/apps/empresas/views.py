from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import Empresa
from .serializers import EmpresaSerializer

class EmpresaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = EmpresaSerializer
    queryset = Empresa.objects.none()
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Empresa.objects.none()
        
        try:
            if hasattr(self.request.user, 'empresa') and self.request.user.empresa:
                return Empresa.objects.filter(id=self.request.user.empresa.id)
            else:
                return Empresa.objects.none()
        except Exception as e:
            return Empresa.objects.none()
    
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_logo(self, request, pk=None):
        """
        Subir o actualizar el logo de la empresa
        """
        empresa = self.get_object()
        
        if 'logo' not in request.FILES:
            return Response(
                {'error': 'No se proporcionó ningún archivo'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Eliminar logo anterior si existe
        if empresa.logo:
            empresa.logo.delete(save=False)
        
        empresa.logo = request.FILES['logo']
        empresa.save()
        
        serializer = self.get_serializer(empresa, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['delete'])
    def delete_logo(self, request, pk=None):
        """
        Eliminar el logo de la empresa
        """
        empresa = self.get_object()
        
        if empresa.logo:
            empresa.logo.delete(save=True)
            return Response({'message': 'Logo eliminado correctamente'})
        
        return Response(
            {'error': 'La empresa no tiene logo'},
            status=status.HTTP_404_NOT_FOUND
        ) 