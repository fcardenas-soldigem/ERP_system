import React from 'react';
import {
  Box,
  Heading,
  Text,
  Flex,
  useDisclosure,
} from '@chakra-ui/react';
import ComprasList from './ComprasList';
import ImportarCompras from './ImportarCompras';
import ComprasChatBar from './ComprasChatBar';

const Compras = () => {
  const { isOpen, onOpen, onClose } = useDisclosure();
  
  return (
    <>
      <Box p={4}>
        <ComprasList />
        <ImportarCompras isOpen={isOpen} onClose={onClose} />
      </Box>
      
      {/* Chatbar flotante del asistente de compras */}
      <ComprasChatBar />
    </>
  );
};

export default Compras;