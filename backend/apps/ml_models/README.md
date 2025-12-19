# 🤖 Machine Learning Models - ERP System

## 📋 Descripción

Módulo de Machine Learning que proporciona análisis predictivo y recomendaciones inteligentes para el sistema ERP.

## 🎯 Modelos Implementados

### 1. Customer Analytics
- **RFM Segmentation**: Segmenta clientes en 5 grupos basados en Recency, Frequency, Monetary
- **Churn Prediction**: Predice qué clientes están en riesgo de abandonar

### 2. Product Recommendations
- **Association Rules**: Recomienda productos basados en patrones de compra (Market Basket Analysis)

### 3. Demand Forecasting
- **Prophet Forecasting**: Predice demanda futura de productos con intervalos de confianza

## 🚀 Inicio Rápido

### Instalación

```bash
# Instalar dependencias
pip install -r requirements.txt

# Crear carpeta para modelos
mkdir -p ml_models_cache
```

### Uso Básico

```python
# Segmentar clientes
from apps.ml_models.customer_analytics.rfm_segmentation import segment_customers
result = segment_customers(empresa_id=1)

# Predecir churn
from apps.ml_models.customer_analytics.churn_prediction import predict_churn
result = predict_churn(empresa_id=1)

# Recomendar productos
from apps.ml_models.product_recommendations.association_rules import get_product_recommendations
result = get_product_recommendations(producto_id=123, top_n=5)

# Predecir demanda
from apps.ml_models.demand_forecasting.demand_predictor import forecast_product_demand
result = forecast_product_demand(producto_id=123, days_ahead=30, current_stock=100)
```

## 📡 APIs REST

Todas las APIs requieren autenticación JWT.

### Customer Analytics

**Segmentar Clientes:**
```http
POST /api/ml/customers/segment/
Content-Type: application/json
Authorization: Bearer {token}

{
  "empresa_id": 1  // opcional
}
```

**Predecir Churn:**
```http
POST /api/ml/customers/churn/
Content-Type: application/json
Authorization: Bearer {token}

{
  "empresa_id": 1  // opcional
}
```

**Dashboard de Clientes:**
```http
GET /api/ml/customers/dashboard/?empresa_id=1
Authorization: Bearer {token}
```

### Product Recommendations

**Entrenar Modelo:**
```http
POST /api/ml/products/train-recommendations/
Content-Type: application/json
Authorization: Bearer {token}

{
  "empresa_id": 1  // opcional
}
```

**Obtener Recomendaciones:**
```http
POST /api/ml/products/recommendations/
Content-Type: application/json
Authorization: Bearer {token}

{
  "producto_id": 123,  // Para un producto
  "producto_ids": [1, 2, 3],  // O para una canasta
  "top_n": 5,
  "empresa_id": 1  // opcional
}
```

### Demand Forecasting

**Predecir Demanda:**
```http
POST /api/ml/demand/forecast/
Content-Type: application/json
Authorization: Bearer {token}

{
  "producto_id": 123,
  "days_ahead": 30,
  "current_stock": 100,  // opcional
  "empresa_id": 1  // opcional
}
```

**Predicción en Lote:**
```http
POST /api/ml/demand/batch-forecast/
Content-Type: application/json
Authorization: Bearer {token}

{
  "top_n": 20,
  "days_ahead": 30,
  "empresa_id": 1  // opcional
}
```

### General

**Dashboard ML:**
```http
GET /api/ml/dashboard/?empresa_id=1
Authorization: Bearer {token}
```

**Health Check:**
```http
GET /api/ml/health/
Authorization: Bearer {token}
```

## 📊 Respuestas de API

### Segmentación RFM

```json
{
  "success": true,
  "segments": [
    {
      "cliente_id": 1,
      "recency": 5,
      "frequency": 10,
      "monetary": 5000,
      "R_score": 5,
      "F_score": 4,
      "M_score": 5,
      "RFM_score": 14,
      "segment": 0,
      "segment_name": "Champions"
    }
  ],
  "statistics": {
    "Champions": {
      "count": 50,
      "avg_recency": 10.5,
      "avg_frequency": 12.3,
      "avg_monetary": 4500,
      "total_monetary": 225000,
      "avg_rfm_score": 13.5
    }
  },
  "total_customers": 250,
  "message": "Segmentación completada para 250 clientes"
}
```

### Predicción de Churn

```json
{
  "success": true,
  "at_risk_customers": [
    {
      "id": 1,
      "nombre": "Cliente XYZ",
      "churn_probability": 85.5,
      "churn_risk": "Alto",
      "days_since_purchase": 90,
      "total_purchases": 15,
      "total_spent": 10000,
      "recommended_action": "Cliente valioso en riesgo crítico: Contacto inmediato con oferta personalizada"
    }
  ],
  "statistics": {
    "Alto": {
      "count": 25,
      "avg_churn_prob": 78.5,
      "total_revenue_at_risk": 125000,
      "avg_days_since_purchase": 95
    }
  },
  "high_risk_count": 25,
  "medium_risk_count": 40,
  "total_customers": 250
}
```

### Recomendaciones de Productos

```json
{
  "success": true,
  "recommendations": [
    {
      "id": 456,
      "nombre": "Producto Recomendado",
      "codigo": "PROD-456",
      "categoria": "Electrónica",
      "precio": 299.99,
      "confidence": 75.5,
      "lift": 2.3,
      "support": 15.2,
      "recommendation_strength": "Alta"
    }
  ],
  "count": 5,
  "message": "Se encontraron 5 recomendaciones"
}
```

### Predicción de Demanda

```json
{
  "success": true,
  "product_info": {
    "id": 123,
    "nombre": "Producto ABC",
    "codigo": "PROD-123",
    "precio": 99.99
  },
  "forecast": [
    {
      "fecha": "2025-10-16",
      "demanda_predicha": 15.5,
      "demanda_minima": 10.2,
      "demanda_maxima": 20.8
    }
  ],
  "summary": {
    "total_predicted_demand": 465.0,
    "avg_daily_demand": 15.5,
    "max_daily_demand": 22.3,
    "min_daily_demand": 8.7,
    "trend": "Creciente (+12.5%)",
    "confidence_interval": {
      "lower": 350.0,
      "upper": 580.0
    }
  },
  "reorder_recommendation": {
    "needs_reorder": true,
    "current_stock": 100,
    "reorder_point": 120.5,
    "recommended_order_quantity": 465.0,
    "lead_time_demand": 100.5,
    "safety_stock": 20.0,
    "days_until_stockout": 6,
    "urgency": "CRÍTICO"
  },
  "historical_data_points": 365,
  "message": "Predicción generada para 30 días"
}
```

## 🔧 Configuración

### Variables de Entorno

No se requieren variables de entorno adicionales. Los modelos se guardan en:
```
backend/ml_models_cache/
```

### Requisitos Mínimos de Datos

- **RFM Segmentation**: Mínimo 5 clientes con historial de compras
- **Churn Prediction**: Mínimo 10 clientes con historial
- **Product Recommendations**: Mínimo 10 transacciones
- **Demand Forecasting**: Mínimo 14 días de historial de ventas

## 🎨 Personalización

### Ajustar Parámetros de Segmentación

```python
from apps.ml_models.customer_analytics.rfm_segmentation import RFMSegmentation

rfm = RFMSegmentation(n_clusters=5)  # Cambiar número de segmentos
```

### Ajustar Umbral de Churn

```python
from apps.ml_models.customer_analytics.churn_prediction import ChurnPredictor

predictor = ChurnPredictor()
predictor.CHURN_THRESHOLD_DAYS = 60  # Cambiar de 90 a 60 días
```

### Ajustar Parámetros de Recomendación

```python
from apps.ml_models.product_recommendations.association_rules import ProductRecommender

recommender = ProductRecommender(
    min_support=0.01,      # Mínimo 1% de soporte
    min_confidence=0.3,    # Mínimo 30% de confianza
    min_lift=1.0           # Lift mínimo de 1.0
)
```

## 📈 Métricas y Monitoreo

### Verificar Estado de Modelos

```http
GET /api/ml/health/
```

Respuesta:
```json
{
  "status": "healthy",
  "models": {
    "rfm_segmentation": true,
    "churn_prediction": true,
    "product_recommendations": true
  },
  "message": "ML models service is running"
}
```

## 🐛 Troubleshooting

### Error: "No hay suficientes datos"

**Causa:** No hay suficientes registros históricos  
**Solución:** Esperar a tener más datos o reducir requisitos mínimos

### Error: "Modelo no entrenado"

**Causa:** El modelo no se ha entrenado aún  
**Solución:** Llamar al endpoint de entrenamiento primero

### Error: "No se encontraron patrones frecuentes"

**Causa:** min_support muy alto  
**Solución:** Reducir min_support en ProductRecommender

## 📚 Referencias

- **Prophet**: https://facebook.github.io/prophet/
- **scikit-learn**: https://scikit-learn.org/
- **mlxtend**: http://rasbt.github.io/mlxtend/

## 🤝 Contribuir

Para agregar nuevos modelos:

1. Crear carpeta en `apps/ml_models/`
2. Implementar clase del modelo
3. Agregar función principal de uso
4. Crear vista en `views.py`
5. Agregar ruta en `urls.py`
6. Documentar en este README

## 📄 Licencia

Parte del sistema ERP - Uso interno

---

**Última actualización:** Octubre 2025  
**Versión:** 1.0

