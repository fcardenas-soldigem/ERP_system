from rest_framework import serializers
from .models import Usuario, Perfil
from apps.empresas.serializers import EmpresaSerializer  # Importamos desde empresas

class UsuarioSerializer(serializers.ModelSerializer):
    empresa = EmpresaSerializer(read_only=True)
    
    class Meta:
        model = Usuario
        fields = ['id', 'usuario', 'empresa', 'rol', 'telefono', 'activo']

class PerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Perfil
        fields = ['id', 'usuario', 'telefono'] 