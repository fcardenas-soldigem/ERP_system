# Auditoría del módulo de Machine Learning — ERP Soldigem

**Fecha:** 2026-10-16 · **Alcance:** `backend/apps/ml_models/`, su registro en `config/`, `requirements_ml.txt`, `ml_models_cache/`, consumidores en `frontend/src`.
**Método:** solo lectura de código y `git log/blame`. No se ejecutó código, migraciones ni consultas a BD. Todas las rutas son relativas a `backend/` salvo que se indique lo contrario.

---

## 1. Resumen ejecutivo

1. El módulo ofrece tres modelos por empresa (segmentación RFM con K-Means, "churn" con Random Forest, recomendaciones con reglas de asociación/Apriori) y un cuarto (demanda con Prophet) que existe como código pero **no está conectado a ningún endpoint** (`apps/ml_models/views.py:226` solo itera 3 tipos; `services/training_service.py` no tiene `train_demand_*`).
2. **Está activo en producción.** `config/settings.py:115` registra `apps.ml_models` sin condición; `config/urls.py:41-45` monta `api/ml/` en `try/except`, pero el `except` nunca se dispara en prod porque `backend/requirements.txt:60-66` ya incluye scikit-learn, prophet, mlxtend y joblib, y `backend/Dockerfile:19-20` instala ese archivo. `requirements_ml.txt` es un duplicado que **el Dockerfile no usa**. El `try/except` solo protege al entorno local sin esas libs (`config/test_urls.py:3-5`).
3. El frontend lo expone a **todos los usuarios**: ruta `ml-dashboard` (`frontend/src/App.jsx:99,207`) y entrada de menú "Machine Learning" (`frontend/src/components/Layout/AnimatedSidebar.jsx:106`).
4. **Riesgo 1 — Funcionalmente roto:** 2 de los 3 endpoints de predicción fallan siempre con 500 por desajuste de claves entre lo que se guarda y lo que se lee del `.pkl` (`views.py:273-276` vs `customer_analytics/rfm_segmentation.py:155-159`; `views.py:328` vs `customer_analytics/churn_prediction.py:160-164`).
5. **Riesgo 2 — Persistencia efímera:** los modelos se guardan en disco local del contenedor (`training_service.py:30`), Cloud Run los pierde en cada redeploy/escala a cero (`DEPLOY.md:142`: `--min-instances 0 --max-instances 3`), mientras la fila `MLModel` sigue `active` en BD → la UI dice "Activo" pero `joblib.load` lanza `FileNotFoundError`.
6. **Riesgo 3 — Entrenamiento síncrono sin control de acceso ni rate-limit:** cualquier usuario autenticado de cualquier rol puede disparar `train/all` (`views.py:18` solo `IsAuthenticated`), que corre dentro del request con N+1 queries por cliente (`services/data_extractor.py:54-77`) en una instancia de 1 vCPU/1 GiB con timeout de 120 s (`Dockerfile:105`, `DEPLOY.md:142`).
7. **Aislamiento multitenant en el flujo conectado: correcto.** Todas las consultas de `DataExtractor` y `TrainingService` filtran por `empresa`. El riesgo de mezcla vive en código **muerto pero presente** (`utils/data_preparation.py`, funciones a nivel de módulo en los 4 archivos de modelo) que consulta sin `empresa` y escribe `.pkl` en una ruta compartida.
8. El fallback `empresa_id` del cliente en `views.py:29-33` es inalcanzable con el `CustomUser` actual (siempre tiene atributo `empresa`, `apps/authentication/models.py:14`), pero es una bomba latente.
9. El "churn" no predice nada: la etiqueta es `recency > 90` (`churn_prediction.py:20,62`) y `recency` es a su vez la primera feature (`churn_prediction.py:38`) → modelo tautológico.
10. **Recomendación:** retirar del despliegue (ocultar menú + no montar `api/ml/` detrás de un flag) hasta corregir claves de carga, persistencia y permisos. Detalle en §7.

---

## 2. Inventario de modelos predictivos

| # | Modelo | Qué predice | Algoritmo / librería | Features | Tablas y columnas de origen | Periodicidad |
|---|--------|-------------|----------------------|----------|-----------------------------|--------------|
| 1 | Segmentación RFM | Agrupa clientes en 5 segmentos (Champions, Loyal, Potential, At Risk, Hibernating) | `sklearn.cluster.KMeans(n_clusters=5, random_state=42, n_init=10)` + `StandardScaler` (`rfm_segmentation.py:7-8,86`). Scores R/F/M con `pd.qcut` q=5 (`:43-49`) | `recency`, `frequency`, `monetary` (`:80`) | Ver bloque A | Bajo demanda (endpoint). Sugerencia de reentrenar a 30 días en `training_service.py:386-406` |
| 2 | Churn | Probabilidad de abandono por cliente; riesgo Alto/Medio/Bajo (`churn_prediction.py:121-130`) | `RandomForestClassifier(n_estimators=100, max_depth=10, class_weight='balanced')` (`:90-96`) | 10 features derivadas de RFM (`:77-81`): recency, frequency, monetary, avg_ticket, customer_age_days, purchase_rate, recency_ratio, is_inactive(>60d), low_frequency(<3), declining_engagement | Ver bloque A (mismo `extract_rfm_data`) | Bajo demanda |
| 3 | Recomendaciones | Productos que se compran juntos (reglas A→B con confidence/lift/support) | `mlxtend.frequent_patterns.apriori` + `association_rules` (`association_rules.py:7,45,51`); `min_support=0.01, min_confidence=0.2, min_lift=1.0` (`training_service.py:216-221`) | Matriz canasta transacción×producto binaria (`association_rules.py:41-42`) | Ver bloque B | Bajo demanda |
| 4 | Predicción de demanda | Demanda diaria futura por producto + punto de reorden | `prophet.Prophet(daily/weekly seasonality, changepoint_prior_scale=0.05)` (`demand_forecasting/demand_predictor.py:7,38-44`) | Serie `ds`/`y` por producto | **No conectado.** Usa `utils/data_preparation.py:81-132`, que importa `apps.ventas.models.VentaDetalle` (no existe; el modelo real es `DetalleVenta`, `apps/ventas/models.py:786`) y filtra por `venta__fecha` (no existe; es `fecha_emision`, `apps/ventas/models.py:145`). `DataExtractor.extract_demand_data` (`data_extractor.py:166-208`) sí es correcto pero nadie lo llama. | N/A |

**Bloque A — origen de datos RFM/Churn** (`services/data_extractor.py:26-97`):
- `Venta`: `empresa` (`:36,58`), `estado='pagado'` (`:37,59`; valor válido según `apps/ventas/models.py:85`), `fecha_emision` (Max/Min, `:66-67`), `total` (Sum, `:77`), `cliente` (`:57`).
- `Cliente`: `empresa`, `activo=True` (`:49-52`), `id`, `nombre`, `documento` (`:82-84`).
- Derivadas: `recency = hoy - última venta`, `frequency = nº ventas pagadas`, `monetary = Σ total`, `avg_ticket`, `customer_age_days` (`:75-79`).
- Nota: solo ventas `pagado`; clientes sin ventas pagadas se omiten (`:62-63`).

**Bloque B — origen de datos Recomendaciones** (`data_extractor.py:136-164`):
- `Venta`: `empresa`, `estado='pagado'` (`:143-146`), `id` como `transaction_id` (`:156`).
- `DetalleVenta` (vía `venta.detalles`): `producto.id`, `producto.nombre`, `cantidad` (`:157-159`).
- **Bug:** `DetalleVenta.producto` es nullable desde D1 (`apps/ventas/models.py:797-800`); `detalle.producto.id` lanza `AttributeError` si la empresa tiene líneas de texto libre (también en `:123-124` y `:196`). Entrenar recomendaciones en esas empresas devuelve 500.

**Funciones legado a nivel de módulo (no conectadas a `views.py`, verificado con grep sin otros llamadores):** `segment_customers` (`rfm_segmentation.py:172`), `predict_churn` (`churn_prediction.py:177`), `train_recommendation_model` / `get_product_recommendations` (`association_rules.py:222,275`), `forecast_product_demand` / `batch_forecast_top_products` (`demand_predictor.py:208,289`). Todas aceptan `empresa_id=None` por defecto y dependen de `utils/data_preparation.py`, que importa `apps.core.models.Cliente` (`:18,174`; en `apps/core/models.py` solo existe `Empresa`) y `VentaDetalle` (`:66,93`). **Ese archivo no puede ejecutarse hoy (ImportError)**, lo que de facto neutraliza esas funciones, pero son deuda y riesgo si alguien las "arregla" sin añadir el filtro de empresa (ver §4).

**Documentación desactualizada:** `apps/ml_models/README.md:59-152` documenta endpoints `/api/ml/customers/segment/`, `/api/ml/demand/forecast/`, `/api/ml/health/`, etc. que **no existen**; las rutas reales son las de `urls.py:6` + `@action` de `views.py` (`/api/ml/models/train/...`, `/predict/...`, `/list/`, `/status/`, `/training-history/`). `ACCEDER_ML_DASHBOARD.md:109-112` habla de mínimos de 20 clientes/50 ventas/30 días; el código exige 2/2/1 (§5).

---

## 3. Dónde se guarda el modelo entrenado

**Ruta exacta (flujo conectado):**
`<BASE_DIR>/ml_models_cache/empresa_<id>/<model_type>_v<N>.pkl`
- Directorio: `training_service.py:30-31` (`Path(settings.BASE_DIR) / 'ml_models_cache' / f'empresa_{empresa.id}'`, `mkdir(parents=True, exist_ok=True)`).
- Nombres: `rfm_segmentation_v{N}.pkl` (`:61`), `churn_prediction_v{N}.pkl` (`:134`), `product_recommendations_v{N}.pkl` (`:212`).
- `BASE_DIR = backend/` (`config/settings.py:12`) → en el contenedor es `/app/ml_models_cache/...` (`Dockerfile:35,54`). El directorio es escribible porque `chown -R appuser /app` (`Dockerfile:79-80`).

**Formato:** `joblib.dump(dict)` (`rfm_segmentation.py:155-159`, `churn_prediction.py:160-164`, `association_rules.py:201-207`); lectura con `joblib.load(ml_model.model_file_path)` (`training_service.py:345`). Es pickle de Python: deserializar un archivo manipulado ejecuta código arbitrario. Hoy la ruta viene de la BD y no de input del usuario (riesgo bajo, ver §6).

**Registro en BD** (`apps/ml_models/models.py`): `MLModel` con `empresa` FK (`:24-29`), `model_type` (`:30-34`), `version` (`:35-38`), `status` (`:39-43`), `model_file_path` **absoluto** (`:50-53`), `training_data_info`/`hyperparameters` JSON (`:56-65`), `trained_at`/`last_used_at` (`:69-70`), `unique_together (empresa, model_type, version)` (`:76`). `MLPrediction` (`:116-146`) guarda un resumen por llamada a predict (no la predicción por cliente). `TrainingJob` (`:149-196`) registra cada entrenamiento con `started_at/completed_at/error_message`. Migraciones: `0001_initial`, `0002_...` (2025-10-22).

**¿Sobrevive a un redeploy en Cloud Run? No.**
- El archivo vive en el filesystem del contenedor; `settings.py:286-304` configura GCS (`STORAGES`) **solo para media**, no para `ml_models_cache`. No hay código que suba el `.pkl` a GCS.
- `DEPLOY.md:142`: `--min-instances 0 --max-instances 3`. Con escala a cero el disco desaparece; con 2-3 instancias, un entrenamiento en la instancia A no es visible desde la B.
- `.gcloudignore:19-20` excluye `backend/ml_models_cache/` del build → la imagen arranca siempre sin modelos. (`.dockerignore` no lo excluye: un `docker build` local sí copiaría los `.pkl` locales a la imagen.)
- Tras el redeploy la fila `MLModel` sigue `status='active'` → `check_status` responde `has_model: true` (`views.py:230-240`), la UI muestra "Activo" (`MLDashboard.jsx:111-115`), y cualquier `predict/*` falla en `joblib.load` con `FileNotFoundError` → `error_interno` 500 (`views.py:302-303`). No existe comprobación `os.path.exists` en `load_model` (`training_service.py:339-350`).
- **Ruta absoluta en BD:** si una misma BD se usa desde local (`/Users/.../backend/ml_models_cache/...`) y desde prod (`/app/...`), las filas apuntan a rutas inválidas en el otro entorno. No se puede determinar leyendo código si eso ha ocurrido.

**Contenido actual de `backend/ml_models_cache/` (solo listado, no abiertos):**
```
churn_prediction_model.pkl          (101 KB, 2025-10-15)   ← legado, ningún código actual escribe este nombre
product_recommendations_model.pkl   (7 KB,   2025-10-15)   ← legado
rfm_segmentation_model.pkl          (6 KB,   2025-10-15)   ← legado
empresa_1/churn_prediction_v1.pkl, _v2.pkl                 (57 KB c/u, 2025-11-05)
empresa_1/product_recommendations_v1.pkl … _v6.pkl         (4 KB c/u, 2025-11-05)
empresa_1/rfm_segmentation_v1.pkl, _v2.pkl                 (1.2 KB c/u, 2025-11-05)
```
Los tres archivos de la raíz no coinciden con ningún nombre que el código actual genere (los defaults actuales son `rfm_model.pkl`, `churn_model.pkl`, `product_recommendations.pkl`, `demand_forecast_{id}.pkl`: `rfm_segmentation.py:34`, `churn_prediction.py:29`, `association_rules.py:28`, `demand_predictor.py:22`); son restos de una versión anterior. Las 6 versiones de recomendaciones indican entrenamientos repetidos sin limpieza: cada `train` crea un archivo nuevo y nunca borra los anteriores. `ml_models_cache/` está en `.gitignore:56`.

---

## 4. Por empresa o global — análisis de aislamiento multitenant

### 4.1 Endpoints (`apps/ml_models/views.py`)

| Aspecto | Evidencia | Evaluación |
|---|---|---|
| Permisos | `permission_classes = [IsAuthenticated]` (`:18`). No usa `HasEmpresaPermission` (convención del repo, `CLAUDE.md`; definida en `apps/core/permissions.py:8-15`). `ModulePermission` reserva `ml_models` solo al rol `admin` (`permissions.py` ROLE_PERMISSIONS['admin']) pero **no se aplica** a este ViewSet (solo se usa en `apps/core/views.py:58`). | Cualquier rol (comercial, almacén, readonly…) puede entrenar y predecir. |
| Resolución de empresa | `_get_empresa` (`:20-33`): 1) `request.user.usuario.empresa` — `CustomUser` no tiene atributo `usuario`, nunca entra; 2) `request.user.empresa` — `CustomUser.empresa` FK existe (`apps/authentication/models.py:14-19`), **siempre entra aquí**; 3) fallback `empresa_id` desde `request.data`/`query_params` (`:30-32`) — inalcanzable hoy. | El tenant se toma del usuario autenticado. Correcto en la práctica. |
| `empresa_id` del cliente | `:29-33` acepta `empresa_id` arbitrario con `get_object_or_404(Empresa, id=...)` sin verificar pertenencia. | **Latente.** Si `user.empresa` fuera `None` (superusuario: la señal `create_user_empresa` no le crea empresa, `authentication/models.py:65`) la rama 2 devuelve `None` → `TrainingService(None)` → `AttributeError` en `empresa.id` (`training_service.py:30`) → 500. No llega a la rama 3. Debe eliminarse igualmente. |
| `producto_id` del cliente | `:371,383` se usa solo para filtrar reglas del modelo propio en memoria; no consulta BD. | Sin fuga. Un ID de otra empresa simplemente no aparece en las reglas. |
| Listado/estado/historial | `MLModel.objects.filter(empresa=empresa)` (`:188`); `TrainingJob.objects.filter(empresa=self.empresa)` (`training_service.py:379`); `MLModel.get_active_model(empresa, type)` (`models.py:107-111`). | Filtrado correcto. |
| `MLPrediction` | Se crea con `model=ml_model` (`:285-290, 336-341, 388-393`); sin columna `empresa` propia, hereda vía FK. | Aceptable; ningún endpoint la lista. |

### 4.2 Consultas de datos en el flujo conectado (`services/data_extractor.py`)

Todas filtran por `empresa`: `Venta` (`:35-38`, `:56-60`, `:106-109`, `:143-146`, `:218-220`, `:233-236`), `Cliente` (`:49-52`, `:222-225`), `Producto` (`:227-230`), `DetalleVenta` por `venta__empresa` (`:179-183`). **No se encontró ninguna consulta sin `empresa` en este archivo.** `TrainingService` también filtra `MLModel`/`TrainingJob` por empresa (`training_service.py:44-49, 72-73, 117-122, 149-150, 195-200, 228-229, 362-365, 379`) y `mark_as_active` desactiva solo versiones de la misma empresa (`models.py:87-91`).

### 4.3 Consultas SIN filtro de empresa (código presente pero no conectado)

| Archivo:línea | Consulta | Condición de fuga |
|---|---|---|
| `utils/data_preparation.py:21-23` | `Venta.objects.all()`; filtra solo `if empresa_id` | Con `empresa_id=None` (default de todas las funciones legado) mezcla **todas** las empresas en el RFM. |
| `utils/data_preparation.py:69-71` | `VentaDetalle.objects.select_related(...)`; filtra solo `if empresa_id` | Ídem para recomendaciones. |
| `utils/data_preparation.py:100-106` | `VentaDetalle.objects.filter(producto_id=..., venta__fecha__gte=...)`; `empresa` opcional | Demanda por producto cruza empresas si `empresa_id=None`. |
| `utils/data_preparation.py:160` | `Producto.objects.get(id=producto_id)` | Devuelve nombre/código/precio de un producto de **cualquier** empresa. |
| `utils/data_preparation.py:177` | `Cliente.objects.get(id=cliente_id)` | Devuelve nombre/documento de un cliente de **cualquier** empresa. |
| `demand_forecasting/demand_predictor.py:305-311` | `VentaDetalle.objects.values('producto_id').annotate(...)`; filtra solo `if empresa_id` | Top productos global. |
| `rfm_segmentation.py:34`, `churn_prediction.py:29`, `association_rules.py:28`, `demand_predictor.py:22` | Ruta de `.pkl` **compartida** `ml_models_cache/<nombre>.pkl` cuando no se pasa `model_path` | Las funciones legado escriben/leen un único modelo para todas las empresas; `get_product_recommendations` (`association_rules.py:291-302`) carga ese archivo global y, si no existe, entrena con `empresa_id` opcional. |

Hoy este código **no se ejecuta**: `data_preparation.py` importa símbolos inexistentes (`apps.core.models.Cliente` en `:18,174`; `apps.ventas.models.VentaDetalle` en `:66,93`) y lanzaría `ImportError` en la primera llamada. Sigue siendo riesgo porque: (a) está en `INSTALLED_APPS` y es importable; (b) el README (`:33-49`) lo documenta como la forma de uso; (c) basta "corregir" los imports para reactivar consultas globales.

### 4.4 Puntos donde datos de varias empresas podrían entrar al mismo entrenamiento/predicción

- **Flujo conectado (`views.py` → `TrainingService` → `DataExtractor`):** ninguno encontrado. Directorio y filas por empresa; consultas filtradas.
- **Flujo legado:** todos los listados en 4.3.
- **Riesgo operativo (no de código):** una BD compartida entre local y prod con `model_file_path` absoluto (`models.py:50-53`) puede hacer que una instancia cargue un `.pkl` de otro entorno si la ruta existe — improbable, pero el diseño lo permite.

---

## 5. Reentrenamiento

**Cómo y cuándo.** Solo manual, vía HTTP: `POST /api/ml/models/train/rfm/` (`views.py:35`), `train/churn/` (`:76`), `train/recommendations/` (`:106`), `train/all/` (`:146`). No existe comando `manage.py`, tarea Celery, cron ni Cloud Scheduler (grep en `backend/apps`, `backend/config`, `cloudbuild.yaml`, `requirements.txt`: sin resultados; `redis` está en requirements pero no hay worker). `TrainingJob.status` admite `pending` (`models.py:154`) pero el código crea siempre `running` y termina en el mismo request (`training_service.py:44-49, 95-98`).

**Síncrono dentro del request.** `train_all_models` (`training_service.py:264-315`) encadena los 3 entrenamientos en el hilo HTTP. El frontend lo trata como asíncrono: muestra "Entrenamiento iniciado… puede tardar varios minutos" y recarga a los 5 s (`MLDashboard.jsx:79-90`), pero el `await` bloquea hasta que termina o expira. Límites: gunicorn `--timeout 120` (`Dockerfile:105`) y Cloud Run `--timeout 120` (`DEPLOY.md:142`). Un timeout deja el `TrainingJob` en `running` para siempre (el `except` de `:102-108` no se ejecuta si gunicorn mata el worker).

**Quién puede dispararlo.** Cualquier usuario autenticado con empresa (`views.py:18`). Sin verificación de rol, sin throttle (`REST_FRAMEWORK.DEFAULT_THROTTLE_RATES` solo define `leads` y `mcp`, `settings.py:329-332`). Cada llamada crea una nueva versión y un `.pkl` adicional sin borrar los anteriores (`training_service.py:61-62, 352-367`); localmente ya hay v1…v6 de recomendaciones.

**Costo/tiempo (estimación por lectura, no medido).**
- `extract_rfm_data` hace 5 queries por cliente activo: `exists`, `Max`, `Min`, `count`, `Sum` (`data_extractor.py:62-77`) → con 2 000 clientes ≈ 10 000 queries por entrenamiento; se ejecuta dos veces en `train/all` (RFM y churn, `training_service.py:58,131`) y otra vez en cada `predict/rfm` y `predict/churn` (`views.py:268,322`).
- `extract_product_transactions` itera `venta.detalles.all()` en Python (`:153-160`); Apriori construye una matriz densa transacciones×productos (`association_rules.py:41-42`, `applymap` deprecado en pandas 2.1). Con catálogos grandes y `min_support=0.01` el consumo de RAM puede superar 1 GiB.
- RandomForest de 100 árboles y K-Means sobre cientos/miles de filas: segundos.
- Prophet no se usa en el flujo conectado, pero está instalado en la imagen (`requirements.txt:61`) con su stack cmdstan.

**Datos escasos.** Los umbrales se bajaron "para desarrollo/pruebas" y así quedaron en prod (`data_extractor.py:263-283`: RFM/churn 2 clientes, 2 ventas, 1 día; recomendaciones 5 ventas, 3 productos; comentarios "Reducido de 20 a 2", etc.). Consecuencias:
- `pd.qcut(q=5, labels=[...], duplicates='drop')` (`rfm_segmentation.py:43-49`) lanza `ValueError("Bin labels must be one fewer than the number of bin edges")` cuando hay valores repetidos (frecuente con <10 clientes). Se devuelve como 400 con el mensaje técnico (`views.py:68-72`).
- Churn con una sola clase (p. ej. todos los clientes con `recency ≤ 90`): `predict_proba(...)[:, 1]` (`churn_prediction.py:115`) → `IndexError` → 500. El modelo en sí es tautológico: etiqueta `recency > 90` (`:62`) y feature `days_since_last_purchase = recency` (`:38`).
- `validate_data_for_training` cuenta **todas** las ventas (`data_extractor.py:217-220`) pero la extracción usa solo `pagado` → pasa la validación y luego falla con "No hay ventas" (`:41,149`).
- `check_if_retraining_needed` compara `ventas_count` (ventas totales) contra `training_samples` (nº de clientes para RFM/churn, nº de filas detalle para recomendaciones) (`training_service.py:409-414`) → la señal "requiere reentrenamiento" es incoherente.
- `n_clusters` se reduce a `len(df)-1` si hay menos clientes que clusters (`rfm_segmentation.py:73-74`).

---

## 6. Riesgos clasificados

### ALTO

| Riesgo | Evidencia | Recomendación |
|---|---|---|
| **A1. `predict/rfm` siempre 500 (KeyError).** La vista lee `model_data['kmeans']`, `['segment_mapping']`, `['features']` pero el archivo se guarda con `model`, `scaler`, `n_clusters`. Además asigna `model.kmeans` mientras `predict()` usa `self.model` → "Modelo no entrenado". | `views.py:273-276` vs `rfm_segmentation.py:155-159`; `rfm_segmentation.py:100-101,111` | Unificar contrato: que la vista use `RFMSegmentation.load_model()` o alinear claves. Añadir test de ida y vuelta save→load→predict. |
| **A2. `predict/churn` siempre 500 (KeyError).** La vista lee `model_data['features']`; el archivo guarda `feature_names`; la clase usa `self.feature_names` (queda `[]` → `X` vacío). | `views.py:327-328` vs `churn_prediction.py:160-164,111` | Igual que A1. La pestaña "Churn" del dashboard (`ChurnPrediction.jsx:44`) es inoperante. |
| **A3. Modelos no sobreviven a redeploy/escala en Cloud Run; BD queda inconsistente.** Archivo en disco efímero; sin GCS; `min-instances 0`, `max-instances 3`; `MLModel.status='active'` persiste; `load_model` sin `exists()`. UI muestra "Activo" y predict da 500. | `training_service.py:30,345`; `settings.py:286-304` (GCS solo media); `DEPLOY.md:142`; `.gcloudignore:19-20`; `views.py:230-240` | Guardar el `.pkl` en GCS (o en un `BinaryField`/bucket y cargar bajo demanda) y verificar existencia antes de reportar `has_model`. Mientras tanto, retirar el módulo del despliegue. |
| **A4. Entrenamiento síncrono disparable por cualquier rol, sin throttle.** CPU/RAM de la única vCPU, N+1 por cliente, timeout 120 s, `TrainingJob` queda en `running`. | `views.py:18,146-177`; `data_extractor.py:54-77`; `Dockerfile:103-105`; `DEPLOY.md:142`; `settings.py:329-332` | Restringir a `admin` (aplicar `ModulePermission` o `HasEmpresaPermission` + rol), añadir throttle, mover a Cloud Run Job/tarea en segundo plano (`TrainingJob.pending`). |
| **A5. Línea de detalle sin producto rompe recomendaciones/demanda.** `DetalleVenta.producto` es nullable (D1); `detalle.producto.id` → `AttributeError` → 500 en `train/recommendations` para empresas con líneas de texto libre. | `apps/ventas/models.py:797-800`; `data_extractor.py:123-124,157,196` | `detalles.filter(producto__isnull=False)` o `select_related('producto')` + `continue` si `producto_id is None`. |

### MEDIO

| Riesgo | Evidencia | Recomendación |
|---|---|---|
| **M1. Código legado con consultas globales (sin `empresa`) y `.pkl` compartido.** Hoy inerte por `ImportError`, pero importable y documentado en README. | `utils/data_preparation.py:21-23,69-71,100-106,160,177`; `demand_predictor.py:305-311`; rutas compartidas `rfm_segmentation.py:34`, `churn_prediction.py:29`, `association_rules.py:28`, `demand_predictor.py:22`; README `:33-49` | Eliminar `utils/data_preparation.py` y las funciones a nivel de módulo (`segment_customers`, `predict_churn`, `train_recommendation_model`, `get_product_recommendations`, `forecast_product_demand`, `batch_forecast_top_products`), o hacer `empresa` obligatoria. |
| **M2. Fallback `empresa_id` del cliente en `_get_empresa`.** Inalcanzable hoy con `CustomUser`, pero acepta un tenant arbitrario sin verificar pertenencia. Superusuario sin empresa → 500 en vez de 403. | `views.py:29-33`; `authentication/models.py:14-19,65` | Sustituir por `HasEmpresaPermission` y `request.user.empresa` directo; eliminar la rama de fallback. |
| **M3. Sin control de acceso por rol en el frontend ni backend.** Menú visible a todos; `ModulePermission` mapea `ml_models` a `admin` pero no se aplica. | `AnimatedSidebar.jsx:106`; `App.jsx:207`; `permissions.py` (ROLE_PERMISSIONS admin → `ml_models`) vs `views.py:18` | Aplicar `ModulePermission` al ViewSet y ocultar el menú según rol. |
| **M4. Dependencias pesadas en la imagen de prod sin uso real.** prophet (+cmdstanpy), matplotlib, seaborn, tqdm en `requirements.txt`; `requirements_ml.txt` duplicado e ignorado por el Dockerfile; comentario "opcional" engañoso. | `requirements.txt:58-66`; `requirements_ml.txt:1-29`; `Dockerfile:19-20` | Sacar el bloque ML de `requirements.txt` (dejarlo solo en `requirements_ml.txt`) para que el `try/except` de `urls.py:41-45` realmente desactive el módulo; o instalar `requirements_ml.txt` explícitamente solo en la imagen que lo necesite. |
| **M5. Modelo de churn sin valor predictivo (fuga de etiqueta).** Target `recency > 90` y feature `recency`. | `churn_prediction.py:20,38,62` | Definir el target con una ventana temporal distinta a la de las features (p. ej. features a fecha t, etiqueta "no compró entre t y t+90"). |
| **M6. Umbrales de datos "de desarrollo" en prod + fallos con datos escasos.** `qcut` y `predict_proba[:,1]` fallan; validación cuenta ventas no pagadas. | `data_extractor.py:263-283,217-220`; `rfm_segmentation.py:43-49`; `churn_prediction.py:115` | Restaurar mínimos razonables (≥20 clientes, ≥50 ventas pagadas, ≥30 días) y validar con el mismo filtro `pagado`. |
| **M7. Inconsistencia de nombres de segmento.** `fit` nombra clusters por heurística (`:116-134`); `predict` usa el dict fijo `SEGMENT_NAMES` por índice de cluster (`:112`). Si A1 se corrige, los nombres que vería el usuario no coincidirían con los del entrenamiento. | `rfm_segmentation.py:19-25,90-92,112` | Persistir el mapeo cluster→nombre en el `.pkl` y usarlo en `predict`. |
| **M8. Señal de reentrenamiento incoherente y archivos acumulándose.** Compara ventas totales vs nº de clientes; cada train deja un `.pkl` más. | `training_service.py:409-414,61-62`; `ml_models_cache/empresa_1/` (v1…v6) | Guardar `ventas_count` en `training_data_info` y comparar contra eso; borrar/archivar versiones `outdated`. |

### BAJO

| Riesgo | Evidencia | Recomendación |
|---|---|---|
| **B1. Pickle/joblib.** Deserialización arbitraria, pero la ruta proviene de la BD (sin input del usuario) y el directorio lo escribe el propio proceso. | `training_service.py:345`; `models.py:50-53` | Mantener así; si se migra a GCS, validar que la ruta esté dentro del prefijo de la empresa. |
| **B2. Documentación obsoleta.** README describe endpoints inexistentes y mínimos distintos; `ACCEDER_ML_DASHBOARD.md` cita puerto 3000 y MUI. | `apps/ml_models/README.md:59-152,299-304`; `ACCEDER_ML_DASHBOARD.md:13,21,109-112` | Reescribir o borrar. |
| **B3. `.dockerignore` no excluye `ml_models_cache/`.** Un build local metería `.pkl` de desarrollo en la imagen (en Cloud Build lo evita `.gcloudignore`). | `.dockerignore` (sin entrada); `.gcloudignore:19-20` | Añadir `backend/ml_models_cache/` a `.dockerignore`. |
| **B4. `_get_next_version` se llama dos veces y hay `unique_together`.** Dos entrenamientos concurrentes de la misma empresa pueden colisionar con `IntegrityError` → 500. | `training_service.py:61,75,352-367`; `models.py:76` | Calcular la versión una vez y envolver en `transaction.atomic()` con `select_for_update`, o usar un lock por empresa. |
| **B5. `applymap` deprecado (pandas 2.1).** Solo warning hoy; romperá al subir pandas. | `association_rules.py:42`; `requirements.txt:27` | Reemplazar por `(basket > 0).astype(int)`. |
| **B6. Mensajes de `ValueError` técnicos al cliente.** `str(e)` de pandas/sklearn llega al usuario como 400. | `views.py:68-72,101-102,141-142,300-301,352-353` | Mapear a mensajes de negocio; los inesperados ya van por `error_interno` (correcto desde commit `1647cd6`). |

---

## 7. Recomendación final

**Retirar del despliegue hasta corregir.** Argumentos: 2 de 3 predicciones fallan de forma determinista (A1, A2); la tercera deja de funcionar tras cada redeploy (A3) y falla en empresas con líneas libres (A5); el botón "Entrenar Modelos" es accesible a cualquier rol y consume la única vCPU de forma síncrona (A4). En su estado actual el módulo solo genera errores 500 y confusión en la UI, y mantiene ~300 MB de dependencias en la imagen.

**Pasos mínimos para retirarlo sin romper nada:**
1. Ocultar la entrada "Machine Learning" del menú (`AnimatedSidebar.jsx:106`) y la ruta `ml-dashboard` (`App.jsx:99,207`).
2. Mover el bloque ML de `backend/requirements.txt:60-66` a `requirements_ml.txt` (que ya lo contiene) para que `config/urls.py:41-45` deje de montar `api/ml/` en prod; o condicionar el `include` a un flag `ML_ENABLED` de entorno. Mantener `apps.ml_models` en `INSTALLED_APPS` para no tocar migraciones (los modelos de BD no importan sklearn).
3. Opcional: borrar `utils/data_preparation.py` y las funciones legado (M1) en el mismo PR.

**Si se decide mantener/aislar, en este orden:** A1+A2 (contrato save/load con test), A3 (GCS + `exists()`), A4+M2+M3 (permisos `admin` + throttle + job asíncrono), A5, M6, M5, M7, M8.

**Qué probar a mano (en local, con el stack ML instalado y una empresa de prueba):**
1. `POST /api/ml/models/train/all/` con un usuario de rol `comercial` → hoy responde 200/201; debería ser 403.
2. `POST /api/ml/models/predict/rfm/` y `predict/churn/` tras un `train/all` exitoso → esperar 500 (KeyError en logs) confirmando A1/A2.
3. Crear una venta pagada con una línea de texto libre (`producto=None`) y ejecutar `train/recommendations/` → esperar 500 (`AttributeError: 'NoneType' object has no attribute 'id'`) confirmando A5.
4. Entrenar, borrar `backend/ml_models_cache/empresa_<id>/`, llamar `GET /status/` (dirá `has_model: true`) y luego `predict/recommendations/` → `FileNotFoundError` 500, confirmando A3 (simula redeploy).
5. Con 2-3 clientes y 2 ventas pagadas, `train/rfm/` → esperar 400 con mensaje de `pd.qcut` (M6).
6. En un usuario superusuario sin empresa, `GET /api/ml/models/status/` → 500 en vez de 403 (M2).
7. Medir duración y nº de queries de `train/all` con `django-debug-toolbar` o `connection.queries` para una empresa con >500 clientes (A4).
8. `POST /predict/recommendations/` con `producto_id` de otra empresa → debe devolver lista vacía (verifica que no hay fuga por ID).

**No determinable solo con código:** si la BD de prod contiene filas `MLModel` con `model_file_path` de rutas locales (`/Users/...`); la memoria/tiempo real de Apriori con el catálogo actual; si algún usuario de prod ha ejecutado `train/all` (consultar `ml_models_trainingjob`).
