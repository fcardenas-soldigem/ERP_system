-- ================================================================
-- FASE 7: CREAR CHECK CONSTRAINTS PARA ESTADOS
-- Fecha: 2026-02-24
-- Riesgo: MEDIO (puede rechazar datos inválidos existentes)
-- NOTA: Usamos CHECK en lugar de ENUM por mejor compatibilidad Django
-- ================================================================

-- 7.1 Estados de documentos (compras, ventas, cotizaciones)
ALTER TABLE compras_compra DROP CONSTRAINT IF EXISTS chk_compra_estado;
ALTER TABLE compras_compra ADD CONSTRAINT chk_compra_estado 
CHECK (estado IN ('borrador', 'pendiente', 'aprobada', 'pagada', 'parcial', 'cancelada', 'anulada'));

ALTER TABLE ventas_venta DROP CONSTRAINT IF EXISTS chk_venta_estado;
ALTER TABLE ventas_venta ADD CONSTRAINT chk_venta_estado 
CHECK (estado IN ('borrador', 'pendiente', 'aprobada', 'pagada', 'parcial', 'cancelada', 'anulada'));

ALTER TABLE compras_ordencompra DROP CONSTRAINT IF EXISTS chk_ordencompra_estado;
ALTER TABLE compras_ordencompra ADD CONSTRAINT chk_ordencompra_estado 
CHECK (estado IN ('borrador', 'pendiente', 'aprobada', 'enviada', 'recibida', 'cancelada'));

ALTER TABLE ventas_ordenventa DROP CONSTRAINT IF EXISTS chk_ordenventa_estado;
ALTER TABLE ventas_ordenventa ADD CONSTRAINT chk_ordenventa_estado 
CHECK (estado IN ('borrador', 'pendiente', 'confirmada', 'en_proceso', 'enviada', 'entregada', 'cancelada'));

ALTER TABLE cotizaciones DROP CONSTRAINT IF EXISTS chk_cotizacion_estado;
ALTER TABLE cotizaciones ADD CONSTRAINT chk_cotizacion_estado 
CHECK (estado IN ('borrador', 'enviada', 'aceptada', 'rechazada', 'vencida', 'convertida'));

-- 7.2 Estados de producción
ALTER TABLE produccion_ordenproduccion DROP CONSTRAINT IF EXISTS chk_ordenproduccion_estado;
ALTER TABLE produccion_ordenproduccion ADD CONSTRAINT chk_ordenproduccion_estado 
CHECK (estado IN ('borrador', 'pendiente', 'en_proceso', 'pausada', 'completada', 'cancelada'));

-- 7.3 Tipos de compra
ALTER TABLE compras_compra DROP CONSTRAINT IF EXISTS chk_tipo_compra;
ALTER TABLE compras_compra ADD CONSTRAINT chk_tipo_compra 
CHECK (tipo_compra IN ('contado', 'credito_15', 'credito_30', 'credito_45', 'credito_60', 'credito_90'));

-- 7.4 Métodos de pago
ALTER TABLE compras_compra DROP CONSTRAINT IF EXISTS chk_metodo_pago_compra;
ALTER TABLE compras_compra ADD CONSTRAINT chk_metodo_pago_compra 
CHECK (metodo_pago IN ('efectivo', 'transferencia', 'tarjeta_credito', 'tarjeta_debito', 'cheque', 'pendiente', 'otro'));

ALTER TABLE compras_pagocompra DROP CONSTRAINT IF EXISTS chk_metodo_pago_pagocompra;
ALTER TABLE compras_pagocompra ADD CONSTRAINT chk_metodo_pago_pagocompra 
CHECK (metodo_pago IN ('efectivo', 'transferencia', 'tarjeta_credito', 'tarjeta_debito', 'cheque', 'otro'));

ALTER TABLE ventas_pagoventa DROP CONSTRAINT IF EXISTS chk_metodo_pago_pagoventa;
ALTER TABLE ventas_pagoventa ADD CONSTRAINT chk_metodo_pago_pagoventa 
CHECK (metodo_pago IN ('efectivo', 'transferencia', 'tarjeta_credito', 'tarjeta_debito', 'cheque', 'otro'));

-- 7.5 Monedas
ALTER TABLE compras_compra DROP CONSTRAINT IF EXISTS chk_moneda_compra;
ALTER TABLE compras_compra ADD CONSTRAINT chk_moneda_compra 
CHECK (moneda IS NULL OR moneda IN ('PEN', 'USD', 'EUR'));

ALTER TABLE ventas_venta DROP CONSTRAINT IF EXISTS chk_moneda_venta;
ALTER TABLE ventas_venta ADD CONSTRAINT chk_moneda_venta 
CHECK (moneda IN ('PEN', 'USD', 'EUR'));

ALTER TABLE cotizaciones DROP CONSTRAINT IF EXISTS chk_moneda_cotizacion;
ALTER TABLE cotizaciones ADD CONSTRAINT chk_moneda_cotizacion 
CHECK (moneda IN ('PEN', 'USD', 'EUR'));

-- 7.6 Tipos de producto
ALTER TABLE inventario_producto DROP CONSTRAINT IF EXISTS chk_tipo_producto;
ALTER TABLE inventario_producto ADD CONSTRAINT chk_tipo_producto 
CHECK (tipo_producto IN ('materia_prima', 'producto_terminado', 'insumo', 'servicio', 'consumible'));

-- 7.7 Tipos de movimiento de inventario
ALTER TABLE inventario_movimientoinventario DROP CONSTRAINT IF EXISTS chk_tipo_movimiento;
ALTER TABLE inventario_movimientoinventario ADD CONSTRAINT chk_tipo_movimiento 
CHECK (tipo_movimiento IN (
    'entrada', 'salida', 
    'ajuste_positivo', 'ajuste_negativo', 
    'transferencia_entrada', 'transferencia_salida',
    'produccion_consumo', 'produccion_output',
    'compra', 'venta', 'devolucion'
));

-- 7.8 Tipos de evento de producción
ALTER TABLE produccion_historialordenproduccion DROP CONSTRAINT IF EXISTS chk_tipo_evento;
ALTER TABLE produccion_historialordenproduccion ADD CONSTRAINT chk_tipo_evento 
CHECK (tipo_evento IN (
    'creacion', 'inicio', 'pausa', 'reanudacion', 
    'actualizacion_progreso', 'finalizacion', 'cancelacion', 'otro'
));

-- 7.9 Frecuencia de compras recurrentes
ALTER TABLE compras_comprarecurrente DROP CONSTRAINT IF EXISTS chk_frecuencia;
ALTER TABLE compras_comprarecurrente ADD CONSTRAINT chk_frecuencia 
CHECK (frecuencia IN ('diario', 'semanal', 'quincenal', 'mensual', 'bimestral', 'trimestral', 'semestral', 'anual'));

-- 7.10 Tipos de documento
ALTER TABLE ventas_cliente DROP CONSTRAINT IF EXISTS chk_tipo_documento_cliente;
ALTER TABLE ventas_cliente ADD CONSTRAINT chk_tipo_documento_cliente 
CHECK (tipo_documento IN ('DNI', 'RUC', 'CE', 'PASAPORTE', 'OTRO'));

-- VERIFICACIÓN
SELECT 'CHECK constraints creados:' as info;
SELECT 
    tc.table_name,
    tc.constraint_name,
    cc.check_clause
FROM information_schema.table_constraints tc
JOIN information_schema.check_constraints cc 
    ON tc.constraint_name = cc.constraint_name
WHERE tc.constraint_type = 'CHECK'
AND tc.table_schema = 'public'
AND tc.constraint_name LIKE 'chk_%'
ORDER BY tc.table_name;

DO $$ 
BEGIN
    RAISE NOTICE '✅ FASE 7 COMPLETADA: CHECK constraints para estados creados';
    RAISE NOTICE '⚠️ Actualizar choices en modelos Django para coincidir';
END $$;
