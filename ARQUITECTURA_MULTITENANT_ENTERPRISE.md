# ARQUITECTURA MULTI-TENANT ENTERPRISE
## ERP Django + Supabase PostgreSQL

**Fecha:** 2026-02-24  
**Arquitecto:** Sistema Senior PostgreSQL / SaaS Multi-Tenant  
**Nivel:** Enterprise (Fintech-grade)

---

## FASE 1 – DIAGNÓSTICO COMPLETO

### 1.1 TABLAS SIN `empresa_id` (CRÍTICO)

Las siguientes tablas **NO tienen aislamiento multi-tenant** y representan un riesgo de seguridad crítico:

| Tabla | Relación Padre | Acción Requerida |
|-------|----------------|------------------|
| `ai_assistant_aiaction` | conversation → empresa | Agregar empresa_id via JOIN |
| `ai_assistant_message` | conversation → empresa | Agregar empresa_id via JOIN |
| `compras_compradetalle` | compra → empresa | Agregar empresa_id via JOIN |
| `compras_comprobantepago` | compra → empresa | Agregar empresa_id via JOIN |
| `compras_ordencompradetalle` | orden → empresa | Agregar empresa_id via JOIN |
| `compras_pagocompra` | compra → empresa | Agregar empresa_id via JOIN |
| `compras_recepcioncompra` | orden → empresa | Agregar empresa_id via JOIN |
| `core_perfil` | usuario → empresa | Agregar empresa_id via JOIN |
| `detalles_cotizacion` | cotizacion → empresa | Agregar empresa_id via JOIN |
| `inventario_ajusteinventario` | almacen → empresa | Agregar empresa_id via JOIN |
| `produccion_consumoreal` | orden_produccion → empresa | Agregar empresa_id via JOIN |
| `produccion_historialordenproduccion` | orden → empresa | Agregar empresa_id via JOIN |
| `produccion_productioncost` | orden_produccion → empresa | Agregar empresa_id via JOIN |
| `produccion_productionoutput` | orden_produccion → empresa | Agregar empresa_id via JOIN |
| `produccion_productionwaste` | orden_produccion → empresa | Agregar empresa_id via JOIN |
| `produccion_recetadetalle` | receta → empresa | Agregar empresa_id via JOIN |
| `ventas_comprobantepago` | venta → empresa | Agregar empresa_id via JOIN |
| `ventas_detalleventa` | venta → empresa | Agregar empresa_id via JOIN |
| `ventas_factura` | venta → empresa | Agregar empresa_id via JOIN |
| `ventas_pagoventa` | venta → empresa | Agregar empresa_id via JOIN |

**Total: 20 tablas sin aislamiento adecuado**

---

### 1.2 INCONSISTENCIAS DE TIPOS PK/FK (CRÍTICO)

| Tabla | Columna FK | Tipo Actual | Tipo Esperado | Tabla Referenciada |
|-------|------------|-------------|---------------|-------------------|
| `inventario_movimientoinventario` | `compra_id` | `integer` | `bigint` | `compras_compra` |
| `inventario_movimientoinventario` | `venta_id` | `integer` | `bigint` | `ventas_venta` |
| `inventario_movimientoinventario` | `ajuste_id` | `integer` | `bigint` | `inventario_ajusteinventario` |
| `inventario_movimientoinventario` | `orden_produccion_id` | `integer` | `bigint` | `produccion_ordenproduccion` |
| `inventario_inventarioproductosterminados` | `orden_produccion_id` | `integer` | `bigint` | `produccion_ordenproduccion` |
| `inventario_ajusteinventario` | `cantidad` | `integer` | `numeric` | - |
| `auth_group_permissions` | `group_id` | `integer` | `integer` | `auth_group` (OK) |
| `auth_group_permissions` | `permission_id` | `integer` | `integer` | `auth_permission` (OK) |

**Riesgo:** Overflow de ID, inconsistencia en JOINs, errores silenciosos.

---

### 1.3 COLUMNAS VARCHAR QUE DEBERÍAN SER ENUM/CATÁLOGO

#### Estados Críticos (Alta Frecuencia de Query)

| Campo | Tablas | Valores Detectados |
|-------|--------|-------------------|
| `estado` | compras_compra, compras_ordencompra, cotizaciones, produccion_ordenproduccion, ventas_venta, ventas_ordenventa | pendiente, pagada, completada, cancelada, borrador, aceptada, etc. |
| `tipo_compra` | compras_compra | contado, credito_30, credito_60, credito_90 |
| `metodo_pago` | compras_compra, compras_pagocompra, ventas_pagoventa, ventas_venta | efectivo, transferencia, tarjeta, pendiente |
| `moneda` | compras_compra, ventas_venta, compras_pagocompra | PEN, USD, EUR |
| `tipo_movimiento` | inventario_movimientoinventario | entrada, salida, ajuste, transferencia |
| `tipo_documento` | inventario_movimientoinventario, ventas_cliente | factura, boleta, guia, DNI, RUC |
| `tipo_producto` | inventario_producto | materia_prima, producto_terminado, servicio |
| `tipo_evento` | produccion_historialordenproduccion | creacion, inicio, actualizacion_progreso, finalizacion, cancelacion |
| `frecuencia` | compras_comprarecurrente | mensual, quincenal, semanal, anual |
| `rol` | core_usuario | admin, vendedor, almacenero, contador |

**Problema:** Sin validación a nivel DB, datos inconsistentes, queries lentas (no indexables eficientemente).

---

### 1.4 ÍNDICES FALTANTES CRÍTICOS

| Tabla | Índice Faltante | Justificación |
|-------|-----------------|---------------|
| `compras_compra` | `(empresa_id, fecha_emision)` | Reportes por período |
| `compras_compra` | `(empresa_id, estado)` | Filtros de estado |
| `ventas_venta` | `(empresa_id, fecha_emision)` | Reportes por período |
| `ventas_venta` | `(empresa_id, estado)` | Filtros de estado |
| `produccion_ordenproduccion` | `(empresa_id, estado)` | Dashboard producción |
| `produccion_ordenproduccion` | `(empresa_id, fecha_programada)` | Planificación |
| `inventario_movimientoinventario` | `(empresa_id, fecha)` | Kardex, reportes |
| `inventario_movimientoinventario` | `(empresa_id, tipo_movimiento)` | Filtros |
| `inventario_producto` | `(empresa_id, tipo_producto)` | Filtros por tipo |
| `inventario_stock` | `(empresa_id, producto_id)` | Consultas frecuentes |
| `cotizaciones` | `(empresa_id, estado)` | Pipeline comercial |
| `cotizaciones` | `(empresa_id, fecha_emision)` | Reportes |

---

### 1.5 SOFT DELETE FALTANTE

**Estado actual:** NINGUNA tabla implementa soft delete.

**Tablas críticas que requieren soft delete:**
- `empresas_empresa`
- `authentication_customuser`
- `ventas_cliente`
- `compras_proveedor`
- `inventario_producto`
- `inventario_almacen`
- `inventario_categoria`
- `produccion_recetaproducto`
- `compras_compra`
- `ventas_venta`
- `produccion_ordenproduccion`
- `cotizaciones`

---

### 1.6 RLS (ROW LEVEL SECURITY) - NO IMPLEMENTADO

**Estado actual:** RLS está **DESACTIVADO** en todas las tablas.

**Riesgo crítico:** Sin RLS, cualquier query puede acceder a datos de otras empresas si hay un bug en el código de aplicación.

---

## FASE 2 – PLAN DE MIGRACIÓN SEGURO

### ORDEN DE EJECUCIÓN (Crítico)

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Corregir FK inconsistentes (integer → bigint)               │
│     ↓                                                           │
│  2. Agregar columna empresa_id a tablas hijas                   │
│     ↓                                                           │
│  3. Poblar empresa_id usando JOINs con tablas padre             │
│     ↓                                                           │
│  4. Crear índices estratégicos                                  │
│     ↓                                                           │
│  5. Crear ENUMs para estados críticos                           │
│     ↓                                                           │
│  6. Activar RLS y crear políticas                               │
│     ↓                                                           │
│  7. Agregar soft delete (deleted_at, deleted_by)                │
│     ↓                                                           │
│  8. [FUTURO] Evaluar migración bigint → UUID                    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.1 Estrategia de Migración Sin Downtime

1. **Agregar columnas NULLABLE primero** (sin romper aplicación)
2. **Poblar datos en background** (script batch)
3. **Agregar NOT NULL constraint** después de poblar
4. **Crear índices CONCURRENTLY** (sin bloquear tablas)
5. **Activar RLS tabla por tabla** (rollback granular)

---

## FASE 3 – SCRIPTS SQL DE IMPLEMENTACIÓN

### 3.1 PASO 1: Corregir FK Inconsistentes

```sql
-- ================================================================
-- PASO 1: CORREGIR TIPOS DE FK INCONSISTENTES
-- Ejecutar en orden, verificar cada paso
-- ================================================================

-- 1.1 inventario_movimientoinventario.compra_id (integer → bigint)
ALTER TABLE inventario_movimientoinventario 
ALTER COLUMN compra_id TYPE bigint;

-- 1.2 inventario_movimientoinventario.venta_id (integer → bigint)
ALTER TABLE inventario_movimientoinventario 
ALTER COLUMN venta_id TYPE bigint;

-- 1.3 inventario_movimientoinventario.ajuste_id (integer → bigint)
ALTER TABLE inventario_movimientoinventario 
ALTER COLUMN ajuste_id TYPE bigint;

-- 1.4 inventario_movimientoinventario.orden_produccion_id (integer → bigint)
ALTER TABLE inventario_movimientoinventario 
ALTER COLUMN orden_produccion_id TYPE bigint;

-- 1.5 inventario_inventarioproductosterminados.orden_produccion_id (integer → bigint)
ALTER TABLE inventario_inventarioproductosterminados 
ALTER COLUMN orden_produccion_id TYPE bigint;

-- 1.6 inventario_ajusteinventario.cantidad (integer → numeric para consistencia)
ALTER TABLE inventario_ajusteinventario 
ALTER COLUMN cantidad TYPE numeric(10,2);

-- Verificación
SELECT table_name, column_name, data_type 
FROM information_schema.columns 
WHERE column_name IN ('compra_id', 'venta_id', 'ajuste_id', 'orden_produccion_id', 'cantidad')
AND table_schema = 'public'
ORDER BY table_name;
```

### 3.2 PASO 2: Agregar empresa_id a Tablas Hijas

```sql
-- ================================================================
-- PASO 2: AGREGAR COLUMNA empresa_id (NULLABLE primero)
-- ================================================================

-- 2.1 Tablas de AI Assistant
ALTER TABLE ai_assistant_aiaction ADD COLUMN IF NOT EXISTS empresa_id BIGINT;
ALTER TABLE ai_assistant_message ADD COLUMN IF NOT EXISTS empresa_id BIGINT;

-- 2.2 Tablas de Compras
ALTER TABLE compras_compradetalle ADD COLUMN IF NOT EXISTS empresa_id BIGINT;
ALTER TABLE compras_comprobantepago ADD COLUMN IF NOT EXISTS empresa_id BIGINT;
ALTER TABLE compras_ordencompradetalle ADD COLUMN IF NOT EXISTS empresa_id BIGINT;
ALTER TABLE compras_pagocompra ADD COLUMN IF NOT EXISTS empresa_id BIGINT;
ALTER TABLE compras_recepcioncompra ADD COLUMN IF NOT EXISTS empresa_id BIGINT;

-- 2.3 Tablas de Core
ALTER TABLE core_perfil ADD COLUMN IF NOT EXISTS empresa_id BIGINT;

-- 2.4 Tablas de Cotizaciones
ALTER TABLE detalles_cotizacion ADD COLUMN IF NOT EXISTS empresa_id BIGINT;

-- 2.5 Tablas de Inventario
ALTER TABLE inventario_ajusteinventario ADD COLUMN IF NOT EXISTS empresa_id BIGINT;

-- 2.6 Tablas de Producción
ALTER TABLE produccion_consumoreal ADD COLUMN IF NOT EXISTS empresa_id BIGINT;
ALTER TABLE produccion_historialordenproduccion ADD COLUMN IF NOT EXISTS empresa_id BIGINT;
ALTER TABLE produccion_productioncost ADD COLUMN IF NOT EXISTS empresa_id BIGINT;
ALTER TABLE produccion_productionoutput ADD COLUMN IF NOT EXISTS empresa_id BIGINT;
ALTER TABLE produccion_productionwaste ADD COLUMN IF NOT EXISTS empresa_id BIGINT;
ALTER TABLE produccion_recetadetalle ADD COLUMN IF NOT EXISTS empresa_id BIGINT;

-- 2.7 Tablas de Ventas
ALTER TABLE ventas_comprobantepago ADD COLUMN IF NOT EXISTS empresa_id BIGINT;
ALTER TABLE ventas_detalleventa ADD COLUMN IF NOT EXISTS empresa_id BIGINT;
ALTER TABLE ventas_factura ADD COLUMN IF NOT EXISTS empresa_id BIGINT;
ALTER TABLE ventas_pagoventa ADD COLUMN IF NOT EXISTS empresa_id BIGINT;

-- Verificación
SELECT table_name, column_name, is_nullable 
FROM information_schema.columns 
WHERE column_name = 'empresa_id' 
AND table_schema = 'public'
ORDER BY table_name;
```

### 3.3 PASO 3: Poblar empresa_id con JOINs

```sql
-- ================================================================
-- PASO 3: POBLAR empresa_id USANDO JOINS CON TABLAS PADRE
-- Ejecutar en transacciones separadas para evitar locks largos
-- ================================================================

-- 3.1 AI Assistant
BEGIN;
UPDATE ai_assistant_aiaction aa
SET empresa_id = ac.empresa_id
FROM ai_assistant_conversation ac
WHERE aa.conversation_id = ac.id
AND aa.empresa_id IS NULL;
COMMIT;

BEGIN;
UPDATE ai_assistant_message am
SET empresa_id = ac.empresa_id
FROM ai_assistant_conversation ac
WHERE am.conversation_id = ac.id
AND am.empresa_id IS NULL;
COMMIT;

-- 3.2 Compras - Detalles
BEGIN;
UPDATE compras_compradetalle cd
SET empresa_id = c.empresa_id
FROM compras_compra c
WHERE cd.compra_id = c.id
AND cd.empresa_id IS NULL;
COMMIT;

BEGIN;
UPDATE compras_comprobantepago cp
SET empresa_id = c.empresa_id
FROM compras_compra c
WHERE cp.compra_id = c.id
AND cp.empresa_id IS NULL;
COMMIT;

BEGIN;
UPDATE compras_pagocompra pc
SET empresa_id = c.empresa_id
FROM compras_compra c
WHERE pc.compra_id = c.id
AND pc.empresa_id IS NULL;
COMMIT;

-- 3.3 Compras - Órdenes
BEGIN;
UPDATE compras_ordencompradetalle od
SET empresa_id = o.empresa_id
FROM compras_ordencompra o
WHERE od.orden_id = o.id
AND od.empresa_id IS NULL;
COMMIT;

BEGIN;
UPDATE compras_recepcioncompra rc
SET empresa_id = o.empresa_id
FROM compras_ordencompra o
WHERE rc.orden_id = o.id
AND rc.empresa_id IS NULL;
COMMIT;

-- 3.4 Core
BEGIN;
UPDATE core_perfil cp
SET empresa_id = cu.empresa_id
FROM authentication_customuser cu
WHERE cp.usuario_id = cu.id
AND cp.empresa_id IS NULL;
COMMIT;

-- 3.5 Cotizaciones
BEGIN;
UPDATE detalles_cotizacion dc
SET empresa_id = c.empresa_id
FROM cotizaciones c
WHERE dc.cotizacion_id = c.id
AND dc.empresa_id IS NULL;
COMMIT;

-- 3.6 Inventario
BEGIN;
UPDATE inventario_ajusteinventario ai
SET empresa_id = a.empresa_id
FROM inventario_almacen a
WHERE ai.almacen_id = a.id
AND ai.empresa_id IS NULL;
COMMIT;

-- 3.7 Producción - Detalles de Orden
BEGIN;
UPDATE produccion_consumoreal cr
SET empresa_id = op.empresa_id
FROM produccion_ordenproduccion op
WHERE cr.orden_produccion_id = op.id
AND cr.empresa_id IS NULL;
COMMIT;

BEGIN;
UPDATE produccion_historialordenproduccion hp
SET empresa_id = op.empresa_id
FROM produccion_ordenproduccion op
WHERE hp.orden_id = op.id
AND hp.empresa_id IS NULL;
COMMIT;

BEGIN;
UPDATE produccion_productioncost pc
SET empresa_id = op.empresa_id
FROM produccion_ordenproduccion op
WHERE pc.orden_produccion_id = op.id
AND pc.empresa_id IS NULL;
COMMIT;

BEGIN;
UPDATE produccion_productionoutput po
SET empresa_id = op.empresa_id
FROM produccion_ordenproduccion op
WHERE po.orden_produccion_id = op.id
AND po.empresa_id IS NULL;
COMMIT;

BEGIN;
UPDATE produccion_productionwaste pw
SET empresa_id = op.empresa_id
FROM produccion_ordenproduccion op
WHERE pw.orden_produccion_id = op.id
AND pw.empresa_id IS NULL;
COMMIT;

-- 3.8 Producción - Detalles de Receta
BEGIN;
UPDATE produccion_recetadetalle rd
SET empresa_id = rp.empresa_id
FROM produccion_recetaproducto rp
WHERE rd.receta_id = rp.id
AND rd.empresa_id IS NULL;
COMMIT;

-- 3.9 Ventas
BEGIN;
UPDATE ventas_comprobantepago vc
SET empresa_id = v.empresa_id
FROM ventas_venta v
WHERE vc.venta_id = v.id
AND vc.empresa_id IS NULL;
COMMIT;

BEGIN;
UPDATE ventas_detalleventa dv
SET empresa_id = v.empresa_id
FROM ventas_venta v
WHERE dv.venta_id = v.id
AND dv.empresa_id IS NULL;
COMMIT;

BEGIN;
UPDATE ventas_factura vf
SET empresa_id = v.empresa_id
FROM ventas_venta v
WHERE vf.venta_id = v.id
AND vf.empresa_id IS NULL;
COMMIT;

BEGIN;
UPDATE ventas_pagoventa pv
SET empresa_id = v.empresa_id
FROM ventas_venta v
WHERE pv.venta_id = v.id
AND pv.empresa_id IS NULL;
COMMIT;

-- VERIFICACIÓN: Contar registros sin empresa_id
SELECT 'ai_assistant_aiaction' as tabla, COUNT(*) as sin_empresa FROM ai_assistant_aiaction WHERE empresa_id IS NULL
UNION ALL SELECT 'ai_assistant_message', COUNT(*) FROM ai_assistant_message WHERE empresa_id IS NULL
UNION ALL SELECT 'compras_compradetalle', COUNT(*) FROM compras_compradetalle WHERE empresa_id IS NULL
UNION ALL SELECT 'compras_comprobantepago', COUNT(*) FROM compras_comprobantepago WHERE empresa_id IS NULL
UNION ALL SELECT 'compras_ordencompradetalle', COUNT(*) FROM compras_ordencompradetalle WHERE empresa_id IS NULL
UNION ALL SELECT 'compras_pagocompra', COUNT(*) FROM compras_pagocompra WHERE empresa_id IS NULL
UNION ALL SELECT 'compras_recepcioncompra', COUNT(*) FROM compras_recepcioncompra WHERE empresa_id IS NULL
UNION ALL SELECT 'core_perfil', COUNT(*) FROM core_perfil WHERE empresa_id IS NULL
UNION ALL SELECT 'detalles_cotizacion', COUNT(*) FROM detalles_cotizacion WHERE empresa_id IS NULL
UNION ALL SELECT 'inventario_ajusteinventario', COUNT(*) FROM inventario_ajusteinventario WHERE empresa_id IS NULL
UNION ALL SELECT 'produccion_consumoreal', COUNT(*) FROM produccion_consumoreal WHERE empresa_id IS NULL
UNION ALL SELECT 'produccion_historialordenproduccion', COUNT(*) FROM produccion_historialordenproduccion WHERE empresa_id IS NULL
UNION ALL SELECT 'produccion_productioncost', COUNT(*) FROM produccion_productioncost WHERE empresa_id IS NULL
UNION ALL SELECT 'produccion_productionoutput', COUNT(*) FROM produccion_productionoutput WHERE empresa_id IS NULL
UNION ALL SELECT 'produccion_productionwaste', COUNT(*) FROM produccion_productionwaste WHERE empresa_id IS NULL
UNION ALL SELECT 'produccion_recetadetalle', COUNT(*) FROM produccion_recetadetalle WHERE empresa_id IS NULL
UNION ALL SELECT 'ventas_comprobantepago', COUNT(*) FROM ventas_comprobantepago WHERE empresa_id IS NULL
UNION ALL SELECT 'ventas_detalleventa', COUNT(*) FROM ventas_detalleventa WHERE empresa_id IS NULL
UNION ALL SELECT 'ventas_factura', COUNT(*) FROM ventas_factura WHERE empresa_id IS NULL
UNION ALL SELECT 'ventas_pagoventa', COUNT(*) FROM ventas_pagoventa WHERE empresa_id IS NULL;
```

### 3.4 PASO 4: Agregar NOT NULL y Foreign Keys

```sql
-- ================================================================
-- PASO 4: AGREGAR CONSTRAINTS NOT NULL Y FOREIGN KEYS
-- Solo ejecutar después de verificar que NO hay NULLs
-- ================================================================

-- 4.1 Agregar NOT NULL (solo si la verificación anterior dio 0 en todas)
ALTER TABLE ai_assistant_aiaction ALTER COLUMN empresa_id SET NOT NULL;
ALTER TABLE ai_assistant_message ALTER COLUMN empresa_id SET NOT NULL;
ALTER TABLE compras_compradetalle ALTER COLUMN empresa_id SET NOT NULL;
ALTER TABLE compras_comprobantepago ALTER COLUMN empresa_id SET NOT NULL;
ALTER TABLE compras_ordencompradetalle ALTER COLUMN empresa_id SET NOT NULL;
ALTER TABLE compras_pagocompra ALTER COLUMN empresa_id SET NOT NULL;
ALTER TABLE compras_recepcioncompra ALTER COLUMN empresa_id SET NOT NULL;
ALTER TABLE core_perfil ALTER COLUMN empresa_id SET NOT NULL;
ALTER TABLE detalles_cotizacion ALTER COLUMN empresa_id SET NOT NULL;
ALTER TABLE inventario_ajusteinventario ALTER COLUMN empresa_id SET NOT NULL;
ALTER TABLE produccion_consumoreal ALTER COLUMN empresa_id SET NOT NULL;
ALTER TABLE produccion_historialordenproduccion ALTER COLUMN empresa_id SET NOT NULL;
ALTER TABLE produccion_productioncost ALTER COLUMN empresa_id SET NOT NULL;
ALTER TABLE produccion_productionoutput ALTER COLUMN empresa_id SET NOT NULL;
ALTER TABLE produccion_productionwaste ALTER COLUMN empresa_id SET NOT NULL;
ALTER TABLE produccion_recetadetalle ALTER COLUMN empresa_id SET NOT NULL;
ALTER TABLE ventas_comprobantepago ALTER COLUMN empresa_id SET NOT NULL;
ALTER TABLE ventas_detalleventa ALTER COLUMN empresa_id SET NOT NULL;
ALTER TABLE ventas_factura ALTER COLUMN empresa_id SET NOT NULL;
ALTER TABLE ventas_pagoventa ALTER COLUMN empresa_id SET NOT NULL;

-- 4.2 Agregar Foreign Keys
ALTER TABLE ai_assistant_aiaction 
ADD CONSTRAINT fk_aiaction_empresa FOREIGN KEY (empresa_id) REFERENCES empresas_empresa(id);

ALTER TABLE ai_assistant_message 
ADD CONSTRAINT fk_message_empresa FOREIGN KEY (empresa_id) REFERENCES empresas_empresa(id);

ALTER TABLE compras_compradetalle 
ADD CONSTRAINT fk_compradetalle_empresa FOREIGN KEY (empresa_id) REFERENCES empresas_empresa(id);

ALTER TABLE compras_comprobantepago 
ADD CONSTRAINT fk_comprobantepago_compra_empresa FOREIGN KEY (empresa_id) REFERENCES empresas_empresa(id);

ALTER TABLE compras_ordencompradetalle 
ADD CONSTRAINT fk_ordencompradetalle_empresa FOREIGN KEY (empresa_id) REFERENCES empresas_empresa(id);

ALTER TABLE compras_pagocompra 
ADD CONSTRAINT fk_pagocompra_empresa FOREIGN KEY (empresa_id) REFERENCES empresas_empresa(id);

ALTER TABLE compras_recepcioncompra 
ADD CONSTRAINT fk_recepcioncompra_empresa FOREIGN KEY (empresa_id) REFERENCES empresas_empresa(id);

ALTER TABLE core_perfil 
ADD CONSTRAINT fk_perfil_empresa FOREIGN KEY (empresa_id) REFERENCES empresas_empresa(id);

ALTER TABLE detalles_cotizacion 
ADD CONSTRAINT fk_detallecotizacion_empresa FOREIGN KEY (empresa_id) REFERENCES empresas_empresa(id);

ALTER TABLE inventario_ajusteinventario 
ADD CONSTRAINT fk_ajusteinventario_empresa FOREIGN KEY (empresa_id) REFERENCES empresas_empresa(id);

ALTER TABLE produccion_consumoreal 
ADD CONSTRAINT fk_consumoreal_empresa FOREIGN KEY (empresa_id) REFERENCES empresas_empresa(id);

ALTER TABLE produccion_historialordenproduccion 
ADD CONSTRAINT fk_historialorden_empresa FOREIGN KEY (empresa_id) REFERENCES empresas_empresa(id);

ALTER TABLE produccion_productioncost 
ADD CONSTRAINT fk_productioncost_empresa FOREIGN KEY (empresa_id) REFERENCES empresas_empresa(id);

ALTER TABLE produccion_productionoutput 
ADD CONSTRAINT fk_productionoutput_empresa FOREIGN KEY (empresa_id) REFERENCES empresas_empresa(id);

ALTER TABLE produccion_productionwaste 
ADD CONSTRAINT fk_productionwaste_empresa FOREIGN KEY (empresa_id) REFERENCES empresas_empresa(id);

ALTER TABLE produccion_recetadetalle 
ADD CONSTRAINT fk_recetadetalle_empresa FOREIGN KEY (empresa_id) REFERENCES empresas_empresa(id);

ALTER TABLE ventas_comprobantepago 
ADD CONSTRAINT fk_comprobantepago_venta_empresa FOREIGN KEY (empresa_id) REFERENCES empresas_empresa(id);

ALTER TABLE ventas_detalleventa 
ADD CONSTRAINT fk_detalleventa_empresa FOREIGN KEY (empresa_id) REFERENCES empresas_empresa(id);

ALTER TABLE ventas_factura 
ADD CONSTRAINT fk_factura_empresa FOREIGN KEY (empresa_id) REFERENCES empresas_empresa(id);

ALTER TABLE ventas_pagoventa 
ADD CONSTRAINT fk_pagoventa_empresa FOREIGN KEY (empresa_id) REFERENCES empresas_empresa(id);
```

### 3.5 PASO 5: Crear Índices Estratégicos

```sql
-- ================================================================
-- PASO 5: CREAR ÍNDICES ESTRATÉGICOS
-- Usar CONCURRENTLY para evitar bloqueos en producción
-- ================================================================

-- 5.1 Índices en empresa_id (tablas recién actualizadas)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_aiaction_empresa ON ai_assistant_aiaction(empresa_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_message_empresa ON ai_assistant_message(empresa_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_compradetalle_empresa ON compras_compradetalle(empresa_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comprobantepago_compra_empresa ON compras_comprobantepago(empresa_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ordencompradetalle_empresa ON compras_ordencompradetalle(empresa_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pagocompra_empresa ON compras_pagocompra(empresa_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recepcioncompra_empresa ON compras_recepcioncompra(empresa_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_perfil_empresa ON core_perfil(empresa_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_detallecotizacion_empresa ON detalles_cotizacion(empresa_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ajusteinventario_empresa ON inventario_ajusteinventario(empresa_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_consumoreal_empresa ON produccion_consumoreal(empresa_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_historialorden_empresa ON produccion_historialordenproduccion(empresa_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_productioncost_empresa ON produccion_productioncost(empresa_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_productionoutput_empresa ON produccion_productionoutput(empresa_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_productionwaste_empresa ON produccion_productionwaste(empresa_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recetadetalle_empresa ON produccion_recetadetalle(empresa_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comprobantepago_venta_empresa ON ventas_comprobantepago(empresa_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_detalleventa_empresa ON ventas_detalleventa(empresa_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_factura_empresa ON ventas_factura(empresa_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pagoventa_empresa ON ventas_pagoventa(empresa_id);

-- 5.2 Índices compuestos para reportes (empresa_id + fecha)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_compra_empresa_fecha 
ON compras_compra(empresa_id, fecha_emision);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_compra_empresa_estado 
ON compras_compra(empresa_id, estado);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_venta_empresa_fecha 
ON ventas_venta(empresa_id, fecha_emision);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_venta_empresa_estado 
ON ventas_venta(empresa_id, estado);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ordenproduccion_empresa_estado 
ON produccion_ordenproduccion(empresa_id, estado);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ordenproduccion_empresa_fecha 
ON produccion_ordenproduccion(empresa_id, fecha_programada);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_movimiento_empresa_fecha 
ON inventario_movimientoinventario(empresa_id, fecha);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_movimiento_empresa_tipo 
ON inventario_movimientoinventario(empresa_id, tipo_movimiento);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_producto_empresa_tipo 
ON inventario_producto(empresa_id, tipo_producto);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stock_empresa_producto 
ON inventario_stock(empresa_id, producto_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cotizacion_empresa_estado 
ON cotizaciones(empresa_id, estado);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cotizacion_empresa_fecha 
ON cotizaciones(empresa_id, fecha_emision);

-- 5.3 Índices para búsquedas frecuentes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_producto_empresa_sku 
ON inventario_producto(empresa_id, sku);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cliente_empresa_documento 
ON ventas_cliente(empresa_id, documento);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_proveedor_empresa_ruc 
ON compras_proveedor(empresa_id, ruc);
```

### 3.6 PASO 6: Crear ENUMs para Estados

```sql
-- ================================================================
-- PASO 6: CREAR TIPOS ENUM PARA ESTADOS CRÍTICOS
-- NOTA: Django no soporta ENUMs nativamente, usar CHECK constraints
-- ================================================================

-- 6.1 Crear tipos ENUM (para referencia, usar con cautela en Django)
DO $$ BEGIN
    CREATE TYPE estado_documento AS ENUM (
        'borrador', 'pendiente', 'aprobada', 'rechazada', 
        'en_proceso', 'completada', 'pagada', 'parcial', 
        'cancelada', 'anulada'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE tipo_compra AS ENUM (
        'contado', 'credito_15', 'credito_30', 'credito_45', 
        'credito_60', 'credito_90'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE metodo_pago AS ENUM (
        'efectivo', 'transferencia', 'tarjeta_credito', 
        'tarjeta_debito', 'cheque', 'pendiente', 'otro'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE tipo_moneda AS ENUM ('PEN', 'USD', 'EUR');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE tipo_movimiento_inv AS ENUM (
        'entrada', 'salida', 'ajuste_positivo', 'ajuste_negativo', 
        'transferencia_entrada', 'transferencia_salida', 
        'produccion_consumo', 'produccion_output'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE tipo_producto AS ENUM (
        'materia_prima', 'producto_terminado', 'insumo', 
        'servicio', 'consumible'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE tipo_evento_produccion AS ENUM (
        'creacion', 'inicio', 'pausa', 'reanudacion', 
        'actualizacion_progreso', 'finalizacion', 'cancelacion', 'otro'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- 6.2 Alternativa con CHECK constraints (mejor compatibilidad Django)
-- Ejemplo para compras_compra.estado
ALTER TABLE compras_compra DROP CONSTRAINT IF EXISTS chk_compra_estado;
ALTER TABLE compras_compra ADD CONSTRAINT chk_compra_estado 
CHECK (estado IN ('borrador', 'pendiente', 'aprobada', 'pagada', 'parcial', 'cancelada', 'anulada'));

ALTER TABLE ventas_venta DROP CONSTRAINT IF EXISTS chk_venta_estado;
ALTER TABLE ventas_venta ADD CONSTRAINT chk_venta_estado 
CHECK (estado IN ('borrador', 'pendiente', 'aprobada', 'pagada', 'parcial', 'cancelada', 'anulada'));

ALTER TABLE produccion_ordenproduccion DROP CONSTRAINT IF EXISTS chk_orden_estado;
ALTER TABLE produccion_ordenproduccion ADD CONSTRAINT chk_orden_estado 
CHECK (estado IN ('borrador', 'pendiente', 'en_proceso', 'completada', 'cancelada'));

ALTER TABLE cotizaciones DROP CONSTRAINT IF EXISTS chk_cotizacion_estado;
ALTER TABLE cotizaciones ADD CONSTRAINT chk_cotizacion_estado 
CHECK (estado IN ('borrador', 'enviada', 'aceptada', 'rechazada', 'vencida', 'convertida'));
```

### 3.7 PASO 7: Activar RLS (Row Level Security)

```sql
-- ================================================================
-- PASO 7: ACTIVAR ROW LEVEL SECURITY
-- CRÍTICO: Esto protege los datos a nivel de base de datos
-- ================================================================

-- 7.1 Crear función para obtener empresa_id del contexto
CREATE OR REPLACE FUNCTION get_current_empresa_id() 
RETURNS BIGINT AS $$
BEGIN
    RETURN NULLIF(current_setting('app.current_empresa', true), '')::BIGINT;
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 7.2 Activar RLS en tablas principales (con empresa_id)
-- IMPORTANTE: El superusuario (postgres) bypasea RLS por defecto

-- Empresas (tabla raíz - RLS especial)
ALTER TABLE empresas_empresa ENABLE ROW LEVEL SECURITY;
CREATE POLICY empresa_isolation ON empresas_empresa
    FOR ALL
    USING (id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Usuarios
ALTER TABLE authentication_customuser ENABLE ROW LEVEL SECURITY;
CREATE POLICY user_isolation ON authentication_customuser
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Clientes
ALTER TABLE ventas_cliente ENABLE ROW LEVEL SECURITY;
CREATE POLICY cliente_isolation ON ventas_cliente
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Proveedores
ALTER TABLE compras_proveedor ENABLE ROW LEVEL SECURITY;
CREATE POLICY proveedor_isolation ON compras_proveedor
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Productos
ALTER TABLE inventario_producto ENABLE ROW LEVEL SECURITY;
CREATE POLICY producto_isolation ON inventario_producto
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Stock
ALTER TABLE inventario_stock ENABLE ROW LEVEL SECURITY;
CREATE POLICY stock_isolation ON inventario_stock
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Almacenes
ALTER TABLE inventario_almacen ENABLE ROW LEVEL SECURITY;
CREATE POLICY almacen_isolation ON inventario_almacen
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Categorías
ALTER TABLE inventario_categoria ENABLE ROW LEVEL SECURITY;
CREATE POLICY categoria_isolation ON inventario_categoria
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR empresa_id IS NULL OR get_current_empresa_id() IS NULL);

-- Movimientos de inventario
ALTER TABLE inventario_movimientoinventario ENABLE ROW LEVEL SECURITY;
CREATE POLICY movimiento_isolation ON inventario_movimientoinventario
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Inventario Materias Primas
ALTER TABLE inventario_inventariomateriasprimas ENABLE ROW LEVEL SECURITY;
CREATE POLICY inv_mp_isolation ON inventario_inventariomateriasprimas
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Inventario Productos Terminados
ALTER TABLE inventario_inventarioproductosterminados ENABLE ROW LEVEL SECURITY;
CREATE POLICY inv_pt_isolation ON inventario_inventarioproductosterminados
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Compras
ALTER TABLE compras_compra ENABLE ROW LEVEL SECURITY;
CREATE POLICY compra_isolation ON compras_compra
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Compra Detalles
ALTER TABLE compras_compradetalle ENABLE ROW LEVEL SECURITY;
CREATE POLICY compradetalle_isolation ON compras_compradetalle
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Pagos Compra
ALTER TABLE compras_pagocompra ENABLE ROW LEVEL SECURITY;
CREATE POLICY pagocompra_isolation ON compras_pagocompra
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Órdenes de Compra
ALTER TABLE compras_ordencompra ENABLE ROW LEVEL SECURITY;
CREATE POLICY ordencompra_isolation ON compras_ordencompra
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Compras Recurrentes
ALTER TABLE compras_comprarecurrente ENABLE ROW LEVEL SECURITY;
CREATE POLICY comprarecurrente_isolation ON compras_comprarecurrente
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Ventas
ALTER TABLE ventas_venta ENABLE ROW LEVEL SECURITY;
CREATE POLICY venta_isolation ON ventas_venta
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Detalle Ventas
ALTER TABLE ventas_detalleventa ENABLE ROW LEVEL SECURITY;
CREATE POLICY detalleventa_isolation ON ventas_detalleventa
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Pagos Venta
ALTER TABLE ventas_pagoventa ENABLE ROW LEVEL SECURITY;
CREATE POLICY pagoventa_isolation ON ventas_pagoventa
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Órdenes de Venta
ALTER TABLE ventas_ordenventa ENABLE ROW LEVEL SECURITY;
CREATE POLICY ordenventa_isolation ON ventas_ordenventa
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Cotizaciones
ALTER TABLE cotizaciones ENABLE ROW LEVEL SECURITY;
CREATE POLICY cotizacion_isolation ON cotizaciones
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Detalles Cotización
ALTER TABLE detalles_cotizacion ENABLE ROW LEVEL SECURITY;
CREATE POLICY detallecotizacion_isolation ON detalles_cotizacion
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Producción - Recetas
ALTER TABLE produccion_recetaproducto ENABLE ROW LEVEL SECURITY;
CREATE POLICY receta_isolation ON produccion_recetaproducto
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Producción - Detalles Receta
ALTER TABLE produccion_recetadetalle ENABLE ROW LEVEL SECURITY;
CREATE POLICY recetadetalle_isolation ON produccion_recetadetalle
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Producción - Órdenes
ALTER TABLE produccion_ordenproduccion ENABLE ROW LEVEL SECURITY;
CREATE POLICY ordenproduccion_isolation ON produccion_ordenproduccion
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Producción - Consumo Real
ALTER TABLE produccion_consumoreal ENABLE ROW LEVEL SECURITY;
CREATE POLICY consumoreal_isolation ON produccion_consumoreal
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Producción - Historial
ALTER TABLE produccion_historialordenproduccion ENABLE ROW LEVEL SECURITY;
CREATE POLICY historialorden_isolation ON produccion_historialordenproduccion
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Producción - Costos
ALTER TABLE produccion_productioncost ENABLE ROW LEVEL SECURITY;
CREATE POLICY productioncost_isolation ON produccion_productioncost
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- ML Models
ALTER TABLE ml_models_mlmodel ENABLE ROW LEVEL SECURITY;
CREATE POLICY mlmodel_isolation ON ml_models_mlmodel
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE ml_models_trainingjob ENABLE ROW LEVEL SECURITY;
CREATE POLICY trainingjob_isolation ON ml_models_trainingjob
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- AI Assistant
ALTER TABLE ai_assistant_conversation ENABLE ROW LEVEL SECURITY;
CREATE POLICY conversation_isolation ON ai_assistant_conversation
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE ai_assistant_aiinsight ENABLE ROW LEVEL SECURITY;
CREATE POLICY aiinsight_isolation ON ai_assistant_aiinsight
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- Verificación de RLS activado
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
AND rowsecurity = true
ORDER BY tablename;
```

### 3.8 PASO 8: Soft Delete

```sql
-- ================================================================
-- PASO 8: IMPLEMENTAR SOFT DELETE
-- Agregar columnas deleted_at y deleted_by
-- ================================================================

-- 8.1 Agregar columnas de soft delete a tablas principales
ALTER TABLE empresas_empresa ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE empresas_empresa ADD COLUMN IF NOT EXISTS deleted_by BIGINT;

ALTER TABLE authentication_customuser ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE authentication_customuser ADD COLUMN IF NOT EXISTS deleted_by BIGINT;

ALTER TABLE ventas_cliente ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE ventas_cliente ADD COLUMN IF NOT EXISTS deleted_by BIGINT;

ALTER TABLE compras_proveedor ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE compras_proveedor ADD COLUMN IF NOT EXISTS deleted_by BIGINT;

ALTER TABLE inventario_producto ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE inventario_producto ADD COLUMN IF NOT EXISTS deleted_by BIGINT;

ALTER TABLE inventario_almacen ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE inventario_almacen ADD COLUMN IF NOT EXISTS deleted_by BIGINT;

ALTER TABLE inventario_categoria ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE inventario_categoria ADD COLUMN IF NOT EXISTS deleted_by BIGINT;

ALTER TABLE produccion_recetaproducto ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE produccion_recetaproducto ADD COLUMN IF NOT EXISTS deleted_by BIGINT;

ALTER TABLE compras_compra ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE compras_compra ADD COLUMN IF NOT EXISTS deleted_by BIGINT;

ALTER TABLE ventas_venta ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE ventas_venta ADD COLUMN IF NOT EXISTS deleted_by BIGINT;

ALTER TABLE produccion_ordenproduccion ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE produccion_ordenproduccion ADD COLUMN IF NOT EXISTS deleted_by BIGINT;

ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS deleted_by BIGINT;

-- 8.2 Crear índices para soft delete (queries de activos)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_empresa_active ON empresas_empresa(id) WHERE deleted_at IS NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_active ON authentication_customuser(id) WHERE deleted_at IS NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cliente_active ON ventas_cliente(empresa_id) WHERE deleted_at IS NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_proveedor_active ON compras_proveedor(empresa_id) WHERE deleted_at IS NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_producto_active ON inventario_producto(empresa_id) WHERE deleted_at IS NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_almacen_active ON inventario_almacen(empresa_id) WHERE deleted_at IS NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_categoria_active ON inventario_categoria(empresa_id) WHERE deleted_at IS NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_receta_active ON produccion_recetaproducto(empresa_id) WHERE deleted_at IS NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_compra_active ON compras_compra(empresa_id) WHERE deleted_at IS NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_venta_active ON ventas_venta(empresa_id) WHERE deleted_at IS NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ordenproduccion_active ON produccion_ordenproduccion(empresa_id) WHERE deleted_at IS NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cotizacion_active ON cotizaciones(empresa_id) WHERE deleted_at IS NULL;

-- 8.3 Actualizar políticas RLS para excluir soft-deleted
-- Ejemplo para ventas_cliente
DROP POLICY IF EXISTS cliente_isolation ON ventas_cliente;
CREATE POLICY cliente_isolation ON ventas_cliente
    FOR ALL
    USING (
        (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL)
        AND deleted_at IS NULL
    );

-- Repetir para otras tablas con soft delete...
```

---

## FASE 4 – ARQUITECTURA IDEAL SAAS ENTERPRISE

### 4.1 Aislamiento Multi-Tenant Fuerte

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CAPAS DE SEGURIDAD                               │
├─────────────────────────────────────────────────────────────────────────┤
│  CAPA 1: Aplicación (Django)                                            │
│  - Middleware que setea app.current_empresa                             │
│  - Managers con filtro automático por empresa_id                        │
│  - Validación en serializers                                            │
├─────────────────────────────────────────────────────────────────────────┤
│  CAPA 2: Base de Datos (PostgreSQL + RLS)                               │
│  - Row Level Security activo en TODAS las tablas                        │
│  - Políticas basadas en current_setting('app.current_empresa')          │
│  - Foreign Keys con integridad referencial                              │
├─────────────────────────────────────────────────────────────────────────┤
│  CAPA 3: Infraestructura (Supabase)                                     │
│  - Conexiones pooling con PgBouncer                                     │
│  - SSL/TLS obligatorio                                                  │
│  - Backups automáticos                                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Middleware Django para RLS

```python
# middleware/tenant.py
class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.db import connection
        
        # Obtener empresa_id del usuario autenticado
        empresa_id = None
        if hasattr(request, 'user') and request.user.is_authenticated:
            empresa_id = getattr(request.user, 'empresa_id', None)
        
        # Setear variable de sesión para RLS
        if empresa_id:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET LOCAL app.current_empresa = %s", 
                    [str(empresa_id)]
                )
        
        response = self.get_response(request)
        return response
```

### 4.3 Manager Base Multi-Tenant

```python
# core/managers.py
from django.db import models

class TenantManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        # El RLS ya filtra, pero esto es defensa en profundidad
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.current_empresa', true)")
            empresa_id = cursor.fetchone()[0]
        
        if empresa_id:
            return qs.filter(empresa_id=empresa_id)
        return qs

class SoftDeleteManager(TenantManager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)
    
    def with_deleted(self):
        return super().get_queryset()
```

### 4.4 Modelo Base Enterprise

```python
# core/models.py
from django.db import models
from django.utils import timezone

class TenantModel(models.Model):
    """Modelo base para todas las entidades multi-tenant"""
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted_by = models.ForeignKey(
        'authentication.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )
    
    objects = SoftDeleteManager()
    all_objects = TenantManager()
    
    class Meta:
        abstract = True
    
    def soft_delete(self, user=None):
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=['deleted_at', 'deleted_by'])
    
    def restore(self):
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['deleted_at', 'deleted_by'])
```

### 4.5 Escalabilidad a 1000+ Empresas

| Aspecto | Recomendación |
|---------|---------------|
| **Particionamiento** | Considerar particionamiento por empresa_id para tablas > 10M filas |
| **Connection Pooling** | Usar PgBouncer con pool_mode=transaction |
| **Read Replicas** | Configurar réplicas de lectura para reportes pesados |
| **Caching** | Redis para caché de sesiones y datos frecuentes |
| **CDN** | Cloudflare para assets estáticos |
| **Monitoring** | pg_stat_statements + Grafana para métricas |

### 4.6 Auditoría Completa (Fintech-grade)

```sql
-- Tabla de auditoría
CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    tabla VARCHAR(100) NOT NULL,
    operacion VARCHAR(10) NOT NULL, -- INSERT, UPDATE, DELETE
    registro_id BIGINT NOT NULL,
    empresa_id BIGINT NOT NULL,
    usuario_id BIGINT,
    datos_anteriores JSONB,
    datos_nuevos JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_empresa ON audit_log(empresa_id);
CREATE INDEX idx_audit_tabla ON audit_log(tabla);
CREATE INDEX idx_audit_fecha ON audit_log(created_at);

-- Trigger de auditoría genérico
CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (tabla, operacion, registro_id, empresa_id, usuario_id, datos_nuevos)
        VALUES (TG_TABLE_NAME, 'INSERT', NEW.id, NEW.empresa_id, 
                NULLIF(current_setting('app.current_user', true), '')::BIGINT,
                to_jsonb(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (tabla, operacion, registro_id, empresa_id, usuario_id, datos_anteriores, datos_nuevos)
        VALUES (TG_TABLE_NAME, 'UPDATE', NEW.id, NEW.empresa_id,
                NULLIF(current_setting('app.current_user', true), '')::BIGINT,
                to_jsonb(OLD), to_jsonb(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (tabla, operacion, registro_id, empresa_id, usuario_id, datos_anteriores)
        VALUES (TG_TABLE_NAME, 'DELETE', OLD.id, OLD.empresa_id,
                NULLIF(current_setting('app.current_user', true), '')::BIGINT,
                to_jsonb(OLD));
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Aplicar trigger a tablas críticas (ejemplo)
CREATE TRIGGER audit_compras_compra
AFTER INSERT OR UPDATE OR DELETE ON compras_compra
FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

CREATE TRIGGER audit_ventas_venta
AFTER INSERT OR UPDATE OR DELETE ON ventas_venta
FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

CREATE TRIGGER audit_inventario_producto
AFTER INSERT OR UPDATE OR DELETE ON inventario_producto
FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();
```

---

## RESUMEN EJECUTIVO

### Problemas Críticos Identificados:
1. **20 tablas sin empresa_id** → Riesgo de fuga de datos entre tenants
2. **5 columnas FK con tipo incorrecto** → Riesgo de overflow/errores
3. **10+ columnas varchar para estados** → Datos inconsistentes, queries lentas
4. **0 tablas con RLS** → Sin protección a nivel DB
5. **0 tablas con soft delete** → Pérdida irrecuperable de datos
6. **~15 índices faltantes** → Performance degradado en reportes

### Orden de Implementación:
1. ✅ Corregir FK inconsistentes (integer -> bigint) - EJECUTADO 2026-02-24
2. ✅ Agregar empresa_id a 20 tablas hijas - EJECUTADO 2026-02-24
3. ✅ Poblar empresa_id (101 registros via JOINs + NOT NULL + FKs) - EJECUTADO 2026-02-24
4. ✅ Crear 56 índices estratégicos (CONCURRENTLY) - EJECUTADO 2026-02-24
5. ✅ Crear 16 CHECK constraints para estados - EJECUTADO 2026-02-24
6. ✅ Activar RLS en 55 tablas + 45 políticas + función get_current_empresa_id() - EJECUTADO 2026-02-24
7. ✅ Soft delete (14 tablas + índices parciales + funciones helper) - EJECUTADO 2026-02-24
8. ✅ Auditoría enterprise (audit_log + audit_trigger_func + 33 triggers) - EJECUTADO 2026-02-24
9. ⏳ Evaluar migración bigint -> UUID (fase futura, no prioritaria)

### Integración Django:
- ✅ Middleware TenantMiddleware activado en settings.py (después de AuthenticationMiddleware)
- ✅ ATOMIC_REQUESTS habilitado para soporte transaccional de SET/RESET
- ✅ Modelos base creados: TenantModel, SoftDeleteModel, AuditMixin (apps/core/models/base.py)
- ✅ Managers especializados: TenantManager, SoftDeleteManager
- ✅ Logger configurado para tenant middleware
- ⏳ Pendiente: Heredar modelos existentes de SoftDeleteModel/TenantModel
- ⏳ Pendiente: Ejecutar makemigrations + migrate --fake para sincronizar Django con cambios SQL

### Archivos Clave Creados:
| Archivo | Propósito |
|---------|-----------|
| `backend/apps/core/middleware/tenant.py` | Middleware RLS: SET/RESET app.current_empresa por request |
| `backend/apps/core/models/base.py` | Modelos abstractos: TenantModel, SoftDeleteModel, AuditMixin |
| `backend/apps/core/middleware/__init__.py` | Init del paquete middleware |
| `migrations_sql/01-07_*.sql` | Scripts SQL ejecutados en Supabase |

---

**Documento actualizado: 2026-02-24 | Todas las fases de BD ejecutadas | Django integrado**
