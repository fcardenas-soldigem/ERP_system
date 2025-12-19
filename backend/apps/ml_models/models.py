from django.db import models
from apps.empresas.models import Empresa
from django.utils import timezone


class MLModel(models.Model):
    """
    Almacena información sobre modelos ML entrenados por empresa
    """
    MODEL_TYPES = [
        ('rfm_segmentation', 'Segmentación RFM'),
        ('churn_prediction', 'Predicción de Churn'),
        ('product_recommendations', 'Recomendaciones de Productos'),
        ('demand_forecasting', 'Predicción de Demanda'),
    ]
    
    STATUS_CHOICES = [
        ('training', 'Entrenando'),
        ('active', 'Activo'),
        ('outdated', 'Desactualizado'),
        ('failed', 'Fallido'),
    ]
    
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.CASCADE, 
        related_name='ml_models',
        help_text='Empresa dueña del modelo'
    )
    model_type = models.CharField(
        max_length=50, 
        choices=MODEL_TYPES,
        help_text='Tipo de modelo ML'
    )
    version = models.IntegerField(
        default=1,
        help_text='Versión del modelo'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='training'
    )
    
    # Métricas del modelo
    accuracy = models.FloatField(null=True, blank=True, help_text='Precisión del modelo')
    training_samples = models.IntegerField(default=0, help_text='Cantidad de datos usados para entrenar')
    
    # Archivos
    model_file_path = models.CharField(
        max_length=500, 
        help_text='Ruta al archivo .pkl del modelo'
    )
    
    # Metadata
    training_data_info = models.JSONField(
        default=dict, 
        blank=True,
        help_text='Información sobre los datos de entrenamiento'
    )
    hyperparameters = models.JSONField(
        default=dict, 
        blank=True,
        help_text='Hiperparámetros usados'
    )
    
    # Fechas
    created_at = models.DateTimeField(auto_now_add=True)
    trained_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Modelo ML'
        verbose_name_plural = 'Modelos ML'
        ordering = ['-created_at']
        unique_together = ('empresa', 'model_type', 'version')
        indexes = [
            models.Index(fields=['empresa', 'model_type', 'status']),
        ]
    
    def __str__(self):
        return f"{self.empresa.nombre} - {self.get_model_type_display()} v{self.version}"
    
    def mark_as_active(self):
        """Marca este modelo como activo y desactiva versiones anteriores"""
        # Desactivar otros modelos del mismo tipo
        MLModel.objects.filter(
            empresa=self.empresa,
            model_type=self.model_type,
            status='active'
        ).exclude(id=self.id).update(status='outdated')
        
        # Activar este modelo
        self.status = 'active'
        self.trained_at = timezone.now()
        self.save()
    
    def mark_as_used(self):
        """Actualiza la fecha de último uso"""
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at'])
    
    @classmethod
    def get_active_model(cls, empresa, model_type):
        """Obtiene el modelo activo para una empresa y tipo"""
        try:
            return cls.objects.get(
                empresa=empresa,
                model_type=model_type,
                status='active'
            )
        except cls.DoesNotExist:
            return None


class MLPrediction(models.Model):
    """
    Almacena predicciones realizadas por los modelos
    """
    model = models.ForeignKey(
        MLModel, 
        on_delete=models.CASCADE, 
        related_name='predictions'
    )
    
    # Datos de entrada
    input_data = models.JSONField(help_text='Datos de entrada para la predicción')
    
    # Resultado
    prediction = models.JSONField(help_text='Resultado de la predicción')
    confidence = models.FloatField(null=True, blank=True, help_text='Confianza de la predicción')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    execution_time_ms = models.IntegerField(null=True, blank=True, help_text='Tiempo de ejecución en ms')
    
    class Meta:
        verbose_name = 'Predicción ML'
        verbose_name_plural = 'Predicciones ML'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['model', 'created_at']),
        ]
    
    def __str__(self):
        return f"Predicción {self.id} - {self.model.get_model_type_display()}"


class TrainingJob(models.Model):
    """
    Registro de trabajos de entrenamiento
    """
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('running', 'Ejecutando'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
    ]
    
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.CASCADE, 
        related_name='training_jobs'
    )
    model_type = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Resultado
    result_model = models.ForeignKey(
        MLModel, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='training_job'
    )
    error_message = models.TextField(blank=True, help_text='Mensaje de error si falló')
    
    # Fechas
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Trabajo de Entrenamiento'
        verbose_name_plural = 'Trabajos de Entrenamiento'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Training Job {self.id} - {self.empresa.nombre} - {self.status}"
    
    @property
    def duration_seconds(self):
        """Calcula la duración del trabajo en segundos"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
