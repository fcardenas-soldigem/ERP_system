# 📊 TABLAS DE PRODUCCIÓN EN POSTGRESQL

## Resumen de Tablas a Crear

Se crearán **9 tablas** en PostgreSQL para el módulo de producción completo:

---

## 1️⃣ PRODUCTOS (Actualización)

**Tabla:** `inventario_producto`  
**Acción:** Se agrega campo nuevo

```sql
ALTER TABLE inventario_producto 
ADD COLUMN tipo_producto VARCHAR(20) DEFAULT 'RAW';

-- Valores posibles:
-- 'RAW' = Materia Prima / Insumo
-- 'SEMIFINISHED' = Semi-Terminado  
-- 'FINISHED' = Producto Terminado
```

---

## 2️⃣ RECETA DE PRODUCCIÓN (BOM)

**Tabla:** `produccion_recetaproducto`

```sql
CREATE TABLE produccion_recetaproducto (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas_empresa(id),
    producto_terminado_id BIGINT NOT NULL REFERENCES inventario_producto(id),
    nombre VARCHAR(200) NOT NULL,
    cantidad_producida DECIMAL(10,2) DEFAULT 1,
    tiempo_estimado INTEGER DEFAULT 0,  -- minutos
    costo_mano_obra DECIMAL(10,2) DEFAULT 0,
    costo_indirecto DECIMAL(10,2) DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    version INTEGER DEFAULT 1,
    notas TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_empresa_producto_version 
        UNIQUE (empresa_id, producto_terminado_id, version)
);

-- Índices
CREATE INDEX idx_receta_empresa ON produccion_recetaproducto(empresa_id);
CREATE INDEX idx_receta_producto ON produccion_recetaproducto(producto_terminado_id);
CREATE INDEX idx_receta_active ON produccion_recetaproducto(is_active);
```

**Campos clave:**
- ✅ `producto_terminado_id` - Qué se produce
- ✅ `cantidad_producida` - Cantidad estándar del lote
- ✅ `tiempo_estimado` - Minutos estimados
- ✅ `version` - Control de versiones de recetas
- ✅ `is_active` - Solo recetas activas se pueden usar

---

## 3️⃣ DETALLE DE RECETA (Insumos)

**Tabla:** `produccion_recetadetalle`

```sql
CREATE TABLE produccion_recetadetalle (
    id BIGSERIAL PRIMARY KEY,
    receta_id BIGINT NOT NULL REFERENCES produccion_recetaproducto(id) ON DELETE CASCADE,
    insumo_id BIGINT NOT NULL REFERENCES inventario_producto(id),
    cantidad DECIMAL(10,2) NOT NULL,
    unidad_medida VARCHAR(20) NOT NULL,
    costo_unitario DECIMAL(10,2) DEFAULT 0,
    notas TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_receta_insumo UNIQUE (receta_id, insumo_id)
);

-- Índices
CREATE INDEX idx_detalle_receta ON produccion_recetadetalle(receta_id);
CREATE INDEX idx_detalle_insumo ON produccion_recetadetalle(insumo_id);
```

**Campos clave:**
- ✅ `insumo_id` - Producto usado como insumo
- ✅ `cantidad` - Cantidad necesaria
- ✅ `costo_unitario` - Snapshot del costo al crear receta

---

## 4️⃣ ORDEN DE PRODUCCIÓN

**Tabla:** `produccion_ordenproduccion`

```sql
CREATE TABLE produccion_ordenproduccion (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas_empresa(id),
    numero VARCHAR(20) UNIQUE NOT NULL,  -- Auto-generado
    receta_id BIGINT NOT NULL REFERENCES produccion_recetaproducto(id),
    
    -- PLANIFICADO (no se sobrescribe)
    cantidad_planificada DECIMAL(10,2) NOT NULL,
    fecha_programada DATE NOT NULL,
    
    -- REAL (se actualiza durante ejecución)
    cantidad_producida DECIMAL(10,2) DEFAULT 0,
    fecha_inicio TIMESTAMP WITH TIME ZONE,
    fecha_fin TIMESTAMP WITH TIME ZONE,
    tiempo_real INTEGER DEFAULT 0,  -- minutos
    
    -- Almacenes
    almacen_insumos_id BIGINT NOT NULL REFERENCES inventario_almacen(id),
    almacen_destino_id BIGINT NOT NULL REFERENCES inventario_almacen(id),
    
    -- Estado
    estado VARCHAR(20) DEFAULT 'pendiente',
    -- Valores: 'pendiente', 'en_proceso', 'finalizada', 'cancelada'
    
    -- Costos reales
    costo_mano_obra_real DECIMAL(10,2) DEFAULT 0,
    costo_indirecto_real DECIMAL(10,2) DEFAULT 0,
    
    -- Usuarios
    responsable_id BIGINT REFERENCES auth_user(id),
    created_by_id BIGINT REFERENCES auth_user(id),
    
    observaciones TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_orden_empresa ON produccion_ordenproduccion(empresa_id);
CREATE INDEX idx_orden_estado ON produccion_ordenproduccion(estado);
CREATE INDEX idx_orden_fecha_prog ON produccion_ordenproduccion(fecha_programada);
CREATE INDEX idx_orden_receta ON produccion_ordenproduccion(receta_id);
CREATE INDEX idx_orden_numero ON produccion_ordenproduccion(numero);
```

**Principio clave:** 
✅ **`cantidad_planificada` ≠ `cantidad_producida`**  
✅ Lo planificado NUNCA se sobrescribe

---

## 5️⃣ CONSUMO REAL DE INSUMOS

**Tabla:** `produccion_consumoreal`

```sql
CREATE TABLE produccion_consumoreal (
    id BIGSERIAL PRIMARY KEY,
    orden_produccion_id BIGINT NOT NULL REFERENCES produccion_ordenproduccion(id) ON DELETE CASCADE,
    insumo_id BIGINT NOT NULL REFERENCES inventario_producto(id),
    
    -- Teórico vs Real
    cantidad_teorica DECIMAL(10,2) NOT NULL,  -- Según receta
    cantidad_real DECIMAL(10,2) DEFAULT 0,    -- Lo que se usó realmente
    merma DECIMAL(10,2) DEFAULT 0,            -- Desperdicio
    
    costo_unitario DECIMAL(10,2) NOT NULL,
    notas TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_orden_insumo UNIQUE (orden_produccion_id, insumo_id)
);

-- Índices
CREATE INDEX idx_consumo_orden ON produccion_consumoreal(orden_produccion_id);
CREATE INDEX idx_consumo_insumo ON produccion_consumoreal(insumo_id);
```

**Cálculos automáticos (properties):**
- `diferencia = cantidad_real - cantidad_teorica`
- `porcentaje_diferencia = (diferencia / cantidad_teorica) * 100`
- `costo_total = cantidad_real * costo_unitario`
- `costo_merma = merma * costo_unitario`

---

## 6️⃣ PRODUCCIÓN PARCIAL / LOTES

**Tabla:** `produccion_productionoutput`

```sql
CREATE TABLE produccion_productionoutput (
    id BIGSERIAL PRIMARY KEY,
    orden_produccion_id BIGINT NOT NULL REFERENCES produccion_ordenproduccion(id) ON DELETE CASCADE,
    cantidad_producida DECIMAL(10,2) NOT NULL,
    numero_lote VARCHAR(50),
    fecha_produccion TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notas TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_output_orden ON produccion_productionoutput(orden_produccion_id);
CREATE INDEX idx_output_lote ON produccion_productionoutput(numero_lote);
CREATE INDEX idx_output_fecha ON produccion_productionoutput(fecha_produccion);
```

**Uso:**  
✅ Permite cierres parciales  
✅ Útil para producción continua  
✅ Trazabilidad por lotes

---

## 7️⃣ MERMAS Y DESPERDICIOS

**Tabla:** `produccion_productionwaste`

```sql
CREATE TABLE produccion_productionwaste (
    id BIGSERIAL PRIMARY KEY,
    orden_produccion_id BIGINT NOT NULL REFERENCES produccion_ordenproduccion(id) ON DELETE CASCADE,
    producto_id BIGINT NOT NULL REFERENCES inventario_producto(id),
    cantidad_desperdiciada DECIMAL(10,2) NOT NULL,
    motivo VARCHAR(20) DEFAULT 'PROCESS',
    -- Valores: 'PROCESS', 'DAMAGED', 'EXPIRED', 'OTHER'
    costo_unitario DECIMAL(10,2) DEFAULT 0,
    descripcion TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_waste_orden ON produccion_productionwaste(orden_produccion_id);
CREATE INDEX idx_waste_producto ON produccion_productionwaste(producto_id);
CREATE INDEX idx_waste_motivo ON produccion_productionwaste(motivo);
CREATE INDEX idx_waste_fecha ON produccion_productionwaste(created_at);
```

**Cálculo:**
- `costo_total_merma = cantidad_desperdiciada * costo_unitario`

---

## 8️⃣ COSTEO DE PRODUCCIÓN (Snapshot)

**Tabla:** `produccion_productioncost`

```sql
CREATE TABLE produccion_productioncost (
    id BIGSERIAL PRIMARY KEY,
    orden_produccion_id BIGINT UNIQUE NOT NULL REFERENCES produccion_ordenproduccion(id) ON DELETE CASCADE,
    
    -- Costos detallados
    costo_materiales DECIMAL(12,2) DEFAULT 0,    -- Insumos
    costo_mano_obra DECIMAL(12,2) DEFAULT 0,     -- MOD
    costo_indirecto DECIMAL(12,2) DEFAULT 0,     -- CIF
    costo_mermas DECIMAL(12,2) DEFAULT 0,        -- Desperdicios
    
    -- Totales
    costo_total DECIMAL(12,2) DEFAULT 0,
    costo_unitario DECIMAL(12,4) DEFAULT 0,
    cantidad_producida DECIMAL(10,2) DEFAULT 0,
    
    notas TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_cost_orden ON produccion_productioncost(orden_produccion_id);
CREATE INDEX idx_cost_fecha ON produccion_productioncost(created_at);
```

**Cálculos:**
```sql
costo_total = costo_materiales + costo_mano_obra + costo_indirecto + costo_mermas
costo_unitario = costo_total / cantidad_producida
```

---

## 9️⃣ MOVIMIENTOS DE INVENTARIO (Integración)

**Tabla:** `inventario_movimientoinventario` (Ya existe, se usa)

```sql
-- Esta tabla YA EXISTE en el sistema
-- Se usa para registrar:

-- SALIDA (OUT) → Consumo de insumos
INSERT INTO inventario_movimientoinventario (
    tipo_movimiento, 
    motivo,
    reference
) VALUES (
    'salida', 
    'produccion',
    'OP-000001'
);

-- ENTRADA (IN) → Ingreso de producto terminado  
INSERT INTO inventario_movimientoinventario (
    tipo_movimiento,
    motivo, 
    reference
) VALUES (
    'entrada',
    'produccion',
    'OP-000001'
);
```

---

## 🔄 RELACIONES ENTRE TABLAS

```
empresas_empresa
  ├─ produccion_recetaproduccion
  └─ produccion_ordenproduccion

inventario_producto (con tipo_producto)
  ├─ produccion_recetaproducto (producto_terminado)
  ├─ produccion_recetadetalle (insumo)
  ├─ produccion_consumoreal (insumo)
  └─ produccion_productionwaste (producto)

produccion_recetaproducto
  ├─ produccion_recetadetalle
  └─ produccion_ordenproduccion

produccion_ordenproduccion
  ├─ produccion_consumoreal
  ├─ produccion_productionoutput
  ├─ produccion_productionwaste
  ├─ produccion_productioncost (1:1)
  └─ inventario_movimientoinventario

inventario_almacen
  ├─ produccion_ordenproduccion (almacen_insumos)
  └─ produccion_ordenproduccion (almacen_destino)

auth_user
  ├─ produccion_ordenproduccion (responsable)
  └─ produccion_ordenproduccion (created_by)
```

---

## 📊 ESTADÍSTICAS ESPERADAS

Después de crear las tablas:

| Tabla | Filas Esperadas (mes) | Uso |
|-------|----------------------|-----|
| `produccion_recetaproducto` | 10-50 | Baja escritura |
| `produccion_recetadetalle` | 50-500 | Baja escritura |
| `produccion_ordenproduccion` | 100-1000 | Media escritura |
| `produccion_consumoreal` | 500-5000 | Alta escritura |
| `produccion_productionoutput` | 100-1000 | Media escritura |
| `produccion_productionwaste` | 50-500 | Baja-Media |
| `produccion_productioncost` | 100-1000 | Media (1:1 con órdenes) |

---

## ✅ PRINCIPIOS IMPLEMENTADOS

1. ✅ **Separación plan vs realidad**
   - `cantidad_planificada` ≠ `cantidad_producida`
   - `fecha_programada` ≠ `fecha_inicio` / `fecha_fin`
   - `tiempo_estimado` ≠ `tiempo_real`

2. ✅ **Impacto en inventario y costos**
   - Automático via `inventario_movimientoinventario`
   - Actualización de `inventario_stock`
   - Snapshot en `produccion_productioncost`

3. ✅ **Simple hoy, extensible mañana**
   - Versionado de recetas
   - Producción parcial/lotes
   - Múltiples tipos de mermas
   - Costos detallados

---

## 🚀 COMANDOS DE MIGRACIÓN

```bash
cd /Users/renatocardenas/.cursor/worktrees/ERP_system/hps/backend

# 1. Crear migraciones
python3 manage.py makemigrations inventario
python3 manage.py makemigrations produccion

# 2. Ver SQL que se ejecutará (opcional)
python3 manage.py sqlmigrate produccion 0001

# 3. Aplicar migraciones
python3 manage.py migrate

# 4. Verificar tablas creadas
python3 manage.py dbshell
\dt produccion_*
```

---

## 🎯 RESULTADO FINAL

**9 tablas** funcionando en PostgreSQL:

1. ✅ `inventario_producto` (actualizada con tipo_producto)
2. ✅ `produccion_recetaproducto`
3. ✅ `produccion_recetadetalle`
4. ✅ `produccion_ordenproduccion`
5. ✅ `produccion_consumoreal`
6. ✅ `produccion_productionoutput`
7. ✅ `produccion_productionwaste`
8. ✅ `produccion_productioncost`
9. ✅ `inventario_movimientoinventario` (integración)

**Total de campos: ~80 campos** distribuidos en estas tablas.

---

**Fecha:** Diciembre 2025  
**Base de Datos:** PostgreSQL  
**ORM:** Django 4.x  
**Estado:** ✅ Listo para migrar
