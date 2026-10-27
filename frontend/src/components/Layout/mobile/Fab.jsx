import React, { useCallback, useState } from 'react';
import { Box, Icon } from '@chakra-ui/react';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus } from 'lucide-react';
import { BOTTOM_NAV_H } from './BottomNav';
import HojaAcciones from './HojaAcciones';
import { CREAR_DOCUMENTO } from '../navConfig';

const MotionBox = motion(Box);

/**
 * Botón flotante "+" — solo móvil, solo en las listas de CREAR_DOCUMENTO.
 * Un tipo de documento: navega directo. Varios: hoja inferior para elegir.
 */
const Fab = () => {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [hojaAbierta, setHojaAbierta] = useState(false);
  const cerrarHoja = useCallback(() => setHojaAbierta(false), []);
  const crear = CREAR_DOCUMENTO[pathname.replace(/\/$/, '')];

  const onFab = () => {
    if (crear.documentos.length === 1) navigate(crear.documentos[0].path);
    else setHojaAbierta(true);
  };

  return (
    <>
      <AnimatePresence>
        {crear && (
          <MotionBox
            key="fab"
            as="button"
            type="button"
            aria-label={crear.titulo}
            aria-haspopup={crear.documentos.length > 1 ? 'dialog' : undefined}
            title={crear.titulo}
            onClick={onFab}
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

      <HojaAcciones
        abierta={hojaAbierta && Boolean(crear)}
        titulo={crear?.titulo}
        opciones={(crear?.documentos ?? []).map((d) => ({
          label: d.label,
          icon: d.icon,
          onClick: () => { cerrarHoja(); navigate(d.path); },
        }))}
        onClose={cerrarHoja}
      />
    </>
  );
};

export default Fab;
