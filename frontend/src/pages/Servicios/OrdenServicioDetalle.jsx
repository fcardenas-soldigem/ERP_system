import React, { useState, useEffect } from 'react';
import {
  Box, Flex, Heading, Text, Badge, Button, VStack, HStack,
  Divider, Table, Thead, Tbody, Tr, Th, Td, Card, CardBody,
  CardHeader, Spinner, Center, useToast, useColorModeValue,
  Menu, MenuButton, MenuList, MenuItem, IconButton, SimpleGrid,
  Stat, StatLabel, StatNumber, Alert, AlertIcon, Stack,
  Textarea, Modal, ModalOverlay, ModalContent, ModalHeader,
  ModalFooter, ModalBody, ModalCloseButton, useDisclosure,
  Input, FormControl, FormLabel,
} from '@chakra-ui/react';
import {
  FaArrowLeft, FaEdit, FaFileExcel, FaExchangeAlt, FaEllipsisV,
  FaTools, FaCalendar, FaUser, FaCheck, FaPlus, FaExclamationTriangle,
  FaTruck,
} from 'react-icons/fa';
import { useParams, useNavigate } from 'react-router-dom';
import serviciosService from '../../services/serviciosService';

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

const ESTADO_LABEL = {
  diagnostico_pendiente:   'Diagnóstico Pendiente',
  diagnostico_completado:  'Diagnóstico Completado',
  cotizacion_enviada:      'Cotización Enviada',
  cotizacion_aprobada:     'Cotización Aprobada',
  en_reparacion:           'En Reparación',
  reparacion_completada:   'Reparación Completada',
  entregado:               'Entregado',
  cancelado:               'Cancelado',
};

const PRIORIDAD_COLOR = { normal: 'gray', alta: 'orange', urgente: 'red' };

const TIMELINE_ESTADOS = [
  'diagnostico_pendiente',
  'diagnostico_completado',
  'cotizacion_enviada',
  'cotizacion_aprobada',
  'en_reparacion',
  'reparacion_completada',
  'entregado',
];

const ESTADO_ITEM_COLOR = {
  pendiente:      'gray',
  en_diagnostico: 'orange',
  diagnosticado:  'blue',
  en_reparacion:  'purple',
  reparado:       'green',
  no_reparable:   'red',
  entregado:      'teal',
};

const SIGUIENTE_ACCION = {
  diagnostico_pendiente:   { label: 'Completar Diagnóstico', estado: 'diagnostico_completado' },
  diagnostico_completado:  { label: 'Enviar Cotización',     estado: 'cotizacion_enviada' },
  cotizacion_enviada:      { label: 'Marcar Aprobada',       estado: 'cotizacion_aprobada' },
  cotizacion_aprobada:     { label: 'Iniciar Reparación',    estado: 'en_reparacion' },
  en_reparacion:           { label: 'Reparación Completada', estado: 'reparacion_completada' },
  reparacion_completada:   { label: 'Marcar Entregado',      estado: 'entregado' },
};

const fmtFecha = (d) =>
  d ? new Date(d).toLocaleDateString('es-PE', { day: '2-digit', month: 'short', year: 'numeric' }) : '—';

const fmtMoney = (v) =>
  v !== null && v !== undefined
    ? `S/ ${parseFloat(v).toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : '—';

const MargenBadge = ({ pct }) => {
  if (pct === null || pct === undefined) return <Text color="gray.400">—</Text>;
  const n = parseFloat(pct);
  const color = n >= 30 ? 'green' : n >= 15 ? 'yellow' : 'red';
  return (
    <Badge colorScheme={color} variant="subtle" borderRadius="full">
      {n.toFixed(1)}%
    </Badge>
  );
};

const OrdenServicioDetalle = () => {
  const { id }   = useParams();
  const navigate = useNavigate();
  const toast    = useToast();

  const [orden, setOrden]           = useState(null);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState(null);
  const [cambiandoEstado, setCambiandoEstado] = useState(false);

  const { isOpen: isSeguimientoOpen, onOpen: onSeguimientoOpen, onClose: onSeguimientoClose } = useDisclosure();
  const [seguimientoData, setSeguimientoData] = useState({
    estado_reportado: '', fecha_entrega_prometida: '', notas: '',
  });
  const [guardandoSeg, setGuardandoSeg] = useState(false);

  const cardBg      = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const labelColor  = useColorModeValue('gray.500', 'gray.400');

  useEffect(() => { cargar(); }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const cargar = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await serviciosService.obtener(id);
      setOrden(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'No se pudo cargar la orden');
      toast({ title: 'Error', description: err.message, status: 'error', duration: 4000, isClosable: true });
    } finally {
      setLoading(false);
    }
  };

  const handleCambiarEstado = async (estado, notas = '') => {
    try {
      setCambiandoEstado(true);
      await serviciosService.cambiarEstado(orden.id, { estado, notas });
      toast({ title: 'Estado actualizado', description: `${orden.numero} → ${ESTADO_LABEL[estado]}`, status: 'success', duration: 2500, isClosable: true });
      cargar();
    } catch (err) {
      toast({ title: 'Error', description: err.response?.data?.error || err.message, status: 'error', duration: 4000, isClosable: true });
    } finally {
      setCambiandoEstado(false);
    }
  };

  const handleAgregarSeguimiento = async () => {
    if (!seguimientoData.estado_reportado || !seguimientoData.notas) {
      toast({ title: 'Completa estado y notas', status: 'warning', duration: 3000, isClosable: true });
      return;
    }
    try {
      setGuardandoSeg(true);
      await serviciosService.agregarSeguimiento(orden.id, seguimientoData);
      toast({ title: 'Seguimiento registrado', status: 'success', duration: 2500, isClosable: true });
      onSeguimientoClose();
      setSeguimientoData({ estado_reportado: '', fecha_entrega_prometida: '', notas: '' });
      cargar();
    } catch (err) {
      toast({ title: 'Error', description: err.response?.data ? JSON.stringify(err.response.data).slice(0, 120) : err.message, status: 'error', duration: 4000, isClosable: true });
    } finally {
      setGuardandoSeg(false);
    }
  };

  if (loading) return <Center py={24}><Spinner size="xl" color="blue.500" /></Center>;
  if (error)   return <Center py={16}><Alert status="error" maxW="400px" borderRadius="lg"><AlertIcon />{error}</Alert></Center>;
  if (!orden)  return null;

  const timelineIdx  = TIMELINE_ESTADOS.indexOf(orden.estado);
  const accionSig    = SIGUIENTE_ACCION[orden.estado];
  const estaVencido  = orden.estado_sla === 'vencido';
  const estaEnRiesgo = orden.en_riesgo;

  const totalCostoProv   = (orden.items || []).reduce((s, i) => s + parseFloat(i.costo_proveedor || 0), 0);
  const totalPrecioClient = (orden.items || []).reduce((s, i) => s + parseFloat(i.precio_cliente || 0), 0);
  const totalMargen      = totalPrecioClient - totalCostoProv;
  const margenPct        = totalPrecioClient > 0 ? (totalMargen / totalPrecioClient) * 100 : 0;

  return (
    <Box p={6} maxW="1300px" mx="auto">
      {/* Barra superior */}
      <Flex justify="space-between" align="center" mb={6}>
        <HStack spacing={3}>
          <IconButton icon={<FaArrowLeft />} variant="ghost" size="sm" onClick={() => navigate('/app/servicios')} aria-label="Volver" />
          <Box>
            <Heading size="md" fontFamily="mono">{orden.numero}</Heading>
            <Text fontSize="sm" color={labelColor}>{orden.cliente_nombre}</Text>
          </Box>
          <Badge
            colorScheme={ESTADO_COLOR[orden.estado]}
            borderRadius="full"
            px={3}
            py={1}
            fontSize="sm"
          >
            {ESTADO_LABEL[orden.estado] || orden.estado}
          </Badge>
          <Badge
            colorScheme={PRIORIDAD_COLOR[orden.prioridad]}
            variant={orden.prioridad === 'urgente' ? 'solid' : 'subtle'}
            borderRadius="full"
            px={2}
          >
            {orden.prioridad?.toUpperCase()}
          </Badge>
        </HStack>
        <HStack spacing={2}>
          <Button
            leftIcon={<FaFileExcel />}
            variant="outline"
            colorScheme="green"
            size="sm"
            onClick={() => serviciosService.exportarExcel()}
          >
            Excel
          </Button>
          <Button
            leftIcon={<FaEdit />}
            colorScheme="blue"
            size="sm"
            variant="outline"
            onClick={() => navigate(`/app/servicios/${orden.id}/editar`)}
          >
            Editar
          </Button>
          {accionSig && (
            <Button
              colorScheme="blue"
              size="sm"
              leftIcon={<FaExchangeAlt />}
              isLoading={cambiandoEstado}
              onClick={() => handleCambiarEstado(accionSig.estado)}
            >
              {accionSig.label}
            </Button>
          )}
        </HStack>
      </Flex>

      {/* Banner vencido */}
      {estaVencido && orden.estado !== 'entregado' && orden.estado !== 'cancelado' && (
        <Alert status="error" borderRadius="lg" mb={4}>
          <AlertIcon />
          <Text fontWeight="bold">
            SLA VENCIDO — hace {Math.abs(orden.dias_restantes_sla)} días
          </Text>
          <Text ml={2} fontSize="sm">Requiere atención inmediata</Text>
        </Alert>
      )}

      {/* Layout 65/35 */}
      <Flex gap={5} align="flex-start" direction={{ base: 'column', lg: 'row' }}>

        {/* ── Columna izquierda (65%) ── */}
        <Box flex="1" minW={0}>

          {/* Info general */}
          <Card bg={cardBg} borderColor={borderColor} border="1px solid" borderRadius="lg" mb={4} shadow="sm">
            <CardHeader pb={2}>
              <Heading size="sm" color="blue.600">Información de la Orden</Heading>
            </CardHeader>
            <CardBody pt={0}>
              <SimpleGrid columns={{ base: 2, sm: 3 }} spacing={4} mb={4}>
                <Box>
                  <Text fontSize="xs" color={labelColor} mb={0.5}>Cliente</Text>
                  <Text fontWeight="semibold">{orden.cliente_nombre || '—'}</Text>
                </Box>
                <Box>
                  <Text fontSize="xs" color={labelColor} mb={0.5}>Proveedor Reparación</Text>
                  <Text fontWeight="semibold">{orden.proveedor_nombre || '—'}</Text>
                </Box>
                <Box>
                  <Text fontSize="xs" color={labelColor} mb={0.5}>Prioridad</Text>
                  <Badge colorScheme={PRIORIDAD_COLOR[orden.prioridad]} variant="subtle">
                    {orden.prioridad?.toUpperCase()}
                  </Badge>
                </Box>
              </SimpleGrid>
              <Divider mb={4} />
              <SimpleGrid columns={{ base: 2, sm: 3, md: 5 }} spacing={4}>
                {[
                  { label: 'Ingreso',             value: fmtFecha(orden.fecha_ingreso) },
                  { label: 'Diagnóstico',          value: fmtFecha(orden.fecha_diagnostico) },
                  { label: 'Cotiz. enviada',       value: fmtFecha(orden.fecha_cotizacion_enviada) },
                  { label: 'Aprobación',           value: fmtFecha(orden.fecha_aprobacion) },
                  { label: 'Inicio reparación',    value: fmtFecha(orden.fecha_inicio_reparacion) },
                  { label: 'Entrega estimada',     value: fmtFecha(orden.fecha_entrega_estimada) },
                  { label: 'Entrega real',         value: fmtFecha(orden.fecha_entrega_real) },
                ].map(({ label, value }) => (
                  <Box key={label}>
                    <Text fontSize="xs" color={labelColor} mb={0.5}>{label}</Text>
                    <Text fontSize="sm" fontWeight="medium">{value}</Text>
                  </Box>
                ))}
              </SimpleGrid>
              {orden.notas_internas && (
                <>
                  <Divider my={3} />
                  <Box>
                    <Text fontSize="xs" color={labelColor} mb={1}>Notas internas</Text>
                    <Text fontSize="sm" color="gray.700" whiteSpace="pre-wrap">{orden.notas_internas}</Text>
                  </Box>
                </>
              )}
            </CardBody>
          </Card>

          {/* Tabla de equipos */}
          <Card bg={cardBg} borderColor={borderColor} border="1px solid" borderRadius="lg" shadow="sm" mb={4}>
            <CardHeader pb={2}>
              <Flex justify="space-between" align="center">
                <HStack>
                  <FaTools size={13} color="var(--chakra-colors-blue-500)" />
                  <Heading size="sm" color="blue.600">Equipos / Ítems</Heading>
                </HStack>
                <Badge colorScheme="purple" variant="subtle">{orden.items?.length ?? 0} ítem(s)</Badge>
              </Flex>
            </CardHeader>
            <CardBody pt={0}>
              {!orden.items?.length ? (
                <Center py={6}><Text color="gray.400" fontSize="sm">Sin ítems registrados</Text></Center>
              ) : (
                <>
                  <Box overflowX="auto">
                    <Table size="sm" variant="simple">
                      <Thead bg="blue.50">
                        <Tr>
                          <Th w="32px">#</Th>
                          <Th>N° Serie</Th>
                          <Th>Modelo</Th>
                          <Th>Falla Cliente</Th>
                          <Th>Falla Diagnóstico</Th>
                          <Th>Estado</Th>
                          <Th isNumeric>Costo Prov.</Th>
                          <Th isNumeric>Precio Cliente</Th>
                          <Th>Margen</Th>
                        </Tr>
                      </Thead>
                      <Tbody>
                        {(orden.items || []).map((item, i) => {
                          const margenItemPct =
                            item.precio_cliente && parseFloat(item.precio_cliente) > 0
                              ? ((parseFloat(item.precio_cliente) - parseFloat(item.costo_proveedor || 0)) / parseFloat(item.precio_cliente)) * 100
                              : null;
                          return (
                            <Tr key={item.id} bg={i % 2 === 1 ? 'gray.50' : undefined}>
                              <Td color="gray.400" fontSize="xs">{item.numero_item}</Td>
                              <Td>
                                <Text fontFamily="mono" fontSize="xs">{item.numero_serie || '—'}</Text>
                                {item.falla_adicional && (
                                  <Badge colorScheme="red" fontSize="9px" mt={0.5}>Falla adicional</Badge>
                                )}
                              </Td>
                              <Td>
                                <Text fontSize="xs">{item.modelo || '—'}</Text>
                                <Text fontSize="xs" color="gray.400">{item.marca || ''}</Text>
                              </Td>
                              <Td maxW="160px">
                                <Text fontSize="xs" noOfLines={2}>{item.falla_cliente || '—'}</Text>
                              </Td>
                              <Td maxW="160px">
                                <Text fontSize="xs" noOfLines={2}>{item.falla_diagnostico || '—'}</Text>
                              </Td>
                              <Td>
                                <Badge
                                  colorScheme={ESTADO_ITEM_COLOR[item.estado_item] || 'gray'}
                                  variant="subtle"
                                  fontSize="xs"
                                  borderRadius="full"
                                >
                                  {item.estado_item?.replace(/_/g, ' ')}
                                </Badge>
                              </Td>
                              <Td isNumeric fontSize="xs">{fmtMoney(item.costo_proveedor)}</Td>
                              <Td isNumeric fontSize="xs">{fmtMoney(item.precio_cliente)}</Td>
                              <Td><MargenBadge pct={margenItemPct} /></Td>
                            </Tr>
                          );
                        })}
                      </Tbody>
                    </Table>
                  </Box>
                  {/* Totales */}
                  <Flex justify="flex-end" mt={3} gap={6} pr={2} flexWrap="wrap">
                    <Box textAlign="right">
                      <Text fontSize="xs" color={labelColor}>Total costo proveedor</Text>
                      <Text fontWeight="bold" fontSize="sm">{fmtMoney(totalCostoProv)}</Text>
                    </Box>
                    <Box textAlign="right">
                      <Text fontSize="xs" color={labelColor}>Total precio cliente</Text>
                      <Text fontWeight="bold" fontSize="sm">{fmtMoney(totalPrecioClient)}</Text>
                    </Box>
                    <Box textAlign="right">
                      <Text fontSize="xs" color={labelColor}>Margen total</Text>
                      <Text
                        fontWeight="bold"
                        fontSize="sm"
                        color={margenPct >= 30 ? 'green.600' : margenPct >= 15 ? 'orange.500' : 'red.500'}
                      >
                        {fmtMoney(totalMargen)} ({margenPct.toFixed(1)}%)
                      </Text>
                    </Box>
                  </Flex>
                </>
              )}
            </CardBody>
          </Card>

          {/* Seguimiento del proveedor */}
          <Card bg={cardBg} borderColor={borderColor} border="1px solid" borderRadius="lg" shadow="sm">
            <CardHeader pb={2}>
              <Flex justify="space-between" align="center">
                <Heading size="sm" color="blue.600">Seguimiento del Proveedor</Heading>
                <Button
                  size="xs"
                  colorScheme="blue"
                  leftIcon={<FaPlus />}
                  onClick={onSeguimientoOpen}
                  variant="outline"
                >
                  Agregar seguimiento
                </Button>
              </Flex>
            </CardHeader>
            <CardBody pt={0}>
              {!orden.seguimientos?.length ? (
                <Center py={6} flexDir="column" gap={2}>
                  <Text color="gray.400" fontSize="sm">Sin seguimientos registrados</Text>
                  <Button size="xs" leftIcon={<FaPlus />} colorScheme="blue" variant="ghost" onClick={onSeguimientoOpen}>
                    Registrar primer seguimiento
                  </Button>
                </Center>
              ) : (
                <VStack align="stretch" spacing={0}>
                  {(orden.seguimientos || []).map((seg, i) => (
                    <Flex key={seg.id} gap={3} pb={i < orden.seguimientos.length - 1 ? 4 : 0} align="flex-start">
                      <Flex direction="column" align="center" flexShrink={0} pt="3px">
                        <Box
                          w="10px" h="10px"
                          borderRadius="full"
                          bg="blue.400"
                          flexShrink={0}
                        />
                        {i < orden.seguimientos.length - 1 && (
                          <Box w="2px" flex="1" minH="24px" bg="blue.100" mt="2px" />
                        )}
                      </Flex>
                      <Box flex="1" pb={i < orden.seguimientos.length - 1 ? 2 : 0}>
                        <HStack mb={0.5} flexWrap="wrap">
                          <Text fontSize="xs" color={labelColor}>{fmtFecha(seg.fecha)}</Text>
                          <Badge colorScheme="blue" variant="subtle" fontSize="xs">
                            {seg.estado_reportado}
                          </Badge>
                          {seg.fecha_entrega_prometida && (
                            <Badge colorScheme="orange" variant="subtle" fontSize="xs">
                              Prometida: {fmtFecha(seg.fecha_entrega_prometida)}
                            </Badge>
                          )}
                        </HStack>
                        <Text fontSize="sm">{seg.notas}</Text>
                        <Text fontSize="xs" color={labelColor} mt={0.5}>
                          — {seg.registrado_por_nombre || 'usuario'}
                        </Text>
                      </Box>
                    </Flex>
                  ))}
                </VStack>
              )}
            </CardBody>
          </Card>
        </Box>

        {/* ── Columna derecha (35%) ── */}
        <Box w={{ base: '100%', lg: '340px' }} flexShrink={0}>

          {/* SLA y tiempo */}
          <Card bg={cardBg} borderColor={borderColor} border="1px solid" borderRadius="lg" shadow="sm" mb={4}>
            <CardHeader pb={2}><Heading size="sm" color="blue.600">SLA y Tiempo</Heading></CardHeader>
            <CardBody pt={0}>
              <Center mb={3}>
                <Box textAlign="center">
                  <Text
                    fontSize="5xl"
                    fontWeight="black"
                    lineHeight="1"
                    color={
                      orden.estado_sla === 'vencido' ? 'red.500'
                      : orden.estado_sla === 'critico' ? 'red.400'
                      : orden.estado_sla === 'alerta' ? 'orange.400'
                      : 'gray.700'
                    }
                  >
                    {orden.dias_transcurridos ?? '—'}
                  </Text>
                  <Text fontSize="xs" color={labelColor}>días transcurridos</Text>
                </Box>
              </Center>

              {/* Barra SLA */}
              {orden.dias_restantes_sla !== null && (
                <>
                  <Box mb={2}>
                    <Flex justify="space-between" mb={1}>
                      <Text fontSize="xs" color={labelColor}>Progreso SLA</Text>
                      <Text fontSize="xs" color={labelColor}>{orden.dias_sla ?? 30} días total</Text>
                    </Flex>
                    <Box h="8px" bg="gray.100" borderRadius="full" overflow="hidden">
                      <Box
                        h="100%"
                        w={`${Math.min(100, ((orden.dias_transcurridos ?? 0) / (orden.dias_sla ?? 30)) * 100)}%`}
                        bg={
                          orden.estado_sla === 'vencido' ? 'red.500'
                          : orden.estado_sla === 'critico' ? 'red.400'
                          : orden.estado_sla === 'alerta' ? 'orange.400'
                          : 'green.400'
                        }
                        borderRadius="full"
                        transition="width 0.3s"
                      />
                    </Box>
                  </Box>
                  <Flex justify="space-between" align="center">
                    <Badge
                      colorScheme={
                        orden.estado_sla === 'vencido' ? 'red'
                        : orden.estado_sla === 'critico' ? 'red'
                        : orden.estado_sla === 'alerta' ? 'orange'
                        : 'green'
                      }
                      fontSize="sm"
                      px={2}
                    >
                      {orden.estado_sla === 'vencido'
                        ? `Vencido hace ${Math.abs(orden.dias_restantes_sla)} días`
                        : `${orden.dias_restantes_sla} días restantes`}
                    </Badge>
                  </Flex>
                  {orden.fecha_entrega_estimada && (
                    <Text fontSize="xs" color={labelColor} mt={2}>
                      Vence el {fmtFecha(orden.fecha_entrega_estimada)}
                    </Text>
                  )}
                </>
              )}
            </CardBody>
          </Card>

          {/* Resumen financiero */}
          <Card bg={cardBg} borderColor={borderColor} border="1px solid" borderRadius="lg" shadow="sm" mb={4}>
            <CardHeader pb={2}><Heading size="sm" color="blue.600">Resumen Financiero</Heading></CardHeader>
            <CardBody pt={0}>
              <VStack align="stretch" spacing={3} fontSize="sm">
                <Flex justify="space-between">
                  <Text color={labelColor}>Costo proveedor (c/IGV)</Text>
                  <Text fontWeight="bold">{fmtMoney(totalCostoProv)}</Text>
                </Flex>
                <Flex justify="space-between">
                  <Text color={labelColor}>Precio cliente (s/IGV)</Text>
                  <Text fontWeight="bold">{fmtMoney(totalPrecioClient)}</Text>
                </Flex>
                <Divider />
                <Flex justify="space-between" align="center">
                  <Text color={labelColor} fontWeight="semibold">Margen total</Text>
                  <VStack align="flex-end" spacing={0}>
                    <Text
                      fontWeight="bold"
                      color={margenPct >= 30 ? 'green.600' : margenPct >= 15 ? 'orange.500' : 'red.500'}
                    >
                      {fmtMoney(totalMargen)}
                    </Text>
                    <Text
                      fontSize="xs"
                      fontWeight="bold"
                      color={margenPct >= 30 ? 'green.600' : margenPct >= 15 ? 'orange.500' : 'red.500'}
                    >
                      {margenPct.toFixed(1)}%
                    </Text>
                  </VStack>
                </Flex>
                <Box>
                  <Flex justify="space-between" mb={1}>
                    <Text fontSize="xs" color={labelColor}>vs. objetivo (40%)</Text>
                    <Text fontSize="xs" color={margenPct >= 40 ? 'green.600' : 'red.500'}>
                      {margenPct >= 40 ? '✓ Cumple' : `−${(40 - margenPct).toFixed(1)}%`}
                    </Text>
                  </Flex>
                  <Box h="4px" bg="gray.100" borderRadius="full">
                    <Box
                      h="100%"
                      w={`${Math.min(100, (margenPct / 40) * 100)}%`}
                      bg={margenPct >= 40 ? 'green.400' : margenPct >= 25 ? 'orange.400' : 'red.400'}
                      borderRadius="full"
                    />
                  </Box>
                </Box>
              </VStack>
            </CardBody>
          </Card>

          {/* Estado del proceso — timeline */}
          <Card bg={cardBg} borderColor={borderColor} border="1px solid" borderRadius="lg" shadow="sm" mb={4}>
            <CardHeader pb={2}><Heading size="sm" color="blue.600">Estado del Proceso</Heading></CardHeader>
            <CardBody pt={0}>
              <VStack align="stretch" spacing={0}>
                {TIMELINE_ESTADOS.map((e, i) => {
                  const done    = i <= timelineIdx && orden.estado !== 'cancelado';
                  const current = e === orden.estado;
                  const fecha   = (() => {
                    switch (e) {
                      case 'diagnostico_completado': return orden.fecha_diagnostico;
                      case 'cotizacion_enviada':     return orden.fecha_cotizacion_enviada;
                      case 'cotizacion_aprobada':    return orden.fecha_aprobacion;
                      case 'en_reparacion':          return orden.fecha_inicio_reparacion;
                      case 'entregado':              return orden.fecha_entrega_real;
                      default:                       return null;
                    }
                  })();

                  return (
                    <Flex key={e} align="flex-start" gap={3} pb={i < TIMELINE_ESTADOS.length - 1 ? 4 : 0}>
                      <Flex direction="column" align="center" flexShrink={0} pt="2px">
                        <Box
                          w="22px" h="22px"
                          borderRadius="full"
                          bg={current ? 'blue.500' : done ? 'blue.400' : 'gray.200'}
                          display="flex"
                          alignItems="center"
                          justifyContent="center"
                          border={current ? '2px solid var(--chakra-colors-blue-300)' : 'none'}
                          flexShrink={0}
                        >
                          {done && <FaCheck size={10} color="white" />}
                        </Box>
                        {i < TIMELINE_ESTADOS.length - 1 && (
                          <Box
                            w="2px"
                            h="24px"
                            bg={i < timelineIdx && orden.estado !== 'cancelado' ? 'blue.300' : 'gray.200'}
                            mt={1}
                          />
                        )}
                      </Flex>
                      <Box pt="1px" flex="1">
                        <Text
                          fontSize="sm"
                          fontWeight={current ? 'bold' : 'medium'}
                          color={done ? 'blue.600' : 'gray.400'}
                        >
                          {ESTADO_LABEL[e]}
                        </Text>
                        {fecha && (
                          <Text fontSize="xs" color={labelColor}>{fmtFecha(fecha)}</Text>
                        )}
                      </Box>
                    </Flex>
                  );
                })}
                {orden.estado === 'cancelado' && (
                  <Badge colorScheme="red" mt={2} alignSelf="flex-start">Cancelado</Badge>
                )}
              </VStack>

              {accionSig && (
                <>
                  <Divider my={4} />
                  <Stack spacing={2}>
                    <Button
                      size="sm"
                      w="full"
                      colorScheme="blue"
                      leftIcon={<FaExchangeAlt />}
                      isLoading={cambiandoEstado}
                      onClick={() => handleCambiarEstado(accionSig.estado)}
                    >
                      {accionSig.label}
                    </Button>
                    {orden.estado !== 'cancelado' && (
                      <Button
                        size="sm"
                        w="full"
                        colorScheme="red"
                        variant="ghost"
                        leftIcon={<FaExchangeAlt />}
                        isLoading={cambiandoEstado}
                        onClick={() => handleCambiarEstado('cancelado')}
                      >
                        Cancelar orden
                      </Button>
                    )}
                  </Stack>
                </>
              )}
            </CardBody>
          </Card>

          {/* Guía de remisión */}
          {orden.guia_remision && (
            <Card bg={cardBg} borderColor={borderColor} border="1px solid" borderRadius="lg" shadow="sm">
              <CardHeader pb={2}>
                <HStack>
                  <FaTruck size={13} color="var(--chakra-colors-blue-500)" />
                  <Heading size="sm" color="blue.600">Guía de Remisión</Heading>
                </HStack>
              </CardHeader>
              <CardBody pt={0}>
                <VStack align="stretch" spacing={2}>
                  <Text fontSize="sm" color={labelColor}>
                    Guía de entrada asociada a esta orden de servicio.
                  </Text>
                  <Button
                    size="sm"
                    w="full"
                    leftIcon={<FaTruck />}
                    colorScheme="blue"
                    variant="outline"
                    onClick={() => navigate(`/app/guias/${orden.guia_remision}`)}
                  >
                    Ver Guía
                  </Button>
                </VStack>
              </CardBody>
            </Card>
          )}
        </Box>
      </Flex>

      {/* Modal: Agregar seguimiento */}
      <Modal isOpen={isSeguimientoOpen} onClose={onSeguimientoClose} size="md">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader fontSize="md">Agregar Seguimiento del Proveedor</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel fontSize="sm">Estado reportado por proveedor</FormLabel>
                <Input
                  placeholder="Ej: En diagnóstico, Esperando repuestos..."
                  value={seguimientoData.estado_reportado}
                  onChange={(e) => setSeguimientoData(p => ({ ...p, estado_reportado: e.target.value }))}
                />
              </FormControl>
              <FormControl>
                <FormLabel fontSize="sm">Fecha entrega prometida</FormLabel>
                <Input
                  type="date"
                  value={seguimientoData.fecha_entrega_prometida}
                  onChange={(e) => setSeguimientoData(p => ({ ...p, fecha_entrega_prometida: e.target.value }))}
                />
              </FormControl>
              <FormControl isRequired>
                <FormLabel fontSize="sm">Notas</FormLabel>
                <Textarea
                  placeholder="Detalles del seguimiento..."
                  value={seguimientoData.notas}
                  onChange={(e) => setSeguimientoData(p => ({ ...p, notas: e.target.value }))}
                  rows={3}
                />
              </FormControl>
            </VStack>
          </ModalBody>
          <ModalFooter gap={2}>
            <Button variant="ghost" size="sm" onClick={onSeguimientoClose}>Cancelar</Button>
            <Button
              colorScheme="blue"
              size="sm"
              isLoading={guardandoSeg}
              onClick={handleAgregarSeguimiento}
            >
              Guardar seguimiento
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default OrdenServicioDetalle;
