from rest_framework import serializers

from .models import Lead


class LeadSerializer(serializers.ModelSerializer):
    # Honeypot anti-spam: campo señuelo oculto por CSS en el frontend. Un bot lo
    # rellena, un humano no. write_only y no es un campo del modelo.
    website = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = Lead
        fields = [
            'id', 'nombre', 'empresa', 'email', 'telefono', 'rubro', 'tamano',
            'usa_inventario', 'mensaje', 'utm_source', 'utm_campaign',
            'fecha', 'website',
        ]
        read_only_fields = ['id', 'fecha']

    def validate_nombre(self, value):
        value = (value or '').strip()
        if len(value) < 2:
            raise serializers.ValidationError('Ingresa tu nombre.')
        return value

    def validate(self, attrs):
        # Si el honeypot vino lleno, es un bot: lo marcamos para descartar en la view.
        if (attrs.get('website') or '').strip():
            raise serializers.ValidationError({'detail': 'spam detectado'})
        attrs.pop('website', None)
        return attrs
