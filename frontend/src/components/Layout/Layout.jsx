import React from 'react';
import { Outlet, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Navbar from '../Navbar/Navbar';
import AnimatedSidebar from './AnimatedSidebar';
import { Box, Flex, Spinner, Center } from '@chakra-ui/react';
import { FaShoppingCart, FaRobot, FaBox, FaUsers, FaCog, FaChartBar, FaMoneyBillWave, FaBrain, FaFileInvoice, FaIndustry } from 'react-icons/fa';

const Layout = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  const menuItems = [
    {
      name: 'Dashboard',
      icon: FaChartBar,
      path: '/app/dashboard'
    },
    {
      name: 'Ventas',
      icon: FaShoppingCart,
      path: '/app/ventas'
    },
    {
      name: 'Cotizaciones',
      icon: FaFileInvoice,
      path: '/app/cotizaciones'
    },
    {
      name: 'Compras',
      icon: FaBox,
      path: '/app/compras'
    },
    {
      name: 'Cuentas',
      icon: FaMoneyBillWave,
      subItems: [
        {
          name: 'Cuentas por Cobrar',
          path: '/app/cuentas/por-cobrar'
        },
        {
          name: 'Cuentas por Pagar',
          path: '/app/cuentas/por-pagar'
        }
      ]
    },
    {
      name: 'Inventario',
      icon: FaBox,
      path: '/app/inventario'
    },
    {
      name: 'Producción',
      icon: FaIndustry,
      subItems: [
        {
          name: 'Dashboard',
          path: '/produccion/dashboard'
        },
        {
          name: 'Recetas (BOM)',
          path: '/produccion/recetas'
        },
        {
          name: 'Órdenes de Producción',
          path: '/produccion/ordenes'
        }
      ]
    },
    {
      name: 'Proveedores',
      icon: FaUsers,
      path: '/app/proveedores'
    },
    {
      name: 'Clientes',
      icon: FaUsers,
      path: '/app/clientes'
    },
    {
      name: 'Asistente Virtual',
      icon: FaRobot,
      path: '/app/ai-assistant'
    },
    {
      name: 'Machine Learning',
      icon: FaBrain,
      path: '/app/ml-dashboard'
    },
    {
      name: 'Configuración',
      icon: FaCog,
      path: '/app/configuracion'
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
    <Flex minH="100vh" bg="gray.50" _dark={{ bg: "gray.900" }}>
      <AnimatedSidebar menuItems={menuItems} />
      <Box flex="1" overflow="auto">
        <Navbar />
        <Box p={6}>
          <Outlet />
        </Box>
      </Box>
    </Flex>
  );
};

export default Layout; 