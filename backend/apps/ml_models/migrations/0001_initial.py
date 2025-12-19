# Generated manually for ml_models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('empresas', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MLModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model_type', models.CharField(
                    choices=[
                        ('rfm_segmentation', 'Segmentación RFM'),
                        ('churn_prediction', 'Predicción de Churn'),
                        ('product_recommendations', 'Recomendaciones de Productos'),
                        ('demand_forecasting', 'Predicción de Demanda'),
                    ],
                    help_text='Tipo de modelo ML',
                    max_length=50
                )),
                ('version', models.IntegerField(default=1, help_text='Versión del modelo')),
                ('status', models.CharField(
                    choices=[
                        ('training', 'Entrenando'),
                        ('active', 'Activo'),
                        ('outdated', 'Desactualizado'),
                        ('failed', 'Fallido'),
                    ],
                    default='training',
                    max_length=20
                )),
                ('accuracy', models.FloatField(blank=True, help_text='Precisión del modelo', null=True)),
                ('training_samples', models.IntegerField(default=0, help_text='Cantidad de datos usados para entrenar')),
                ('model_file_path', models.CharField(help_text='Ruta al archivo .pkl del modelo', max_length=500)),
                ('training_data_info', models.JSONField(blank=True, default=dict, help_text='Información sobre los datos de entrenamiento')),
                ('hyperparameters', models.JSONField(blank=True, default=dict, help_text='Hiperparámetros usados')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('trained_at', models.DateTimeField(blank=True, null=True)),
                ('last_used_at', models.DateTimeField(blank=True, null=True)),
                ('empresa', models.ForeignKey(
                    help_text='Empresa dueña del modelo',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='ml_models',
                    to='empresas.empresa'
                )),
            ],
            options={
                'verbose_name': 'Modelo ML',
                'verbose_name_plural': 'Modelos ML',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['empresa', 'model_type', 'status'], name='ml_models_m_empresa_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='TrainingJob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model_type', models.CharField(max_length=50)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pendiente'),
                        ('running', 'Ejecutando'),
                        ('completed', 'Completado'),
                        ('failed', 'Fallido'),
                    ],
                    default='pending',
                    max_length=20
                )),
                ('error_message', models.TextField(blank=True, help_text='Mensaje de error si falló')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('empresa', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='training_jobs',
                    to='empresas.empresa'
                )),
                ('result_model', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='training_job',
                    to='ml_models.mlmodel'
                )),
            ],
            options={
                'verbose_name': 'Trabajo de Entrenamiento',
                'verbose_name_plural': 'Trabajos de Entrenamiento',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='MLPrediction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('input_data', models.JSONField(help_text='Datos de entrada para la predicción')),
                ('prediction', models.JSONField(help_text='Resultado de la predicción')),
                ('confidence', models.FloatField(blank=True, help_text='Confianza de la predicción', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('execution_time_ms', models.IntegerField(blank=True, help_text='Tiempo de ejecución en ms', null=True)),
                ('model', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='predictions',
                    to='ml_models.mlmodel'
                )),
            ],
            options={
                'verbose_name': 'Predicción ML',
                'verbose_name_plural': 'Predicciones ML',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['model', 'created_at'], name='ml_models_m_model_i_idx'),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name='mlmodel',
            constraint=models.UniqueConstraint(fields=('empresa', 'model_type', 'version'), name='unique_empresa_model_version'),
        ),
    ]


