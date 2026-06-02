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
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  HStack,
  VStack,
  Badge,
  Progress,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
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
  FormControl,
  FormLabel,
  Input,
  Textarea,
  useToast,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Menu,
  MenuButton,
  MenuList,
  MenuItem
} from '@chakra-ui/react';
import { 
  ChevronLeftIcon,
  ChevronDownIcon,
  EditIcon,
  CopyIcon,
  DeleteIcon,
  CheckIcon,
  WarningIcon,
  TimeIcon
} from '@chakra-ui/icons';
import { FiPackage, FiBox, FiClock, FiCheckCircle, FiTarget, FiDollarSign, FiCalendar, FiUser, FiPlay, FiPause, FiActivity } from 'react-icons/fi';

const OrdenDetalle = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  const [cantidadActualizar, setCantidadActualizar] = useState(0);
  const { isOpen: isUpdateOpen, onOpen: onUpdateOpen, onClose: onUpdateClose } = useDisclosure();
  const { isOpen: isCompleteOpen, onOpen: onCompleteOpen, onClose: onCompleteClose } = useDisclosure();
  const { isOpen: isCancelOpen, onOpen: onCancelOpen, onClose: onCancelClose } = useDisclosure();

  // Query para obtener detalle
  const { data: orden, isLoading, error } = useQuery({
    queryKey: ['orden-detalle', id],
    queryFn: async () => {
      const response = await produccionService.getOrden(id);
      return response.data;
    }
  });

  // Mutations
  const iniciarMutation = useMutation({
    mutationFn: () => produccionService.iniciarOrden(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['orden-detalle', id]);
      queryClient.invalidateQueries(['inventario-materias-primas']);
      toast({ title: 'Orden iniciada', status: 'success' });
    },
    onError: (error) => {
      toast({ 
        title: 'Error al iniciar', 
        description: error.response?.data?.error || 'No se pudo iniciar la orden',
        status: 'error' 
      });
    }
  });

  const actualizarProgresoMutation = useMutation({
    mutationFn: (cantidad) => produccionService.actualizarProgreso(id, { cantidad_producida: cantidad }),
    onSuccess: () => {
      queryClient.invalidateQueries(['orden-detalle', id]);
      onUpdateClose();
      toast({ title: 'Progreso actualizado', status: 'success' });
    },
    onError: (error) => {
      toast({ 
        title: 'Error al actualizar', 
        description: error.response?.data?.error || 'No se pudo actualizar el progreso',
        status: 'error' 
      });
    }
  });

  const completarMutation = useMutation({
    mutationFn: (cantidadProducida) => produccionService.finalizarOrden(id, { 
      cantidad_producida: cantidadProducida 
    }),
    onSuccess: () => {
      queryClient.invalidateQueries(['orden-detalle', id]);
      queryClient.invalidateQueries(['ordenes-produccion']);
      onCompleteClose();
      toast({ title: 'Orden completada', status: 'success' });
    },
    onError: (error) => {
      toast({ 
        title: 'Error al completar', 
        description: error.response?.data?.error || 'No se pudo completar la orden',
        status: 'error' 
      });
    }
  });

  const cancelarMutation = useMutation({
    mutationFn: () => produccionService.cancelarOrden(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['orden-detalle', id]);
      queryClient.invalidateQueries(['ordenes-produccion']);
      onCancelClose();
      toast({ title: 'Orden cancelada', status: 'info' });
    }
  });

  const getEstadoConfig = (estado) => {
    const configs = {
      'pendiente': { color: 'gray', icon: '⚪', label: 'Pendiente', colorScheme: 'gray' },
      'planificada': { color: 'gray', icon: '⚪', label: 'Planificada', colorScheme: 'gray' },
      'en_proceso': { color: 'yellow', icon: '🟡', label: 'En Proceso', colorScheme: 'yellow' },
      'finalizada': { color: 'green', icon: '🟢', label: 'Finalizada', colorScheme: 'green' },
      'completada': { color: 'green', icon: '🟢', label: 'Completada', colorScheme: 'green' },
      'cancelada': { color: 'red', icon: '🔴', label: 'Cancelada', colorScheme: 'red' },
      'pausada': { color: 'orange', icon: '🟠', label: 'Pausada', colorScheme: 'orange' }
    };
    return configs[estado] || configs['pendiente'];
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('es-PE', {
      style: 'currency',
      currency: 'PEN'
    }).format(amount || 0);
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('es-PE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatDateShort = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('es-PE', {
      day: '2-digit',
      month: 'short'
    });
  };

  if (isLoading) {
    return (
      <Box p={6}>
        <Flex justify="center" align="center" h="400px" direction="column">
          <Spinner size="xl" color="blue.500" thickness="4px" mb={4} />
          <Text color="gray.600">Cargando detalle de la orden...</Text>
        </Flex>
      </Box>
    );
  }

  if (error || !orden) {
    return (
      <Box p={6}>
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>No se pudo cargar la orden de producción</AlertDescription>
        </Alert>
        <Button mt={4} leftIcon={<ChevronLeftIcon />} onClick={() => navigate(-1)}>
          Volver
        </Button>
      </Box>
    );
  }

  const estadoConfig = getEstadoConfig(orden.estado);
  const progreso = orden.cantidad_planificada 
    ? Math.round((orden.cantidad_producida || 0) / orden.cantidad_planificada * 100)
    : 0;

  return (
    <Box p={6}>
      {/* Header con navegación */}
      <Flex justify="space-between" align="center" mb={6} flexWrap="wrap" gap={4}>
        <HStack spacing={4}>
          <Button
            leftIcon={<ChevronLeftIcon />}
            variant="ghost"
            onClick={() => navigate('/app/produccion/ordenes')}
          >
            Volver
          </Button>
          <Box>
            <HStack>
              <Heading size="lg">Orden #{orden.numero || orden.id}</Heading>
              <Badge colorScheme={estadoConfig.colorScheme} fontSize="md" px={3} py={1}>
                {estadoConfig.icon} {estadoConfig.label}
              </Badge>
            </HStack>
            <Text color="gray.600" fontSize="sm">
              Creada el {formatDate(orden.fecha_creacion || orden.created_at)}
            </Text>
          </Box>
        </HStack>

        {/* Acciones */}
        <Menu>
          <MenuButton
            as={Button}
            rightIcon={<ChevronDownIcon />}
            colorScheme="blue"
          >
            Acciones
          </MenuButton>
          <MenuList>
            {(orden.estado === 'pendiente' || orden.estado === 'planificada') && (
              <MenuItem 
                icon={<Icon as={FiPlay} color="green.500" />}
                onClick={() => iniciarMutation.mutate()}
                isDisabled={iniciarMutation.isLoading}
              >
                {iniciarMutation.isLoading ? 'Iniciando...' : 'Iniciar Producción'}
              </MenuItem>
            )}
            {orden.estado === 'en_proceso' && (
              <>
                <MenuItem 
                  icon={<Icon as={FiActivity} />}
                  onClick={() => {
                    setCantidadActualizar(orden.cantidad_producida || 0);
                    onUpdateOpen();
                  }}
                >
                  Actualizar Progreso
                </MenuItem>
                <MenuItem 
                  icon={<CheckIcon color="green.500" />}
                  onClick={onCompleteOpen}
                >
                  Completar Orden
                </MenuItem>
                <MenuItem 
                  icon={<Icon as={FiPause} color="orange.500" />}
                >
                  Pausar
                </MenuItem>
              </>
            )}
            <Divider />
            <MenuItem icon={<EditIcon />}>Editar</MenuItem>
            <MenuItem icon={<CopyIcon />}>Duplicar</MenuItem>
            {orden.estado !== 'finalizada' && orden.estado !== 'completada' && orden.estado !== 'cancelada' && (
              <MenuItem 
                icon={<DeleteIcon color="red.500" />}
                onClick={onCancelOpen}
                color="red.500"
              >
                Cancelar
              </MenuItem>
            )}
          </MenuList>
        </Menu>
      </Flex>

      {/* Producto y Progreso Principal */}
      <Card bg={cardBg} borderWidth="2px" borderColor={`${estadoConfig.color}.200`} mb={6} borderRadius="xl" overflow="hidden">
        <Box h="4px" bgGradient={`linear(to-r, ${estadoConfig.color}.400, ${estadoConfig.color}.600)`} />
        <CardBody>
          <Flex direction={{ base: 'column', md: 'row' }} gap={6}>
            {/* Info Producto */}
            <Box flex={1}>
              <Text fontSize="sm" color="gray.500" mb={1}>Producto a fabricar</Text>
              <Heading size="md" mb={2}>{orden.producto_nombre || 'Producto'}</Heading>
              <Text color="gray.600" fontSize="sm">
                Receta: {orden.receta_nombre || '-'}
              </Text>
            </Box>

            {/* Progreso */}
            <Box flex={2}>
              <Flex justify="space-between" mb={2}>
                <Text fontWeight="semibold">Progreso de Producción</Text>
                <Text fontWeight="bold" color={`${estadoConfig.color}.600`}>
                  {orden.cantidad_producida || 0} / {orden.cantidad_planificada} unidades
                </Text>
              </Flex>
              <Progress 
                value={progreso} 
                colorScheme={progreso >= 100 ? 'green' : progreso > 0 ? 'yellow' : 'gray'} 
                borderRadius="full" 
                size="lg"
                mb={2}
              />
              <Flex justify="space-between" fontSize="sm" color="gray.500">
                <Text>Iniciado</Text>
                <Text fontWeight="bold" fontSize="md" color={`${estadoConfig.color}.600`}>{progreso}%</Text>
                <Text>Completado</Text>
              </Flex>
            </Box>
          </Flex>
        </CardBody>
      </Card>

      {/* Información en Grid */}
      <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4} mb={6}>
        <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl">
          <CardBody>
            <Stat>
              <HStack mb={2}>
                <Flex w="36px" h="36px" bg="blue.50" borderRadius="lg" align="center" justify="center">
                  <Icon as={FiCalendar} color="blue.500" />
                </Flex>
                <StatLabel>Fecha Programada</StatLabel>
              </HStack>
              <StatNumber fontSize="lg">{formatDateShort(orden.fecha_programada)}</StatNumber>
              <StatHelpText>{formatDate(orden.fecha_inicio)}</StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl">
          <CardBody>
            <Stat>
              <HStack mb={2}>
                <Flex w="36px" h="36px" bg="purple.50" borderRadius="lg" align="center" justify="center">
                  <Icon as={FiUser} color="purple.500" />
                </Flex>
                <StatLabel>Responsable</StatLabel>
              </HStack>
              <StatNumber fontSize="lg">{orden.responsable_nombre || '-'}</StatNumber>
              <StatHelpText>asignado</StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl">
          <CardBody>
            <Stat>
              <HStack mb={2}>
                <Flex w="36px" h="36px" bg="orange.50" borderRadius="lg" align="center" justify="center">
                  <Icon as={FiClock} color="orange.500" />
                </Flex>
                <StatLabel>Tiempo</StatLabel>
              </HStack>
              <StatNumber fontSize="lg">
                {orden.tiempo_real ? `${(orden.tiempo_real / 60).toFixed(1)}h` : '-'} / {orden.tiempo_estimado ? `${(orden.tiempo_estimado / 60).toFixed(1)}h` : `${((orden.receta_info?.tiempo_estimado || 0) * (orden.cantidad_planificada || 1) / 60).toFixed(1)}h`}
              </StatNumber>
              <StatHelpText>real / estimado</StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl">
          <CardBody>
            <Stat>
              <HStack mb={2}>
                <Flex w="36px" h="36px" bg="green.50" borderRadius="lg" align="center" justify="center">
                  <Icon as={FiDollarSign} color="green.500" />
                </Flex>
                <StatLabel>Costo</StatLabel>
              </HStack>
              <StatNumber fontSize="lg" color="green.600">
                {formatCurrency(orden.costos_reales?.costo_total || orden.costo_estimado || (orden.receta_info?.costos?.costo_total || 0) * (orden.cantidad_planificada || 1))}
              </StatNumber>
              <StatHelpText>{orden.costos_reales ? 'real' : 'estimado'}</StatHelpText>
            </Stat>
          </CardBody>
        </Card>
      </SimpleGrid>

      <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
        {/* Materiales */}
        <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl">
          <CardHeader pb={2}>
            <HStack>
              <Icon as={FiBox} color="blue.500" />
              <Heading size="md">Materiales Utilizados</Heading>
            </HStack>
          </CardHeader>
          <CardBody pt={0}>
            {orden.detalles && orden.detalles.length > 0 ? (
              <VStack spacing={3} align="stretch">
                {orden.detalles.map((detalle, index) => {
                  const materiaPrima = detalle.materia_prima_nombre || `Material ${index + 1}`;
                  const requerido = detalle.cantidad_requerida || detalle.cantidad || 0;
                  const usado = detalle.cantidad_usada || 0;
                  const progresoMaterial = requerido > 0 ? Math.round((usado / requerido) * 100) : 0;
                  const stockDisponible = detalle.stock_disponible || 0;
                  const stockSuficiente = stockDisponible >= requerido;
                  
                  return (
                    <Box key={index} p={3} bg="gray.50" borderRadius="lg">
                      <Flex justify="space-between" mb={1}>
                        <HStack>
                          <Text fontWeight="medium">{materiaPrima}</Text>
                          {!stockSuficiente && (
                            <Badge colorScheme="red" fontSize="xs">Stock insuficiente</Badge>
                          )}
                        </HStack>
                        <Text fontSize="sm" color="gray.600">
                          {usado.toFixed(2)} / {requerido.toFixed(2)} {detalle.unidad || 'und'}
                        </Text>
                      </Flex>
                      <Text fontSize="xs" color="gray.500" mb={2}>
                        Stock disponible: {stockDisponible.toFixed(2)} {detalle.unidad || 'und'}
                      </Text>
                      <Progress 
                        value={progresoMaterial} 
                        colorScheme={progresoMaterial >= 100 ? 'green' : 'blue'} 
                        borderRadius="full" 
                        size="sm" 
                      />
                    </Box>
                  );
                })}
              </VStack>
            ) : orden.receta_info?.detalles && orden.receta_info.detalles.length > 0 ? (
              <VStack spacing={3} align="stretch">
                {orden.receta_info.detalles.map((detalle, index) => {
                  const requerido = (detalle.cantidad || 0) * (orden.cantidad_planificada || 1);
                  const stockDisponible = detalle.insumo_stock || 0;
                  
                  return (
                    <Box key={index} p={3} bg="gray.50" borderRadius="lg">
                      <Flex justify="space-between" mb={1}>
                        <Text fontWeight="medium">{detalle.insumo_nombre}</Text>
                        <Text fontSize="sm" color="gray.600">
                          {requerido.toFixed(2)} {detalle.unidad_medida || 'und'}
                        </Text>
                      </Flex>
                      <Text fontSize="xs" color="gray.500">
                        Stock: {stockDisponible.toFixed(2)} | Costo unit: S/ {detalle.costo_unitario || 0}
                      </Text>
                    </Box>
                  );
                })}
              </VStack>
            ) : (
              <Box textAlign="center" py={8}>
                <Icon as={FiPackage} boxSize={8} color="gray.400" mb={2} />
                <Text color="gray.500">No hay materiales registrados</Text>
              </Box>
            )}
          </CardBody>
        </Card>

        {/* Historial */}
        <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl">
          <CardHeader pb={2}>
            <HStack>
              <Icon as={FiActivity} color="purple.500" />
              <Heading size="md">Historial de Actividad</Heading>
            </HStack>
          </CardHeader>
          <CardBody pt={0}>
            {orden.historial && orden.historial.length > 0 ? (
              <VStack spacing={3} align="stretch">
                {orden.historial.map((evento, index) => (
                  <HStack key={index} p={3} bg="gray.50" borderRadius="lg" spacing={3}>
                    <Box w="8px" h="8px" borderRadius="full" bg="blue.400" />
                    <Box flex={1}>
                      <Text fontWeight="medium" fontSize="sm">{evento.descripcion || evento.accion}</Text>
                      <Text fontSize="xs" color="gray.500">
                        {formatDate(evento.fecha)} {evento.usuario && `- ${evento.usuario}`}
                      </Text>
                    </Box>
                  </HStack>
                ))}
              </VStack>
            ) : (
              <VStack spacing={3} align="stretch">
                {/* Eventos por defecto basados en el estado */}
                <HStack p={3} bg="gray.50" borderRadius="lg" spacing={3}>
                  <Box w="8px" h="8px" borderRadius="full" bg="blue.400" />
                  <Box flex={1}>
                    <Text fontWeight="medium" fontSize="sm">Orden creada</Text>
                    <Text fontSize="xs" color="gray.500">{formatDate(orden.fecha_creacion || orden.created_at)}</Text>
                  </Box>
                </HStack>
                {orden.fecha_inicio && (
                  <HStack p={3} bg="gray.50" borderRadius="lg" spacing={3}>
                    <Box w="8px" h="8px" borderRadius="full" bg="yellow.400" />
                    <Box flex={1}>
                      <Text fontWeight="medium" fontSize="sm">Producción iniciada</Text>
                      <Text fontSize="xs" color="gray.500">{formatDate(orden.fecha_inicio)}</Text>
                    </Box>
                  </HStack>
                )}
                {orden.estado === 'completada' && orden.fecha_fin && (
                  <HStack p={3} bg="green.50" borderRadius="lg" spacing={3}>
                    <Box w="8px" h="8px" borderRadius="full" bg="green.400" />
                    <Box flex={1}>
                      <Text fontWeight="medium" fontSize="sm">Orden completada</Text>
                      <Text fontSize="xs" color="gray.500">{formatDate(orden.fecha_fin)}</Text>
                    </Box>
                  </HStack>
                )}
              </VStack>
            )}
          </CardBody>
        </Card>
      </SimpleGrid>

      {/* Notas */}
      {orden.notas && (
        <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl" mt={6}>
          <CardHeader pb={2}>
            <Heading size="md">Notas</Heading>
          </CardHeader>
          <CardBody pt={0}>
            <Text color="gray.600">{orden.notas}</Text>
          </CardBody>
        </Card>
      )}

      {/* Modal Actualizar Progreso */}
      <Modal isOpen={isUpdateOpen} onClose={onUpdateClose} isCentered>
        <ModalOverlay />
        <ModalContent borderRadius="xl">
          <ModalHeader>Actualizar Progreso</ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            <FormControl>
              <FormLabel>Cantidad Producida</FormLabel>
              <Input
                type="number"
                value={cantidadActualizar}
                onChange={(e) => setCantidadActualizar(Number(e.target.value))}
                max={orden.cantidad_planificada}
              />
              <Text fontSize="sm" color="gray.500" mt={2}>
                Máximo: {orden.cantidad_planificada} unidades
              </Text>
            </FormControl>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onUpdateClose}>Cancelar</Button>
            <Button
              colorScheme="blue"
              onClick={() => actualizarProgresoMutation.mutate(cantidadActualizar)}
              isLoading={actualizarProgresoMutation.isLoading}
            >
              Actualizar
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Modal Completar */}
      <Modal isOpen={isCompleteOpen} onClose={onCompleteClose} isCentered>
        <ModalOverlay />
        <ModalContent borderRadius="xl">
          <ModalHeader>Completar Orden</ModalHeader>
          <ModalCloseButton />
          <ModalBody textAlign="center" py={6}>
            <Icon as={CheckIcon} boxSize={12} color="green.400" mb={4} />
            <Text mb={2}>¿Confirmar que la producción ha finalizado?</Text>
            <Text fontWeight="bold" fontSize="lg">
              {orden.cantidad_producida || 0} / {orden.cantidad_planificada} unidades producidas
            </Text>
            {(orden.cantidad_producida || 0) < orden.cantidad_planificada && (
              <Alert status="warning" mt={4} borderRadius="md">
                <AlertIcon />
                <Text fontSize="sm">La producción no alcanzó la cantidad planificada</Text>
              </Alert>
            )}
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onCompleteClose}>Cancelar</Button>
            <Button
              colorScheme="green"
              onClick={() => completarMutation.mutate(orden.cantidad_producida || orden.cantidad_planificada)}
              isLoading={completarMutation.isLoading}
            >
              Completar Orden
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Modal Cancelar */}
      <Modal isOpen={isCancelOpen} onClose={onCancelClose} isCentered>
        <ModalOverlay />
        <ModalContent borderRadius="xl">
          <ModalHeader>Cancelar Orden</ModalHeader>
          <ModalCloseButton />
          <ModalBody textAlign="center" py={6}>
            <Icon as={WarningIcon} boxSize={12} color="orange.400" mb={4} />
            <Text mb={2}>¿Estás seguro de cancelar esta orden?</Text>
            <Text fontWeight="bold">{orden.producto_nombre}</Text>
            <Text fontSize="sm" color="gray.500">Esta acción no se puede deshacer</Text>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onCancelClose}>No, mantener</Button>
            <Button
              colorScheme="red"
              onClick={() => cancelarMutation.mutate()}
              isLoading={cancelarMutation.isLoading}
            >
              Sí, cancelar
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default OrdenDetalle;
