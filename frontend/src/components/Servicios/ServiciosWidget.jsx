import React, { useEffect, useState } from 'react';
import {
  Box, Flex, Text, Badge, HStack, VStack, Button,
  Divider, Spinner, useColorModeValue,
} from '@chakra-ui/react';
import { FaTools, FaCheckCircle, FaPlus, FaExclamationTriangle } from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';
import serviciosService from '../../services/serviciosService';

const SLABarMini = ({ orden }) => {
  const { dias_restantes_sla, dias_sla = 30, estado_sla } = orden;

  if (dias_restantes_sla === null || dias_restantes_sla === undefined) return null;

  const usado  = dias_sla - dias_restantes_sla;
  const pct    = Math.min(100, Math.max(0, (usado / dias_sla) * 100));
  const vencida = dias_restantes_sla < 0;

  const color = estado_sla === 'vencido'  ? '#ef4444'
    : estado_sla === 'critico' ? '#f97316'
    : estado_sla === 'alerta'  ? '#f59e0b'
    : '#22c55e';

  return (
    <Box>
      <Box h="4px" bg="gray.100" borderRadius="full" overflow="hidden" mb={0.5}>
        <Box
          h="100%"
          w={`${pct}%`}
          bg={color}
          borderRadius="full"
          sx={vencida ? { animation: 'sla-pulse 1.5s infinite' } : undefined}
        />
      </Box>
      <Text
        fontSize="xs"
        fontWeight={estado_sla !== 'ok' ? 'bold' : 'normal'}
        color={color}
      >
        {vencida
          ? `Vencida hace ${Math.abs(dias_restantes_sla)} día${Math.abs(dias_restantes_sla) !== 1 ? 's' : ''}`
          : `${dias_restantes_sla} día${dias_restantes_sla !== 1 ? 's' : ''} restantes`}
      </Text>
    </Box>
  );
};

const ServiciosWidget = () => {
  const navigate  = useNavigate();
  const cardBg    = useColorModeValue('white', 'gray.800');
  const border    = useColorModeValue('gray.200', 'gray.600');
  const labelColor = useColorModeValue('gray.500', 'gray.400');

  const [resumen, setResumen]       = useState(null);
  const [enRiesgo, setEnRiesgo]     = useState([]);
  const [loading, setLoading]       = useState(true);
  const [completadasMes, setCompletadasMes] = useState(0);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const [res, lista] = await Promise.all([
          serviciosService.resumen(),
          serviciosService.listar({ en_riesgo: 'true', page_size: 3 }),
        ]);
        if (!mounted) return;
        setResumen(res);
        const items = lista?.results ?? (Array.isArray(lista) ? lista : []);
        setEnRiesgo(items.slice(0, 3));

        // Completadas este mes
        const now = new Date();
        const desde = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`;
        const completadas = await serviciosService.listar({
          estado: 'entregado',
          fecha_ingreso_desde: desde,
          page_size: 1,
        });
        if (mounted) {
          setCompletadasMes(completadas?.count ?? (Array.isArray(completadas) ? completadas.length : 0));
        }
      } catch (_) {
        // widget es best-effort
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => { mounted = false; };
  }, []);

  const totalActivas = resumen?.total_activas ?? 0;
  const enRiesgoN    = resumen?.en_riesgo     ?? 0;
  const vencidasN    = resumen?.vencidas      ?? 0;

  return (
    <Box
      bg={cardBg}
      border="1px solid"
      borderColor={border}
      borderRadius="lg"
      shadow="sm"
      overflow="hidden"
    >
      {/* Header */}
      <Flex
        align="center"
        justify="space-between"
        px={4}
        py={3}
        borderBottom="1px solid"
        borderColor={border}
      >
        <HStack spacing={2}>
          <Box p={1.5} bg="blue.50" borderRadius="md">
            <FaTools size={13} color="var(--chakra-colors-blue-500)" />
          </Box>
          <Text fontWeight="semibold" fontSize="sm">Órdenes de Servicio</Text>
        </HStack>
        <Text
          fontSize="xs"
          color="blue.500"
          cursor="pointer"
          fontWeight="medium"
          _hover={{ textDecoration: 'underline' }}
          onClick={() => navigate('/app/servicios')}
        >
          Ver todas →
        </Text>
      </Flex>

      <Box px={4} py={3}>
        {loading ? (
          <Flex justify="center" py={4}><Spinner size="sm" color="blue.400" /></Flex>
        ) : (
          <>
            {/* KPI row */}
            <HStack spacing={4} mb={4} justify="space-between">
              <VStack spacing={0} align="center" flex="1">
                <Text
                  fontSize="2xl"
                  fontWeight="black"
                  lineHeight="1"
                  color="blue.600"
                >
                  {totalActivas}
                </Text>
                <Text fontSize="xs" color={labelColor}>Activas</Text>
              </VStack>
              <Divider orientation="vertical" h="36px" />
              <VStack spacing={0} align="center" flex="1">
                <HStack spacing={1} align="baseline">
                  <Text
                    fontSize="2xl"
                    fontWeight="black"
                    lineHeight="1"
                    color={enRiesgoN > 0 ? 'red.500' : 'gray.400'}
                    sx={enRiesgoN > 0 ? { animation: 'sla-pulse 2s infinite' } : undefined}
                  >
                    {enRiesgoN}
                  </Text>
                </HStack>
                <Text fontSize="xs" color={labelColor}>En riesgo</Text>
              </VStack>
              <Divider orientation="vertical" h="36px" />
              <VStack spacing={0} align="center" flex="1">
                <Text
                  fontSize="2xl"
                  fontWeight="black"
                  lineHeight="1"
                  color="green.500"
                >
                  {completadasMes}
                </Text>
                <Text fontSize="xs" color={labelColor}>Entregadas</Text>
              </VStack>
            </HStack>

            {/* Alerta de vencidas */}
            {vencidasN > 0 && (
              <Flex
                bg="red.50"
                border="1px solid"
                borderColor="red.200"
                borderRadius="md"
                p={2}
                mb={3}
                align="center"
                gap={2}
              >
                <FaExclamationTriangle size={12} color="var(--chakra-colors-red-500)" />
                <Text fontSize="xs" color="red.600" fontWeight="semibold">
                  {vencidasN} orden{vencidasN !== 1 ? 'es' : ''} vencida{vencidasN !== 1 ? 's' : ''}
                </Text>
              </Flex>
            )}

            {/* Lista de órdenes en riesgo */}
            {enRiesgo.length === 0 ? (
              <Flex align="center" gap={2} py={2}>
                <FaCheckCircle color="var(--chakra-colors-green-500)" size={14} />
                <Text fontSize="sm" color="green.600" fontWeight="medium">
                  Todas las órdenes al día
                </Text>
              </Flex>
            ) : (
              <VStack align="stretch" spacing={3}>
                <Text fontSize="xs" color={labelColor} fontWeight="semibold" textTransform="uppercase">
                  Órdenes en riesgo
                </Text>
                {enRiesgo.map((orden) => (
                  <Box
                    key={orden.id}
                    cursor="pointer"
                    _hover={{ bg: 'gray.50' }}
                    borderRadius="md"
                    p={2}
                    mx={-2}
                    onClick={() => navigate(`/app/servicios/${orden.id}`)}
                  >
                    <Flex justify="space-between" align="flex-start" mb={1}>
                      <HStack spacing={2}>
                        <Text fontFamily="mono" fontSize="xs" fontWeight="bold" color="blue.600">
                          {orden.numero}
                        </Text>
                        <Badge
                          colorScheme={orden.estado_sla === 'vencido' ? 'red' : 'orange'}
                          variant="subtle"
                          fontSize="9px"
                          borderRadius="full"
                        >
                          {orden.estado_sla === 'vencido' ? 'VENCIDA' : 'EN RIESGO'}
                        </Badge>
                      </HStack>
                    </Flex>
                    <Text fontSize="xs" color={labelColor} noOfLines={1} mb={1}>
                      {orden.cliente_nombre || '—'}
                    </Text>
                    <SLABarMini orden={orden} />
                  </Box>
                ))}
              </VStack>
            )}
          </>
        )}
      </Box>

      {/* Footer */}
      <Box
        borderTop="1px solid"
        borderColor={border}
        px={4}
        py={2}
      >
        <Button
          w="full"
          size="xs"
          leftIcon={<FaPlus />}
          colorScheme="blue"
          variant="ghost"
          justifyContent="flex-start"
          onClick={() => navigate('/app/servicios/nueva')}
        >
          Nueva Orden de Servicio
        </Button>
      </Box>

      {/* CSS para animación pulsante */}
      <style>{`
        @keyframes sla-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </Box>
  );
};

export default ServiciosWidget;
