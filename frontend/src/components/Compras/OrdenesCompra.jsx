import React, { useState } from 'react';
import {
  Box,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Button,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  FormControl,
  FormLabel,
  Input,
  Select,
  NumberInput,
  NumberInputField,
  VStack,
  HStack,
  Badge,
  IconButton,
  Tooltip,
  Checkbox,
  useToast,
  TableContainer,
  InputGroup,
  InputLeftElement,
  Spinner,
} from '@chakra-ui/react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AddIcon, CheckIcon, CloseIcon, DownloadIcon, SearchIcon } from '@chakra-ui/icons';
import { comprasService } from '../../services/compras.service';

const OrdenesCompra = () => {
  const queryClient = useQueryClient();
  const toast = useToast();
  const empresaId = localStorage.getItem('empresa_id');

  // Estados
  const [searchTerm, setSearchTerm] = useState('');
  const [filterTerm, setFilterTerm] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [nuevaOrden, setNuevaOrden] = useState({
    proveedor: '',
    almacen: '',
    producto: '',
    cantidad: 0,
    precio_unitario: 0,
    sku: '',
    estado: 'borrador',
    igv_incluido: false
  });

  // Queries
  const { data: ordenesData, isLoading: loadingOrdenes } = useQuery({
    queryKey: ['ordenesCompra', empresaId],
    queryFn: () => comprasService.getOrdenes(empresaId),
    select: (data) => {
      // Asegurarnos de que data sea un array
      return Array.isArray(data) ? data : [];
    }
  });

  const { data: proveedores = [], isLoading: loadingProveedores } = useQuery({
    queryKey: ['proveedores'],
    queryFn: () => comprasService.getProveedores(),
    select: (data) => Array.isArray(data) ? data : []
  });

  // Mutations
  const aprobarOrdenMutation = useMutation({
    mutationFn: (id) => comprasService.aprobarOrden(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['ordenesCompra']);
      toast({
        title: 'Éxito',
        description: 'Orden aprobada correctamente',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    }
  });

  const crearOrdenMutation = useMutation({
    mutationFn: (ordenData) => comprasService.createOrdenCompra(ordenData),
    onSuccess: () => {
      queryClient.invalidateQueries(['ordenesCompra']);
      setShowModal(false);
      toast({
        title: 'Éxito',
        description: 'Orden creada correctamente',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      setNuevaOrden({
        proveedor: '',
        almacen: '',
        producto: '',
        cantidad: 0,
        precio_unitario: 0,
        sku: '',
        estado: 'borrador',
        igv_incluido: false
      });
    }
  });

  // Handlers
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setNuevaOrden(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = () => {
    crearOrdenMutation.mutate({
      ...nuevaOrden,
      empresa: empresaId
    });
  };

  const getEstadoBadge = (estado) => {
    const colorScheme = {
      'borrador': 'gray',
      'pendiente': 'yellow',
      'aprobada': 'green',
      'recibida': 'blue',
      'cancelada': 'red'
    };
    return (
      <Badge colorScheme={colorScheme[estado]}>
        {estado.toUpperCase()}
      </Badge>
    );
  };

  if (loadingOrdenes) {
    return (
      <Box display="flex" justifyContent="center" p={4}>
        <Spinner size="xl" />
      </Box>
    );
  }

  return (
    <Box>
      <HStack mb={4} spacing={4}>
        <InputGroup maxW="300px">
          <InputLeftElement pointerEvents="none">
            <SearchIcon color="gray.300" />
          </InputLeftElement>
          <Input
            placeholder="Buscar por ID o proveedor..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </InputGroup>

        <Select
          maxW="200px"
          value={filterTerm}
          onChange={(e) => setFilterTerm(e.target.value)}
        >
          <option value="">Todos los estados</option>
          <option value="borrador">Borrador</option>
          <option value="pendiente">Pendiente</option>
          <option value="aprobada">Aprobada</option>
          <option value="recibida">Recibida</option>
          <option value="cancelada">Cancelada</option>
        </Select>

        <Button
          leftIcon={<AddIcon />}
          colorScheme="blue"
          onClick={() => setShowModal(true)}
        >
          Nueva Orden
        </Button>
      </HStack>

      <TableContainer>
        <Table variant="simple">
          <Thead>
            <Tr>
              <Th>Número</Th>
              <Th>Fecha</Th>
              <Th>Proveedor</Th>
              <Th>Producto</Th>
              <Th>Cantidad</Th>
              <Th>Total</Th>
              <Th>Estado</Th>
              <Th>Acciones</Th>
            </Tr>
          </Thead>
          <Tbody>
            {Array.isArray(ordenesData) && ordenesData.length > 0 ? (
              ordenesData.map((orden) => (
                <Tr key={orden.id}>
                  <Td>{orden.numero_orden}</Td>
                  <Td>{new Date(orden.fecha).toLocaleDateString()}</Td>
                  <Td>{orden.proveedor_nombre}</Td>
                  <Td>{orden.producto_nombre}</Td>
                  <Td>{orden.cantidad}</Td>
                  <Td>${orden.total?.toFixed(2)}</Td>
                  <Td>{getEstadoBadge(orden.estado)}</Td>
                  <Td>
                    <HStack spacing={2}>
                      {orden.estado === 'pendiente' && (
                        <Tooltip label="Aprobar orden">
                          <IconButton
                            icon={<CheckIcon />}
                            colorScheme="green"
                            onClick={() => aprobarOrdenMutation.mutate(orden.id)}
                            aria-label="Aprobar orden"
                          />
                        </Tooltip>
                      )}
                    </HStack>
                  </Td>
                </Tr>
              ))
            ) : (
              <Tr>
                <Td colSpan={8} textAlign="center">
                  No hay órdenes de compra disponibles
                </Td>
              </Tr>
            )}
          </Tbody>
        </Table>
      </TableContainer>

      <Modal isOpen={showModal} onClose={() => setShowModal(false)}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Nueva Orden de Compra</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel>Proveedor</FormLabel>
                <Select
                  name="proveedor"
                  value={nuevaOrden.proveedor}
                  onChange={handleInputChange}
                >
                  <option value="">Seleccione un proveedor</option>
                  {proveedores.length > 0 ? (
                    proveedores.map(prov => (
                      <option key={prov.id} value={prov.id}>
                        {prov.nombre}
                      </option>
                    ))
                  ) : (
                    <option value="" disabled>No hay proveedores disponibles</option>
                  )}
                </Select>
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Cantidad</FormLabel>
                <NumberInput min={1}>
                  <NumberInputField
                    name="cantidad"
                    value={nuevaOrden.cantidad}
                    onChange={handleInputChange}
                  />
                </NumberInput>
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Precio Unitario</FormLabel>
                <NumberInput min={0} precision={2}>
                  <NumberInputField
                    name="precio_unitario"
                    value={nuevaOrden.precio_unitario}
                    onChange={handleInputChange}
                  />
                </NumberInput>
              </FormControl>

              <FormControl>
                <Checkbox
                  name="igv_incluido"
                  isChecked={nuevaOrden.igv_incluido}
                  onChange={(e) => handleInputChange({
                    target: {
                      name: 'igv_incluido',
                      value: e.target.checked
                    }
                  })}
                >
                  IGV Incluido
                </Checkbox>
              </FormControl>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button colorScheme="blue" mr={3} onClick={handleSubmit}>
              Crear Orden
            </Button>
            <Button onClick={() => setShowModal(false)}>Cancelar</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default OrdenesCompra; 