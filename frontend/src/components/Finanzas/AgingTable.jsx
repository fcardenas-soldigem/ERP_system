import React, { useState } from 'react';
import {
  Box, Flex, Text, SimpleGrid, Progress, Table, Tbody, Tr, Td, Th, Thead,
  Badge, Button, HStack, VStack, Icon, useColorModeValue, useDisclosure,
} from '@chakra-ui/react';
import { FiAlertCircle, FiCalendar, FiMessageCircle } from 'react-icons/fi';
import { useNavigate } from 'react-router-dom';
import WhatsAppModal from './WhatsAppModal';

const fmt  = (n) => Number(n ?? 0).toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtK = (n) => Number(n ?? 0).toLocaleString('es-PE', { maximumFractionDigits: 0 });

const AGING_COLS = [
  { key: 'vigente',  label: 'Al día',       color: '#22c55e', bg: '#f0fdf4' },
  { key: '30_dias',  label: 'Hasta 30 días', color: '#eab308', bg: '#fefce8' },
  { key: '60_dias',  label: '31-60 días',    color: '#f97316', bg: '#fff7ed' },
  { key: '90_dias',  label: 'Más de 60',     color: '#ef4444', bg: '#fff1f2' },
];

const AgingBar = ({ aging = {}, total }) => {
  const max = total || 1;
  return (
    <SimpleGrid columns={4} spacing={3} mb={4}>
      {AGING_COLS.map(({ key, label, color, bg }) => {
        const val = aging[key] ?? 0;
        const pct = (val / max) * 100;
        return (
          <Box key={key} bg={bg} borderRadius="lg" p={3} border="1px solid" borderColor={`${color}30`}>
            <Text fontSize="10px" fontWeight="semibold" color="gray.500" textTransform="uppercase" letterSpacing="wider" mb={1}>{label}</Text>
            <Text fontSize="lg" fontWeight="bold" color="gray.900" fontVariantNumeric="tabular-nums">S/ {fmtK(val)}</Text>
            <Progress value={pct} size="xs" mt={2} borderRadius="full"
              sx={{ '& > div': { background: color, borderRadius: 'full' } }} />
          </Box>
        );
      })}
    </SimpleGrid>
  );
};

const AgingTable = ({ cxc, cxp }) => {
  const navigate = useNavigate();
  const border = useColorModeValue('gray.100', 'gray.700');
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [waTarget, setWaTarget] = useState([]);

  const morososVencidos = (cxc?.morosos ?? []).filter(m => m.dias > 0);
  const totalVencido = morososVencidos.reduce((s, m) => s + m.monto, 0);
  const proximosPagos = cxp?.proximos_pagos ?? [];
  const totalSemana = proximosPagos.reduce((s, p) => s + p.monto, 0);

  const openWA = (lista) => {
    setWaTarget(lista);
    onOpen();
  };

  return (
    <>
      <WhatsAppModal isOpen={isOpen} onClose={onClose} morosos={waTarget} />

      <SimpleGrid columns={{ base: 1, xl: 2 }} spacing={6}>

        {/* ── Por cobrar ── */}
        <Box bg="white" border="1px solid" borderColor={border} borderRadius="xl" overflow="hidden">
          <Box px={5} py={4} borderBottom="1px solid" borderColor={border}>
            <Flex justify="space-between" align="flex-start">
              <VStack align="flex-start" spacing={0.5}>
                <Text fontSize="sm" fontWeight="bold" color="gray.800">
                  {cxc?.dso != null
                    ? `Tus clientes te pagan en ${cxc.dso} días promedio`
                    : 'Lo que te deben tus clientes'}
                </Text>
                <Text fontSize="xs" color="gray.400">
                  Total pendiente: S/ {fmt(cxc?.total)}
                  {cxc?.dso != null && (
                    <Text as="span" color="gray.300"> · DSO: {cxc.dso} días</Text>
                  )}
                </Text>
              </VStack>
              <Button size="xs" variant="ghost" colorScheme="blue" onClick={() => navigate('/app/ventas')} flexShrink={0}>
                Ver todas →
              </Button>
            </Flex>

            {/* Insight de morosos urgentes */}
            {morososVencidos.length > 0 && (
              <Box mt={3} bg="orange.50" borderRadius="lg" p={3} border="1px solid" borderColor="orange.200">
                <Flex align="center" justify="space-between" gap={2} wrap="wrap">
                  <HStack spacing={2}>
                    <Icon as={FiAlertCircle} color="orange.500" boxSize="14px" flexShrink={0} />
                    <Text fontSize="xs" color="orange.700" fontWeight="medium">
                      {morososVencidos.length === 1
                        ? `1 cliente te debe S/ ${fmtK(totalVencido)} con más de 30 días`
                        : `${morososVencidos.length} clientes te deben S/ ${fmtK(totalVencido)} por más de 30 días`}
                    </Text>
                  </HStack>
                  <Button
                    size="xs"
                    colorScheme="green"
                    variant="solid"
                    leftIcon={<Icon as={FiMessageCircle} boxSize="11px" />}
                    onClick={() => openWA(morososVencidos)}
                    fontSize="10px"
                    h="24px"
                  >
                    Enviar recordatorio
                  </Button>
                </Flex>
              </Box>
            )}
          </Box>

          <Box px={5} py={4}>
            <AgingBar aging={cxc?.aging} total={cxc?.total} />

            {morososVencidos.length > 0 && (
              <>
                <Text fontSize="xs" fontWeight="semibold" color="gray.400" textTransform="uppercase" letterSpacing="wider" mb={3}>
                  Los que más días llevan sin pagar
                </Text>
                <Table size="sm" variant="unstyled">
                  <Thead>
                    <Tr>
                      <Th px={0} py={1} fontSize="10px" color="gray.400">Cliente</Th>
                      <Th px={0} py={1} fontSize="10px" color="gray.400" isNumeric>Monto</Th>
                      <Th px={0} py={1} fontSize="10px" color="gray.400" isNumeric>Días</Th>
                      <Th px={0} py={1}></Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {morososVencidos.slice(0, 5).map((m, i) => (
                      <Tr key={i} borderBottom="1px solid" borderColor={border}>
                        <Td px={0} py={2.5}>
                          <Text fontSize="xs" fontWeight="medium" noOfLines={1}>{m.cliente}</Text>
                          {m.venta_num && <Text fontSize="10px" color="gray.400">{m.venta_num}</Text>}
                        </Td>
                        <Td px={0} py={2.5} isNumeric>
                          <Text fontSize="xs" fontWeight="semibold" fontVariantNumeric="tabular-nums">S/ {fmtK(m.monto)}</Text>
                        </Td>
                        <Td px={0} py={2.5} isNumeric>
                          <Badge colorScheme={m.dias > 60 ? 'red' : m.dias > 30 ? 'orange' : 'yellow'} variant="subtle" fontSize="10px" borderRadius="sm">
                            {m.dias}d
                          </Badge>
                        </Td>
                        <Td px={0} py={2.5}>
                          <HStack spacing={1}>
                            <Button size="xs" colorScheme="green" variant="outline" borderRadius="full" fontSize="10px" h="20px"
                              onClick={() => navigate(`/app/ventas/${m.venta_id}/pagos/nuevo`)}>
                              Cobrar
                            </Button>
                            <Button size="xs" colorScheme="teal" variant="ghost" borderRadius="full" fontSize="10px" h="20px"
                              onClick={() => openWA([m])}>
                              WA
                            </Button>
                          </HStack>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </>
            )}
          </Box>
        </Box>

        {/* ── Por pagar ── */}
        <Box bg="white" border="1px solid" borderColor={border} borderRadius="xl" overflow="hidden">
          <Box px={5} py={4} borderBottom="1px solid" borderColor={border}>
            <Flex justify="space-between" align="flex-start">
              <VStack align="flex-start" spacing={0.5}>
                <Text fontSize="sm" fontWeight="bold" color="gray.800">
                  {cxp?.dpo != null
                    ? `Pagas a tus proveedores en ${cxp.dpo} días promedio`
                    : 'Lo que les debes a tus proveedores'}
                </Text>
                <Text fontSize="xs" color="gray.400">
                  Total pendiente: S/ {fmt(cxp?.total)}
                  {cxp?.dpo != null && (
                    <Text as="span" color="gray.300"> · DPO: {cxp.dpo} días</Text>
                  )}
                </Text>
              </VStack>
              <Button size="xs" variant="ghost" colorScheme="blue" onClick={() => navigate('/app/compras')} flexShrink={0}>
                Ver todas →
              </Button>
            </Flex>

            {/* Insight de facturas próximas */}
            {proximosPagos.length > 0 && (
              <Box mt={3} bg={cxp?.alerta_esta_semana ? '#fff1f2' : '#f0fdf4'} borderRadius="lg" p={3}
                border="1px solid" borderColor={cxp?.alerta_esta_semana ? '#fca5a5' : '#86efac'}>
                <Flex align="center" justify="space-between" gap={2} wrap="wrap">
                  <HStack spacing={2}>
                    <Icon as={FiCalendar} color={cxp?.alerta_esta_semana ? 'red.500' : 'green.500'} boxSize="14px" flexShrink={0} />
                    <Text fontSize="xs" color={cxp?.alerta_esta_semana ? 'red.700' : 'green.700'} fontWeight="medium">
                      {`Tienes ${proximosPagos.length} factura${proximosPagos.length > 1 ? 's' : ''} que vence${proximosPagos.length === 1 ? '' : 'n'} esta semana por S/ ${fmtK(totalSemana)}`}
                    </Text>
                  </HStack>
                  <Button
                    size="xs"
                    colorScheme={cxp?.alerta_esta_semana ? 'red' : 'green'}
                    variant="outline"
                    onClick={() => navigate('/app/compras')}
                    fontSize="10px"
                    h="24px"
                  >
                    Ver pagos de la semana
                  </Button>
                </Flex>
              </Box>
            )}
          </Box>

          <Box px={5} py={4}>
            <AgingBar aging={cxp?.aging} total={cxp?.total} />

            {proximosPagos.length > 0 && (
              <>
                <Text fontSize="xs" fontWeight="semibold" color="gray.400" textTransform="uppercase" letterSpacing="wider" mb={3}>
                  Próximos a vencer (esta semana)
                </Text>
                <Table size="sm" variant="unstyled">
                  <Thead>
                    <Tr>
                      <Th px={0} py={1} fontSize="10px" color="gray.400">Proveedor</Th>
                      <Th px={0} py={1} fontSize="10px" color="gray.400" isNumeric>Monto</Th>
                      <Th px={0} py={1} fontSize="10px" color="gray.400" isNumeric>Vence en</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {proximosPagos.slice(0, 5).map((p, i) => (
                      <Tr key={i} borderBottom="1px solid" borderColor={border} bg={p.urgente ? '#fff1f2' : 'transparent'}>
                        <Td px={0} py={2.5}>
                          <Text fontSize="xs" fontWeight="medium" noOfLines={1}>{p.proveedor}</Text>
                          <Text fontSize="10px" color="gray.400">{p.vence}</Text>
                        </Td>
                        <Td px={0} py={2.5} isNumeric>
                          <Text fontSize="xs" fontWeight="semibold" fontVariantNumeric="tabular-nums">S/ {fmtK(p.monto)}</Text>
                        </Td>
                        <Td px={0} py={2.5} isNumeric>
                          <Badge colorScheme={p.urgente ? 'red' : 'orange'} variant="subtle" fontSize="10px" borderRadius="sm">
                            {p.dias_restantes === 0 ? '¡Hoy!' : `${p.dias_restantes}d`}
                          </Badge>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </>
            )}
          </Box>
        </Box>

      </SimpleGrid>
    </>
  );
};

export default AgingTable;
