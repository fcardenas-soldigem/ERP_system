import React, { useState } from 'react';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { produccionService } from '../../services/produccion.service';
import {
  Box,
  Heading,
  Text,
  Flex,
  SimpleGrid,
  Card,
  CardHeader,
  CardBody,
  Button,
  VStack,
  HStack,
  Badge,
  Progress,
  Alert,
  AlertIcon,
  Icon,
  Spinner,
  Divider,
  useColorModeValue,
  Link,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  useDisclosure,
  useToast,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td
} from '@chakra-ui/react';
import { 
  ChevronLeftIcon,
  EditIcon,
  CopyIcon,
  DeleteIcon,
  AddIcon
} from '@chakra-ui/icons';
import { FiPackage, FiBox, FiClock, FiDollarSign, FiClipboard, FiCalendar } from 'react-icons/fi';

const RecetaDetalle = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  const { isOpen: isDeleteOpen, onOpen: onDeleteOpen, onClose: onDeleteClose } = useDisclosure();

  // Query para receta
  const { data: receta, isLoading, error } = useQuery({
    queryKey: ['receta', id],
    queryFn: () => produccionService.getReceta(id),
    select: (response) => response?.data || response
  });

  // Mutation para duplicar
  const duplicarMutation = useMutation({
    mutationFn: () => produccionService.duplicarReceta(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['recetas']);
      toast({
        title: 'Receta duplicada exitosamente',
        status: 'success',
        duration: 3000
      });
      navigate('/app/produccion/recetas');
    },
    onError: () => {
      toast({
        title: 'Error al duplicar receta',
        status: 'error',
        duration: 3000
      });
    }
  });

  // Mutation para eliminar
  const eliminarMutation = useMutation({
    mutationFn: () => produccionService.deleteReceta(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['recetas']);
      toast({
        title: 'Receta eliminada exitosamente',
        status: 'success',
        duration: 3000
      });
      navigate('/app/produccion/recetas');
    },
    onError: () => {
      toast({
        title: 'Error al eliminar receta',
        description: 'Puede que esté siendo usada en órdenes de producción',
        status: 'error',
        duration: 5000
      });
    }
  });

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('es-PE', {
      style: 'currency',
      currency: 'PEN'
    }).format(amount || 0);
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('es-PE');
  };

  if (isLoading) {
    return (
      <Box p={6}>
        <Flex justify="center" align="center" h="300px" direction="column">
          <Spinner size="xl" color="blue.500" thickness="4px" mb={4} />
          <Text color="gray.600">Cargando receta...</Text>
        </Flex>
      </Box>
    );
  }

  if (error || !receta) {
    return (
      <Box p={6}>
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          {error?.message || 'Receta no encontrada'}
        </Alert>
        <Button
          mt={4}
          leftIcon={<ChevronLeftIcon />}
          variant="ghost"
          onClick={() => navigate('/app/produccion/recetas')}
        >
          Volver a recetas
        </Button>
      </Box>
    );
  }

  const costos = receta.costos || {};

  return (
    <Box p={6}>
      {/* Header */}
      <Flex justify="space-between" align="start" mb={6} flexWrap="wrap" gap={4}>
        <HStack spacing={4}>
          <Button
            leftIcon={<ChevronLeftIcon />}
            variant="ghost"
            onClick={() => navigate('/app/produccion/recetas')}
          >
            Volver
          </Button>
          <Box>
            <HStack mb={1}>
              <Heading size="lg">{receta.nombre}</Heading>
              <Badge colorScheme={receta.is_active ? 'green' : 'gray'} fontSize="sm">
                {receta.is_active ? '✓ Activa' : 'Inactiva'}
              </Badge>
            </HStack>
            <Text color="gray.600">Versión {receta.version}</Text>
          </Box>
        </HStack>

        <HStack spacing={2}>
          <Button
            leftIcon={<EditIcon />}
            colorScheme="yellow"
            as={RouterLink}
            to={`/app/produccion/recetas/${id}/editar`}
          >
            Editar
          </Button>
          <Button
            leftIcon={<CopyIcon />}
            colorScheme="blue"
            onClick={() => duplicarMutation.mutate()}
            isLoading={duplicarMutation.isLoading}
          >
            Duplicar
          </Button>
          <Button
            leftIcon={<DeleteIcon />}
            colorScheme="red"
            onClick={onDeleteOpen}
          >
            Eliminar
          </Button>
        </HStack>
      </Flex>

      <SimpleGrid columns={{ base: 1, lg: 3 }} spacing={6}>
        {/* Contenido Principal */}
        <Box gridColumn={{ lg: 'span 2' }}>
          <VStack spacing={6} align="stretch">
            {/* Producto Terminado */}
            <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl">
              <CardHeader pb={2}>
                <HStack>
                  <Icon as={FiPackage} color="blue.500" />
                  <Heading size="md">Producto Terminado</Heading>
                </HStack>
              </CardHeader>
              <CardBody>
                <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
                  <Box>
                    <Text fontSize="sm" color="gray.500">Producto</Text>
                    <Text fontWeight="medium">{receta.producto_terminado_nombre}</Text>
                  </Box>
                  <Box>
                    <Text fontSize="sm" color="gray.500">SKU</Text>
                    <Text fontWeight="medium">{receta.producto_terminado_sku}</Text>
                  </Box>
                  <Box>
                    <Text fontSize="sm" color="gray.500">Cantidad Producida</Text>
                    <Text fontWeight="medium">{receta.cantidad_producida}</Text>
                  </Box>
                  <Box>
                    <Text fontSize="sm" color="gray.500">Tiempo Estimado</Text>
                    <Text fontWeight="medium">{receta.tiempo_estimado} minutos</Text>
                  </Box>
                </SimpleGrid>
              </CardBody>
            </Card>

            {/* Insumos */}
            <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl">
              <CardHeader pb={2}>
                <HStack>
                  <Icon as={FiBox} color="green.500" />
                  <Heading size="md">Insumos Necesarios</Heading>
                </HStack>
              </CardHeader>
              <CardBody>
                {receta.detalles && receta.detalles.length > 0 ? (
                  <Box overflowX="auto">
                    <Table size="sm" variant="simple">
                      <Thead bg="gray.50">
                        <Tr>
                          <Th>Insumo</Th>
                          <Th>SKU</Th>
                          <Th isNumeric>Cantidad</Th>
                          <Th isNumeric>Costo Unit.</Th>
                          <Th isNumeric>Costo Total</Th>
                        </Tr>
                      </Thead>
                      <Tbody>
                        {receta.detalles.map((detalle) => (
                          <Tr key={detalle.id} _hover={{ bg: 'gray.50' }}>
                            <Td>
                              <Text fontWeight="medium">{detalle.insumo_nombre}</Text>
                              {detalle.notas && (
                                <Text fontSize="xs" color="gray.500">{detalle.notas}</Text>
                              )}
                            </Td>
                            <Td>
                              <Text fontSize="sm" color="gray.500">{detalle.insumo_sku}</Text>
                            </Td>
                            <Td isNumeric>
                              {detalle.cantidad} {detalle.insumo_unidad_medida}
                            </Td>
                            <Td isNumeric>{formatCurrency(detalle.costo_unitario)}</Td>
                            <Td isNumeric fontWeight="medium">{formatCurrency(detalle.costo_total)}</Td>
                          </Tr>
                        ))}
                      </Tbody>
                      <Tbody>
                        <Tr bg="gray.50">
                          <Td colSpan={4} textAlign="right" fontWeight="medium">
                            Subtotal Insumos:
                          </Td>
                          <Td isNumeric fontWeight="bold">
                            {formatCurrency(costos.costo_insumos)}
                          </Td>
                        </Tr>
                      </Tbody>
                    </Table>
                  </Box>
                ) : (
                  <Box textAlign="center" py={8}>
                    <Icon as={FiBox} boxSize={8} color="gray.400" mb={2} />
                    <Text color="gray.500">No hay insumos definidos para esta receta</Text>
                  </Box>
                )}
              </CardBody>
            </Card>

            {/* Notas */}
            {receta.notas && (
              <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl">
                <CardHeader pb={2}>
                  <HStack>
                    <Icon as={FiClipboard} color="purple.500" />
                    <Heading size="md">Notas / Instrucciones</Heading>
                  </HStack>
                </CardHeader>
                <CardBody>
                  <Text color="gray.700" whiteSpace="pre-wrap">{receta.notas}</Text>
                </CardBody>
              </Card>
            )}

            {/* Metadatos */}
            <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl">
              <CardHeader pb={2}>
                <HStack>
                  <Icon as={FiCalendar} color="orange.500" />
                  <Heading size="md">Información del Sistema</Heading>
                </HStack>
              </CardHeader>
              <CardBody>
                <SimpleGrid columns={2} spacing={4} fontSize="sm">
                  <Box>
                    <Text color="gray.500">Creada</Text>
                    <Text fontWeight="medium">{formatDate(receta.created_at)}</Text>
                  </Box>
                  <Box>
                    <Text color="gray.500">Última modificación</Text>
                    <Text fontWeight="medium">{formatDate(receta.updated_at)}</Text>
                  </Box>
                </SimpleGrid>
              </CardBody>
            </Card>
          </VStack>
        </Box>

        {/* Sidebar - Resumen de Costos */}
        <Box>
          <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl" position="sticky" top={6}>
            <CardHeader pb={2}>
              <HStack>
                <Icon as={FiDollarSign} color="green.500" />
                <Heading size="md">Resumen de Costos</Heading>
              </HStack>
            </CardHeader>
            <CardBody>
              <VStack spacing={4} align="stretch">
                {/* Barra de Insumos */}
                <Box>
                  <Flex justify="space-between" fontSize="sm" mb={1}>
                    <Text color="gray.600">Insumos</Text>
                    <Text fontWeight="medium">{formatCurrency(costos.costo_insumos)}</Text>
                  </Flex>
                  <Progress 
                    value={((costos.costo_insumos || 0) / (costos.costo_total || 1)) * 100} 
                    colorScheme="blue" 
                    borderRadius="full" 
                    size="sm" 
                  />
                </Box>

                {/* Barra de Mano de Obra */}
                <Box>
                  <Flex justify="space-between" fontSize="sm" mb={1}>
                    <Text color="gray.600">Mano de Obra</Text>
                    <Text fontWeight="medium">{formatCurrency(receta.costo_mano_obra)}</Text>
                  </Flex>
                  <Progress 
                    value={((receta.costo_mano_obra || 0) / (costos.costo_total || 1)) * 100} 
                    colorScheme="green" 
                    borderRadius="full" 
                    size="sm" 
                  />
                </Box>

                {/* Barra de Costos Indirectos */}
                <Box>
                  <Flex justify="space-between" fontSize="sm" mb={1}>
                    <Text color="gray.600">Costos Indirectos</Text>
                    <Text fontWeight="medium">{formatCurrency(receta.costo_indirecto)}</Text>
                  </Flex>
                  <Progress 
                    value={((receta.costo_indirecto || 0) / (costos.costo_total || 1)) * 100} 
                    colorScheme="yellow" 
                    borderRadius="full" 
                    size="sm" 
                  />
                </Box>

                <Divider />

                {/* Costo Total */}
                <Flex justify="space-between" align="center">
                  <Text fontWeight="semibold">Costo Total:</Text>
                  <Text fontSize="lg" fontWeight="bold" color="blue.600">
                    {formatCurrency(costos.costo_total)}
                  </Text>
                </Flex>

                {/* Costo Unitario */}
                <Box bg="blue.50" p={4} borderRadius="xl" borderWidth="2px" borderColor="blue.200">
                  <Text fontSize="xs" color="gray.600" mb={1}>Costo Unitario Teórico</Text>
                  <Text fontSize="2xl" fontWeight="bold" color="blue.600">
                    {formatCurrency(costos.costo_unitario)}
                  </Text>
                  <Text fontSize="xs" color="gray.500" mt={1}>
                    Por {receta.cantidad_producida} unidad(es)
                  </Text>
                </Box>

                {/* Botón crear orden */}
                <Button
                  as={RouterLink}
                  to={`/app/produccion/ordenes/nueva?receta_id=${receta.id}`}
                  colorScheme="green"
                  size="lg"
                  leftIcon={<AddIcon />}
                  w="full"
                >
                  Crear Orden de Producción
                </Button>
              </VStack>
            </CardBody>
          </Card>
        </Box>
      </SimpleGrid>

      {/* Modal de eliminación */}
      <Modal isOpen={isDeleteOpen} onClose={onDeleteClose} isCentered>
        <ModalOverlay />
        <ModalContent borderRadius="xl">
          <ModalHeader>Eliminar Receta</ModalHeader>
          <ModalCloseButton />
          <ModalBody textAlign="center" py={6}>
            <Icon as={DeleteIcon} boxSize={12} color="red.400" mb={4} />
            <Text mb={2}>¿Está seguro de eliminar esta receta?</Text>
            <Text fontWeight="bold" fontSize="lg">"{receta.nombre}"</Text>
            <Text fontSize="sm" color="gray.500" mt={2}>Esta acción no se puede deshacer</Text>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onDeleteClose}>
              Cancelar
            </Button>
            <Button
              colorScheme="red"
              onClick={() => eliminarMutation.mutate()}
              isLoading={eliminarMutation.isLoading}
            >
              Eliminar
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default RecetaDetalle;
