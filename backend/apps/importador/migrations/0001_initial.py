import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('empresas', '0004_add_firma_digital_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ImportacionExcel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('archivo', models.FileField(blank=True, null=True, upload_to='importaciones/')),
                ('nombre_archivo', models.CharField(max_length=255)),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('estado', models.CharField(
                    choices=[
                        ('procesando', 'Procesando'),
                        ('preview', 'En Preview'),
                        ('importando', 'Importando'),
                        ('completado', 'Completado'),
                        ('parcial', 'Parcial (con errores)'),
                        ('error', 'Error'),
                    ],
                    default='procesando',
                    max_length=20,
                )),
                ('total_filas', models.IntegerField(default=0)),
                ('filas_importadas', models.IntegerField(default=0)),
                ('filas_con_error', models.IntegerField(default=0)),
                ('proveedores_creados', models.IntegerField(default=0)),
                ('productos_creados', models.IntegerField(default=0)),
                ('compras_creadas', models.IntegerField(default=0)),
                ('ventas_creadas', models.IntegerField(default=0)),
                ('preview_json', models.JSONField(blank=True, default=dict)),
                ('mapeo_json', models.JSONField(blank=True, default=dict)),
                ('errores_json', models.JSONField(blank=True, default=list)),
                ('empresa', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='importaciones',
                    to='empresas.empresa',
                )),
                ('usuario', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Importación Excel',
                'verbose_name_plural': 'Importaciones Excel',
                'ordering': ['-fecha'],
            },
        ),
        migrations.CreateModel(
            name='MapeoColumnas',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre_hoja', models.CharField(max_length=100)),
                ('columnas_origen', models.JSONField()),
                ('mapeo', models.JSONField()),
                ('usos', models.IntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('empresa', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='mapeos_columnas',
                    to='empresas.empresa',
                )),
            ],
            options={
                'verbose_name': 'Mapeo de Columnas',
                'verbose_name_plural': 'Mapeos de Columnas',
            },
        ),
    ]
