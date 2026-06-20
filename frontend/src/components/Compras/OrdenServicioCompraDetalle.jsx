import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Button, Heading, Text, Flex, HStack, VStack, Badge,
  Table, Thead, Tbody, Tr, Th, Td, Grid, GridItem, Divider,
  useToast, Center, SimpleGrid, Stat, StatLabel, StatNumber,
} from '@chakra-ui/react';
import {
  FaArrowLeft, FaEdit, FaFilePdf, FaTools,
} from 'react-icons/fa';
import { useNavigate, useParams } from 'react-router-dom';
import comprasService from '../../services/compras.service';

const ESTADO_COLOR = {
  borrador: 'gray', enviada: 'blue', aprobada: 'teal', rechazada: 'red', completada: 'green',
};

const fmtFecha = (d) =>
  d ? new Date(d + 'T00:00:00').toLocaleDateString('es-PE', {
    day: '2-digit', month: 'long', year: 'numeric',
  }) : '—';

const InfoItem = ({ label, value }) => (
  <Box>
    <Text fontSize="xs" color="gray.500" textTransform="uppercase" letterSpacing="wide">{label}</Text>
    <Text fontSize="sm" fontWeight="medium">{value || '—'}</Text>
  </Box>
);

const OrdenServicioCompraDetalle = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [orden, setOrden] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exportando, setExportando] = useState(false);

  const cargar = useCallback(async () => {
    try {
      setLoading(true);
      const data = await comprasService.getOrdenServicio(id);
      setOrden(data);
    } catch (err) {
      toast({ title: 'Error al cargar la orden', description: err.message, status: 'error', duration: 4000 });
    } finally {
      setLoading(false);
    }
  }, [id, toast]);

  useEffect(() => { cargar(); }, [cargar]);

  const handleExportarPDF = async () => {
    try {
      setExportando(true);
      await comprasService.exportarPDFOrdenServicio(orden);
    } catch (err) {
      toast({ title: 'Error al exportar PDF', description: err.message, status: 'error', duration: 4000 });
    } finally {
      setExportando(false);
    }
  };

  if (loading) {
    return <Center py={20}><Text color="gray.400">Cargando orden...</Text></Center>;
  }
  if (!orden) {
    return (
      <Center py={20} flexDir="column" gap={3}>
        <Text color="gray.400">No se encontró la orden</Text>
        <Button onClick={() => navigate('/app/compras/ordenes-servicio')}>Volver</Button>
      </Center>
    );
  }

  const sym = orden.moneda === 'PEN' ? 'S/' : '$';
  const fmtMoney = (v) => `${sym} ${Number(v || 0).toLocaleString('es-PE', { minimumFractionDigits: 2 })}`;

  return (
    <Box p={6}>
      {/* Header */}
      <Flex justify="space-between" align="flex-start" mb={6} wrap="wrap" gap={3}>
        <HStack spacing={3} align="flex-start">
          <Box p={2} bg="purple.50" borderRadius="lg" mt={1}>
            <FaTools size={20} color="var(--chakra-colors-purple-500)" />
          </Box>
          <VStack align="flex-start" spacing={1}>
            <HStack>
              <Heading size="lg" fontFamily="mono">OCS-{orden.numero}</Heading>
              <Badge colorScheme={ESTADO_COLOR[orden.estado] || 'gray'} borderRadius="full" px={2}>
                {orden.estado_display || orden.estado}
              </Badge>
            </HStack>
            <Text fontSize="sm" color="gray.500">Orden de Compra de Servicio · {orden.proveedor_nombre}</Text>
          </VStack>
        </HStack>
        <HStack spacing={2}>
          <Button leftIcon={<FaArrowLeft />} variant="ghost" onClick={() => navigate('/app/compras/ordenes-servicio')}>
            Volver
          </Button>
          <Button leftIcon={<FaEdit />} variant="outline" colorScheme="purple"
            onClick={() => navigate(`/app/compras/ordenes-servicio/${orden.id}/editar`)}>
            Editar
          </Button>
          <Button leftIcon={<FaFilePdf />} colorScheme="red" isLoading={exportando} onClick={handleExportarPDF}>
            PDF
          </Button>
        </HStack>
      </Flex>

      <VStack spacing={5} align="stretch">
        {/* Datos generales */}
        <Box bg="white" p={6} borderRadius="lg" shadow="sm">
          <Heading size="md" mb={4}>Datos de la Orden</Heading>
          <Grid templateColumns={{ base: '1fr 1fr', md: 'repeat(4, 1fr)' }} gap={4}>
            <InfoItem label="Proveedor" value={orden.proveedor_nombre} />
            <InfoItem label="RUC" value={orden.proveedor_info?.ruc} />
            <InfoItem label="Contacto" value={orden.contacto_nombre} />
            <InfoItem label="Email" value={orden.contacto_email} />
            <InfoItem label="Fecha Emisión" value={fmtFecha(orden.fecha_emision)} />
            <InfoItem label="Fecha Entrega" value={fmtFecha(orden.fecha_entrega)} />
            <InfoItem label="Forma de Pago" value={orden.forma_pago} />
            <InfoItem label="Moneda" value={orden.moneda === 'PEN' ? 'Soles' : 'Dólares'} />
            {orden.referencia && <InfoItem label="Referencia" value={orden.referencia} />}
          </Grid>
        </Box>

        {/* Equipos */}
        <Box bg="white" p={6} borderRadius="lg" shadow="sm">
          <Heading size="md" mb={4}>Equipos / Trabajos ({orden.items?.length || 0})</Heading>
          <Box overflowX="auto">
            <Table size="sm" variant="simple">
              <Thead bg="gray.50">
                <Tr>
                  <Th>N°</Th>
                  <Th>N° Serie</Th>
                  <Th>Modelo</Th>
                  <Th>Marca</Th>
                  <Th>Trabajo</Th>
                  <Th isNumeric>Cant.</Th>
                  <Th isNumeric>Costo</Th>
                  <Th isNumeric>Importe</Th>
                </Tr>
              </Thead>
              <Tbody>
                {(orden.items || []).map((it, i) => (
                  <Tr key={it.id || i}>
                    <Td>{it.numero_item || i + 1}</Td>
                    <Td fontFamily="mono" fontSize="xs">{it.numero_serie || '—'}</Td>
                    <Td fontSize="sm">{it.modelo || '—'}</Td>
                    <Td fontSize="sm">{it.marca || '—'}</Td>
                    <Td fontSize="sm" maxW="280px"><Text whiteSpace="pre-wrap">{it.trabajo || '—'}</Text></Td>
                    <Td isNumeric>{Number(it.cantidad || 0)}</Td>
                    <Td isNumeric>{fmtMoney(it.costo_unitario)}</Td>
                    <Td isNumeric fontWeight="medium">{fmtMoney(it.importe)}</Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Box>

          {/* Totales */}
          <Flex justify="flex-end" mt={4}>
            <Box minW="280px">
              <Grid templateColumns="1fr auto" gap={2} alignItems="center">
                <Text color="gray.600">Subtotal:</Text>
                <Text textAlign="right">{fmtMoney(orden.subtotal)}</Text>
                <Text color="gray.600">IGV ({Number(orden.porcentaje_igv)}%):</Text>
                <Text textAlign="right">{fmtMoney(orden.igv)}</Text>
                <Divider gridColumn="1 / -1" my={1} />
                <Text fontSize="lg" fontWeight="bold" color="purple.600">TOTAL:</Text>
                <Text fontSize="lg" fontWeight="bold" color="purple.600" textAlign="right">{fmtMoney(orden.total)}</Text>
              </Grid>
            </Box>
          </Flex>
        </Box>

        {/* Notas */}
        {orden.notas && (
          <Box bg="white" p={6} borderRadius="lg" shadow="sm">
            <Heading size="md" mb={3}>Notas / Observaciones</Heading>
            <Text fontSize="sm" whiteSpace="pre-wrap" color="gray.700">{orden.notas}</Text>
          </Box>
        )}
      </VStack>
    </Box>
  );
};

export default OrdenServicioCompraDetalle;
