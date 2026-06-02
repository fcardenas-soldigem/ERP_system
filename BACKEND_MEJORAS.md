# Backend Mejoras — ERP System

> Fecha: 2026-05-29 · Rama: commit · Archivos modificados: 30+

---

## Resumen Ejecutivo

El backend del ERP se encontraba con cinco bugs críticos activos en producción, una configuración de base de datos que abría una conexión TCP nueva por cada request, y **309 sentencias `print()` de debug** emitiendo información interna en los logs de Cloud Run sin ningún formato ni control de nivel.

**Qué se corrigió:**
| # | Problema | Severidad | Estado |
|---|---|---|---|
| 1 | Ventas pagadas podían eliminarse (typo en estado) | Crítico | Corregido |
| 2 | `FacturaViewSet` exponía facturas de todos los tenants | Crítico | Corregido |
| 3 | Race condition en generación de números de Venta/Compra | Crítico | Corregido |
| 4 | N+1 queries en listado y exportación de ventas | Grave | Corregido |
| 5 | `CONN_MAX_AGE: 0` — nueva conexión a BD por request | Grave | Corregido |
| 6 | 309 `print()` de debug en producción | Moderado | Corregido |

**Impacto esperado:**
- Las ventas cobradas ya no pueden eliminarse accidentalmente.
- Los datos de cada empresa solo son accesibles por sus propios usuarios (multi-tenancy restaurado en facturas).
- Bajo carga concurrente, los números de venta/compra ya no colisionan.
- El listado de ventas pasó de ~21 queries por página a 3 queries fijas (independiente del tamaño de página).
- Cada request ahorra ~50ms al reutilizar conexiones a la base de datos remota (Supabase).
- Los logs de Cloud Run ahora tienen formato estructurado con nivel, timestamp, módulo y mensaje.

---

## Bugs Críticos Corregidos

### Bug 1 — Ventas pagadas se podían eliminar

**Archivo:** `backend/apps/ventas/views.py`, línea 910

**Problema:** La comparación usaba el string `'pagada'` (forma femenina) pero el modelo define el estado como `'pagado'` (forma masculina). La condición nunca era `True`, por lo que cualquier usuario podía borrar una venta ya cobrada.

```python
# ANTES — ventas/views.py:921
@transaction.atomic
def destroy(self, request, *args, **kwargs):
    venta = self.get_object()
    if venta.estado == 'pagada':          # ← nunca True; 'pagada' != 'pagado'
        return Response(
            {'error': 'No se puede eliminar una venta pagada'},
            status=status.HTTP_400_BAD_REQUEST
        )
    venta.detalles.all().delete()
    venta.delete()
    return Response({'mensaje': 'Venta eliminada correctamente'}, ...)
```

```python
# DESPUÉS — ventas/views.py:910
@transaction.atomic
def destroy(self, request, *args, **kwargs):
    venta = self.get_object()
    if venta.estado == 'pagado':          # ← coincide con ESTADO_CHOICES del modelo
        return Response(
            {'error': 'No se puede eliminar una venta pagada'},
            status=status.HTTP_400_BAD_REQUEST
        )
    venta.detalles.all().delete()
    venta.delete()
    return Response({'mensaje': 'Venta eliminada correctamente'}, ...)
```

**Por qué importa:** Una venta con estado `'pagado'` es un registro contable. Borrarlo elimina el movimiento de stock asociado y rompe la trazabilidad financiera. Este bug pasó desapercibido porque el camino feliz (crear, pagar, ver) funciona sin tocar `destroy`.

---

### Bug 2 — FacturaViewSet sin filtro de empresa

**Archivo:** `backend/apps/ventas/views.py`, clase `FacturaViewSet`

**Problema:** El queryset usaba `Factura.objects.all()` sin filtrar por empresa. Cualquier usuario autenticado podía listar (o modificar con DELETE/PATCH) las facturas de otras empresas mediante `GET /api/ventas/facturas/`.

```python
# ANTES — ventas/views.py
class FacturaViewSet(viewsets.ModelViewSet):
    queryset = Factura.objects.all()          # ← todas las facturas de todos los tenants
    serializer_class = FacturaSerializer
    # Sin permission_classes — usa el default global IsAuthenticated solamente
```

```python
# DESPUÉS — ventas/views.py
class FacturaViewSet(viewsets.ModelViewSet):
    serializer_class = FacturaSerializer
    permission_classes = [IsAuthenticated, HasEmpresaPermission]

    def get_queryset(self):
        return Factura.objects.filter(
            venta__empresa=self.request.user.empresa    # ← solo las facturas de tu empresa
        ).select_related('cliente', 'venta')
```

**Por qué importa:** El sistema es multi-tenant — cada empresa debe ver únicamente sus propios datos. Este fallo violaba ese invariante fundamental. Se aprovechó el fix para añadir `select_related` y eliminar el N+1 en el listado de facturas.

---

### Bug 3 — Race condition en numeración de Ventas y Compras

**Archivos:**
- `backend/apps/ventas/models.py`, método `Venta.save()`
- `backend/apps/compras/models.py`, método `Compra.save()`

**Problema:** El algoritmo anterior cargaba todos los números existentes en memoria Python, calculaba `max()`, e incrementaba. Aunque usaba `transaction.atomic()`, no bloqueaba las filas con un `SELECT FOR UPDATE`. Bajo carga concurrente, dos requests podían leer el mismo `max_num` simultáneamente y ambos intentar crear `V-000042`, provocando una excepción 500 por violación del constraint `unique_together`.

```python
# ANTES — ventas/models.py (~60 líneas)
def save(self, *args, **kwargs):
    print(f"DEBUG SAVE: Método save llamado, numero actual: {self.numero}")
    if not self.numero:
        with transaction.atomic():
            # Carga TODOS los números en memoria — sin bloqueo de filas
            ventas_existentes = Venta.objects.filter(
                empresa_id=self.empresa.id
            ).values_list('numero', flat=True)           # ← sin SELECT FOR UPDATE

            numeros_existentes = []
            for numero in ventas_existentes:             # ← parsing manual en Python
                if numero.startswith('V-'):
                    numeros_existentes.append(int(numero.split('-')[1]))
                elif numero.isdigit():
                    numeros_existentes.append(int(numero))

            max_num = max(numeros_existentes)            # ← dos requests leen el mismo max
            siguiente_num = max_num + 1
            self.numero = f"V-{str(siguiente_num).zfill(6)}"

            while Venta.objects.filter(                  # ← busy-wait en BD
                empresa_id=self.empresa.id,
                numero=self.numero
            ).exists():
                siguiente_num += 1
                self.numero = f"V-{str(siguiente_num).zfill(6)}"
```

```python
# DESPUÉS — ventas/models.py (~20 líneas)
def save(self, *args, **kwargs):
    if not self.numero:
        with transaction.atomic():
            # SELECT FOR UPDATE bloquea la última fila — el segundo request espera
            ultima = (
                Venta.objects.select_for_update()
                .filter(empresa_id=self.empresa.id, numero__startswith='V-')
                .order_by('-numero')
                .only('numero')
                .first()
            )
            if ultima:
                try:
                    siguiente_num = int(ultima.numero.split('-')[1]) + 1
                except (ValueError, IndexError):
                    siguiente_num = Venta.objects.filter(
                        empresa_id=self.empresa.id
                    ).count() + 1
            else:
                # Compatibilidad con registros legacy (formato numérico puro)
                legacy = (
                    Venta.objects.select_for_update()
                    .filter(empresa_id=self.empresa.id, numero__regex=r'^\d+$')
                    .order_by('-numero')
                    .only('numero')
                    .first()
                )
                siguiente_num = (int(legacy.numero) + 1) if legacy else 1

            self.numero = f"V-{str(siguiente_num).zfill(6)}"
```

El mismo cambio se aplicó a `Compra.save()` en `compras/models.py` (prefijo `C-`).

**Por qué importa:** `SELECT FOR UPDATE` hace que la segunda transacción espere en la base de datos hasta que la primera haga commit, garantizando que cada request lee un `max_num` distinto. También elimina ~100 líneas de código de parsing manual y el bucle `while` de busy-wait.

---

## Mejoras de Rendimiento Aplicadas

### CONN_MAX_AGE: 0 → 60

**Archivo:** `backend/config/settings.py`

```python
# ANTES
'CONN_MAX_AGE': 0,          # Nueva conexión TCP+TLS en CADA request
'CONN_HEALTH_CHECKS': False,
```

```python
# DESPUÉS
'CONN_MAX_AGE': 60,         # Reutiliza la misma conexión hasta 60 segundos
'CONN_HEALTH_CHECKS': True, # Detecta conexiones zombie antes de reutilizarlas
```

Con `CONN_MAX_AGE: 0`, Django abre y cierra una conexión TCP+TLS a Supabase (PostgreSQL remoto) en cada request HTTP. El handshake TLS sobre una conexión remota tarda entre 30ms y 80ms. Con `CONN_MAX_AGE: 60`, la conexión se reutiliza dentro del mismo worker durante 60 segundos. `CONN_HEALTH_CHECKS: True` envía un ping antes de reutilizar una conexión para evitar errores si Supabase cerró la conexión por timeout de su lado.

**Impacto:** ~50ms menos de latencia por request. En producción con gunicorn (3 workers, 120s timeout), esto se multiplica por el volumen de requests.

---

### select_related + prefetch_related en VentaViewSet

**Archivo:** `backend/apps/ventas/views.py`, clase `VentaViewSet`

```python
# ANTES — N+1 queries por página
def get_queryset(self):
    queryset = self.queryset.filter(empresa=self.request.user.empresa)
    # Sin select_related ni prefetch_related
    return queryset.order_by('-fecha_emision')
    # Con PAGE_SIZE=10: 1 (ventas) + 10 (clientes) + 10 (detalles) = 21+ queries
```

```python
# DESPUÉS — 3 queries fijas por página
def get_queryset(self):
    queryset = Venta.objects.filter(
        empresa=self.request.user.empresa
    ).select_related('cliente').prefetch_related('detalles__producto')
    return queryset.order_by('-fecha_emision')
    # Con PAGE_SIZE=10: 1 (ventas+clientes JOIN) + 1 (detalles) + 1 (productos) = 3 queries
```

Este cambio impacta:
- **Listado de ventas** (`GET /api/ventas/`) — la vista más consultada del sistema.
- **Exportar Excel** (`GET /api/ventas/exportar_excel/`) — antes iteraba 500 ventas con 2 queries adicionales cada una (~1500 queries por export).
- **`ventas_pendientes`** — endpoint de cuentas por cobrar que lista todas las ventas a crédito pendientes.

---

### Eliminación de 309 print() de debug

**Archivos afectados:** 25 archivos en `backend/apps/`

```
ventas/serializers.py          61 eliminados
compras/views.py               40 convertidos a logger.*
ventas/models.py               28 convertidos a logger.*
ai_assistant/ (7 archivos)     70 eliminados
inventario/views.py            11 eliminados
inventario/signals.py          11 convertidos a logger.debug
compras/models.py              10 convertidos a logger.*
... (13 archivos más)
```

Los 309 `print()` iban a stdout sin estructura, sin nivel de log, y sin timestamp. En Cloud Run, cada línea de stdout es un log entry que se indexa y factura. Se reemplazaron por llamadas al módulo `logging` de Python con el patrón:

```python
# En cada archivo modificado (Grupo B)
import logging
logger = logging.getLogger(__name__)

# Debug puro → eliminado completamente (Grupo A — 194 prints)
# Operacional (stock, pagos) → logger.info(...)
# Errores en except → logger.error(..., exc_info=True)
```

Se actualizó `config/settings.py` con un formatter y logger padre `apps`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
    },
    'root': {'handlers': ['console'], 'level': 'WARNING'},
    'loggers': {
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',   # DEBUG en dev, INFO en prod
            'propagate': False,
        },
        # django.request, django.server en ERROR
        # apps.core.middleware.tenant en DEBUG/WARNING
    },
}
```

**Antes:** `=== ACTUALIZANDO STOCK PARA VENTA V-000042 ===` (stdout sin estructura)
**Después:** `INFO 2026-05-29 20:47:44,555 apps.ventas.models Actualizando stock venta V-000042 (modo: stock)`

---

## Bugs Pendientes (no corregidos aún)

### 1. `anular_venta()` no revierte `InventarioProductosTerminados`

**Archivo:** `backend/apps/ventas/models.py`, método `anular_venta()`, línea ~491

Al anular una venta pagada, el método revierte el `Stock` legacy pero no toca `InventarioProductosTerminados` ni registra un `MovimientoInventario` de reversión. Esto deja los inventarios separados (MP, PT) desincronizados con el Stock legacy.

**Riesgo:** Alto — si se anulan ventas de productos terminados, el conteo de stock en el módulo de inventario avanzado queda incorrecto indefinidamente.

**Fix necesario:** Añadir `InventarioProductosTerminados.revertir_venta(...)` en `anular_venta()`, espejando la lógica inversa de `_descontar_producto_terminado`.

---

### 2. Modelos ML no persisten en Cloud Run

**Archivo:** `backend/apps/ml_models/models.py`, campo `model_file_path = CharField(...)`

Los modelos de Machine Learning (churn prediction, RFM segmentation, demand forecasting) se guardan como archivos `.pkl` en el filesystem. Cloud Run es efímero — cada nuevo contenedor parte de imagen limpia, borrando todos los archivos generados en contenedores anteriores.

**Riesgo:** Medio — cada redeploy borra los modelos entrenados. El dashboard de ML mostrará errores o datos vacíos tras cualquier deployment.

**Fix necesario:** Almacenar los `.pkl` en Google Cloud Storage y actualizar `model_file_path` para apuntar a una URI de GCS (`gs://bucket/...`). Cargar el modelo bajo demanda con `joblib.load(gcs_client.download(path))`.

---

### 3. `CSRF_TRUSTED_ORIGINS` hardcodeado

**Archivo:** `backend/config/settings.py`, líneas 45-48

```python
CSRF_TRUSTED_ORIGINS = [
    'https://erp-backend-25656632090.southamerica-west1.run.app',  # ← hardcodeado
    'https://*.run.app',
]
```

Si el servicio de Cloud Run cambia de ID (nuevo proyecto, nueva región, redeploy desde cero), el hash en la URL cambiará y CSRF fallará en producción sin ningún error obvio — simplemente todas las requests POST/PUT/PATCH devolverán 403.

**Fix necesario:** Mover a variable de entorno: `CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',')`.

---

### 4. `VentaListCreateView` sin filtro de empresa

**Archivo:** `backend/apps/ventas/views.py`, líneas 40-47

```python
class VentaListCreateView(generics.ListCreateAPIView):
    queryset = Venta.objects.all()   # ← todas las ventas de todos los tenants
    serializer_class = VentaSerializer
    pagination_class = VentaPagination
```

Esta vista convive con `VentaViewSet` en el mismo router. Si bien `VentaViewSet` (que sí filtra por empresa) toma prioridad en las rutas estándar, `VentaListCreateView` podría ser accesible en rutas legacy. Debería eliminarse o añadirle el filtro.

---

### 5. `OrdenCompra.convertir_a_compra()` deshabilitado

**Archivo:** `backend/apps/compras/models.py`, línea ~757

```python
def convertir_a_compra(self):
    if self.estado != 'aprobada':
        raise ValidationError('Solo se pueden convertir a compra las órdenes aprobadas')
    raise ValidationError('Funcionalidad temporalmente deshabilitada')  # ← siempre falla
```

El flujo Orden de Compra → Compra está roto. Si el negocio usa este flujo, los usuarios no pueden completarlo desde el sistema.

---

## Deuda Técnica Identificada

### Archivos excesivamente largos

| Archivo | Líneas | Problema |
|---|---|---|
| `apps/ventas/views.py` | ~1220 | Un solo ViewSet con 15+ actions, importaciones mixtas, lógica de reportes |
| `apps/ventas/models.py` | ~500 | Métodos de 200+ líneas (`actualizar_stock`, `_descontar_materias_primas_por_receta`) |
| `apps/compras/models.py` | ~850 | Incluye 6 modelos distintos + señales + utilidades |
| `frontend/src/components/Ventas/NuevaVenta.jsx` | ~857 | Un solo formulario con toda la lógica de cliente, documento y productos |

Cada uno de estos archivos viola el principio de responsabilidad única. Son difíciles de testear, revisar y mantener.

---

### Sin tests unitarios

Los archivos `tests.py` en todas las apps contienen solo el boilerplate vacío de Django. No hay cobertura de:
- Lógica de stock (`actualizar_stock`, `anular_venta`)
- Generación de números de venta/compra
- Cálculo de IGV (subtotal, total)
- Permisos multi-tenant (`HasEmpresaPermission`)
- Serializers con validaciones de DNI/RUC

**Riesgo:** Cualquier refactor rompe funcionalidad de negocio sin que los tests lo detecten.

---

### Lógica de negocio en el Model layer

`Venta.actualizar_stock()`, `Compra.actualizar_stock()`, y `Venta._descontar_materias_primas_por_receta()` contienen 200+ líneas de lógica de negocio directamente en métodos del modelo Django. Esto hace que:
- Sea imposible testear la lógica de stock sin una base de datos real.
- Los modelos acumulen demasiadas responsabilidades.
- La lógica sea difícil de reutilizar desde otros contextos (comandos de gestión, tareas Celery, etc.).

**Solución recomendada:** Extraer a un `StockService` en `apps/inventario/services/stock_service.py` con métodos estáticos testeable en aislamiento.

---

### Dos clientes HTTP en el frontend

El frontend tiene tres puntos de entrada para la API:
- `src/lib/api.js` — fuente de verdad (axios con interceptors de JWT)
- `src/services/api.jsx` — re-exporta desde `lib/api.js`
- `src/api.jsx` — re-exporta desde `services/api.jsx`

Cualquier desarrollador nuevo puede importar de cualquiera de los tres, generando imports inconsistentes. Debería haber un único punto de importación: `import api from '@/lib/api'`.

---

### `Factura` como modelo redundante

El modelo `Factura` (en `ventas/models.py:611`) duplica campos de `Venta` (`subtotal`, `igv`, `total`) con lógica de cálculo propia. En la práctica el sistema usa `Venta` + `ComprobantePago` para todo y `Factura` no es referenciada desde el frontend. Es código muerto que aumenta la superficie de ataque.

---

## Próximos Pasos Recomendados

### Prioridad Alta — Correctness y seguridad (hacer antes del próximo deploy)

1. **Corregir `anular_venta()` para revertir `InventarioProductosTerminados`**
   - Archivo: `apps/ventas/models.py`
   - Añadir reversión espejada de `_descontar_producto_terminado` al anular.
   - Agregar test de integración que verifique que stock + inventarioPT quedan sincronizados.

2. **Mover `CSRF_TRUSTED_ORIGINS` a variable de entorno**
   - Archivo: `apps/ventas/views.py` y `config/settings.py`
   - `CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',')`
   - Añadir al `.env` y `ENV_EXAMPLE.txt`.

3. **Eliminar o corregir `VentaListCreateView`**
   - Si ya no se usa: eliminar la clase y su referencia si existe en algún `urlpatterns`.
   - Si se usa: añadir `get_queryset()` con filtro `empresa=request.user.empresa`.

### Prioridad Media — Rendimiento y mantenibilidad (próximo sprint)

4. **Extraer `StockService` del Model layer**
   - Crear `apps/inventario/services/stock_service.py`
   - Mover `actualizar_stock()` y `_descontar_materias_primas_por_receta()` a métodos estáticos.
   - Dejar en el modelo solo un delegado: `def actualizar_stock(self): StockService.procesar_venta(self)`.

5. **Escribir tests para lógica crítica**
   - Priorizar: generación de números (race condition), cálculo de IGV, filtros multi-tenant.
   - Usar `pytest-django` con factories (`factory_boy`) para generar datos de prueba.
   - Meta: 80% de cobertura en `ventas/models.py` y `compras/models.py`.

6. **Migrar almacenamiento de modelos ML a Google Cloud Storage**
   - Requiere: `google-cloud-storage` en `requirements.txt`.
   - Actualizar `MLModel.model_file_path` a URI de GCS.
   - Implementar carga lazy: `joblib.load(gcs_client.open(uri))`.

### Prioridad Baja — Simplificación y UX (backlog)

7. **Consolidar formularios duplicados de compras en el frontend**
   - `OrdenCompraForm.jsx`, `PurchaseOrderForm.jsx` y `PurchaseOrderServiciosForm.jsx` resuelven el mismo problema.
   - Unificar en un solo formulario con selector de tipo (productos/servicios).

8. **Eliminar el modelo `Factura` o documentar su propósito**
   - Si es código muerto: eliminar modelo, migración de borrado, y `FacturaViewSet`.
   - Si tiene uso futuro: añadir comentario con el caso de uso y conectar al frontend.

9. **Unificar los tres puntos de importación de la API en el frontend**
   - Mantener solo `src/lib/api.js`.
   - Eliminar `src/services/api.jsx` y `src/api.jsx`.
   - Actualizar todos los imports con un codemod o búsqueda global.

10. **Añadir onboarding forzado de empresa**
    - Al crear usuario, se genera un RUC aleatorio inválido (`get_random_string(11, '0123456789')`).
    - Añadir una pantalla de configuración de empresa obligatoria antes de acceder al dashboard si `empresa.ruc` no tiene formato válido.

---

*Documento generado con `/document-generate` (gstack) · 2026-05-29*
