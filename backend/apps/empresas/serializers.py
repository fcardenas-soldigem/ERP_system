from rest_framework import serializers
from .models import Empresa

class EmpresaSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    firma_elaborado_url = serializers.SerializerMethodField()
    firma_aprobado_url = serializers.SerializerMethodField()

    class Meta:
        model = Empresa
        fields = [
            'id', 'uuid', 'nombre', 'ruc', 'direccion', 'telefono', 'email',
            'logo', 'logo_url', 'firma_elaborado', 'firma_elaborado_url',
            'firma_aprobado', 'firma_aprobado_url', 'is_active', 'tipo_cambio_usd',
        ]
        read_only_fields = ['id', 'uuid', 'is_active', 'logo_url', 'firma_elaborado_url', 'firma_aprobado_url']

    def _build_url(self, field):
        request = self.context.get('request')
        if field and request:
            return request.build_absolute_uri(field.url)
        return None

    def get_logo_url(self, obj):
        return self._build_url(obj.logo)

    def get_firma_elaborado_url(self, obj):
        return self._build_url(obj.firma_elaborado)

    def get_firma_aprobado_url(self, obj):
        return self._build_url(obj.firma_aprobado)