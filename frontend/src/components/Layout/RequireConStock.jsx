import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { Spinner, Center } from '@chakra-ui/react';
import { useModoInventario } from '../../hooks/useModoInventario';

/**
 * D6 — Protege las rutas de Inventario. En empresas 'sin_stock' redirige al
 * dashboard (sin error) si alguien entra por URL directa.
 */
const RequireConStock = () => {
  const { conStock, isLoading } = useModoInventario();
  if (isLoading) return <Center py={10}><Spinner /></Center>;
  if (!conStock) return <Navigate to="/app/dashboard" replace />;
  return <Outlet />;
};

export default RequireConStock;
