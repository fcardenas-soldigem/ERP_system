import React from 'react';
import { Box, Flex, Text, Icon, useColorModeValue } from '@chakra-ui/react';
import { useNavigate } from 'react-router-dom';
import {
  FaPlus, FaShoppingCart, FaBox, FaFileInvoice,
  FaMoneyBillWave, FaWarehouse, FaTruck,
} from 'react-icons/fa';

const ACTIONS = [
  { label: 'Nueva Venta',      icon: FaPlus,           path: '/app/ventas/nueva',        color: '#3b6feb' },
  { label: 'Nueva Compra',     icon: FaShoppingCart,   path: '/app/compras/nueva',        color: '#7c3aed' },
  { label: 'Nuevo Producto',   icon: FaBox,            path: '/app/inventario/nuevo',     color: '#0891b2' },
  { label: 'Nueva Cotización', icon: FaFileInvoice,    path: '/app/cotizaciones/nueva',   color: '#059669' },
  { label: 'Registrar Cobro',  icon: FaMoneyBillWave,  path: '/app/cuentas/por-cobrar',   color: '#d97706' },
  { label: 'Nueva Guía',       icon: FaTruck,          path: '/app/guias/nueva',          color: '#0e7490' },
  { label: 'Ver Inventario',   icon: FaWarehouse,      path: '/app/inventario',           color: '#64748b' },
];

const QuickActions = () => {
  const navigate = useNavigate();
  // Match the Dashboard background so the fade blends correctly (F-008 fix)
  const dashBg = useColorModeValue('gray.50', 'gray.900');

  return (
    <Box position="relative">
      {/* Fade gradient on right edge to hint more chips exist */}
      <Box
        position="absolute"
        right={0}
        top={0}
        bottom={0}
        w="48px"
        bgGradient={`linear(to-r, transparent, var(--chakra-colors-gray-50))`}
        zIndex={1}
        pointerEvents="none"
        display={{ base: 'block', lg: 'none' }}
        _dark={{ bgGradient: 'linear(to-r, transparent, gray.900)' }}
      />
      <Flex
        gap={2}
        overflowX="auto"
        pb={1}
        sx={{
          scrollSnapType: 'x mandatory',
          scrollBehavior: 'smooth',
          '&::-webkit-scrollbar': { display: 'none' },
          msOverflowStyle: 'none',
          scrollbarWidth: 'none',
        }}
      >
        {ACTIONS.map(({ label, icon, path, color }) => (
          <Flex
            key={label}
            as="button"
            type="button"
            aria-label={label}
            onClick={() => navigate(path)}
            align="center"
            gap={2}
            px={4}
            py={2}
            borderRadius="full"
            bg="gray.100"
            color="gray.700"
            fontSize="sm"
            fontWeight="medium"
            whiteSpace="nowrap"
            flexShrink={0}
            cursor="pointer"
            border="1px solid"
            borderColor="gray.200"
            transition="all 0.15s"
            scrollSnapAlign="start"
            _hover={{ bg: 'white', borderColor: color, color: color, boxShadow: 'sm' }}
            _active={{ transform: 'scale(0.97)' }}
          >
            <Icon as={icon} boxSize="13px" color={color} />
            <Text>{label}</Text>
          </Flex>
        ))}
      </Flex>
    </Box>
  );
};

export default QuickActions;
