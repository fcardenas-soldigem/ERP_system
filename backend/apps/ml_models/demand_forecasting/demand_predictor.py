"""
Predicción de Demanda usando Prophet (Facebook)
Predice la demanda futura de productos basándose en historial de ventas
"""
import pandas as pd
import numpy as np
from prophet import Prophet
import joblib
import os
from django.conf import settings
from datetime import datetime, timedelta


class DemandForecaster:
    """
    Modelo de predicción de demanda usando Prophet
    """
    
    def __init__(self):
        self.model = None
        self.producto_id = None
        self.model_path_template = os.path.join(settings.BASE_DIR, 'ml_models_cache', 'demand_forecast_{}.pkl')
    
    def fit(self, df, producto_id):
        """
        Entrena el modelo de predicción
        
        Args:
            df: DataFrame con columnas ds (fecha) y y (cantidad)
            producto_id: ID del producto
        """
        if df.empty or len(df) < 14:  # Mínimo 2 semanas de datos
            raise ValueError("Se necesitan al menos 14 días de datos históricos")
        
        self.producto_id = producto_id
        
        # Crear y configurar modelo Prophet
        self.model = Prophet(
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality='auto',
            changepoint_prior_scale=0.05,  # Flexibilidad en cambios de tendencia
            seasonality_prior_scale=10.0,   # Fuerza de estacionalidad
        )
        
        # Entrenar
        self.model.fit(df)
        
        return self.model
    
    def predict(self, days_ahead=30):
        """
        Predice la demanda futura
        
        Args:
            days_ahead: Días a predecir hacia adelante
        
        Returns:
            DataFrame con predicciones
        """
        if self.model is None:
            raise ValueError("Modelo no entrenado. Llama a fit() primero")
        
        # Crear dataframe futuro
        future = self.model.make_future_dataframe(periods=days_ahead)
        
        # Predecir
        forecast = self.model.predict(future)
        
        # Asegurar que no haya valores negativos
        forecast['yhat'] = forecast['yhat'].clip(lower=0)
        forecast['yhat_lower'] = forecast['yhat_lower'].clip(lower=0)
        forecast['yhat_upper'] = forecast['yhat_upper'].clip(lower=0)
        
        return forecast
    
    def get_forecast_summary(self, forecast, days_ahead=30):
        """
        Resume las predicciones futuras
        """
        # Filtrar solo predicciones futuras
        future_forecast = forecast.tail(days_ahead)
        
        summary = {
            'total_predicted_demand': round(future_forecast['yhat'].sum(), 2),
            'avg_daily_demand': round(future_forecast['yhat'].mean(), 2),
            'max_daily_demand': round(future_forecast['yhat'].max(), 2),
            'min_daily_demand': round(future_forecast['yhat'].min(), 2),
            'trend': self._analyze_trend(future_forecast),
            'confidence_interval': {
                'lower': round(future_forecast['yhat_lower'].sum(), 2),
                'upper': round(future_forecast['yhat_upper'].sum(), 2)
            }
        }
        
        return summary
    
    def _analyze_trend(self, forecast_df):
        """
        Analiza la tendencia de la predicción
        """
        if len(forecast_df) < 2:
            return 'Insuficientes datos'
        
        first_week = forecast_df.head(7)['yhat'].mean()
        last_week = forecast_df.tail(7)['yhat'].mean()
        
        change_pct = ((last_week - first_week) / first_week * 100) if first_week > 0 else 0
        
        if change_pct > 10:
            return f'Creciente (+{round(change_pct, 1)}%)'
        elif change_pct < -10:
            return f'Decreciente ({round(change_pct, 1)}%)'
        else:
            return 'Estable'
    
    def get_reorder_recommendation(self, forecast, current_stock, lead_time_days=7):
        """
        Recomienda cuándo y cuánto reordenar
        
        Args:
            forecast: DataFrame con predicciones
            current_stock: Stock actual del producto
            lead_time_days: Días que tarda en llegar el pedido
        
        Returns:
            dict con recomendación de reorden
        """
        # Demanda durante el lead time
        lead_time_forecast = forecast.head(lead_time_days)
        lead_time_demand = lead_time_forecast['yhat'].sum()
        
        # Demanda para el próximo mes
        next_month_forecast = forecast.head(30)
        next_month_demand = next_month_forecast['yhat'].sum()
        
        # Punto de reorden (demanda durante lead time + stock de seguridad)
        safety_stock = lead_time_demand * 0.2  # 20% de seguridad
        reorder_point = lead_time_demand + safety_stock
        
        # Cantidad óptima de pedido (demanda de 30 días)
        optimal_order_quantity = next_month_demand
        
        # Determinar si necesita reordenar
        needs_reorder = current_stock < reorder_point
        days_until_stockout = self._calculate_days_until_stockout(current_stock, forecast)
        
        return {
            'needs_reorder': needs_reorder,
            'current_stock': current_stock,
            'reorder_point': round(reorder_point, 2),
            'recommended_order_quantity': round(optimal_order_quantity, 2),
            'lead_time_demand': round(lead_time_demand, 2),
            'safety_stock': round(safety_stock, 2),
            'days_until_stockout': days_until_stockout,
            'urgency': self._get_urgency_level(days_until_stockout, lead_time_days)
        }
    
    def _calculate_days_until_stockout(self, current_stock, forecast):
        """
        Calcula en cuántos días se agotará el stock
        """
        cumulative_demand = 0
        for i, row in forecast.iterrows():
            cumulative_demand += row['yhat']
            if cumulative_demand >= current_stock:
                return i + 1
        return len(forecast) + 1  # Stock suficiente para todo el período
    
    def _get_urgency_level(self, days_until_stockout, lead_time_days):
        """
        Determina el nivel de urgencia del reorden
        """
        if days_until_stockout <= lead_time_days:
            return 'CRÍTICO'
        elif days_until_stockout <= lead_time_days * 1.5:
            return 'ALTO'
        elif days_until_stockout <= lead_time_days * 2:
            return 'MEDIO'
        else:
            return 'BAJO'
    
    def save_model(self):
        """Guarda el modelo entrenado"""
        if self.producto_id is None:
            raise ValueError("No hay producto_id asociado al modelo")
        
        model_path = self.model_path_template.format(self.producto_id)
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        joblib.dump({
            'model': self.model,
            'producto_id': self.producto_id
        }, model_path)
    
    def load_model(self, producto_id):
        """Carga el modelo guardado"""
        model_path = self.model_path_template.format(producto_id)
        
        if os.path.exists(model_path):
            data = joblib.load(model_path)
            self.model = data['model']
            self.producto_id = data['producto_id']
            return True
        return False


def forecast_product_demand(producto_id, days_ahead=30, current_stock=None, empresa_id=None):
    """
    Predice la demanda futura de un producto
    
    Args:
        producto_id: ID del producto
        days_ahead: Días a predecir
        current_stock: Stock actual (opcional, para recomendación de reorden)
        empresa_id: ID de la empresa
    
    Returns:
        dict con predicciones y recomendaciones
    """
    from apps.ml_models.utils.data_preparation import prepare_demand_data, get_product_info
    
    # Preparar datos históricos
    df = prepare_demand_data(producto_id, empresa_id, days_back=365)
    
    if df.empty or len(df) < 14:
        return {
            'success': False,
            'message': 'No hay suficientes datos históricos para predecir (mínimo 14 días)',
            'forecast': [],
            'summary': {}
        }
    
    # Crear y entrenar modelo
    forecaster = DemandForecaster()
    
    try:
        forecaster.fit(df, producto_id)
        
        # Predecir
        forecast = forecaster.predict(days_ahead)
        
        # Obtener resumen
        summary = forecaster.get_forecast_summary(forecast, days_ahead)
        
        # Recomendación de reorden si se proporciona stock actual
        reorder_recommendation = None
        if current_stock is not None:
            reorder_recommendation = forecaster.get_reorder_recommendation(
                forecast.tail(days_ahead),
                current_stock
            )
        
        # Preparar datos de forecast para respuesta
        future_forecast = forecast.tail(days_ahead)[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
        future_forecast['ds'] = future_forecast['ds'].dt.strftime('%Y-%m-%d')
        future_forecast = future_forecast.rename(columns={
            'ds': 'fecha',
            'yhat': 'demanda_predicha',
            'yhat_lower': 'demanda_minima',
            'yhat_upper': 'demanda_maxima'
        })
        
        # Información del producto
        product_info = get_product_info(producto_id)
        
        # Guardar modelo
        forecaster.save_model()
        
        return {
            'success': True,
            'product_info': product_info,
            'forecast': future_forecast.to_dict('records'),
            'summary': summary,
            'reorder_recommendation': reorder_recommendation,
            'historical_data_points': len(df),
            'message': f'Predicción generada para {days_ahead} días'
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'Error al predecir demanda: {str(e)}',
            'forecast': [],
            'summary': {}
        }


def batch_forecast_top_products(empresa_id=None, top_n=20, days_ahead=30):
    """
    Predice demanda para los productos más vendidos
    
    Args:
        empresa_id: ID de la empresa
        top_n: Número de productos a analizar
        days_ahead: Días a predecir
    
    Returns:
        dict con predicciones de múltiples productos
    """
    from apps.ventas.models import VentaDetalle
    from django.db.models import Sum, Count
    
    # Obtener top productos por ventas
    top_products_qs = VentaDetalle.objects.values('producto_id').annotate(
        total_vendido=Sum('cantidad'),
        num_ventas=Count('id')
    ).order_by('-total_vendido')
    
    if empresa_id:
        top_products_qs = top_products_qs.filter(venta__empresa_id=empresa_id)
    
    top_products = list(top_products_qs[:top_n])
    
    # Predecir para cada producto
    forecasts = []
    for product in top_products:
        producto_id = product['producto_id']
        result = forecast_product_demand(producto_id, days_ahead, empresa_id=empresa_id)
        
        if result['success']:
            forecasts.append({
                'producto_id': producto_id,
                'product_info': result['product_info'],
                'summary': result['summary'],
                'historical_sales': product['total_vendido']
            })
    
    return {
        'success': True,
        'forecasts': forecasts,
        'total_products_analyzed': len(forecasts),
        'message': f'Predicciones generadas para {len(forecasts)} productos'
    }

