-- ================================================================
-- FASE 5: ACTIVAR ROW LEVEL SECURITY (RLS)
-- Fecha: 2026-02-24
-- Riesgo: ALTO (afecta todas las queries)
-- IMPORTANTE: Probar en staging primero
-- ================================================================

-- 5.1 Crear función para obtener empresa_id del contexto
CREATE OR REPLACE FUNCTION get_current_empresa_id() 
RETURNS BIGINT AS $$
BEGIN
    RETURN NULLIF(current_setting('app.current_empresa', true), '')::BIGINT;
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 5.2 Activar RLS en tablas principales
-- NOTA: La condición "OR get_current_empresa_id() IS NULL" permite
-- que el superusuario y migraciones funcionen sin restricción

-- === EMPRESAS Y USUARIOS ===
ALTER TABLE empresas_empresa ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS empresa_isolation ON empresas_empresa;
CREATE POLICY empresa_isolation ON empresas_empresa
    FOR ALL
    USING (id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE authentication_customuser ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS user_isolation ON authentication_customuser;
CREATE POLICY user_isolation ON authentication_customuser
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- === CLIENTES Y PROVEEDORES ===
ALTER TABLE ventas_cliente ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS cliente_isolation ON ventas_cliente;
CREATE POLICY cliente_isolation ON ventas_cliente
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE compras_proveedor ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS proveedor_isolation ON compras_proveedor;
CREATE POLICY proveedor_isolation ON compras_proveedor
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- === INVENTARIO ===
ALTER TABLE inventario_producto ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS producto_isolation ON inventario_producto;
CREATE POLICY producto_isolation ON inventario_producto
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE inventario_stock ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS stock_isolation ON inventario_stock;
CREATE POLICY stock_isolation ON inventario_stock
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE inventario_almacen ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS almacen_isolation ON inventario_almacen;
CREATE POLICY almacen_isolation ON inventario_almacen
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE inventario_categoria ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS categoria_isolation ON inventario_categoria;
CREATE POLICY categoria_isolation ON inventario_categoria
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR empresa_id IS NULL OR get_current_empresa_id() IS NULL);

ALTER TABLE inventario_movimientoinventario ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS movimiento_isolation ON inventario_movimientoinventario;
CREATE POLICY movimiento_isolation ON inventario_movimientoinventario
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE inventario_inventariomateriasprimas ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS inv_mp_isolation ON inventario_inventariomateriasprimas;
CREATE POLICY inv_mp_isolation ON inventario_inventariomateriasprimas
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE inventario_inventarioproductosterminados ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS inv_pt_isolation ON inventario_inventarioproductosterminados;
CREATE POLICY inv_pt_isolation ON inventario_inventarioproductosterminados
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE inventario_ajusteinventario ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS ajuste_isolation ON inventario_ajusteinventario;
CREATE POLICY ajuste_isolation ON inventario_ajusteinventario
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- === COMPRAS ===
ALTER TABLE compras_compra ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS compra_isolation ON compras_compra;
CREATE POLICY compra_isolation ON compras_compra
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE compras_compradetalle ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS compradetalle_isolation ON compras_compradetalle;
CREATE POLICY compradetalle_isolation ON compras_compradetalle
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE compras_pagocompra ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pagocompra_isolation ON compras_pagocompra;
CREATE POLICY pagocompra_isolation ON compras_pagocompra
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE compras_ordencompra ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS ordencompra_isolation ON compras_ordencompra;
CREATE POLICY ordencompra_isolation ON compras_ordencompra
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE compras_ordencompradetalle ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS ordencompradetalle_isolation ON compras_ordencompradetalle;
CREATE POLICY ordencompradetalle_isolation ON compras_ordencompradetalle
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE compras_comprarecurrente ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS comprarecurrente_isolation ON compras_comprarecurrente;
CREATE POLICY comprarecurrente_isolation ON compras_comprarecurrente
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE compras_comprobantepago ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS comprobante_compra_isolation ON compras_comprobantepago;
CREATE POLICY comprobante_compra_isolation ON compras_comprobantepago
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE compras_recepcioncompra ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS recepcion_isolation ON compras_recepcioncompra;
CREATE POLICY recepcion_isolation ON compras_recepcioncompra
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- === VENTAS ===
ALTER TABLE ventas_venta ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS venta_isolation ON ventas_venta;
CREATE POLICY venta_isolation ON ventas_venta
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE ventas_detalleventa ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS detalleventa_isolation ON ventas_detalleventa;
CREATE POLICY detalleventa_isolation ON ventas_detalleventa
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE ventas_pagoventa ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pagoventa_isolation ON ventas_pagoventa;
CREATE POLICY pagoventa_isolation ON ventas_pagoventa
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE ventas_ordenventa ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS ordenventa_isolation ON ventas_ordenventa;
CREATE POLICY ordenventa_isolation ON ventas_ordenventa
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE ventas_factura ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS factura_isolation ON ventas_factura;
CREATE POLICY factura_isolation ON ventas_factura
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE ventas_comprobantepago ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS comprobante_venta_isolation ON ventas_comprobantepago;
CREATE POLICY comprobante_venta_isolation ON ventas_comprobantepago
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- === COTIZACIONES ===
ALTER TABLE cotizaciones ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS cotizacion_isolation ON cotizaciones;
CREATE POLICY cotizacion_isolation ON cotizaciones
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE detalles_cotizacion ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS detallecotizacion_isolation ON detalles_cotizacion;
CREATE POLICY detallecotizacion_isolation ON detalles_cotizacion
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- === PRODUCCIÓN ===
ALTER TABLE produccion_recetaproducto ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS receta_isolation ON produccion_recetaproducto;
CREATE POLICY receta_isolation ON produccion_recetaproducto
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE produccion_recetadetalle ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS recetadetalle_isolation ON produccion_recetadetalle;
CREATE POLICY recetadetalle_isolation ON produccion_recetadetalle
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE produccion_ordenproduccion ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS ordenproduccion_isolation ON produccion_ordenproduccion;
CREATE POLICY ordenproduccion_isolation ON produccion_ordenproduccion
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE produccion_consumoreal ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS consumoreal_isolation ON produccion_consumoreal;
CREATE POLICY consumoreal_isolation ON produccion_consumoreal
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE produccion_historialordenproduccion ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS historialorden_isolation ON produccion_historialordenproduccion;
CREATE POLICY historialorden_isolation ON produccion_historialordenproduccion
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE produccion_productioncost ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS productioncost_isolation ON produccion_productioncost;
CREATE POLICY productioncost_isolation ON produccion_productioncost
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE produccion_productionoutput ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS productionoutput_isolation ON produccion_productionoutput;
CREATE POLICY productionoutput_isolation ON produccion_productionoutput
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE produccion_productionwaste ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS productionwaste_isolation ON produccion_productionwaste;
CREATE POLICY productionwaste_isolation ON produccion_productionwaste
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- === ML MODELS ===
ALTER TABLE ml_models_mlmodel ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS mlmodel_isolation ON ml_models_mlmodel;
CREATE POLICY mlmodel_isolation ON ml_models_mlmodel
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE ml_models_trainingjob ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS trainingjob_isolation ON ml_models_trainingjob;
CREATE POLICY trainingjob_isolation ON ml_models_trainingjob
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- === AI ASSISTANT ===
ALTER TABLE ai_assistant_conversation ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS conversation_isolation ON ai_assistant_conversation;
CREATE POLICY conversation_isolation ON ai_assistant_conversation
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE ai_assistant_aiinsight ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS aiinsight_isolation ON ai_assistant_aiinsight;
CREATE POLICY aiinsight_isolation ON ai_assistant_aiinsight
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE ai_assistant_aiaction ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS aiaction_isolation ON ai_assistant_aiaction;
CREATE POLICY aiaction_isolation ON ai_assistant_aiaction
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE ai_assistant_message ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS aimessage_isolation ON ai_assistant_message;
CREATE POLICY aimessage_isolation ON ai_assistant_message
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- === CORE ===
ALTER TABLE core_usuario ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS coreusuario_isolation ON core_usuario;
CREATE POLICY coreusuario_isolation ON core_usuario
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

ALTER TABLE core_perfil ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS perfil_isolation ON core_perfil;
CREATE POLICY perfil_isolation ON core_perfil
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- ================================================================
-- VERIFICACIÓN DE RLS
-- ================================================================
SELECT 'Tablas con RLS activado:' as info;
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
AND rowsecurity = true
ORDER BY tablename;

SELECT 'Políticas RLS creadas:' as info;
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd
FROM pg_policies 
WHERE schemaname = 'public'
ORDER BY tablename;

DO $$ 
BEGIN
    RAISE NOTICE '✅ FASE 5 COMPLETADA: RLS activado en todas las tablas multi-tenant';
    RAISE NOTICE '⚠️ IMPORTANTE: Configurar middleware Django para setear app.current_empresa';
END $$;
