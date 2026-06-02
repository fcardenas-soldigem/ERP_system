import React from 'react';
import {
  Box,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Button,
  useDisclosure,
  Spinner,
  HStack,
  useToast,
  IconButton,
  Tooltip,
  Badge,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  FormControl,
  FormLabel,
  Input,
  Textarea,
  Select,
  VStack
} from '@chakra-ui/react';
import { AddIcon, CheckIcon } from '@chakra-ui/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { comprasService } from '../../services/compras.service';

const RecepcionCompra = () => {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { isOpen, onOpen, onClose } = useDisclosure();

  // Query para obtener recepciones
  const { data: recepciones, isLoading } = useQuery({
    queryKey: ['recepciones'],
    queryFn: () => comprasService.getRecepciones()
  });

  // Query para obtener órdenes de compra pendientes
  const { data: ordenesCompra } = useQuery({
    queryKey: ['ordenesCompra'],
    queryFn: () => comprasService.getOrdenesCompra()
  });

  // Mutación para crear nueva recepción
  const createRecepcionMutation = useMutation({
    mutationFn: (nuevaRecepcion) =>
      comprasService.createRecepcion(nuevaRecepcion),
    onSuccess: () => {
      queryClient.invalidateQueries(['recepciones']);
      toast({
        title: 'Recepción creada exitosamente',
        status: 'success',
        duration: 3000
      });
      onClose();
    },
    onError: (error) => {
      toast({
        title: 'Error al crear la recepción',
        description: error.response?.data?.detail || 'Error desconocido',
        status: 'error',
        duration: 3000
      });
    }
  });

  // Mutación para confirmar recepción
  const confirmarRecepcionMutation = useMutation({
    mutationFn: (recepcionId) =>
      comprasService.confirmarRecepcion(recepcionId),
    onSuccess: () => {
      queryClient.invalidateQueries(['recepciones']);
      toast({
        title: 'Recepción confirmada',
        status: 'success',
        duration: 3000
      });
    }
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const nuevaRecepcion = {
      orden_compra: formData.get('orden_compra'),
      fecha_recepcion: formData.get('fecha_recepcion'),
      recibido_por: formData.get('recibido_por'),
      notas: formData.get('notas')
    };
    createRecepcionMutation.mutate(nuevaRecepcion);
  };

  const handleConfirmar = (recepcionId) => {
    confirmarRecepcionMutation.mutate(recepcionId);
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" p={4}>
        <Spinner size="xl" />
      </Box>
    );
  }

  return (
    <Box>
      <HStack spacing={4} mb={4} justify="space-between">
        <Button 
          leftIcon={<AddIcon />}
          colorScheme="blue" 
          onClick={onOpen}
        >
          Nueva Recepción
        </Button>
      </HStack>

      <Table variant="simple">
        <Thead>
          <Tr>
            <Th>Orden de Compra</Th>
            <Th>Proveedor</Th>
            <Th>Fecha Recepción</Th>
            <Th>Recibido Por</Th>
            <Th>Notas</Th>
            <Th>Estado</Th>
            <Th>Acciones</Th>
          </Tr>
        </Thead>
        <Tbody>
          {recepciones?.map((recepcion) => (
            <Tr key={recepcion.id}>
              <Td>{recepcion.orden_compra_numero}</Td>
              <Td>{recepcion.orden_compra_proveedor}</Td>
              <Td>{new Date(recepcion.fecha_recepcion).toLocaleDateString()}</Td>
              <Td>{recepcion.recibido_por}</Td>
              <Td>{recepcion.notas}</Td>
              <Td>
                <Badge colorScheme="green">
                  Recibido
                </Badge>
              </Td>
              <Td>
                <Tooltip label="Confirmar recepción">
                  <IconButton
                    icon={<CheckIcon />}
                    colorScheme="green"
                    size="sm"
                    onClick={() => handleConfirmar(recepcion.id)}
                    isDisabled={recepcion.estado === 'confirmado'}
                  />
                </Tooltip>
              </Td>
            </Tr>
          ))}
        </Tbody>
      </Table>

      <Modal isOpen={isOpen} onClose={onClose} size="xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Nueva Recepción</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack as="form" spacing={4} onSubmit={handleSubmit}>
              <FormControl isRequired>
                <FormLabel>Orden de Compra</FormLabel>
                <Select name="orden_compra" placeholder="Seleccione una orden">
                  {ordenesCompra?.map(orden => (
                    <option key={orden.id} value={orden.id}>
                      {orden.numero_orden} - {orden.proveedor_nombre}
                    </option>
                  ))}
                </Select>
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Fecha de Recepción</FormLabel>
                <Input
                  name="fecha_recepcion"
                  type="date"
                  defaultValue={new Date().toISOString().split('T')[0]}
                />
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Recibido Por</FormLabel>
                <Input name="recibido_por" />
              </FormControl>

              <FormControl>
                <FormLabel>Notas</FormLabel>
                <Textarea name="notas" />
              </FormControl>
            </VStack>
          </ModalBody>

          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose}>
              Cancelar
            </Button>
            <Button 
              colorScheme="blue" 
              type="submit"
              isLoading={createRecepcionMutation.isLoading}
            >
              Guardar
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default RecepcionCompra; 