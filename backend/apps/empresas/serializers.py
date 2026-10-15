from rest_framework import serializers

from apps.core.uploads import field_url_safe
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
            'modo_inventario',  # B4/D6 — lectura y escritura
        ]
        read_only_fields = ['id', 'uuid', 'is_active', 'logo_url', 'firma_elaborado_url', 'firma_aprobado_url']

    def _build_url(self, field):
        # field_url_safe nunca lanza: devuelve None si el archivo falta o el storage
        # no puede resolver la URL (evita 500 en el serializer).
        url = field_url_safe(field)
        if not url:
            return None
        request = self.context.get('request')
        # Las URLs firmadas de GCS ya son absolutas; build_absolute_uri las respeta.
        return request.build_absolute_uri(url) if request else url

    def get_logo_url(self, obj):
        return self._build_url(obj.logo)

    def get_firma_elaborado_url(self, obj):
        return self._build_url(obj.firma_elaborado)

    def get_firma_aprobado_url(self, obj):
        return self._build_url(obj.firma_aprobado)