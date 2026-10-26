import React from 'react';
import { Box, Flex, Icon, Text, useColorModeValue } from '@chakra-ui/react';
import { useLocation, useNavigate } from 'react-router-dom';
import { House, FileText, ShoppingCart, Bot, LayoutGrid } from 'lucide-react';

// Alto útil de la barra; el safe-area inferior (iPhone) se suma por fuera.
export const BOTTOM_NAV_H = '56px';

const TABS = [
  { label: 'Inicio',       icon: House,        path: '/app/dashboard' },
  { label: 'Cotizaciones', icon: FileText,     path: '/app/cotizaciones' },
  { label: 'Ventas',       icon: ShoppingCart, path: '/app/ventas' },
  { label: 'Jorge',        icon: Bot,          path: '/app/ai-assistant' },
];

const enRuta = (pathname, path) => pathname === path || pathname.startsWith(`${path}/`);

const Tab = ({ label, icon, activo, onClick }) => {
  const inactivo = useColorModeValue('neutral.500', 'neutral.400');
  const color = useColorModeValue('brand.500', 'brand.300');
  return (
    <Flex
      as="button"
      type="button"
      onClick={onClick}
      aria-label={label}
      aria-current={activo ? 'page' : undefined}
      flex="1"
      minW={0}
      h="100%"
      direction="column"
      align="center"
      justify="center"
      gap="3px"
      color={activo ? color : inactivo}
      // Toque: feedback de presión inmediato, sin animar el cambio de color
      // (la barra se usa decenas de veces al día).
      transition="transform 120ms cubic-bezier(0.23, 1, 0.32, 1)"
      _active={{ transform: 'scale(0.96)' }}
      sx={{ WebkitTapHighlightColor: 'transparent' }}
    >
      <Icon as={icon} boxSize="22px" strokeWidth={activo ? 2.1 : 1.75} />
      <Text fontSize="12px" lineHeight="14px" fontWeight={activo ? 600 : 500} noOfLines={1}>
        {label}
      </Text>
    </Flex>
  );
};

/** Barra inferior fija — solo móvil (< md). 5 pestañas; "Más" abre el lanzador. */
const BottomNav = ({ masAbierto, onMas }) => {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const bg = useColorModeValue('white', 'gray.800');
  const borde = useColorModeValue('neutral.200', 'gray.700');

  const tabActiva = TABS.find((t) => enRuta(pathname, t.path));

  return (
    <Box
      as="nav"
      aria-label="Navegación principal"
      position="fixed"
      left={0}
      right={0}
      bottom={0}
      zIndex="sticky"
      bg={bg}
      borderTop="1px solid"
      borderColor={borde}
      pb="env(safe-area-inset-bottom)"
    >
      <Flex h={BOTTOM_NAV_H} align="stretch">
        {TABS.map((t) => (
          <Tab
            key={t.path}
            label={t.label}
            icon={t.icon}
            activo={!masAbierto && tabActiva === t}
            onClick={() => navigate(t.path)}
          />
        ))}
        <Tab
          label="Más"
          icon={LayoutGrid}
          activo={masAbierto || !tabActiva}
          onClick={onMas}
        />
      </Flex>
    </Box>
  );
};

export default BottomNav;
