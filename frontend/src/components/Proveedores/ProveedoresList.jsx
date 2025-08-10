import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Container,
  Flex,
  Input,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  IconButton,
  useToast,
  InputGroup,
  InputLeftElement,
  Stack,
  Text,
  Badge,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import { SearchIcon, EditIcon, DeleteIcon } from '@chakra-ui/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { proveedoresService } from '../../services/proveedores.service';
import { useNavigate } from 'react-router-dom';

const ProveedoresList = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();

  // Verificar que tenemos el ID de empresa
  useEffect(() => {
    const empresaId = localStorage.getItem('empresa_id');
    console.log('ID de empresa en localStorage:', empresaId);
  }, []);

  const { data: proveedoresData, isLoading, error, refetch } = useQuery({
    queryKey: ['proveedores'],
    queryFn: proveedoresService.getProveedores,
    select: (data) => {
      console.log('Datos recibidos en select:', data);
      // Si data es null o undefined, retornar array vacío
      if (!data) return [];
      // Si ya es un array, retornarlo
      if (Array.isArray(data)) return data;
      // Si tiene una propiedad results que es un array, retornar eso
      if (Array.isArray(data.results)) return data.results;
      // Si es un objeto, convertirlo en array
      if (typeof data === 'object') return [data];
      // Por defecto retornar array vacío
      return [];
    },
    onError: (error) => {
      console.error('Error en la consulta:', error);
      toast({
        title: 'Error al cargar los proveedores',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  });

  useEffect(() => {
    console.log('Estado actual de proveedoresData:', proveedoresData);
  }, [proveedoresData]);

  const deleteMutation = useMutation({
    mutationFn: proveedoresService.eliminarProveedor,
    onSuccess: () => {
      queryClient.invalidateQueries(['proveedores']);
      toast({
        title: 'Proveedor eliminado',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    },
    onError: (error) => {
      toast({
        title: 'Error al eliminar el proveedor',
        description: error.message,
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    },
  });

  const handleEdit = (proveedor) => {
    navigate(`/proveedores/${proveedor.id}/editar`);
  };

  const handleDelete = async (id) => {
    if (window.confirm('¿Estás seguro de que deseas eliminar este proveedor?')) {
      deleteMutation.mutate(id);
    }
  };

  const filteredProveedores = proveedoresData?.filter(proveedor =>
    proveedor.razon_social?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    proveedor.ruc?.includes(searchTerm) ||
    proveedor.telefono?.includes(searchTerm) ||
    proveedor.direccion?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    proveedor.email?.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  if (isLoading) return <Text>Cargando proveedores...</Text>;
  
  if (error) {
    return (
      <Alert status="error">
        <AlertIcon />
        <Box>
          <Text fontWeight="bold">Error al cargar los proveedores</Text>
          <Text>{error.message}</Text>
          <Button mt={2} onClick={() => refetch()}>Reintentar</Button>
        </Box>
      </Alert>
    );
  }

  return (
    <Container maxW="container.xl" py={5}>
      <Stack spacing={5}>
        <InputGroup>
          <InputLeftElement pointerEvents="none">
            <SearchIcon color="gray.300" />
          </InputLeftElement>
          <Input
            placeholder="Buscar por razón social, RUC, teléfono, dirección o email..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </InputGroup>

        {(!proveedoresData || proveedoresData.length === 0) ? (
          <Alert status="info">
            <AlertIcon />
            No hay proveedores registrados
          </Alert>
        ) : (
          <Box overflowX="auto">
            <Table variant="simple">
              <Thead>
                <Tr>
                  <Th>RUC</Th>
                  <Th>Razón Social</Th>
                  <Th>Dirección</Th>
                  <Th>Teléfono</Th>
                  <Th>Email</Th>
                  <Th>Estado</Th>
                  <Th>Acciones</Th>
                </Tr>
              </Thead>
              <Tbody>
                {filteredProveedores.map((proveedor) => (
                  <Tr key={proveedor.id}>
                    <Td>{proveedor.ruc}</Td>
                    <Td>{proveedor.razon_social}</Td>
                    <Td>
                      <Text fontSize="sm" noOfLines={2} maxW="200px">
                        {proveedor.direccion || '-'}
                      </Text>
                    </Td>
                    <Td>{proveedor.telefono || '-'}</Td>
                    <Td>
                      <Text fontSize="sm" noOfLines={1} maxW="150px">
                        {proveedor.email || '-'}
                      </Text>
                    </Td>
                    <Td>
                      <Badge
                        colorScheme={proveedor.activo ? 'green' : 'red'}
                      >
                        {proveedor.activo ? 'ACTIVO' : 'INACTIVO'}
                      </Badge>
                    </Td>
                    <Td>
                      <Flex gap={2}>
                        <IconButton
                          icon={<EditIcon />}
                          onClick={() => handleEdit(proveedor)}
                          aria-label="Editar"
                          size="sm"
                        />
                        <IconButton
                          icon={<DeleteIcon />}
                          onClick={() => handleDelete(proveedor.id)}
                          aria-label="Eliminar"
                          size="sm"
                          colorScheme="red"
                        />
                      </Flex>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Box>
        )}
      </Stack>
    </Container>
  );
};

export default ProveedoresList; 