"""
Segmentación RFM (Recency, Frequency, Monetary)
Clasifica clientes en segmentos basados en su comportamiento de compra
"""
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import joblib
import os
from django.conf import settings


class RFMSegmentation:
    """
    Modelo de segmentación RFM usando K-Means clustering
    """
    
    SEGMENT_NAMES = {
        0: 'Champions',        # Alta F, alta M, baja R
        1: 'Loyal Customers',  # Alta F, media M, baja R
        2: 'Potential Loyalists', # Media F, media M, baja R
        3: 'At Risk',          # Baja F, cualquier M, alta R
        4: 'Hibernating',      # Muy baja F, baja M, muy alta R
    }
    
    def __init__(self, n_clusters=5, model_path=None):
        self.n_clusters = n_clusters
        self.model = None
        self.scaler = StandardScaler()
        if model_path:
            self.model_path = model_path
        else:
            self.model_path = os.path.join(settings.BASE_DIR, 'ml_models_cache', 'rfm_model.pkl')
    
    def _calculate_rfm_scores(self, df):
        """
        Calcula scores RFM (1-5) para cada métrica
        """
        df_scored = df.copy()
        
        # Recency: menor es mejor (invertir)
        df_scored['R_score'] = pd.qcut(df['recency'], q=5, labels=[5, 4, 3, 2, 1], duplicates='drop')
        
        # Frequency: mayor es mejor
        df_scored['F_score'] = pd.qcut(df['frequency'].rank(method='first'), q=5, labels=[1, 2, 3, 4, 5], duplicates='drop')
        
        # Monetary: mayor es mejor
        df_scored['M_score'] = pd.qcut(df['monetary'], q=5, labels=[1, 2, 3, 4, 5], duplicates='drop')
        
        # Convertir a numérico
        df_scored['R_score'] = df_scored['R_score'].astype(int)
        df_scored['F_score'] = df_scored['F_score'].astype(int)
        df_scored['M_score'] = df_scored['M_score'].astype(int)
        
        # RFM Score combinado
        df_scored['RFM_score'] = df_scored['R_score'] + df_scored['F_score'] + df_scored['M_score']
        
        return df_scored
    
    def fit(self, df):
        """
        Entrena el modelo de segmentación
        
        Args:
            df: DataFrame con columnas recency, frequency, monetary
        """
        # Ajustar n_clusters si hay pocos clientes
        if df.empty or len(df) < 2:
            raise ValueError(f"Se necesitan al menos 2 clientes para entrenar")
        
        # Si hay menos clientes que clusters, reducir el número de clusters
        if len(df) < self.n_clusters:
            self.n_clusters = max(2, len(df) - 1)
        
        # Calcular scores RFM
        df_scored = self._calculate_rfm_scores(df)
        
        # Preparar features para clustering
        features = df_scored[['recency', 'frequency', 'monetary']].values
        
        # Normalizar
        features_scaled = self.scaler.fit_transform(features)
        
        # Entrenar K-Means
        self.model = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
        df_scored['segment'] = self.model.fit_predict(features_scaled)
        
        # Asignar nombres de segmentos basados en características
        df_scored['segment_name'] = df_scored['segment'].map(
            lambda x: self._get_segment_name(df_scored[df_scored['segment'] == x])
        )
        
        return df_scored
    
    def predict(self, df):
        """
        Predice segmentos para nuevos clientes
        """
        if self.model is None:
            raise ValueError("Modelo no entrenado. Llama a fit() primero")
        
        # Calcular scores RFM
        df_scored = self._calculate_rfm_scores(df)
        
        # Preparar features
        features = df_scored[['recency', 'frequency', 'monetary']].values
        features_scaled = self.scaler.transform(features)
        
        # Predecir
        df_scored['segment'] = self.model.predict(features_scaled)
        df_scored['segment_name'] = df_scored['segment'].map(self.SEGMENT_NAMES)
        
        return df_scored
    
    def _get_segment_name(self, segment_df):
        """
        Determina el nombre del segmento basado en características promedio
        """
        avg_r = segment_df['R_score'].mean()
        avg_f = segment_df['F_score'].mean()
        avg_m = segment_df['M_score'].mean()
        
        # Lógica para asignar nombres
        if avg_f >= 4 and avg_m >= 4 and avg_r >= 4:
            return 'Champions'
        elif avg_f >= 3 and avg_r >= 3:
            return 'Loyal Customers'
        elif avg_r >= 3 and avg_f < 3:
            return 'Potential Loyalists'
        elif avg_r <= 2 and avg_f >= 2:
            return 'At Risk'
        else:
            return 'Hibernating'
    
    def get_segment_statistics(self, df_segmented):
        """
        Calcula estadísticas por segmento
        """
        stats = df_segmented.groupby('segment_name').agg({
            'cliente_id': 'count',
            'recency': 'mean',
            'frequency': 'mean',
            'monetary': ['mean', 'sum'],
            'RFM_score': 'mean'
        }).round(2)
        
        stats.columns = ['count', 'avg_recency', 'avg_frequency', 'avg_monetary', 'total_monetary', 'avg_rfm_score']
        
        return stats.to_dict('index')
    
    def save_model(self):
        """Guarda el modelo entrenado"""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'n_clusters': self.n_clusters
        }, self.model_path)
    
    def load_model(self):
        """Carga el modelo guardado"""
        if os.path.exists(self.model_path):
            data = joblib.load(self.model_path)
            self.model = data['model']
            self.scaler = data['scaler']
            self.n_clusters = data['n_clusters']
            return True
        return False


def segment_customers(empresa_id=None):
    """
    Función principal para segmentar clientes
    
    Returns:
        dict con segmentos y estadísticas
    """
    from apps.ml_models.utils.data_preparation import prepare_customer_data
    
    # Preparar datos
    df = prepare_customer_data(empresa_id)
    
    if df.empty or len(df) < 5:
        return {
            'success': False,
            'message': 'No hay suficientes datos de clientes para segmentar',
            'segments': [],
            'statistics': {}
        }
    
    # Crear y entrenar modelo
    rfm = RFMSegmentation(n_clusters=5)
    
    try:
        df_segmented = rfm.fit(df)
        
        # Obtener estadísticas
        stats = rfm.get_segment_statistics(df_segmented)
        
        # Preparar resultados
        segments = df_segmented.to_dict('records')
        
        # Guardar modelo
        rfm.save_model()
        
        return {
            'success': True,
            'segments': segments,
            'statistics': stats,
            'total_customers': len(df_segmented),
            'message': f'Segmentación completada para {len(df_segmented)} clientes'
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'Error en segmentación: {str(e)}',
            'segments': [],
            'statistics': {}
        }

