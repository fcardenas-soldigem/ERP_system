import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Button, Table, Thead, Tbody, Tr, Th, Td,
  Badge, IconButton, Menu, MenuButton, MenuList, MenuItem,
  useToast, Flex, Heading, Input, HStack, Text,
  Center, Tabs, TabList, Tab, InputGroup, InputLeftElement,
  Checkbox, VStack,
} from '@chakra-ui/react';
import {
  FaPlus, FaEllipsisV, FaEye, FaEdit, FaFilePdf,
  FaExchangeAlt, FaTrash, FaSearch, FaChevronLeft, FaChevronRight,
  FaTruck, FaCopy, FaTimesCircle,
} from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';
import guiasService from '../../services/guiasService';

const PAGE_SIZE = 20;

const ESTADO_TABS = [
  { label: 'Todas',      value: '' },
  { label: 'Borrador',   value: 'borrador' },
  { label: 'Emitida',    value: 'emitida' },
  { label: 'En Proceso', value: 'en_proceso' },
  { label: 'Entregada',  value: 'entregada' },
  { label: 'Cancelada',  value: 'cancelada' },
];

const ESTADO_COLOR = {
  borrador:   'gray',
  emitida:    'blue',
  en_proceso: 'yellow',
  entregada:  'green',
  cancelada:  'red',
};

const MOTIVO_COLOR = {
  ingreso_reparacion: 'blue',
  devolucion_cliente: 'green',
  traslado_tecnico:   'orange',
  otro:               'gray',
};

const MOTIVO_LABEL = {
  ingreso_reparacion: 'Ing. Reparación',
  devolucion_cliente: 'Dev. Cliente',
  traslado_tecnico:   'Traslado Técnico',
  otro:               'Otro',
};

const ESTADOS_SIGUIENTES = {
  borrador:   ['emitida', 'cancelada'],
  emitida:    ['en_proceso', 'cancelada'],
  en_proceso: ['entregada', 'cancelada'],
  entregada:  [],
  cancelada:  [],
};

const fmtFecha = (d) => d ? new Date(d + 'T00:00:00').toLocaleDateString('es-PE') : '—';

const GuiaList = () => {
  const [guias, setGuias]           = useState([]);
  const [loading, setLoading]       = useState(true);
  const [selected, setSelected]     = useState(new Set());
  const [tabIndex, setTabIndex]     = useState(0);
  const [search, setSearch]         = useState('');
  const [fechaDesde, setFechaDesde] = useState('');
  const [fechaHasta, setFechaHasta] = useState('');
  const [guiasMes, setGuiasMes]     = useState(0);
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
        ...(fechaDesde   && { fecha_desde: fechaDesde }),
        ...(fechaHasta   && { fecha_hasta: fechaHasta }),
      };
      const data = await guiasService.getAll(params);
      if (data?.results) {
        setGuias(data.results);
        const total = data.count || 0;
        setPaginacion({
          count: total,
          page,
          totalPages: Math.max(1, Math.ceil(total / PAGE_SIZE)),
          hasPrev: !!data.previous,
          hasNext: !!data.next,
        });
      } else if (Array.isArray(data)) {
        setGuias(data);
        setPaginacion({ count: data.length, page: 1, totalPages: 1, hasPrev: false, hasNext: false });
      } else {
        setGuias([]);
      }
    } catch (err) {
      toast({ title: 'Error al cargar guías', description: err.message, status: 'error', duration: 4000, isClosable: true });
      setGuias([]);
    } finally {
      setLoading(false);
    }
  }, [search, estadoFiltro, fechaDesde, fechaHasta, toast]);

  // Contador guías del mes
  useEffect(() => {
    const now = new Date();
    const desde = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`;
    guiasService.getAll({ fecha_desde: desde, page_size: 1 })
      .then(d => setGuiasMes(d?.count ?? (Array.isArray(d) ? d.length : 0)))
      .catch(() => {});
  }, []);

  useEffect(() => { cargar(1); }, [cargar]);

  const toggleSelect = (id) =>
    setSelected(prev => { const s = new Set(prev); s.has(id) ? s.delete(id) : s.add(id); return s; });

  const handlePDF = async (guia) => {
    try {
      await guiasService.exportarPDF(guia.id, guia.numero);
      toast({ title: 'PDF descargado', status: 'success', duration: 2500, isClosable: true });
    } catch (err) {
      toast({ title: 'Error al generar PDF', description: err.message, status: 'error', duration: 4000, isClosable: true });
    }
  };

  const handleExportarSeleccionadas = async () => {
    const ids = [...selected];
    for (const id of ids) {
      const guia = guias.find(g => g.id === id);
      if (guia) {
        try { await guiasService.exportarPDF(guia.id, guia.numero); }
        catch { /* continuar con las demás */ }
      }
    }
    toast({ title: `${ids.length} PDF(s) descargados`, status: 'success', duration: 2500, isClosable: true });
  };

  const handleCambiarEstado = async (guia, estado) => {
    try {
      await guiasService.cambiarEstado(guia.id, estado);
      toast({ title: 'Estado actualizado', description: `${guia.numero} → ${estado}`, status: 'success', duration: 2500, isClosable: true });
      cargar(paginacion.page);
    } catch (err) {
      toast({ title: 'Error', description: err.response?.data?.error || err.message, status: 'error', duration: 4000, isClosable: true });
    }
  };

  const handleDuplicar = async (guia) => {
    try {
      const payload = {
        motivo:              guia.motivo,
        fecha_emision:       new Date().toISOString().split('T')[0],
        fecha_traslado:      guia.fecha_traslado,
        cliente:             guia.cliente ?? null,
        nombre_destinatario: guia.nombre_destinatario,
        ruc_destinatario:    guia.ruc_destinatario ?? '',
        direccion_origen:    guia.direccion_origen,
        direccion_destino:   guia.direccion_destino,
        observaciones:       guia.observaciones ?? '',
        items:               (guia.items || []).map((it, i) => ({
          numero_item:    i + 1,
          descripcion:    it.descripcion,
          serie:          it.serie ?? '',
          marca:          it.marca ?? '',
          modelo:         it.modelo ?? '',
          cantidad:       it.cantidad,
          unidad_medida:  it.unidad_medida ?? 'UNIDAD',
          estado_ingreso: it.estado_ingreso ?? '',
          accesorios:     it.accesorios ?? '',
        })),
      };
      const nueva = await guiasService.create(payload);
      toast({ title: `Guía ${nueva.numero} creada (copia)`, status: 'success', duration: 3000, isClosable: true });
      cargar(paginacion.page);
    } catch (err) {
      toast({ title: 'Error al duplicar', description: err.response?.data ? JSON.stringify(err.response.data).slice(0, 120) : err.message, status: 'error', duration: 4000, isClosable: true });
    }
  };

  const handleEliminar = async (id) => {
    if (!window.confirm('¿Eliminar esta guía?')) return;
    try {
      await guiasService.delete(id);
      toast({ title: 'Guía eliminada', status: 'success', duration: 2500, isClosable: true });
      const nuevaPag = guias.length === 1 && paginacion.page > 1 ? paginacion.page - 1 : paginacion.page;
      cargar(nuevaPag);
    } catch (err) {
      toast({ title: 'Error al eliminar', description: err.message, status: 'error', duration: 4000, isClosable: true });
    }
  };

  return (
    <Box p={6}>
      {/* Header */}
      <Flex justify="space-between" align="flex-start" mb={6}>
        <HStack spacing={3} align="flex-start">
          <Box p={2} bg="blue.50" borderRadius="lg" mt={0.5}>
            <FaTruck size={20} color="var(--chakra-colors-blue-500)" />
          </Box>
          <VStack align="flex-start" spacing={0}>
            <Heading size="lg">Guías de Remisión</Heading>
            <Text fontSize="sm" color="gray.500">Control de ingreso y salida de equipos</Text>
          </VStack>
        </HStack>
        <HStack spacing={3} align="center">
          <Text fontSize="sm" color="gray.400">{guiasMes} guías este mes</Text>
          <Button leftIcon={<FaPlus />} colorScheme="blue" onClick={() => navigate('/app/guias/nueva')}>
            Nueva Guía
          </Button>
        </HStack>
      </Flex>

      {/* Filtros */}
      <Flex gap={3} mb={4} wrap="wrap" align="flex-end">
        <InputGroup maxW="320px">
          <InputLeftElement pointerEvents="none">
            <FaSearch color="var(--chakra-colors-gray-400)" size={13} />
          </InputLeftElement>
          <Input
            pl={9}
            placeholder="Buscar número, cliente, RUC..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </InputGroup>
        <Input type="date" maxW="160px" value={fechaDesde} onChange={(e) => setFechaDesde(e.target.value)} />
        <Input type="date" maxW="160px" value={fechaHasta} onChange={(e) => setFechaHasta(e.target.value)} />
      </Flex>

      {/* Tabs por estado */}
      <Tabs
        index={tabIndex}
        onChange={(i) => { setTabIndex(i); setSelected(new Set()); }}
        mb={4}
        colorScheme="blue"
      >
        <TabList>
          {ESTADO_TABS.map((t) => (
            <Tab key={t.value} fontSize="sm">{t.label}</Tab>
          ))}
        </TabList>
      </Tabs>

      {/* Tabla */}
      {loading ? (
        <Center py={16}><Text color="gray.400">Cargando guías...</Text></Center>
      ) : guias.length === 0 ? (
        <Center py={16} flexDir="column" gap={3}>
          <FaTruck size={36} color="var(--chakra-colors-gray-300)" />
          <Text color="gray.400">No hay guías de remisión registradas</Text>
          <Button size="sm" colorScheme="blue" leftIcon={<FaPlus />} onClick={() => navigate('/app/guias/nueva')}>
            Crear primera guía
          </Button>
        </Center>
      ) : (
        <Box overflowX="auto" bg="white" borderRadius="lg" shadow="sm" border="1px solid" borderColor="gray.100">
          <Table variant="simple" size="sm">
            <Thead bg="gray.50">
              <Tr>
                <Th w="36px">
                  <Checkbox
                    isChecked={selected.size === guias.length && guias.length > 0}
                    isIndeterminate={selected.size > 0 && selected.size < guias.length}
                    onChange={(e) => setSelected(e.target.checked ? new Set(guias.map(g => g.id)) : new Set())}
                  />
                </Th>
                <Th>Número</Th>
                <Th>Cliente / Destinatario</Th>
                <Th>Fecha Emisión</Th>
                <Th>Fecha Traslado</Th>
                <Th>Equipos</Th>
                <Th>Motivo</Th>
                <Th>Estado</Th>
                <Th w="48px"></Th>
              </Tr>
            </Thead>
            <Tbody>
              {guias.map((guia) => {
                const sigEstados = ESTADOS_SIGUIENTES[guia.estado] || [];
                return (
                  <Tr
                    key={guia.id}
                    _hover={{ bg: 'gray.50' }}
                    bg={selected.has(guia.id) ? 'blue.50' : undefined}
                  >
                    <Td>
                      <Checkbox isChecked={selected.has(guia.id)} onChange={() => toggleSelect(guia.id)} />
                    </Td>
                    <Td>
                      <Text
                        fontWeight="bold"
                        color="blue.600"
                        cursor="pointer"
                        _hover={{ textDecoration: 'underline' }}
                        onClick={() => navigate(`/app/guias/${guia.id}`)}
                      >
                        {guia.numero}
                      </Text>
                    </Td>
                    <Td maxW="200px">
                      <Text noOfLines={1} fontSize="sm">{guia.cliente_nombre || guia.nombre_destinatario}</Text>
                    </Td>
                    <Td fontSize="sm">{fmtFecha(guia.fecha_emision)}</Td>
                    <Td fontSize="sm">{fmtFecha(guia.fecha_traslado)}</Td>
                    <Td>
                      <Badge colorScheme="purple" variant="subtle" borderRadius="full">
                        {guia.total_items ?? (guia.items?.length ?? 0)} eq.
                      </Badge>
                    </Td>
                    <Td>
                      <Badge
                        colorScheme={MOTIVO_COLOR[guia.motivo] || 'gray'}
                        variant="subtle"
                        fontSize="xs"
                        borderRadius="full"
                        px={2}
                      >
                        {MOTIVO_LABEL[guia.motivo] || guia.motivo}
                      </Badge>
                    </Td>
                    <Td>
                      <Badge
                        colorScheme={ESTADO_COLOR[guia.estado] || 'gray'}
                        borderRadius="full"
                        px={2}
                      >
                        {guia.estado?.replace('_', ' ').toUpperCase()}
                      </Badge>
                    </Td>
                    <Td>
                      <Menu>
                        <MenuButton as={IconButton} icon={<FaEllipsisV />} variant="ghost" size="sm" />
                        <MenuList fontSize="sm" minW="180px">
                          <MenuItem icon={<FaEye />} onClick={() => navigate(`/app/guias/${guia.id}`)}>
                            Ver Detalle
                          </MenuItem>
                          {guia.estado === 'borrador' && (
                            <MenuItem icon={<FaEdit />} onClick={() => navigate(`/app/guias/${guia.id}/editar`)}>
                              Editar
                            </MenuItem>
                          )}
                          <MenuItem icon={<FaFilePdf />} onClick={() => handlePDF(guia)}>
                            Exportar PDF
                          </MenuItem>
                          <MenuItem icon={<FaCopy />} onClick={() => handleDuplicar(guia)}>
                            Duplicar
                          </MenuItem>
                          {sigEstados.length > 0 && sigEstados.map((e) => (
                            <MenuItem
                              key={e}
                              icon={<FaExchangeAlt />}
                              onClick={() => handleCambiarEstado(guia, e)}
                            >
                              → {e.replace('_', ' ')}
                            </MenuItem>
                          ))}
                          {guia.estado === 'borrador' && (
                            <MenuItem icon={<FaTrash />} color="red.500" onClick={() => handleEliminar(guia.id)}>
                              Eliminar
                            </MenuItem>
                          )}
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
            {' '}de <b>{paginacion.count}</b> guías
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

      {/* Barra flotante de selección */}
      {selected.size > 0 && (
        <Flex
          position="fixed"
          bottom={6}
          left="50%"
          transform="translateX(-50%)"
          bg="gray.800"
          color="white"
          px={5}
          py={3}
          borderRadius="xl"
          shadow="xl"
          align="center"
          gap={4}
          zIndex={1000}
        >
          <Text fontSize="sm" fontWeight="medium">{selected.size} guía(s) seleccionada(s)</Text>
          <Button
            size="sm"
            colorScheme="blue"
            leftIcon={<FaFilePdf />}
            onClick={handleExportarSeleccionadas}
          >
            Exportar PDF
          </Button>
          <IconButton
            icon={<FaTimesCircle />}
            size="sm"
            variant="ghost"
            colorScheme="whiteAlpha"
            color="white"
            onClick={() => setSelected(new Set())}
            aria-label="Cancelar selección"
            _hover={{ bg: 'whiteAlpha.200' }}
          />
        </Flex>
      )}
    </Box>
  );
};

export default GuiaList;
