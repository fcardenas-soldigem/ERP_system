-- ================================================================
-- FASE 4: CREAR ÍNDICES ESTRATÉGICOS
-- Fecha: 2026-02-24
-- Riesgo: BAJO (operación CONCURRENTLY no bloquea)
-- Downtime: CERO
-- ================================================================

-- 4.1 Índices en empresa_id para tablas recién actualizadas
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_aiaction_empresa 
ON ai_assistant_aiaction(empresa_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_message_empresa 
ON ai_assistant_message(empresa_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_compradetalle_empresa 
ON compras_compradetalle(empresa_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comprobantepago_compra_empresa 
ON compras_comprobantepago(empresa_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ordencompradetalle_empresa 
ON compras_ordencompradetalle(empresa_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pagocompra_empresa 
ON compras_pagocompra(empresa_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recepcioncompra_empresa 
ON compras_recepcioncompra(empresa_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_perfil_empresa 
ON core_perfil(empresa_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_detallecotizacion_empresa 
ON detalles_cotizacion(empresa_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ajusteinventario_empresa 
ON inventario_ajusteinventario(empresa_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_consumoreal_empresa 
ON produccion_consumoreal(empresa_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_historialorden_empresa 
ON produccion_historialordenproduccion(empresa_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_productioncost_empresa 
ON produccion_productioncost(empresa_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_productionoutput_empresa 
ON produccion_productionoutput(empresa_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_productionwaste_empresa 
ON produccion_productionwaste(empresa_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recetadetalle_empresa 
ON produccion_recetadetalle(empresa_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comprobantepago_venta_empresa 
ON ventas_comprobantepago(empresa_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_detalleventa_empresa 
ON ventas_detalleventa(empresa_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_factura_empresa 
ON ventas_factura(empresa_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pagoventa_empresa 
ON ventas_pagoventa(empresa_id);

-- 4.2 Índices compuestos para REPORTES (empresa + fecha)
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

-- 4.3 Índices para búsquedas frecuentes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_producto_empresa_sku 
ON inventario_producto(empresa_id, sku);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cliente_empresa_doc 
ON ventas_cliente(empresa_id, documento);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_proveedor_empresa_ruc_idx
ON compras_proveedor(empresa_id, ruc);

-- 4.4 Índices para fechas de creación (ordenamiento)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_compra_created 
ON compras_compra(created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_venta_created 
ON ventas_venta(fecha_creacion DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cotizacion_created 
ON cotizaciones(fecha_creacion DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orden_created 
ON produccion_ordenproduccion(created_at DESC);

-- VERIFICACIÓN
SELECT 'Índices creados:' as info;
SELECT 
    tablename,
    indexname
FROM pg_indexes
WHERE schemaname = 'public'
AND (indexname LIKE 'idx_%' OR indexname LIKE '%empresa%')
ORDER BY tablename, indexname;

DO $$ 
BEGIN
    RAISE NOTICE '✅ FASE 4 COMPLETADA: Índices estratégicos creados';
END $$;
