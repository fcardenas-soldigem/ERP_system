from rest_framework import serializers
from .models import ImportacionExcel, MapeoColumnas


class ImportacionExcelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportacionExcel
        fields = [
            'id', 'nombre_archivo', 'fecha', 'estado',
            'total_filas', 'filas_importadas', 'filas_con_error',
            'proveedores_creados', 'productos_creados',
            'compras_creadas', 'ventas_creadas',
            'errores_json', 'preview_json',
        ]
        read_only_fields = fields


class MapeoColumnasSerializer(serializers.ModelSerializer):
    class Meta:
        model = MapeoColumnas
        fields = ['id', 'nombre_hoja', 'columnas_origen', 'mapeo', 'usos']
