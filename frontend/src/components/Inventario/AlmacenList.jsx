import React, { useState } from 'react';
import {
  Box,
  Button,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  IconButton,
  useDisclosure,
  Spinner,
  Text,
  HStack
} from '@chakra-ui/react';
import { AddIcon, EditIcon } from '@chakra-ui/icons';
import { useQuery } from '@tanstack/react-query';
import { inventarioAPI } from '../../lib/api';
import AlmacenForm from './AlmacenForm';

const AlmacenList = () => {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedAlmacen, setSelectedAlmacen] = useState(null);

  const { data: almacenes, isLoading } = useQuery({
    queryKey: ['almacenes'],
    queryFn: () => inventarioAPI.getAlmacenes()
  });

  if (isLoading) return <Spinner />;

  return (
    <Box>
      <HStack justify="space-between" mb={4}>
        <Text fontSize="xl">Lista de Almacenes</Text>
        <Button 
          leftIcon={<AddIcon />} 
          colorScheme="blue" 
          onClick={() => {
            setSelectedAlmacen(null);
            onOpen();
          }}
        >
          Añadir Almacén
        </Button>
      </HStack>

      <Table variant="simple">
        <Thead>
          <Tr>
            <Th>Nombre</Th>
            <Th>Ubicación</Th>
            <Th>Acciones</Th>
          </Tr>
        </Thead>
        <Tbody>
          {almacenes?.data?.map((almacen) => (
            <Tr key={almacen.id}>
              <Td>{almacen.nombre}</Td>
              <Td>{almacen.ubicacion}</Td>
              <Td>
                <IconButton
                  icon={<EditIcon />}
                  aria-label="Editar"
                  onClick={() => {
                    setSelectedAlmacen(almacen);
                    onOpen();
                  }}
                />
              </Td>
            </Tr>
          ))}
        </Tbody>
      </Table>

      <AlmacenForm
        isOpen={isOpen}
        onClose={onClose}
        almacenInicial={selectedAlmacen}
      />
    </Box>
  );
};

export default AlmacenList; 