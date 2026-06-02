-- ================================================================
-- FASE 3: POBLAR empresa_id USANDO JOINS CON TABLAS PADRE
-- Fecha: 2026-02-24
-- Riesgo: MEDIO (modifica datos existentes)
-- Downtime: CERO (operaciones en background)
-- IMPORTANTE: Ejecutar cada bloque BEGIN/COMMIT por separado
-- ================================================================

-- 3.1 AI Assistant - Actions via Conversation
BEGIN;
UPDATE ai_assistant_aiaction aa
SET empresa_id = ac.empresa_id
FROM ai_assistant_conversation ac
WHERE aa.conversation_id = ac.id
AND aa.empresa_id IS NULL;
COMMIT;

-- 3.2 AI Assistant - Messages via Conversation
BEGIN;
UPDATE ai_assistant_message am
SET empresa_id = ac.empresa_id
FROM ai_assistant_conversation ac
WHERE am.conversation_id = ac.id
AND am.empresa_id IS NULL;
COMMIT;

-- 3.3 Compras - Detalles via Compra
BEGIN;
UPDATE compras_compradetalle cd
SET empresa_id = c.empresa_id
FROM compras_compra c
WHERE cd.compra_id = c.id
AND cd.empresa_id IS NULL;
COMMIT;

-- 3.4 Compras - Comprobante via Compra
BEGIN;
UPDATE compras_comprobantepago cp
SET empresa_id = c.empresa_id
FROM compras_compra c
WHERE cp.compra_id = c.id
AND cp.empresa_id IS NULL;
COMMIT;

-- 3.5 Compras - Pagos via Compra
BEGIN;
UPDATE compras_pagocompra pc
SET empresa_id = c.empresa_id
FROM compras_compra c
WHERE pc.compra_id = c.id
AND pc.empresa_id IS NULL;
COMMIT;

-- 3.6 Compras - Orden Detalle via Orden
BEGIN;
UPDATE compras_ordencompradetalle od
SET empresa_id = o.empresa_id
FROM compras_ordencompra o
WHERE od.orden_id = o.id
AND od.empresa_id IS NULL;
COMMIT;

-- 3.7 Compras - Recepción via Orden
BEGIN;
UPDATE compras_recepcioncompra rc
SET empresa_id = o.empresa_id
FROM compras_ordencompra o
WHERE rc.orden_id = o.id
AND rc.empresa_id IS NULL;
COMMIT;

-- 3.8 Core - Perfil via Usuario
BEGIN;
UPDATE core_perfil cp
SET empresa_id = cu.empresa_id
FROM authentication_customuser cu
WHERE cp.usuario_id = cu.id
AND cp.empresa_id IS NULL
AND cu.empresa_id IS NOT NULL;
COMMIT;

-- 3.9 Cotizaciones - Detalles via Cotización
BEGIN;
UPDATE detalles_cotizacion dc
SET empresa_id = c.empresa_id
FROM cotizaciones c
WHERE dc.cotizacion_id = c.id
AND dc.empresa_id IS NULL;
COMMIT;

-- 3.10 Inventario - Ajuste via Almacén
BEGIN;
UPDATE inventario_ajusteinventario ai
SET empresa_id = a.empresa_id
FROM inventario_almacen a
WHERE ai.almacen_id = a.id
AND ai.empresa_id IS NULL;
COMMIT;

-- 3.11 Producción - Consumo Real via Orden Producción
BEGIN;
UPDATE produccion_consumoreal cr
SET empresa_id = op.empresa_id
FROM produccion_ordenproduccion op
WHERE cr.orden_produccion_id = op.id
AND cr.empresa_id IS NULL;
COMMIT;

-- 3.12 Producción - Historial via Orden Producción
BEGIN;
UPDATE produccion_historialordenproduccion hp
SET empresa_id = op.empresa_id
FROM produccion_ordenproduccion op
WHERE hp.orden_id = op.id
AND hp.empresa_id IS NULL;
COMMIT;

-- 3.13 Producción - Costo via Orden Producción
BEGIN;
UPDATE produccion_productioncost pc
SET empresa_id = op.empresa_id
FROM produccion_ordenproduccion op
WHERE pc.orden_produccion_id = op.id
AND pc.empresa_id IS NULL;
COMMIT;

-- 3.14 Producción - Output via Orden Producción
BEGIN;
UPDATE produccion_productionoutput po
SET empresa_id = op.empresa_id
FROM produccion_ordenproduccion op
WHERE po.orden_produccion_id = op.id
AND po.empresa_id IS NULL;
COMMIT;

-- 3.15 Producción - Waste via Orden Producción
BEGIN;
UPDATE produccion_productionwaste pw
SET empresa_id = op.empresa_id
FROM produccion_ordenproduccion op
WHERE pw.orden_produccion_id = op.id
AND pw.empresa_id IS NULL;
COMMIT;

-- 3.16 Producción - Receta Detalle via Receta
BEGIN;
UPDATE produccion_recetadetalle rd
SET empresa_id = rp.empresa_id
FROM produccion_recetaproducto rp
WHERE rd.receta_id = rp.id
AND rd.empresa_id IS NULL;
COMMIT;

-- 3.17 Ventas - Comprobante via Venta
BEGIN;
UPDATE ventas_comprobantepago vc
SET empresa_id = v.empresa_id
FROM ventas_venta v
WHERE vc.venta_id = v.id
AND vc.empresa_id IS NULL;
COMMIT;

-- 3.18 Ventas - Detalle via Venta
BEGIN;
UPDATE ventas_detalleventa dv
SET empresa_id = v.empresa_id
FROM ventas_venta v
WHERE dv.venta_id = v.id
AND dv.empresa_id IS NULL;
COMMIT;

-- 3.19 Ventas - Factura via Venta
BEGIN;
UPDATE ventas_factura vf
SET empresa_id = v.empresa_id
FROM ventas_venta v
WHERE vf.venta_id = v.id
AND vf.empresa_id IS NULL;
COMMIT;

-- 3.20 Ventas - Pago via Venta
BEGIN;
UPDATE ventas_pagoventa pv
SET empresa_id = v.empresa_id
FROM ventas_venta v
WHERE pv.venta_id = v.id
AND pv.empresa_id IS NULL;
COMMIT;

-- ================================================================
-- VERIFICACIÓN CRÍTICA: NO debe haber registros sin empresa_id
-- ================================================================
SELECT 'VERIFICACIÓN - Registros sin empresa_id (debe ser 0):' as info;
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
UNION ALL SELECT 'ventas_pagoventa', COUNT(*) FROM ventas_pagoventa WHERE empresa_id IS NULL
ORDER BY sin_empresa DESC;

DO $$ 
BEGIN
    RAISE NOTICE '✅ FASE 3 COMPLETADA: empresa_id poblado';
    RAISE NOTICE '⚠️ VERIFICAR que todos los conteos sean 0 antes de continuar';
END $$;
