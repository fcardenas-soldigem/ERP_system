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
    venta_info = serializers.SerializerMethodField()
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    moneda_display = serializers.CharField(source='get_moneda_display', read_only=True)
    
    class Meta:
        model = Cotizacion
        fields = [
            'id', 'numero', 'empresa', 'empresa_info', 'cliente', 'cliente_info',
            'usuario_creador', 'asunto', 'descripcion', 'fecha_emision',
            'fecha_vencimiento', 'fecha_aceptacion', 'estado', 'estado_display',
            'moneda', 'moneda_display', 'subtotal', 'descuento', 'igv', 'total',
            'incluye_igv', 'precios_incluyen_igv', 'porcentaje_igv', 'forma_pago', 'pago_facturas', 'tiempo_entrega',
            'lugar_entrega', 'validez_oferta', 'notas', 'terminos_condiciones',
            'contacto_nombre', 'contacto_email',
            'venta', 'venta_info', 'detalles', 'fecha_creacion', 'fecha_modificacion'
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

    def get_venta_info(self, obj):
        """
        Información de la venta generada (si la cotización fue convertida).
        """
        if not obj.venta_id:
            return None
        venta = obj.venta
        return {
            'id': venta.id,
            'numero': venta.numero,
            'estado': venta.estado,
            'total': str(venta.total),
            'moneda': venta.moneda,
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
            instance.detalles.all().delete()
            if hasattr(instance, '_prefetched_objects_cache'):
                instance._prefetched_objects_cache.pop('detalles', None)
            for detalle_data in detalles_data:
                DetalleCotizacion.objects.create(cotizacion=instance, **detalle_data)

        # Recalcular totales con datos frescos
        if hasattr(instance, '_prefetched_objects_cache'):
            instance._prefetched_objects_cache.pop('detalles', None)
        instance.calcular_totales()
        
        return instance
    
    def validate_fecha_vencimiento(self, value):
        return value


class CotizacionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear/actualizar cotizaciones.
    Acepta 'cliente' (FK id) o los campos libres 'cliente_nombre'/'cliente_ruc'
    para auto-crear el cliente si no existe.
    """
    detalles = DetalleCotizacionSerializer(many=True)
    cliente_nombre = serializers.CharField(write_only=True, required=False, allow_blank=True, default='')
    cliente_ruc = serializers.CharField(write_only=True, required=False, allow_blank=True, default='')
    cliente_direccion = serializers.CharField(write_only=True, required=False, allow_blank=True, default='')
    cliente_email = serializers.EmailField(write_only=True, required=False, allow_blank=True, default='')
    cliente_contacto = serializers.CharField(write_only=True, required=False, allow_blank=True, default='')

    class Meta:
        model = Cotizacion
        fields = [
            'id', 'numero', 'cliente',
            'cliente_nombre', 'cliente_ruc', 'cliente_direccion',
            'cliente_email', 'cliente_contacto',
            'asunto', 'descripcion', 'fecha_vencimiento',
            'moneda', 'incluye_igv', 'precios_incluyen_igv', 'porcentaje_igv', 'descuento',
            'forma_pago', 'pago_facturas',
            'tiempo_entrega', 'lugar_entrega', 'validez_oferta',
            'notas', 'terminos_condiciones', 'contacto_nombre', 'contacto_email', 'detalles'
        ]
        read_only_fields = ['id', 'numero']
        extra_kwargs = {
            'cliente': {'required': False, 'allow_null': True},
        }

    def _resolve_cliente(self, validated_data, empresa, usuario):
        """
        Resuelve el cliente: usa el FK si viene, si no busca/crea por RUC o nombre.
        """
        cliente_nombre = validated_data.pop('cliente_nombre', '').strip()
        cliente_ruc = validated_data.pop('cliente_ruc', '').strip()
        cliente_direccion = validated_data.pop('cliente_direccion', '').strip()
        cliente_email = validated_data.pop('cliente_email', '').strip()
        cliente_contacto = validated_data.pop('cliente_contacto', '').strip()

        cliente = validated_data.get('cliente')
        if cliente:
            # Actualizar contacto/email aunque el cliente ya tenga FK
            update_fields = []
            if cliente_contacto and cliente.telefono != cliente_contacto:
                cliente.telefono = cliente_contacto
                update_fields.append('telefono')
            if cliente_email and cliente.email != cliente_email:
                cliente.email = cliente_email
                update_fields.append('email')
            if update_fields:
                cliente.save(update_fields=update_fields)
            return cliente

        if not cliente_nombre and not cliente_ruc:
            raise serializers.ValidationError({'cliente_nombre': 'Debe ingresar el nombre o RUC del cliente.'})

        # Buscar por RUC primero, luego por nombre
        from apps.ventas.models import Cliente
        qs = Cliente.objects.filter(empresa=empresa, activo=True)
        if cliente_ruc:
            obj = qs.filter(documento=cliente_ruc).first()
        else:
            obj = qs.filter(nombre__iexact=cliente_nombre).first()

        if not obj:
            tipo_doc = 'ruc' if cliente_ruc and len(cliente_ruc) == 11 else 'dni'
            obj = Cliente.objects.create(
                empresa=empresa,
                usuario=usuario,
                nombre=cliente_nombre or cliente_ruc,
                documento=cliente_ruc or '00000000',
                tipo_documento=tipo_doc,
                direccion=cliente_direccion or None,
                email=cliente_email or None,
                telefono=cliente_contacto or None,
            )
        else:
            update_fields = []
            if cliente_nombre and obj.nombre != cliente_nombre:
                obj.nombre = cliente_nombre
                update_fields.append('nombre')
            if cliente_direccion:
                obj.direccion = cliente_direccion
                update_fields.append('direccion')
            if cliente_email:
                obj.email = cliente_email
                update_fields.append('email')
            if cliente_contacto:
                obj.telefono = cliente_contacto
                update_fields.append('telefono')
            if update_fields:
                obj.save(update_fields=update_fields)

        validated_data['cliente'] = obj
        return obj

    def create(self, validated_data):
        request = self.context.get('request')
        empresa = request.user.empresa
        usuario = request.user
        self._resolve_cliente(validated_data, empresa, usuario)

        validated_data['empresa'] = empresa
        validated_data['usuario_creador'] = usuario
        if not validated_data.get('asunto'):
            validated_data['asunto'] = f"Cotización para {validated_data['cliente'].nombre}"

        detalles_data = validated_data.pop('detalles', [])
        cotizacion = Cotizacion.objects.create(**validated_data)
        for detalle_data in detalles_data:
            DetalleCotizacion.objects.create(cotizacion=cotizacion, **detalle_data)
        cotizacion.calcular_totales()
        return cotizacion

    def update(self, instance, validated_data):
        request = self.context.get('request')
        self._resolve_cliente(validated_data, request.user.empresa, request.user)

        if not validated_data.get('asunto'):
            validated_data['asunto'] = instance.asunto or f"Cotización para {validated_data.get('cliente', instance.cliente).nombre}"

        detalles_data = validated_data.pop('detalles', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if detalles_data is not None:
            instance.detalles.all().delete()
            # Limpiar cache de prefetch para que calcular_totales lea de la BD real
            if hasattr(instance, '_prefetched_objects_cache'):
                instance._prefetched_objects_cache.pop('detalles', None)
            for detalle_data in detalles_data:
                DetalleCotizacion.objects.create(cotizacion=instance, **detalle_data)

        # Limpiar cache nuevamente antes del cálculo final
        if hasattr(instance, '_prefetched_objects_cache'):
            instance._prefetched_objects_cache.pop('detalles', None)
        instance.calcular_totales()
        return instance

