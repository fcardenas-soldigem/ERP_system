import React, { useState, useEffect, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { produccionService } from '../../services/produccion.service';
import { inventarioService } from '../../services/inventario.service';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  Box,
  Heading,
  Text,
  Flex,
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
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  Divider,
  useToast,
  useColorModeValue,
  Collapse,
  useDisclosure
} from '@chakra-ui/react';
import { 
  AddIcon, 
  DeleteIcon, 
  ChevronLeftIcon, 
  ChevronRightIcon,
  CheckIcon,
  WarningIcon,
  SearchIcon,
  ChevronDownIcon,
  ChevronUpIcon
} from '@chakra-ui/icons';
import { FiPackage, FiBox, FiClipboard, FiDollarSign, FiClock } from 'react-icons/fi';

const RecetaWizard = ({ isOpen, onClose, recetaToEdit = null }) => {
  const queryClient = useQueryClient();
  const toast = useToast();
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  // Estado del wizard
  const [paso, setPaso] = useState(1);
  const [showMaterialModal, setShowMaterialModal] = useState(false);
  
  // Estado del formulario
  const [formData, setFormData] = useState({
    producto_terminado: '',
    nombre: '',
    cantidad_producida: 1,
    activa: true,
    notas: '',
    tiempo_estimado: 120,
    costo_mano_obra: 0,
    costos_indirectos: 0
  });

  const [materiales, setMateriales] = useState([]);
  const [materialActual, setMaterialActual] = useState({
    materia_prima: '',
    cantidad: '',
    desperdicio: 0,
    opcional: false
  });

  // Queries - inventarioService ya devuelve los datos procesados directamente
  const { data: productosTerminados = [] } = useQuery({
    queryKey: ['productos-terminados'],
    queryFn: () => inventarioService.getProductosTerminados()
  });

  const { data: materiasPrimas = [] } = useQuery({
    queryKey: ['materias-primas'],
    queryFn: () => inventarioService.getMateriasPrimas()
  });

  // Mutation
  const saveMutation = useMutation({
    mutationFn: async (data) => {
      if (recetaToEdit) {
        return await produccionService.updateReceta(recetaToEdit.id, data);
      }
      return await produccionService.createReceta(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['recetas']);
      toast({
        title: recetaToEdit ? 'Receta actualizada' : 'Receta creada',
        status: 'success',
        duration: 3000
      });
      handleClose();
    },
    onError: (error) => {
      toast({
        title: 'Error al guardar',
        description: error.message,
        status: 'error',
        duration: 5000
      });
    }
  });

  // Cargar datos si estamos editando
  useEffect(() => {
    if (recetaToEdit) {
      setFormData({
        producto_terminado: recetaToEdit.producto_terminado || '',
        nombre: recetaToEdit.nombre || '',
        cantidad_producida: recetaToEdit.cantidad_producida || 1,
        activa: recetaToEdit.activa !== false,
        notas: recetaToEdit.notas || '',
        tiempo_estimado: recetaToEdit.tiempo_estimado || 120,
        costo_mano_obra: recetaToEdit.costo_mano_obra || 0,
        costos_indirectos: recetaToEdit.costos_indirectos || 0
      });
      setMateriales(recetaToEdit.detalles || []);
    } else {
      resetForm();
    }
    setPaso(1);
  }, [recetaToEdit, isOpen]);

  const resetForm = () => {
    setFormData({
      producto_terminado: '',
      nombre: '',
      cantidad_producida: 1,
      activa: true,
      notas: '',
      tiempo_estimado: 120,
      costo_mano_obra: 0,
      costos_indirectos: 0
    });
    setMateriales([]);
    setPaso(1);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  // Calcular costos
  const costoMateriales = useMemo(() => {
    return materiales.reduce((sum, m) => {
      const mp = materiasPrimas.find(p => (p.producto || p.id) === Number(m.materia_prima));
      const cantidad = Number(m.cantidad) * (1 + (Number(m.desperdicio) / 100));
      return sum + (cantidad * (mp?.costo_unitario_promedio || mp?.costo_unitario || 0));
    }, 0);
  }, [materiales, materiasPrimas]);

  const costoTotal = useMemo(() => {
    return costoMateriales + Number(formData.costo_mano_obra || 0) + Number(formData.costos_indirectos || 0);
  }, [costoMateriales, formData.costo_mano_obra, formData.costos_indirectos]);

  // Handlers
  const handleProductoChange = (e) => {
    const productoId = e.target.value;
    const producto = productosTerminados.find(p => (p.producto || p.id) === Number(productoId));
    const nombreProducto = producto?.producto_nombre || producto?.nombre;
    
    setFormData(prev => ({
      ...prev,
      producto_terminado: productoId,
      nombre: nombreProducto ? `Receta estándar - ${nombreProducto}` : ''
    }));
  };

  const handleAddMaterial = () => {
    if (!materialActual.materia_prima || !materialActual.cantidad) {
      toast({
        title: 'Campos requeridos',
        description: 'Selecciona un material y cantidad',
        status: 'warning',
        duration: 3000
      });
      return;
    }

    const mp = materiasPrimas.find(p => (p.producto || p.id) === Number(materialActual.materia_prima));
    
    setMateriales(prev => [...prev, {
      ...materialActual,
      nombre: mp?.producto_nombre || mp?.nombre || 'Material',
      unidad: mp?.unidad_medida || 'und',
      costo_unitario: mp?.costo_unitario_promedio || mp?.costo_unitario || 0
    }]);

    setMaterialActual({
      materia_prima: '',
      cantidad: '',
      desperdicio: 0,
      opcional: false
    });
    setShowMaterialModal(false);
  };

  const handleRemoveMaterial = (index) => {
    setMateriales(prev => prev.filter((_, i) => i !== index));
  };

  const handleSave = () => {
    if (!formData.producto_terminado || !formData.nombre || materiales.length === 0) {
      toast({
        title: 'Faltan datos',
        description: 'Completa todos los campos y agrega al menos un material',
        status: 'warning',
        duration: 3000
      });
      return;
    }

    // Preparar datos para el backend (mapear campos del frontend a los del backend)
    const data = {
      producto_terminado: Number(formData.producto_terminado),
      nombre: formData.nombre,
      cantidad_producida: Number(formData.cantidad_producida),
      tiempo_estimado: Number(formData.tiempo_estimado || 0),
      costo_mano_obra: Number(formData.costo_mano_obra || 0),
      costo_indirecto: Number(formData.costos_indirectos || 0), // Backend usa 'costo_indirecto'
      is_active: formData.activa, // Backend usa 'is_active'
      notas: formData.notas || '',
      detalles: materiales.map(m => {
        // Buscar la materia prima para obtener datos adicionales
        const mp = materiasPrimas.find(p => (p.producto || p.id) === Number(m.materia_prima));
        return {
          insumo: Number(m.materia_prima), // Backend espera 'insumo', no 'materia_prima'
          cantidad: Number(m.cantidad),
          // NO enviar unidad_medida - el backend la asigna automáticamente del insumo
          costo_unitario: Number(m.costo_unitario || mp?.costo_unitario_promedio || 0)
        };
      })
    };

    console.log('Datos a enviar al backend:', data);
    saveMutation.mutate(data);
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('es-PE', {
      style: 'currency',
      currency: 'PEN'
    }).format(amount || 0);
  };

  const pasos = [
    { num: 1, title: 'Información Básica', icon: FiClipboard },
    { num: 2, title: 'Materiales', icon: FiBox },
    { num: 3, title: 'Costos y Resumen', icon: FiDollarSign }
  ];

  const canProceed = () => {
    if (paso === 1) {
      return formData.producto_terminado && formData.nombre && formData.cantidad_producida > 0;
    }
    if (paso === 2) {
      return materiales.length > 0;
    }
    return true;
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="xl" scrollBehavior="inside">
      <ModalOverlay bg="blackAlpha.600" />
      <ModalContent borderRadius="2xl" maxW="700px" m={4}>
        {/* Header con stepper */}
        <ModalHeader pb={0}>
          <Text fontSize="xl" fontWeight="bold" mb={4}>
            {recetaToEdit ? 'Editar Receta' : 'Nueva Receta de Producción'}
          </Text>
          
          {/* Stepper */}
          <HStack spacing={0} mb={4}>
            {pasos.map((p, index) => (
              <React.Fragment key={p.num}>
                <VStack spacing={1} flex={1}>
                  <Flex
                    w="40px"
                    h="40px"
                    borderRadius="full"
                    bg={paso >= p.num ? 'green.500' : 'gray.200'}
                    color={paso >= p.num ? 'white' : 'gray.500'}
                    align="center"
                    justify="center"
                    transition="all 0.3s"
                  >
                    {paso > p.num ? <CheckIcon /> : <Icon as={p.icon} />}
                  </Flex>
                  <Text fontSize="xs" color={paso >= p.num ? 'green.600' : 'gray.500'} fontWeight="medium">
                    {p.title}
                  </Text>
                </VStack>
                {index < pasos.length - 1 && (
                  <Box flex={1} h="3px" bg={paso > p.num ? 'green.500' : 'gray.200'} mx={2} borderRadius="full" />
                )}
              </React.Fragment>
            ))}
          </HStack>
        </ModalHeader>

        <ModalCloseButton />

        <ModalBody py={6}>
          {/* PASO 1: Información Básica */}
          {paso === 1 && (
            <VStack spacing={5} align="stretch">
              <FormControl isRequired>
                <FormLabel fontWeight="semibold">Producto Final</FormLabel>
                <Select
                  placeholder="Seleccionar producto terminado..."
                  value={formData.producto_terminado}
                  onChange={handleProductoChange}
                  size="lg"
                >
                  {productosTerminados.map(p => (
                    <option key={p.id} value={p.producto || p.id}>
                      {p.producto_nombre || p.nombre} {(p.producto_sku || p.sku) ? `(${p.producto_sku || p.sku})` : ''}
                    </option>
                  ))}
                </Select>
              </FormControl>

              <FormControl isRequired>
                <FormLabel fontWeight="semibold">Nombre de la Receta</FormLabel>
                <Input
                  placeholder="Ej: Receta estándar Mesa Comedor"
                  value={formData.nombre}
                  onChange={(e) => setFormData(prev => ({ ...prev, nombre: e.target.value }))}
                  size="lg"
                />
              </FormControl>

              <FormControl isRequired>
                <FormLabel fontWeight="semibold">Cantidad que Produce</FormLabel>
                <HStack>
                  <Input
                    type="number"
                    min={1}
                    value={formData.cantidad_producida}
                    onChange={(e) => setFormData(prev => ({ ...prev, cantidad_producida: Number(e.target.value) }))}
                    w="120px"
                    size="lg"
                  />
                  <Text color="gray.600">unidades por cada ejecución</Text>
                </HStack>
              </FormControl>

              <FormControl display="flex" alignItems="center">
                <Switch
                  id="activa"
                  isChecked={formData.activa}
                  onChange={(e) => setFormData(prev => ({ ...prev, activa: e.target.checked }))}
                  colorScheme="green"
                  size="lg"
                  mr={3}
                />
                <FormLabel htmlFor="activa" mb={0}>
                  Receta activa
                </FormLabel>
              </FormControl>

              <FormControl>
                <FormLabel fontWeight="semibold">Notas / Instrucciones</FormLabel>
                <Textarea
                  placeholder="Instrucciones especiales para esta receta..."
                  value={formData.notas}
                  onChange={(e) => setFormData(prev => ({ ...prev, notas: e.target.value }))}
                  rows={3}
                />
              </FormControl>
            </VStack>
          )}

          {/* PASO 2: Materiales */}
          {paso === 2 && (
            <VStack spacing={5} align="stretch">
              <Flex justify="space-between" align="center">
                <Text fontWeight="semibold">Materiales e Insumos Necesarios</Text>
                <Button
                  leftIcon={<AddIcon />}
                  colorScheme="green"
                  size="sm"
                  onClick={() => setShowMaterialModal(true)}
                >
                  Agregar Material
                </Button>
              </Flex>

              {materiales.length === 0 ? (
                <Box textAlign="center" py={8} bg="gray.50" borderRadius="xl">
                  <Icon as={FiBox} boxSize={10} color="gray.400" mb={3} />
                  <Text color="gray.600" mb={2}>No hay materiales agregados</Text>
                  <Text color="gray.500" fontSize="sm">
                    Agrega los materiales necesarios para esta receta
                  </Text>
                </Box>
              ) : (
                <VStack spacing={3} align="stretch">
                  {materiales.map((material, index) => {
                    const mp = materiasPrimas.find(p => (p.producto || p.id) === Number(material.materia_prima));
                    const stockDisponible = mp?.cantidad_disponible || 0;
                    
                    return (
                      <Box
                        key={index}
                        p={4}
                        bg="white"
                        borderWidth="2px"
                        borderColor="gray.200"
                        borderRadius="xl"
                        position="relative"
                        _hover={{ borderColor: 'green.300' }}
                        transition="all 0.2s"
                      >
                        <Flex justify="space-between" align="start">
                          <Box flex={1}>
                            <HStack mb={2}>
                              <Icon as={FiPackage} color="green.500" />
                              <Text fontWeight="bold">{material.nombre || mp?.producto_nombre || mp?.nombre}</Text>
                              {material.opcional && (
                                <Badge colorScheme="gray" fontSize="xs">Opcional</Badge>
                              )}
                            </HStack>
                            <SimpleGrid columns={3} spacing={4} fontSize="sm">
                              <Box>
                                <Text color="gray.500">Cantidad</Text>
                                <Text fontWeight="medium">{material.cantidad} {material.unidad || mp?.unidad_medida}</Text>
                              </Box>
                              <Box>
                                <Text color="gray.500">Stock</Text>
                                <Text fontWeight="medium" color={stockDisponible > Number(material.cantidad) ? 'green.600' : 'red.500'}>
                                  {stockDisponible} disponible
                                </Text>
                              </Box>
                              <Box>
                                <Text color="gray.500">Desperdicio</Text>
                                <Text fontWeight="medium">{material.desperdicio || 0}%</Text>
                              </Box>
                            </SimpleGrid>
                          </Box>
                          <IconButton
                            icon={<DeleteIcon />}
                            variant="ghost"
                            colorScheme="red"
                            size="sm"
                            onClick={() => handleRemoveMaterial(index)}
                            aria-label="Eliminar material"
                          />
                        </Flex>
                      </Box>
                    );
                  })}
                </VStack>
              )}

              {/* Costo de materiales */}
              {materiales.length > 0 && (
                <Box bg="green.50" p={4} borderRadius="xl" borderWidth="2px" borderColor="green.200">
                  <Flex justify="space-between" align="center">
                    <HStack>
                      <Icon as={FiDollarSign} color="green.600" />
                      <Text fontWeight="semibold" color="green.700">Costo Estimado de Materiales</Text>
                    </HStack>
                    <Text fontSize="xl" fontWeight="bold" color="green.600">
                      {formatCurrency(costoMateriales)}
                    </Text>
                  </Flex>
                </Box>
              )}

              {/* Modal para agregar material */}
              <Modal isOpen={showMaterialModal} onClose={() => setShowMaterialModal(false)} isCentered>
                <ModalOverlay />
                <ModalContent borderRadius="xl">
                  <ModalHeader>Agregar Material</ModalHeader>
                  <ModalCloseButton />
                  <ModalBody pb={6}>
                    <VStack spacing={4}>
                      <FormControl isRequired>
                        <FormLabel>Material / Insumo</FormLabel>
                        <Select
                          placeholder="Seleccionar materia prima..."
                          value={materialActual.materia_prima}
                          onChange={(e) => setMaterialActual(prev => ({ ...prev, materia_prima: e.target.value }))}
                        >
                          {materiasPrimas.map(mp => (
                            <option key={mp.id} value={mp.producto || mp.id}>
                              {mp.producto_nombre || mp.nombre} ({mp.cantidad_disponible || 0} {mp.unidad_medida} disponibles)
                            </option>
                          ))}
                        </Select>
                      </FormControl>

                      <FormControl isRequired>
                        <FormLabel>Cantidad Requerida</FormLabel>
                        <HStack>
                          <Input
                            type="number"
                            step="0.01"
                            placeholder="0"
                            value={materialActual.cantidad}
                            onChange={(e) => setMaterialActual(prev => ({ ...prev, cantidad: e.target.value }))}
                          />
                          <Text color="gray.600" minW="80px">
                            {materiasPrimas.find(p => (p.producto || p.id) === Number(materialActual.materia_prima))?.unidad_medida || 'unidades'}
                          </Text>
                        </HStack>
                      </FormControl>

                      <FormControl>
                        <FormLabel>% de Desperdicio</FormLabel>
                        <Input
                          type="number"
                          placeholder="0"
                          value={materialActual.desperdicio}
                          onChange={(e) => setMaterialActual(prev => ({ ...prev, desperdicio: Number(e.target.value) }))}
                        />
                      </FormControl>

                      <FormControl display="flex" alignItems="center">
                        <Switch
                          isChecked={materialActual.opcional}
                          onChange={(e) => setMaterialActual(prev => ({ ...prev, opcional: e.target.checked }))}
                          colorScheme="blue"
                          mr={3}
                        />
                        <FormLabel mb={0}>Material opcional (no bloquea producción)</FormLabel>
                      </FormControl>
                    </VStack>
                  </ModalBody>
                  <ModalFooter>
                    <Button variant="ghost" mr={3} onClick={() => setShowMaterialModal(false)}>
                      Cancelar
                    </Button>
                    <Button colorScheme="green" onClick={handleAddMaterial}>
                      Agregar Material
                    </Button>
                  </ModalFooter>
                </ModalContent>
              </Modal>
            </VStack>
          )}

          {/* PASO 3: Costos y Resumen */}
          {paso === 3 && (
            <VStack spacing={5} align="stretch">
              <Text fontWeight="semibold" fontSize="lg">Tiempo y Costos de Producción</Text>

              <SimpleGrid columns={2} spacing={4}>
                <FormControl>
                  <FormLabel>Tiempo Estimado</FormLabel>
                  <HStack>
                    <Input
                      type="number"
                      value={formData.tiempo_estimado}
                      onChange={(e) => setFormData(prev => ({ ...prev, tiempo_estimado: Number(e.target.value) }))}
                      w="100px"
                    />
                    <Text color="gray.600">minutos = {(formData.tiempo_estimado / 60).toFixed(1)} hrs</Text>
                  </HStack>
                </FormControl>

                <FormControl>
                  <FormLabel>Costo Mano de Obra (S/)</FormLabel>
                  <Input
                    type="number"
                    step="0.01"
                    value={formData.costo_mano_obra}
                    onChange={(e) => setFormData(prev => ({ ...prev, costo_mano_obra: Number(e.target.value) }))}
                  />
                </FormControl>
              </SimpleGrid>

              <FormControl>
                <FormLabel>Costos Indirectos / CIF (S/)</FormLabel>
                <Input
                  type="number"
                  step="0.01"
                  placeholder="Electricidad, agua, depreciación, etc."
                  value={formData.costos_indirectos}
                  onChange={(e) => setFormData(prev => ({ ...prev, costos_indirectos: Number(e.target.value) }))}
                />
              </FormControl>

              {/* Resumen */}
              <Box bg="gray.50" p={6} borderRadius="xl" borderWidth="2px" borderColor="gray.200">
                <Heading size="md" mb={4} color="gray.700">
                  📊 Resumen Final
                </Heading>

                <VStack spacing={3} align="stretch" mb={5}>
                  <Flex justify="space-between">
                    <Text color="gray.600">Producto:</Text>
                    <Text fontWeight="medium">
                      {(() => {
                        const p = productosTerminados.find(pt => (pt.producto || pt.id) === Number(formData.producto_terminado));
                        return p?.producto_nombre || p?.nombre || '-';
                      })()}
                    </Text>
                  </Flex>
                  <Flex justify="space-between">
                    <Text color="gray.600">Produce:</Text>
                    <Text fontWeight="medium">{formData.cantidad_producida} unidad(es)</Text>
                  </Flex>
                  <Flex justify="space-between">
                    <Text color="gray.600">Materiales:</Text>
                    <Text fontWeight="medium">{materiales.length} items</Text>
                  </Flex>
                  <Flex justify="space-between">
                    <Text color="gray.600">Tiempo estimado:</Text>
                    <Text fontWeight="medium">{(formData.tiempo_estimado / 60).toFixed(1)} horas</Text>
                  </Flex>
                </VStack>

                <Divider my={4} />

                <VStack spacing={2} align="stretch">
                  <Flex justify="space-between">
                    <Text>Materiales:</Text>
                    <Text>{formatCurrency(costoMateriales)}</Text>
                  </Flex>
                  <Flex justify="space-between">
                    <Text>Mano de Obra:</Text>
                    <Text>{formatCurrency(formData.costo_mano_obra)}</Text>
                  </Flex>
                  <Flex justify="space-between">
                    <Text>Costos Indirectos:</Text>
                    <Text>{formatCurrency(formData.costos_indirectos)}</Text>
                  </Flex>
                  <Divider />
                  <Flex justify="space-between" pt={2}>
                    <Text fontWeight="bold" fontSize="lg">COSTO TOTAL:</Text>
                    <Text fontWeight="bold" fontSize="xl" color="green.600">
                      {formatCurrency(costoTotal)}
                    </Text>
                  </Flex>
                </VStack>
              </Box>
            </VStack>
          )}
        </ModalBody>

        <ModalFooter borderTopWidth="1px" pt={4}>
          <HStack spacing={3} w="full" justify="space-between">
            <Button variant="ghost" onClick={handleClose}>
              Cancelar
            </Button>
            <HStack>
              {paso > 1 && (
                <Button
                  leftIcon={<ChevronLeftIcon />}
                  variant="outline"
                  onClick={() => setPaso(prev => prev - 1)}
                >
                  Atrás
                </Button>
              )}
              {paso < 3 ? (
                <Button
                  rightIcon={<ChevronRightIcon />}
                  colorScheme="green"
                  onClick={() => setPaso(prev => prev + 1)}
                  isDisabled={!canProceed()}
                >
                  Siguiente
                </Button>
              ) : (
                <Button
                  leftIcon={<CheckIcon />}
                  colorScheme="green"
                  onClick={handleSave}
                  isLoading={saveMutation.isLoading}
                >
                  {recetaToEdit ? 'Actualizar Receta' : 'Crear Receta'}
                </Button>
              )}
            </HStack>
          </HStack>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default RecetaWizard;
