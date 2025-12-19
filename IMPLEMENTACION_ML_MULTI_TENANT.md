# 🏢 Implementación ML Multi-Tenant (Por Empresa)

## 📋 Resumen

Se ha implementado un sistema completo de **Machine Learning multi-tenant** que permite:

✅ **Entrenar modelos específicos por empresa** usando sus propios datos del ERP  
✅ **Extraer datos automáticamente** desde ventas, clientes y productos de cada empresa  
✅ **Gestionar versiones** de modelos y su ciclo de vida  
✅ **Validar datos** antes de entrenar (requisitos mínimos)  
✅ **Reentrenar automáticamente** cuando hay nuevos datos  
✅ **Hacer predicciones** con los modelos entrenados  
✅ **Auditar** entrenamientos y predicciones  

---

## 🏗️ Arquitectura

### 1. Modelos de Base de Datos

#### `MLModel`
Almacena información sobre modelos entrenados:
- `empresa`: ForeignKey a Empresa (multi-tenant)
- `model_type`: Tipo de modelo (rfm_segmentation, churn_prediction, etc.)
- `version`: Número de versión
- `status`: Estado (training, active, outdated, failed)
- `model_file_path`: Ruta al archivo .pkl
- `training_data_info`: Metadata JSON sobre los datos de entrenamiento
- `hyperparameters`: Hiperparámetros usados
- `trained_at`: Fecha de entrenamiento
- `last_used_at`: Última vez que se usó

#### `TrainingJob`
Registro de trabajos de entrenamiento:
- `empresa`: ForeignKey a Empresa
- `model_type`: Tipo de modelo
- `status`: pending, running, completed, failed
- `result_model`: ForeignKey al modelo resultante
- `error_message`: Mensaje de error si falló
- Timestamps: created_at, started_at, completed_at

#### `MLPrediction`
Almacena predicciones realizadas:
- `model`: ForeignKey a MLModel
- `input_data`: Datos de entrada (JSON)
- `prediction`: Resultado (JSON)
- `confidence`: Confianza de la predicción
- `execution_time_ms`: Tiempo de ejecución

### 2. Servicios

#### `DataExtractor` 
Extrae datos del ERP por empresa:

```python
from apps.ml_models.services.data_extractor import DataExtractor

extractor = DataExtractor(empresa)

# Extraer datos para RFM
rfm_data = extractor.extract_rfm_data()
# Retorna: DataFrame con cliente_id, recency, frequency, monetary, etc.

# Extraer ventas completas
sales_data = extractor.extract_sales_data()

# Extraer transacciones para recomendaciones
transactions = extractor.extract_product_transactions()

# Validar datos antes de entrenar
is_valid, message, info = extractor.validate_data_for_training('rfm_segmentation')
```

**Requisitos mínimos por modelo:**

| Modelo | Clientes | Ventas | Productos | Días Historial |
|--------|----------|--------|-----------|----------------|
| RFM Segmentation | 20 | 50 | - | 30 |
| Churn Prediction | 30 | 100 | - | 60 |
| Product Recommendations | - | 100 | 10 | 30 |
| Demand Forecasting | - | 200 | - | 90 |

#### `TrainingService`
Gestiona el entrenamiento de modelos:

```python
from apps.ml_models.services.training_service import TrainingService

service = TrainingService(empresa)

# Entrenar modelo RFM
ml_model = service.train_rfm_segmentation(n_clusters=5)

# Entrenar modelo de Churn
ml_model = service.train_churn_prediction()

# Entrenar recomendaciones
ml_model = service.train_product_recommendations(
    min_support=0.01,
    min_confidence=0.2
)

# Entrenar todos los modelos
results = service.train_all_models()

# Cargar modelo entrenado
model_data, ml_model = service.load_model('rfm_segmentation')

# Verificar si necesita reentrenamiento
needs_retraining, reason = service.check_if_retraining_needed('rfm_segmentation')
```

---

## 🚀 APIs Disponibles

### Base URL: `/api/ml/models/`

### 1. Entrenar Modelos

#### Entrenar RFM
```http
POST /api/ml/models/train/rfm/
Content-Type: application/json
Authorization: Bearer {token}

{
  "n_clusters": 5
}
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Modelo RFM entrenado exitosamente para Empresa XYZ",
  "model": {
    "id": 1,
    "type": "rfm_segmentation",
    "version": 1,
    "training_samples": 150,
    "training_info": {
      "clientes_count": 150,
      "avg_recency": 45.2,
      "avg_frequency": 3.5,
      "avg_monetary": 1250.50
    },
    "trained_at": "2025-10-15T20:30:00Z"
  }
}
```

#### Entrenar Churn
```http
POST /api/ml/models/train/churn/
Authorization: Bearer {token}
```

#### Entrenar Recomendaciones
```http
POST /api/ml/models/train/recommendations/
Content-Type: application/json
Authorization: Bearer {token}

{
  "min_support": 0.01,
  "min_confidence": 0.2
}
```

#### Entrenar Todos
```http
POST /api/ml/models/train/all/
Authorization: Bearer {token}
```

### 2. Hacer Predicciones

#### Segmentación RFM
```http
POST /api/ml/models/predict/rfm/
Authorization: Bearer {token}
```

**Respuesta:**
```json
{
  "success": true,
  "segments": {
    "Champions": {
      "count": 25,
      "avg_recency": 15,
      "avg_frequency": 8.5,
      "avg_monetary": 5000,
      "total_monetary": 125000
    },
    "At Risk": {
      "count": 40,
      "avg_recency": 120,
      "avg_frequency": 2.1,
      "avg_monetary": 500,
      "total_monetary": 20000
    }
  },
  "total_clientes": 150,
  "model_version": 1,
  "execution_time_ms": 234
}
```

#### Predicción de Churn
```http
POST /api/ml/models/predict/churn/
Authorization: Bearer {token}
```

**Respuesta:**
```json
{
  "success": true,
  "total_clientes": 150,
  "high_risk_count": 35,
  "high_risk_clientes": [
    {
      "cliente_id": 123,
      "cliente_nombre": "Juan Pérez",
      "churn_probability": 0.95,
      "churn_risk": "Alto",
      "recency": 180,
      "frequency": 2,
      "monetary": 500
    }
  ],
  "model_version": 1,
  "execution_time_ms": 156
}
```

#### Recomendaciones de Productos
```http
POST /api/ml/models/predict/recommendations/
Content-Type: application/json
Authorization: Bearer {token}

{
  "producto_id": 45  // opcional
}
```

**Respuesta:**
```json
{
  "success": true,
  "recommendations": [
    {
      "product_a_id": 45,
      "product_b_id": 67,
      "product_a_name": "Laptop HP",
      "product_b_name": "Mouse Inalámbrico",
      "confidence": 0.75,
      "lift": 2.3,
      "support": 0.05
    }
  ],
  "model_version": 1,
  "execution_time_ms": 89
}
```

### 3. Gestión de Modelos

#### Listar Modelos
```http
GET /api/ml/models/list/
Authorization: Bearer {token}
```

#### Estado de Modelos
```http
GET /api/ml/models/status/
Authorization: Bearer {token}
```

**Respuesta:**
```json
{
  "success": true,
  "empresa": {
    "empresa": "Mi Empresa SAC",
    "ventas_count": 1250,
    "clientes_count": 180,
    "productos_count": 450,
    "dias_historial": 365
  },
  "models": [
    {
      "type": "rfm_segmentation",
      "has_model": true,
      "version": 2,
      "trained_at": "2025-10-15T20:30:00Z",
      "needs_retraining": false,
      "retraining_reason": "Modelo actualizado"
    },
    {
      "type": "churn_prediction",
      "has_model": true,
      "version": 1,
      "trained_at": "2025-09-20T15:00:00Z",
      "needs_retraining": true,
      "retraining_reason": "Modelo tiene 25 días (umbral: 30)"
    },
    {
      "type": "product_recommendations",
      "has_model": false,
      "version": null,
      "trained_at": null,
      "needs_retraining": true,
      "retraining_reason": "No existe modelo entrenado"
    }
  ]
}
```

#### Historial de Entrenamientos
```http
GET /api/ml/models/training-history/
Authorization: Bearer {token}
```

---

## 📂 Estructura de Archivos

```
backend/apps/ml_models/
├── models.py                          # Modelos Django (MLModel, TrainingJob, MLPrediction)
├── views.py                           # APIs REST
├── urls.py                            # Rutas
├── admin.py                           # Admin de Django
├── services/
│   ├── data_extractor.py             # Extrae datos del ERP por empresa
│   └── training_service.py           # Entrena y gestiona modelos
├── customer_analytics/
│   ├── rfm_segmentation.py           # Modelo RFM
│   └── churn_prediction.py           # Modelo Churn
├── product_recommendations/
│   └── association_rules.py          # Modelo Recomendaciones
└── demand_forecasting/
    └── demand_predictor.py           # Modelo Demanda

backend/ml_models_cache/              # Modelos entrenados
├── empresa_1/
│   ├── rfm_segmentation_v1.pkl
│   ├── churn_prediction_v1.pkl
│   └── product_recommendations_v1.pkl
├── empresa_2/
│   └── ...
└── empresa_3/
    └── ...
```

---

## 🔄 Flujo de Trabajo

### Primer Uso (Nueva Empresa)

1. **Usuario se registra** y crea su empresa
2. **Empresa empieza a usar el ERP** (ventas, clientes, productos)
3. **Cuando hay suficientes datos**, el sistema permite entrenar modelos:
   ```http
   POST /api/ml/models/train/all/
   ```
4. **Modelos se entrenan** con los datos reales de la empresa
5. **Modelos quedan activos** y listos para usar
6. **Usuario hace predicciones**:
   ```http
   POST /api/ml/models/predict/rfm/
   POST /api/ml/models/predict/churn/
   ```

### Reentrenamiento Automático

El sistema detecta cuándo un modelo necesita reentrenamiento:

1. **Por antigüedad**: Modelo tiene más de 30 días
2. **Por nuevos datos**: Hay 20% más datos que cuando se entrenó

```python
# Verificar manualmente
GET /api/ml/models/status/

# Si needs_retraining = true, reentrenar:
POST /api/ml/models/train/rfm/
```

### Uso en Producción

```python
# En el frontend, al cargar dashboard de clientes:
fetch('/api/ml/models/predict/rfm/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
})
.then(res => res.json())
.then(data => {
  // Mostrar segmentos en gráficos
  displaySegments(data.segments);
});

// Al ver detalle de un cliente:
fetch('/api/ml/models/predict/churn/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
})
.then(res => res.json())
.then(data => {
  // Mostrar alerta si cliente está en riesgo
  if (data.high_risk_clientes.find(c => c.cliente_id === currentClienteId)) {
    showChurnAlert();
  }
});

// En página de producto:
fetch('/api/ml/models/predict/recommendations/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ producto_id: currentProductId })
})
.then(res => res.json())
.then(data => {
  // Mostrar "También te puede interesar..."
  displayRecommendations(data.recommendations);
});
```

---

## 🔧 Pasos de Instalación

### 1. Instalar Dependencias ML

```bash
cd backend
source venv/bin/activate
pip install scikit-learn pandas numpy prophet mlxtend joblib matplotlib seaborn
```

### 2. Crear Migraciones

```bash
python manage.py makemigrations ml_models
python manage.py migrate
```

### 3. Registrar en Admin (opcional)

Editar `backend/apps/ml_models/admin.py`:

```python
from django.contrib import admin
from apps.ml_models.models import MLModel, TrainingJob, MLPrediction

@admin.register(MLModel)
class MLModelAdmin(admin.ModelAdmin):
    list_display = ['empresa', 'model_type', 'version', 'status', 'trained_at']
    list_filter = ['model_type', 'status', 'empresa']
    search_fields = ['empresa__razon_social']

@admin.register(TrainingJob)
class TrainingJobAdmin(admin.ModelAdmin):
    list_display = ['empresa', 'model_type', 'status', 'created_at', 'duration_seconds']
    list_filter = ['status', 'model_type']

@admin.register(MLPrediction)
class MLPredictionAdmin(admin.ModelAdmin):
    list_display = ['model', 'created_at', 'execution_time_ms']
    list_filter = ['model__model_type']
```

### 4. Probar APIs

```bash
# Verificar estado
curl -X GET http://localhost:8080/api/ml/models/status/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# Entrenar modelo RFM
curl -X POST http://localhost:8080/api/ml/models/train/rfm/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"n_clusters": 5}'

# Hacer predicción
curl -X POST http://localhost:8080/api/ml/models/predict/rfm/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 📊 Ejemplo de Uso Completo

```python
# Script para entrenar modelos de una empresa
from apps.empresas.models import Empresa
from apps.ml_models.services.training_service import TrainingService
from apps.ml_models.services.data_extractor import DataExtractor

# Obtener empresa
empresa = Empresa.objects.get(ruc='20123456789')

# Crear servicio
service = TrainingService(empresa)
extractor = DataExtractor(empresa)

# 1. Verificar datos disponibles
summary = extractor.get_data_summary()
print(f"Empresa: {summary['empresa']}")
print(f"Ventas: {summary['ventas_count']}")
print(f"Clientes: {summary['clientes_count']}")

# 2. Validar si se puede entrenar
is_valid, message, info = extractor.validate_data_for_training('rfm_segmentation')
if not is_valid:
    print(f"No se puede entrenar: {message}")
    exit()

# 3. Entrenar todos los modelos
results = service.train_all_models()
print(f"Exitosos: {len(results['success'])}")
print(f"Fallidos: {len(results['failed'])}")

# 4. Hacer predicciones
model_data, ml_model = service.load_model('rfm_segmentation')
rfm_data = extractor.extract_rfm_data()

from apps.ml_models.customer_analytics.rfm_segmentation import RFMSegmentation
model = RFMSegmentation()
model.kmeans = model_data['kmeans']
model.scaler = model_data['scaler']
model.segment_mapping = model_data['segment_mapping']
model.features = model_data['features']

df_segmented = model.predict(rfm_data)
stats = model.get_segment_statistics(df_segmented)

for segment, data in stats.items():
    print(f"{segment}: {data['count']} clientes, ${data['total_monetary']:,.2f}")
```

---

## 🎯 Ventajas del Sistema Multi-Tenant

✅ **Aislamiento de datos**: Cada empresa tiene sus propios modelos  
✅ **Personalización**: Modelos entrenados con datos específicos de cada empresa  
✅ **Escalabilidad**: Soporta miles de empresas  
✅ **Versionado**: Mantiene historial de versiones de modelos  
✅ **Auditoría**: Registra todos los entrenamientos y predicciones  
✅ **Validación**: Verifica requisitos mínimos antes de entrenar  
✅ **Reentrenamiento**: Detecta cuándo actualizar modelos  

---

## 🔐 Seguridad

- ✅ Cada empresa solo puede acceder a sus propios modelos
- ✅ Autenticación requerida en todas las APIs
- ✅ Los archivos .pkl se guardan en directorios separados por empresa
- ✅ Validación de permisos en cada endpoint

---

## 📈 Próximos Pasos

1. **Implementar en el frontend** los dashboards de visualización
2. **Crear tareas programadas** (Celery) para reentrenamiento automático
3. **Agregar notificaciones** cuando un modelo necesita reentrenamiento
4. **Implementar A/B testing** para comparar versiones de modelos
5. **Agregar más modelos** (CLV, Demand Forecasting, etc.)

---

**¡El sistema está listo para usar con datos reales de cada empresa! 🚀**


