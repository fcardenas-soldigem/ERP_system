import React from 'react';
import {
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  IconButton,
  HStack,
  useToast
} from '@chakra-ui/react';
import { EditIcon, DeleteIcon } from '@chakra-ui/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../utils/api';

const StockTable = ({ onEdit }) => {
  const queryClient = useQueryClient();
  const toast = useToast();

  const { data: stocks = [], isLoading } = useQuery({
    queryKey: ['stocks'],
    queryFn: async () => {
      const response = await api.get('/api/inventario/stocks/');
      return response.data;
    }
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => api.delete(`/api/inventario/stocks/${id}/`),
    onSuccess: () => {
      queryClient.invalidateQueries(['stocks']);
      toast({
        title: 'Stock eliminado',
        status: 'success',
        duration: 2000,
      });
    },
    onError: (error) => {
      console.error('Error:', error);
      toast({
        title: 'Error',
        description: 'No se pudo eliminar el stock',
        status: 'error',
        duration: 3000,
      });
    }
  });

  if (isLoading) {
    return <div>Cargando...</div>;
  }

  return (
    <Table variant="simple">
      <Thead>
        <Tr>
          <Th>Producto</Th>
          <Th>Almacén</Th>
          <Th>Cantidad</Th>
          <Th>Acciones</Th>
        </Tr>
      </Thead>
      <Tbody>
        {stocks.map((stock) => (
          <Tr key={stock.id}>
            <Td>{stock.producto_nombre}</Td>
            <Td>{stock.almacen_nombre}</Td>
            <Td>{stock.cantidad}</Td>
            <Td>
              <HStack spacing={2}>
                <IconButton
                  icon={<EditIcon />}
                  onClick={() => onEdit(stock)}
                  aria-label="Editar"
                  size="sm"
                />
                <IconButton
                  icon={<DeleteIcon />}
                  onClick={() => deleteMutation.mutate(stock.id)}
                  aria-label="Eliminar"
                  size="sm"
                  colorScheme="red"
                />
              </HStack>
            </Td>
          </Tr>
        ))}
      </Tbody>
    </Table>
  );
};

export default StockTable; 