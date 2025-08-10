from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Empresa
from .serializers import EmpresaSerializer

class EmpresaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = EmpresaSerializer
    queryset = Empresa.objects.none()

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Empresa.objects.none()
        
        try:
            return Empresa.objects.filter(id=self.request.user.empresa.id)
        except Exception as e:
            print(f"Error en EmpresaViewSet.get_queryset: {e}")
            return Empresa.objects.none() 