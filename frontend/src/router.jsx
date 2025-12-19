import { createBrowserRouter } from 'react-router-dom';
import App from './App';
import Dashboard from './components/Dashboard/Dashboard';
import VentasList from './components/Ventas/VentaList';
import ComprasList from './components/Compras/ComprasList';
import CompraForm from './components/Compras/CompraForm';
import CompraDetalle from './components/Compras/CompraDetalle';
import CompraEdit from './components/Compras/CompraEdit';
import InventarioList from './components/Inventario/InventarioList';
import Login from './pages/Login';
import Register from './pages/Register';
import ProveedoresList from './components/Proveedores/ProveedoresList';
import CuentasPorPagar from './components/Cuentas/CuentasPorPagar';
import CuentasPorCobrar from './components/Cuentas/CuentasPorCobrar';
import VentaPagoForm from './components/Cuentas/VentaPagoForm';
import VentaPagos from './components/Ventas/VentaPagos';
import MLDashboard from './components/ML/MLDashboard';
// Producción
import RecetasList from './components/Produccion/RecetasList';
import RecetaForm from './components/Produccion/RecetaForm';
import RecetaDetalle from './components/Produccion/RecetaDetalle';
import OrdenProduccionList from './components/Produccion/OrdenProduccionList';
import OrdenProduccionForm from './components/Produccion/OrdenProduccionForm';
import OrdenProduccionEjecucion from './components/Produccion/OrdenProduccionEjecucion';
import OrdenDetalle from './components/Produccion/OrdenDetalle';
import DashboardProduccion from './components/Produccion/DashboardProduccion';

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      {
        path: '/',
        element: <Dashboard />,
      },
      {
        path: '/ventas',
        element: <VentasList />,
      },
      {
        path: '/ventas/:id/pagos',
        element: <VentaPagos />,
      },
      {
        path: '/ventas/:id/pagos/nuevo',
        element: <VentaPagoForm />,
      },
      {
        path: '/compras',
        element: <ComprasList />,
      },
      {
        path: '/compras/nueva',
        element: <CompraForm />,
      },
      {
        path: '/compras/:id',
        element: <CompraDetalle />,
      },
      {
        path: '/compras/:id/editar',
        element: <CompraEdit />,
      },
      {
        path: '/inventario',
        element: <InventarioList />,
      },
      {
        path: '/proveedores',
        element: <ProveedoresList />,
      },
      {
        path: '/cuentas/por-pagar',
        element: <CuentasPorPagar />,
      },
      {
        path: '/cuentas/por-cobrar',
        element: <CuentasPorCobrar />,
      },
      {
        path: '/cuentas/por-cobrar/:id/registrar-pago',
        element: <VentaPagoForm />,
      },
      {
        path: '/ml-dashboard',
        element: <MLDashboard />,
      },
      // Producción
      {
        path: '/produccion/dashboard',
        element: <DashboardProduccion />,
      },
      {
        path: '/produccion/recetas',
        element: <RecetasList />,
      },
      {
        path: '/produccion/recetas/nueva',
        element: <RecetaForm />,
      },
      {
        path: '/produccion/recetas/:id',
        element: <RecetaDetalle />,
      },
      {
        path: '/produccion/recetas/:id/editar',
        element: <RecetaForm />,
      },
      {
        path: '/produccion/ordenes',
        element: <OrdenProduccionList />,
      },
      {
        path: '/produccion/ordenes/nueva',
        element: <OrdenProduccionForm />,
      },
      {
        path: '/produccion/ordenes/:id',
        element: <OrdenDetalle />,
      },
      {
        path: '/produccion/ordenes/:id/ejecutar',
        element: <OrdenProduccionEjecucion />,
      },
    ],
  },
  {
    path: '/login',
    element: <Login />,
  },
  {
    path: '/register',
    element: <Register />,
  },
]);

export default router; 