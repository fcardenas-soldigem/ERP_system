import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Button, Table, Thead, Tbody, Tr, Th, Td,
  Badge, IconButton, Menu, MenuButton, MenuList, MenuItem,
  useToast, Flex, Heading, Input, HStack, Text,
  Center, Tabs, TabList, Tab, InputGroup, InputLeftElement,
  VStack, SimpleGrid, Stat, StatLabel, StatNumber,
  Tooltip, Switch, FormLabel,
} from '@chakra-ui/react';
import {
  FaPlus, FaEllipsisV, FaEye, FaEdit, FaFileExcel,
  FaExchangeAlt, FaSearch, FaChevronLeft, FaChevronRight,
  FaExclamationTriangle, FaTools,
} from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';
import serviciosService from '../../services/serviciosService';

const PAGE_SIZE = 20;

const ESTADO_TABS = [
  { label: 'Todas',                  value: '' },
  { label: 'Diag. Pendiente',        value: 'diagnostico_pendiente' },
  { label: 'Diagnosticado',          value: 'diagnostico_completado' },
  { label: 'Cotiz. Enviada',         value: 'cotizacion_enviada' },
  { label: 'Aprobada',               value: 'cotizacion_aprobada' },
  { label: 'En Reparación',          value: 'en_reparacion' },
  { label: 'Completada',             value: 'reparacion_completada' },
  { label: 'Entregado',              value: 'entregado' },
  { label: 'Cancelado',              value: 'cancelado' },
];

const ESTADO_COLOR = {
  diagnostico_pendiente:   'orange',
  diagnostico_completado:  'blue',
  cotizacion_enviada:      'cyan',
  cotizacion_aprobada:     'teal',
  en_reparacion:           'purple',
  reparacion_completada:   'green',
  entregado:               'gray',
  cancelado:               'red',
};

const PRIORIDAD_COLOR = {
  normal:  'gray',
  alta:    'orange',
  urgente: 'red',
};

const fmtFecha = (d) =>
  d ? new Date(d + 'T00:00:00').toLocaleDateString('es-PE', {
    day: '2-digit', month: 'short', year: 'numeric',
  }) : '—';

const SLABar = ({ orden }) => {
  const { dias_restantes_sla, dias_sla = 30, estado_sla, fecha_entrega_estimada } = orden;

  if (dias_restantes_sla === null || dias_restantes_sla === undefined) {
    return <Text fontSize="xs" color="gray.400">Sin fecha</Text>;
  }

  const usado   = dias_sla - dias_restantes_sla;
  const pct     = Math.min(100, Math.max(0, (usado / dias_sla) * 100));
  const vencido = dias_restantes_sla < 0;

  const barColor = estado_sla === 'vencido'  ? 'red.500'
    : estado_sla === 'critico' ? 'red.400'
    : estado_sla === 'alerta'  ? 'orange.400'
    : 'green.400';

  const textColor = estado_sla === 'vencido'  ? 'red.600'
    : estado_sla === 'critico' ? 'red.500'
    : estado_sla === 'alerta'  ? 'orange.500'
    : 'green.600';

  const label = vencido
    ? `Vencido hace ${Math.abs(dias_restantes_sla)} días`
    : `${dias_restantes_sla} días restantes`;

  return (
    <Tooltip label={fecha_entrega_estimada ? `Vence el ${fmtFecha(fecha_entrega_estimada)}` : ''} placement="top">
      <Box minW="110px">
        <Box
          h="5px"
          bg="gray.100"
          borderRadius="full"
          overflow="hidden"
          mb={1}
          position="relative"
        >
          <Box
            h="100%"
            w={`${pct}%`}
            bg={barColor}
            borderRadius="full"
            sx={vencido ? { animation: 'pulse 1.5s infinite' } : undefined}
          />
        </Box>
        <Text
          fontSize="xs"
          fontWeight={estado_sla !== 'ok' ? 'bold' : 'normal'}
          color={textColor}
          whiteSpace="nowrap"
        >
          {label}
        </Text>
      </Box>
    </Tooltip>
  );
};

const StatCard = ({ label, value, colorScheme, icon }) => (
  <Box
    bg={`${colorScheme}.50`}
    border="1px solid"
    borderColor={`${colorScheme}.100`}
    borderRadius="lg"
    p={3}
    flex="1"
    minW="120px"
  >
    <Stat>
      <StatLabel fontSize="xs" color={`${colorScheme}.700`} fontWeight="medium">
        {label}
      </StatLabel>
      <StatNumber fontSize="2xl" color={`${colorScheme}.600`} lineHeight="1.2" mt={1}>
        {value}
      </StatNumber>
    </Stat>
  </Box>
);

const OrdenServicioList = () => {
  const [ordenes, setOrdenes]       = useState([]);
  const [loading, setLoading]       = useState(true);
  const [tabIndex, setTabIndex]     = useState(0);
  const [search, setSearch]         = useState('');
  const [soloRiesgo, setSoloRiesgo] = useState(false);
  const [resumen, setResumen]       = useState(null);
  const [paginacion, setPaginacion] = useState({
    count: 0, page: 1, totalPages: 1, hasPrev: false, hasNext: false,
  });
  const [exportando, setExportando] = useState(false);

  const navigate = useNavigate();
  const toast    = useToast();

  const estadoFiltro = ESTADO_TABS[tabIndex].value;

  const cargar = useCallback(async (page = 1) => {
    try {
      setLoading(true);
      const params = {
        page,
        page_size: PAGE_SIZE,
        ...(search       && { search }),
        ...(estadoFiltro && { estado: estadoFiltro }),
        ...(soloRiesgo   && { en_riesgo: 'true' }),
      };
      const data = await serviciosService.listar(params);
      if (data?.results) {
        setOrdenes(data.results);
        const total = data.count || 0;
        setPaginacion({
          count: total,
          page,
          totalPages: Math.max(1, Math.ceil(total / PAGE_SIZE)),
          hasPrev: !!data.previous,
          hasNext: !!data.next,
        });
      } else if (Array.isArray(data)) {
        setOrdenes(data);
        setPaginacion({ count: data.length, page: 1, totalPages: 1, hasPrev: false, hasNext: false });
      } else {
        setOrdenes([]);
      }
    } catch (err) {
      toast({ title: 'Error al cargar órdenes', description: err.message, status: 'error', duration: 4000, isClosable: true });
      setOrdenes([]);
    } finally {
      setLoading(false);
    }
  }, [search, estadoFiltro, soloRiesgo, toast]);

  useEffect(() => { cargar(1); }, [cargar]);

  useEffect(() => {
    serviciosService.resumen()
      .then(setResumen)
      .catch(() => {});
  }, []);

  const handleCambiarEstado = async (orden, estado, notas = '') => {
    try {
      await serviciosService.cambiarEstado(orden.id, { estado, notas });
      toast({ title: 'Estado actualizado', description: `${orden.numero} → ${estado}`, status: 'success', duration: 2500, isClosable: true });
      cargar(paginacion.page);
    } catch (err) {
      toast({ title: 'Error', description: err.response?.data?.error || err.message, status: 'error', duration: 4000, isClosable: true });
    }
  };

  const handleExportarExcel = async () => {
    try {
      setExportando(true);
      await serviciosService.exportarExcel();
      toast({ title: 'Excel descargado', status: 'success', duration: 2500, isClosable: true });
    } catch (err) {
      toast({ title: 'Error al exportar', description: err.message, status: 'error', duration: 4000, isClosable: true });
    } finally {
      setExportando(false);
    }
  };

  const SIGUIENTES_ESTADOS = {
    diagnostico_pendiente:  ['diagnostico_completado', 'cancelado'],
    diagnostico_completado: ['cotizacion_enviada', 'cancelado'],
    cotizacion_enviada:     ['cotizacion_aprobada', 'cancelado'],
    cotizacion_aprobada:    ['en_reparacion', 'cancelado'],
    en_reparacion:          ['reparacion_completada', 'cancelado'],
    reparacion_completada:  ['entregado', 'cancelado'],
    entregado:              [],
    cancelado:              [],
  };

  const estadoLabel = (e) =>
    ESTADO_TABS.find(t => t.value === e)?.label || e?.replace(/_/g, ' ') || '—';

  const completadasEsteMes = (() => {
    const now = new Date();
    return ordenes.filter(o => {
      if (o.estado !== 'entregado') return false;
      const f = o.fecha_entrega_real;
      if (!f) return false;
      const d = new Date(f);
      return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
    }).length;
  })();

  return (
    <Box p={6}>
      {/* Header */}
      <Flex justify="space-between" align="flex-start" mb={5}>
        <HStack spacing={3} align="flex-start">
          <Box p={2} bg="blue.50" borderRadius="lg" mt={0.5}>
            <FaTools size={20} color="var(--chakra-colors-blue-500)" />
          </Box>
          <VStack align="flex-start" spacing={0}>
            <Heading size="lg">Órdenes de Servicio</Heading>
            <Text fontSize="sm" color="gray.500">Control de reparaciones y SLA</Text>
          </VStack>
        </HStack>
        <HStack spacing={2}>
          <Button
            leftIcon={<FaFileExcel />}
            variant="outline"
            colorScheme="green"
            size="sm"
            onClick={handleExportarExcel}
            isLoading={exportando}
          >
            Excel
          </Button>
          <Button
            leftIcon={<FaPlus />}
            colorScheme="blue"
            onClick={() => navigate('/app/servicios/nueva')}
          >
            Nueva Orden
          </Button>
        </HStack>
      </Flex>

      {/* Stat cards */}
      <SimpleGrid columns={{ base: 2, md: 4 }} spacing={3} mb={5}>
        <StatCard
          label="Activas"
          value={resumen?.total_activas ?? '—'}
          colorScheme="blue"
        />
        <StatCard
          label="En riesgo SLA"
          value={resumen?.en_riesgo ?? '—'}
          colorScheme="yellow"
        />
        <StatCard
          label="Vencidas"
          value={resumen?.vencidas ?? '—'}
          colorScheme="red"
        />
        <StatCard
          label="Completadas este mes"
          value={completadasEsteMes}
          colorScheme="green"
        />
      </SimpleGrid>

      {/* Filtros */}
      <Flex gap={3} mb={4} wrap="wrap" align="center">
        <InputGroup maxW="320px">
          <InputLeftElement pointerEvents="none">
            <FaSearch color="var(--chakra-colors-gray-400)" size={13} />
          </InputLeftElement>
          <Input
            pl={9}
            placeholder="Número, cliente, serie, modelo..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </InputGroup>
        <HStack spacing={2} align="center">
          <FormLabel htmlFor="solo-riesgo" mb={0} fontSize="sm" color="gray.600" cursor="pointer">
            Solo en riesgo
          </FormLabel>
          <Switch
            id="solo-riesgo"
            colorScheme="red"
            isChecked={soloRiesgo}
            onChange={(e) => setSoloRiesgo(e.target.checked)}
          />
          {soloRiesgo && (
            <Badge colorScheme="red" variant="subtle">
              <FaExclamationTriangle style={{ display: 'inline', marginRight: 4 }} />
              Filtro activo
            </Badge>
          )}
        </HStack>
      </Flex>

      {/* Tabs por estado */}
      <Tabs
        index={tabIndex}
        onChange={(i) => setTabIndex(i)}
        mb={4}
        colorScheme="blue"
      >
        <TabList overflowX="auto" whiteSpace="nowrap" sx={{ '::-webkit-scrollbar': { display: 'none' } }}>
          {ESTADO_TABS.map((t) => (
            <Tab key={t.value} fontSize="sm" flexShrink={0}>
              {t.label}
            </Tab>
          ))}
        </TabList>
      </Tabs>

      {/* Tabla */}
      {loading ? (
        <Center py={16}><Text color="gray.400">Cargando órdenes...</Text></Center>
      ) : ordenes.length === 0 ? (
        <Center py={16} flexDir="column" gap={3}>
          <FaTools size={36} color="var(--chakra-colors-gray-300)" />
          <Text color="gray.400">No hay órdenes de servicio registradas</Text>
          <Button
            size="sm"
            colorScheme="blue"
            leftIcon={<FaPlus />}
            onClick={() => navigate('/app/servicios/nueva')}
          >
            Crear primera orden
          </Button>
        </Center>
      ) : (
        <Box overflowX="auto" bg="white" borderRadius="lg" shadow="sm" border="1px solid" borderColor="gray.100">
          <Table variant="simple" size="sm">
            <Thead bg="gray.50">
              <Tr>
                <Th>Número</Th>
                <Th>Cliente</Th>
                <Th>Proveedor</Th>
                <Th isNumeric>Equipos</Th>
                <Th>Ingreso</Th>
                <Th isNumeric>Días</Th>
                <Th minW="140px">SLA</Th>
                <Th>Estado</Th>
                <Th>Prioridad</Th>
                <Th w="48px"></Th>
              </Tr>
            </Thead>
            <Tbody>
              {ordenes.map((orden) => {
                const sigEstados = SIGUIENTES_ESTADOS[orden.estado] || [];
                const estaEnRiesgo = orden.en_riesgo;

                return (
                  <Tr
                    key={orden.id}
                    _hover={{ bg: 'gray.50' }}
                    bg={estaEnRiesgo && orden.estado !== 'entregado' ? 'red.50' : undefined}
                  >
                    <Td>
                      <Text
                        fontWeight="bold"
                        color="blue.600"
                        cursor="pointer"
                        _hover={{ textDecoration: 'underline' }}
                        onClick={() => navigate(`/app/servicios/${orden.id}`)}
                        fontFamily="mono"
                        fontSize="sm"
                      >
                        {orden.numero}
                      </Text>
                    </Td>
                    <Td maxW="160px">
                      <Text noOfLines={1} fontSize="sm">
                        {orden.cliente_nombre || '—'}
                      </Text>
                    </Td>
                    <Td maxW="140px">
                      <Text noOfLines={1} fontSize="sm" color="gray.600">
                        {orden.proveedor_nombre || '—'}
                      </Text>
                    </Td>
                    <Td isNumeric>
                      <Badge colorScheme="purple" variant="subtle" borderRadius="full">
                        {orden.total_items ?? 0}
                      </Badge>
                    </Td>
                    <Td fontSize="sm" whiteSpace="nowrap">
                      {fmtFecha(orden.fecha_ingreso)}
                    </Td>
                    <Td isNumeric>
                      <Text
                        fontSize="xl"
                        fontWeight="bold"
                        color={
                          (orden.dias_transcurridos ?? 0) > 25 ? 'red.500'
                          : (orden.dias_transcurridos ?? 0) > 15 ? 'orange.500'
                          : 'gray.700'
                        }
                        lineHeight="1"
                      >
                        {orden.dias_transcurridos ?? '—'}
                      </Text>
                    </Td>
                    <Td>
                      <SLABar orden={orden} />
                    </Td>
                    <Td>
                      <Badge
                        colorScheme={ESTADO_COLOR[orden.estado] || 'gray'}
                        borderRadius="full"
                        px={2}
                        fontSize="xs"
                      >
                        {estadoLabel(orden.estado)}
                      </Badge>
                    </Td>
                    <Td>
                      <Badge
                        colorScheme={PRIORIDAD_COLOR[orden.prioridad] || 'gray'}
                        variant={orden.prioridad === 'urgente' ? 'solid' : 'subtle'}
                        borderRadius="full"
                        px={2}
                        fontSize="xs"
                      >
                        {orden.prioridad || 'normal'}
                      </Badge>
                    </Td>
                    <Td>
                      <Menu>
                        <MenuButton as={IconButton} icon={<FaEllipsisV />} variant="ghost" size="sm" />
                        <MenuList fontSize="sm" minW="190px">
                          <MenuItem
                            icon={<FaEye />}
                            onClick={() => navigate(`/app/servicios/${orden.id}`)}
                          >
                            Ver detalle
                          </MenuItem>
                          <MenuItem
                            icon={<FaEdit />}
                            onClick={() => navigate(`/app/servicios/${orden.id}/editar`)}
                          >
                            Editar
                          </MenuItem>
                          {sigEstados.length > 0 && sigEstados.map((e) => (
                            <MenuItem
                              key={e}
                              icon={<FaExchangeAlt />}
                              color={e === 'cancelado' ? 'red.500' : undefined}
                              onClick={() => handleCambiarEstado(orden, e)}
                            >
                              → {estadoLabel(e)}
                            </MenuItem>
                          ))}
                        </MenuList>
                      </Menu>
                    </Td>
                  </Tr>
                );
              })}
            </Tbody>
          </Table>
        </Box>
      )}

      {/* Paginación */}
      {!loading && paginacion.totalPages > 1 && (
        <Flex justify="space-between" align="center" mt={4} px={1}>
          <Text fontSize="sm" color="gray.500">
            Mostrando{' '}
            <b>{Math.min((paginacion.page - 1) * PAGE_SIZE + 1, paginacion.count)}–{Math.min(paginacion.page * PAGE_SIZE, paginacion.count)}</b>
            {' '}de <b>{paginacion.count}</b> órdenes
          </Text>
          <HStack spacing={1}>
            <IconButton
              icon={<FaChevronLeft />}
              size="sm"
              variant="outline"
              isDisabled={!paginacion.hasPrev}
              onClick={() => cargar(paginacion.page - 1)}
              aria-label="Anterior"
            />
            {Array.from({ length: paginacion.totalPages }, (_, i) => i + 1)
              .filter(p => p === 1 || p === paginacion.totalPages || Math.abs(p - paginacion.page) <= 2)
              .reduce((acc, p, idx, arr) => {
                if (idx > 0 && p - arr[idx - 1] > 1) acc.push('…');
                acc.push(p);
                return acc;
              }, [])
              .map((p, idx) =>
                p === '…'
                  ? <Text key={`e${idx}`} px={2} color="gray.400" fontSize="sm">…</Text>
                  : <Button
                      key={p}
                      size="sm"
                      variant={p === paginacion.page ? 'solid' : 'outline'}
                      colorScheme={p === paginacion.page ? 'blue' : 'gray'}
                      minW="36px"
                      onClick={() => cargar(p)}
                    >{p}</Button>
              )}
            <IconButton
              icon={<FaChevronRight />}
              size="sm"
              variant="outline"
              isDisabled={!paginacion.hasNext}
              onClick={() => cargar(paginacion.page + 1)}
              aria-label="Siguiente"
            />
          </HStack>
        </Flex>
      )}
    </Box>
  );
};

export default OrdenServicioList;
