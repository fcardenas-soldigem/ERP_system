-- ================================================================
-- FASE 8: AUDITORÍA ENTERPRISE (Fintech-grade)
-- Fecha: 2026-02-24
-- Riesgo: BAJO (solo agrega tabla y triggers)
-- Downtime: CERO
-- NOTA: Ya ejecutado en Supabase
-- ================================================================

-- 8.1 Tabla de auditoría
CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    tabla VARCHAR(100) NOT NULL,
    operacion VARCHAR(10) NOT NULL,
    registro_id BIGINT NOT NULL,
    empresa_id BIGINT,
    usuario_id BIGINT,
    datos_anteriores JSONB,
    datos_nuevos JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 8.2 Índices para audit_log
CREATE INDEX IF NOT EXISTS idx_audit_empresa ON audit_log(empresa_id);
CREATE INDEX IF NOT EXISTS idx_audit_tabla ON audit_log(tabla);
CREATE INDEX IF NOT EXISTS idx_audit_fecha ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_registro ON audit_log(tabla, registro_id);
CREATE INDEX IF NOT EXISTS idx_audit_empresa_fecha ON audit_log(empresa_id, created_at);

-- 8.3 RLS en audit_log
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS audit_isolation ON audit_log;
CREATE POLICY audit_isolation ON audit_log
    FOR ALL
    USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL);

-- 8.4 Función trigger genérica de auditoría
CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (tabla, operacion, registro_id, empresa_id, usuario_id, datos_nuevos)
        VALUES (
            TG_TABLE_NAME, 'INSERT', NEW.id,
            CASE WHEN TG_TABLE_NAME = 'empresas_empresa' THEN NEW.id ELSE NEW.empresa_id END,
            NULLIF(current_setting('app.current_user', true), '')::BIGINT,
            to_jsonb(NEW)
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (tabla, operacion, registro_id, empresa_id, usuario_id, datos_anteriores, datos_nuevos)
        VALUES (
            TG_TABLE_NAME, 'UPDATE', NEW.id,
            CASE WHEN TG_TABLE_NAME = 'empresas_empresa' THEN NEW.id ELSE NEW.empresa_id END,
            NULLIF(current_setting('app.current_user', true), '')::BIGINT,
            to_jsonb(OLD), to_jsonb(NEW)
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (tabla, operacion, registro_id, empresa_id, usuario_id, datos_anteriores)
        VALUES (
            TG_TABLE_NAME, 'DELETE', OLD.id,
            CASE WHEN TG_TABLE_NAME = 'empresas_empresa' THEN OLD.id ELSE OLD.empresa_id END,
            NULLIF(current_setting('app.current_user', true), '')::BIGINT,
            to_jsonb(OLD)
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 8.5 Triggers en tablas críticas de negocio
-- Empresas
DROP TRIGGER IF EXISTS audit_empresas ON empresas_empresa;
CREATE TRIGGER audit_empresas
    AFTER INSERT OR UPDATE OR DELETE ON empresas_empresa
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Usuarios
DROP TRIGGER IF EXISTS audit_users ON authentication_customuser;
CREATE TRIGGER audit_users
    AFTER INSERT OR UPDATE OR DELETE ON authentication_customuser
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Clientes
DROP TRIGGER IF EXISTS audit_clientes ON ventas_cliente;
CREATE TRIGGER audit_clientes
    AFTER INSERT OR UPDATE OR DELETE ON ventas_cliente
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Proveedores
DROP TRIGGER IF EXISTS audit_proveedores ON compras_proveedor;
CREATE TRIGGER audit_proveedores
    AFTER INSERT OR UPDATE OR DELETE ON compras_proveedor
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Productos
DROP TRIGGER IF EXISTS audit_productos ON inventario_producto;
CREATE TRIGGER audit_productos
    AFTER INSERT OR UPDATE OR DELETE ON inventario_producto
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Stock
DROP TRIGGER IF EXISTS audit_stock ON inventario_stock;
CREATE TRIGGER audit_stock
    AFTER INSERT OR UPDATE OR DELETE ON inventario_stock
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Almacenes
DROP TRIGGER IF EXISTS audit_almacenes ON inventario_almacen;
CREATE TRIGGER audit_almacenes
    AFTER INSERT OR UPDATE OR DELETE ON inventario_almacen
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Movimientos de inventario
DROP TRIGGER IF EXISTS audit_movimientos ON inventario_movimientoinventario;
CREATE TRIGGER audit_movimientos
    AFTER INSERT OR UPDATE OR DELETE ON inventario_movimientoinventario
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Compras
DROP TRIGGER IF EXISTS audit_compras ON compras_compra;
CREATE TRIGGER audit_compras
    AFTER INSERT OR UPDATE OR DELETE ON compras_compra
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Detalle compras
DROP TRIGGER IF EXISTS audit_compradetalle ON compras_compradetalle;
CREATE TRIGGER audit_compradetalle
    AFTER INSERT OR UPDATE OR DELETE ON compras_compradetalle
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Pagos compra
DROP TRIGGER IF EXISTS audit_pagocompra ON compras_pagocompra;
CREATE TRIGGER audit_pagocompra
    AFTER INSERT OR UPDATE OR DELETE ON compras_pagocompra
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Órdenes de compra
DROP TRIGGER IF EXISTS audit_ordencompra ON compras_ordencompra;
CREATE TRIGGER audit_ordencompra
    AFTER INSERT OR UPDATE OR DELETE ON compras_ordencompra
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Ventas
DROP TRIGGER IF EXISTS audit_ventas ON ventas_venta;
CREATE TRIGGER audit_ventas
    AFTER INSERT OR UPDATE OR DELETE ON ventas_venta
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Detalle ventas
DROP TRIGGER IF EXISTS audit_detalleventa ON ventas_detalleventa;
CREATE TRIGGER audit_detalleventa
    AFTER INSERT OR UPDATE OR DELETE ON ventas_detalleventa
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Pagos venta
DROP TRIGGER IF EXISTS audit_pagoventa ON ventas_pagoventa;
CREATE TRIGGER audit_pagoventa
    AFTER INSERT OR UPDATE OR DELETE ON ventas_pagoventa
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Órdenes de venta
DROP TRIGGER IF EXISTS audit_ordenventa ON ventas_ordenventa;
CREATE TRIGGER audit_ordenventa
    AFTER INSERT OR UPDATE OR DELETE ON ventas_ordenventa
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Facturas
DROP TRIGGER IF EXISTS audit_facturas ON ventas_factura;
CREATE TRIGGER audit_facturas
    AFTER INSERT OR UPDATE OR DELETE ON ventas_factura
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Cotizaciones
DROP TRIGGER IF EXISTS audit_cotizaciones ON cotizaciones;
CREATE TRIGGER audit_cotizaciones
    AFTER INSERT OR UPDATE OR DELETE ON cotizaciones
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Detalles cotización
DROP TRIGGER IF EXISTS audit_detallecotizacion ON detalles_cotizacion;
CREATE TRIGGER audit_detallecotizacion
    AFTER INSERT OR UPDATE OR DELETE ON detalles_cotizacion
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Producción - Recetas
DROP TRIGGER IF EXISTS audit_recetas ON produccion_recetaproducto;
CREATE TRIGGER audit_recetas
    AFTER INSERT OR UPDATE OR DELETE ON produccion_recetaproducto
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Producción - Detalle recetas
DROP TRIGGER IF EXISTS audit_recetadetalle ON produccion_recetadetalle;
CREATE TRIGGER audit_recetadetalle
    AFTER INSERT OR UPDATE OR DELETE ON produccion_recetadetalle
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Producción - Órdenes
DROP TRIGGER IF EXISTS audit_ordenproduccion ON produccion_ordenproduccion;
CREATE TRIGGER audit_ordenproduccion
    AFTER INSERT OR UPDATE OR DELETE ON produccion_ordenproduccion
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Producción - Consumo real
DROP TRIGGER IF EXISTS audit_consumoreal ON produccion_consumoreal;
CREATE TRIGGER audit_consumoreal
    AFTER INSERT OR UPDATE OR DELETE ON produccion_consumoreal
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Producción - Historial
DROP TRIGGER IF EXISTS audit_historialorden ON produccion_historialordenproduccion;
CREATE TRIGGER audit_historialorden
    AFTER INSERT OR UPDATE OR DELETE ON produccion_historialordenproduccion
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Producción - Costos
DROP TRIGGER IF EXISTS audit_productioncost ON produccion_productioncost;
CREATE TRIGGER audit_productioncost
    AFTER INSERT OR UPDATE OR DELETE ON produccion_productioncost
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Producción - Output
DROP TRIGGER IF EXISTS audit_productionoutput ON produccion_productionoutput;
CREATE TRIGGER audit_productionoutput
    AFTER INSERT OR UPDATE OR DELETE ON produccion_productionoutput
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Producción - Waste
DROP TRIGGER IF EXISTS audit_productionwaste ON produccion_productionwaste;
CREATE TRIGGER audit_productionwaste
    AFTER INSERT OR UPDATE OR DELETE ON produccion_productionwaste
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Inventario - Materias primas
DROP TRIGGER IF EXISTS audit_inv_mp ON inventario_inventariomateriasprimas;
CREATE TRIGGER audit_inv_mp
    AFTER INSERT OR UPDATE OR DELETE ON inventario_inventariomateriasprimas
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Inventario - Productos terminados
DROP TRIGGER IF EXISTS audit_inv_pt ON inventario_inventarioproductosterminados;
CREATE TRIGGER audit_inv_pt
    AFTER INSERT OR UPDATE OR DELETE ON inventario_inventarioproductosterminados
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- AI Assistant
DROP TRIGGER IF EXISTS audit_conversations ON ai_assistant_conversation;
CREATE TRIGGER audit_conversations
    AFTER INSERT OR UPDATE OR DELETE ON ai_assistant_conversation
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Compras recurrentes
DROP TRIGGER IF EXISTS audit_comprarecurrente ON compras_comprarecurrente;
CREATE TRIGGER audit_comprarecurrente
    AFTER INSERT OR UPDATE OR DELETE ON compras_comprarecurrente
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Ajustes de inventario
DROP TRIGGER IF EXISTS audit_ajusteinventario ON inventario_ajusteinventario;
CREATE TRIGGER audit_ajusteinventario
    AFTER INSERT OR UPDATE OR DELETE ON inventario_ajusteinventario
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Categorías
DROP TRIGGER IF EXISTS audit_categorias ON inventario_categoria;
CREATE TRIGGER audit_categorias
    AFTER INSERT OR UPDATE OR DELETE ON inventario_categoria
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- VERIFICACIÓN
SELECT 'Triggers de auditoría:' as info;
SELECT 
    event_object_table as tabla,
    trigger_name,
    event_manipulation as operacion
FROM information_schema.triggers
WHERE trigger_schema = 'public'
AND trigger_name LIKE 'audit_%'
ORDER BY event_object_table;

DO $$ 
BEGIN
    RAISE NOTICE '✅ FASE 8 COMPLETADA: Auditoría enterprise implementada';
    RAISE NOTICE '33 triggers activos en tablas críticas de negocio';
END $$;
