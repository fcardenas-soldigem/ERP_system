"""
Migración de datos: crea las 9 categorías de gasto predeterminadas
para cada empresa existente en la base de datos.
"""

from django.db import migrations

CATEGORIAS_DEFAULT = [
    {'nombre': 'Planilla y sueldos',       'es_fijo': True,  'icono': 'FiUsers',         'color': '#7c3aed', 'orden': 1},
    {'nombre': 'Recibos por honorarios',   'es_fijo': False, 'icono': 'FiFileText',       'color': '#6366f1', 'orden': 2},
    {'nombre': 'Alquiler de local',        'es_fijo': True,  'icono': 'FiHome',           'color': '#f97316', 'orden': 3},
    {'nombre': 'Servicios básicos',        'es_fijo': True,  'icono': 'FiZap',            'color': '#eab308', 'orden': 4},
    {'nombre': 'Transporte y combustible', 'es_fijo': False, 'icono': 'FiTruck',          'color': '#22c55e', 'orden': 5},
    {'nombre': 'Impuestos y SUNAT',        'es_fijo': True,  'icono': 'FiDollarSign',     'color': '#ef4444', 'orden': 6},
    {'nombre': 'Marketing y publicidad',   'es_fijo': False, 'icono': 'FiTrendingUp',     'color': '#ec4899', 'orden': 7},
    {'nombre': 'Mantenimiento y reparaciones', 'es_fijo': False, 'icono': 'FiTool',       'color': '#6b7280', 'orden': 8},
    {'nombre': 'Otros gastos',             'es_fijo': False, 'icono': 'FiMoreHorizontal', 'color': '#9ca3af', 'orden': 9},
]


def crear_categorias_default(apps, schema_editor):
    Empresa = apps.get_model('empresas', 'Empresa')
    CategoriaGasto = apps.get_model('finanzas', 'CategoriaGasto')

    for empresa in Empresa.objects.all():
        for cat in CATEGORIAS_DEFAULT:
            CategoriaGasto.objects.get_or_create(
                empresa=empresa,
                nombre=cat['nombre'],
                defaults={
                    'es_fijo': cat['es_fijo'],
                    'icono':   cat['icono'],
                    'color':   cat['color'],
                    'orden':   cat['orden'],
                    'activo':  True,
                },
            )


def revertir_categorias_default(apps, schema_editor):
    """No hace nada en reversa — dejar las categorías creadas."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('finanzas', '0001_initial'),
        ('empresas', '0005_empresa_tipo_cambio_usd'),
    ]

    operations = [
        migrations.RunPython(crear_categorias_default, revertir_categorias_default),
    ]
