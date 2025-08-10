import React from 'react';
import ProveedoresList from '../components/Proveedores/ProveedoresList';
import { Container, Heading, Box } from '@chakra-ui/react';

const Proveedores = () => {
  return (
    <Container maxW="container.xl" py={5}>
      <Box mb={5}>
        <Heading size="lg">Directorio de Proveedores</Heading>
      </Box>
      <ProveedoresList />
    </Container>
  );
};

export default Proveedores; 