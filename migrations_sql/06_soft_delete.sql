-- ================================================================
-- FASE 6: IMPLEMENTAR SOFT DELETE
-- Fecha: 2026-02-24
-- Riesgo: BAJO (solo agrega columnas)
-- Downtime: CERO
-- ================================================================

-- 6.1 Agregar columnas de soft delete a tablas principales
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

ALTER TABLE compras_ordencompra ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE compras_ordencompra ADD COLUMN IF NOT EXISTS deleted_by BIGINT;

ALTER TABLE ventas_ordenventa ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE ventas_ordenventa ADD COLUMN IF NOT EXISTS deleted_by BIGINT;

-- 6.2 Crear índices parciales para queries de activos (muy eficientes)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_empresa_active 
ON empresas_empresa(id) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_active 
ON authentication_customuser(empresa_id) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cliente_active 
ON ventas_cliente(empresa_id) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_proveedor_active 
ON compras_proveedor(empresa_id) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_producto_active 
ON inventario_producto(empresa_id) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_almacen_active 
ON inventario_almacen(empresa_id) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_categoria_active 
ON inventario_categoria(empresa_id) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_receta_active 
ON produccion_recetaproducto(empresa_id) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_compra_active 
ON compras_compra(empresa_id) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_venta_active 
ON ventas_venta(empresa_id) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ordenproduccion_active 
ON produccion_ordenproduccion(empresa_id) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cotizacion_active 
ON cotizaciones(empresa_id) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ordencompra_active 
ON compras_ordencompra(empresa_id) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ordenventa_active 
ON ventas_ordenventa(empresa_id) WHERE deleted_at IS NULL;

-- 6.3 Funciones helper para soft delete
CREATE OR REPLACE FUNCTION soft_delete(
    p_table_name TEXT,
    p_id BIGINT,
    p_user_id BIGINT DEFAULT NULL
) RETURNS BOOLEAN AS $$
DECLARE
    v_sql TEXT;
BEGIN
    v_sql := format(
        'UPDATE %I SET deleted_at = NOW(), deleted_by = %L WHERE id = %L AND deleted_at IS NULL',
        p_table_name, p_user_id, p_id
    );
    EXECUTE v_sql;
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION restore_deleted(
    p_table_name TEXT,
    p_id BIGINT
) RETURNS BOOLEAN AS $$
DECLARE
    v_sql TEXT;
BEGIN
    v_sql := format(
        'UPDATE %I SET deleted_at = NULL, deleted_by = NULL WHERE id = %L AND deleted_at IS NOT NULL',
        p_table_name, p_id
    );
    EXECUTE v_sql;
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- VERIFICACIÓN
SELECT 'Columnas soft delete agregadas:' as info;
SELECT table_name, column_name
FROM information_schema.columns
WHERE column_name IN ('deleted_at', 'deleted_by')
AND table_schema = 'public'
ORDER BY table_name, column_name;

DO $$ 
BEGIN
    RAISE NOTICE '✅ FASE 6 COMPLETADA: Soft delete implementado';
    RAISE NOTICE '⚠️ Actualizar modelos Django con SoftDeleteManager';
END $$;
