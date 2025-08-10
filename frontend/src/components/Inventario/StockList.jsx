import React from 'react';
import {
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Box,
  Badge,
  Text,
  Spinner,
  useToast,
  Button,
  Flex
} from '@chakra-ui/react';
import { DownloadIcon } from '@chakra-ui/icons';
import { useQuery } from '@tanstack/react-query';
import { productosService } from '../../services/productos.service';

const StockList = () => {
  const toast = useToast();

  const { data: productos = [], isLoading, error } = useQuery({
    queryKey: ['productos'],
    queryFn: productosService.getProductos,
  });

  if (isLoading) return <Spinner />;
  
  if (error) {
    toast({
      title: 'Error al cargar productos',
      description: error.message,
      status: 'error',
      duration: 3000,
      isClosable: true,
    });
    return <Text>Error al cargar los datos</Text>;
  }

  const getEstadoColor = (estado) => {
    switch (estado) {
      case 'Disponible':
        return 'green';
      case 'Sin Stock':
        return 'red';
      case 'Stock Bajo':
        return 'yellow';
      default:
        return 'gray';
    }
  };

  const handleExportarInventario = () => {
    // Aquí se implementará la lógica para exportar el inventario
    toast({
      title: 'Exportando inventario',
      description: 'La exportación se iniciará en breve',
      status: 'info',
      duration: 3000,
      isClosable: true,
    });
  };

  return (
    <Box overflowX="auto">
      <Flex justify="flex-end" mb={4}>
        <Button leftIcon={<DownloadIcon />} colorScheme="blue" onClick={handleExportarInventario}>
          Exportar Inventario
        </Button>
      </Flex>
      <Table variant="simple">
        <Thead>
          <Tr>
            <Th>SKU</Th>
            <Th>Nombre</Th>
            <Th>Descripción</Th>
            <Th isNumeric>Stock Total</Th>
            <Th isNumeric>Stock Mínimo</Th>
            <Th>Estado</Th>
            <Th>Categoría</Th>
          </Tr>
        </Thead>
        <Tbody>
          {productos.map((producto) => (
            <Tr key={producto.id}>
              <Td>{producto.sku}</Td>
              <Td>{producto.nombre}</Td>
              <Td>{producto.descripcion}</Td>
              <Td isNumeric>{producto.stock_total}</Td>
              <Td isNumeric>{producto.stock_minimo}</Td>
              <Td>
                <Badge
                  colorScheme={getEstadoColor(producto.get_estado_display)}
                >
                  {producto.get_estado_display}
                </Badge>
              </Td>
              <Td>{producto.categoria_nombre}</Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
      {(!productos || productos.length === 0) && (
        <Text mt={4} textAlign="center">No hay productos registrados</Text>
      )}
    </Box>
  );
};

export default StockList; 