import React from 'react';
import { Box, Flex, Text, Icon } from '@chakra-ui/react';
import { useNavigate } from 'react-router-dom';
import {
  Plus, ShoppingCart, Package, FileText, Banknote, Warehouse, Truck,
} from 'lucide-react';
import { useModoInventario } from '../../hooks/useModoInventario';
import { usePuedeEscribir } from '../../hooks/usePuedeEscribir';

// requiereStock: acciones de inventario, ocultas para empresas sin_stock.
// UN solo estilo (secondary) e íconos neutros: las quick actions son un grupo,
// no siete botones compitiendo en color.
const ACTIONS = [
  { label: 'Nueva Venta',      icon: Plus,         path: '/app/ventas/nueva' },
  { label: 'Nueva Compra',     icon: ShoppingCart, path: '/app/compras/nueva' },
  { label: 'Nuevo Producto',   icon: Package,      path: '/app/inventario/nuevo', requiereStock: true },
  { label: 'Nueva Cotización', icon: FileText,     path: '/app/cotizaciones/nueva' },
  { label: 'Registrar Cobro',  icon: Banknote,     path: '/app/cuentas/por-cobrar' },
  { label: 'Nueva Guía',       icon: Truck,        path: '/app/guias/nueva' },
  { label: 'Ver Inventario',   icon: Warehouse,    path: '/app/inventario', requiereStock: true },
];

const QuickActions = () => {
  const navigate = useNavigate();
  const { conStock } = useModoInventario();
  const puedeEscribir = usePuedeEscribir();
  // solo_lectura: quedan solo los accesos de consulta (Ver Inventario, Registrar
  // Cobro navega a una lista). Los "Nueva/Nuevo" crean documentos.
  const acciones = ACTIONS.filter(a => (!a.requiereStock || conStock)
    && (puedeEscribir || !/^Nuev/.test(a.label)));

  return (
    <Box position="relative">
      {/* Fade gradient on right edge to hint more chips exist */}
      <Box
        position="absolute"
        right={0}
        top={0}
        bottom={0}
        w="48px"
        bgGradient={`linear(to-r, transparent, var(--chakra-colors-neutral-50))`}
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
        {acciones.map(({ label, icon, path }) => (
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
            bg="white"
            color="neutral.700"
            fontSize="sm"
            fontWeight="medium"
            whiteSpace="nowrap"
            flexShrink={0}
            cursor="pointer"
            border="1px solid"
            borderColor="neutral.300"
            transition="background-color 120ms ease, border-color 120ms ease, transform 120ms cubic-bezier(0.23, 1, 0.32, 1)"
            scrollSnapAlign="start"
            _hover={{ bg: 'neutral.50', borderColor: 'neutral.400' }}
            _active={{ transform: 'scale(0.97)' }}
          >
            <Icon as={icon} boxSize="13px" color="neutral.600" strokeWidth={2} />
            <Text>{label}</Text>
          </Flex>
        ))}
      </Flex>
    </Box>
  );
};

export default QuickActions;
