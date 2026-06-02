import React, { useEffect, useState } from 'react';
import {
  Box, Heading, Button, Table, Thead, Tbody, Tr, Th, Td, TableContainer,
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalCloseButton, ModalBody,
  FormControl, FormLabel, Input, Select, SimpleGrid, VStack, HStack, IconButton,
  useDisclosure,
} from '@chakra-ui/react';
import { DeleteIcon, AddIcon } from '@chakra-ui/icons';
import { api } from '../../lib/api';

const OrdenesVenta = () => {
  const [ordenesVenta, setOrdenesVenta] = useState([]);
  const [clientes, setClientes] = useState([]);
  const [productos, setProductos] = useState([]);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [nuevaOrden, setNuevaOrden] = useState({
    cliente: '', fecha: '', estado: 'pendiente', productos: []
  });

  useEffect(() => {
    fetchOrdenesVenta();
    fetchClientes();
    fetchProductos();
  }, []);

  const fetchOrdenesVenta = async () => {
    try {
      const response = await api.get('ventas/ordenes/');
      setOrdenesVenta(response.data);
    } catch (error) { console.error('Error al obtener órdenes de venta:', error); }
  };

  const fetchClientes = async () => {
    try {
      const response = await api.get('ventas/clientes/');
      setClientes(response.data);
    } catch (error) { console.error('Error al obtener clientes:', error); }
  };

  const fetchProductos = async () => {
    try {
      const response = await api.get('inventario/productos/');
      setProductos(response.data);
    } catch (error) { console.error('Error al obtener productos:', error); }
  };

  const handleInputChange = (e) => {
    setNuevaOrden({ ...nuevaOrden, [e.target.name]: e.target.value });
  };

  const handleProductoChange = (index, field, value) => {
    const nuevosProductos = [...nuevaOrden.productos];
    nuevosProductos[index][field] = value;
    setNuevaOrden({ ...nuevaOrden, productos: nuevosProductos });
  };

  const agregarProducto = () => {
    setNuevaOrden({
      ...nuevaOrden,
      productos: [...nuevaOrden.productos, { producto: '', cantidad: 1, precio: 0 }]
    });
  };

  const eliminarProducto = (index) => {
    const nuevosProductos = [...nuevaOrden.productos];
    nuevosProductos.splice(index, 1);
    setNuevaOrden({ ...nuevaOrden, productos: nuevosProductos });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await api.post('ventas/ordenes/', nuevaOrden);
      fetchOrdenesVenta();
      onClose();
      setNuevaOrden({ cliente: '', fecha: '', estado: 'pendiente', productos: [] });
    } catch (error) { console.error('Error al crear orden de venta:', error); }
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`ventas/ordenes/${id}/`);
      fetchOrdenesVenta();
    } catch (error) { console.error('Error al eliminar orden de venta:', error); }
  };

  return (
    <Box mt={5}>
      <HStack justify="space-between" mb={4}>
        <Heading size="md">Órdenes de Venta</Heading>
        <Button colorScheme="blue" leftIcon={<AddIcon />} onClick={onOpen}>
          Crear Orden de Venta
        </Button>
      </HStack>

      <TableContainer bg="white" borderRadius="lg" shadow="sm">
        <Table variant="simple">
          <Thead><Tr>
            <Th>ID Orden</Th><Th>Cliente</Th><Th>Fecha</Th><Th>Estado</Th><Th>Acciones</Th>
          </Tr></Thead>
          <Tbody>
            {ordenesVenta.map((orden) => (
              <Tr key={orden.id}>
                <Td>{orden.id}</Td>
                <Td>{orden.cliente.nombre}</Td>
                <Td>{orden.fecha}</Td>
                <Td>{orden.estado}</Td>
                <Td>
                  <Button size="sm" colorScheme="red" onClick={() => handleDelete(orden.id)}>
                    Eliminar
                  </Button>
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      </TableContainer>

      <Modal isOpen={isOpen} onClose={onClose} size="xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Crear Orden de Venta</ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            <form onSubmit={handleSubmit}>
              <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} mb={4}>
                <FormControl isRequired>
                  <FormLabel>Cliente</FormLabel>
                  <Select name="cliente" value={nuevaOrden.cliente} onChange={handleInputChange} placeholder="Selecciona un cliente">
                    {clientes.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
                  </Select>
                </FormControl>
                <FormControl isRequired>
                  <FormLabel>Fecha</FormLabel>
                  <Input type="date" name="fecha" value={nuevaOrden.fecha} onChange={handleInputChange} />
                </FormControl>
                <FormControl isRequired>
                  <FormLabel>Estado</FormLabel>
                  <Select name="estado" value={nuevaOrden.estado} onChange={handleInputChange}>
                    <option value="pendiente">Pendiente</option>
                    <option value="completada">Completada</option>
                    <option value="cancelada">Cancelada</option>
                  </Select>
                </FormControl>
              </SimpleGrid>

              <Heading size="sm" mb={3}>Productos</Heading>
              <VStack spacing={3} align="stretch">
                {nuevaOrden.productos.map((prod, index) => (
                  <HStack key={index} p={3} border="1px" borderColor="gray.200" borderRadius="md">
                    <FormControl flex={5}>
                      <Select value={prod.producto} onChange={(e) => handleProductoChange(index, 'producto', e.target.value)} placeholder="Selecciona un producto">
                        {productos.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
                      </Select>
                    </FormControl>
                    <FormControl flex={2}>
                      <Input type="number" min="1" value={prod.cantidad} onChange={(e) => handleProductoChange(index, 'cantidad', e.target.value)} />
                    </FormControl>
                    <FormControl flex={2}>
                      <Input type="number" min="0" value={prod.precio} onChange={(e) => handleProductoChange(index, 'precio', e.target.value)} />
                    </FormControl>
                    <IconButton icon={<DeleteIcon />} colorScheme="red" variant="ghost" onClick={() => eliminarProducto(index)} />
                  </HStack>
                ))}
              </VStack>
              <HStack mt={4} spacing={4}>
                <Button variant="outline" onClick={agregarProducto}>Agregar Producto</Button>
                <Button colorScheme="blue" type="submit">Crear Orden</Button>
              </HStack>
            </form>
          </ModalBody>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default OrdenesVenta;
