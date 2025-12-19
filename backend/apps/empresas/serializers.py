from rest_framework import serializers
from .models import Empresa

class EmpresaSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Empresa
        fields = ['id', 'nombre', 'ruc', 'direccion', 'telefono', 'email', 'logo', 'logo_url', 'is_active']
        read_only_fields = ['id', 'is_active', 'logo_url']
    
    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
        return None 