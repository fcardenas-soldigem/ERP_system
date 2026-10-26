import React, { useCallback, useState } from 'react';
import { Outlet, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import AnimatedSidebar from './AnimatedSidebar';
import EmpresaCheck from './EmpresaCheck';
import AppLoading from '../common/AppLoading';
import BottomNav, { BOTTOM_NAV_H } from './mobile/BottomNav';
import MasSheet from './mobile/MasSheet';
import { useEsMovil } from '../../hooks/useEsMovil';
import { Box, Flex } from '@chakra-ui/react';

// Móvil: el contenido deja libre la barra inferior (+ safe-area) y el FAB.
const MOVIL_CONTENIDO = {
  p: 4,
  pb: `calc(${BOTTOM_NAV_H} + env(safe-area-inset-bottom) + 88px)`,
};

const Layout = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();
  const esMovil = useEsMovil();
  const [masAbierto, setMasAbierto] = useState(false);
  const cerrarMas = useCallback(() => setMasAbierto(false), []);

  if (isLoading) return <AppLoading />;

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return (
    <EmpresaCheck>
      <Flex minH="100vh" bg="bg.default">
        {/* Escritorio: una sola navegación, el sidebar (tema y cerrar sesión
            viven en su bloque de usuario). Móvil (< md): barra inferior. */}
        <AnimatedSidebar />
        <Box flex="1" overflow="auto" minW={0}>
          <Box p={6} {...(esMovil ? MOVIL_CONTENIDO : {})}>
            <Outlet />
          </Box>
        </Box>
        {esMovil && (
          <>
            <BottomNav masAbierto={masAbierto} onMas={() => setMasAbierto((v) => !v)} />
            <MasSheet abierto={masAbierto} onClose={cerrarMas} />
          </>
        )}
      </Flex>
    </EmpresaCheck>
  );
};

export default Layout;
