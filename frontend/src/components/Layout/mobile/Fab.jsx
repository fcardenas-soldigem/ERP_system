import React from 'react';
import { Box, Icon } from '@chakra-ui/react';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus } from 'lucide-react';
import { BOTTOM_NAV_H } from './BottomNav';

const MotionBox = motion(Box);

// Pantalla de lista (ruta exacta) → documento que crea en un toque.
const ACCIONES = {
  '/app/dashboard':                { label: 'Nueva cotización', path: '/app/cotizaciones/nueva' },
  '/app/cotizaciones':             { label: 'Nueva cotización', path: '/app/cotizaciones/nueva' },
  '/app/ventas':                   { label: 'Nueva venta',      path: '/app/ventas/nueva' },
  '/app/compras':                  { label: 'Nueva compra',     path: '/app/compras/nueva' },
  '/app/compras/ordenes':          { label: 'Nueva orden de compra', path: '/app/compras/orden-compra/nueva' },
  '/app/compras/ordenes-servicio': { label: 'Nueva OC de servicio',  path: '/app/compras/orden-servicio/nueva' },
};

/** Botón flotante "+" — solo móvil, solo en las listas de ACCIONES. */
const Fab = () => {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const accion = ACCIONES[pathname.replace(/\/$/, '')];

  return (
    <AnimatePresence>
      {accion && (
        <MotionBox
          key="fab"
          as="button"
          type="button"
          aria-label={accion.label}
          title={accion.label}
          onClick={() => navigate(accion.path)}
          position="fixed"
          right={4}
          bottom={`calc(${BOTTOM_NAV_H} + env(safe-area-inset-bottom) + 16px)`}
          zIndex="sticky"
          w="56px"
          h="56px"
          borderRadius="full"
          bg="brand.500"
          color="white"
          display="flex"
          alignItems="center"
          justifyContent="center"
          boxShadow="0 4px 12px rgba(20, 44, 78, 0.24), 0 1px 3px rgba(20, 44, 78, 0.16)"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1, transition: { duration: 0.2, ease: [0.23, 1, 0.32, 1] } }}
          exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.12 } }}
          whileTap={{ scale: 0.95 }}
          sx={{ WebkitTapHighlightColor: 'transparent' }}
        >
          <Icon as={Plus} boxSize="26px" strokeWidth={2.25} />
        </MotionBox>
      )}
    </AnimatePresence>
  );
};

export default Fab;
