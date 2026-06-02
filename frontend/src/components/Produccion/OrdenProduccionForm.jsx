import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { produccionService } from '../../services/produccion.service';
import { almacenesService } from '../../services/almacenes.service';
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
  FormControl,
  FormLabel,
  Input,
  Select,
  Textarea,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Icon,
  Spinner,
  Badge,
  Divider,
  useColorModeValue,
  useToast,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Progress
} from '@chakra-ui/react';
import { ChevronLeftIcon, CheckIcon, WarningIcon } from '@chakra-ui/icons';
import { FiPackage, FiBox, FiClock, FiDollarSign, FiCalendar, FiClipboard } from 'react-icons/fi';

const OrdenProduccionForm = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [searchParams] = useSearchParams();
  const recetaIdParam = searchParams.get('receta_id');

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  const [validacionStock, setValidacionStock] = useState(null);
  const [loadingValidacion, setLoadingValidacion] = useState(false);

  const [formData, setFormData] = useState({
    receta_id: recetaIdParam || '',
    cantidad: 1,
    fecha_programada: new Date().toISOString().split('T')[0],
    almacen_insumos_id: '',
    almacen_destino_id: '',
    observaciones: ''
  });

  // Query para recetas
  const { data: recetas = [], isLoading: loadingRecetas } = useQuery({
    queryKey: ['recetas-activas'],
    queryFn: async () => {
      const response = await produccionService.getRecetas({ is_active: true });
      const data = response.data;
      return data?.results || data || [];
    }
  });

  // Query para almacenes
  const { data: almacenes = [], isLoading: loadingAlmacenes } = useQuery({
    queryKey: ['almacenes'],
    queryFn: async () => {
      const response = await almacenesService.getAlmacenes();
      const data = response.data;
      return data?.results || data || [];
    }
  });

  // Query para receta seleccionada
  const { data: recetaSeleccionada } = useQuery({
    queryKey: ['receta', formData.receta_id],
    queryFn: () => produccionService.getReceta(formData.receta_id),
    enabled: !!formData.receta_id,
    select: (response) => response?.data || response
  });

  // Mutation para crear orden
  const createMutation = useMutation({
    mutationFn: (data) => produccionService.createOrden(data),
    onSuccess: (response) => {
      queryClient.invalidateQueries(['ordenes-produccion']);
      toast({
        title: 'Orden creada exitosamente',
        status: 'success',
        duration: 3000
      });
      navigate(`/app/produccion/ordenes/${response?.data?.id || response?.id}`);
    },
    onError: (error) => {
      toast({
        title: 'Error al crear orden',
        description: error.response?.data?.error || error.message,
        status: 'error',
        duration: 5000
      });
    }
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));

    if (['receta_id', 'cantidad', 'almacen_insumos_id'].includes(name)) {
      setValidacionStock(null);
    }
  };

  const validarStock = async () => {
    if (!formData.receta_id || !formData.cantidad || !formData.almacen_insumos_id) {
      toast({
        title: 'Campos requeridos',
        description: 'Complete receta, cantidad y almacén de insumos para validar',
        status: 'warning',
        duration: 3000
      });
      return;
    }

    try {
      setLoadingValidacion(true);
      const response = await produccionService.validarStock({
        receta_id: parseInt(formData.receta_id),
        cantidad: parseFloat(formData.cantidad),
        almacen_insumos_id: parseInt(formData.almacen_insumos_id)
      });
      setValidacionStock(response.data || response);
    } catch (err) {
      toast({
        title: 'Error al validar stock',
        status: 'error',
        duration: 3000
      });
    } finally {
      setLoadingValidacion(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!formData.receta_id || !formData.cantidad || !formData.almacen_insumos_id || !formData.almacen_destino_id) {
      toast({
        title: 'Campos requeridos',
        description: 'Complete todos los campos obligatorios',
        status: 'warning',
        duration: 3000
      });
      return;
    }

    if (parseFloat(formData.cantidad) <= 0) {
      toast({
        title: 'Cantidad inválida',
        description: 'La cantidad debe ser mayor a 0',
        status: 'warning',
        duration: 3000
      });
      return;
    }

      const dataToSend = {
        receta_id: parseInt(formData.receta_id),
        cantidad: parseFloat(formData.cantidad),
        fecha_programada: formData.fecha_programada,
        almacen_insumos_id: parseInt(formData.almacen_insumos_id),
        almacen_destino_id: parseInt(formData.almacen_destino_id),
        observaciones: formData.observaciones || ''
      };

    createMutation.mutate(dataToSend);
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('es-PE', {
      style: 'currency',
      currency: 'PEN'
    }).format(amount || 0);
  };

  const isLoading = loadingRecetas || loadingAlmacenes;

  if (isLoading) {
    return (
      <Box p={6}>
        <Flex justify="center" align="center" h="300px" direction="column">
          <Spinner size="xl" color="blue.500" thickness="4px" mb={4} />
          <Text color="gray.600">Cargando datos...</Text>
        </Flex>
      </Box>
    );
  }

  return (
    <Box p={6}>
      {/* Header */}
      <Flex align="center" mb={6}>
        <Button
          leftIcon={<ChevronLeftIcon />}
          variant="ghost"
          onClick={() => navigate('/app/produccion/ordenes')}
          mr={4}
        >
          Volver
        </Button>
        <Box>
          <Heading size="lg" bgGradient="linear(to-r, blue.600, purple.600)" bgClip="text">
            Nueva Orden de Producción
          </Heading>
          <Text color="gray.600" mt={1}>
            Complete los datos para crear una orden de producción
          </Text>
        </Box>
      </Flex>

      <form onSubmit={handleSubmit}>
        <SimpleGrid columns={{ base: 1, lg: 3 }} spacing={6}>
          {/* Formulario Principal */}
          <Box gridColumn={{ lg: 'span 2' }}>
            <VStack spacing={6} align="stretch">
            {/* Información Básica */}
              <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl">
                <CardHeader pb={2}>
                  <HStack>
                    <Icon as={FiClipboard} color="blue.500" />
                    <Heading size="md">Información de la Orden</Heading>
                  </HStack>
                </CardHeader>
                <CardBody>
                  <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                    <FormControl isRequired gridColumn={{ md: 'span 2' }}>
                      <FormLabel fontWeight="semibold">Receta a Producir</FormLabel>
                      <Select
                    name="receta_id"
                    value={formData.receta_id}
                    onChange={handleChange}
                        placeholder="Seleccione una receta"
                        size="lg"
                  >
                    {recetas.map(receta => (
                      <option key={receta.id} value={receta.id}>
                        {receta.nombre} - {receta.producto_terminado_nombre} (v{receta.version})
                      </option>
                    ))}
                      </Select>
                    </FormControl>

                    <FormControl isRequired>
                      <FormLabel fontWeight="semibold">Cantidad a Producir</FormLabel>
                      <Input
                    type="number"
                    name="cantidad"
                    value={formData.cantidad}
                    onChange={handleChange}
                    min="0.01"
                    step="0.01"
                        size="lg"
                      />
                    </FormControl>

                    <FormControl isRequired>
                      <FormLabel fontWeight="semibold">Fecha Programada</FormLabel>
                      <Input
                    type="date"
                    name="fecha_programada"
                    value={formData.fecha_programada}
                    onChange={handleChange}
                        size="lg"
                      />
                    </FormControl>

                    <FormControl isRequired>
                      <FormLabel fontWeight="semibold">Almacén de Insumos</FormLabel>
                      <Select
                    name="almacen_insumos_id"
                    value={formData.almacen_insumos_id}
                    onChange={handleChange}
                        placeholder="Seleccione almacén"
                  >
                    {almacenes.map(almacen => (
                      <option key={almacen.id} value={almacen.id}>
                        {almacen.nombre}
                      </option>
                    ))}
                      </Select>
                    </FormControl>

                    <FormControl isRequired>
                      <FormLabel fontWeight="semibold">Almacén de Destino</FormLabel>
                      <Select
                    name="almacen_destino_id"
                    value={formData.almacen_destino_id}
                    onChange={handleChange}
                        placeholder="Seleccione almacén"
                  >
                    {almacenes.map(almacen => (
                      <option key={almacen.id} value={almacen.id}>
                        {almacen.nombre}
                      </option>
                    ))}
                      </Select>
                    </FormControl>

                    <FormControl gridColumn={{ md: 'span 2' }}>
                      <FormLabel fontWeight="semibold">Observaciones</FormLabel>
                      <Textarea
                    name="observaciones"
                    value={formData.observaciones}
                    onChange={handleChange}
                    placeholder="Notas adicionales..."
                        rows={3}
                      />
                    </FormControl>
                  </SimpleGrid>
                </CardBody>
              </Card>

            {/* Validación de Stock */}
            {formData.receta_id && formData.cantidad && formData.almacen_insumos_id && (
                <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl">
                  <CardHeader pb={2}>
                    <Flex justify="space-between" align="center">
                      <HStack>
                        <Icon as={FiBox} color="purple.500" />
                        <Heading size="md">Validación de Stock</Heading>
                      </HStack>
                      <Button
                        colorScheme="blue"
                        size="sm"
                    onClick={validarStock}
                        isLoading={loadingValidacion}
                      >
                        Validar Stock
                      </Button>
                    </Flex>
                  </CardHeader>
                  <CardBody>
                    {validacionStock ? (
                      <VStack spacing={4} align="stretch">
                        <Alert
                          status={validacionStock.valido ? 'success' : 'warning'}
                          borderRadius="md"
                        >
                          <AlertIcon />
                          {validacionStock.valido 
                            ? 'Stock suficiente para todos los insumos'
                            : 'Stock insuficiente para algunos insumos'
                          }
                        </Alert>

                        {validacionStock.insumos && (
                          <Box overflowX="auto">
                            <Table size="sm" variant="simple">
                              <Thead bg="gray.50">
                                <Tr>
                                  <Th>Insumo</Th>
                                  <Th isNumeric>Necesario</Th>
                                  <Th isNumeric>Disponible</Th>
                                  <Th textAlign="center">Estado</Th>
                                </Tr>
                              </Thead>
                              <Tbody>
                                {validacionStock.insumos.map((insumo, idx) => (
                                  <Tr key={idx}>
                                    <Td>
                                      <Text fontWeight="medium">{insumo.insumo_nombre}</Text>
                                      <Text fontSize="xs" color="gray.500">{insumo.insumo_sku}</Text>
                                    </Td>
                                    <Td isNumeric>{insumo.cantidad_necesaria}</Td>
                                    <Td isNumeric>{insumo.stock_disponible}</Td>
                                    <Td textAlign="center">
                                      {insumo.suficiente ? (
                                        <Badge colorScheme="green">
                                          <CheckIcon mr={1} /> OK
                                        </Badge>
                                      ) : (
                                        <Badge colorScheme="red">
                                          <WarningIcon mr={1} /> Falta: {insumo.faltante}
                                        </Badge>
                                      )}
                                    </Td>
                                  </Tr>
                                ))}
                              </Tbody>
                            </Table>
                          </Box>
                        )}
                      </VStack>
                    ) : (
                      <Box textAlign="center" py={8}>
                        <Icon as={FiBox} boxSize={8} color="gray.400" mb={2} />
                        <Text color="gray.500">
                          Haz clic en "Validar Stock" para verificar la disponibilidad de insumos
                        </Text>
                      </Box>
                    )}
                  </CardBody>
                </Card>
              )}
            </VStack>
          </Box>

          {/* Sidebar - Resumen */}
          <Box>
            <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl" position="sticky" top={6}>
              <CardHeader pb={2}>
                <HStack>
                  <Icon as={FiDollarSign} color="green.500" />
                  <Heading size="md">Resumen</Heading>
                </HStack>
              </CardHeader>
              <CardBody>
              {recetaSeleccionada ? (
                  <VStack spacing={4} align="stretch">
                    <Box>
                      <Text fontSize="sm" color="gray.500" mb={1}>Producto</Text>
                      <Text fontWeight="medium">{recetaSeleccionada.producto_terminado_nombre}</Text>
                    </Box>

                    <Box>
                      <Text fontSize="sm" color="gray.500" mb={1}>Cantidad a Producir</Text>
                      <Text fontSize="2xl" fontWeight="bold" color="blue.600">{formData.cantidad}</Text>
                    </Box>

                    <Box>
                      <Text fontSize="sm" color="gray.500" mb={1}>Tiempo Estimado</Text>
                      <Text fontWeight="medium">
                      {Math.round((recetaSeleccionada.tiempo_estimado / recetaSeleccionada.cantidad_producida) * parseFloat(formData.cantidad || 0))} min
                      </Text>
                    </Box>

                  {recetaSeleccionada.costos && (
                      <Box>
                        <Text fontSize="sm" color="gray.500" mb={1}>Costo Estimado Total</Text>
                        <Text fontSize="xl" fontWeight="bold" color="green.600">
                          {formatCurrency(recetaSeleccionada.costos.costo_unitario * parseFloat(formData.cantidad || 0))}
                        </Text>
                      </Box>
                    )}

                    <Divider />

                    <Box>
                      <Text fontSize="sm" color="gray.500" mb={1}>Insumos Requeridos</Text>
                      <Text fontWeight="medium">{recetaSeleccionada.detalles?.length || 0} insumos</Text>
                    </Box>
                  </VStack>
                ) : (
                  <Box textAlign="center" py={8}>
                    <Icon as={FiPackage} boxSize={8} color="gray.400" mb={2} />
                    <Text color="gray.500">
                  Seleccione una receta para ver el resumen
                    </Text>
                  </Box>
              )}

                <VStack spacing={3} mt={6}>
                  <Button
                  type="submit"
                    colorScheme="blue"
                    size="lg"
                    w="full"
                    isLoading={createMutation.isLoading}
                    isDisabled={validacionStock && !validacionStock.valido}
                  >
                    Crear Orden
                  </Button>
                  <Button
                    variant="outline"
                    w="full"
                  onClick={() => navigate('/app/produccion/ordenes')}
                >
                  Cancelar
                  </Button>
                </VStack>
              </CardBody>
            </Card>
          </Box>
        </SimpleGrid>
      </form>
    </Box>
  );
};

export default OrdenProduccionForm;
