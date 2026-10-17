from rest_framework import serializers
from .models import Usuario, Perfil
from apps.empresas.serializers import EmpresaSerializer  # Importamos desde empresas
from apps.core.serializers_base import EmpresaScopedModelSerializer


# `usuario` (FK a CustomUser, que tiene `empresa`) acotado al tenant: antes se podía crear un
# Usuario/Perfil apuntando a un usuario de otra empresa.
class UsuarioSerializer(EmpresaScopedModelSerializer):
    empresa = EmpresaSerializer(read_only=True)
    
    class Meta:
        model = Usuario
        fields = ['id', 'usuario', 'empresa', 'rol', 'telefono', 'activo']

class PerfilSerializer(EmpresaScopedModelSerializer):
    class Meta:
        model = Perfil
        # 'telefono' no existe en Perfil → ImproperlyConfigured (500) en toda la ruta.
        fields = ['id', 'usuario', 'fecha_nacimiento', 'direccion', 'foto'] 