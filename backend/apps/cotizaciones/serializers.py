from rest_framework import serializers
from .models import Cotizacion, DetalleCotizacion
from apps.ventas.models import Cliente
from apps.inventario.models import Producto
from decimal import Decimal


class DetalleCotizacionSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_codigo = serializers.CharField(source='producto.codigo', read_only=True)
    
    class Meta:
        model = DetalleCotizacion
        fields = [
            'id', 'producto', 'producto_nombre', 'producto_codigo',
            'codigo', 'descripcion', 'cantidad', 'precio_unitario',
            'descuento_item', 'subtotal', 'orden'
        ]
        read_only_fields = ['subtotal']
    
    def validate(self, data):
        """
        Validar que al menos haya descripción o producto
        """
        if not data.get('descripcion') and not data.get('producto'):
            raise serializers.ValidationError(
                "Debe proporcionar una descripción o seleccionar un producto"
            )
        
        # Si hay producto, copiar información
        if data.get('producto'):
            producto = data['producto']
            if not data.get('descripcion'):
                data['descripcion'] = producto.nombre
            if not data.get('codigo'):
                data['codigo'] = producto.sku  # Usar 'sku' en lugar de 'codigo'
            if not data.get('precio_unitario'):
                data['precio_unitario'] = producto.precio_venta
        
        return data


class CotizacionListSerializer(serializers.ModelSerializer):
    """
    Serializer para listado de cotizaciones (sin detalles)
    """
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    usuario_nombre = serializers.CharField(source='usuario_creador.username', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    moneda_display = serializers.CharField(source='get_moneda_display', read_only=True)
    
    class Meta:
        model = Cotizacion
        fields = [
            'id', 'numero', 'cliente', 'cliente_nombre', 'asunto',
            'fecha_emision', 'fecha_vencimiento', 'estado', 'estado_display',
            'moneda', 'moneda_display', 'total', 'usuario_nombre'
        ]


class CotizacionSerializer(serializers.ModelSerializer):
    """
    Serializer completo para cotizaciones con detalles
    """
    detalles = DetalleCotizacionSerializer(many=True, required=False)
    cliente_info = serializers.SerializerMethodField()
    empresa_info = serializers.SerializerMethodField()
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    moneda_display = serializers.CharField(source='get_moneda_display', read_only=True)
    
    class Meta:
        model = Cotizacion
        fields = [
            'id', 'numero', 'empresa', 'empresa_info', 'cliente', 'cliente_info',
            'usuario_creador', 'asunto', 'descripcion', 'fecha_emision',
            'fecha_vencimiento', 'fecha_aceptacion', 'estado', 'estado_display',
            'moneda', 'moneda_display', 'subtotal', 'descuento', 'igv', 'total',
            'incluye_igv', 'porcentaje_igv', 'forma_pago', 'pago_facturas', 'tiempo_entrega',
            'lugar_entrega', 'validez_oferta', 'notas', 'terminos_condiciones',
            'venta', 'detalles', 'fecha_creacion', 'fecha_modificacion'
        ]
        read_only_fields = [
            'numero', 'subtotal', 'igv', 'total',
            'fecha_emision', 'fecha_creacion', 'fecha_modificacion'
        ]
    
    def get_cliente_info(self, obj):
        """
        Información completa del cliente
        """
        return {
            'id': obj.cliente.id,
            'nombre': obj.cliente.nombre,
            'documento': obj.cliente.documento,
            'tipo_documento': obj.cliente.tipo_documento,
            'direccion': obj.cliente.direccion,
            'telefono': obj.cliente.telefono,
            'email': obj.cliente.email,
        }
    
    def get_empresa_info(self, obj):
        """
        Información completa de la empresa
        """
        return {
            'id': obj.empresa.id,
            'nombre': obj.empresa.nombre,
            'ruc': obj.empresa.ruc,
            'direccion': obj.empresa.direccion,
            'telefono': obj.empresa.telefono,
            'email': obj.empresa.email,
            'logo': obj.empresa.logo.url if obj.empresa.logo else None,
        }
    
    def create(self, validated_data):
        """
        Crear cotización con sus detalles
        """
        detalles_data = validated_data.pop('detalles', [])
        cotizacion = Cotizacion.objects.create(**validated_data)
        
        # Crear detalles
        for detalle_data in detalles_data:
            DetalleCotizacion.objects.create(cotizacion=cotizacion, **detalle_data)
        
        # Calcular totales
        cotizacion.calcular_totales()
        
        return cotizacion
    
    def update(self, instance, validated_data):
        """
        Actualizar cotización y sus detalles
        """
        detalles_data = validated_data.pop('detalles', None)
        
        # Actualizar campos de la cotización
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Actualizar detalles si se proporcionan
        if detalles_data is not None:
            # Eliminar detalles existentes
            instance.detalles.all().delete()
            
            # Crear nuevos detalles
            for detalle_data in detalles_data:
                DetalleCotizacion.objects.create(cotizacion=instance, **detalle_data)
        
        # Recalcular totales
        instance.calcular_totales()
        
        return instance
    
    def validate_fecha_vencimiento(self, value):
        """
        Validar que la fecha de vencimiento sea futura
        """
        from django.utils import timezone
        if value < timezone.now().date():
            raise serializers.ValidationError(
                "La fecha de vencimiento debe ser posterior a la fecha actual"
            )
        return value


class CotizacionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para crear cotizaciones rápidamente
    """
    detalles = DetalleCotizacionSerializer(many=True)
    
    class Meta:
        model = Cotizacion
        fields = [
            'cliente', 'asunto', 'descripcion', 'fecha_vencimiento',
            'moneda', 'incluye_igv', 'descuento', 'forma_pago', 'pago_facturas',
            'tiempo_entrega', 'lugar_entrega', 'validez_oferta',
            'notas', 'terminos_condiciones', 'detalles'
        ]
    
    def create(self, validated_data):
        """
        Crear cotización con empresa y usuario del contexto
        """
        request = self.context.get('request')
        validated_data['empresa'] = request.user.empresa
        validated_data['usuario_creador'] = request.user
        
        detalles_data = validated_data.pop('detalles')
        cotizacion = Cotizacion.objects.create(**validated_data)
        
        for detalle_data in detalles_data:
            DetalleCotizacion.objects.create(cotizacion=cotizacion, **detalle_data)
        
        cotizacion.calcular_totales()
        
        return cotizacion

