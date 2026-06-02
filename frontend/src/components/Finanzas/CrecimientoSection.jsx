import React from 'react';
import {
  Box, SimpleGrid, Text, HStack, VStack, Icon,
  Tooltip as ChakraTooltip, useColorModeValue,
} from '@chakra-ui/react';
import { FiArrowUpRight, FiArrowDownRight, FiUsers, FiShoppingCart, FiTrendingUp, FiStar } from 'react-icons/fi';

const fmt  = (n, d = 2) => Number(n ?? 0).toLocaleString('es-PE', { minimumFractionDigits: d, maximumFractionDigits: d });
const fmtI = (n) => Number(n ?? 0).toLocaleString('es-PE', { maximumFractionDigits: 0 });

const DeltaBadge = ({ pct }) => {
  if (pct === undefined || pct === null) return null;
  const up = pct >= 0;
  return (
    <HStack spacing={0.5}>
      <Icon as={up ? FiArrowUpRight : FiArrowDownRight} color={up ? 'green.500' : 'red.500'} boxSize="13px" />
      <Text fontSize="xs" fontWeight="semibold" color={up ? 'green.500' : 'red.500'}>
        {Math.abs(pct).toFixed(1)}%
      </Text>
      <Text fontSize="xs" color="gray.400">vs mes anterior</Text>
    </HStack>
  );
};

const CrecCard = ({ icono, titulo, valor, delta, sub, tooltip }) => {
  const border = useColorModeValue('gray.100', 'gray.700');
  return (
    <ChakraTooltip label={tooltip} hasArrow placement="top" fontSize="xs" maxW="240px" isDisabled={!tooltip}>
      <Box bg="white" border="1px solid" borderColor={border} borderRadius="xl" p={5} cursor={tooltip ? 'help' : 'default'}>
        <HStack mb={3} spacing={2}>
          <Icon as={icono} color="gray.400" boxSize="15px" />
          <Text fontSize="10px" fontWeight="semibold" color="gray.400" textTransform="uppercase" letterSpacing="wider">
            {titulo}
          </Text>
        </HStack>
        <Text fontSize="2xl" fontWeight="bold" color="gray.900" fontVariantNumeric="tabular-nums" lineHeight="1.1">
          {valor}
        </Text>
        {delta !== undefined && <Box mt={1.5}><DeltaBadge pct={delta} /></Box>}
        {sub && <Text fontSize="xs" color="gray.400" mt={1}>{sub}</Text>}
      </Box>
    </ChakraTooltip>
  );
};

const CrecimientoSection = ({ crecimiento }) => {
  if (!crecimiento) return null;

  const {
    revenue_growth_pct,
    ventas_mes, ventas_anterior,
    transacciones_mes, transacciones_anterior,
    ticket_promedio, ticket_promedio_anterior, ticket_variacion_pct,
    nuevos_clientes,
  } = crecimiento;

  const txVariacion = transacciones_anterior > 0
    ? ((transacciones_mes - transacciones_anterior) / transacciones_anterior * 100)
    : 0;

  return (
    <SimpleGrid columns={{ base: 1, sm: 2, lg: 4 }} spacing={4}>

      <CrecCard
        icono={FiTrendingUp}
        titulo="Tus ventas crecieron"
        valor={`${revenue_growth_pct >= 0 ? '+' : ''}${revenue_growth_pct.toFixed(1)}%`}
        sub={`S/ ${fmt(ventas_mes, 0)} este mes vs S/ ${fmt(ventas_anterior, 0)} el anterior`}
        delta={revenue_growth_pct}
        tooltip="Cuánto más (o menos) vendiste vs el mes anterior"
      />

      <CrecCard
        icono={FiShoppingCart}
        titulo="Cada venta fue de"
        valor={`S/ ${fmt(ticket_promedio, 0)}`}
        sub={`El mes pasado: S/ ${fmt(ticket_promedio_anterior, 0)}`}
        delta={ticket_variacion_pct}
        tooltip="Cuánto gasta cada cliente en promedio por visita. Sube cuando vendes más o productos más caros."
      />

      <CrecCard
        icono={FiShoppingCart}
        titulo="Ventas que hiciste"
        valor={fmtI(transacciones_mes)}
        sub={`${fmtI(transacciones_anterior)} el mes pasado`}
        delta={txVariacion}
        tooltip="Cuántas ventas cobraste en el período"
      />

      <CrecCard
        icono={FiUsers}
        titulo="Clientes nuevos"
        valor={fmtI(nuevos_clientes)}
        sub="Primera compra este mes"
        tooltip="Clientes que compraron por primera vez en tu negocio este período"
      />

    </SimpleGrid>
  );
};

export default CrecimientoSection;
