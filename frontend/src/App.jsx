import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ChakraProvider } from '@chakra-ui/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from './lib/queryClient';
import theme from './theme';
import './utils/debugAuth.js';
import ErrorBoundary from './components/common/ErrorBoundary';
import AppLoading from './components/common/AppLoading';
import { AuthProvider } from './components/context/AuthContext';
import PrivateRoute from './components/PrivateRoute';

// ─── Lazy-loaded routes ──────────────────────────────────────────────────────
// Each route is a separate chunk. Initial bundle only loads shell + auth.
const Layout        = lazy(() => import('./components/Layout/Layout'));
const LandingPage   = lazy(() => import('./pages/LandingPage'));
const Login         = lazy(() => import('./components/Auth/Login'));
const NotFound      = lazy(() => import('./components/NotFound'));

// Core
const Dashboard     = lazy(() => import('./components/Dashboard/Dashboard'));
const Ventas        = lazy(() => import('./components/Ventas/Ventas'));
const NuevaVenta    = lazy(() => import('./components/Ventas/NuevaVenta'));
const VentaDetalle  = lazy(() => import('./components/Ventas/VentaDetalle'));
const VentaEdit     = lazy(() => import('./components/Ventas/VentaEdit'));
const VentaPagos    = lazy(() => import('./components/Ventas/VentaPagos'));
const VentaPagoForm = lazy(() => import('./components/Ventas/VentaPagoForm'));
const Clientes      = lazy(() => import('./components/Ventas/Clientes'));

// Compras — consolidated
const Compras             = lazy(() => import('./components/Compras/Compras'));
const CompraForm          = lazy(() => import('./components/Compras/CompraForm'));
const OrdenCompraForm     = lazy(() => import('./components/Compras/OrdenCompraForm'));
const OrdenCompraServicioForm = lazy(() => import('./components/Compras/OrdenCompraServicioForm'));
const OrdenesServicioCompraList = lazy(() => import('./components/Compras/OrdenesServicioCompraList'));
const OrdenServicioCompraDetalle = lazy(() => import('./components/Compras/OrdenServicioCompraDetalle'));
const OrdenesCompraList   = lazy(() => import('./components/Compras/OrdenesCompraList'));
const OrdenCompraDetalle  = lazy(() => import('./components/Compras/OrdenCompraDetalle'));
const CompraDetalle = lazy(() => import('./components/Compras/CompraDetalle'));
const CompraEdit    = lazy(() => import('./components/Compras/CompraEdit'));
const CompraPagos   = lazy(() => import('./components/Compras/CompraPagos'));
const CompraPagoForm= lazy(() => import('./components/Compras/CompraPagoForm'));
const Proveedores   = lazy(() => import('./components/Proveedores/Proveedores'));
const ProveedorForm = lazy(() => import('./components/Proveedores/ProveedorForm'));

// Inventario
const Inventario              = lazy(() => import('./components/Inventario/Inventario'));
const AddProducto             = lazy(() => import('./components/Inventario/AddProducto'));
const KardexMejorado          = lazy(() => import('./components/Inventario/KardexMejorado'));
const InventarioEnlaces       = lazy(() => import('./components/Inventario/InventarioEnlaces'));
const InventarioMateriasPrimas= lazy(() => import('./components/Inventario/InventarioMateriasPrimas'));
const InventarioProductosTerminados = lazy(() => import('./components/Inventario/InventarioProductosTerminados'));
const ResumenInventariosSeparados   = lazy(() => import('./components/Inventario/ResumenInventariosSeparados'));
const CargaMasivaInventario   = lazy(() => import('./components/Inventario/CargaMasivaInventario'));

// Importador Excel
const ImportadorWizard = lazy(() => import('./pages/Importador/ImportadorWizard'));

// Cotizaciones — consolidated: CotizacionForm replaces CotizacionFormSimple
const CotizacionList         = lazy(() => import('./components/Cotizaciones/CotizacionList'));
const CotizacionForm         = lazy(() => import('./components/Cotizaciones/CotizacionForm'));
const CotizacionServiciosForm= lazy(() => import('./components/Cotizaciones/CotizacionServiciosForm'));
const CotizacionDetalle      = lazy(() => import('./components/Cotizaciones/CotizacionDetalle'));

// Cuentas
const CuentasPorCobrar   = lazy(() => import('./components/Cuentas/CuentasPorCobrar'));
const CuentasPorPagar    = lazy(() => import('./components/Cuentas/CuentasPorPagar'));
const RegistrarPagoVenta = lazy(() => import('./components/Cuentas/RegistrarPagoVenta'));
const RegistrarPagoCompra= lazy(() => import('./components/Cuentas/RegistrarPagoCompra'));

// Producción
const DashboardProduccion    = lazy(() => import('./components/Produccion/DashboardProduccion'));
const RecetasList            = lazy(() => import('./components/Produccion/RecetasList'));
const RecetaForm             = lazy(() => import('./components/Produccion/RecetaForm'));
const RecetaDetalle          = lazy(() => import('./components/Produccion/RecetaDetalle'));
const OrdenProduccionList    = lazy(() => import('./components/Produccion/OrdenProduccionList'));
const OrdenProduccionForm    = lazy(() => import('./components/Produccion/OrdenProduccionForm'));
const OrdenProduccionEjecucion = lazy(() => import('./components/Produccion/OrdenProduccionEjecucion'));
const OrdenDetalle           = lazy(() => import('./components/Produccion/OrdenDetalle'));

// Finanzas
const FinanzasPage  = lazy(() => import('./pages/Finanzas/FinanzasPage'));
const GastosPage    = lazy(() => import('./pages/Finanzas/GastosPage'));

// Guías de Remisión
const GuiaList    = lazy(() => import('./pages/Guias/GuiaList'));
const GuiaDetalle = lazy(() => import('./pages/Guias/GuiaDetalle'));
const GuiaForm    = lazy(() => import('./pages/Guias/GuiaForm'));

// Órdenes de Servicio
const OrdenServicioList    = lazy(() => import('./pages/Servicios/OrdenServicioList'));
const OrdenServicioDetalle = lazy(() => import('./pages/Servicios/OrdenServicioDetalle'));
const OrdenServicioForm    = lazy(() => import('./pages/Servicios/OrdenServicioForm'));

// Avanzado
const Configuracion = lazy(() => import('./pages/Configuracion'));
const AIAssistant   = lazy(() => import('./pages/AIAssistant'));
const MLDashboard   = lazy(() => import('./components/ML/MLDashboard'));

function App() {
    return (
        <Router>
            <QueryClientProvider client={queryClient}>
                <ChakraProvider theme={theme}>
                    <ErrorBoundary fullscreen>
                    <AuthProvider>
                        <Suspense fallback={<AppLoading />}>
                        <Routes>
                            <Route path="/" element={<LandingPage />} />
                            <Route path="/login" element={<Login />} />
                            <Route path="/app" element={<PrivateRoute><Layout /></PrivateRoute>}>
                                <Route index element={<Navigate to="/app/dashboard" replace />} />

                                {/* CORE */}
                                <Route path="dashboard" element={<Dashboard />} />
                                <Route path="ventas" element={<Ventas />} />
                                <Route path="ventas/nueva" element={<NuevaVenta />} />
                                <Route path="ventas/:id" element={<VentaDetalle />} />
                                <Route path="ventas/:id/editar" element={<VentaEdit />} />
                                <Route path="ventas/:id/pagos" element={<VentaPagos />} />
                                <Route path="ventas/:id/pagos/nuevo" element={<VentaPagoForm />} />
                                <Route path="clientes" element={<Clientes />} />

                                {/* COMPRAS — consolidated */}
                                <Route path="compras" element={<Compras />} />
                                <Route path="compras/nueva" element={<CompraForm />} />
                                <Route path="compras/orden-compra/nueva" element={<OrdenCompraForm />} />
                                <Route path="compras/ordenes-servicio" element={<OrdenesServicioCompraList />} />
                                <Route path="compras/orden-servicio/nueva" element={<OrdenCompraServicioForm />} />
                                <Route path="compras/ordenes-servicio/:id" element={<OrdenServicioCompraDetalle />} />
                                <Route path="compras/ordenes-servicio/:id/editar" element={<OrdenCompraServicioForm />} />
                                <Route path="compras/ordenes" element={<OrdenesCompraList />} />
                                <Route path="compras/ordenes/:id" element={<OrdenCompraDetalle />} />
                                <Route path="compras/:id" element={<CompraDetalle />} />
                                <Route path="compras/:id/editar" element={<CompraEdit />} />
                                <Route path="compras/:id/pagos" element={<CompraPagos />} />
                                <Route path="compras/:id/pagos/nuevo" element={<CompraPagoForm />} />
                                <Route path="proveedores" element={<Proveedores />} />
                                <Route path="proveedores/nuevo" element={<ProveedorForm />} />
                                <Route path="proveedores/:id/editar" element={<ProveedorForm />} />

                                {/* FINANZAS */}
                                <Route path="finanzas" element={<FinanzasPage />} />
                                <Route path="finanzas/gastos" element={<GastosPage />} />

                                {/* INVENTARIO */}
                                <Route path="inventario" element={<Inventario />} />
                                <Route path="inventario/nuevo" element={<AddProducto />} />
                                <Route path="inventario/:id/editar" element={<AddProducto />} />
                                <Route path="inventario/kardex" element={<KardexMejorado />} />
                                <Route path="inventario/materias-primas" element={<InventarioMateriasPrimas />} />
                                <Route path="inventario/productos-terminados" element={<InventarioProductosTerminados />} />
                                <Route path="inventario/resumen-separado" element={<ResumenInventariosSeparados />} />
                                <Route path="inventario/carga-masiva" element={<CargaMasivaInventario />} />
                                <Route path="inventario/enlaces" element={<InventarioEnlaces />} />
                                <Route path="importador" element={<ImportadorWizard />} />

                                {/* COTIZACIONES — consolidated (CotizacionForm replaces CotizacionFormSimple) */}
                                <Route path="cotizaciones" element={<CotizacionList />} />
                                <Route path="cotizaciones/nueva" element={<CotizacionForm />} />
                                <Route path="cotizaciones/servicios/nueva" element={<CotizacionServiciosForm />} />
                                <Route path="cotizaciones/servicios/:id/editar" element={<CotizacionServiciosForm />} />
                                <Route path="cotizaciones/:id" element={<CotizacionDetalle />} />
                                <Route path="cotizaciones/:id/editar" element={<CotizacionForm />} />

                                {/* CUENTAS */}
                                <Route path="cuentas/por-cobrar" element={<CuentasPorCobrar />} />
                                <Route path="cuentas/por-cobrar/:ventaId/registrar-pago" element={<RegistrarPagoVenta />} />
                                <Route path="cuentas/por-pagar" element={<CuentasPorPagar />} />
                                <Route path="cuentas/por-pagar/:compraId/registrar-pago" element={<RegistrarPagoCompra />} />

                                {/* PRODUCCIÓN */}
                                <Route path="produccion/dashboard" element={<DashboardProduccion />} />
                                <Route path="produccion/recetas" element={<RecetasList />} />
                                <Route path="produccion/recetas/nueva" element={<RecetaForm />} />
                                <Route path="produccion/recetas/:id" element={<RecetaDetalle />} />
                                <Route path="produccion/recetas/:id/editar" element={<RecetaForm />} />
                                <Route path="produccion/ordenes" element={<OrdenProduccionList />} />
                                <Route path="produccion/ordenes/nueva" element={<OrdenProduccionForm />} />
                                <Route path="produccion/ordenes/:id" element={<OrdenDetalle />} />
                                <Route path="produccion/ordenes/:id/ejecutar" element={<OrdenProduccionEjecucion />} />

                                {/* GUÍAS DE REMISIÓN */}
                                <Route path="guias" element={<GuiaList />} />
                                <Route path="guias/nueva" element={<GuiaForm />} />
                                <Route path="guias/:id" element={<GuiaDetalle />} />
                                <Route path="guias/:id/editar" element={<GuiaForm />} />

                                {/* ÓRDENES DE SERVICIO */}
                                <Route path="servicios" element={<OrdenServicioList />} />
                                <Route path="servicios/nueva" element={<OrdenServicioForm />} />
                                <Route path="servicios/:id" element={<OrdenServicioDetalle />} />
                                <Route path="servicios/:id/editar" element={<OrdenServicioForm />} />

                                {/* AVANZADO */}
                                <Route path="ai-assistant" element={<AIAssistant />} />
                                <Route path="ml-dashboard" element={<MLDashboard />} />
                                <Route path="configuracion" element={<Configuracion />} />

                                <Route path="*" element={<NotFound />} />
                            </Route>
                        </Routes>
                        </Suspense>
                    </AuthProvider>
                    </ErrorBoundary>
                </ChakraProvider>
            </QueryClientProvider>
        </Router>
    );
}
export default App;
