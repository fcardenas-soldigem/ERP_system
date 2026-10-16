from rest_framework import serializers

from .models import ApiToken


class ApiTokenSerializer(serializers.ModelSerializer):
    estado = serializers.CharField(read_only=True)
    activo = serializers.BooleanField(read_only=True)

    class Meta:
        model = ApiToken
        fields = [
            'id', 'nombre', 'token_prefix', 'scopes', 'created_at',
            'last_used_at', 'expires_at', 'revoked_at', 'estado', 'activo',
        ]
        read_only_fields = fields
