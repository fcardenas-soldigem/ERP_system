from rest_framework import serializers
from .models import Empresa

class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = ['id', 'nombre', 'ruc', 'direccion', 'telefono', 'email', 'is_active']
        read_only_fields = ['id', 'is_active'] 