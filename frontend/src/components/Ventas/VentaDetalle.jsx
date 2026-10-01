import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box, Card, CardBody, Heading, VStack, HStack, Text, Table, Thead, Tbody, Tr, Th, Td,
  Spinner, Button, Flex, Badge, Divider, Tooltip, useToast, Textarea,
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter, ModalCloseButton,
  useDisclosure, Link, Circle,
} from '@chakra-ui/react';
import { ventasService } from '../../services/ventas.service';
import { getSimboloMoneda } from '../../utils/currency';
import {
  ESTADOS_OPERATIVOS, ESTADO_OPERATIVO_LABEL, SIGUIENTE_ESTADO, VERBO_SIGUIENTE,
  SLA_COLOR_SCHEME, SLA_LABEL, estadoAnterior,
} from './estadoOperativo';

const COLOR_PRIMARIO = '#2B5EA7';

const VentaDetalle = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [venta, setVenta] = useState(null);
  const [detalles, setDetalles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notaRetroceso, setNotaRetroceso] = useState('');
  const { isOpen, onOpen, onClose } = useDisclosure();

  const cargar = useCallback(async () => {
    try {
      const data = await ventasService.getVenta(id);
      setVenta(data);
      setDetalles(data.detalles || []);
    } catch {
      setVenta(null);
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => { cargar(); }, [cargar]);

  const cambiar = async (nuevoEstado, nota = '') => {
    setSaving(true);
    try {
      await ventasService.cambiarEstadoOperativo(id, nuevoEstado, nota);
      await cargar();
      toast({ title: `Estado: ${ESTADO_OPERATIVO_LABEL[nuevoEstado]}`, status: 'success', duration: 2500 });
    } catch (e) {
      toast({ title: 'No se pudo cambiar', description: e.response?.data?.detail || e.message, status: 'error', duration: 5000, isClosable: true });
    } finally {
      setSaving(false);
    }
  };

  const confirmarRetroceso = async () => {
    const prev = estadoAnterior(venta.estado_operativo);
    onClose();
    await cambiar(prev, notaRetroceso);
    setNotaRetroceso('');
  };

  if (isLoading) return <Spinner size="xl" />;
  if (!venta) return <Text>No se encontró la venta.</Text>;

  const simboloMoneda = getSimboloMoneda(venta.moneda);
  const actual = venta.estado_operativo;
  const idxActual = ESTADOS_OPERATIVOS.indexOf(actual);
  const siguiente = SIGUIENTE_ESTADO[actual];
  const prev = estadoAnterior(actual);
  const slaColor = SLA_COLOR_SCHEME[venta.estado_sla_operativo || 'sin_sla'];
  const ocs = venta.ordenes_compra || [];
  const historial = venta.historial_operativo || [];

  return (
    <Box maxW="container.lg" mx="auto" py={8}>
      <VStack spacing={6} align="stretch">
        {/* ── Timeline operativo ── */}
        <Card>
          <CardBody>
            <Flex justify="space-between" align="center" mb={5} wrap="wrap" gap={3}>
              <Heading size="md" color={COLOR_PRIMARIO}>Estado operativo</Heading>
              <HStack>
                <Tooltip label={`${venta.dias_en_estado_operativo ?? 0} día(s) en este estado`} hasArrow>
                  <Badge colorScheme={slaColor} variant="subtle" px={2} py={1}>
                    {SLA_LABEL[venta.estado_sla_operativo || 'sin_sla']}
                  </Badge>
                </Tooltip>
                {prev && actual !== 'cobrado' && (
                  <Button size="sm" variant="outline" onClick={onOpen} isDisabled={saving}>
                    Retroceder
                  </Button>
                )}
                {siguiente && (
                  <Button size="sm" colorScheme="blue" onClick={() => cambiar(siguiente)} isLoading={saving}>
                    {VERBO_SIGUIENTE[actual]}
                  </Button>
                )}
              </HStack>
            </Flex>

            {/* Stepper horizontal */}
            <Flex align="flex-start" justify="space-between" overflowX="auto" pb={2}>
              {ESTADOS_OPERATIVOS.map((e, i) => {
                const hecho = i < idxActual;
                const esActual = i === idxActual;
                return (
                  <React.Fragment key={e}>
                    <VStack spacing={1} minW="80px" flex="0 0 auto">
                      <Circle
                        size="28px"
                        bg={esActual ? COLOR_PRIMARIO : hecho ? 'green.400' : 'gray.200'}
                        color={esActual || hecho ? 'white' : 'gray.500'}
                        fontSize="xs" fontWeight="bold"
                      >
                        {hecho ? '✓' : i + 1}
                      </Circle>
                      <Text fontSize="xs" textAlign="center"
                        color={esActual ? COLOR_PRIMARIO : 'gray.500'}
                        fontWeight={esActual ? 'bold' : 'normal'}>
                        {ESTADO_OPERATIVO_LABEL[e]}
                      </Text>
                    </VStack>
                    {i < ESTADOS_OPERATIVOS.length - 1 && (
                      <Box flex="1" h="2px" bg={i < idxActual ? 'green.400' : 'gray.200'} mt="13px" minW="16px" />
                    )}
                  </React.Fragment>
                );
              })}
            </Flex>
          </CardBody>
        </Card>

        {/* ── Datos de la venta ── */}
        <Card>
          <CardBody>
            <Heading size="md" mb={4}>Detalle de Venta</Heading>
            <HStack align="start" spacing={10} wrap="wrap">
              <VStack align="start" spacing={1}>
                <Text><b>Número:</b> {venta.numero}</Text>
                <Text><b>Cliente:</b> {venta.cliente_nombre}</Text>
                <Text><b>Fecha de Emisión:</b> {venta.fecha_emision}</Text>
              </VStack>
              <VStack align="start" spacing={1}>
                <Text><b>Estado de pago:</b> <Badge colorScheme="blue">{venta.estado}</Badge></Text>
                <Text><b>Subtotal:</b> {simboloMoneda} {venta.subtotal}</Text>
                <Text><b>Total:</b> <b>{simboloMoneda} {venta.total}</b></Text>
              </VStack>
            </HStack>

            <Heading size="sm" mt={5} mb={2}>Productos</Heading>
            <Table size="sm" variant="simple">
              <Thead>
                <Tr>
                  <Th>Producto</Th><Th>Origen</Th><Th isNumeric>Cantidad</Th>
                  <Th isNumeric>P. Unitario</Th><Th isNumeric>Subtotal</Th>
                </Tr>
              </Thead>
              <Tbody>
                {detalles.length === 0 ? (
                  <Tr><Td colSpan={5}>Sin productos</Td></Tr>
                ) : detalles.map((d, i) => (
                  <Tr key={d.id || i}>
                    <Td>{d.producto_nombre || d.descripcion || '—'}</Td>
                    <Td>
                      {d.origen === 'stock' ? (
                        <Badge colorScheme="purple" variant="subtle">Stock</Badge>
                      ) : (
                        <Badge colorScheme="blue" variant="subtle">A pedido</Badge>
                      )}
                    </Td>
                    <Td isNumeric>{d.cantidad}</Td>
                    <Td isNumeric>{simboloMoneda} {d.precio_unitario}</Td>
                    <Td isNumeric>{simboloMoneda} {(d.cantidad * d.precio_unitario).toFixed(2)}</Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </CardBody>
        </Card>

        {/* ── OCs vinculadas + Historial ── */}
        <HStack align="stretch" spacing={6} wrap={{ base: 'wrap', md: 'nowrap' }}>
          <Card flex="1" minW="280px">
            <CardBody>
              <Heading size="sm" mb={3}>Órdenes de compra vinculadas</Heading>
              {ocs.length === 0 ? (
                <Text fontSize="sm" color="gray.500">Ninguna.</Text>
              ) : (
                <VStack align="stretch" spacing={2}>
                  {ocs.map((oc) => (
                    <HStack key={oc.id} justify="space-between" p={2} bg="gray.50" borderRadius="md">
                      <Link color={COLOR_PRIMARIO} fontWeight="bold" onClick={() => navigate('/app/compras')}>
                        OC-{oc.numero}
                      </Link>
                      <Text fontSize="sm" noOfLines={1}>{oc.proveedor}</Text>
                      <Badge>{oc.estado}</Badge>
                    </HStack>
                  ))}
                </VStack>
              )}
            </CardBody>
          </Card>

          <Card flex="1" minW="280px">
            <CardBody>
              <Heading size="sm" mb={3}>Historial operativo</Heading>
              {historial.length === 0 ? (
                <Text fontSize="sm" color="gray.500">Sin movimientos.</Text>
              ) : (
                <VStack align="stretch" spacing={0}>
                  {historial.map((h, i) => (
                    <Box key={i} pl={4} borderLeft="2px solid" borderColor="gray.200" pb={3} position="relative">
                      <Circle size="10px" bg={COLOR_PRIMARIO} position="absolute" left="-6px" top="4px" />
                      <Text fontSize="sm" fontWeight="medium">
                        {ESTADO_OPERATIVO_LABEL[h.estado_nuevo] || h.estado_nuevo}
                      </Text>
                      <Text fontSize="xs" color="gray.500">
                        {h.fecha ? new Date(h.fecha).toLocaleString('es-PE') : ''} · {h.usuario || 'sistema'}
                      </Text>
                      {h.nota ? <Text fontSize="xs" color="gray.600">{h.nota}</Text> : null}
                    </Box>
                  ))}
                </VStack>
              )}
            </CardBody>
          </Card>
        </HStack>

        <Flex justify="flex-end">
          <Button onClick={() => navigate('/app/ventas')}>Volver</Button>
        </Flex>
      </VStack>

      {/* Modal retroceder (pide nota) */}
      <Modal isOpen={isOpen} onClose={onClose} isCentered>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Retroceder estado</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <Text fontSize="sm" mb={2}>
              Volver a <b>{ESTADO_OPERATIVO_LABEL[estadoAnterior(actual)]}</b>. Indica el motivo:
            </Text>
            <Textarea value={notaRetroceso} onChange={(e) => setNotaRetroceso(e.target.value)}
              placeholder="Motivo del retroceso" rows={3} />
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose}>Cancelar</Button>
            <Button colorScheme="blue" onClick={confirmarRetroceso} isDisabled={!notaRetroceso.trim()}>
              Retroceder
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default VentaDetalle;
