import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { produccionService } from '../../services/produccion.service';
import QuickCreateOrden from './QuickCreateOrden';
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
  Icon,
  Input,
  InputGroup,
  InputLeftElement,
  Select,
  useColorModeValue,
  Spinner,
  IconButton,
  Tabs,
  TabList,
  Tab,
  TabPanels,
  TabPanel,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  useDisclosure,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Tooltip
} from '@chakra-ui/react';
import { 
  SearchIcon, 
  AddIcon, 
  ChevronRightIcon,
  RepeatIcon,
  ViewIcon,
  TimeIcon,
  WarningIcon,
  CheckCircleIcon,
  ChevronDownIcon,
  EditIcon,
  CopyIcon,
  DeleteIcon
} from '@chakra-ui/icons';
import { FiPackage, FiBox, FiClock, FiCheckCircle, FiTarget, FiDollarSign, FiCalendar, FiUser, FiList, FiGrid } from 'react-icons/fi';

const OrdenProduccionList = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  
  const [showQuickCreate, setShowQuickCreate] = useState(false);
  const [busqueda, setBusqueda] = useState('');
  const [filtroEstado, setFiltroEstado] = useState('');
  const [vistaActiva, setVistaActiva] = useState('grid'); // 'grid' o 'timeline'
  const [ordenToCancel, setOrdenToCancel] = useState(null);
  const { isOpen: isCancelOpen, onOpen: onCancelOpen, onClose: onCancelClose } = useDisclosure();

  // Query para órdenes
  const { data: ordenes = [], isLoading, error, refetch } = useQuery({
    queryKey: ['ordenes-produccion'],
    queryFn: async () => {
      const response = await produccionService.getOrdenes();
      const data = response.data;
      return Array.isArray(data) ? data : data?.results || [];
    }
  });

  // Mutation para cancelar
  const cancelMutation = useMutation({
    mutationFn: (id) => produccionService.cancelarOrden(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['ordenes-produccion']);
      onCancelClose();
      setOrdenToCancel(null);
    }
  });

  // Mutation para iniciar
  const iniciarMutation = useMutation({
    mutationFn: (id) => produccionService.iniciarOrden(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['ordenes-produccion']);
    }
  });

  // Filtrar órdenes
  const ordenesFiltradas = ordenes.filter(orden => {
    if (busqueda) {
      const search = busqueda.toLowerCase();
      if (!orden.numero?.toLowerCase().includes(search) &&
          !orden.producto_nombre?.toLowerCase().includes(search) &&
          !orden.receta_nombre?.toLowerCase().includes(search)) {
        return false;
      }
    }
    if (filtroEstado && orden.estado !== filtroEstado) return false;
    return true;
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
      year: '2-digit'
    });
  };

  const calcularProgreso = (orden) => {
    if (!orden.cantidad_planificada) return 0;
    return Math.round((orden.cantidad_producida || 0) / orden.cantidad_planificada * 100);
  };

  const handleCancelClick = (orden) => {
    setOrdenToCancel(orden);
    onCancelOpen();
  };

  // Stats
  const stats = {
    total: ordenes.length,
    enProceso: ordenes.filter(o => o.estado === 'en_proceso').length,
    completadas: ordenes.filter(o => o.estado === 'finalizada' || o.estado === 'completada').length,
    pendientes: ordenes.filter(o => o.estado === 'pendiente' || o.estado === 'planificada').length
  };

  if (isLoading) {
    return (
      <Box p={6}>
        <Flex justify="center" align="center" h="300px" direction="column">
          <Spinner size="xl" color="blue.500" thickness="4px" mb={4} />
          <Text color="gray.600">Cargando órdenes...</Text>
        </Flex>
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={6}>
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          No se pudieron cargar las órdenes de producción
        </Alert>
      </Box>
    );
  }

  return (
    <Box p={6}>
      {/* Header */}
      <Flex justify="space-between" align="center" mb={6} flexWrap="wrap" gap={4}>
        <Box>
          <Heading size="lg" bgGradient="linear(to-r, blue.600, purple.600)" bgClip="text">
            Órdenes de Producción
          </Heading>
          <Text color="gray.600" mt={1}>
            Gestiona y monitorea el avance de producción
          </Text>
        </Box>
        <HStack spacing={3}>
          <Button
            leftIcon={<RepeatIcon />}
            variant="outline"
            onClick={() => refetch()}
          >
            Actualizar
          </Button>
          <Button
            leftIcon={<AddIcon />}
            colorScheme="blue"
            onClick={() => setShowQuickCreate(true)}
          >
            Nueva Orden
          </Button>
        </HStack>
      </Flex>

      {/* Stats Cards */}
      <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4} mb={6}>
        <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl">
          <CardBody>
            <Stat>
              <StatLabel color="gray.500">Total</StatLabel>
              <StatNumber color="blue.600">{stats.total}</StatNumber>
              <StatHelpText>órdenes</StatHelpText>
            </Stat>
          </CardBody>
        </Card>
        <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl">
          <CardBody>
            <Stat>
              <StatLabel color="gray.500">En Proceso</StatLabel>
              <StatNumber color="yellow.500">{stats.enProceso}</StatNumber>
              <StatHelpText>activas</StatHelpText>
            </Stat>
          </CardBody>
        </Card>
        <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl">
          <CardBody>
            <Stat>
              <StatLabel color="gray.500">Completadas</StatLabel>
              <StatNumber color="green.500">{stats.completadas}</StatNumber>
              <StatHelpText>finalizadas</StatHelpText>
            </Stat>
          </CardBody>
        </Card>
        <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl">
          <CardBody>
            <Stat>
              <StatLabel color="gray.500">Pendientes</StatLabel>
              <StatNumber color="gray.500">{stats.pendientes}</StatNumber>
              <StatHelpText>por iniciar</StatHelpText>
            </Stat>
          </CardBody>
        </Card>
      </SimpleGrid>

      {/* Filtros y Vista */}
      <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} mb={6} borderRadius="xl">
        <CardBody>
          <Flex justify="space-between" align="center" flexWrap="wrap" gap={4}>
            <HStack spacing={4} flex={1}>
              <InputGroup maxW="400px">
                <InputLeftElement pointerEvents="none">
                  <SearchIcon color="gray.400" />
                </InputLeftElement>
                <Input
                  placeholder="Buscar por número, producto..."
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                />
              </InputGroup>
              <Select 
                w="200px"
                value={filtroEstado}
                onChange={(e) => setFiltroEstado(e.target.value)}
              >
                <option value="">Todos los estados</option>
                <option value="pendiente">⚪ Pendiente</option>
                <option value="en_proceso">🟡 En Proceso</option>
                <option value="finalizada">🟢 Finalizada</option>
                <option value="cancelada">🔴 Cancelada</option>
              </Select>
            </HStack>
            <HStack>
              <Tooltip label="Vista en grilla">
                <IconButton
                  icon={<Icon as={FiGrid} />}
                  variant={vistaActiva === 'grid' ? 'solid' : 'ghost'}
                  colorScheme={vistaActiva === 'grid' ? 'blue' : 'gray'}
                  onClick={() => setVistaActiva('grid')}
                  aria-label="Vista grid"
                />
              </Tooltip>
              <Tooltip label="Vista timeline">
                <IconButton
                  icon={<Icon as={FiList} />}
                  variant={vistaActiva === 'timeline' ? 'solid' : 'ghost'}
                  colorScheme={vistaActiva === 'timeline' ? 'blue' : 'gray'}
                  onClick={() => setVistaActiva('timeline')}
                  aria-label="Vista timeline"
                />
              </Tooltip>
            </HStack>
          </Flex>
        </CardBody>
      </Card>

      {/* Lista de órdenes */}
      {ordenesFiltradas.length === 0 ? (
        <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl">
          <CardBody>
            <VStack py={12} spacing={4}>
              <Icon as={FiBox} boxSize={12} color="gray.400" />
              <Text fontSize="lg" fontWeight="medium" color="gray.600">
                {busqueda || filtroEstado ? "No se encontraron órdenes" : "No hay órdenes de producción"}
              </Text>
              <Text color="gray.500" textAlign="center">
                {busqueda || filtroEstado 
                  ? "Intenta con otros filtros"
                  : "Crea tu primera orden de producción"
                }
              </Text>
              {!busqueda && !filtroEstado && (
                <Button leftIcon={<AddIcon />} colorScheme="blue" onClick={() => setShowQuickCreate(true)}>
                  Nueva Orden
                </Button>
              )}
            </VStack>
          </CardBody>
        </Card>
      ) : vistaActiva === 'grid' ? (
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
          {ordenesFiltradas.map((orden) => {
            const estadoConfig = getEstadoConfig(orden.estado);
            const progreso = calcularProgreso(orden);
            
            return (
              <Card 
                key={orden.id}
                bg={cardBg} 
                borderWidth="2px" 
                borderColor={orden.estado === 'en_proceso' ? 'yellow.300' : borderColor}
                borderRadius="xl"
                overflow="hidden"
                transition="all 0.3s"
                _hover={{ shadow: 'lg', transform: 'translateY(-4px)' }}
              >
                {/* Barra de color según estado */}
                <Box 
                  h="4px" 
                  bgGradient={`linear(to-r, ${estadoConfig.color}.400, ${estadoConfig.color}.600)`} 
                />
                
                <CardHeader pb={2}>
                  <Flex justify="space-between" align="start">
                    <Box flex={1} mr={2}>
                      <HStack mb={1}>
                        <Text fontWeight="bold" fontSize="sm" color="gray.500">
                          #{orden.numero || orden.id}
                        </Text>
                      </HStack>
                      <Text fontWeight="bold" fontSize="md" noOfLines={1}>
                        {orden.producto_nombre || 'Producto'}
                      </Text>
                    </Box>
                    <Badge colorScheme={estadoConfig.colorScheme} fontSize="xs">
                      {estadoConfig.icon} {estadoConfig.label}
                    </Badge>
                  </Flex>
                </CardHeader>

                <CardBody pt={0}>
                  {/* Progreso */}
                  <Box mb={4}>
                    <Flex justify="space-between" fontSize="sm" mb={1}>
                      <Text color="gray.600">Progreso</Text>
                      <Text fontWeight="medium">{orden.cantidad_producida || 0} / {orden.cantidad_planificada} und</Text>
                    </Flex>
                    <Progress 
                      value={progreso} 
                      colorScheme={progreso >= 100 ? 'green' : progreso > 0 ? 'yellow' : 'gray'} 
                      borderRadius="full" 
                      size="sm" 
                    />
                    <Text fontSize="xs" color="gray.500" textAlign="right" mt={1}>{progreso}%</Text>
                  </Box>

                  {/* Info */}
                  <VStack spacing={2} align="stretch" fontSize="sm">
                    <Flex justify="space-between" color="gray.600">
                      <HStack><Icon as={FiCalendar} /><Text>Fecha:</Text></HStack>
                      <Text fontWeight="medium">{formatDate(orden.fecha_programada || orden.fecha_inicio)}</Text>
                    </Flex>
                    {orden.responsable_nombre && (
                      <Flex justify="space-between" color="gray.600">
                        <HStack><Icon as={FiUser} /><Text>Responsable:</Text></HStack>
                        <Text fontWeight="medium" noOfLines={1}>{orden.responsable_nombre}</Text>
                      </Flex>
                    )}
                    {orden.costo_estimado > 0 && (
                      <Flex justify="space-between" color="gray.600">
                        <HStack><Icon as={FiDollarSign} /><Text>Costo:</Text></HStack>
                        <Text fontWeight="medium" color="green.600">{formatCurrency(orden.costo_estimado)}</Text>
                      </Flex>
                    )}
                  </VStack>

                  {/* Acciones */}
                  <Flex justify="space-between" align="center" mt={4} pt={4} borderTopWidth="1px">
                    <Button
                      size="sm"
                      variant="ghost"
                      colorScheme="blue"
                      rightIcon={<ChevronRightIcon />}
                      onClick={() => navigate(`/app/produccion/ordenes/${orden.id}`)}
                    >
                      Ver detalle
                    </Button>
                    
                    <Menu>
                      <MenuButton
                        as={IconButton}
                        icon={<ChevronDownIcon />}
                        variant="ghost"
                        size="sm"
                        aria-label="Acciones"
                      />
                      <MenuList>
                        {(orden.estado === 'pendiente' || orden.estado === 'planificada') && (
                          <MenuItem 
                            icon={<Icon as={FiCheckCircle} color="green.500" />}
                            onClick={() => iniciarMutation.mutate(orden.id)}
                          >
                            Iniciar producción
                          </MenuItem>
                        )}
                        <MenuItem 
                          icon={<ViewIcon />}
                          onClick={() => navigate(`/app/produccion/ordenes/${orden.id}`)}
                        >
                          Ver detalle
                        </MenuItem>
                        <MenuItem 
                          icon={<CopyIcon />}
                          onClick={() => {/* duplicar */}}
                        >
                          Duplicar
                        </MenuItem>
                        {orden.estado !== 'finalizada' && orden.estado !== 'completada' && orden.estado !== 'cancelada' && (
                          <MenuItem 
                            icon={<DeleteIcon color="red.500" />}
                            onClick={() => handleCancelClick(orden)}
                            color="red.500"
                          >
                            Cancelar
                          </MenuItem>
                        )}
                      </MenuList>
                    </Menu>
                  </Flex>
                </CardBody>
              </Card>
            );
          })}
        </SimpleGrid>
      ) : (
        // Vista Timeline
        <VStack spacing={4} align="stretch">
          {ordenesFiltradas.map((orden) => {
            const estadoConfig = getEstadoConfig(orden.estado);
            const progreso = calcularProgreso(orden);
            
            return (
              <Card 
                key={orden.id}
                bg={cardBg} 
                borderWidth="1px" 
                borderColor={borderColor}
                borderRadius="xl"
                overflow="hidden"
                borderLeftWidth="4px"
                borderLeftColor={`${estadoConfig.color}.500`}
              >
                <CardBody>
                  <Flex justify="space-between" align="center" flexWrap="wrap" gap={4}>
                    <HStack spacing={4}>
                      <Box textAlign="center" minW="60px">
                        <Text fontSize="xs" color="gray.500">{formatDate(orden.fecha_programada)}</Text>
                        <Text fontWeight="bold" fontSize="sm" color={`${estadoConfig.color}.600`}>
                          #{orden.numero || orden.id}
                        </Text>
                      </Box>
                      <Box>
                        <Text fontWeight="bold">{orden.producto_nombre}</Text>
                        <Text fontSize="sm" color="gray.500">{orden.receta_nombre}</Text>
                      </Box>
                    </HStack>

                    <HStack spacing={6}>
                      <Box minW="120px">
                        <Progress 
                          value={progreso} 
                          colorScheme={progreso >= 100 ? 'green' : progreso > 0 ? 'yellow' : 'gray'} 
                          borderRadius="full" 
                          size="sm" 
                        />
                        <Text fontSize="xs" color="gray.500" mt={1}>
                          {orden.cantidad_producida || 0}/{orden.cantidad_planificada} und ({progreso}%)
                        </Text>
                      </Box>
                      <Badge colorScheme={estadoConfig.colorScheme} fontSize="sm">
                        {estadoConfig.icon} {estadoConfig.label}
                      </Badge>
                      <Button
                        size="sm"
                        colorScheme="blue"
                        variant="outline"
                        rightIcon={<ChevronRightIcon />}
                        onClick={() => navigate(`/app/produccion/ordenes/${orden.id}`)}
                      >
                        Ver
                      </Button>
                    </HStack>
                  </Flex>
                </CardBody>
              </Card>
            );
          })}
        </VStack>
      )}

      {/* Quick Create Modal */}
      <QuickCreateOrden
        isOpen={showQuickCreate}
        onClose={() => setShowQuickCreate(false)}
      />

      {/* Modal de cancelación */}
      <Modal isOpen={isCancelOpen} onClose={onCancelClose} isCentered>
        <ModalOverlay />
        <ModalContent borderRadius="xl">
          <ModalHeader>Cancelar Orden</ModalHeader>
          <ModalCloseButton />
          <ModalBody textAlign="center" py={6}>
            <Icon as={WarningIcon} boxSize={12} color="orange.400" mb={4} />
            <Text color="gray.600" mb={2}>
              ¿Estás seguro de cancelar esta orden?
            </Text>
            <Text fontWeight="bold" fontSize="lg">
              {ordenToCancel?.numero || `#${ordenToCancel?.id}`} - {ordenToCancel?.producto_nombre}
            </Text>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onCancelClose}>
              No, mantener
            </Button>
            <Button
              colorScheme="red"
              onClick={() => cancelMutation.mutate(ordenToCancel?.id)}
              isLoading={cancelMutation.isLoading}
            >
              Sí, cancelar
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default OrdenProduccionList;
