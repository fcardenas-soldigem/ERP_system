import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ChakraProvider } from '@chakra-ui/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import 'bootstrap/dist/css/bootstrap.min.css';
import './utils/debugAuth.js';
import { AuthProvider } from './components/context/AuthContext';
import PrivateRoute from './components/PrivateRoute';
import Login from './components/Auth/Login';
import Dashboard from './components/Dashboard/Dashboard';
import Clientes from './components/Ventas/Clientes';
import Ventas from './components/Ventas/Ventas';
import NuevaVenta from './components/Ventas/NuevaVenta';
import Inventario from './components/Inventario/Inventario';
import AddProducto from './components/Inventario/AddProducto';
import KardexMejorado from './components/Inventario/KardexMejorado';
import InventarioEnlaces from './components/Inventario/InventarioEnlaces';
import Compras from './components/Compras/Compras';
import Configuracion from './pages/Configuracion';
import AIAssistant from './pages/AIAssistant';
import Layout from './components/Layout/Layout';
import NotFound from './components/NotFound';
import CompraForm from './components/Compras/CompraForm';
import Proveedores from './components/Proveedores/Proveedores';
import ProveedorForm from './components/Proveedores/ProveedorForm';
import CompraEdit from './components/Compras/CompraEdit';
import CompraDetalle from './components/Compras/CompraDetalle';
import VentaDetalle from './components/Ventas/VentaDetalle';
import VentaEdit from './components/Ventas/VentaEdit';
import CompraPagos from './components/Compras/CompraPagos';
import CompraPagoForm from './components/Compras/CompraPagoForm';
import VentaPagos from './components/Ventas/VentaPagos';
import VentaPagoForm from './components/Ventas/VentaPagoForm';
import CuentasPorCobrar from './components/Cuentas/CuentasPorCobrar';
import CuentasPorPagar from './components/Cuentas/CuentasPorPagar';
import RegistrarPagoVenta from './components/Cuentas/RegistrarPagoVenta';
import RegistrarPagoCompra from './components/Cuentas/RegistrarPagoCompra';

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            refetchOnWindowFocus: false,
            retry: 1,
            staleTime: 5 * 60 * 1000,
        }
    }
});

function App() {
    return (
        <Router>
            <QueryClientProvider client={queryClient}>
                <ChakraProvider>
                    <AuthProvider>
                        <Routes>
                            <Route path="/login" element={<Login />} />
                            <Route path="/" element={<PrivateRoute><Layout /></PrivateRoute>}>
                                <Route index element={<Navigate to="/dashboard" replace />} />
                                <Route path="dashboard" element={<Dashboard />} />
                                <Route path="ventas" element={<Ventas />} />
                                <Route path="ventas/nueva" element={<NuevaVenta />} />
                                <Route path="ventas/:id" element={<VentaDetalle />} />
                                <Route path="ventas/:id/editar" element={<VentaEdit />} />
                                <Route path="ventas/:id/pagos" element={<VentaPagos />} />
                                <Route path="ventas/:id/pagos/nuevo" element={<VentaPagoForm />} />
                                <Route path="clientes" element={<Clientes />} />
                                <Route path="inventario" element={<Inventario />} />
                                <Route path="inventario/nuevo" element={<AddProducto />} />
                                <Route path="inventario/kardex-mejorado" element={<KardexMejorado />} />
                                <Route path="inventario/enlaces" element={<InventarioEnlaces />} />
                                <Route path="compras" element={<Compras />} />
                                <Route path="compras/nueva" element={<CompraForm />} />
                                <Route path="compras/:id" element={<CompraDetalle />} />
                                <Route path="compras/:id/editar" element={<CompraEdit />} />
                                <Route path="compras/:id/pagos" element={<CompraPagos />} />
                                <Route path="compras/:id/pagos/nuevo" element={<CompraPagoForm />} />
                                <Route path="proveedores" element={<Proveedores />} />
                                <Route path="proveedores/nuevo" element={<ProveedorForm />} />
                                <Route path="proveedores/:id/editar" element={<ProveedorForm />} />
                                <Route path="configuracion" element={<Configuracion />} />
                                <Route path="ai-assistant" element={<AIAssistant />} />
                                <Route path="cuentas/por-cobrar" element={<CuentasPorCobrar />} />
                                <Route path="cuentas/por-cobrar/:ventaId/registrar-pago" element={<RegistrarPagoVenta />} />
                                <Route path="cuentas/por-pagar" element={<CuentasPorPagar />} />
                                <Route path="cuentas/por-pagar/:compraId/registrar-pago" element={<RegistrarPagoCompra />} />
                                <Route path="*" element={<NotFound />} />
                            </Route>
                        </Routes>
                        <ToastContainer />
                    </AuthProvider>
                </ChakraProvider>
            </QueryClientProvider>
        </Router>
    );
}
export default App;