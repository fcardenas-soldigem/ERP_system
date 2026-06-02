from rest_framework import serializers
from .models import RecetaProducto, RecetaDetalle, OrdenProduccion, ConsumoReal, HistorialOrdenProduccion
from apps.inventario.models import Producto, Almacen, InventarioMateriasPrimas
from apps.empresas.models import Empresa
from django.contrib.auth import get_user_model

User = get_user_model()


class RecetaDetalleSerializer(serializers.ModelSerializer):
    """Serializer para detalles de receta (insumos)"""
    insumo_nombre = serializers.CharField(source='insumo.nombre', read_only=True)
    insumo_sku = serializers.CharField(source='insumo.sku', read_only=True)
    insumo_unidad_medida = serializers.CharField(source='insumo.unidad_medida', read_only=True)
    insumo_stock = serializers.SerializerMethodField()
    costo_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = RecetaDetalle
        fields = [
            'id', 'insumo', 'insumo_nombre', 'insumo_sku', 'insumo_unidad_medida',
            'insumo_stock', 'cantidad', 'unidad_medida', 'costo_unitario', 'costo_total', 'notas'
        ]
        extra_kwargs = {
            'unidad_medida': {'required': False, 'allow_blank': True},
            'costo_unitario': {'required': False},
            'notas': {'required': False, 'allow_blank': True},
        }
    
    def get_insumo_stock(self, obj):
        """Obtiene el stock disponible del insumo desde InventarioMateriasPrimas"""
        if obj.insumo:
            # Intentar obtener del inventario de materias primas primero
            try:
                inv_mp = InventarioMateriasPrimas.objects.filter(
                    producto=obj.insumo,
                    empresa=obj.receta.empresa
                ).first()
                if inv_mp:
                    return float(inv_mp.cantidad_disponible or 0)
            except Exception:
                pass
            # Fallback al stock_total del producto
            return float(obj.insumo.stock_total or 0)
        return 0
    
    def validate(self, data):
        """Validaciones personalizadas"""
        if data.get('cantidad', 0) <= 0:
            raise serializers.ValidationError({'cantidad': 'La cantidad debe ser mayor a 0'})
        
        # Si no viene unidad_medida, asignarla del insumo
        if not data.get('unidad_medida') and data.get('insumo'):
            data['unidad_medida'] = data['insumo'].unidad_medida
        
        # Si no viene costo_unitario, asignarlo del insumo
        if not data.get('costo_unitario') and data.get('insumo'):
            data['costo_unitario'] = data['insumo'].precio_compra
        
        return data


class RecetaProductoListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listado de recetas"""
    producto_terminado_nombre = serializers.CharField(source='producto_terminado.nombre', read_only=True)
    producto_terminado_sku = serializers.CharField(source='producto_terminado.sku', read_only=True)
    total_insumos = serializers.SerializerMethodField()
    costo_teorico = serializers.SerializerMethodField()
    
    class Meta:
        model = RecetaProducto
        fields = [
            'id', 'nombre', 'producto_terminado', 'producto_terminado_nombre',
            'producto_terminado_sku', 'cantidad_producida', 'version',
            'is_active', 'total_insumos', 'costo_teorico', 'tiempo_estimado'
        ]
    
    def get_total_insumos(self, obj):
        return obj.detalles.count()
    
    def get_costo_teorico(self, obj):
        costos = obj.calcular_costo_teorico()
        return costos['costo_unitario']


class RecetaProductoSerializer(serializers.ModelSerializer):
    """Serializer completo para recetas con detalles"""
    detalles = RecetaDetalleSerializer(many=True, read_only=True)
    producto_terminado_nombre = serializers.CharField(source='producto_terminado.nombre', read_only=True)
    producto_terminado_sku = serializers.CharField(source='producto_terminado.sku', read_only=True)
    costos = serializers.SerializerMethodField()
    
    class Meta:
        model = RecetaProducto
        fields = [
            'id', 'empresa', 'producto_terminado', 'producto_terminado_nombre',
            'producto_terminado_sku', 'nombre', 'cantidad_producida',
            'tiempo_estimado', 'costo_mano_obra', 'costo_indirecto',
            'is_active', 'version', 'notas', 'detalles', 'costos',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['empresa', 'created_at', 'updated_at']
    
    def get_costos(self, obj):
        return obj.calcular_costo_teorico()
    
    def validate(self, data):
        """Validaciones personalizadas"""
        if data.get('cantidad_producida', 0) <= 0:
            raise serializers.ValidationError({
                'cantidad_producida': 'La cantidad producida debe ser mayor a 0'
            })
        return data


class RecetaProductoCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear/editar recetas con detalles"""
    detalles = RecetaDetalleSerializer(many=True)
    
    class Meta:
        model = RecetaProducto
        fields = [
            'producto_terminado', 'nombre', 'cantidad_producida',
            'tiempo_estimado', 'costo_mano_obra', 'costo_indirecto',
            'is_active', 'version', 'notas', 'detalles'
        ]
    
    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles', [])
        empresa = self.context['request'].user.empresa
        receta = RecetaProducto.objects.create(empresa=empresa, **validated_data)
        
        for detalle_data in detalles_data:
            RecetaDetalle.objects.create(receta=receta, **detalle_data)
        
        return receta
    
    def update(self, instance, validated_data):
        detalles_data = validated_data.pop('detalles', None)
        
        # Actualizar campos de la receta
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Si se enviaron detalles, reemplazarlos completamente
        if detalles_data is not None:
            instance.detalles.all().delete()
            for detalle_data in detalles_data:
                RecetaDetalle.objects.create(receta=instance, **detalle_data)
        
        return instance


class ConsumoRealSerializer(serializers.ModelSerializer):
    """Serializer para consumos reales de insumos"""
    insumo_nombre = serializers.CharField(source='insumo.nombre', read_only=True)
    insumo_sku = serializers.CharField(source='insumo.sku', read_only=True)
    insumo_unidad_medida = serializers.CharField(source='insumo.unidad_medida', read_only=True)
    diferencia = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    porcentaje_diferencia = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    porcentaje_merma = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    costo_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    costo_merma = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = ConsumoReal
        fields = [
            'id', 'insumo', 'insumo_nombre', 'insumo_sku', 'insumo_unidad_medida',
            'cantidad_teorica', 'cantidad_real', 'diferencia', 'porcentaje_diferencia',
            'merma', 'porcentaje_merma', 'costo_unitario', 'costo_total',
            'costo_merma', 'notas'
        ]
        read_only_fields = ['cantidad_teorica', 'costo_unitario']


class OrdenProduccionListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listado de órdenes"""
    receta_nombre = serializers.CharField(source='receta.nombre', read_only=True)
    producto_nombre = serializers.CharField(source='receta.producto_terminado.nombre', read_only=True)
    producto_sku = serializers.CharField(source='receta.producto_terminado.sku', read_only=True)
    responsable_nombre = serializers.SerializerMethodField()
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    esta_retrasada = serializers.BooleanField(read_only=True)
    eficiencia_produccion = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = OrdenProduccion
        fields = [
            'id', 'numero', 'receta', 'receta_nombre', 'producto_nombre',
            'producto_sku', 'estado', 'estado_display', 'cantidad_planificada',
            'cantidad_producida', 'fecha_programada', 'fecha_inicio', 'fecha_fin',
            'responsable', 'responsable_nombre', 'esta_retrasada',
            'eficiencia_produccion', 'created_at'
        ]
    
    def get_responsable_nombre(self, obj):
        if obj.responsable:
            return f"{obj.responsable.first_name} {obj.responsable.last_name}".strip() or obj.responsable.username
        return None


class HistorialOrdenProduccionSerializer(serializers.ModelSerializer):
    """Serializer para el historial de actividades de una orden"""
    tipo_evento_display = serializers.CharField(source='get_tipo_evento_display', read_only=True)
    usuario_nombre = serializers.SerializerMethodField()
    
    class Meta:
        model = HistorialOrdenProduccion
        fields = ['id', 'tipo_evento', 'tipo_evento_display', 'descripcion', 
                  'datos_adicionales', 'usuario', 'usuario_nombre', 'fecha']
    
    def get_usuario_nombre(self, obj):
        if obj.usuario:
            return f"{obj.usuario.first_name} {obj.usuario.last_name}".strip() or obj.usuario.username
        return None


class OrdenProduccionSerializer(serializers.ModelSerializer):
    """Serializer completo para órdenes de producción"""
    receta_info = RecetaProductoSerializer(source='receta', read_only=True)
    receta_nombre = serializers.CharField(source='receta.nombre', read_only=True)
    producto_nombre = serializers.CharField(source='receta.producto_terminado.nombre', read_only=True)
    producto_sku = serializers.CharField(source='receta.producto_terminado.sku', read_only=True)
    consumos = ConsumoRealSerializer(many=True, read_only=True)
    detalles = serializers.SerializerMethodField()
    historial = HistorialOrdenProduccionSerializer(many=True, read_only=True)
    almacen_insumos_nombre = serializers.CharField(source='almacen_insumos.nombre', read_only=True)
    almacen_destino_nombre = serializers.CharField(source='almacen_destino.nombre', read_only=True)
    responsable_nombre = serializers.SerializerMethodField()
    created_by_nombre = serializers.SerializerMethodField()
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    esta_retrasada = serializers.BooleanField(read_only=True)
    eficiencia_produccion = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    eficiencia_tiempo = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    costos_reales = serializers.SerializerMethodField()
    tiempo_estimado = serializers.SerializerMethodField()
    costo_estimado = serializers.SerializerMethodField()
    
    class Meta:
        model = OrdenProduccion
        fields = [
            'id', 'numero', 'empresa', 'receta', 'receta_info', 'receta_nombre',
            'producto_nombre', 'producto_sku',
            'estado', 'estado_display', 'cantidad_planificada', 'cantidad_producida',
            'fecha_programada', 'fecha_inicio', 'fecha_fin',
            'almacen_insumos', 'almacen_insumos_nombre',
            'almacen_destino', 'almacen_destino_nombre',
            'costo_mano_obra_real', 'costo_indirecto_real', 'tiempo_real',
            'tiempo_estimado', 'costo_estimado',
            'observaciones', 'responsable', 'responsable_nombre',
            'created_by', 'created_by_nombre', 'consumos', 'detalles', 'historial',
            'esta_retrasada', 'eficiencia_produccion', 'eficiencia_tiempo',
            'costos_reales', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'numero', 'empresa', 'created_by', 'created_at', 'updated_at',
            'fecha_inicio', 'fecha_fin'
        ]
    
    def get_responsable_nombre(self, obj):
        if obj.responsable:
            return f"{obj.responsable.first_name} {obj.responsable.last_name}".strip() or obj.responsable.username
        return None
    
    def get_created_by_nombre(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.username
        return None
    
    def get_costos_reales(self, obj):
        if obj.estado == 'finalizada':
            return obj.calcular_costo_real()
        return None
    
    def get_tiempo_estimado(self, obj):
        """Calcula el tiempo estimado basado en la receta y cantidad"""
        if obj.receta and obj.receta.tiempo_estimado:
            return float(obj.receta.tiempo_estimado * obj.cantidad_planificada)
        return None
    
    def get_costo_estimado(self, obj):
        """Calcula el costo estimado basado en la receta y cantidad"""
        if obj.receta:
            costos = obj.receta.calcular_costo_teorico()
            return float(costos['costo_total'] * obj.cantidad_planificada)
        return None
    
    def get_detalles(self, obj):
        """Obtiene los detalles de materiales de la receta con cantidades calculadas"""
        if not obj.receta:
            return []
        
        detalles = []
        for detalle in obj.receta.detalles.all():
            cantidad_requerida = float(detalle.cantidad * obj.cantidad_planificada)
            # Buscar consumo real si existe
            consumo = obj.consumos.filter(insumo=detalle.insumo).first()
            cantidad_usada = float(consumo.cantidad_real) if consumo else 0
            
            # Obtener stock desde InventarioMateriasPrimas primero
            stock_disponible = 0
            try:
                inv_mp = InventarioMateriasPrimas.objects.filter(
                    producto=detalle.insumo,
                    empresa=obj.empresa
                ).first()
                if inv_mp:
                    stock_disponible = float(inv_mp.cantidad_disponible or 0)
                else:
                    # Fallback al stock_total del producto
                    stock_disponible = float(detalle.insumo.stock_total or 0)
            except Exception:
                stock_disponible = float(detalle.insumo.stock_total or 0)
            
            detalles.append({
                'id': detalle.id,
                'insumo_id': detalle.insumo.id,
                'materia_prima_nombre': detalle.insumo.nombre,
                'materia_prima_sku': detalle.insumo.sku,
                'cantidad_requerida': cantidad_requerida,
                'cantidad_usada': cantidad_usada,
                'unidad': detalle.unidad_medida or detalle.insumo.unidad_medida,
                'costo_unitario': float(detalle.costo_unitario or 0),
                'stock_disponible': stock_disponible
            })
        
        return detalles


class OrdenProduccionCreateSerializer(serializers.Serializer):
    """Serializer para crear órdenes de producción"""
    receta_id = serializers.IntegerField()
    cantidad = serializers.DecimalField(max_digits=10, decimal_places=2)
    fecha_programada = serializers.DateField()
    almacen_insumos_id = serializers.IntegerField()
    almacen_destino_id = serializers.IntegerField()
    responsable_id = serializers.IntegerField(required=False, allow_null=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)
    
    def validate_cantidad(self, value):
        if value <= 0:
            raise serializers.ValidationError('La cantidad debe ser mayor a 0')
        return value
    
    def create(self, validated_data):
        from .services.produccion_service import ProduccionService
        
        empresa = self.context['request'].user.empresa
        created_by = self.context['request'].user
        
        responsable = None
        if validated_data.get('responsable_id'):
            try:
                responsable = User.objects.get(id=validated_data['responsable_id'])
            except User.DoesNotExist:
                pass
        
        orden = ProduccionService.crear_orden_produccion(
            empresa=empresa,
            receta_id=validated_data['receta_id'],
            cantidad=validated_data['cantidad'],
            fecha_programada=validated_data['fecha_programada'],
            almacen_insumos_id=validated_data['almacen_insumos_id'],
            almacen_destino_id=validated_data['almacen_destino_id'],
            responsable=responsable,
            created_by=created_by,
            observaciones=validated_data.get('observaciones', '')
        )
        
        return orden


class FinalizarOrdenSerializer(serializers.Serializer):
    """Serializer para finalizar órdenes de producción"""
    cantidad_producida = serializers.DecimalField(max_digits=10, decimal_places=2)
    costo_mano_obra_real = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    costo_indirecto_real = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    observaciones = serializers.CharField(required=False, allow_blank=True)
    
    def validate_cantidad_producida(self, value):
        if value <= 0:
            raise serializers.ValidationError('La cantidad producida debe ser mayor a 0')
        return value


class ActualizarConsumoSerializer(serializers.Serializer):
    """Serializer para actualizar consumo de un insumo"""
    insumo_id = serializers.IntegerField()
    cantidad_real = serializers.DecimalField(max_digits=10, decimal_places=2)
    merma = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    notas = serializers.CharField(required=False, allow_blank=True)
    
    def validate_cantidad_real(self, value):
        if value < 0:
            raise serializers.ValidationError('La cantidad real no puede ser negativa')
        return value
    
    def validate_merma(self, value):
        if value < 0:
            raise serializers.ValidationError('La merma no puede ser negativa')
        return value
