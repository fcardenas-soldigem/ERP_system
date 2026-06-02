-- ================================================================
-- FASE 2: AGREGAR COLUMNA empresa_id A TABLAS HIJAS
-- Fecha: 2026-02-24
-- Riesgo: BAJO (columna nullable, sin datos)
-- Downtime: CERO
-- ================================================================

-- Estado actual
SELECT 'Tablas sin empresa_id antes de migración:' as info;
SELECT table_name 
FROM information_schema.tables t
WHERE table_schema = 'public' 
AND table_type = 'BASE TABLE'
AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns c 
    WHERE c.table_name = t.table_name 
    AND c.column_name = 'empresa_id'
    AND c.table_schema = 'public'
)
AND table_name NOT LIKE 'django_%'
AND table_name NOT LIKE 'auth_%'
ORDER BY table_name;

-- 2.1 Tablas de AI Assistant
ALTER TABLE ai_assistant_aiaction ADD COLUMN IF NOT EXISTS empresa_id BIGINT;
ALTER TABLE ai_assistant_message ADD COLUMN IF NOT EXISTS empresa_id BIGINT;

-- 2.2 Tablas de Compras (detalles)
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

-- VERIFICACIÓN
SELECT 'Columnas empresa_id agregadas:' as info;
SELECT table_name, column_name, is_nullable, data_type
FROM information_schema.columns 
WHERE column_name = 'empresa_id' 
AND table_schema = 'public'
ORDER BY table_name;

DO $$ 
BEGIN
    RAISE NOTICE '✅ FASE 2 COMPLETADA: Columnas empresa_id agregadas (NULLABLE)';
END $$;
