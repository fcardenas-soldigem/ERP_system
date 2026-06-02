import React from 'react';
import {
  Box, Flex, Text, SimpleGrid, Progress, HStack, VStack, Icon, Button,
  Tooltip as ChakraTooltip, useColorModeValue, Divider, Badge,
} from '@chakra-ui/react';
import { FiArrowUpRight, FiArrowDownRight, FiInfo, FiAlertTriangle, FiExternalLink } from 'react-icons/fi';
import { useNavigate } from 'react-router-dom';

const fmt  = (n, d = 2) => Number(n ?? 0).toLocaleString('es-PE', { minimumFractionDigits: d, maximumFractionDigits: d });
const fmtK = (n) => Number(n ?? 0).toLocaleString('es-PE', { maximumFractionDigits: 0 });

const MARGEN = {
  verde:    { bg: '#dcfce7', border: '#22c55e', text: '#166534', bar: '#22c55e' },
  amarillo: { bg: '#fef9c3', border: '#eab308', text: '#713f12', bar: '#eab308' },
  rojo:     { bg: '#fee2e2', border: '#ef4444', text: '#991b1b', bar: '#ef4444' },
};

const InfoTip = ({ label }) => (
  <ChakraTooltip label={label} hasArrow placement="top" fontSize="xs" maxW="260px">
    <span><Icon as={FiInfo} color="gray.300" boxSize="12px" cursor="help" /></span>
  </ChakraTooltip>
);

// ─── Semáforo color para margen neto ─────────────────────────────────────────
const semaforoNeto = (pct) => {
  if (pct >= 15) return { emoji: '🟢', color: 'green.600', label: 'Buen margen neto' };
  if (pct >= 5)  return { emoji: '🟡', color: 'yellow.600', label: 'Margen neto ajustado' };
  return { emoji: '🔴', color: 'red.600', label: 'Margen neto bajo' };
};

// ─── Cascada P&L ─────────────────────────────────────────────────────────────
const CascadaUtilidad = ({ ventas, costo, utilidadBruta, gastos, utilidadNeta, border }) => {
  const margenBruto = ventas > 0 ? ((utilidadBruta / ventas) * 100).toFixed(1) : 0;
  const margenNeto  = ventas > 0 ? ((utilidadNeta  / ventas) * 100).toFixed(1) : 0;
  const semaforo    = semaforoNeto(Number(margenNeto));

  return (
    <Box
      bg="white"
      border="1px solid"
      borderColor={border}
      borderRadius="xl"
      p={5}
      fontVariantNumeric="tabular-nums"
      fontSize="sm"
    >
      <Text fontSize="10px" fontWeight="semibold" color="gray.400" textTransform="uppercase" letterSpacing="wider" mb={4}>
        Estado de resultados del período
      </Text>

      <VStack spacing={2} align="stretch">
        {/* Ventas */}
        <Flex justify="space-between">
          <Text color="gray.600">Ventas netas del período</Text>
          <Text fontWeight="medium">S/ {fmtK(ventas)}</Text>
        </Flex>
        <Flex justify="space-between">
          <Text color="gray.500">- Costo de ventas (COGS)</Text>
          <Text color="gray.500">- S/ {fmtK(costo)}</Text>
        </Flex>

        <Divider borderColor="gray.200" />

        {/* Utilidad bruta */}
        <Flex justify="space-between" align="center">
          <HStack spacing={2}>
            <Text fontWeight="semibold" color="gray.700">= Utilidad bruta</Text>
            <Badge colorScheme="blue" fontSize="10px" borderRadius="full">margen {margenBruto}%</Badge>
          </HStack>
          <Text fontWeight="bold" color="blue.600">S/ {fmtK(utilidadBruta)}</Text>
        </Flex>

        <Flex justify="space-between">
          <Text color="gray.500">- Gastos operativos</Text>
          <Text color="gray.500">- S/ {fmtK(gastos)}</Text>
        </Flex>

        <Divider borderColor="gray.200" />

        {/* Utilidad neta */}
        <Flex justify="space-between" align="center">
          <HStack spacing={2}>
            <Text fontWeight="semibold" color="gray.700">= Utilidad neta</Text>
            <Badge
              colorScheme={Number(margenNeto) >= 15 ? 'green' : Number(margenNeto) >= 5 ? 'yellow' : 'red'}
              fontSize="10px"
              borderRadius="full"
            >
              margen {margenNeto}%
            </Badge>
            <Text fontSize="sm">{semaforo.emoji}</Text>
          </HStack>
          <Text fontWeight="bold" color={Number(utilidadNeta) >= 0 ? 'green.600' : 'red.600'}>
            S/ {fmtK(utilidadNeta)}
          </Text>
        </Flex>
      </VStack>
    </Box>
  );
};

const RentabilidadSection = ({ rentabilidad }) => {
  const navigate = useNavigate();
  const border = useColorModeValue('gray.100', 'gray.700');

  if (!rentabilidad) return null;

  const {
    ventas_mes, costo_ventas_mes, utilidad_bruta, margen_bruto_pct,
    semaforo_margen, vs_mes_anterior_pct, por_producto = [], nota,
    tiene_gastos_registrados, gastos_operativos, utilidad_neta, margen_neto_pct,
  } = rentabilidad;

  const isUp    = vs_mes_anterior_pct >= 0;
  const mc      = MARGEN[semaforo_margen] ?? MARGEN.amarillo;
  const maxUtil = Math.max(...por_producto.map(p => p.utilidad), 1);

  // "De cada S/100 que vendes, te quedan S/X.XX"
  const gananciaCada100 = fmt(margen_bruto_pct, 2);

  // Insight por margen
  const insightMargen = isUp
    ? `Tu margen subió ${fmt(Math.abs(vs_mes_anterior_pct), 1)}% vs el mes pasado`
    : `Tu margen bajó ${fmt(Math.abs(vs_mes_anterior_pct), 1)}%. Revisa precios de tus productos más vendidos`;

  // Top 3 con peor margen para el botón de acción
  const productosMenorMargen = [...por_producto].sort((a, b) => a.margen_pct - b.margen_pct).slice(0, 3);

  return (
    <Box>
      <SimpleGrid columns={{ base: 1, sm: 3 }} spacing={4} mb={6}>

        {/* Ventas del mes */}
        <Box bg="white" border="1px solid" borderColor={border} borderRadius="xl" p={5}>
          <HStack mb={2} justify="space-between">
            <Text fontSize="10px" fontWeight="semibold" color="gray.400" textTransform="uppercase" letterSpacing="wider">
              Ventas cobradas
            </Text>
            <InfoTip label="Total facturado y cobrado en el período, sin IGV" />
          </HStack>
          <Text fontSize="2xl" fontWeight="bold" color="gray.900" fontVariantNumeric="tabular-nums">
            S/ {fmtK(ventas_mes)}
          </Text>
          <HStack mt={1} spacing={1}>
            <Icon as={isUp ? FiArrowUpRight : FiArrowDownRight} color={isUp ? 'green.500' : 'red.500'} boxSize="14px" />
            <Text fontSize="xs" fontWeight="semibold" color={isUp ? 'green.500' : 'red.500'}>
              {Math.abs(vs_mes_anterior_pct).toFixed(1)}% vs mes anterior
            </Text>
          </HStack>
        </Box>

        {/* Costo de lo vendido */}
        <Box bg="white" border="1px solid" borderColor={border} borderRadius="xl" p={5}>
          <HStack mb={2} justify="space-between">
            <Text fontSize="10px" fontWeight="semibold" color="gray.400" textTransform="uppercase" letterSpacing="wider">
              Lo que te costó venderlo
            </Text>
            <InfoTip label={nota ?? 'Estimado por precio de catálogo de cada producto'} />
          </HStack>
          <Text fontSize="2xl" fontWeight="bold" color="gray.700" fontVariantNumeric="tabular-nums">
            S/ {fmtK(costo_ventas_mes)}
          </Text>
          <Text fontSize="xs" color="gray.400" mt={1}>Estimado por catálogo</Text>
        </Box>

        {/* Margen — el KPI principal */}
        <Box bg={mc.bg} border="1px solid" borderColor={mc.border} borderRadius="xl" p={5}>
          <HStack mb={1} justify="space-between">
            <Text fontSize="10px" fontWeight="semibold" color={mc.text} textTransform="uppercase" letterSpacing="wider">
              Lo que te queda después de costos
            </Text>
            <InfoTip label={`De cada S/100 que vendes, S/${gananciaCada100} es tuyo después de pagar lo que vendiste. El resto son costos.`} />
          </HStack>

          <Text fontSize="2xl" fontWeight="bold" color={mc.text} fontVariantNumeric="tabular-nums" mt={1}>
            S/{gananciaCada100} de cada S/100
          </Text>

          <Text fontSize="10px" color={mc.text} opacity={0.7} mt={0.5}>
            Margen bruto: {fmt(margen_bruto_pct, 1)}% · Utilidad: S/ {fmtK(utilidad_bruta)}
          </Text>

          <Progress value={margen_bruto_pct} max={100} size="xs" mt={3} borderRadius="full"
            sx={{ '& > div': { background: mc.bar, borderRadius: 'full' } }} />

          <HStack mt={2} spacing={1.5}>
            <Icon
              as={isUp ? FiArrowUpRight : FiAlertTriangle}
              color={isUp ? 'green.500' : mc.text}
              boxSize="12px"
            />
            <Text fontSize="xs" color={isUp ? 'green.600' : mc.text} fontWeight="medium">
              {insightMargen}
            </Text>
          </HStack>
        </Box>

      </SimpleGrid>

      {/* ── Cascada de utilidades ── */}
      {tiene_gastos_registrados ? (
        <Box mb={6}>
          <CascadaUtilidad
            ventas={ventas_mes}
            costo={costo_ventas_mes}
            utilidadBruta={utilidad_bruta}
            gastos={gastos_operativos ?? 0}
            utilidadNeta={utilidad_neta ?? (utilidad_bruta - (gastos_operativos ?? 0))}
            border={border}
          />
        </Box>
      ) : (
        <Box
          bg="blue.50"
          border="1px solid"
          borderColor="blue.200"
          borderRadius="xl"
          p={5}
          mb={6}
        >
          <HStack justify="space-between" align="flex-start" wrap="wrap" gap={3}>
            <VStack align="flex-start" spacing={1}>
              <Text fontSize="sm" fontWeight="semibold" color="blue.700">
                Utilidad bruta estimada: S/ {fmtK(utilidad_bruta)}
              </Text>
              <Text fontSize="xs" color="blue.600">
                * Utilidad bruta estimada. Registra tus gastos operativos para ver la utilidad real.
              </Text>
            </VStack>
            <Button
              size="sm"
              colorScheme="blue"
              variant="outline"
              rightIcon={<FiExternalLink size={12} />}
              onClick={() => navigate('/app/finanzas/gastos')}
            >
              Registrar gastos →
            </Button>
          </HStack>
        </Box>
      )}

      {/* Tabla de productos */}
      {por_producto.length > 0 && (
        <Box bg="white" border="1px solid" borderColor={border} borderRadius="xl" overflow="hidden">
          <Flex px={5} py={4} borderBottom="1px solid" borderColor={border} justify="space-between" align="center">
            <VStack align="flex-start" spacing={0}>
              <Text fontSize="sm" fontWeight="semibold" color="gray.700">
                ¿Cuánto te deja cada producto?
              </Text>
              <Text fontSize="xs" color="gray.400">
                Los primeros son los más rentables · los últimos los que menos margen dan
              </Text>
            </VStack>
            {!isUp && productosMenorMargen.length > 0 && (
              <Button
                size="xs"
                colorScheme="orange"
                variant="outline"
                onClick={() => navigate('/app/inventario')}
                fontSize="xs"
              >
                Ver productos con menor margen
              </Button>
            )}
          </Flex>
          <Box px={5} py={3}>
            {por_producto.map((p, i) => {
              const pct    = (p.utilidad / maxUtil) * 100;
              const mColor = p.margen_pct >= 30 ? '#22c55e' : p.margen_pct >= 15 ? '#eab308' : '#ef4444';
              const label  = p.margen_pct >= 30 ? 'Buen margen' : p.margen_pct >= 15 ? 'Margen ok' : 'Poco margen';
              return (
                <Flex key={i} align="center" gap={3} py={2.5}>
                  <Text w="20px" fontSize="xs" fontWeight="bold" color="gray.400">#{i + 1}</Text>
                  <Box flex="1" minW={0}>
                    <Flex justify="space-between" mb={1.5} align="center">
                      <Text fontSize="sm" fontWeight="medium" noOfLines={1}>{p.nombre}</Text>
                      <HStack spacing={3} flexShrink={0} ml={2}>
                        <Text fontSize="10px" color="gray.400">{label}</Text>
                        <Text fontSize="xs" color="gray.400">{fmt(p.margen_pct, 1)}%</Text>
                        <Text fontSize="xs" fontWeight="semibold" color="gray.700">S/ {fmtK(p.utilidad)}</Text>
                      </HStack>
                    </Flex>
                    <Progress value={pct} size="xs" borderRadius="full"
                      sx={{ '& > div': { background: mColor, borderRadius: 'full', transition: 'width 0.6s ease' } }} />
                  </Box>
                </Flex>
              );
            })}
          </Box>
        </Box>
      )}
    </Box>
  );
};

export default RentabilidadSection;
