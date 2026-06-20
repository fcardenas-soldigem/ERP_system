import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Button, Table, Thead, Tbody, Tr, Th, Td,
  Badge, IconButton, Menu, MenuButton, MenuList, MenuItem,
  useToast, Flex, Heading, Input, HStack, Text, VStack,
  Center, Tabs, TabList, Tab, InputGroup, InputLeftElement,
} from '@chakra-ui/react';
import {
  FaPlus, FaEllipsisV, FaEye, FaEdit, FaFilePdf, FaTrash,
  FaSearch, FaChevronLeft, FaChevronRight, FaExchangeAlt, FaTools, FaArrowLeft,
} from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';
import comprasService from '../../services/compras.service';

const PAGE_SIZE = 20;

const ESTADO_TABS = [
  { label: 'Todas',      value: '' },
  { label: 'Borrador',   value: 'borrador' },
  { label: 'Enviada',    value: 'enviada' },
  { label: 'Aprobada',   value: 'aprobada' },
  { label: 'Rechazada',  value: 'rechazada' },
  { label: 'Completada', value: 'completada' },
];

const ESTADO_COLOR = {
  borrador:   'gray',
  enviada:    'blue',
  aprobada:   'teal',
  rechazada:  'red',
  completada: 'green',
};

const SIGUIENTES_ESTADOS = {
  borrador:   ['enviada', 'rechazada'],
  enviada:    ['aprobada', 'rechazada'],
  aprobada:   ['completada', 'rechazada'],
  rechazada:  [],
  completada: [],
};

const fmtFecha = (d) =>
  d ? new Date(d + 'T00:00:00').toLocaleDateString('es-PE', {
    day: '2-digit', month: 'short', year: 'numeric',
  }) : '—';

const OrdenesServicioCompraList = () => {
  const [ordenes, setOrdenes]   = useState([]);
  const [loading, setLoading]   = useState(true);
  const [tabIndex, setTabIndex] = useState(0);
  const [search, setSearch]     = useState('');
  const [exportandoId, setExportandoId] = useState(null);
  const [paginacion, setPaginacion] = useState({
    count: 0, page: 1, totalPages: 1, hasPrev: false, hasNext: false,
  });

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
      };
      const data = await comprasService.getOrdenesServicio(params);
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
  }, [search, estadoFiltro, toast]);

  useEffect(() => { cargar(1); }, [cargar]);

  const handleCambiarEstado = async (orden, estado) => {
    try {
      await comprasService.cambiarEstadoOrdenServicio(orden.id, estado);
      toast({ title: 'Estado actualizado', description: `OCS-${orden.numero} → ${estado}`, status: 'success', duration: 2500, isClosable: true });
      cargar(paginacion.page);
    } catch (err) {
      toast({ title: 'Error', description: err.response?.data?.error || err.message, status: 'error', duration: 4000, isClosable: true });
    }
  };

  const handleExportarPDF = async (orden) => {
    try {
      setExportandoId(orden.id);
      await comprasService.exportarPDFOrdenServicio(orden);
    } catch (err) {
      toast({ title: 'Error al exportar PDF', description: err.message, status: 'error', duration: 4000, isClosable: true });
    } finally {
      setExportandoId(null);
    }
  };

  const handleEliminar = async (orden) => {
    if (!window.confirm(`¿Eliminar la orden OCS-${orden.numero}? Esta acción no se puede deshacer.`)) return;
    try {
      await comprasService.deleteOrdenServicio(orden.id);
      toast({ title: 'Orden eliminada', status: 'success', duration: 2500 });
      cargar(paginacion.page);
    } catch (err) {
      toast({ title: 'Error al eliminar', description: err.message, status: 'error', duration: 4000 });
    }
  };

  const estadoLabel = (e) => ESTADO_TABS.find(t => t.value === e)?.label || e || '—';

  return (
    <Box p={6}>
      {/* Header */}
      <Flex justify="space-between" align="flex-start" mb={5} wrap="wrap" gap={3}>
        <HStack spacing={3} align="flex-start">
          <Box p={2} bg="purple.50" borderRadius="lg" mt={0.5}>
            <FaTools size={20} color="var(--chakra-colors-purple-500)" />
          </Box>
          <VStack align="flex-start" spacing={0}>
            <Heading size="lg">Órdenes de Compra de Servicio</Heading>
            <Text fontSize="sm" color="gray.500">Reparaciones solicitadas a proveedores</Text>
          </VStack>
        </HStack>
        <HStack spacing={2}>
          <Button leftIcon={<FaArrowLeft />} variant="ghost" size="sm" onClick={() => navigate('/app/compras/ordenes')}>
            Órdenes de Compra
          </Button>
          <Button
            leftIcon={<FaPlus />}
            colorScheme="purple"
            onClick={() => navigate('/app/compras/orden-servicio/nueva')}
          >
            Nueva Orden
          </Button>
        </HStack>
      </Flex>

      {/* Filtros */}
      <Flex gap={3} mb={4} wrap="wrap" align="center">
        <InputGroup maxW="320px">
          <InputLeftElement pointerEvents="none">
            <FaSearch color="var(--chakra-colors-gray-400)" size={13} />
          </InputLeftElement>
          <Input
            pl={9}
            placeholder="Número, proveedor, serie, modelo..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </InputGroup>
      </Flex>

      {/* Tabs por estado */}
      <Tabs index={tabIndex} onChange={(i) => setTabIndex(i)} mb={4} colorScheme="purple">
        <TabList overflowX="auto" whiteSpace="nowrap" sx={{ '::-webkit-scrollbar': { display: 'none' } }}>
          {ESTADO_TABS.map((t) => (
            <Tab key={t.value} fontSize="sm" flexShrink={0}>{t.label}</Tab>
          ))}
        </TabList>
      </Tabs>

      {/* Tabla */}
      {loading ? (
        <Center py={16}><Text color="gray.400">Cargando órdenes...</Text></Center>
      ) : ordenes.length === 0 ? (
        <Center py={16} flexDir="column" gap={3}>
          <FaTools size={36} color="var(--chakra-colors-gray-300)" />
          <Text color="gray.400">No hay órdenes de compra de servicio registradas</Text>
          <Button size="sm" colorScheme="purple" leftIcon={<FaPlus />} onClick={() => navigate('/app/compras/orden-servicio/nueva')}>
            Crear primera orden
          </Button>
        </Center>
      ) : (
        <Box overflowX="auto" bg="white" borderRadius="lg" shadow="sm" border="1px solid" borderColor="gray.100">
          <Table variant="simple" size="sm">
            <Thead bg="gray.50">
              <Tr>
                <Th>Número</Th>
                <Th>Proveedor</Th>
                <Th isNumeric>Equipos</Th>
                <Th>Emisión</Th>
                <Th>Entrega</Th>
                <Th isNumeric>Total</Th>
                <Th>Estado</Th>
                <Th w="48px"></Th>
              </Tr>
            </Thead>
            <Tbody>
              {ordenes.map((orden) => {
                const sigEstados = SIGUIENTES_ESTADOS[orden.estado] || [];
                const sym = orden.moneda === 'PEN' ? 'S/' : '$';
                return (
                  <Tr key={orden.id} _hover={{ bg: 'gray.50' }}>
                    <Td>
                      <Text
                        fontWeight="bold" color="purple.600" cursor="pointer"
                        _hover={{ textDecoration: 'underline' }}
                        onClick={() => navigate(`/app/compras/ordenes-servicio/${orden.id}`)}
                        fontFamily="mono" fontSize="sm"
                      >
                        OCS-{orden.numero}
                      </Text>
                    </Td>
                    <Td maxW="200px">
                      <Text noOfLines={1} fontSize="sm">{orden.proveedor_nombre || '—'}</Text>
                    </Td>
                    <Td isNumeric>
                      <Badge colorScheme="purple" variant="subtle" borderRadius="full">{orden.total_items ?? 0}</Badge>
                    </Td>
                    <Td fontSize="sm" whiteSpace="nowrap">{fmtFecha(orden.fecha_emision)}</Td>
                    <Td fontSize="sm" whiteSpace="nowrap">{fmtFecha(orden.fecha_entrega)}</Td>
                    <Td isNumeric fontWeight="bold" whiteSpace="nowrap">
                      {sym} {Number(orden.total || 0).toLocaleString('es-PE', { minimumFractionDigits: 2 })}
                    </Td>
                    <Td>
                      <Badge colorScheme={ESTADO_COLOR[orden.estado] || 'gray'} borderRadius="full" px={2} fontSize="xs">
                        {estadoLabel(orden.estado)}
                      </Badge>
                    </Td>
                    <Td>
                      <Menu>
                        <MenuButton as={IconButton} icon={<FaEllipsisV />} variant="ghost" size="sm" />
                        <MenuList fontSize="sm" minW="190px">
                          <MenuItem icon={<FaEye />} onClick={() => navigate(`/app/compras/ordenes-servicio/${orden.id}`)}>
                            Ver detalle
                          </MenuItem>
                          <MenuItem icon={<FaEdit />} onClick={() => navigate(`/app/compras/ordenes-servicio/${orden.id}/editar`)}>
                            Editar
                          </MenuItem>
                          <MenuItem
                            icon={<FaFilePdf />}
                            onClick={() => handleExportarPDF(orden)}
                            isDisabled={exportandoId === orden.id}
                          >
                            Descargar PDF
                          </MenuItem>
                          {sigEstados.map((e) => (
                            <MenuItem
                              key={e}
                              icon={<FaExchangeAlt />}
                              color={e === 'rechazada' ? 'red.500' : undefined}
                              onClick={() => handleCambiarEstado(orden, e)}
                            >
                              → {estadoLabel(e)}
                            </MenuItem>
                          ))}
                          <MenuItem icon={<FaTrash />} color="red.500" onClick={() => handleEliminar(orden)}>
                            Eliminar
                          </MenuItem>
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
            <IconButton icon={<FaChevronLeft />} size="sm" variant="outline" isDisabled={!paginacion.hasPrev}
              onClick={() => cargar(paginacion.page - 1)} aria-label="Anterior" />
            <Text fontSize="sm" px={2}>{paginacion.page} / {paginacion.totalPages}</Text>
            <IconButton icon={<FaChevronRight />} size="sm" variant="outline" isDisabled={!paginacion.hasNext}
              onClick={() => cargar(paginacion.page + 1)} aria-label="Siguiente" />
          </HStack>
        </Flex>
      )}
    </Box>
  );
};

export default OrdenesServicioCompraList;
