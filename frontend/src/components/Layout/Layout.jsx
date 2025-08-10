import React from 'react';
import { Outlet, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Navbar from '../Navbar/Navbar';
import Sidebar from './Sidebar';
import { Box, Flex, Spinner, Center } from '@chakra-ui/react';
import { FaShoppingCart, FaRobot, FaBox, FaUsers, FaCog, FaChartBar, FaMoneyBillWave } from 'react-icons/fa';

const Layout = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  const menuItems = [
    {
      name: 'Dashboard',
      icon: FaChartBar,
      path: '/dashboard'
    },
    {
      name: 'Ventas',
      icon: FaShoppingCart,
      path: '/ventas'
    },
    {
      name: 'Compras',
      icon: FaBox,
      path: '/compras'
    },
    {
      name: 'Cuentas',
      icon: FaMoneyBillWave,
      subItems: [
        {
          name: 'Cuentas por Cobrar',
          path: '/cuentas/por-cobrar'
        },
        {
          name: 'Cuentas por Pagar',
          path: '/cuentas/por-pagar'
        }
      ]
    },
    {
      name: 'Inventario',
      icon: FaBox,
      path: '/inventario'
    },
    {
      name: 'Proveedores',
      icon: FaUsers,
      path: '/proveedores'
    },
    {
      name: 'Clientes',
      icon: FaUsers,
      path: '/clientes'
    },
    {
      name: 'Asistente Virtual',
      icon: FaRobot,
      path: '/ai-assistant'
    },
    {
      name: 'Configuración',
      icon: FaCog,
      path: '/configuracion'
    }
  ];

  if (isLoading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" />
      </Center>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return (
    <Box minH="100vh">
      <Navbar />
      <Flex>
        <Sidebar menuItems={menuItems} />
        <Box flex="1" p={4}>
          <Outlet />
        </Box>
      </Flex>
    </Box>
  );
};

export default Layout; 