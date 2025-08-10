from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.empresas.serializers import EmpresaSerializer

User = get_user_model()

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            raise serializers.ValidationError("Se requiere correo electrónico y contraseña.")

        return data

class UserSerializer(serializers.ModelSerializer):
    empresa_data = EmpresaSerializer(source='empresa', read_only=True)
    nombre_completo = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 
            'email', 
            'nombre', 
            'apellido', 
            'nombre_completo',
            'empresa', 
            'empresa_data', 
            'is_active',
            'is_staff',
            'last_login'
        )
        read_only_fields = ('id', 'is_active', 'empresa_data', 'is_staff', 'last_login')

    def get_nombre_completo(self, obj):
        return f"{obj.nombre} {obj.apellido}".strip()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Agregar información adicional de la empresa si existe
        if instance.empresa:
            data['empresa_info'] = {
                'id': instance.empresa.id,
                'nombre': instance.empresa.nombre,
                'ruc': instance.empresa.ruc,
                'is_active': instance.empresa.is_active
            }
        return data

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user
