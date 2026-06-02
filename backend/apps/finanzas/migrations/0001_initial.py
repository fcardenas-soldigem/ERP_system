import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('empresas', '0005_empresa_tipo_cambio_usd'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoriaGasto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('icono', models.CharField(blank=True, max_length=50)),
                ('color', models.CharField(blank=True, max_length=20)),
                ('es_fijo', models.BooleanField(default=False, help_text='True = gasto fijo (planilla, alquiler). False = variable.')),
                ('orden', models.IntegerField(default=0)),
                ('activo', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('empresa', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='categorias_gasto',
                    to='empresas.empresa',
                )),
            ],
            options={
                'verbose_name': 'Categoría de Gasto',
                'verbose_name_plural': 'Categorías de Gasto',
                'ordering': ['orden', 'nombre'],
                'unique_together': {('empresa', 'nombre')},
            },
        ),
        migrations.CreateModel(
            name='GastoOperativo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descripcion', models.CharField(max_length=300)),
                ('monto', models.DecimalField(decimal_places=2, max_digits=12)),
                ('moneda', models.CharField(
                    choices=[('PEN', 'Sol Peruano'), ('USD', 'Dólar')],
                    default='PEN',
                    max_length=3,
                )),
                ('fecha', models.DateField()),
                ('es_recurrente', models.BooleanField(default=False)),
                ('frecuencia', models.CharField(blank=True, max_length=20, null=True,
                    help_text='mensual / quincenal / semanal')),
                ('comprobante_tipo', models.CharField(
                    blank=True,
                    choices=[
                        ('factura', 'Factura'),
                        ('boleta', 'Boleta'),
                        ('recibo_honorarios', 'Recibo x Hon.'),
                        ('sin_comprobante', 'Sin comprobante'),
                    ],
                    max_length=30,
                    null=True,
                )),
                ('comprobante_numero', models.CharField(blank=True, max_length=50, null=True)),
                ('proveedor_servicio', models.CharField(blank=True, max_length=200, null=True)),
                ('estado', models.CharField(
                    choices=[
                        ('pagado', 'Pagado'),
                        ('pendiente', 'Pendiente'),
                        ('programado', 'Programado'),
                    ],
                    default='pagado',
                    max_length=20,
                )),
                ('notas', models.TextField(blank=True, null=True)),
                ('archivo_adjunto', models.FileField(blank=True, null=True, upload_to='gastos/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('categoria', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='gastos',
                    to='finanzas.categoriagasto',
                )),
                ('creado_por', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='gastos_creados',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('empresa', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='gastos_operativos',
                    to='empresas.empresa',
                )),
            ],
            options={
                'verbose_name': 'Gasto Operativo',
                'verbose_name_plural': 'Gastos Operativos',
                'ordering': ['-fecha', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='GastoRecurrente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descripcion', models.CharField(max_length=300)),
                ('monto', models.DecimalField(decimal_places=2, max_digits=12)),
                ('moneda', models.CharField(default='PEN', max_length=3)),
                ('frecuencia', models.CharField(
                    choices=[
                        ('mensual', 'Mensual'),
                        ('quincenal', 'Quincenal'),
                        ('semanal', 'Semanal'),
                    ],
                    default='mensual',
                    max_length=20,
                )),
                ('dia_del_mes', models.IntegerField(default=1, help_text='Día del mes (1-31)')),
                ('activo', models.BooleanField(default=True)),
                ('ultimo_generado', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('categoria', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='gastos_recurrentes',
                    to='finanzas.categoriagasto',
                )),
                ('empresa', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='gastos_recurrentes',
                    to='empresas.empresa',
                )),
            ],
            options={
                'verbose_name': 'Gasto Recurrente',
                'verbose_name_plural': 'Gastos Recurrentes',
                'ordering': ['descripcion'],
            },
        ),
    ]
