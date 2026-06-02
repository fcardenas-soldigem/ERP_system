import React, { useState, useEffect, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { produccionService } from '../../services/produccion.service';
import { inventarioService } from '../../services/inventario.service'; // Solo para almacenes
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  Box,
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
  Badge,
  Progress,
  Alert,
  AlertIcon,
  Icon,
  Spinner,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  Collapse,
  useDisclosure,
  useToast,
  useColorModeValue,
  Divider
} from '@chakra-ui/react';
import { 
  ChevronDownIcon, 
  ChevronUpIcon, 
  CheckIcon, 
  WarningIcon,
  InfoIcon
} from '@chakra-ui/icons';
import { FiTarget, FiClock, FiDollarSign, FiBox, FiAlertCircle, FiCheckCircle } from 'react-icons/fi';

const QuickCreateOrden = ({ isOpen, onClose }) => {
  const queryClient = useQueryClient();
  const toast = useToast();
  const cardBg = useColorModeValue('white', 'gray.800');
  const { isOpen: showDetails, onToggle: toggleDetails } = useDisclosure();

  // Estado del formulario
  const [formData, setFormData] = useState({
    producto_terminado: '',
    receta: '',
    cantidad_planificada: 1,
    fecha_programada: new Date().toISOString().split('T')[0],
    almacen_insumos: '',
    almacen_destino: '',
    responsable_nombre: '',
    notas: ''
  });

  const [verificacionStock, setVerificacionStock] = useState(null);
  const [loadingStock, setLoadingStock] = useState(false);

  // Queries
  const { data: recetas = [] } = useQuery({
    queryKey: ['recetas'],
    queryFn: async () => {
      const response = await produccionService.getRecetas();
      const data = response.data;
      return Array.isArray(data) ? data : data?.results || [];
    }
  });

  const { data: almacenes = [] } = useQuery({
    queryKey: ['almacenes'],
    queryFn: async () => {
      const data = await inventarioService.getAlmacenes();
      return Array.isArray(data) ? data : data?.results || [];
    }
  });

  // Solo productos terminados que tienen recetas activas
  const productosConReceta = useMemo(() => {
    const productosIds = new Set(
      recetas
        .filter(r => r.is_active || r.activa)
        .map(r => r.producto_terminado)
    );
    
    return recetas
      .filter(r => r.is_active || r.activa)
      .reduce((acc, r) => {
        if (!acc.find(p => p.id === r.producto_terminado)) {
          acc.push({
            id: r.producto_terminado,
            nombre: r.producto_terminado_nombre,
            sku: r.producto_terminado_sku
          });
        }
        return acc;
      }, []);
  }, [recetas]);

  // Recetas disponibles para el producto seleccionado
  const recetasProducto = useMemo(() => {
    if (!formData.producto_terminado) return [];
    return recetas.filter(r => 
      r.producto_terminado === Number(formData.producto_terminado) && (r.is_active || r.activa)
    );
  }, [formData.producto_terminado, recetas]);

  // Receta seleccionada
  const recetaSeleccionada = useMemo(() => {
    if (!formData.receta) return null;
    return recetas.find(r => r.id === Number(formData.receta));
  }, [formData.receta, recetas]);

  // Costos y tiempo estimados
  const costoEstimado = useMemo(() => {
    if (!recetaSeleccionada) return 0;
    const costoUnitario = recetaSeleccionada.costo_teorico || recetaSeleccionada.costo_total || recetaSeleccionada.costos?.costo_unitario || 0;
    return costoUnitario * formData.cantidad_planificada;
  }, [recetaSeleccionada, formData.cantidad_planificada]);

  const tiempoEstimado = useMemo(() => {
    if (!recetaSeleccionada) return 0;
    return (recetaSeleccionada.tiempo_estimado || 0) * formData.cantidad_planificada / 60;
  }, [recetaSeleccionada, formData.cantidad_planificada]);

  // Auto-seleccionar receta cuando se elige producto
  const prevProductoRef = React.useRef(formData.producto_terminado);
  useEffect(() => {
    // Solo ejecutar si cambió el producto (no cuando cambian las recetas)
    if (prevProductoRef.current !== formData.producto_terminado) {
      prevProductoRef.current = formData.producto_terminado;
      
      if (formData.producto_terminado) {
        const recetasDisponibles = recetas.filter(r => 
          r.producto_terminado === Number(formData.producto_terminado) && (r.is_active || r.activa)
        );
        if (recetasDisponibles.length > 0) {
          setFormData(prev => ({ ...prev, receta: recetasDisponibles[0].id.toString() }));
        } else {
          setFormData(prev => ({ ...prev, receta: '' }));
        }
      } else {
        setFormData(prev => ({ ...prev, receta: '' }));
      }
      setVerificacionStock(null);
    }
  }, [formData.producto_terminado, recetas]);

  // Verificar stock cuando cambia cantidad o receta (cálculo local basado en la receta)
  useEffect(() => {
    const verificar = async () => {
      if (!formData.receta || !formData.cantidad_planificada) {
        setVerificacionStock(null);
        return;
      }

      setLoadingStock(true);
      try {
        // Obtener los detalles de la receta directamente
        const response = await produccionService.getReceta(formData.receta);
        const recetaData = response.data;
        const detalles = recetaData?.detalles || [];
        
        if (detalles.length === 0) {
          setVerificacionStock({ suficiente: true, materiales: [] });
          return;
        }
        
        // Calcular materiales necesarios vs disponibles
        const materiales = detalles.map(det => {
          const cantidadRequerida = parseFloat(det.cantidad || 0) * formData.cantidad_planificada;
          const stockDisponible = parseFloat(det.insumo_stock || det.stock_disponible || 0);
          
          return {
            nombre: det.insumo_nombre || det.materia_prima_nombre || det.producto_nombre || 'Material',
            requerido: cantidadRequerida,
            disponible: stockDisponible,
            suficiente: stockDisponible >= cantidadRequerida,
            unidad: det.unidad_medida || 'und'
          };
        });
        
        setVerificacionStock({
          suficiente: materiales.every(m => m.suficiente),
          materiales
        });
      } catch (error) {
        console.error('Error verificando stock:', error);
        setVerificacionStock(null);
      } finally {
        setLoadingStock(false);
      }
    };

    const timer = setTimeout(verificar, 500);
    return () => clearTimeout(timer);
  }, [formData.receta, formData.cantidad_planificada]);

  // Mutation para crear
  const createMutation = useMutation({
    mutationFn: (data) => produccionService.createOrden(data),
    onSuccess: () => {
      queryClient.invalidateQueries(['ordenes-produccion']);
      queryClient.invalidateQueries(['dashboard-produccion']);
      toast({
        title: 'Orden creada exitosamente',
        status: 'success',
        duration: 3000
      });
      handleClose();
    },
    onError: (error) => {
      toast({
        title: 'Error al crear orden',
        description: error.message,
        status: 'error',
        duration: 5000
      });
    }
  });

  const handleClose = () => {
    setFormData({
      producto_terminado: '',
      receta: '',
      cantidad_planificada: 1,
      fecha_programada: new Date().toISOString().split('T')[0],
      almacen_insumos: '',
      almacen_destino: '',
      responsable_nombre: '',
      notas: ''
    });
    setVerificacionStock(null);
    onClose();
  };

  const handleSubmit = () => {
    if (!formData.producto_terminado || !formData.receta || !formData.cantidad_planificada) {
      toast({
        title: 'Campos requeridos',
        description: 'Completa todos los campos obligatorios',
        status: 'warning',
        duration: 3000
      });
      return;
    }

    // Usar el primer almacén si no se seleccionó ninguno
    const almacenInsumos = formData.almacen_insumos || (almacenes.length > 0 ? almacenes[0].id : null);
    const almacenDestino = formData.almacen_destino || (almacenes.length > 0 ? almacenes[0].id : null);

    if (!almacenInsumos || !almacenDestino) {
      toast({
        title: 'Error',
        description: 'No hay almacenes disponibles. Crea un almacén primero.',
        status: 'error',
        duration: 5000
      });
      return;
    }

    const data = {
      receta_id: Number(formData.receta),
      cantidad: Number(formData.cantidad_planificada),
      fecha_programada: formData.fecha_programada,
      almacen_insumos_id: Number(almacenInsumos),
      almacen_destino_id: Number(almacenDestino),
      observaciones: formData.responsable_nombre 
        ? `Responsable: ${formData.responsable_nombre}\n${formData.notas || ''}`
        : (formData.notas || '')
    };

    createMutation.mutate(data);
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('es-PE', {
      style: 'currency',
      currency: 'PEN'
    }).format(amount || 0);
  };

  const stockSuficiente = verificacionStock?.suficiente !== false;

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="lg" scrollBehavior="inside">
      <ModalOverlay bg="blackAlpha.600" />
      <ModalContent borderRadius="2xl" m={4}>
        <ModalHeader>
          <Text fontSize="xl" fontWeight="bold">
            Nueva Orden de Producción
          </Text>
          <Text fontSize="sm" fontWeight="normal" color="gray.500">
            Crea una orden en 3 sencillos pasos
          </Text>
        </ModalHeader>
        <ModalCloseButton />

        <ModalBody>
          <VStack spacing={5} align="stretch">
            {/* Producto - Solo productos con recetas activas */}
            <FormControl isRequired>
              <FormLabel fontWeight="semibold">Producto a Producir</FormLabel>
              {productosConReceta.length === 0 ? (
                <Alert status="warning" borderRadius="md">
                  <AlertIcon />
                  <Text fontSize="sm">No hay productos con recetas activas. Crea una receta primero.</Text>
                </Alert>
              ) : (
                <Select
                  placeholder="Seleccionar producto..."
                  value={formData.producto_terminado}
                  onChange={(e) => setFormData(prev => ({ ...prev, producto_terminado: e.target.value }))}
                  size="lg"
                >
                  {productosConReceta.map(p => (
                    <option key={p.id} value={p.id}>
                      {p.nombre} {p.sku ? `(${p.sku})` : ''}
                    </option>
                  ))}
                </Select>
              )}
            </FormControl>

            {/* Receta */}
            {formData.producto_terminado && (
              <Box 
                p={4} 
                bg="blue.50" 
                borderRadius="xl" 
                borderWidth="2px" 
                borderColor="blue.200"
              >
                <HStack justify="space-between" mb={2}>
                  <HStack>
                    <Icon as={FiTarget} color="blue.500" />
                    <Text fontWeight="semibold" color="blue.700">Receta</Text>
                  </HStack>
                  {recetasProducto.length > 1 && (
                    <Badge colorScheme="blue">{recetasProducto.length} disponibles</Badge>
                  )}
                </HStack>
                
                {recetasProducto.length === 0 ? (
                  <Alert status="warning" borderRadius="md">
                    <AlertIcon />
                    <Text fontSize="sm">No hay recetas activas para este producto</Text>
                  </Alert>
                ) : recetasProducto.length === 1 ? (
                  <Text color="blue.700">{recetasProducto[0].nombre}</Text>
                ) : (
                  <Select
                    value={formData.receta}
                    onChange={(e) => setFormData(prev => ({ ...prev, receta: e.target.value }))}
                    bg="white"
                  >
                    {recetasProducto.map(r => (
                      <option key={r.id} value={r.id}>{r.nombre}</option>
                    ))}
                  </Select>
                )}
              </Box>
            )}

            {/* Cantidad y Fecha */}
            <SimpleGrid columns={2} spacing={4}>
              <FormControl isRequired>
                <FormLabel fontWeight="semibold">Cantidad a Producir</FormLabel>
                <Input
                  type="number"
                  min={1}
                  value={formData.cantidad_planificada}
                  onChange={(e) => setFormData(prev => ({ ...prev, cantidad_planificada: Number(e.target.value) }))}
                  size="lg"
                />
              </FormControl>

              <FormControl>
                <FormLabel fontWeight="semibold">Fecha Programada</FormLabel>
                <Input
                  type="date"
                  value={formData.fecha_programada}
                  onChange={(e) => setFormData(prev => ({ ...prev, fecha_programada: e.target.value }))}
                  size="lg"
                />
              </FormControl>
            </SimpleGrid>

            {/* Almacenes */}
            {almacenes.length > 1 && (
              <SimpleGrid columns={2} spacing={4}>
                <FormControl>
                  <FormLabel fontWeight="semibold">Almacén de Insumos</FormLabel>
                  <Select
                    placeholder="Seleccionar almacén..."
                    value={formData.almacen_insumos}
                    onChange={(e) => setFormData(prev => ({ ...prev, almacen_insumos: e.target.value }))}
                  >
                    {almacenes.map(a => (
                      <option key={a.id} value={a.id}>{a.nombre}</option>
                    ))}
                  </Select>
                </FormControl>

                <FormControl>
                  <FormLabel fontWeight="semibold">Almacén de Destino</FormLabel>
                  <Select
                    placeholder="Seleccionar almacén..."
                    value={formData.almacen_destino}
                    onChange={(e) => setFormData(prev => ({ ...prev, almacen_destino: e.target.value }))}
                  >
                    {almacenes.map(a => (
                      <option key={a.id} value={a.id}>{a.nombre}</option>
                    ))}
                  </Select>
                </FormControl>
              </SimpleGrid>
            )}

            {/* Responsable (opcional) */}
            <FormControl>
              <FormLabel fontWeight="semibold">Responsable (opcional)</FormLabel>
              <Input
                placeholder="Nombre del responsable..."
                value={formData.responsable_nombre || ''}
                onChange={(e) => setFormData(prev => ({ ...prev, responsable_nombre: e.target.value }))}
              />
            </FormControl>

            {/* Verificación de Stock */}
            {formData.receta && (
              <Box 
                p={4} 
                borderRadius="xl" 
                borderWidth="2px"
                borderColor={loadingStock ? 'gray.200' : stockSuficiente ? 'green.200' : 'orange.200'}
                bg={loadingStock ? 'gray.50' : stockSuficiente ? 'green.50' : 'orange.50'}
              >
                <Flex justify="space-between" align="center" mb={3}>
                  <HStack>
                    {loadingStock ? (
                      <Spinner size="sm" color="blue.500" />
                    ) : stockSuficiente ? (
                      <Icon as={FiCheckCircle} color="green.500" boxSize={5} />
                    ) : (
                      <Icon as={FiAlertCircle} color="orange.500" boxSize={5} />
                    )}
                    <Text fontWeight="semibold" color={stockSuficiente ? 'green.700' : 'orange.700'}>
                      {loadingStock ? 'Verificando stock...' : stockSuficiente ? 'Stock suficiente' : 'Stock insuficiente'}
                    </Text>
                  </HStack>
                  {verificacionStock && (
                    <Button
                      size="xs"
                      variant="ghost"
                      rightIcon={showDetails ? <ChevronUpIcon /> : <ChevronDownIcon />}
                      onClick={toggleDetails}
                    >
                      {showDetails ? 'Ocultar' : 'Ver detalles'}
                    </Button>
                  )}
                </Flex>

                <Collapse in={showDetails}>
                  {verificacionStock?.materiales && (
                    <VStack spacing={2} align="stretch">
                      {verificacionStock.materiales.map((mat, idx) => (
                        <Flex 
                          key={idx} 
                          justify="space-between" 
                          align="center"
                          p={2}
                          bg="white"
                          borderRadius="md"
                          fontSize="sm"
                        >
                          <Text>{mat.nombre}</Text>
                          <HStack spacing={3}>
                            <Text color="gray.600">
                              Necesitas: {mat.requerido} {mat.unidad}
                            </Text>
                            <Text color={mat.suficiente ? 'green.600' : 'red.600'}>
                              Disponible: {mat.disponible}
                            </Text>
                            {mat.suficiente ? (
                              <Icon as={CheckIcon} color="green.500" />
                            ) : (
                              <Icon as={WarningIcon} color="red.500" />
                            )}
                          </HStack>
                        </Flex>
                      ))}
                    </VStack>
                  )}
                </Collapse>

                {!stockSuficiente && !loadingStock && (
                  <Alert status="warning" mt={3} borderRadius="md" variant="subtle">
                    <AlertIcon />
                    <Text fontSize="sm">Puedes crear la orden aunque falte stock. Se marcará como pendiente de materiales.</Text>
                  </Alert>
                )}
              </Box>
            )}

            {/* Resumen de Costos */}
            {recetaSeleccionada && (
              <Box bg="gray.50" p={4} borderRadius="xl" borderWidth="1px" borderColor="gray.200">
                <SimpleGrid columns={2} spacing={4}>
                  <Stat textAlign="center">
                    <StatLabel>
                      <HStack justify="center">
                        <Icon as={FiDollarSign} />
                        <Text>Costo Estimado</Text>
                      </HStack>
                    </StatLabel>
                    <StatNumber color="green.600" fontSize="xl">
                      {formatCurrency(costoEstimado)}
                    </StatNumber>
                  </Stat>
                  <Stat textAlign="center">
                    <StatLabel>
                      <HStack justify="center">
                        <Icon as={FiClock} />
                        <Text>Tiempo Estimado</Text>
                      </HStack>
                    </StatLabel>
                    <StatNumber color="blue.600" fontSize="xl">
                      {tiempoEstimado.toFixed(1)} hrs
                    </StatNumber>
                  </Stat>
                </SimpleGrid>
              </Box>
            )}

            {/* Notas */}
            <FormControl>
              <FormLabel fontWeight="semibold">Notas (opcional)</FormLabel>
              <Textarea
                placeholder="Instrucciones especiales para esta orden..."
                value={formData.notas}
                onChange={(e) => setFormData(prev => ({ ...prev, notas: e.target.value }))}
                rows={2}
              />
            </FormControl>
          </VStack>
        </ModalBody>

        <ModalFooter borderTopWidth="1px" pt={4}>
          <HStack spacing={3}>
            <Button variant="ghost" onClick={handleClose}>
              Cancelar
            </Button>
            <Button
              colorScheme="blue"
              onClick={handleSubmit}
              isLoading={createMutation.isLoading}
              isDisabled={!formData.producto_terminado || !formData.receta || !formData.cantidad_planificada}
              leftIcon={<Icon as={FiCheckCircle} />}
            >
              Crear Orden
            </Button>
          </HStack>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default QuickCreateOrden;
