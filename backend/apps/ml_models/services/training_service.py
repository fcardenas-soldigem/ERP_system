"""
Servicio para entrenar modelos ML por empresa
"""
import os
import joblib
from pathlib import Path
from django.conf import settings
from django.utils import timezone
from apps.ml_models.models import MLModel, TrainingJob
from apps.ml_models.services.data_extractor import DataExtractor
from apps.ml_models.customer_analytics.rfm_segmentation import RFMSegmentation
from apps.ml_models.customer_analytics.churn_prediction import ChurnPredictor
from apps.ml_models.product_recommendations.association_rules import ProductRecommender


class TrainingService:
    """
    Servicio para entrenar y gestionar modelos ML por empresa
    """
    
    def __init__(self, empresa):
        """
        Args:
            empresa: Instancia de Empresa
        """
        self.empresa = empresa
        self.extractor = DataExtractor(empresa)
        
        # Directorio para modelos de esta empresa
        self.models_dir = Path(settings.BASE_DIR) / 'ml_models_cache' / f'empresa_{empresa.id}'
        self.models_dir.mkdir(parents=True, exist_ok=True)
    
    def train_rfm_segmentation(self, n_clusters=5):
        """
        Entrena modelo de segmentación RFM con datos de la empresa
        
        Args:
            n_clusters: Número de segmentos a crear
            
        Returns:
            MLModel instance
        """
        # Crear registro de trabajo
        job = TrainingJob.objects.create(
            empresa=self.empresa,
            model_type='rfm_segmentation',
            status='running',
            started_at=timezone.now()
        )
        
        try:
            # Validar datos
            is_valid, message, data_info = self.extractor.validate_data_for_training('rfm_segmentation')
            if not is_valid:
                raise ValueError(f"Datos insuficientes: {message}")
            
            # Extraer datos
            rfm_data = self.extractor.extract_rfm_data()
            
            # Preparar ruta del modelo
            model_filename = f'rfm_segmentation_v{self._get_next_version("rfm_segmentation")}.pkl'
            model_path = self.models_dir / model_filename
            
            # Entrenar modelo
            model = RFMSegmentation(n_clusters=n_clusters, model_path=str(model_path))
            df_segmented = model.fit(rfm_data)
            
            # Guardar modelo
            model.save_model()
            
            # Crear registro en BD
            ml_model = MLModel.objects.create(
                empresa=self.empresa,
                model_type='rfm_segmentation',
                version=self._get_next_version('rfm_segmentation'),
                status='active',
                training_samples=len(rfm_data),
                model_file_path=str(model_path),
                training_data_info={
                    'clientes_count': len(rfm_data),
                    'avg_recency': float(rfm_data['recency'].mean()),
                    'avg_frequency': float(rfm_data['frequency'].mean()),
                    'avg_monetary': float(rfm_data['monetary'].mean()),
                },
                hyperparameters={
                    'n_clusters': n_clusters,
                },
                trained_at=timezone.now()
            )
            
            # Marcar como activo
            ml_model.mark_as_active()
            
            # Actualizar job
            job.status = 'completed'
            job.result_model = ml_model
            job.completed_at = timezone.now()
            job.save()
            
            return ml_model
            
        except Exception as e:
            # Marcar job como fallido
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = timezone.now()
            job.save()
            raise
    
    def train_churn_prediction(self):
        """
        Entrena modelo de predicción de churn con datos de la empresa
        
        Returns:
            MLModel instance
        """
        job = TrainingJob.objects.create(
            empresa=self.empresa,
            model_type='churn_prediction',
            status='running',
            started_at=timezone.now()
        )
        
        try:
            # Validar datos
            is_valid, message, data_info = self.extractor.validate_data_for_training('churn_prediction')
            if not is_valid:
                raise ValueError(f"Datos insuficientes: {message}")
            
            # Extraer datos
            rfm_data = self.extractor.extract_rfm_data()
            
            # Preparar ruta del modelo
            model_filename = f'churn_prediction_v{self._get_next_version("churn_prediction")}.pkl'
            model_path = self.models_dir / model_filename
            
            # Entrenar modelo
            model = ChurnPredictor(model_path=str(model_path))
            df_trained = model.fit(rfm_data)
            
            # Guardar modelo
            model.save_model()
            
            # Calcular métricas
            df_predicted = model.predict(rfm_data)
            high_risk_count = len(df_predicted[df_predicted['churn_risk'] == 'Alto'])
            
            # Crear registro en BD
            ml_model = MLModel.objects.create(
                empresa=self.empresa,
                model_type='churn_prediction',
                version=self._get_next_version('churn_prediction'),
                status='active',
                training_samples=len(rfm_data),
                model_file_path=str(model_path),
                training_data_info={
                    'clientes_count': len(rfm_data),
                    'high_risk_count': high_risk_count,
                    'high_risk_percentage': float(high_risk_count / len(rfm_data) * 100),
                },
                hyperparameters={
                    'churn_threshold_days': 90,
                    'n_estimators': 100,
                },
                trained_at=timezone.now()
            )
            
            ml_model.mark_as_active()
            
            job.status = 'completed'
            job.result_model = ml_model
            job.completed_at = timezone.now()
            job.save()
            
            return ml_model
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = timezone.now()
            job.save()
            raise
    
    def train_product_recommendations(self, min_support=0.01, min_confidence=0.2):
        """
        Entrena modelo de recomendaciones de productos
        
        Args:
            min_support: Soporte mínimo para itemsets frecuentes
            min_confidence: Confianza mínima para reglas
            
        Returns:
            MLModel instance
        """
        job = TrainingJob.objects.create(
            empresa=self.empresa,
            model_type='product_recommendations',
            status='running',
            started_at=timezone.now()
        )
        
        try:
            # Validar datos
            is_valid, message, data_info = self.extractor.validate_data_for_training('product_recommendations')
            if not is_valid:
                raise ValueError(f"Datos insuficientes: {message}")
            
            # Extraer datos
            transactions_df = self.extractor.extract_product_transactions()
            
            # Preparar ruta del modelo
            model_filename = f'product_recommendations_v{self._get_next_version("product_recommendations")}.pkl'
            model_path = self.models_dir / model_filename
            
            # Entrenar modelo
            model = ProductRecommender(
                min_support=min_support,
                min_confidence=min_confidence,
                min_lift=1.0,
                model_path=str(model_path)
            )
            rules = model.fit(transactions_df)
            
            # Guardar modelo
            model.save_model()
            
            # Crear registro en BD
            ml_model = MLModel.objects.create(
                empresa=self.empresa,
                model_type='product_recommendations',
                version=self._get_next_version('product_recommendations'),
                status='active',
                training_samples=len(transactions_df),
                model_file_path=str(model_path),
                training_data_info={
                    'transactions_count': transactions_df['transaction_id'].nunique(),
                    'products_count': transactions_df['producto_id'].nunique(),
                    'rules_count': len(rules) if rules is not None else 0,
                },
                hyperparameters={
                    'min_support': min_support,
                    'min_confidence': min_confidence,
                    'min_lift': 1.0,
                },
                trained_at=timezone.now()
            )
            
            ml_model.mark_as_active()
            
            job.status = 'completed'
            job.result_model = ml_model
            job.completed_at = timezone.now()
            job.save()
            
            return ml_model
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = timezone.now()
            job.save()
            raise
    
    def train_all_models(self):
        """
        Entrena todos los modelos disponibles para la empresa
        
        Returns:
            dict con resultados
        """
        results = {
            'success': [],
            'failed': [],
        }
        
        # RFM Segmentation
        try:
            model = self.train_rfm_segmentation()
            results['success'].append({
                'type': 'rfm_segmentation',
                'model': model,
            })
        except Exception as e:
            results['failed'].append({
                'type': 'rfm_segmentation',
                'error': str(e),
            })
        
        # Churn Prediction
        try:
            model = self.train_churn_prediction()
            results['success'].append({
                'type': 'churn_prediction',
                'model': model,
            })
        except Exception as e:
            results['failed'].append({
                'type': 'churn_prediction',
                'error': str(e),
            })
        
        # Product Recommendations
        try:
            model = self.train_product_recommendations()
            results['success'].append({
                'type': 'product_recommendations',
                'model': model,
            })
        except Exception as e:
            results['failed'].append({
                'type': 'product_recommendations',
                'error': str(e),
            })
        
        return results
    
    def get_active_model(self, model_type):
        """
        Obtiene el modelo activo para un tipo específico
        
        Args:
            model_type: Tipo de modelo
            
        Returns:
            MLModel instance o None
        """
        return MLModel.get_active_model(self.empresa, model_type)
    
    def load_model(self, model_type):
        """
        Carga un modelo entrenado desde disco
        
        Args:
            model_type: Tipo de modelo
            
        Returns:
            Modelo cargado
        """
        ml_model = self.get_active_model(model_type)
        
        if not ml_model:
            raise ValueError(f"No hay modelo activo de tipo {model_type} para {self.empresa.nombre}")
        
        # Cargar desde archivo
        model_data = joblib.load(ml_model.model_file_path)
        
        # Marcar como usado
        ml_model.mark_as_used()
        
        return model_data, ml_model
    
    def _get_next_version(self, model_type):
        """
        Obtiene el siguiente número de versión para un tipo de modelo
        
        Args:
            model_type: Tipo de modelo
            
        Returns:
            int: Número de versión
        """
        last_version = MLModel.objects.filter(
            empresa=self.empresa,
            model_type=model_type
        ).aggregate(max_version=models.Max('version'))['max_version']
        
        return (last_version or 0) + 1
    
    def get_training_history(self, model_type=None):
        """
        Obtiene el historial de entrenamientos
        
        Args:
            model_type: Filtrar por tipo (opcional)
            
        Returns:
            QuerySet de TrainingJob
        """
        jobs = TrainingJob.objects.filter(empresa=self.empresa)
        
        if model_type:
            jobs = jobs.filter(model_type=model_type)
        
        return jobs.order_by('-created_at')
    
    def check_if_retraining_needed(self, model_type, days_threshold=30):
        """
        Verifica si un modelo necesita reentrenamiento
        
        Args:
            model_type: Tipo de modelo
            days_threshold: Días desde último entrenamiento
            
        Returns:
            tuple (needs_retraining: bool, reason: str)
        """
        ml_model = self.get_active_model(model_type)
        
        if not ml_model:
            return True, "No existe modelo entrenado"
        
        # Verificar antigüedad
        days_since_training = (timezone.now() - ml_model.trained_at).days
        
        if days_since_training > days_threshold:
            return True, f"Modelo tiene {days_since_training} días (umbral: {days_threshold})"
        
        # Verificar si hay suficientes nuevos datos
        current_summary = self.extractor.get_data_summary()
        training_samples = ml_model.training_samples
        
        # Si hay 20% más datos, recomendar reentrenamiento
        if current_summary['ventas_count'] > training_samples * 1.2:
            return True, f"Hay {current_summary['ventas_count'] - training_samples} nuevas ventas"
        
        return False, "Modelo actualizado"


# Importar models de Django para usar en _get_next_version
from django.db import models


