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
  HStack,
  useToast,
  Badge
} from '@chakra-ui/react';
import { AddIcon, EditIcon, DeleteIcon, WarningIcon } from '@chakra-ui/icons';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { inventarioAPI } from '../../api';
import ProductoForm from './ProductoForm';

const ProductoList = ({ categorias, estadisticas }) => {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedProducto, setSelectedProducto] = useState(null);
  const queryClient = useQueryClient();
  const toast = useToast();

  // Consulta para obtener productos
  const { data: productos, isLoading, error } = useQuery({
    queryKey: ['productos'],
    queryFn: async () => {
      const response = await inventarioAPI.getProductos();
      // Asegurarse de que productos sea un array
      return Array.isArray(response.data) ? response.data : [];
    },
    refetchOnMount: true,
    refetchInterval: 5000,
    onError: (error) => {
      toast({
        title: 'Error',
        description: 'No se pudieron cargar los productos',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  });

  const handleAddClick = () => {
    setSelectedProducto(null);
    onOpen();
  };

  const handleEditClick = (producto) => {
    setSelectedProducto(producto);
    onOpen();
  };

  const handleDelete = async (id) => {
    if (window.confirm('¿Está seguro de eliminar este producto?')) {
      try {
        await inventarioAPI.deleteProducto(id);
        toast({
          title: 'Éxito',
          description: 'Producto eliminado correctamente',
          status: 'success',
          duration: 2000,
          isClosable: true,
        });
        queryClient.invalidateQueries(['productos']);
      } catch (error) {
        toast({
          title: 'Error',
          description: 'No se pudo eliminar el producto',
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
      }
    }
  };

  if (isLoading) return <Spinner />;
  if (error) return <Text>Error al cargar los productos</Text>;

  // Asegurarse de que productos sea un array antes de usar map
  const productosArray = productos || [];

  return (
    <Box>
      <HStack justify="space-between" mb={4}>
        <Text fontSize="xl">Lista de Productos</Text>
        <Button leftIcon={<AddIcon />} colorScheme="blue" onClick={handleAddClick}>
          Añadir Producto
        </Button>
      </HStack>

      <Table variant="simple">
        <Thead>
          <Tr>
            <Th>SKU</Th>
            <Th>Nombre</Th>
            <Th>Descripción</Th>
            <Th>Precio</Th>
            <Th>Stock Total</Th>
            <Th>Stock Mínimo</Th>
            <Th>Estado</Th>
            <Th>Categoría</Th>
            <Th>Almacén</Th>
            <Th>Acciones</Th>
          </Tr>
        </Thead>
        <Tbody>
          {productosArray.map((producto) => (
            <Tr key={producto.id}>
              <Td>{producto.sku}</Td>
              <Td>{producto.nombre}</Td>
              <Td>{producto.descripcion}</Td>
              <Td>${producto.precio}</Td>
              <Td>
                {producto.stock_total}
                {producto.alerta_stock && (
                  <WarningIcon color="red.500" ml={2} />
                )}
              </Td>
              <Td>{producto.stock_minimo}</Td>
              <Td>
                <Badge
                  colorScheme={producto.alerta_stock ? 'red' : 'green'}
                >
                  {producto.alerta_stock ? 'Stock Bajo' : 'Normal'}
                </Badge>
              </Td>
              <Td>{categorias.find(c => c.id === producto.categoria)?.nombre || 'N/A'}</Td>
              <Td>{producto.almacen_nombre}</Td>
              <Td>
                <HStack spacing={2}>
                  <IconButton
                    icon={<EditIcon />}
                    aria-label="Editar"
                    size="sm"
                    onClick={() => handleEditClick(producto)}
                  />
                  <IconButton
                    icon={<DeleteIcon />}
                    aria-label="Eliminar"
                    size="sm"
                    colorScheme="red"
                    onClick={() => handleDelete(producto.id)}
                  />
                </HStack>
              </Td>
            </Tr>
          ))}
        </Tbody>
      </Table>

      <ProductoForm
        isOpen={isOpen}
        onClose={() => {
          onClose();
          queryClient.invalidateQueries(['productos']);
        }}
        productoInicial={selectedProducto}
        categorias={categorias}
      />
    </Box>
  );
};

export default ProductoList;