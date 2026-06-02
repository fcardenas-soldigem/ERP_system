import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { produccionService } from '../../services/produccion.service';
import { inventarioService } from '../../services/inventario.service';
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
  Switch,
  Badge,
  Progress,
  Alert,
  AlertIcon,
  Icon,
  IconButton,
  Spinner,
  Divider,
  useColorModeValue,
  useToast
} from '@chakra-ui/react';
import { 
  ChevronLeftIcon,
  AddIcon,
  DeleteIcon
} from '@chakra-ui/icons';
import { FiPackage, FiBox, FiClock, FiDollarSign, FiClipboard } from 'react-icons/fi';

const RecetaForm = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const queryClient = useQueryClient();
  const toast = useToast();
  const isEditing = Boolean(id);

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  const [formData, setFormData] = useState({
    producto_terminado: '',
    nombre: '',
    cantidad_producida: 1,
    tiempo_estimado: 0,
    costo_mano_obra: 0,
    costo_indirecto: 0,
    is_active: true,
    version: 1,
    notas: '',
    detalles: []
  });

  // Query para productos terminados (para seleccionar qué producir)
  // inventarioService ya devuelve los datos procesados directamente
  const { data: productos = [], isLoading: loadingProductos } = useQuery({
    queryKey: ['productos-terminados'],
    queryFn: () => inventarioService.getProductosTerminados()
  });

  // Query para insumos (materias primas)
  const { data: insumos = [], isLoading: loadingInsumos } = useQuery({
    queryKey: ['materias-primas'],
    queryFn: () => inventarioService.getMateriasPrimas()
  });

  // Query para receta (si estamos editando)
  const { data: recetaOriginal, isLoading: loadingReceta } = useQuery({
    queryKey: ['receta', id],
    queryFn: () => produccionService.getReceta(id),
    enabled: isEditing,
    select: (response) => response?.data || response
  });

  // Cargar datos de receta cuando estamos editando
  useEffect(() => {
    if (recetaOriginal) {
      setFormData({
        producto_terminado: recetaOriginal.producto_terminado,
        nombre: recetaOriginal.nombre,
        cantidad_producida: recetaOriginal.cantidad_producida,
        tiempo_estimado: recetaOriginal.tiempo_estimado,
        costo_mano_obra: recetaOriginal.costo_mano_obra,
        costo_indirecto: recetaOriginal.costo_indirecto,
        is_active: recetaOriginal.is_active,
        version: recetaOriginal.version,
        notas: recetaOriginal.notas || '',
        detalles: recetaOriginal.detalles || []
      });
    }
  }, [recetaOriginal]);

  // Mutation para guardar
  const saveMutation = useMutation({
    mutationFn: async (data) => {
      if (isEditing) {
        return await produccionService.updateReceta(id, data);
      }
      return await produccionService.createReceta(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['recetas']);
      toast({
        title: isEditing ? 'Receta actualizada' : 'Receta creada',
        status: 'success',
        duration: 3000
      });
      navigate('/app/produccion/recetas');
    },
    onError: (error) => {
      toast({
        title: 'Error al guardar',
        description: error.response?.data?.error || error.message,
        status: 'error',
        duration: 5000
      });
    }
  });

  // Calcular costos
  const costos = useMemo(() => {
    const costoInsumos = formData.detalles.reduce((sum, detalle) => {
      return sum + (parseFloat(detalle.cantidad || 0) * parseFloat(detalle.costo_unitario || 0));
    }, 0);
    
    const costoTotal = costoInsumos + 
                      parseFloat(formData.costo_mano_obra || 0) + 
                      parseFloat(formData.costo_indirecto || 0);
    
    const costoUnitario = formData.cantidad_producida > 0 
                         ? costoTotal / parseFloat(formData.cantidad_producida) 
                         : 0;

    return { costoInsumos, costoTotal, costoUnitario };
  }, [formData.detalles, formData.costo_mano_obra, formData.costo_indirecto, formData.cantidad_producida]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const agregarInsumo = () => {
    setFormData(prev => ({
      ...prev,
      detalles: [
        ...prev.detalles,
        {
          insumo: '',
          cantidad: 0,
          unidad_medida: 'unidad',
          costo_unitario: 0,
          notas: ''
        }
      ]
    }));
  };

  const eliminarInsumo = (index) => {
    setFormData(prev => ({
      ...prev,
      detalles: prev.detalles.filter((_, i) => i !== index)
    }));
  };

  const handleInsumoChange = (index, field, value) => {
    setFormData(prev => {
      const nuevosDetalles = [...prev.detalles];
      nuevosDetalles[index] = {
        ...nuevosDetalles[index],
        [field]: value
      };

      // Si cambia el insumo, actualizar unidad_medida y costo_unitario
      if (field === 'insumo') {
        const insumoSeleccionado = insumos.find(p => (p.producto || p.id) === parseInt(value));
        if (insumoSeleccionado) {
          nuevosDetalles[index].unidad_medida = insumoSeleccionado.unidad_medida;
          nuevosDetalles[index].costo_unitario = insumoSeleccionado.costo_unitario_promedio || insumoSeleccionado.precio_compra || 0;
        }
      }

      return { ...prev, detalles: nuevosDetalles };
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Validaciones
    if (!formData.producto_terminado) {
      toast({ title: 'Debe seleccionar un producto terminado', status: 'warning', duration: 3000 });
      return;
    }

    if (!formData.nombre.trim()) {
      toast({ title: 'Debe ingresar un nombre para la receta', status: 'warning', duration: 3000 });
      return;
    }

    if (formData.cantidad_producida <= 0) {
      toast({ title: 'La cantidad producida debe ser mayor a 0', status: 'warning', duration: 3000 });
      return;
    }

    if (formData.detalles.length === 0) {
      toast({ title: 'Debe agregar al menos un insumo', status: 'warning', duration: 3000 });
      return;
    }

    const insumosIncompletos = formData.detalles.some(
      detalle => !detalle.insumo || detalle.cantidad <= 0
    );

    if (insumosIncompletos) {
      toast({ title: 'Todos los insumos deben tener producto y cantidad mayor a 0', status: 'warning', duration: 3000 });
      return;
    }

      const dataToSend = {
        ...formData,
        detalles: formData.detalles.map(detalle => ({
          insumo: parseInt(detalle.insumo),
          cantidad: parseFloat(detalle.cantidad),
          unidad_medida: detalle.unidad_medida,
          costo_unitario: parseFloat(detalle.costo_unitario),
          notas: detalle.notas || ''
        }))
      };

    saveMutation.mutate(dataToSend);
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('es-PE', {
      style: 'currency',
      currency: 'PEN'
    }).format(amount || 0);
  };

  const isLoading = loadingProductos || loadingInsumos || (isEditing && loadingReceta);

  if (isLoading) {
    return (
      <Box p={6}>
        <Flex justify="center" align="center" h="300px" direction="column">
          <Spinner size="xl" color="blue.500" thickness="4px" mb={4} />
          <Text color="gray.600">Cargando {isEditing ? 'receta' : 'datos'}...</Text>
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
          onClick={() => navigate('/app/produccion/recetas')}
          mr={4}
        >
          Volver
        </Button>
        <Box>
          <HStack spacing={3}>
            <Flex w="48px" h="48px" bg="blue.500" borderRadius="xl" align="center" justify="center">
              <Icon as={FiPackage} boxSize={6} color="white" />
            </Flex>
            <Box>
              <Heading size="lg">
                  {isEditing ? 'Editar Receta' : 'Nueva Receta de Producción'}
              </Heading>
              <Text color="gray.600" fontSize="sm">
                  {isEditing ? 'Modifique los datos de la receta' : 'Complete los datos para crear una nueva receta (BOM)'}
              </Text>
            </Box>
          </HStack>
        </Box>
      </Flex>

      <form onSubmit={handleSubmit}>
        <SimpleGrid columns={{ base: 1, lg: 3 }} spacing={6}>
          {/* Columna Principal */}
          <Box gridColumn={{ lg: 'span 2' }}>
            <VStack spacing={6} align="stretch">
            {/* Información Básica */}
              <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl">
                <CardHeader pb={2}>
                  <HStack>
                    <Flex w="36px" h="36px" bg="blue.500" borderRadius="lg" align="center" justify="center">
                      <Icon as={FiClipboard} color="white" />
                    </Flex>
                    <Heading size="md">Información Básica</Heading>
                  </HStack>
                </CardHeader>
                <CardBody>
                  <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                    <FormControl isRequired gridColumn={{ md: 'span 2' }}>
                      <FormLabel fontWeight="semibold">Producto Terminado</FormLabel>
                      <Select
                    name="producto_terminado"
                    value={formData.producto_terminado}
                    onChange={handleChange}
                        placeholder="Seleccione un producto"
                        size="lg"
                  >
                    {productos.map(producto => (
                          <option key={producto.id} value={producto.producto || producto.id}>
                            {producto.producto_nombre || producto.nombre} ({producto.producto_sku || producto.sku})
                      </option>
                    ))}
                      </Select>
                    </FormControl>

                    <FormControl isRequired gridColumn={{ md: 'span 2' }}>
                      <FormLabel fontWeight="semibold">Nombre de la Receta</FormLabel>
                      <Input
                    name="nombre"
                    value={formData.nombre}
                    onChange={handleChange}
                    placeholder="Ej: Receta estándar de..."
                        size="lg"
                      />
                    </FormControl>

                    <FormControl isRequired>
                      <FormLabel fontWeight="semibold">Cantidad Producida</FormLabel>
                      <Input
                    type="number"
                    name="cantidad_producida"
                    value={formData.cantidad_producida}
                    onChange={handleChange}
                    min="0.01"
                    step="0.01"
                  />
                    </FormControl>

                {isEditing && (
                      <FormControl>
                        <FormLabel fontWeight="semibold">Versión</FormLabel>
                        <Input
                      type="number"
                      name="version"
                      value={formData.version}
                      onChange={handleChange}
                      min="1"
                        />
                      </FormControl>
                    )}

                    <FormControl display="flex" alignItems="center" gridColumn={{ md: 'span 2' }}>
                      <Switch
                        id="is_active"
                      name="is_active"
                        isChecked={formData.is_active}
                        onChange={(e) => setFormData(prev => ({ ...prev, is_active: e.target.checked }))}
                        colorScheme="green"
                        size="lg"
                        mr={3}
                      />
                      <FormLabel htmlFor="is_active" mb={0}>
                        Receta activa
                      </FormLabel>
                    </FormControl>

                    <FormControl gridColumn={{ md: 'span 2' }}>
                      <FormLabel fontWeight="semibold">Notas / Instrucciones</FormLabel>
                      <Textarea
                    name="notas"
                    value={formData.notas}
                    onChange={handleChange}
                    placeholder="Instrucciones adicionales para la producción..."
                        rows={3}
                      />
                    </FormControl>
                  </SimpleGrid>
                </CardBody>
              </Card>

            {/* Insumos */}
              <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl">
                <CardHeader pb={2}>
                  <Flex justify="space-between" align="center">
                    <HStack>
                      <Flex w="36px" h="36px" bg="green.500" borderRadius="lg" align="center" justify="center">
                        <Icon as={FiBox} color="white" />
                      </Flex>
                      <Box>
                        <Heading size="md">Insumos de la Receta</Heading>
                        <Text fontSize="xs" color="gray.500">Selecciona los productos del inventario necesarios</Text>
                      </Box>
                    </HStack>
                    <Button
                      leftIcon={<AddIcon />}
                      colorScheme="blue"
                      size="sm"
                  onClick={agregarInsumo}
                >
                  Agregar Insumo
                    </Button>
                  </Flex>
                </CardHeader>
                <CardBody>
              {formData.detalles.length === 0 ? (
                    <Box textAlign="center" py={12} bg="gray.50" borderRadius="xl" borderWidth="2px" borderStyle="dashed" borderColor="gray.200">
                      <Icon as={FiBox} boxSize={10} color="gray.400" mb={3} />
                      <Text color="gray.600" fontWeight="medium" mb={1}>No hay insumos agregados</Text>
                      <Text fontSize="sm" color="gray.500">
                        Haz clic en "Agregar Insumo" para comenzar a construir tu receta
                      </Text>
                    </Box>
                  ) : (
                    <VStack spacing={4} align="stretch">
                    {formData.detalles.map((detalle, index) => (
                        <Box
                        key={index}
                          p={4}
                          bg="white"
                          borderWidth="2px"
                          borderColor="gray.200"
                          borderRadius="xl"
                          _hover={{ borderColor: 'blue.300' }}
                          transition="all 0.2s"
                        >
                          <Flex align="start" gap={3}>
                          {/* Número de orden */}
                            <Flex
                              w="32px"
                              h="32px"
                              bg="blue.500"
                              borderRadius="lg"
                              align="center"
                              justify="center"
                              flexShrink={0}
                            >
                              <Text color="white" fontWeight="bold" fontSize="sm">{index + 1}</Text>
                            </Flex>

                            <SimpleGrid columns={12} spacing={3} flex={1}>
                              <FormControl gridColumn={{ base: 'span 12', md: 'span 5' }} isRequired>
                                <FormLabel fontSize="xs" fontWeight="semibold">Producto/Insumo</FormLabel>
                                <Select
                                  value={detalle.insumo}
                                  onChange={(e) => handleInsumoChange(index, 'insumo', e.target.value)}
                                  placeholder="Seleccionar producto..."
                                  size="sm"
                                >
                              {insumos.map(insumo => (
                                    <option key={insumo.id} value={insumo.producto || insumo.id}>
                                      {insumo.producto_nombre || insumo.nombre} ({insumo.producto_sku || insumo.sku})
                                </option>
                              ))}
                                </Select>
                              </FormControl>

                              <FormControl gridColumn={{ base: 'span 6', md: 'span 2' }} isRequired>
                                <FormLabel fontSize="xs" fontWeight="semibold">Cantidad</FormLabel>
                                <Input
                              type="number"
                              value={detalle.cantidad}
                              onChange={(e) => handleInsumoChange(index, 'cantidad', e.target.value)}
                              min="0.01"
                              step="0.01"
                                  size="sm"
                                />
                              </FormControl>

                              <FormControl gridColumn={{ base: 'span 6', md: 'span 2' }}>
                                <FormLabel fontSize="xs" fontWeight="semibold">Costo Unit.</FormLabel>
                                <Input
                              type="number"
                              value={detalle.costo_unitario}
                              onChange={(e) => handleInsumoChange(index, 'costo_unitario', e.target.value)}
                              min="0"
                              step="0.01"
                                  size="sm"
                                />
                              </FormControl>

                              <FormControl gridColumn={{ base: 'span 10', md: 'span 2' }}>
                                <FormLabel fontSize="xs" fontWeight="semibold">Subtotal</FormLabel>
                                <Box
                                  px={3}
                                  py={2}
                                  bg="blue.50"
                                  borderWidth="1px"
                                  borderColor="blue.200"
                                  borderRadius="md"
                                  textAlign="right"
                                >
                                  <Text fontWeight="bold" color="blue.600" fontSize="sm">
                                    {formatCurrency(parseFloat(detalle.cantidad || 0) * parseFloat(detalle.costo_unitario || 0))}
                                  </Text>
                                </Box>
                              </FormControl>

                              <Flex gridColumn={{ base: 'span 2', md: 'span 1' }} align="end" justify="center">
                                <IconButton
                                  icon={<DeleteIcon />}
                                  variant="ghost"
                                  colorScheme="red"
                                  size="sm"
                              onClick={() => eliminarInsumo(index)}
                                  aria-label="Eliminar insumo"
                                />
                              </Flex>

                              <FormControl gridColumn="span 12" mt={2}>
                                <Input
                              value={detalle.notas}
                              onChange={(e) => handleInsumoChange(index, 'notas', e.target.value)}
                              placeholder="Notas o instrucciones especiales..."
                                  size="sm"
                                  bg="gray.50"
                                />
                              </FormControl>
                            </SimpleGrid>
                          </Flex>
                        </Box>
                      ))}
                    </VStack>
                  )}
                </CardBody>
              </Card>

            {/* Tiempo y Costos */}
              <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl">
                <CardHeader pb={2}>
                  <HStack>
                    <Flex w="36px" h="36px" bg="purple.500" borderRadius="lg" align="center" justify="center">
                      <Icon as={FiClock} color="white" />
                    </Flex>
                    <Heading size="md">Tiempo y Costos de Producción</Heading>
                  </HStack>
                </CardHeader>
                <CardBody>
                  <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
                    <FormControl>
                      <FormLabel fontWeight="semibold">Tiempo Estimado (minutos)</FormLabel>
                      <Input
                    type="number"
                    name="tiempo_estimado"
                    value={formData.tiempo_estimado}
                    onChange={handleChange}
                    min="0"
                    placeholder="0"
                      />
                      <Text fontSize="xs" color="gray.500" mt={1}>Duración estimada del proceso</Text>
                    </FormControl>

                    <FormControl>
                      <FormLabel fontWeight="semibold">Costo Mano de Obra (S/)</FormLabel>
                      <Input
                    type="number"
                    name="costo_mano_obra"
                    value={formData.costo_mano_obra}
                    onChange={handleChange}
                    min="0"
                    step="0.01"
                    placeholder="0.00"
                      />
                      <Text fontSize="xs" color="gray.500" mt={1}>Costo de personal involucrado</Text>
                    </FormControl>

                    <FormControl>
                      <FormLabel fontWeight="semibold">Costos Indirectos / CIF (S/)</FormLabel>
                      <Input
                    type="number"
                    name="costo_indirecto"
                    value={formData.costo_indirecto}
                    onChange={handleChange}
                    min="0"
                    step="0.01"
                    placeholder="0.00"
                      />
                      <Text fontSize="xs" color="gray.500" mt={1}>Electricidad, agua, depreciación, etc.</Text>
                    </FormControl>
                  </SimpleGrid>
                </CardBody>
              </Card>
            </VStack>
          </Box>

          {/* Sidebar - Resumen */}
          <Box>
            <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl" position="sticky" top={6}>
              <CardHeader pb={2}>
                <HStack>
                  <Flex w="36px" h="36px" bg="yellow.500" borderRadius="lg" align="center" justify="center">
                    <Icon as={FiDollarSign} color="white" />
                  </Flex>
                  <Heading size="md">Resumen de Costos</Heading>
                </HStack>
              </CardHeader>
              <CardBody>
                <VStack spacing={4} align="stretch">
                {/* Costo Insumos */}
                  <Box p={4} bg="gray.50" borderRadius="lg" borderWidth="1px" borderColor="gray.200">
                    <Flex justify="space-between" align="center">
                      <HStack>
                        <Icon as={FiPackage} color="gray.600" />
                        <Text fontSize="sm" color="gray.600" fontWeight="medium">Costo Insumos</Text>
                      </HStack>
                      <Text fontWeight="bold">{formatCurrency(costos.costoInsumos)}</Text>
                    </Flex>
                  </Box>

                {/* Mano de Obra */}
                  <Box p={4} bg="gray.50" borderRadius="lg" borderWidth="1px" borderColor="gray.200">
                    <Flex justify="space-between" align="center">
                      <HStack>
                        <Icon as={FiClock} color="gray.600" />
                        <Text fontSize="sm" color="gray.600" fontWeight="medium">Mano de Obra</Text>
                      </HStack>
                      <Text fontWeight="bold">{formatCurrency(formData.costo_mano_obra)}</Text>
                    </Flex>
                  </Box>

                {/* Costos Indirectos */}
                  <Box p={4} bg="gray.50" borderRadius="lg" borderWidth="1px" borderColor="gray.200">
                    <Flex justify="space-between" align="center">
                      <HStack>
                        <Icon as={FiDollarSign} color="gray.600" />
                        <Text fontSize="sm" color="gray.600" fontWeight="medium">Costos Indirectos</Text>
                      </HStack>
                      <Text fontWeight="bold">{formatCurrency(formData.costo_indirecto)}</Text>
                    </Flex>
                  </Box>

                  <Divider />

                {/* Costo Total */}
                  <Box p={5} bg="blue.500" borderRadius="xl">
                    <Flex justify="space-between" align="center">
                      <HStack>
                        <Icon as={FiDollarSign} color="white" />
                        <Text color="white" fontWeight="bold">Costo Total</Text>
                      </HStack>
                      <Text fontSize="2xl" fontWeight="black" color="white">
                        {formatCurrency(costos.costoTotal)}
                      </Text>
                    </Flex>
                  </Box>

                {/* Costo por Unidad */}
                  <Box p={5} bgGradient="linear(to-br, yellow.400, yellow.500)" borderRadius="xl">
                    <HStack mb={2}>
                      <Flex w="28px" h="28px" bg="whiteAlpha.300" borderRadius="lg" align="center" justify="center">
                        <Icon as={FiDollarSign} color="white" boxSize={4} />
                      </Flex>
                      <Text fontSize="sm" color="white" fontWeight="bold">Costo por Unidad</Text>
                    </HStack>
                    <Text fontSize="2xl" fontWeight="black" color="white" mb={1}>
                      {formatCurrency(costos.costoUnitario)}
                    </Text>
                    <Text fontSize="xs" color="whiteAlpha.900">
                    Por {formData.cantidad_producida} unidad(es)
                    </Text>
                  </Box>

                {/* Botones */}
                  <VStack spacing={3} pt={4}>
                    <Button
                    type="submit"
                      colorScheme="green"
                      size="lg"
                      w="full"
                      isLoading={saveMutation.isLoading}
                    >
                        {isEditing ? 'Actualizar Receta' : 'Crear Receta'}
                    </Button>
                    <Button
                      variant="outline"
                      w="full"
                    onClick={() => navigate('/app/produccion/recetas')}
                  >
                    Cancelar
                    </Button>
                  </VStack>
                </VStack>
              </CardBody>
            </Card>
          </Box>
        </SimpleGrid>
      </form>
    </Box>
  );
};

export default RecetaForm;
