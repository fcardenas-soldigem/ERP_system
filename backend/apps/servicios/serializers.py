from rest_framework import serializers
from .models import OrdenServicio, ItemOrdenServicio, SeguimientoProveedor, HistorialEstadoOS


class ItemOrdenServicioSerializer(serializers.ModelSerializer):
    estado_item_display = serializers.CharField(
        source='get_estado_item_display', read_only=True
    )

    class Meta:
        model = ItemOrdenServicio
        fields = [
            'id', 'numero_item', 'descripcion', 'numero_serie', 'marca', 'modelo',
            'falla_cliente', 'falla_diagnostico', 'falla_adicional',
            'estado_item', 'estado_item_display',
            'costo_proveedor', 'precio_cliente', 'margen',
            'notas', 'item_guia',
        ]


class SeguimientoProveedorSerializer(serializers.ModelSerializer):
    registrado_por_nombre = serializers.CharField(
        source='registrado_por.get_full_name', read_only=True
    )

    class Meta:
        model = SeguimientoProveedor
        fields = [
            'id', 'fecha', 'estado_reportado', 'fecha_entrega_prometida',
            'notas', 'registrado_por', 'registrado_por_nombre', 'created_at',
        ]
        read_only_fields = ['registrado_por', 'created_at']


class HistorialEstadoOSSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(
        source='usuario.get_full_name', read_only=True
    )
    estado_anterior_display = serializers.SerializerMethodField()
    estado_nuevo_display = serializers.SerializerMethodField()

    class Meta:
        model = HistorialEstadoOS
        fields = [
            'id', 'estado_anterior', 'estado_anterior_display',
            'estado_nuevo', 'estado_nuevo_display',
            'fecha', 'usuario', 'usuario_nombre', 'notas',
        ]
        read_only_fields = ['fecha', 'usuario']

    def _estado_display(self, codigo):
        mapa = dict(OrdenServicio.ESTADO_CHOICES)
        return mapa.get(codigo, codigo)

    def get_estado_anterior_display(self, obj):
        return self._estado_display(obj.estado_anterior)

    def get_estado_nuevo_display(self, obj):
        return self._estado_display(obj.estado_nuevo)


class OrdenServicioSerializer(serializers.ModelSerializer):
    items = ItemOrdenServicioSerializer(many=True, read_only=True)
    seguimientos = SeguimientoProveedorSerializer(many=True, read_only=True)
    historial = HistorialEstadoOSSerializer(many=True, read_only=True)

    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    prioridad_display = serializers.CharField(source='get_prioridad_display', read_only=True)
    cliente_nombre = serializers.CharField(source='cliente.__str__', read_only=True)
    proveedor_nombre = serializers.CharField(
        source='proveedor_reparacion.__str__', read_only=True
    )

    dias_transcurridos = serializers.IntegerField(read_only=True)
    dias_restantes_sla = serializers.IntegerField(read_only=True)
    estado_sla = serializers.CharField(read_only=True)
    en_riesgo = serializers.BooleanField(read_only=True)

    class Meta:
        model = OrdenServicio
        fields = [
            'id', 'numero', 'empresa',
            'guia_remision', 'cliente', 'cliente_nombre',
            'proveedor_reparacion', 'proveedor_nombre',
            'fecha_ingreso', 'fecha_diagnostico',
            'fecha_cotizacion_enviada', 'fecha_aprobacion',
            'fecha_inicio_reparacion', 'fecha_entrega_estimada', 'fecha_entrega_real',
            'cotizacion', 'estado', 'estado_display',
            'dias_sla', 'prioridad', 'prioridad_display',
            'notas_internas', 'creado_por',
            'created_at', 'updated_at',
            'dias_transcurridos', 'dias_restantes_sla', 'estado_sla', 'en_riesgo',
            'items', 'seguimientos', 'historial',
        ]
        read_only_fields = ['numero', 'empresa', 'creado_por', 'created_at', 'updated_at']


class OrdenServicioListSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    prioridad_display = serializers.CharField(source='get_prioridad_display', read_only=True)
    cliente_nombre = serializers.CharField(source='cliente.__str__', read_only=True)
    proveedor_nombre = serializers.CharField(
        source='proveedor_reparacion.__str__', read_only=True
    )
    dias_restantes_sla = serializers.IntegerField(read_only=True)
    estado_sla = serializers.CharField(read_only=True)
    en_riesgo = serializers.BooleanField(read_only=True)
    total_items = serializers.SerializerMethodField()

    class Meta:
        model = OrdenServicio
        fields = [
            'id', 'numero', 'cliente', 'cliente_nombre',
            'proveedor_reparacion', 'proveedor_nombre',
            'fecha_ingreso', 'fecha_entrega_estimada', 'fecha_entrega_real',
            'estado', 'estado_display', 'prioridad', 'prioridad_display',
            'dias_restantes_sla', 'estado_sla', 'en_riesgo', 'total_items',
            'created_at',
        ]

    def get_total_items(self, obj):
        return obj.items.count()


class OrdenServicioResumenSerializer(serializers.ModelSerializer):
    estado_sla = serializers.CharField(read_only=True)
    en_riesgo = serializers.BooleanField(read_only=True)

    class Meta:
        model = OrdenServicio
        fields = ['id', 'numero', 'estado', 'estado_sla', 'en_riesgo',
                  'proveedor_reparacion', 'fecha_ingreso']
