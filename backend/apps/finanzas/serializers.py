"""
Serializers para el módulo de Gastos Operativos.
"""

from calendar import monthrange
from datetime import date

from django.db.models import Sum
from rest_framework import serializers

from .models import CategoriaGasto, GastoOperativo, GastoRecurrente


class CategoriaGastoSerializer(serializers.ModelSerializer):
    total_mes = serializers.SerializerMethodField()

    class Meta:
        model = CategoriaGasto
        fields = [
            'id', 'empresa', 'nombre', 'icono', 'color',
            'es_fijo', 'orden', 'activo', 'created_at', 'total_mes',
        ]
        read_only_fields = ['id', 'empresa', 'created_at']

    def get_total_mes(self, obj):
        """Total de gastos pagados del mes en curso para esta categoría."""
        hoy = date.today()
        primer_dia = hoy.replace(day=1)
        _, ultimo = monthrange(hoy.year, hoy.month)
        ultimo_dia = hoy.replace(day=ultimo)
        total = obj.gastos.filter(
            fecha__range=(primer_dia, ultimo_dia),
            estado='pagado',
        ).aggregate(t=Sum('monto'))['t']
        return float(total) if total else 0.0


class GastoOperativoSerializer(serializers.ModelSerializer):
    categoria_detalle = CategoriaGastoSerializer(source='categoria', read_only=True)

    class Meta:
        model = GastoOperativo
        fields = [
            'id', 'empresa', 'categoria', 'categoria_detalle',
            'descripcion', 'monto', 'moneda', 'fecha',
            'es_recurrente', 'frecuencia',
            'comprobante_tipo', 'comprobante_numero',
            'proveedor_servicio', 'estado', 'notas', 'archivo_adjunto',
            'creado_por', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'empresa', 'creado_por', 'created_at', 'updated_at']


class GastoRecurrenteSerializer(serializers.ModelSerializer):
    categoria_detalle = CategoriaGastoSerializer(source='categoria', read_only=True)

    class Meta:
        model = GastoRecurrente
        fields = [
            'id', 'empresa', 'categoria', 'categoria_detalle',
            'descripcion', 'monto', 'moneda', 'frecuencia', 'dia_del_mes',
            'activo', 'ultimo_generado', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'empresa', 'ultimo_generado', 'created_at', 'updated_at']
