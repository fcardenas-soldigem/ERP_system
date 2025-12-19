# 📊 Estructura de Tablas para Machine Learning

## 🗄️ Base de Datos: PostgreSQL

**Decisión:** Usar tablas relacionales tradicionales (NO base de datos vectorial)

---

## 📐 Diagrama de Tablas

```
┌──────────────────────────────────────────────────────────────┐
│                        EMPRESAS                               │
│  ┌────────────────────────────────────────────────────┐     │
│  │ • id (PK)                                           │     │
│  │ • ruc (UNIQUE)                                      │     │
│  │ • razon_social                                      │     │
│  │ • direccion, telefono, email                        │     │
│  │ • activo                                            │     │
│  │ • fecha_registro                                    │     │
│  └────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
                            │
                            │ 1:N (Una empresa tiene muchos modelos)
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                        ML_MODEL                               │
│  ┌────────────────────────────────────────────────────┐     │
│  │ • id (PK)                                           │     │
│  │ • empresa_id (FK → empresas.id)                    │     │
│  │ • model_type                                        │     │
│  │   - rfm_segmentation                                │     │
│  │   - churn_prediction                                │     │
│  │   - product_recommendations                         │     │
│  │   - demand_forecasting                              │     │
│  │ • version (INT)                                     │     │
│  │ • status                                            │     │
│  │   - training, active, outdated, failed              │     │
│  │ • accuracy (FLOAT)                                  │     │
│  │ • training_samples (INT)                            │     │
│  │ • model_file_path (VARCHAR)                         │     │
│  │ • training_data_info (JSON)                         │     │
│  │   {                                                 │     │
│  │     "clientes_count": 150,                          │     │
│  │     "avg_recency": 45.2,                            │     │
│  │     "avg_frequency": 3.5                            │     │
│  │   }                                                 │     │
│  │ • hyperparameters (JSON)                            │     │
│  │   {                                                 │     │
│  │     "n_clusters": 5,                                │     │
│  │     "random_state": 42                              │     │
│  │   }                                                 │     │
│  │ • created_at (TIMESTAMP)                            │     │
│  │ • trained_at (TIMESTAMP)                            │     │
│  │ • last_used_at (TIMESTAMP)                          │     │
│  │                                                     │     │
│  │ UNIQUE(empresa_id, model_type, version)            │     │
│  │ INDEX(empresa_id, model_type, status)              │     │
│  └────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
           │                                      │
           │ 1:1                                  │ 1:N
           ▼                                      ▼
┌─────────────────────┐              ┌────────────────────────┐
│   TRAINING_JOB      │              │    ML_PREDICTION       │
│  ┌────────────────┐ │              │  ┌──────────────────┐ │
│  │ • id (PK)      │ │              │  │ • id (PK)        │ │
│  │ • empresa_id   │ │              │  │ • model_id (FK)  │ │
│  │ • model_type   │ │              │  │ • input_data     │ │
│  │ • status       │ │              │  │   (JSON)         │ │
│  │   - pending    │ │              │  │ • prediction     │ │
│  │   - running    │ │              │  │   (JSON)         │ │
│  │   - completed  │ │              │  │ • confidence     │ │
│  │   - failed     │ │              │  │ • execution_time │ │
│  │ • result_model │ │              │  │ • created_at     │ │
│  │   (FK)         │ │              │  │                  │ │
│  │ • error_msg    │ │              │  │ INDEX(model_id,  │ │
│  │ • created_at   │ │              │  │   created_at)    │ │
│  │ • started_at   │ │              │  └──────────────────┘ │
│  │ • completed_at │ │              └────────────────────────┘
│  └────────────────┘ │
└─────────────────────┘
```

---

## 📋 Descripción de Tablas

### 1. **ML_MODEL** - Modelos Entrenados

**Propósito:** Almacenar metadata de cada modelo entrenado por empresa

**Campos clave:**

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `empresa_id` | FK | Empresa dueña del modelo | 1 |
| `model_type` | VARCHAR | Tipo de modelo | 'rfm_segmentation' |
| `version` | INT | Versión del modelo | 1, 2, 3, ... |
| `status` | VARCHAR | Estado actual | 'active' |
| `model_file_path` | VARCHAR | Ruta al .pkl | '/ml_cache/empresa_1/rfm_v1.pkl' |
| `training_data_info` | JSON | Info sobre datos de entrenamiento | `{"clientes": 150}` |
| `hyperparameters` | JSON | Parámetros del modelo | `{"n_clusters": 5}` |
| `trained_at` | TIMESTAMP | Cuándo se entrenó | '2025-10-22 10:30:00' |
| `last_used_at` | TIMESTAMP | Última predicción | '2025-10-22 15:45:00' |

**Índices:**
- PRIMARY KEY: `id`
- UNIQUE: `(empresa_id, model_type, version)`
- INDEX: `(empresa_id, model_type, status)` ← Para queries rápidas

**Queries comunes:**
```sql
-- Obtener modelo activo de una empresa
SELECT * FROM ml_model 
WHERE empresa_id = 1 
  AND model_type = 'rfm_segmentation' 
  AND status = 'active';

-- Listar todos los modelos de una empresa
SELECT model_type, version, status, trained_at 
FROM ml_model 
WHERE empresa_id = 1 
ORDER BY trained_at DESC;

-- Modelos que necesitan reentrenamiento
SELECT * FROM ml_model 
WHERE status = 'active' 
  AND trained_at < NOW() - INTERVAL '30 days';
```

---

### 2. **TRAINING_JOB** - Historial de Entrenamientos

**Propósito:** Auditoría y seguimiento de trabajos de entrenamiento

**Campos clave:**

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `empresa_id` | FK | Empresa que solicitó | 1 |
| `model_type` | VARCHAR | Tipo de modelo | 'churn_prediction' |
| `status` | VARCHAR | Estado del trabajo | 'completed' |
| `result_model_id` | FK | Modelo resultante | 5 |
| `error_message` | TEXT | Error si falló | null |
| `started_at` | TIMESTAMP | Inicio | '2025-10-22 10:00:00' |
| `completed_at` | TIMESTAMP | Fin | '2025-10-22 10:05:30' |

**Utilidad:**
- Ver cuánto tarda cada entrenamiento
- Identificar problemas recurrentes
- Auditar quién entrenó qué y cuándo

**Queries comunes:**
```sql
-- Trabajos fallidos recientes
SELECT * FROM training_job 
WHERE status = 'failed' 
  AND created_at > NOW() - INTERVAL '7 days';

-- Tiempo promedio de entrenamiento
SELECT 
  model_type,
  AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_seconds
FROM training_job 
WHERE status = 'completed'
GROUP BY model_type;

-- Historial de entrenamientos de una empresa
SELECT 
  model_type, 
  status, 
  created_at,
  (completed_at - started_at) as duration
FROM training_job 
WHERE empresa_id = 1 
ORDER BY created_at DESC 
LIMIT 20;
```

---

### 3. **ML_PREDICTION** - Predicciones Realizadas

**Propósito:** Almacenar resultados de predicciones para auditoría y análisis

**Campos clave:**

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `model_id` | FK | Modelo usado | 5 |
| `input_data` | JSON | Datos de entrada | `{"clientes_count": 150}` |
| `prediction` | JSON | Resultado | `{"segments": {...}}` |
| `confidence` | FLOAT | Confianza | 0.95 |
| `execution_time_ms` | INT | Tiempo en milisegundos | 234 |
| `created_at` | TIMESTAMP | Cuándo se predijo | '2025-10-22 15:45:00' |

**Utilidad:**
- Análisis de performance
- Caché de resultados
- Auditoría de uso

**Queries comunes:**
```sql
-- Predicciones más lentas
SELECT * FROM ml_prediction 
ORDER BY execution_time_ms DESC 
LIMIT 10;

-- Uso diario de modelos
SELECT 
  DATE(created_at) as fecha,
  COUNT(*) as predicciones
FROM ml_prediction 
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY fecha DESC;

-- Última predicción de un modelo
SELECT * FROM ml_prediction 
WHERE model_id = 5 
ORDER BY created_at DESC 
LIMIT 1;
```

---

## 🎯 Estrategia de Almacenamiento

### Modelos (.pkl files)

**NO se guardan en la base de datos**. Se almacenan en filesystem:

```
/ml_models_cache/
  ├── empresa_1/
  │   ├── rfm_segmentation_v1.pkl       (500 KB)
  │   ├── churn_prediction_v1.pkl       (2 MB)
  │   └── product_recommendations_v1.pkl (1 MB)
  ├── empresa_2/
  │   ├── rfm_segmentation_v1.pkl
  │   └── churn_prediction_v1.pkl
  └── empresa_3/
      └── ...
```

**Razones:**
- ✅ Archivos .pkl pueden ser grandes (1-10 MB)
- ✅ Filesystem es más rápido para lectura/escritura
- ✅ Fácil backup con rsync/s3
- ✅ Base de datos solo guarda la ruta

---

## 📊 Tamaño Estimado de Datos

### Por Empresa:

| Tabla | Registros | Tamaño/Registro | Total |
|-------|-----------|-----------------|-------|
| **ml_model** | ~10 modelos | 2 KB | 20 KB |
| **training_job** | ~100 entrenamientos | 500 bytes | 50 KB |
| **ml_prediction** | ~10,000 predicciones/año | 1 KB | 10 MB |

**Total por empresa:** ~10-15 MB/año en BD

**Para 1,000 empresas:** ~10-15 GB en 1 año (muy manejable)

---

## 🔐 Seguridad y Aislamiento

### Row-Level Security

Cada query automáticamente filtra por `empresa_id`:

```python
# Django ORM asegura aislamiento
ml_models = MLModel.objects.filter(empresa=request.user.empresa)

# SQL generado automáticamente incluye:
# WHERE empresa_id = 123
```

### Índices para Performance

```sql
-- Índice compuesto para queries frecuentes
CREATE INDEX idx_ml_model_empresa_type_status 
ON ml_model(empresa_id, model_type, status);

-- Índice para predicciones recientes
CREATE INDEX idx_ml_prediction_model_date 
ON ml_prediction(model_id, created_at DESC);
```

---

## 🚀 Escalabilidad

### Estrategias si creces MUCHO:

#### 1. **Particionado de ML_PREDICTION**
```sql
-- Particionar por fecha (eliminar predicciones antiguas)
CREATE TABLE ml_prediction_2025_10 PARTITION OF ml_prediction
FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
```

#### 2. **Archivar modelos viejos**
```sql
-- Mover modelos outdated a tabla de archivo
INSERT INTO ml_model_archive 
SELECT * FROM ml_model 
WHERE status = 'outdated' 
  AND trained_at < NOW() - INTERVAL '6 months';
```

#### 3. **Caché con Redis**
```python
# Cachear predicciones frecuentes
@cache_result(key='rfm_{empresa_id}', ttl=3600)
def get_rfm_segments(empresa_id):
    return mlService.predictRFM()
```

---

## 📈 Monitoreo y Métricas

### Queries útiles para dashboards:

```sql
-- Total de modelos activos
SELECT 
  model_type,
  COUNT(*) as total_activos
FROM ml_model 
WHERE status = 'active'
GROUP BY model_type;

-- Empresas sin modelos entrenados
SELECT e.id, e.razon_social
FROM empresas e
LEFT JOIN ml_model m ON e.id = m.empresa_id
WHERE m.id IS NULL;

-- Uso diario de predicciones
SELECT 
  DATE(p.created_at) as fecha,
  m.model_type,
  COUNT(*) as predicciones,
  AVG(p.execution_time_ms) as avg_time_ms
FROM ml_prediction p
JOIN ml_model m ON p.model_id = m.id
WHERE p.created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(p.created_at), m.model_type
ORDER BY fecha DESC, predicciones DESC;
```

---

## ✅ Resumen

### Por qué esta estructura es correcta:

1. **✅ Aislamiento por empresa**
   - Cada empresa tiene sus propios modelos
   - Queries eficientes con índices

2. **✅ Versionado automático**
   - Múltiples versiones del mismo modelo
   - Rollback fácil

3. **✅ Auditoría completa**
   - Historial de entrenamientos
   - Todas las predicciones registradas

4. **✅ Flexible y extensible**
   - JSON para datos variables
   - Fácil agregar nuevos model_types

5. **✅ Performance**
   - Modelos en filesystem (rápido)
   - Solo metadata en BD (ligero)
   - Índices optimizados

6. **✅ Escalable**
   - Soporta miles de empresas
   - Estrategias de particionado si crece

---

## 🎯 Próximos Pasos

1. ✅ **Migraciones creadas** (`0001_initial.py`)
2. ⏳ **Solucionar permisos de PostgreSQL**
3. ⏳ **Ejecutar migraciones**
4. ⏳ **Probar con datos reales**

---

**¿Listo para ejecutar las migraciones? Solo necesitamos solucionar los permisos de PostgreSQL primero.**


