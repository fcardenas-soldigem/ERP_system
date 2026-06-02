-- ================================================================
-- FASE 1: CORREGIR TIPOS DE FK INCONSISTENTES
-- Fecha: 2026-02-24
-- Riesgo: BAJO (cambio de tipo compatible)
-- Downtime: ~1 minuto por tabla
-- ================================================================

-- BACKUP: Verificar estado actual antes de ejecutar
SELECT 'ESTADO ACTUAL - FK Types' as info;
SELECT table_name, column_name, data_type 
FROM information_schema.columns 
WHERE column_name IN ('compra_id', 'venta_id', 'ajuste_id', 'orden_produccion_id')
AND table_name = 'inventario_movimientoinventario'
AND table_schema = 'public';

-- 1.1 inventario_movimientoinventario.compra_id (integer → bigint)
DO $$ 
BEGIN
    RAISE NOTICE 'Cambiando compra_id a bigint...';
END $$;
ALTER TABLE inventario_movimientoinventario 
ALTER COLUMN compra_id TYPE bigint;

-- 1.2 inventario_movimientoinventario.venta_id (integer → bigint)
DO $$ 
BEGIN
    RAISE NOTICE 'Cambiando venta_id a bigint...';
END $$;
ALTER TABLE inventario_movimientoinventario 
ALTER COLUMN venta_id TYPE bigint;

-- 1.3 inventario_movimientoinventario.ajuste_id (integer → bigint)
DO $$ 
BEGIN
    RAISE NOTICE 'Cambiando ajuste_id a bigint...';
END $$;
ALTER TABLE inventario_movimientoinventario 
ALTER COLUMN ajuste_id TYPE bigint;

-- 1.4 inventario_movimientoinventario.orden_produccion_id (integer → bigint)
DO $$ 
BEGIN
    RAISE NOTICE 'Cambiando orden_produccion_id en movimientoinventario a bigint...';
END $$;
ALTER TABLE inventario_movimientoinventario 
ALTER COLUMN orden_produccion_id TYPE bigint;

-- 1.5 inventario_inventarioproductosterminados.orden_produccion_id (integer → bigint)
DO $$ 
BEGIN
    RAISE NOTICE 'Cambiando orden_produccion_id en productosterminados a bigint...';
END $$;
ALTER TABLE inventario_inventarioproductosterminados 
ALTER COLUMN orden_produccion_id TYPE bigint;

-- VERIFICACIÓN FINAL
SELECT 'ESTADO FINAL - FK Types' as info;
SELECT table_name, column_name, data_type 
FROM information_schema.columns 
WHERE column_name IN ('compra_id', 'venta_id', 'ajuste_id', 'orden_produccion_id')
AND table_schema = 'public'
ORDER BY table_name, column_name;

DO $$ 
BEGIN
    RAISE NOTICE '✅ FASE 1 COMPLETADA: FK types corregidos';
END $$;
