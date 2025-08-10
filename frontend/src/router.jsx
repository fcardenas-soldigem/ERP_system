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