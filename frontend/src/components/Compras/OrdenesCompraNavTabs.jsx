import React from 'react';
import { HStack, Button } from '@chakra-ui/react';
import { FaBox, FaTools } from 'react-icons/fa';
import { useNavigate, useLocation } from 'react-router-dom';

const OrdenesCompraNavTabs = () => {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const esServicio = pathname.includes('/ordenes-servicio') || pathname.includes('/orden-servicio');

  return (
    <HStack spacing={2} mb={5}>
      <Button
        leftIcon={<FaBox />}
        size="sm"
        variant={!esServicio ? 'solid' : 'outline'}
        colorScheme={!esServicio ? 'blue' : 'gray'}
        onClick={() => navigate('/app/compras/ordenes')}
      >
        Productos
      </Button>
      <Button
        leftIcon={<FaTools />}
        size="sm"
        variant={esServicio ? 'solid' : 'outline'}
        colorScheme={esServicio ? 'purple' : 'gray'}
        onClick={() => navigate('/app/compras/ordenes-servicio')}
      >
        Servicios de Reparación
      </Button>
    </HStack>
  );
};

export default OrdenesCompraNavTabs;
