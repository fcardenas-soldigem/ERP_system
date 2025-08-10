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
import { inventarioAPI } from '../../api';
import CategoriaForm from './CategoriaForm';

const CategoriaList = () => {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedCategoria, setSelectedCategoria] = useState(null);

  const { data: categorias, isLoading } = useQuery({
    queryKey: ['categorias'],
    queryFn: () => inventarioAPI.getCategorias()
  });

  if (isLoading) return <Spinner />;

  return (
    <Box>
      <HStack justify="space-between" mb={4}>
        <Text fontSize="xl">Lista de Categorías</Text>
        <Button 
          leftIcon={<AddIcon />} 
          colorScheme="blue" 
          onClick={() => {
            setSelectedCategoria(null);
            onOpen();
          }}
        >
          Añadir Categoría
        </Button>
      </HStack>

      <Table variant="simple">
        <Thead>
          <Tr>
            <Th>Nombre</Th>
            <Th>Descripción</Th>
            <Th>Acciones</Th>
          </Tr>
        </Thead>
        <Tbody>
          {categorias?.data?.map((categoria) => (
            <Tr key={categoria.id}>
              <Td>{categoria.nombre}</Td>
              <Td>{categoria.descripcion}</Td>
              <Td>
                <IconButton
                  icon={<EditIcon />}
                  aria-label="Editar"
                  onClick={() => {
                    setSelectedCategoria(categoria);
                    onOpen();
                  }}
                />
              </Td>
            </Tr>
          ))}
        </Tbody>
      </Table>

      <CategoriaForm
        isOpen={isOpen}
        onClose={onClose}
        categoriaInicial={selectedCategoria}
      />
    </Box>
  );
};

export default CategoriaList; 