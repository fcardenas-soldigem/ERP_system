# MIGRACIÓN empresa_id: BIGINT → UUID
## ERP Django + Supabase PostgreSQL

**Fecha:** 2026-02-24
**Nivel:** Enterprise SaaS (Fintech-grade)
**Riesgo:** ALTO — Afecta 44 tablas, 43 FKs, 45 políticas RLS, 91 índices, 20 triggers

---

## FASE 1 — DIAGNÓSTICO

### 1.1 Estado Actual de `empresas_empresa`

| Columna | Tipo | Nullable | Notas |
|---------|------|----------|-------|
| `id` | bigint (PK) | NO | Autoincremental, usado como empresa_id en 44 tablas |
| `nombre` | varchar | NO | |
| `ruc` | varchar | NO | Identificador fiscal |
| `direccion` | varchar | YES | |
| `telefono` | varchar | YES | |
| `email` | varchar | YES | |
| `is_active` | boolean | NO | |
| `logo` | varchar | YES | |
| `deleted_at` | timestamptz | YES | Soft delete |
| `deleted_by` | bigint | YES | |

**Datos actuales:** 2 empresas (ID=1: Soluciones Digitales Empresariales, ID=2: Pet Universe)

### 1.2 Impacto de la Migración

| Componente | Cantidad | Acción Requerida |
|------------|----------|------------------|
| Tablas con `empresa_id` | 44 | Agregar `empresa_uuid`, migrar FK |
| Foreign Keys a `empresas_empresa` | 43 | Recrear apuntando a UUID |
| Políticas RLS | 45 | Recrear con `::uuid` |
| Índices en `empresa_id` | 91 | Recrear en `empresa_uuid` |
| Triggers `auto_empresa` | 20 | Actualizar función |
| Triggers de auditoría | 33 | Se adaptan automáticamente |
| Funciones SQL | 2 | Reescribir para UUID |
| Registros totales afectados | ~350+ | UPDATE con JOIN |

### 1.3 Tablas con Datos (Riesgo de Corrupción)

| Tabla | Registros |
|-------|-----------|
| ml_models_trainingjob | 58 |
| inventario_movimientoinventario | 43 |
| ventas_detalleventa | 31 |
| compras_compradetalle | 26 |
| inventario_producto | 25 |
| inventario_stock | 25 |
| inventario_inventarioproductosterminados | 23 |
| ventas_venta | 14 |
| compras_compra | 13 |
| ai_assistant_message | 10 |
| ml_models_mlmodel | 10 |
| produccion_consumoreal | 10 |
| ventas_pagoventa | 9 |
| compras_proveedor | 7 |
| ventas_cliente | 7 |

### 1.4 Evaluación de Riesgo

```
⚠️  RIESGO CRÍTICO: Esta migración toca el corazón del sistema multi-tenant.
    Un error puede:
    - Romper TODAS las queries
    - Mezclar datos entre empresas
    - Dejar el sistema inoperativo

✅  MITIGACIÓN:
    - Migración incremental (bigint y UUID coexisten)
    - Validación en cada paso
    - Rollback posible hasta el paso final
    - Solo ~350 registros (bajo volumen = bajo riesgo de locks)
```

---

## FASE 2 — PLAN DE MIGRACIÓN SEGURA

### Orden de Ejecución

```
┌─────────────────────────────────────────────────────────────────────┐
│  ETAPA 1: Agregar empresa_uuid a empresas_empresa (PK futura)      │
│     ↓  (sistema sigue operando con bigint)                         │
│  ETAPA 2: Agregar empresa_uuid a las 43 tablas hijas               │
│     ↓  (columnas coexisten, sin FK aún)                            │
│  ETAPA 3: Poblar empresa_uuid en TODAS las tablas via JOIN         │
│     ↓  (datos sincronizados)                                       │
│  ETAPA 4: Crear índices en empresa_uuid                            │
│     ↓  (performance lista)                                         │
│  ETAPA 5: Validar integridad — STOP si hay errores                 │
│     ↓  (punto de no retorno)                                       │
│  ETAPA 6: Crear nuevas FKs en empresa_uuid                         │
│     ↓  (integridad referencial UUID)                               │
│  ETAPA 7: Actualizar RLS, triggers, funciones para UUID            │
│     ↓  (seguridad migrada)                                         │
│  ETAPA 8: Actualizar Django models + middleware                    │
│     ↓  (aplicación migrada)                                        │
│  ETAPA 9: Eliminar columnas bigint + renombrar UUID                │
│     ↓  (limpieza final — IRREVERSIBLE)                             │
│  ETAPA 10: Validación final                                        │
└─────────────────────────────────────────────────────────────────────┘
```

**Regla de oro:** Cada etapa debe ser validada antes de avanzar.
Hasta la ETAPA 8, el sistema funciona con bigint. Rollback es trivial.

---

## FASE 3 — SCRIPTS SQL

### ETAPA 1: Agregar UUID a empresas_empresa

```sql
-- ================================================================
-- ETAPA 1: Agregar empresa_uuid a la tabla principal
-- Riesgo: CERO (solo agrega columna)
-- ================================================================

-- Habilitar extensión UUID si no existe
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Agregar columna UUID con valor auto-generado
ALTER TABLE empresas_empresa 
ADD COLUMN IF NOT EXISTS uuid UUID DEFAULT gen_random_uuid() NOT NULL;

-- Crear índice UNIQUE en uuid (será la nueva PK)
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_empresa_uuid_unique 
ON empresas_empresa(uuid);

-- Verificar
SELECT id, uuid, nombre FROM empresas_empresa;
```

### ETAPA 2: Agregar empresa_uuid a las 43 tablas hijas

```sql
-- ================================================================
-- ETAPA 2: Agregar columna empresa_uuid (NULLABLE) a todas las tablas
-- Riesgo: BAJO (solo agrega columnas vacías)
-- ================================================================

ALTER TABLE ai_assistant_aiaction ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE ai_assistant_aiinsight ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE ai_assistant_conversation ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE ai_assistant_message ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE authentication_customuser ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE compras_compra ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE compras_compradetalle ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE compras_comprarecurrente ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE compras_comprobantepago ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE compras_ordencompra ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE compras_ordencompradetalle ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE compras_pagocompra ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE compras_proveedor ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE compras_recepcioncompra ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE core_perfil ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE core_usuario ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE detalles_cotizacion ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE inventario_ajusteinventario ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE inventario_almacen ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE inventario_categoria ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE inventario_inventariomateriasprimas ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE inventario_inventarioproductosterminados ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE inventario_movimientoinventario ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE inventario_producto ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE inventario_stock ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE ml_models_mlmodel ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE ml_models_trainingjob ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE produccion_consumoreal ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE produccion_historialordenproduccion ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE produccion_ordenproduccion ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE produccion_productioncost ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE produccion_productionoutput ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE produccion_productionwaste ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE produccion_recetadetalle ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE produccion_recetaproducto ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE ventas_cliente ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE ventas_comprobantepago ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE ventas_detalleventa ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE ventas_factura ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE ventas_ordenventa ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE ventas_pagoventa ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
ALTER TABLE ventas_venta ADD COLUMN IF NOT EXISTS empresa_uuid UUID;
```

### ETAPA 3: Poblar empresa_uuid en TODAS las tablas

```sql
-- ================================================================
-- ETAPA 3: Poblar empresa_uuid usando JOIN con empresas_empresa
-- Riesgo: BAJO (solo UPDATE, no modifica estructura)
-- ================================================================

-- Poblar cada tabla hija con el UUID de su empresa
UPDATE ai_assistant_aiaction t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE ai_assistant_aiinsight t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE ai_assistant_conversation t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE ai_assistant_message t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE audit_log t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE authentication_customuser t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE compras_compra t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE compras_compradetalle t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE compras_comprarecurrente t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE compras_comprobantepago t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE compras_ordencompra t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE compras_ordencompradetalle t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE compras_pagocompra t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE compras_proveedor t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE compras_recepcioncompra t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE core_perfil t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE core_usuario t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE cotizaciones t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE detalles_cotizacion t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE inventario_ajusteinventario t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE inventario_almacen t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE inventario_categoria t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE inventario_inventariomateriasprimas t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE inventario_inventarioproductosterminados t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE inventario_movimientoinventario t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE inventario_producto t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE inventario_stock t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE ml_models_mlmodel t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE ml_models_trainingjob t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE produccion_consumoreal t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE produccion_historialordenproduccion t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE produccion_ordenproduccion t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE produccion_productioncost t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE produccion_productionoutput t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE produccion_productionwaste t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE produccion_recetadetalle t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE produccion_recetaproducto t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE ventas_cliente t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE ventas_comprobantepago t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE ventas_detalleventa t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE ventas_factura t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE ventas_ordenventa t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE ventas_pagoventa t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
UPDATE ventas_venta t SET empresa_uuid = e.uuid FROM empresas_empresa e WHERE t.empresa_id = e.id AND t.empresa_uuid IS NULL;
```

### ETAPA 4: Crear índices en empresa_uuid

```sql
-- ================================================================
-- ETAPA 4: Índices en empresa_uuid (CONCURRENTLY para no bloquear)
-- ================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_ai_aiaction ON ai_assistant_aiaction(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_ai_aiinsight ON ai_assistant_aiinsight(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_ai_conversation ON ai_assistant_conversation(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_ai_message ON ai_assistant_message(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_audit_log ON audit_log(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_auth_user ON authentication_customuser(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_compra ON compras_compra(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_compradetalle ON compras_compradetalle(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_comprarecurrente ON compras_comprarecurrente(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_comprobante_compra ON compras_comprobantepago(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_ordencompra ON compras_ordencompra(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_ordencompradet ON compras_ordencompradetalle(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_pagocompra ON compras_pagocompra(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_proveedor ON compras_proveedor(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_recepcion ON compras_recepcioncompra(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_perfil ON core_perfil(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_coreusuario ON core_usuario(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_cotizacion ON cotizaciones(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_detcotizacion ON detalles_cotizacion(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_ajuste ON inventario_ajusteinventario(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_almacen ON inventario_almacen(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_categoria ON inventario_categoria(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_inv_mp ON inventario_inventariomateriasprimas(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_inv_pt ON inventario_inventarioproductosterminados(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_movimiento ON inventario_movimientoinventario(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_producto ON inventario_producto(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_stock ON inventario_stock(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_mlmodel ON ml_models_mlmodel(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_trainingjob ON ml_models_trainingjob(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_consumoreal ON produccion_consumoreal(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_historial ON produccion_historialordenproduccion(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_ordenproduccion ON produccion_ordenproduccion(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_productioncost ON produccion_productioncost(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_productionoutput ON produccion_productionoutput(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_productionwaste ON produccion_productionwaste(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_recetadetalle ON produccion_recetadetalle(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_receta ON produccion_recetaproducto(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_cliente ON ventas_cliente(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_comprobante_venta ON ventas_comprobantepago(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_detalleventa ON ventas_detalleventa(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_factura ON ventas_factura(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_ordenventa ON ventas_ordenventa(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_pagoventa ON ventas_pagoventa(empresa_uuid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uuid_venta ON ventas_venta(empresa_uuid);
```

### ETAPA 5: Validación de Integridad (OBLIGATORIO antes de continuar)

```sql
-- ================================================================
-- ETAPA 5: VALIDACIÓN — PARAR SI ALGÚN RESULTADO NO ES 0
-- ================================================================

-- Verificar que NO hay NULLs en empresa_uuid
SELECT 'ai_assistant_aiaction' as t, count(*) as nulls FROM ai_assistant_aiaction WHERE empresa_uuid IS NULL AND empresa_id IS NOT NULL
UNION ALL SELECT 'authentication_customuser', count(*) FROM authentication_customuser WHERE empresa_uuid IS NULL AND empresa_id IS NOT NULL
UNION ALL SELECT 'compras_compra', count(*) FROM compras_compra WHERE empresa_uuid IS NULL
UNION ALL SELECT 'compras_compradetalle', count(*) FROM compras_compradetalle WHERE empresa_uuid IS NULL
UNION ALL SELECT 'compras_proveedor', count(*) FROM compras_proveedor WHERE empresa_uuid IS NULL
UNION ALL SELECT 'cotizaciones', count(*) FROM cotizaciones WHERE empresa_uuid IS NULL
UNION ALL SELECT 'detalles_cotizacion', count(*) FROM detalles_cotizacion WHERE empresa_uuid IS NULL
UNION ALL SELECT 'inventario_producto', count(*) FROM inventario_producto WHERE empresa_uuid IS NULL
UNION ALL SELECT 'inventario_stock', count(*) FROM inventario_stock WHERE empresa_uuid IS NULL
UNION ALL SELECT 'inventario_almacen', count(*) FROM inventario_almacen WHERE empresa_uuid IS NULL
UNION ALL SELECT 'inventario_movimientoinventario', count(*) FROM inventario_movimientoinventario WHERE empresa_uuid IS NULL
UNION ALL SELECT 'produccion_ordenproduccion', count(*) FROM produccion_ordenproduccion WHERE empresa_uuid IS NULL
UNION ALL SELECT 'produccion_recetaproducto', count(*) FROM produccion_recetaproducto WHERE empresa_uuid IS NULL
UNION ALL SELECT 'ventas_venta', count(*) FROM ventas_venta WHERE empresa_uuid IS NULL
UNION ALL SELECT 'ventas_detalleventa', count(*) FROM ventas_detalleventa WHERE empresa_uuid IS NULL
UNION ALL SELECT 'ventas_cliente', count(*) FROM ventas_cliente WHERE empresa_uuid IS NULL;

-- Verificar consistencia: empresa_uuid debe corresponder al empresa_id correcto
SELECT 'INCONSISTENCIA' as status, t.id, t.empresa_id, t.empresa_uuid, e.uuid as expected_uuid
FROM ventas_venta t
JOIN empresas_empresa e ON t.empresa_id = e.id
WHERE t.empresa_uuid != e.uuid;
-- Repetir para tablas críticas: compras_compra, inventario_producto, etc.
```

### ETAPA 6: Swap — Migrar PK y FKs a UUID

```sql
-- ================================================================
-- ETAPA 6: MIGRACIÓN DE PK/FK — PUNTO DE NO RETORNO
-- ⚠️  Ejecutar en ventana de mantenimiento
-- ⚠️  Hacer backup ANTES de ejecutar
-- ================================================================

-- 6.1 Aplicar NOT NULL a empresa_uuid en tablas con datos
-- (Solo en tablas que tienen empresa_id NOT NULL)
ALTER TABLE ai_assistant_aiaction ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE ai_assistant_aiinsight ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE ai_assistant_conversation ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE ai_assistant_message ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE compras_compra ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE compras_compradetalle ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE compras_comprarecurrente ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE compras_comprobantepago ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE compras_ordencompra ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE compras_ordencompradetalle ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE compras_pagocompra ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE compras_proveedor ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE compras_recepcioncompra ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE core_perfil ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE core_usuario ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE cotizaciones ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE detalles_cotizacion ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE inventario_ajusteinventario ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE inventario_almacen ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE inventario_inventariomateriasprimas ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE inventario_inventarioproductosterminados ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE inventario_movimientoinventario ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE inventario_producto ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE inventario_stock ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE ml_models_mlmodel ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE ml_models_trainingjob ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE produccion_consumoreal ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE produccion_historialordenproduccion ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE produccion_ordenproduccion ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE produccion_productioncost ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE produccion_productionoutput ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE produccion_productionwaste ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE produccion_recetadetalle ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE produccion_recetaproducto ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE ventas_cliente ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE ventas_comprobantepago ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE ventas_detalleventa ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE ventas_factura ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE ventas_ordenventa ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE ventas_pagoventa ALTER COLUMN empresa_uuid SET NOT NULL;
ALTER TABLE ventas_venta ALTER COLUMN empresa_uuid SET NOT NULL;

-- 6.2 Agregar constraint UNIQUE a empresas_empresa.uuid (si no existe)
ALTER TABLE empresas_empresa ADD CONSTRAINT empresas_empresa_uuid_key UNIQUE (uuid);

-- 6.3 Crear Foreign Keys en empresa_uuid → empresas_empresa(uuid)
-- (las FKs viejas en empresa_id se mantienen temporalmente)
ALTER TABLE ai_assistant_aiaction ADD CONSTRAINT fk_uuid_aiaction_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE ai_assistant_aiinsight ADD CONSTRAINT fk_uuid_aiinsight_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE ai_assistant_conversation ADD CONSTRAINT fk_uuid_conversation_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE ai_assistant_message ADD CONSTRAINT fk_uuid_message_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE authentication_customuser ADD CONSTRAINT fk_uuid_user_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE compras_compra ADD CONSTRAINT fk_uuid_compra_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE compras_compradetalle ADD CONSTRAINT fk_uuid_compradetalle_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE compras_comprarecurrente ADD CONSTRAINT fk_uuid_comprarecurrente_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE compras_comprobantepago ADD CONSTRAINT fk_uuid_comprobante_compra_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE compras_ordencompra ADD CONSTRAINT fk_uuid_ordencompra_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE compras_ordencompradetalle ADD CONSTRAINT fk_uuid_ordencompradetalle_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE compras_pagocompra ADD CONSTRAINT fk_uuid_pagocompra_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE compras_proveedor ADD CONSTRAINT fk_uuid_proveedor_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE compras_recepcioncompra ADD CONSTRAINT fk_uuid_recepcion_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE core_perfil ADD CONSTRAINT fk_uuid_perfil_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE core_usuario ADD CONSTRAINT fk_uuid_coreusuario_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE cotizaciones ADD CONSTRAINT fk_uuid_cotizacion_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE detalles_cotizacion ADD CONSTRAINT fk_uuid_detcotizacion_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE inventario_ajusteinventario ADD CONSTRAINT fk_uuid_ajuste_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE inventario_almacen ADD CONSTRAINT fk_uuid_almacen_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE inventario_categoria ADD CONSTRAINT fk_uuid_categoria_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE inventario_inventariomateriasprimas ADD CONSTRAINT fk_uuid_invmp_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE inventario_inventarioproductosterminados ADD CONSTRAINT fk_uuid_invpt_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE inventario_movimientoinventario ADD CONSTRAINT fk_uuid_movimiento_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE inventario_producto ADD CONSTRAINT fk_uuid_producto_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE inventario_stock ADD CONSTRAINT fk_uuid_stock_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE ml_models_mlmodel ADD CONSTRAINT fk_uuid_mlmodel_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE ml_models_trainingjob ADD CONSTRAINT fk_uuid_trainingjob_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE produccion_consumoreal ADD CONSTRAINT fk_uuid_consumoreal_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE produccion_historialordenproduccion ADD CONSTRAINT fk_uuid_historial_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE produccion_ordenproduccion ADD CONSTRAINT fk_uuid_ordenproduccion_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE produccion_productioncost ADD CONSTRAINT fk_uuid_productioncost_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE produccion_productionoutput ADD CONSTRAINT fk_uuid_productionoutput_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE produccion_productionwaste ADD CONSTRAINT fk_uuid_productionwaste_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE produccion_recetadetalle ADD CONSTRAINT fk_uuid_recetadetalle_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE produccion_recetaproducto ADD CONSTRAINT fk_uuid_receta_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE ventas_cliente ADD CONSTRAINT fk_uuid_cliente_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE ventas_comprobantepago ADD CONSTRAINT fk_uuid_comprobante_venta_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE ventas_detalleventa ADD CONSTRAINT fk_uuid_detalleventa_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE ventas_factura ADD CONSTRAINT fk_uuid_factura_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE ventas_ordenventa ADD CONSTRAINT fk_uuid_ordenventa_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE ventas_pagoventa ADD CONSTRAINT fk_uuid_pagoventa_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
ALTER TABLE ventas_venta ADD CONSTRAINT fk_uuid_venta_empresa FOREIGN KEY (empresa_uuid) REFERENCES empresas_empresa(uuid);
```

### ETAPA 7: Actualizar RLS, Triggers y Funciones para UUID

```sql
-- ================================================================
-- ETAPA 7: Migrar RLS y Triggers a empresa_uuid
-- ================================================================

-- 7.1 Nueva función para obtener empresa UUID del contexto
CREATE OR REPLACE FUNCTION get_current_empresa_uuid()
RETURNS UUID AS $$
BEGIN
    RETURN NULLIF(current_setting('app.current_empresa_uuid', true), '')::UUID;
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 7.2 Actualizar trigger auto_set para UUID
CREATE OR REPLACE FUNCTION auto_set_empresa_uuid()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.empresa_uuid IS NULL THEN
        NEW.empresa_uuid := get_current_empresa_uuid();
    END IF;
    IF NEW.empresa_uuid IS NULL AND NEW.empresa_id IS NOT NULL THEN
        SELECT uuid INTO NEW.empresa_uuid
        FROM empresas_empresa WHERE id = NEW.empresa_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 7.3 Actualizar trigger de auditoría para UUID
CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (tabla, operacion, registro_id, empresa_id, empresa_uuid, usuario_id, datos_nuevos)
        VALUES (
            TG_TABLE_NAME, 'INSERT', NEW.id,
            CASE WHEN TG_TABLE_NAME = 'empresas_empresa' THEN NEW.id ELSE NEW.empresa_id END,
            CASE WHEN TG_TABLE_NAME = 'empresas_empresa' THEN NEW.uuid ELSE NEW.empresa_uuid END,
            NULLIF(current_setting('app.current_user', true), '')::BIGINT,
            to_jsonb(NEW)
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (tabla, operacion, registro_id, empresa_id, empresa_uuid, usuario_id, datos_anteriores, datos_nuevos)
        VALUES (
            TG_TABLE_NAME, 'UPDATE', NEW.id,
            CASE WHEN TG_TABLE_NAME = 'empresas_empresa' THEN NEW.id ELSE NEW.empresa_id END,
            CASE WHEN TG_TABLE_NAME = 'empresas_empresa' THEN NEW.uuid ELSE NEW.empresa_uuid END,
            NULLIF(current_setting('app.current_user', true), '')::BIGINT,
            to_jsonb(OLD), to_jsonb(NEW)
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (tabla, operacion, registro_id, empresa_id, empresa_uuid, usuario_id, datos_anteriores)
        VALUES (
            TG_TABLE_NAME, 'DELETE', OLD.id,
            CASE WHEN TG_TABLE_NAME = 'empresas_empresa' THEN OLD.id ELSE OLD.empresa_id END,
            CASE WHEN TG_TABLE_NAME = 'empresas_empresa' THEN OLD.uuid ELSE OLD.empresa_uuid END,
            NULLIF(current_setting('app.current_user', true), '')::BIGINT,
            to_jsonb(OLD)
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 7.4 Las políticas RLS se actualizarán en la ETAPA 9 (después del swap)
-- Por ahora, las políticas existentes con empresa_id siguen funcionando
```

### ETAPA 8: Actualizar Django

**Middleware actualizado** (`apps/core/middleware/tenant.py`):
```python
class TenantMiddleware:
    def __call__(self, request):
        empresa_id = self._get_empresa_id(request)
        empresa_uuid = self._get_empresa_uuid(request)

        if empresa_id:
            self._set_tenant_context(empresa_id, empresa_uuid, request)

        try:
            response = self.get_response(request)
        finally:
            self._clear_tenant_context()
        return response

    def _get_empresa_uuid(self, request):
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
        # Después del swap, empresa.uuid será el campo principal
        empresa = getattr(request.user, 'empresa', None)
        return str(empresa.uuid) if empresa and hasattr(empresa, 'uuid') else None

    def _set_tenant_context(self, empresa_id, empresa_uuid, request):
        with connection.cursor() as cursor:
            cursor.execute("SET app.current_empresa = %s", [str(empresa_id)])
            if empresa_uuid:
                cursor.execute("SET app.current_empresa_uuid = %s", [empresa_uuid])
            if request.user.is_authenticated:
                cursor.execute("SET app.current_user = %s", [str(request.user.id)])
```

**Modelo Empresa actualizado:**
```python
import uuid
from django.db import models

class Empresa(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    nombre = models.CharField(max_length=200)
    ruc = models.CharField(max_length=20)
    # ... demás campos
```

### ETAPA 9: Limpieza Final (IRREVERSIBLE)

```sql
-- ================================================================
-- ETAPA 9: SWAP FINAL — empresa_uuid → empresa_id
-- ⚠️  HACER BACKUP COMPLETO ANTES
-- ⚠️  VENTANA DE MANTENIMIENTO REQUERIDA (~5 minutos downtime)
-- ================================================================

-- Esta etapa se ejecutará DESPUÉS de que Django esté
-- funcionando con empresa_uuid.
--
-- El proceso sería:
-- 1. DROP todas las FK antiguas (empresa_id bigint)
-- 2. DROP columna empresa_id de tablas hijas
-- 3. RENAME empresa_uuid → empresa_id en tablas hijas
-- 4. En empresas_empresa: DROP old id, RENAME uuid → id
-- 5. Actualizar todas las policies RLS
-- 6. Actualizar Django models (empresa_id = UUIDField)
--
-- NOTA: Este paso es IRREVERSIBLE. Solo ejecutar cuando
-- el sistema lleve al menos 1 semana operando con UUID
-- sin errores.
```

### ETAPA 10: Verificación Final

```sql
-- ================================================================
-- ETAPA 10: Verificación post-migración
-- ================================================================

-- Verificar que UUID está poblado en todas las tablas
SELECT 'empresas_empresa' as tabla, count(*) as total,
       count(uuid) as con_uuid,
       count(*) - count(uuid) as sin_uuid
FROM empresas_empresa;

-- Verificar integridad referencial UUID
SELECT 'ventas_venta' as tabla, count(*) as huerfanos
FROM ventas_venta v
WHERE NOT EXISTS (SELECT 1 FROM empresas_empresa e WHERE e.uuid = v.empresa_uuid)
UNION ALL
SELECT 'compras_compra', count(*)
FROM compras_compra c
WHERE NOT EXISTS (SELECT 1 FROM empresas_empresa e WHERE e.uuid = c.empresa_uuid);

-- Verificar que RLS funciona con UUID
SET app.current_empresa_uuid = '<uuid-empresa-1>';
SELECT count(*) as visible_empresa_1 FROM inventario_producto;
RESET app.current_empresa_uuid;
```

---

## FASE 4 — RLS CON UUID

### Política RLS objetivo (post-migración completa)

```sql
-- Una vez que empresa_id sea UUID:
CREATE OR REPLACE FUNCTION get_current_empresa_id()
RETURNS UUID AS $$
BEGIN
    RETURN NULLIF(current_setting('app.current_empresa', true), '')::UUID;
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Política ejemplo
CREATE POLICY tenant_isolation ON inventario_producto
    FOR ALL
    USING (
        empresa_id = get_current_empresa_id()
        OR get_current_empresa_id() IS NULL
    );
```

### Durante la transición (empresa_id bigint + empresa_uuid coexisten)

```sql
-- Las políticas existentes siguen funcionando con bigint
-- Agregar políticas ADICIONALES con UUID para probar:
CREATE POLICY uuid_isolation ON inventario_producto
    FOR ALL
    USING (
        empresa_uuid = get_current_empresa_uuid()
        OR get_current_empresa_uuid() IS NULL
    );
```

---

## FASE 5 — MEJORES PRÁCTICAS SAAS ENTERPRISE

### 5.1 Estructura Ideal Multi-Tenant con UUID

```
┌───────────────────────────────────────────────────────────────────┐
│                    CAPAS DE SEGURIDAD                             │
├───────────────────────────────────────────────────────────────────┤
│  CAPA 1: API Gateway                                             │
│  - Rate limiting por empresa                                     │
│  - API keys con UUID de empresa embebido                         │
│  - JWT claims incluyen empresa_uuid                              │
├───────────────────────────────────────────────────────────────────┤
│  CAPA 2: Aplicación (Django)                                     │
│  - Middleware SET app.current_empresa = uuid                     │
│  - Managers con filtro automático                                │
│  - Serializers validan empresa_uuid                              │
├───────────────────────────────────────────────────────────────────┤
│  CAPA 3: Base de Datos (PostgreSQL + RLS)                        │
│  - RLS con USING (empresa_id = current_empresa::uuid)            │
│  - UUID no expone secuencias (seguridad)                         │
│  - Triggers auto-populan empresa_id                              │
├───────────────────────────────────────────────────────────────────┤
│  CAPA 4: Infraestructura                                         │
│  - SSL obligatorio                                               │
│  - Connection pooling (Supavisor session mode)                   │
│  - Backups automáticos con PITR                                  │
└───────────────────────────────────────────────────────────────────┘
```

### 5.2 Ventajas de UUID sobre Bigint

| Aspecto | Bigint | UUID |
|---------|--------|------|
| Predecibilidad | Secuencial (inseguro) | Aleatorio (seguro) |
| Exposición en URL | `/api/empresa/1/` → enumerable | `/api/empresa/a1b2c3.../` → no enumerable |
| Integraciones API | El partner puede adivinar IDs | Imposible adivinar |
| Merge de datos | Colisiones entre ambientes | Globalmente único |
| Performance INSERT | Ligeramente más rápido | ~5% más lento (aceptable) |
| Tamaño índice | 8 bytes | 16 bytes (2x, aceptable) |

### 5.3 Escalar a 1000+ Empresas

| Aspecto | Recomendación |
|---------|---------------|
| Particionamiento | `PARTITION BY HASH (empresa_id)` para tablas > 10M filas |
| Connection Pooling | Supavisor session mode (actual) |
| Read Replicas | Para reportes pesados |
| Caching | Redis para sesiones y datos frecuentes |
| Monitoring | `pg_stat_statements` + alertas en queries > 1s |
| Audit Log | Particionar por mes: `PARTITION BY RANGE (created_at)` |

### 5.4 Seguridad Adicional

```python
# JWT Claims con UUID
{
    "user_id": 1,
    "empresa_uuid": "a1b2c3d4-...",  # No expone bigint
    "role": "admin",
    "exp": 1234567890
}
```

---

## RESUMEN EJECUTIVO

| Etapa | Descripción | Riesgo | Reversible | Downtime |
|-------|-------------|--------|------------|----------|
| 1 | Agregar UUID a empresas_empresa | Cero | Sí | 0 |
| 2 | Agregar empresa_uuid a 43 tablas | Bajo | Sí | 0 |
| 3 | Poblar empresa_uuid via JOINs | Bajo | Sí | 0 |
| 4 | Crear índices UUID | Bajo | Sí | 0 |
| 5 | **Validar integridad** | — | — | 0 |
| 6 | Crear FKs UUID + NOT NULL | Medio | Difícil | 0 |
| 7 | Actualizar RLS/triggers | Medio | Difícil | 0 |
| 8 | Actualizar Django | Alto | Sí | ~5 min |
| 9 | Swap final (DROP bigint) | **Crítico** | **NO** | ~5 min |
| 10 | Verificación | — | — | 0 |

**Recomendación:** Ejecutar etapas 1-5 inmediatamente (riesgo cero).
Etapas 6-8 en staging primero. Etapa 9 solo después de 1 semana estable.

---

## ESTADO DE EJECUCIÓN

| Etapa | Estado | Fecha |
|-------|--------|-------|
| 1 | ✅ Completada | 2026-02-24 |
| 2 | ✅ Completada | 2026-02-24 |
| 3 | ✅ Completada | 2026-02-24 |
| 4 | ✅ Completada | 2026-02-24 |
| 5 | ✅ Completada (0 errores, 0 inconsistencias) | 2026-02-24 |
| 6 | ✅ Completada — 41 NOT NULL, 43 FKs UUID, UNIQUE constraint | 2026-02-08 |
| 7 | ✅ Completada — 44 políticas RLS duales, 41 triggers UUID, funciones actualizadas | 2026-02-08 |
| 8 | ✅ Completada — Middleware dual (bigint+UUID), modelo Empresa con uuid field | 2026-02-08 |
| 9 | Pendiente — Swap final (DROP bigint, renombrar empresa_uuid → empresa_id) | — |
| 10 | Pendiente — Verificación post-swap | — |

### Resumen de lo ejecutado en Etapas 6-8:

**Etapa 6:**
- `UNIQUE` constraint en `empresas_empresa.uuid`
- `NOT NULL` en `empresa_uuid` de 41 tablas (3 permanecen nullable: `authentication_customuser`, `inventario_categoria`, `audit_log`)
- 43 Foreign Keys `empresa_uuid → empresas_empresa(uuid)` creadas

**Etapa 7:**
- Función `get_current_empresa_uuid()` creada
- Función `auto_set_empresa_uuid()` creada
- 41 triggers `BEFORE INSERT` para auto-set `empresa_uuid`
- 44 políticas RLS duales (soportan tanto `app.current_empresa` bigint como `app.current_empresa_uuid` UUID)
- `audit_trigger_func()` actualizada para registrar `empresa_uuid`

**Etapa 8:**
- Campo `uuid` agregado al modelo Django `Empresa` (`UUIDField`, `editable=False`)
- Migración Django `0003_add_uuid_field` creada y aplicada con `--fake`
- `TenantMiddleware` actualizado para setear `app.current_empresa_uuid` en cada request
- Cache de UUID por empresa (1h TTL) para evitar queries extra
- `RESET app.current_empresa_uuid` agregado al cleanup
- `EmpresaSerializer` actualizado con campo `uuid` (read-only)

**Próximo paso:** Etapa 9 (swap final) solo después de 1+ semana estable con el sistema dual.

---

**Documento generado para migración enterprise UUID — 2026-02-24**
**Última actualización: 2026-02-08**
