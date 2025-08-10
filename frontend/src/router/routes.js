import { FaFileInvoiceDollar } from 'react-icons/fa';
import CuentasPorPagar from '../components/Cuentas/CuentasPorPagar';
import RegistrarPagoCompra from '../components/Cuentas/RegistrarPagoCompra';

const routes = [
  // Rutas de cuentas por pagar
  {
    path: '/cuentas/por-pagar',
    element: <CuentasPorPagar />,
    name: 'Cuentas por Pagar',
    icon: <FaFileInvoiceDollar />,
    showInSidebar: true,
    parent: 'Cuentas'
  },
  {
    path: '/cuentas/por-pagar/:compraId/registrar-pago',
    element: <RegistrarPagoCompra />,
    name: 'Registrar Pago de Compra',
    showInSidebar: false
  },
];

export default routes; 