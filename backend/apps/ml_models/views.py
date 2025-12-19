from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from apps.empresas.models import Empresa
from apps.ml_models.models import MLModel, TrainingJob, MLPrediction
from apps.ml_models.services.training_service import TrainingService
from apps.ml_models.services.data_extractor import DataExtractor
import time


class MLModelViewSet(viewsets.ViewSet):
    """
    ViewSet para gestionar modelos ML por empresa
    """
    permission_classes = [IsAuthenticated]
    
    def _get_empresa(self, request):
        """Obtiene la empresa del usuario autenticado"""
        # Asumiendo que el usuario tiene relación con empresa
        # Ajustar según tu modelo de Usuario
        if hasattr(request.user, 'usuario'):
            return request.user.usuario.empresa
        elif hasattr(request.user, 'empresa'):
            return request.user.empresa
        else:
            # Fallback: usar empresa_id del request
            empresa_id = request.data.get('empresa_id') or request.query_params.get('empresa_id')
            if empresa_id:
                return get_object_or_404(Empresa, id=empresa_id)
            raise ValueError("No se pudo determinar la empresa del usuario")
    
    @action(detail=False, methods=['post'], url_path='train/rfm')
    def train_rfm(self, request):
        """
        Entrena modelo de segmentación RFM para la empresa del usuario
        
        POST /api/ml/models/train/rfm/
        Body: {
            "n_clusters": 5  // opcional
        }
        """
        try:
            empresa = self._get_empresa(request)
            n_clusters = request.data.get('n_clusters', 5)
            
            # Crear servicio de entrenamiento
            training_service = TrainingService(empresa)
            
            # Entrenar modelo
            ml_model = training_service.train_rfm_segmentation(n_clusters=n_clusters)
            
            return Response({
                'success': True,
                'message': f'Modelo RFM entrenado exitosamente para {empresa.nombre}',
                'model': {
                    'id': ml_model.id,
                    'type': ml_model.model_type,
                    'version': ml_model.version,
                    'training_samples': ml_model.training_samples,
                    'training_info': ml_model.training_data_info,
                    'trained_at': ml_model.trained_at,
                }
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Error al entrenar modelo: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='train/churn')
    def train_churn(self, request):
        """
        Entrena modelo de predicción de churn
        
        POST /api/ml/models/train/churn/
        """
        try:
            empresa = self._get_empresa(request)
            training_service = TrainingService(empresa)
            ml_model = training_service.train_churn_prediction()
            
            return Response({
                'success': True,
                'message': f'Modelo de Churn entrenado exitosamente',
                'model': {
                    'id': ml_model.id,
                    'type': ml_model.model_type,
                    'version': ml_model.version,
                    'training_samples': ml_model.training_samples,
                    'training_info': ml_model.training_data_info,
                    'trained_at': ml_model.trained_at,
                }
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='train/recommendations')
    def train_recommendations(self, request):
        """
        Entrena modelo de recomendaciones de productos
        
        POST /api/ml/models/train/recommendations/
        Body: {
            "min_support": 0.01,  // opcional
            "min_confidence": 0.2  // opcional
        }
        """
        try:
            empresa = self._get_empresa(request)
            min_support = float(request.data.get('min_support', 0.01))
            min_confidence = float(request.data.get('min_confidence', 0.2))
            
            training_service = TrainingService(empresa)
            ml_model = training_service.train_product_recommendations(
                min_support=min_support,
                min_confidence=min_confidence
            )
            
            return Response({
                'success': True,
                'message': f'Modelo de Recomendaciones entrenado exitosamente',
                'model': {
                    'id': ml_model.id,
                    'type': ml_model.model_type,
                    'version': ml_model.version,
                    'training_samples': ml_model.training_samples,
                    'training_info': ml_model.training_data_info,
                    'trained_at': ml_model.trained_at,
                }
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='train/all')
    def train_all(self, request):
        """
        Entrena todos los modelos disponibles
        
        POST /api/ml/models/train/all/
        """
        try:
            empresa = self._get_empresa(request)
            training_service = TrainingService(empresa)
            results = training_service.train_all_models()
            
            return Response({
                'success': True,
                'message': f'Entrenamiento completado',
                'results': {
                    'success_count': len(results['success']),
                    'failed_count': len(results['failed']),
                    'success': [
                        {
                            'type': item['type'],
                            'model_id': item['model'].id,
                            'version': item['model'].version,
                        }
                        for item in results['success']
                    ],
                    'failed': results['failed'],
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], url_path='list')
    def list_models(self, request):
        """
        Lista todos los modelos de la empresa
        
        GET /api/ml/models/list/
        """
        try:
            empresa = self._get_empresa(request)
            models = MLModel.objects.filter(empresa=empresa).order_by('-created_at')
            
            return Response({
                'success': True,
                'models': [
                    {
                        'id': model.id,
                        'type': model.model_type,
                        'type_display': model.get_model_type_display(),
                        'version': model.version,
                        'status': model.status,
                        'training_samples': model.training_samples,
                        'trained_at': model.trained_at,
                        'last_used_at': model.last_used_at,
                    }
                    for model in models
                ]
            })
            
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], url_path='status')
    def check_status(self, request):
        """
        Verifica el estado de los modelos y si necesitan reentrenamiento
        
        GET /api/ml/models/status/
        """
        try:
            empresa = self._get_empresa(request)
            training_service = TrainingService(empresa)
            extractor = DataExtractor(empresa)
            
            # Obtener resumen de datos
            data_summary = extractor.get_data_summary()
            
            # Verificar estado de cada tipo de modelo
            model_types = ['rfm_segmentation', 'churn_prediction', 'product_recommendations']
            models_status = []
            
            for model_type in model_types:
                active_model = training_service.get_active_model(model_type)
                needs_retraining, reason = training_service.check_if_retraining_needed(model_type)
                
                models_status.append({
                    'type': model_type,
                    'has_model': active_model is not None,
                    'version': active_model.version if active_model else None,
                    'trained_at': active_model.trained_at if active_model else None,
                    'needs_retraining': needs_retraining,
                    'retraining_reason': reason,
                })
            
            return Response({
                'success': True,
                'empresa': data_summary,
                'models': models_status,
            })
            
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='predict/rfm')
    def predict_rfm(self, request):
        """
        Realiza segmentación RFM de clientes
        
        POST /api/ml/models/predict/rfm/
        """
        try:
            start_time = time.time()
            empresa = self._get_empresa(request)
            training_service = TrainingService(empresa)
            extractor = DataExtractor(empresa)
            
            # Cargar modelo
            model_data, ml_model = training_service.load_model('rfm_segmentation')
            
            # Extraer datos actuales
            rfm_data = extractor.extract_rfm_data()
            
            # Predecir (segmentar)
            from apps.ml_models.customer_analytics.rfm_segmentation import RFMSegmentation
            model = RFMSegmentation()
            model.kmeans = model_data['kmeans']
            model.scaler = model_data['scaler']
            model.segment_mapping = model_data['segment_mapping']
            model.features = model_data['features']
            
            df_segmented = model.predict(rfm_data)
            
            # Estadísticas por segmento
            stats = model.get_segment_statistics(df_segmented)
            
            # Guardar predicción
            execution_time = int((time.time() - start_time) * 1000)
            MLPrediction.objects.create(
                model=ml_model,
                input_data={'clientes_count': len(rfm_data)},
                prediction={'segments': stats},
                execution_time_ms=execution_time
            )
            
            return Response({
                'success': True,
                'segments': stats,
                'total_clientes': len(df_segmented),
                'model_version': ml_model.version,
                'execution_time_ms': execution_time,
            })
            
        except ValueError as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='predict/churn')
    def predict_churn(self, request):
        """
        Predice clientes en riesgo de churn
        
        POST /api/ml/models/predict/churn/
        """
        try:
            start_time = time.time()
            empresa = self._get_empresa(request)
            training_service = TrainingService(empresa)
            extractor = DataExtractor(empresa)
            
            # Cargar modelo
            model_data, ml_model = training_service.load_model('churn_prediction')
            
            # Extraer datos actuales
            rfm_data = extractor.extract_rfm_data()
            
            # Predecir
            from apps.ml_models.customer_analytics.churn_prediction import ChurnPredictor
            model = ChurnPredictor()
            model.model = model_data['model']
            model.features = model_data['features']
            
            df_predicted = model.predict(rfm_data)
            
            # Clientes en riesgo
            high_risk = df_predicted[df_predicted['churn_risk'] == 'Alto'].to_dict('records')
            
            execution_time = int((time.time() - start_time) * 1000)
            MLPrediction.objects.create(
                model=ml_model,
                input_data={'clientes_count': len(rfm_data)},
                prediction={'high_risk_count': len(high_risk)},
                execution_time_ms=execution_time
            )
            
            return Response({
                'success': True,
                'total_clientes': len(df_predicted),
                'high_risk_count': len(high_risk),
                'high_risk_clientes': high_risk[:20],  # Top 20
                'model_version': ml_model.version,
                'execution_time_ms': execution_time,
            })
            
        except ValueError as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='predict/recommendations')
    def predict_recommendations(self, request):
        """
        Obtiene recomendaciones de productos
        
        POST /api/ml/models/predict/recommendations/
        Body: {
            "producto_id": 123  // opcional, para recomendar basado en un producto
        }
        """
        try:
            start_time = time.time()
            empresa = self._get_empresa(request)
            training_service = TrainingService(empresa)
            producto_id = request.data.get('producto_id')
            
            # Cargar modelo
            model_data, ml_model = training_service.load_model('product_recommendations')
            
            # Obtener recomendaciones
            from apps.ml_models.product_recommendations.association_rules import ProductRecommender
            model = ProductRecommender()
            model.rules = model_data['rules']
            model.frequent_itemsets = model_data['frequent_itemsets']
            
            if producto_id:
                recommendations = model.recommend_for_product(producto_id, top_n=10)
            else:
                recommendations = model.get_top_product_pairs(top_n=20)
            
            execution_time = int((time.time() - start_time) * 1000)
            MLPrediction.objects.create(
                model=ml_model,
                input_data={'producto_id': producto_id},
                prediction={'recommendations_count': len(recommendations)},
                execution_time_ms=execution_time
            )
            
            return Response({
                'success': True,
                'recommendations': recommendations,
                'model_version': ml_model.version,
                'execution_time_ms': execution_time,
            })
            
        except ValueError as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], url_path='training-history')
    def training_history(self, request):
        """
        Obtiene el historial de entrenamientos
        
        GET /api/ml/models/training-history/
        """
        try:
            empresa = self._get_empresa(request)
            training_service = TrainingService(empresa)
            
            jobs = training_service.get_training_history()
            
            return Response({
                'success': True,
                'jobs': [
                    {
                        'id': job.id,
                        'model_type': job.model_type,
                        'status': job.status,
                        'created_at': job.created_at,
                        'started_at': job.started_at,
                        'completed_at': job.completed_at,
                        'duration_seconds': job.duration_seconds,
                        'error_message': job.error_message,
                    }
                    for job in jobs[:50]  # Últimos 50
                ]
            })
            
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
