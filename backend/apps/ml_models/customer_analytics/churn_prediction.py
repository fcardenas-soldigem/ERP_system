"""
Predicción de Churn (Abandono de Clientes)
Predice qué clientes están en riesgo de abandonar
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import os
from django.conf import settings
from datetime import timedelta


class ChurnPredictor:
    """
    Modelo de predicción de churn usando Random Forest
    """
    
    CHURN_THRESHOLD_DAYS = 90  # Días sin comprar para considerar churn
    
    def __init__(self, model_path=None):
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []
        if model_path:
            self.model_path = model_path
        else:
            self.model_path = os.path.join(settings.BASE_DIR, 'ml_models_cache', 'churn_model.pkl')
    
    def _engineer_features(self, df):
        """
        Crea features adicionales para el modelo
        """
        df_features = df.copy()
        
        # Features de comportamiento
        df_features['days_since_last_purchase'] = df['recency']
        df_features['purchase_frequency'] = df['frequency']
        df_features['total_spent'] = df['monetary']
        df_features['avg_order_value'] = df['avg_ticket']
        df_features['customer_lifetime_days'] = df['customer_age_days']
        
        # Features calculadas
        df_features['purchase_rate'] = df_features['frequency'] / (df_features['customer_lifetime_days'] + 1)
        df_features['recency_ratio'] = df_features['recency'] / (df_features['customer_lifetime_days'] + 1)
        
        # Indicadores de riesgo
        df_features['is_inactive'] = (df_features['recency'] > 60).astype(int)
        df_features['low_frequency'] = (df_features['frequency'] < 3).astype(int)
        df_features['declining_engagement'] = (
            (df_features['recency'] > df_features['customer_lifetime_days'] * 0.3).astype(int)
        )
        
        return df_features
    
    def _create_labels(self, df):
        """
        Crea etiquetas de churn basadas en recency
        """
        # Cliente en churn si no ha comprado en CHURN_THRESHOLD_DAYS
        df['is_churned'] = (df['recency'] > self.CHURN_THRESHOLD_DAYS).astype(int)
        return df
    
    def fit(self, df):
        """
        Entrena el modelo de predicción de churn
        """
        if df.empty or len(df) < 2:
            raise ValueError("Se necesitan al menos 2 clientes para entrenar")
        
        # Crear features
        df_features = self._engineer_features(df)
        df_features = self._create_labels(df_features)
        
        # Seleccionar features para el modelo
        self.feature_names = [
            'days_since_last_purchase', 'purchase_frequency', 'total_spent',
            'avg_order_value', 'customer_lifetime_days', 'purchase_rate',
            'recency_ratio', 'is_inactive', 'low_frequency', 'declining_engagement'
        ]
        
        X = df_features[self.feature_names].values
        y = df_features['is_churned'].values
        
        # Normalizar features
        X_scaled = self.scaler.fit_transform(X)
        
        # Entrenar Random Forest
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'  # Manejar desbalance de clases
        )
        self.model.fit(X_scaled, y)
        
        return df_features
    
    def predict(self, df):
        """
        Predice probabilidad de churn para clientes
        """
        if self.model is None:
            raise ValueError("Modelo no entrenado. Llama a fit() primero")
        
        # Crear features
        df_features = self._engineer_features(df)
        
        # Preparar datos
        X = df_features[self.feature_names].values
        X_scaled = self.scaler.transform(X)
        
        # Predecir
        df_features['churn_probability'] = self.model.predict_proba(X_scaled)[:, 1]
        df_features['churn_risk'] = df_features['churn_probability'].apply(self._categorize_risk)
        df_features['is_at_risk'] = (df_features['churn_probability'] > 0.5).astype(int)
        
        return df_features
    
    def _categorize_risk(self, probability):
        """
        Categoriza el riesgo de churn
        """
        if probability >= 0.7:
            return 'Alto'
        elif probability >= 0.4:
            return 'Medio'
        else:
            return 'Bajo'
    
    def get_feature_importance(self):
        """
        Retorna la importancia de cada feature
        """
        if self.model is None:
            return {}
        
        importance = dict(zip(self.feature_names, self.model.feature_importances_))
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
    
    def get_risk_statistics(self, df_predicted):
        """
        Calcula estadísticas por nivel de riesgo
        """
        stats = df_predicted.groupby('churn_risk').agg({
            'cliente_id': 'count',
            'churn_probability': 'mean',
            'monetary': 'sum',
            'recency': 'mean'
        }).round(2)
        
        stats.columns = ['count', 'avg_churn_prob', 'total_revenue_at_risk', 'avg_days_since_purchase']
        
        return stats.to_dict('index')
    
    def save_model(self):
        """Guarda el modelo entrenado"""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names
        }, self.model_path)
    
    def load_model(self):
        """Carga el modelo guardado"""
        if os.path.exists(self.model_path):
            data = joblib.load(self.model_path)
            self.model = data['model']
            self.scaler = data['scaler']
            self.feature_names = data['feature_names']
            return True
        return False


def predict_churn(empresa_id=None):
    """
    Función principal para predecir churn de clientes
    
    Returns:
        dict con predicciones y estadísticas
    """
    from apps.ml_models.utils.data_preparation import prepare_customer_data, get_cliente_info
    
    # Preparar datos
    df = prepare_customer_data(empresa_id)
    
    if df.empty or len(df) < 10:
        return {
            'success': False,
            'message': 'No hay suficientes datos de clientes para predecir churn',
            'predictions': [],
            'statistics': {},
            'at_risk_customers': []
        }
    
    # Crear y entrenar modelo
    predictor = ChurnPredictor()
    
    try:
        # Entrenar con datos históricos
        predictor.fit(df)
        
        # Predecir
        df_predicted = predictor.predict(df)
        
        # Obtener clientes en riesgo
        at_risk = df_predicted[df_predicted['churn_risk'].isin(['Alto', 'Medio'])].sort_values(
            'churn_probability', ascending=False
        )
        
        # Enriquecer con información del cliente
        at_risk_list = []
        for _, row in at_risk.head(50).iterrows():  # Top 50 en riesgo
            cliente_info = get_cliente_info(row['cliente_id'])
            if cliente_info:
                at_risk_list.append({
                    **cliente_info,
                    'churn_probability': round(row['churn_probability'] * 100, 2),
                    'churn_risk': row['churn_risk'],
                    'days_since_purchase': int(row['recency']),
                    'total_purchases': int(row['frequency']),
                    'total_spent': float(row['monetary']),
                    'recommended_action': get_recommended_action(row)
                })
        
        # Estadísticas
        stats = predictor.get_risk_statistics(df_predicted)
        feature_importance = predictor.get_feature_importance()
        
        # Guardar modelo
        predictor.save_model()
        
        return {
            'success': True,
            'predictions': df_predicted.to_dict('records'),
            'at_risk_customers': at_risk_list,
            'statistics': stats,
            'feature_importance': feature_importance,
            'total_customers': len(df_predicted),
            'high_risk_count': len(df_predicted[df_predicted['churn_risk'] == 'Alto']),
            'medium_risk_count': len(df_predicted[df_predicted['churn_risk'] == 'Medio']),
            'message': f'Predicción completada para {len(df_predicted)} clientes'
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'Error en predicción de churn: {str(e)}',
            'predictions': [],
            'statistics': {},
            'at_risk_customers': []
        }


def get_recommended_action(customer_row):
    """
    Sugiere acción basada en el perfil del cliente
    """
    prob = customer_row['churn_probability']
    recency = customer_row['recency']
    frequency = customer_row['frequency']
    
    if prob > 0.7:
        if frequency > 10:
            return "Cliente valioso en riesgo crítico: Contacto inmediato con oferta personalizada"
        else:
            return "Riesgo crítico: Enviar campaña de reactivación con descuento especial"
    elif prob > 0.4:
        if recency > 60:
            return "Inactivo: Enviar recordatorio con productos recomendados"
        else:
            return "Monitorear: Incluir en campaña de fidelización"
    else:
        return "Bajo riesgo: Continuar con comunicación regular"

