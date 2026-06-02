import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
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
  Input,
  InputGroup,
  InputLeftElement,
  Select,
  useColorModeValue,
  Spinner,
  Divider
} from '@chakra-ui/react';
import { keyframes } from '@emotion/react';
import { 
  RepeatIcon, 
  AddIcon, 
  ChevronRightIcon, 
  SearchIcon,
  WarningIcon 
} from '@chakra-ui/icons';
import { FiPackage, FiBox, FiClipboard, FiTool, FiClock, FiCheckCircle } from 'react-icons/fi';
import QuickCreateOrden from './QuickCreateOrden';

// Animación de pulso
const pulseAnimation = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
`;

const DashboardProduccion = () => {
  const navigate = useNavigate();
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [filtroEstado, setFiltroEstado] = useState('');
  const [busqueda, setBusqueda] = useState('');

  // Query para métricas del dashboard
  const { data: metricas, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['dashboard-produccion'],
    queryFn: async () => {
      const fechaHasta = new Date();
      const fechaDesde = new Date();
      fechaDesde.setDate(fechaDesde.getDate() - 7);

      const params = {
        fecha_desde: fechaDesde.toISOString().split('T')[0],
        fecha_hasta: fechaHasta.toISOString().split('T')[0]
      };

      const response = await produccionService.getDashboard(params);
      return response.data || response;
    },
    refetchInterval: 30000,
    refetchOnWindowFocus: true
  });

  // Query para órdenes recientes
  const { data: ordenesRecientes = [] } = useQuery({
    queryKey: ['ordenes-recientes', filtroEstado],
    queryFn: async () => {
      const params = filtroEstado ? { estado: filtroEstado } : {};
      const response = await produccionService.getOrdenes(params);
      const data = response.data;
      return Array.isArray(data) ? data : data?.results || [];
    }
  });

  // Filtrar órdenes
  const ordenesFiltradas = ordenesRecientes.filter(orden => {
    if (!busqueda) return true;
    const search = busqueda.toLowerCase();
    return (
      orden.numero?.toString().includes(search) ||
      orden.producto_nombre?.toLowerCase().includes(search)
    );
  }).slice(0, 10);

  // Calcular métricas
  const metricasOperativas = metricas?.metricas_operativas || {};
  const ordenesHoy = metricas?.ordenes_hoy || [];
  const ordenesActivas = metricasOperativas.ordenes_activas || {};
  const produccion = metricasOperativas.produccion || {};
  const mermas = metricasOperativas.mermas || {};
  const cumplimiento = metricasOperativas.cumplimiento || {};
  const costos = metricasOperativas.costos || {};

  // Alertas
  const alertas = [];
  if (ordenesActivas.retrasadas > 0) {
    alertas.push({
      tipo: 'error',
      titulo: `${ordenesActivas.retrasadas} órdenes retrasadas`
    });
  }
  if (mermas.porcentaje_merma > 10) {
    alertas.push({
      tipo: 'warning',
      titulo: `Merma elevada: ${mermas.porcentaje_merma?.toFixed(1)}%`
    });
  }

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('es-PE', {
      style: 'currency',
      currency: 'PEN',
      minimumFractionDigits: 2
    }).format(amount || 0);
  };

  const getStatusColor = (estado) => {
    switch (estado) {
      case 'pendiente': return 'yellow';
      case 'en_proceso': return 'blue';
      case 'finalizada': return 'green';
      case 'cancelada': return 'red';
      default: return 'gray';
    }
  };

  if (isLoading) {
    return (
      <Box p={6}>
        <Flex justify="center" align="center" h="300px" direction="column">
          <Spinner size="xl" color="blue.500" thickness="4px" mb={4} />
          <Text color="gray.600">Cargando dashboard de producción...</Text>
        </Flex>
      </Box>
    );
  }

  return (
    <Box p={6}>
      {/* Header */}
      <Flex justify="space-between" align="center" mb={6} flexWrap="wrap" gap={4}>
        <Box>
          <Heading size="lg" bgGradient="linear(to-r, purple.600, blue.600)" bgClip="text">
            Dashboard de Producción
          </Heading>
          <Text color="gray.600" mt={1}>
            Vista en tiempo real de tu planta de producción
          </Text>
        </Box>
        <HStack spacing={3}>
          <Button
            leftIcon={<RepeatIcon />}
            onClick={() => refetch()}
            variant="outline"
            colorScheme="blue"
            isLoading={isFetching}
            loadingText="Actualizando"
          >
            Actualizar
          </Button>
          <Button
            leftIcon={<AddIcon />}
            colorScheme="blue"
            onClick={() => setShowCreateModal(true)}
          >
            Nueva Orden
          </Button>
        </HStack>
      </Flex>

      {/* Alertas */}
      {alertas.length > 0 && (
        <Alert 
          status="warning" 
          mb={6} 
          borderRadius="xl"
          animation={`${pulseAnimation} 3s ease-in-out infinite`}
        >
          <AlertIcon />
          <Box flex="1">
            <AlertTitle>Se requiere atención</AlertTitle>
            <AlertDescription>
              {alertas.map(a => a.titulo).join(' • ')}
            </AlertDescription>
          </Box>
          <Button 
            size="sm" 
            colorScheme="orange"
            onClick={() => navigate('/app/produccion/ordenes?retrasadas=true')}
          >
            Ver Detalles
          </Button>
        </Alert>
      )}

      {/* Cards Principales */}
      <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6} mb={6}>
        {/* Card En Proceso */}
        <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} shadow="md" borderRadius="xl" overflow="hidden">
          <Box h="4px" bgGradient="linear(to-r, blue.400, blue.600)" />
          <CardHeader pb={2}>
            <Flex justify="space-between" align="center">
              <HStack spacing={3}>
                <Flex w="40px" h="40px" bg="blue.50" borderRadius="lg" align="center" justify="center">
                  <Icon as={FiClock} boxSize={5} color="blue.500" />
                </Flex>
                <Heading size="md" color="gray.700">En Proceso</Heading>
              </HStack>
              <Button 
                size="sm" 
                rightIcon={<ChevronRightIcon />}
                variant="ghost"
                colorScheme="blue"
                onClick={() => navigate('/app/produccion/ordenes?estado=en_proceso')}
              >
                Ver Todo
              </Button>
            </Flex>
          </CardHeader>
          <CardBody>
            <SimpleGrid columns={2} spacing={4}>
              <Stat>
                <StatLabel>Órdenes Activas</StatLabel>
                <StatNumber color="blue.600">{ordenesActivas.en_proceso || 0}</StatNumber>
              </Stat>
              <Stat>
                <StatLabel>Unidades en Proceso</StatLabel>
                <StatNumber color="blue.600">{produccion.total_planificado?.toFixed(0) || 0}</StatNumber>
              </Stat>
              <Stat>
                <StatLabel>Progreso Promedio</StatLabel>
                <StatNumber>{cumplimiento.porcentaje_cumplimiento?.toFixed(0) || 0}%</StatNumber>
              </Stat>
              <Stat>
                <StatLabel>Retrasadas</StatLabel>
                <StatNumber color={ordenesActivas.retrasadas > 0 ? 'red.500' : 'green.500'}>
                  {ordenesActivas.retrasadas || 0}
                </StatNumber>
              </Stat>
            </SimpleGrid>
          </CardBody>
        </Card>

        {/* Card Completadas */}
        <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} shadow="md" borderRadius="xl" overflow="hidden">
          <Box h="4px" bgGradient="linear(to-r, green.400, green.600)" />
          <CardHeader pb={2}>
            <Flex justify="space-between" align="center">
              <HStack spacing={3}>
                <Flex w="40px" h="40px" bg="green.50" borderRadius="lg" align="center" justify="center">
                  <Icon as={FiCheckCircle} boxSize={5} color="green.500" />
                </Flex>
                <Heading size="md" color="gray.700">Completadas (7 días)</Heading>
              </HStack>
              <Button 
                size="sm" 
                rightIcon={<ChevronRightIcon />}
                variant="ghost"
                colorScheme="green"
                onClick={() => navigate('/app/produccion/ordenes?estado=finalizada')}
              >
                Ver Todo
              </Button>
            </Flex>
          </CardHeader>
          <CardBody>
            <SimpleGrid columns={2} spacing={4}>
              <Stat>
                <StatLabel>Total Órdenes</StatLabel>
                <StatNumber color="green.600">{cumplimiento.ordenes_finalizadas || 0}</StatNumber>
              </Stat>
              <Stat>
                <StatLabel>Unidades Producidas</StatLabel>
                <StatNumber color="green.600">{produccion.total_producido?.toFixed(0) || 0}</StatNumber>
              </Stat>
              <Stat>
                <StatLabel>A Tiempo</StatLabel>
                <StatNumber color="green.600">{cumplimiento.ordenes_a_tiempo || 0}</StatNumber>
              </Stat>
              <Stat>
                <StatLabel>Cumplimiento</StatLabel>
                <StatNumber>{cumplimiento.porcentaje_cumplimiento?.toFixed(0) || 0}%</StatNumber>
              </Stat>
            </SimpleGrid>
          </CardBody>
        </Card>
      </SimpleGrid>

      {/* Resumen Consolidado */}
      <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} shadow="md" mb={6} borderRadius="xl" overflow="hidden">
        <Box h="4px" bgGradient="linear(to-r, purple.400, purple.600)" />
        <CardHeader>
          <Heading size="md" color="gray.700">Resumen Consolidado</Heading>
        </CardHeader>
        <CardBody>
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
            <Stat textAlign="center" p={4} bg="blue.50" borderRadius="xl">
              <StatLabel fontSize="xs" color="gray.600">Costo Producción</StatLabel>
              <StatNumber fontSize="xl" color="blue.600">
                {formatCurrency(costos.total_costo_produccion || 0)}
              </StatNumber>
              <StatHelpText fontSize="xs">Últimos 7 días</StatHelpText>
            </Stat>
            
            <Stat textAlign="center" p={4} bg="green.50" borderRadius="xl">
              <StatLabel fontSize="xs" color="gray.600">Valor Producido</StatLabel>
              <StatNumber fontSize="xl" color="green.600">
                {formatCurrency((produccion.total_producido || 0) * (costos.costo_promedio || 0))}
              </StatNumber>
              <StatHelpText fontSize="xs">Valor estimado</StatHelpText>
            </Stat>
            
            <Stat textAlign="center" p={4} bg="orange.50" borderRadius="xl">
              <StatLabel fontSize="xs" color="gray.600">Merma</StatLabel>
              <StatNumber fontSize="xl" color={mermas.porcentaje_merma > 10 ? 'red.600' : 'orange.600'}>
                {mermas.porcentaje_merma?.toFixed(1) || 0}%
              </StatNumber>
              <StatHelpText fontSize="xs">Porcentaje desperdicio</StatHelpText>
            </Stat>
            
            <Stat textAlign="center" p={4} bg="purple.50" borderRadius="xl">
              <StatLabel fontSize="xs" color="gray.600">Pendientes</StatLabel>
              <StatNumber fontSize="xl" color="purple.600">
                {ordenesActivas.pendientes || 0}
              </StatNumber>
              <StatHelpText fontSize="xs">Por iniciar</StatHelpText>
            </Stat>
          </SimpleGrid>
        </CardBody>
      </Card>

      {/* Producción: Plan vs Real */}
      <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} shadow="md" mb={6} borderRadius="xl">
        <CardHeader>
          <Flex justify="space-between" align="center">
            <Heading size="md" color="gray.700">Producción: Plan vs Real</Heading>
            <Text fontSize="sm" color="gray.500">Últimos 7 días</Text>
          </Flex>
        </CardHeader>
        <CardBody>
          <VStack spacing={4} align="stretch">
            <Box>
              <Flex justify="space-between" mb={2}>
                <Text fontSize="sm" color="gray.600">Planificado</Text>
                <Text fontWeight="bold">{produccion.total_planificado?.toFixed(0) || 0} unidades</Text>
              </Flex>
              <Progress value={100} colorScheme="blue" borderRadius="full" h="20px" />
            </Box>
            
            <Box>
              <Flex justify="space-between" mb={2}>
                <Text fontSize="sm" color="gray.600">Producido</Text>
                <Text fontWeight="bold" color={(produccion.diferencia || 0) >= 0 ? 'green.600' : 'red.600'}>
                  {produccion.total_producido?.toFixed(0) || 0} unidades
                </Text>
              </Flex>
              <Progress 
                value={Math.min((produccion.total_producido / Math.max(produccion.total_planificado, 1)) * 100, 100)} 
                colorScheme={(produccion.diferencia || 0) >= 0 ? 'green' : 'red'} 
                borderRadius="full" 
                h="20px" 
              />
            </Box>
            
            <Divider />
            
            <Flex justify="space-between" align="center">
              <Text color="gray.600">Diferencia:</Text>
              <Text fontSize="xl" fontWeight="bold" color={(produccion.diferencia || 0) >= 0 ? 'green.600' : 'red.600'}>
                {(produccion.diferencia || 0) > 0 ? '+' : ''}{(produccion.diferencia || 0).toFixed(0)} unidades
              </Text>
            </Flex>
          </VStack>
        </CardBody>
      </Card>

      {/* Órdenes Recientes */}
      <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} shadow="md" mb={6} borderRadius="xl">
        <CardHeader>
          <Flex justify="space-between" align="center">
            <Heading size="md" color="gray.700">Órdenes de Producción</Heading>
            <Button 
              size="sm" 
              rightIcon={<ChevronRightIcon />}
              variant="ghost"
              colorScheme="blue"
              onClick={() => navigate('/app/produccion/ordenes')}
            >
              Ver todas
            </Button>
          </Flex>
        </CardHeader>
        <CardBody>
          {/* Filtros */}
          <HStack spacing={4} mb={4}>
            <InputGroup flex={1}>
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
              <option value="pendiente">Pendiente</option>
              <option value="en_proceso">En Proceso</option>
              <option value="finalizada">Finalizada</option>
              <option value="cancelada">Cancelada</option>
            </Select>
          </HStack>

          {/* Lista de órdenes */}
          {ordenesFiltradas.length === 0 ? (
            <VStack py={12} spacing={4}>
              <Icon as={FiClipboard} boxSize={12} color="gray.400" />
              <Text fontSize="lg" fontWeight="medium" color="gray.600">No hay órdenes</Text>
              <Text color="gray.500" textAlign="center">
                Comienza creando una nueva orden de producción
              </Text>
              <Button
                leftIcon={<AddIcon />}
                colorScheme="blue"
                onClick={() => setShowCreateModal(true)}
              >
                Nueva Orden
              </Button>
            </VStack>
          ) : (
            <VStack spacing={3} align="stretch">
              {ordenesFiltradas.map((orden) => (
                <Box
                  key={orden.id}
                  p={4}
                  borderRadius="lg"
                  borderWidth="1px"
                  borderLeftWidth="4px"
                  borderLeftColor={`${getStatusColor(orden.estado)}.500`}
                  bg={`${getStatusColor(orden.estado)}.50`}
                  cursor="pointer"
                  onClick={() => navigate(`/app/produccion/ordenes/${orden.id}`)}
                  _hover={{ shadow: 'md', transform: 'translateY(-2px)' }}
                  transition="all 0.2s"
                >
                  <Flex justify="space-between" align="center" flexWrap="wrap" gap={2}>
                    <HStack spacing={4} flex={1}>
                      <Box 
                        w="10px" 
                        h="10px" 
                        borderRadius="full" 
                        bg={`${getStatusColor(orden.estado)}.500`}
                        animation={orden.estado === 'en_proceso' ? `${pulseAnimation} 1.5s ease-in-out infinite` : undefined}
                      />
                      <Box>
                        <HStack spacing={2}>
                          <Text fontWeight="bold">OP-{orden.numero || orden.id}</Text>
                          <Badge colorScheme={getStatusColor(orden.estado)} fontSize="xs">
                            {orden.estado === 'pendiente' ? 'Pendiente' :
                             orden.estado === 'en_proceso' ? 'En Proceso' :
                             orden.estado === 'finalizada' ? 'Finalizada' : 'Cancelada'}
                          </Badge>
                        </HStack>
                        <Text fontSize="sm" color="gray.600">
                          {orden.producto_nombre || orden.receta__producto_terminado__nombre || 'Producto'}
                        </Text>
                      </Box>
                    </HStack>
                    
                    <HStack spacing={6}>
                      <Box textAlign="center" display={{ base: 'none', md: 'block' }}>
                        <Text fontSize="sm" fontWeight="medium">
                      {orden.cantidad_producida || 0} / {orden.cantidad_planificada}
                        </Text>
                        <Progress 
                          value={((orden.cantidad_producida || 0) / (orden.cantidad_planificada || 1)) * 100}
                          size="sm"
                          colorScheme={getStatusColor(orden.estado)}
                          w="80px"
                          borderRadius="full"
                        />
                      </Box>
                      
                      {(orden.estado === 'pendiente' || orden.estado === 'en_proceso') && (
                        <Button
                          size="sm"
                          colorScheme={orden.estado === 'en_proceso' ? 'blue' : 'green'}
                      onClick={(e) => {
                        e.stopPropagation();
                            navigate(`/app/produccion/ordenes/${orden.id}/ejecutar`);
                          }}
                        >
                          {orden.estado === 'en_proceso' ? 'Continuar' : 'Iniciar'}
                        </Button>
                      )}
                    </HStack>
                  </Flex>
                </Box>
              ))}
            </VStack>
          )}
        </CardBody>
      </Card>

      {/* Accesos Rápidos */}
      <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
        <Button
          variant="outline"
          h="auto"
          p={5}
          borderRadius="xl"
          borderWidth="2px"
          onClick={() => setShowCreateModal(true)}
          _hover={{ transform: 'translateY(-4px)', shadow: 'lg', borderColor: 'blue.300', bg: 'blue.50' }}
          transition="all 0.3s ease"
        >
          <VStack spacing={3}>
            <Flex w="48px" h="48px" bg="blue.100" borderRadius="lg" align="center" justify="center">
              <Icon as={FiPackage} boxSize={6} color="blue.600" />
            </Flex>
            <Text fontWeight="medium" color="gray.700">Nueva Orden</Text>
          </VStack>
        </Button>
        
        <Button
          variant="outline"
          h="auto"
          p={5}
          borderRadius="xl"
          borderWidth="2px"
          onClick={() => navigate('/app/produccion/recetas')}
          _hover={{ transform: 'translateY(-4px)', shadow: 'lg', borderColor: 'green.300', bg: 'green.50' }}
          transition="all 0.3s ease"
        >
          <VStack spacing={3}>
            <Flex w="48px" h="48px" bg="green.100" borderRadius="lg" align="center" justify="center">
              <Icon as={FiClipboard} boxSize={6} color="green.600" />
            </Flex>
            <Text fontWeight="medium" color="gray.700">Recetas (BOM)</Text>
          </VStack>
        </Button>
        
        <Button
          variant="outline"
          h="auto"
          p={5}
          borderRadius="xl"
          borderWidth="2px"
          onClick={() => navigate('/app/produccion/ordenes')}
          _hover={{ transform: 'translateY(-4px)', shadow: 'lg', borderColor: 'purple.300', bg: 'purple.50' }}
          transition="all 0.3s ease"
        >
          <VStack spacing={3}>
            <Flex w="48px" h="48px" bg="purple.100" borderRadius="lg" align="center" justify="center">
              <Icon as={FiTool} boxSize={6} color="purple.600" />
            </Flex>
            <Text fontWeight="medium" color="gray.700">Todas las Órdenes</Text>
          </VStack>
        </Button>
        
        <Button
          variant="outline"
          h="auto"
          p={5}
          borderRadius="xl"
          borderWidth="2px"
          onClick={() => navigate('/app/inventario/materias-primas')}
          _hover={{ transform: 'translateY(-4px)', shadow: 'lg', borderColor: 'orange.300', bg: 'orange.50' }}
          transition="all 0.3s ease"
        >
          <VStack spacing={3}>
            <Flex w="48px" h="48px" bg="orange.100" borderRadius="lg" align="center" justify="center">
              <Icon as={FiBox} boxSize={6} color="orange.600" />
            </Flex>
            <Text fontWeight="medium" color="gray.700">Materias Primas</Text>
          </VStack>
        </Button>
      </SimpleGrid>

      {/* Modal de crear orden */}
      <QuickCreateOrden 
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={(orden) => {
          navigate(`/app/produccion/ordenes/${orden.id}`);
        }}
      />
    </Box>
  );
};

export default DashboardProduccion;
