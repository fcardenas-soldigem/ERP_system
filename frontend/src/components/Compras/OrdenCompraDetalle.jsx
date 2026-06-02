import React, { useState } from 'react';
import {
  Box, Card, CardBody, CardHeader, Heading, Text, Badge,
  Button, Flex, HStack, VStack, Divider, Spinner, Center,
  useToast, Stat, StatLabel, StatNumber, StatHelpText,
  Menu, MenuButton, MenuList, MenuItem, IconButton,
  Alert, AlertIcon, SimpleGrid, useColorModeValue,
  Breadcrumb, BreadcrumbItem, BreadcrumbLink,
} from '@chakra-ui/react';
import {
  FaArrowLeft, FaEdit, FaFilePdf, FaEllipsisV,
  FaBuilding, FaCalendarAlt, FaFileAlt, FaCheck, FaTimes,
  FaPaperPlane, FaBoxOpen, FaChevronRight,
} from 'react-icons/fa';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { comprasService } from '../../services/compras.service';

const ESTADO_CONFIG = {
  borrador:   { label: 'Borrador',   color: 'gray',  icon: FaFileAlt   },
  enviada:    { label: 'Enviada',    color: 'blue',  icon: FaPaperPlane },
  aprobada:   { label: 'Aprobada',   color: 'green', icon: FaCheck      },
  rechazada:  { label: 'Rechazada',  color: 'red',   icon: FaTimes      },
  completada: { label: 'Completada', color: 'teal',  icon: FaBoxOpen    },
};

const TRANSICIONES = {
  borrador:   ['enviada', 'aprobada'],
  enviada:    ['aprobada', 'rechazada'],
  aprobada:   ['completada', 'rechazada'],
  rechazada:  [],
  completada: [],
};

const TRANSICION_LABELS = {
  enviada:    'Enviar a Proveedor',
  aprobada:   'Marcar como Aprobada',
  rechazada:  'Cancelar / Rechazar',
  completada: 'Marcar como Completada',
};

const ESTADO_KEY = (raw) => {
  if (!raw) return 'borrador';
  return raw.toLowerCase();
};

const formatCurrency = (amount) => {
  const n = parseFloat(amount) || 0;
  return new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(n);
};

const formatDate = (d, opts = {}) => {
  if (!d) return '—';
  try {
    return new Date(d).toLocaleDateString('es-PE', {
      year: 'numeric', month: 'long', day: 'numeric', ...opts,
    });
  } catch { return d; }
};

const InfoRow = ({ label, value, children }) => (
  <Box>
    <Text fontSize="xs" color="gray.500" fontWeight="medium" mb={0.5}>{label}</Text>
    {children ?? <Text fontSize="sm" color="gray.800">{value || '—'}</Text>}
  </Box>
);

const OrdenCompraDetalle = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  const { data: orden, isLoading, error } = useQuery({
    queryKey: ['orden-compra', id],
    queryFn: () => comprasService.getOrden(id),
    staleTime: 30_000,
  });

  const cambiarEstadoMutation = useMutation({
    mutationFn: (estado) => comprasService.cambiarEstadoOrden(id, estado),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orden-compra', id] });
      queryClient.invalidateQueries({ queryKey: ['ordenes-compra'] });
      toast({ title: 'Estado actualizado', status: 'success', duration: 3000 });
    },
    onError: (err) => toast({
      title: 'Error', description: err.response?.data?.error ?? err.message,
      status: 'error', duration: 5000,
    }),
  });

  const handleExportarPDF = async () => {
    try {
      await comprasService.exportarPDFOrden(orden);
      toast({ title: 'PDF descargado', status: 'success', duration: 3000 });
    } catch (err) {
      toast({ title: 'Error al generar PDF', description: err.message, status: 'error', duration: 5000 });
    }
  };

  if (isLoading) {
    return <Center py={20}><Spinner size="xl" color="blue.500" thickness="4px" /></Center>;
  }

  if (error) {
    return (
      <Box p={6}>
        <Alert status="error" borderRadius="lg"><AlertIcon />{error.message}</Alert>
        <Button mt={4} leftIcon={<FaArrowLeft />} onClick={() => navigate('/app/compras/ordenes')}>
          Volver
        </Button>
      </Box>
    );
  }

  if (!orden) {
    return (
      <Box p={6}>
        <Alert status="warning" borderRadius="lg"><AlertIcon />Orden no encontrada</Alert>
        <Button mt={4} leftIcon={<FaArrowLeft />} onClick={() => navigate('/app/compras/ordenes')}>
          Volver
        </Button>
      </Box>
    );
  }

  const estadoKey = ESTADO_KEY(orden.estado);
  const estadoCfg = ESTADO_CONFIG[estadoKey] ?? { label: orden.estado, color: 'gray' };
  const transiciones = TRANSICIONES[estadoKey] ?? [];

  return (
    <Box p={6}>
      {/* Breadcrumb */}
      <Breadcrumb mb={4} spacing="8px" separator={<FaChevronRight size={10} color="gray" />}>
        <BreadcrumbItem>
          <BreadcrumbLink as={RouterLink} to="/app/compras" color="gray.500" fontSize="sm">Compras</BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbItem>
          <BreadcrumbLink as={RouterLink} to="/app/compras/ordenes" color="gray.500" fontSize="sm">Órdenes de Compra</BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbItem isCurrentPage>
          <Text fontSize="sm" color="gray.700">OC-{orden.numero || id}</Text>
        </BreadcrumbItem>
      </Breadcrumb>

      {/* Header */}
      <Flex justify="space-between" align="flex-start" mb={6} flexWrap="wrap" gap={4}>
        <HStack spacing={4} align="center">
          <IconButton
            icon={<FaArrowLeft />}
            variant="ghost"
            onClick={() => navigate('/app/compras/ordenes')}
            aria-label="Volver"
          />
          <VStack align="start" spacing={0}>
            <Heading size="lg">OC-{orden.numero || id}</Heading>
            <Text color="gray.500" fontSize="sm">{orden.proveedor_nombre || 'Sin proveedor'}</Text>
          </VStack>
          <Badge
            colorScheme={estadoCfg.color}
            fontSize="sm"
            px={3} py={1}
            borderRadius="full"
          >
            {estadoCfg.label}
          </Badge>
        </HStack>

        <HStack spacing={3}>
          <Button leftIcon={<FaFilePdf />} colorScheme="red" variant="outline" onClick={handleExportarPDF}>
            Exportar PDF
          </Button>
          {estadoKey === 'borrador' && (
            <Button leftIcon={<FaEdit />} colorScheme="blue"
              onClick={() => navigate(`/app/compras/orden-compra/${id}/editar`)}>
              Editar
            </Button>
          )}
          {transiciones.length > 0 && (
            <Menu>
              <MenuButton as={IconButton} icon={<FaEllipsisV />} variant="outline" aria-label="Más acciones" />
              <MenuList>
                {transiciones.map((est) => (
                  <MenuItem key={est}
                    isDisabled={cambiarEstadoMutation.isPending}
                    onClick={() => cambiarEstadoMutation.mutate(est)}>
                    {TRANSICION_LABELS[est] ?? `Marcar como ${ESTADO_CONFIG[est]?.label}`}
                  </MenuItem>
                ))}
              </MenuList>
            </Menu>
          )}
        </HStack>
      </Flex>

      {/* Two-column layout */}
      <Flex gap={6} align="flex-start" flexDirection={{ base: 'column', lg: 'row' }}>
        {/* LEFT — 65% */}
        <VStack flex="1" spacing={5} align="stretch" minW={0}>

          {/* Información de la Orden */}
          <Card bg={cardBg} borderColor={borderColor} borderWidth={1} borderRadius="lg" shadow="sm">
            <CardHeader pb={2}>
              <Heading size="sm" color="gray.700">
                <HStack><FaFileAlt /><Text>Información de la Orden</Text></HStack>
              </Heading>
            </CardHeader>
            <Divider />
            <CardBody>
              <SimpleGrid columns={{ base: 1, sm: 2 }} spacing={5}>
                <InfoRow label="Número de Orden" value={`OC-${orden.numero || id}`} />
                <InfoRow label="Estado">
                  <Badge colorScheme={estadoCfg.color} borderRadius="full" px={2}>
                    {estadoCfg.label}
                  </Badge>
                </InfoRow>
                <InfoRow label="Fecha de Emisión" value={formatDate(orden.fecha_creacion)} />
                <InfoRow label="Fecha de Entrega Esperada" value={formatDate(orden.fecha_entrega)} />
                {orden.notas && (
                  <Box gridColumn={{ sm: 'span 2' }}>
                    <InfoRow label="Notas / Observaciones" value={orden.notas} />
                  </Box>
                )}
              </SimpleGrid>
            </CardBody>
          </Card>

          {/* Proveedor */}
          <Card bg={cardBg} borderColor={borderColor} borderWidth={1} borderRadius="lg" shadow="sm">
            <CardHeader pb={2}>
              <Heading size="sm" color="gray.700">
                <HStack><FaBuilding /><Text>Proveedor</Text></HStack>
              </Heading>
            </CardHeader>
            <Divider />
            <CardBody>
              <Text fontSize="md" fontWeight="semibold" color="gray.800" mb={2}>
                {orden.proveedor_nombre || '—'}
              </Text>
              <Text fontSize="sm" color="gray.500">
                Para modificar datos del proveedor, edita la orden o ve a la sección de Proveedores.
              </Text>
            </CardBody>
          </Card>

        </VStack>

        {/* RIGHT — 35% */}
        <VStack
          w={{ base: '100%', lg: '340px' }}
          flexShrink={0}
          spacing={5}
          align="stretch"
        >
          {/* Resumen económico */}
          <Card bg={cardBg} borderColor={borderColor} borderWidth={1} borderRadius="lg" shadow="sm">
            <CardHeader pb={2}>
              <Heading size="sm" color="gray.700">Resumen Económico</Heading>
            </CardHeader>
            <Divider />
            <CardBody>
              <VStack spacing={3} align="stretch">
                <Flex justify="space-between">
                  <Text fontSize="sm" color="gray.600">Subtotal (sin IGV)</Text>
                  <Text fontSize="sm" fontWeight="medium">{formatCurrency(orden.subtotal)}</Text>
                </Flex>
                <Flex justify="space-between">
                  <Text fontSize="sm" color="gray.600">IGV (18%)</Text>
                  <Text fontSize="sm" fontWeight="medium">{formatCurrency(orden.igv)}</Text>
                </Flex>
                <Divider />
                <Flex justify="space-between" align="center">
                  <Text fontWeight="bold">Total</Text>
                  <Text fontSize="xl" fontWeight="bold" color="blue.600">
                    {formatCurrency(orden.total)}
                  </Text>
                </Flex>
                <Text fontSize="xs" color="gray.400">Moneda: Sol Peruano (PEN)</Text>
              </VStack>
            </CardBody>
          </Card>

          {/* Acciones por estado */}
          {transiciones.length > 0 && (
            <Card bg={cardBg} borderColor={borderColor} borderWidth={1} borderRadius="lg" shadow="sm">
              <CardHeader pb={2}>
                <Heading size="sm" color="gray.700">Acciones</Heading>
              </CardHeader>
              <Divider />
              <CardBody>
                <VStack spacing={2} align="stretch">
                  {transiciones.map((est) => {
                    const cfg = ESTADO_CONFIG[est];
                    return (
                      <Button
                        key={est}
                        colorScheme={cfg?.color ?? 'gray'}
                        variant={est === 'rechazada' ? 'outline' : 'solid'}
                        size="sm"
                        isLoading={cambiarEstadoMutation.isPending}
                        onClick={() => cambiarEstadoMutation.mutate(est)}
                      >
                        {TRANSICION_LABELS[est] ?? `Marcar como ${cfg?.label}`}
                      </Button>
                    );
                  })}
                </VStack>
              </CardBody>
            </Card>
          )}

          {/* Exportar PDF */}
          <Card bg={cardBg} borderColor={borderColor} borderWidth={1} borderRadius="lg" shadow="sm">
            <CardHeader pb={2}>
              <Heading size="sm" color="gray.700">Documentos</Heading>
            </CardHeader>
            <Divider />
            <CardBody>
              <Button
                leftIcon={<FaFilePdf />}
                colorScheme="red"
                variant="outline"
                w="full"
                onClick={handleExportarPDF}
              >
                Descargar PDF
              </Button>
              <Text fontSize="xs" color="gray.400" mt={2} textAlign="center">
                PDF de la orden con datos del proveedor y totales
              </Text>
            </CardBody>
          </Card>
        </VStack>
      </Flex>
    </Box>
  );
};

export default OrdenCompraDetalle;
