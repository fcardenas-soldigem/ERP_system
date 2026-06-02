from rest_framework import serializers
from .models import GuiaRemision, ItemGuia


class ItemGuiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemGuia
        fields = [
            'id', 'numero_item', 'descripcion', 'serie', 'marca', 'modelo',
            'cantidad', 'unidad_medida', 'estado_ingreso', 'accesorios',
        ]


class GuiaRemisionSerializer(serializers.ModelSerializer):
    items = ItemGuiaSerializer(many=True, required=False)
    creado_por_nombre = serializers.CharField(
        source='creado_por.get_full_name', read_only=True
    )
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)

    class Meta:
        model = GuiaRemision
        fields = [
            'id', 'empresa', 'numero', 'fecha_emision', 'fecha_traslado',
            'motivo', 'estado', 'cliente', 'cliente_nombre',
            'nombre_destinatario', 'ruc_destinatario',
            'direccion_origen', 'direccion_destino', 'observaciones',
            'creado_por', 'creado_por_nombre', 'created_at', 'updated_at',
            'items',
        ]
        read_only_fields = ['id', 'numero', 'empresa', 'creado_por', 'created_at', 'updated_at']

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        guia = GuiaRemision.objects.create(**validated_data)
        for idx, item_data in enumerate(items_data, start=1):
            item_data.setdefault('numero_item', idx)
            ItemGuia.objects.create(guia=guia, **item_data)
        return guia

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if items_data is not None:
            instance.items.all().delete()
            for idx, item_data in enumerate(items_data, start=1):
                item_data.setdefault('numero_item', idx)
                ItemGuia.objects.create(guia=instance, **item_data)
        return instance


class GuiaRemisionListSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    total_items = serializers.IntegerField(source='items.count', read_only=True)

    class Meta:
        model = GuiaRemision
        fields = [
            'id', 'numero', 'fecha_emision', 'fecha_traslado',
            'motivo', 'estado', 'cliente_nombre',
            'nombre_destinatario', 'direccion_destino',
            'total_items', 'created_at',
        ]
