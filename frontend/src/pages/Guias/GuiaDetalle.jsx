import React, { useState, useEffect } from 'react';
import {
  Box, Flex, Heading, Text, Badge, Button, VStack, HStack,
  Divider, Table, Thead, Tbody, Tr, Th, Td, Card, CardBody,
  CardHeader, Spinner, Center, useToast, useColorModeValue,
  Menu, MenuButton, MenuList, MenuItem, IconButton, SimpleGrid,
  Stat, StatLabel, StatNumber, Alert, AlertIcon, Stack,
} from '@chakra-ui/react';
import {
  FaArrowLeft, FaEdit, FaFilePdf, FaExchangeAlt, FaEllipsisV,
  FaTruck, FaMapMarkerAlt, FaCalendar, FaUser, FaCheck,
} from 'react-icons/fa';
import { useParams, useNavigate } from 'react-router-dom';
import guiasService from '../../services/guiasService';

const ESTADO_COLOR = {
  borrador:   'gray',
  emitida:    'blue',
  en_proceso: 'orange',
  entregada:  'green',
  cancelada:  'red',
};

const MOTIVO_LABEL = {
  ingreso_reparacion: 'Ingreso por Reparación',
  devolucion_cliente: 'Devolución a Cliente',
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

const TIMELINE = ['borrador', 'emitida', 'en_proceso', 'entregada'];

const fmtFecha = (d) => d ? new Date(d).toLocaleDateString('es-PE', { day: '2-digit', month: 'short', year: 'numeric' }) : '—';

const GuiaDetalle = () => {
  const { id }   = useParams();
  const navigate = useNavigate();
  const toast    = useToast();
  const [guia, setGuia]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  const cardBg     = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const labelColor  = useColorModeValue('gray.500', 'gray.400');

  useEffect(() => { cargar(); }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const cargar = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await guiasService.getById(id);
      setGuia(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'No se pudo cargar la guía');
      toast({ title: 'Error', description: err.message, status: 'error', duration: 4000, isClosable: true });
    } finally {
      setLoading(false);
    }
  };

  const handlePDF = async () => {
    try {
      await guiasService.exportarPDF(guia.id, guia.numero);
      toast({ title: 'PDF descargado', status: 'success', duration: 2500, isClosable: true });
    } catch (err) {
      toast({ title: 'Error al generar PDF', description: err.message, status: 'error', duration: 4000, isClosable: true });
    }
  };

  const handleCambiarEstado = async (estado) => {
    try {
      await guiasService.cambiarEstado(guia.id, estado);
      toast({ title: 'Estado actualizado', description: `Guía ${guia.numero} → ${estado}`, status: 'success', duration: 2500, isClosable: true });
      cargar();
    } catch (err) {
      toast({ title: 'Error', description: err.response?.data?.error || err.message, status: 'error', duration: 4000, isClosable: true });
    }
  };

  if (loading) return <Center py={24}><Spinner size="xl" color="blue.500" /></Center>;
  if (error)   return <Center py={16}><Alert status="error" maxW="400px" borderRadius="lg"><AlertIcon />{error}</Alert></Center>;
  if (!guia)   return null;

  const sigEstados = ESTADOS_SIGUIENTES[guia.estado] || [];
  const timelineIdx = TIMELINE.indexOf(guia.estado);

  return (
    <Box p={6} maxW="1200px" mx="auto">
      {/* Barra superior */}
      <Flex justify="space-between" align="center" mb={6}>
        <HStack spacing={3}>
          <IconButton icon={<FaArrowLeft />} variant="ghost" size="sm" onClick={() => navigate('/app/guias')} aria-label="Volver" />
          <Box>
            <Heading size="md">{guia.numero}</Heading>
            <Text fontSize="sm" color={labelColor}>{MOTIVO_LABEL[guia.motivo] || guia.motivo}</Text>
          </Box>
          <Badge colorScheme={ESTADO_COLOR[guia.estado]} borderRadius="full" px={3} py={1} fontSize="sm">
            {guia.estado?.replace('_', ' ').toUpperCase()}
          </Badge>
        </HStack>
        <HStack spacing={2}>
          <Button leftIcon={<FaFilePdf />} colorScheme="red" variant="outline" size="sm" onClick={handlePDF}>
            Descargar PDF
          </Button>
          {guia.estado === 'borrador' && (
            <Button leftIcon={<FaEdit />} colorScheme="blue" size="sm" onClick={() => navigate(`/app/guias/${guia.id}/editar`)}>
              Editar
            </Button>
          )}
          {sigEstados.length > 0 && (
            <Menu>
              <MenuButton as={Button} rightIcon={<FaEllipsisV />} size="sm" variant="outline">
                Cambiar Estado
              </MenuButton>
              <MenuList fontSize="sm">
                {sigEstados.map((e) => (
                  <MenuItem key={e} icon={<FaExchangeAlt />} onClick={() => handleCambiarEstado(e)}>
                    Pasar a: <b style={{ marginLeft: 4 }}>{e.replace('_', ' ')}</b>
                  </MenuItem>
                ))}
              </MenuList>
            </Menu>
          )}
        </HStack>
      </Flex>

      {/* Layout 65/35 */}
      <Flex gap={5} align="flex-start" direction={{ base: 'column', lg: 'row' }}>

        {/* ── Columna izquierda (65%) ── */}
        <Box flex="1" minW={0}>

          {/* Info guía */}
          <Card bg={cardBg} borderColor={borderColor} border="1px solid" borderRadius="lg" mb={4} shadow="sm">
            <CardHeader pb={2}>
              <Heading size="sm" color="blue.600">Información de la Guía</Heading>
            </CardHeader>
            <CardBody pt={0}>
              <SimpleGrid columns={{ base: 1, sm: 3 }} spacing={4}>
                <Stat>
                  <StatLabel color={labelColor} fontSize="xs">Fecha Emisión</StatLabel>
                  <StatNumber fontSize="md">{fmtFecha(guia.fecha_emision)}</StatNumber>
                </Stat>
                <Stat>
                  <StatLabel color={labelColor} fontSize="xs">Fecha Traslado</StatLabel>
                  <StatNumber fontSize="md">{fmtFecha(guia.fecha_traslado)}</StatNumber>
                </Stat>
                <Stat>
                  <StatLabel color={labelColor} fontSize="xs">Motivo</StatLabel>
                  <StatNumber fontSize="sm">{MOTIVO_LABEL[guia.motivo] || guia.motivo}</StatNumber>
                </Stat>
              </SimpleGrid>
            </CardBody>
          </Card>

          {/* Cliente / Destinatario */}
          <Card bg={cardBg} borderColor={borderColor} border="1px solid" borderRadius="lg" mb={4} shadow="sm">
            <CardHeader pb={2}>
              <HStack>
                <FaUser size={13} color="var(--chakra-colors-blue-500)" />
                <Heading size="sm" color="blue.600">Destinatario</Heading>
              </HStack>
            </CardHeader>
            <CardBody pt={0}>
              <SimpleGrid columns={{ base: 1, sm: 2 }} spacing={4} mb={4}>
                <Box>
                  <Text fontSize="xs" color={labelColor} mb={0.5}>Nombre</Text>
                  <Text fontWeight="semibold">{guia.nombre_destinatario}</Text>
                </Box>
                {guia.ruc_destinatario && (
                  <Box>
                    <Text fontSize="xs" color={labelColor} mb={0.5}>RUC</Text>
                    <Text fontWeight="semibold">{guia.ruc_destinatario}</Text>
                  </Box>
                )}
              </SimpleGrid>
              <Divider mb={4} />
              <SimpleGrid columns={{ base: 1, sm: 2 }} spacing={4}>
                <Box>
                  <HStack mb={1} spacing={1}>
                    <FaMapMarkerAlt size={11} color="var(--chakra-colors-green-500)" />
                    <Text fontSize="xs" color={labelColor}>Punto de Partida</Text>
                  </HStack>
                  <Text fontSize="sm">{guia.direccion_origen}</Text>
                </Box>
                <Box>
                  <HStack mb={1} spacing={1}>
                    <FaMapMarkerAlt size={11} color="var(--chakra-colors-red-500)" />
                    <Text fontSize="xs" color={labelColor}>Punto de Llegada</Text>
                  </HStack>
                  <Text fontSize="sm">{guia.direccion_destino}</Text>
                </Box>
              </SimpleGrid>
            </CardBody>
          </Card>

          {/* Tabla de equipos */}
          <Card bg={cardBg} borderColor={borderColor} border="1px solid" borderRadius="lg" shadow="sm" mb={4}>
            <CardHeader pb={2}>
              <Flex justify="space-between" align="center">
                <HStack>
                  <FaTruck size={13} color="var(--chakra-colors-blue-500)" />
                  <Heading size="sm" color="blue.600">Equipos / Artículos</Heading>
                </HStack>
                <Badge colorScheme="purple" variant="subtle">{guia.items?.length ?? 0} ítem(s)</Badge>
              </Flex>
            </CardHeader>
            <CardBody pt={0}>
              {guia.items?.length === 0 ? (
                <Center py={6}><Text color="gray.400" fontSize="sm">Sin ítems registrados</Text></Center>
              ) : (
                <Box overflowX="auto">
                  <Table size="sm" variant="simple">
                    <Thead bg="blue.50">
                      <Tr>
                        <Th w="36px">#</Th>
                        <Th>N° Serie</Th>
                        <Th>Modelo</Th>
                        <Th>Marca</Th>
                        <Th>Falla / Estado Ingreso</Th>
                        <Th isNumeric>Cant.</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {(guia.items || []).map((item, i) => (
                        <Tr key={item.id} bg={i % 2 === 1 ? 'gray.50' : undefined}>
                          <Td color="gray.400">{item.numero_item}</Td>
                          <Td><Text fontFamily="mono" fontSize="xs">{item.serie || '—'}</Text></Td>
                          <Td>{item.modelo || '—'}</Td>
                          <Td>{item.marca || '—'}</Td>
                          <Td maxW="260px">
                            <Text fontSize="xs" noOfLines={2}>{item.estado_ingreso || item.descripcion}</Text>
                          </Td>
                          <Td isNumeric fontWeight="semibold">{item.cantidad}</Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                </Box>
              )}
            </CardBody>
          </Card>

          {/* Observaciones */}
          {guia.observaciones && (
            <Card bg={cardBg} borderColor={borderColor} border="1px solid" borderRadius="lg" shadow="sm">
              <CardHeader pb={2}><Heading size="sm" color="blue.600">Observaciones</Heading></CardHeader>
              <CardBody pt={0}>
                <Text fontSize="sm" whiteSpace="pre-wrap" color={labelColor}>{guia.observaciones}</Text>
              </CardBody>
            </Card>
          )}
        </Box>

        {/* ── Columna derecha (35%) ── */}
        <Box w={{ base: '100%', lg: '340px' }} flexShrink={0}>

          {/* Resumen */}
          <Card bg={cardBg} borderColor={borderColor} border="1px solid" borderRadius="lg" shadow="sm" mb={4}>
            <CardHeader pb={2}><Heading size="sm" color="blue.600">Resumen</Heading></CardHeader>
            <CardBody pt={0}>
              <VStack align="stretch" spacing={3} fontSize="sm">
                <Flex justify="space-between">
                  <Text color={labelColor}>Total equipos</Text>
                  <Text fontWeight="bold">{guia.items?.length ?? 0}</Text>
                </Flex>
                <Flex justify="space-between">
                  <Text color={labelColor}>Unidades totales</Text>
                  <Text fontWeight="bold">{(guia.items || []).reduce((acc, i) => acc + (i.cantidad || 1), 0)}</Text>
                </Flex>
                <Divider />
                <Flex justify="space-between">
                  <Text color={labelColor}>Creado por</Text>
                  <Text>{guia.creado_por_nombre || '—'}</Text>
                </Flex>
              </VStack>
            </CardBody>
          </Card>

          {/* PDF */}
          <Card bg={cardBg} borderColor={borderColor} border="1px solid" borderRadius="lg" shadow="sm" mb={4}>
            <CardBody>
              <Button w="full" leftIcon={<FaFilePdf />} colorScheme="red" onClick={handlePDF}>
                Descargar PDF
              </Button>
              <Text fontSize="xs" color={labelColor} mt={2} textAlign="center">
                Guía de Remisión Interna — documento de control
              </Text>
            </CardBody>
          </Card>

          {/* Estado + Timeline */}
          <Card bg={cardBg} borderColor={borderColor} border="1px solid" borderRadius="lg" shadow="sm">
            <CardHeader pb={2}><Heading size="sm" color="blue.600">Estado del Proceso</Heading></CardHeader>
            <CardBody pt={0}>
              <VStack align="stretch" spacing={0}>
                {TIMELINE.map((e, i) => {
                  const done    = i <= timelineIdx && guia.estado !== 'cancelada';
                  const current = e === guia.estado;
                  return (
                    <Flex key={e} align="flex-start" gap={3} pb={i < TIMELINE.length - 1 ? 4 : 0}>
                      <Flex direction="column" align="center" flexShrink={0} pt="2px">
                        <Box
                          w="22px" h="22px"
                          borderRadius="full"
                          bg={done ? 'blue.500' : 'gray.200'}
                          display="flex" alignItems="center" justifyContent="center"
                          border={current ? '2px solid var(--chakra-colors-blue-400)' : 'none'}
                        >
                          {done && <FaCheck size={10} color="white" />}
                        </Box>
                        {i < TIMELINE.length - 1 && (
                          <Box w="2px" h="24px" bg={i < timelineIdx && guia.estado !== 'cancelada' ? 'blue.400' : 'gray.200'} mt={1} />
                        )}
                      </Flex>
                      <Box pt="1px">
                        <Text fontSize="sm" fontWeight={current ? 'bold' : 'medium'} color={done ? 'blue.600' : 'gray.400'}>
                          {e.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </Text>
                      </Box>
                    </Flex>
                  );
                })}
                {guia.estado === 'cancelada' && (
                  <Badge colorScheme="red" mt={2} alignSelf="flex-start">Cancelada</Badge>
                )}
              </VStack>

              {sigEstados.length > 0 && (
                <>
                  <Divider my={4} />
                  <Stack spacing={2}>
                    {sigEstados.map((e) => (
                      <Button
                        key={e}
                        size="sm"
                        w="full"
                        colorScheme={e === 'cancelada' ? 'red' : 'blue'}
                        variant={e === 'cancelada' ? 'ghost' : 'solid'}
                        leftIcon={<FaExchangeAlt />}
                        onClick={() => handleCambiarEstado(e)}
                      >
                        Pasar a: {e.replace('_', ' ')}
                      </Button>
                    ))}
                  </Stack>
                </>
              )}
            </CardBody>
          </Card>
        </Box>
      </Flex>
    </Box>
  );
};

export default GuiaDetalle;
