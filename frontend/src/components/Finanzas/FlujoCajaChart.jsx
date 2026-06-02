import React, { useMemo } from 'react';
import {
  Box, Flex, Text, SimpleGrid, Tooltip as ChakraTooltip,
  useColorModeValue,
} from '@chakra-ui/react';
import {
  ResponsiveContainer, AreaChart, Area, XAxis, Tooltip, ReferenceLine,
} from 'recharts';

const fmt = (n) => Number(n ?? 0).toLocaleString('es-PE', {
  minimumFractionDigits: 0, maximumFractionDigits: 0,
});

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <Box bg="gray.900" color="white" px={3} py={2} borderRadius="md" fontSize="xs" boxShadow="lg">
      <Text fontWeight="semibold">{d.fecha}</Text>
      <Text color="green.300">↑ Cobros: S/ {fmt(d.cobros)}</Text>
      <Text color="red.300">↓ Pagos: S/ {fmt(d.pagos)}</Text>
      <Text fontWeight="bold" mt={1}>Saldo: S/ {fmt(d.saldo)}</Text>
    </Box>
  );
};

const MetaCard = ({ label, value, sub, color = 'gray.700', tooltip }) => {
  const border = useColorModeValue('gray.100', 'gray.700');
  const card = (
    <Box bg="white" border="1px solid" borderColor={border} borderRadius="lg" p={4}>
      <Text fontSize="10px" fontWeight="semibold" color="gray.400" textTransform="uppercase" letterSpacing="wider" mb={2}>
        {label}
      </Text>
      <Text fontSize="xl" fontWeight="bold" color={color} fontVariantNumeric="tabular-nums">
        {value}
      </Text>
      {sub && <Text fontSize="xs" color="gray.400" mt={1}>{sub}</Text>}
    </Box>
  );
  return tooltip ? (
    <ChakraTooltip label={tooltip} hasArrow placement="top" fontSize="xs">{card}</ChakraTooltip>
  ) : card;
};

const FlujoCajaChart = ({ flujo }) => {
  if (!flujo) return null;

  const { saldo_actual, proyeccion_30_dias, cobros_periodo, pagos_periodo, saldo_diario = [], disclaimer } = flujo;
  const isPositive = saldo_actual >= 0;
  const lineColor  = isPositive ? '#22c55e' : '#ef4444';
  const fillId     = isPositive ? 'fcc-green' : 'fcc-red';
  const lastSaldo  = saldo_diario[saldo_diario.length - 1]?.saldo ?? 0;

  const border = useColorModeValue('gray.100', 'gray.700');

  return (
    <Box bg="white" border="1px solid" borderColor={border} borderRadius="xl" p={6} mb={6}>
      <Flex justify="space-between" align="flex-start" mb={4} wrap="wrap" gap={3}>
        <Box>
          <Text fontSize="10px" fontWeight="semibold" color="gray.400" textTransform="uppercase" letterSpacing="wider" mb={1}>
            Lo que cobras menos lo que pagas este mes
          </Text>
          <Text fontSize="3xl" fontWeight="bold" color={isPositive ? 'green.600' : 'red.500'} fontVariantNumeric="tabular-nums" lineHeight="1">
            S/ {fmt(saldo_actual)}
          </Text>
          <Text fontSize="xs" color="gray.400" mt={1}>{disclaimer}</Text>
        </Box>
      </Flex>

      {/* Chart */}
      {saldo_diario.length > 1 && (
        <Box h="120px" mb={4}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={saldo_diario} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="fcc-green" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#22c55e" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="fcc-red" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#ef4444" stopOpacity={0.12} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="fecha" tick={{ fontSize: 9, fill: '#9ca3af' }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
              <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#e5e7eb', strokeWidth: 1, strokeDasharray: '4 2' }} />
              <ReferenceLine y={0} stroke="#e5e7eb" strokeWidth={1} />
              <Area type="monotone" dataKey="saldo" stroke={lineColor} strokeWidth={2} fill={`url(#${fillId})`} dot={false} activeDot={{ r: 4, fill: lineColor, strokeWidth: 0 }} />
            </AreaChart>
          </ResponsiveContainer>
        </Box>
      )}

      {/* 4 cards debajo */}
      <SimpleGrid columns={{ base: 2, md: 4 }} spacing={3}>
        <MetaCard
          label="Entraron de clientes"
          value={`S/ ${fmt(cobros_periodo)}`}
          color="green.600"
          tooltip="Total que cobraste de tus clientes en este período"
        />
        <MetaCard
          label="Salieron a proveedores"
          value={`S/ ${fmt(pagos_periodo)}`}
          color="red.500"
          tooltip="Total que pagaste a tus proveedores en este período"
        />
        <MetaCard
          label="Pendiente de cobrar"
          value={`S/ ${fmt(flujo.cxc_pendiente)}`}
          color="orange.500"
          tooltip="Lo que tus clientes todavía te deben de ventas a crédito"
        />
        <MetaCard
          label="Si cobras todo en 30 días"
          value={`S/ ${fmt(proyeccion_30_dias)}`}
          color={proyeccion_30_dias >= 0 ? 'blue.600' : 'red.600'}
          tooltip="Estimado de tu caja si cobras todo lo pendiente y pagas todo lo que debes"
          sub={proyeccion_30_dias < 0 ? '⚠️ Proyección negativa' : ''}
        />
      </SimpleGrid>
    </Box>
  );
};

export default FlujoCajaChart;
