import React, { useState } from 'react';
import {
  Box, Flex, Text, SimpleGrid, HStack, VStack, Icon, Badge, Button,
  Divider, Collapse, useColorModeValue,
  Tooltip as ChakraTooltip,
} from '@chakra-ui/react';
import { FiChevronDown, FiChevronUp, FiAlertTriangle, FiUsers, FiInfo } from 'react-icons/fi';
import { useNavigate } from 'react-router-dom';

const fmt = (n, d = 2) => Number(n ?? 0).toLocaleString('es-PE', {
  minimumFractionDigits: d, maximumFractionDigits: d,
});
const fmtK = (n) => Number(n ?? 0).toLocaleString('es-PE', { maximumFractionDigits: 0 });

const InfoTip = ({ label }) => (
  <ChakraTooltip label={label} hasArrow placement="top" fontSize="xs" maxW="240px">
    <span><Icon as={FiInfo} color="gray.300" boxSize="11px" cursor="help" /></span>
  </ChakraTooltip>
);

const MetricaCard = ({ titulo, valor, unit, subtexto, tooltip, semaforo, alerta, delta, deltaLabel }) => {
  const border = useColorModeValue('gray.100', 'gray.700');
  const COLORS = {
    verde:    { badge: 'green',  text: '#166534' },
    amarillo: { badge: 'yellow', text: '#713f12' },
    rojo:     { badge: 'red',    text: '#991b1b' },
  };
  const sc = semaforo ? (COLORS[semaforo] ?? COLORS.amarillo) : null;

  return (
    <Box bg="white" border="1px solid" borderColor={border} borderRadius="xl" p={5}>
      <HStack justify="space-between" mb={2}>
        <Text fontSize="10px" fontWeight="semibold" color="gray.400" textTransform="uppercase" letterSpacing="wider">
          {titulo}
        </Text>
        {tooltip && <InfoTip label={tooltip} />}
      </HStack>

      <Flex align="baseline" gap={1}>
        <Text fontSize="2xl" fontWeight="bold" color="gray.900" fontVariantNumeric="tabular-nums">
          {valor}
        </Text>
        {unit && <Text fontSize="sm" color="gray.400" fontWeight="medium">{unit}</Text>}
      </Flex>

      {semaforo && sc && (
        <Badge colorScheme={sc.badge} variant="subtle" fontSize="10px" borderRadius="full" mt={2} px={2}>
          {semaforo === 'verde' ? 'Saludable' : semaforo === 'amarillo' ? 'Precaución' : 'Crítico'}
        </Badge>
      )}

      {delta !== undefined && delta !== null && (
        <Text fontSize="xs" mt={1} color={delta >= 0 ? 'green.500' : 'red.400'} fontWeight="medium">
          {delta >= 0 ? '▲' : '▼'} {deltaLabel ?? `S/ ${fmtK(Math.abs(delta))} vs mes anterior`}
        </Text>
      )}

      {alerta && (
        <HStack mt={2} spacing={1}>
          <Icon as={FiAlertTriangle} color="orange.400" boxSize="12px" />
          <Text fontSize="xs" color="orange.600">{alerta}</Text>
        </HStack>
      )}

      {subtexto && (
        <Text fontSize="xs" color="gray.400" mt={2} lineHeight="short">{subtexto}</Text>
      )}
    </Box>
  );
};

const KPIsAvanzados = ({ avanzados }) => {
  const [isOpen, setIsOpen] = useState(false);
  const navigate = useNavigate();
  const border = useColorModeValue('gray.100', 'gray.700');

  if (!avanzados) return null;

  const {
    ccc_dias, dio_dias, dso_dias, dpo_dias,
    ratio_liquidez, semaforo_liquidez,
    concentracion_top3_pct, concentracion_alerta, top3_clientes = [],
    indice_morosidad_pct, saldo_neto_mes, saldo_neto_anterior,
  } = avanzados;

  const saldoDelta     = saldo_neto_mes - saldo_neto_anterior;
  const saldoSemaforo  = saldo_neto_mes >= 0 ? 'verde' : 'rojo';

  // Ratio liquidez — lenguaje llano
  const liquidezTexto = ratio_liquidez >= 99
    ? 'Sin deudas pendientes con proveedores'
    : ratio_liquidez >= 1.2
    ? `Por cada S/1 que debes tienes S/${fmt(ratio_liquidez, 1)} disponible. Estás cómodo.`
    : ratio_liquidez >= 1
    ? `Por cada S/1 que debes tienes S/${fmt(ratio_liquidez, 1)}. Ajustado pero OK.`
    : `Lo que debes es más que lo que tienes por cobrar. Acelera cobranzas.`;

  return (
    <Box bg="white" border="1px solid" borderColor={border} borderRadius="xl" overflow="hidden">

      {/* Trigger colapsado */}
      <Button
        variant="ghost"
        w="100%"
        h="auto"
        py={4}
        px={5}
        borderRadius="0"
        onClick={() => setIsOpen(o => !o)}
        justifyContent="space-between"
        fontWeight="semibold"
        fontSize="sm"
        color="gray.600"
        rightIcon={<Icon as={isOpen ? FiChevronUp : FiChevronDown} color="gray.400" />}
      >
        <HStack spacing={3}>
          <Text>Ver métricas avanzadas</Text>
          <Badge colorScheme="purple" variant="subtle" fontSize="10px" borderRadius="full">
            Para entender a fondo
          </Badge>
        </HStack>
      </Button>

      <Collapse in={isOpen} animateOpacity>
        <Divider />
        <Box px={5} py={5}>

          <Text fontSize="xs" color="gray.400" mb={4}>
            Estas métricas te ayudan a entender cómo fluye la plata en tu negocio.
            No necesitas actuar sobre ellas todos los días — son para cuando quieres entender por qué tu caja sube o baja.
          </Text>

          <SimpleGrid columns={{ base: 1, sm: 2, lg: 3 }} spacing={4} mb={4}>

            {/* CCC */}
            <MetricaCard
              titulo="Tu plata da la vuelta en"
              valor={ccc_dias}
              unit="días"
              subtexto="Compras → vendes → cobras. Menos días = mejor. Si sube, cobras más lento o pagas más rápido."
              tooltip="Ciclo de Conversión de Caja (CCC). Cuántos días tarda tu dinero en regresar después de que compras mercadería."
            />

            {/* Ratio liquidez */}
            <MetricaCard
              titulo={ratio_liquidez < 1 ? 'Atención: debes más de lo que cobrarás' : 'Liquidez'}
              valor={ratio_liquidez >= 99 ? '—' : `${fmt(ratio_liquidez, 1)}x`}
              subtexto={liquidezTexto}
              semaforo={semaforo_liquidez}
              tooltip="Ratio de liquidez: divide lo que te deben (CxC) + tu saldo entre lo que debes (CxP). Más de 1.2 es sano."
            />

            {/* DIO */}
            <MetricaCard
              titulo="Tu stock dura en venderse"
              valor={dio_dias}
              unit="días"
              subtexto="Si sube mucho, tienes mercadería parada. Si baja mucho, podrías quedarte sin stock."
              tooltip="Días de Inventario (DIO). Cuántos días tarda en venderse tu inventario actual al ritmo actual de ventas."
            />

            {/* DSO técnico */}
            <MetricaCard
              titulo="Promedio de días para cobrar"
              valor={dso_dias ?? '—'}
              unit={dso_dias != null ? 'días' : undefined}
              subtexto="Días promedio que tarda un cliente en pagarte. Calculado sobre los últimos 90 días."
              tooltip="Days Sales Outstanding (DSO). Métrica técnica de cobranza. Si sube, tus clientes te están demorando más."
            />

            {/* DPO técnico */}
            <MetricaCard
              titulo="Promedio de días que tardas en pagar"
              valor={dpo_dias ?? '—'}
              unit={dpo_dias != null ? 'días' : undefined}
              subtexto="Días promedio que tardas en pagar a tus proveedores. Más días = mejor para tu caja."
              tooltip="Days Payable Outstanding (DPO). Cuántos días tardas en pagar a proveedores. Calculado sobre últimos 90 días."
            />

            {/* Saldo neto */}
            <MetricaCard
              titulo="Saldo neto del mes"
              valor={`S/ ${fmtK(saldo_neto_mes)}`}
              semaforo={saldoSemaforo}
              delta={saldoDelta}
              subtexto="Cobros reales menos pagos reales del período. No incluye sueldos ni gastos fuera del sistema."
            />

          </SimpleGrid>

          {/* Concentración de clientes */}
          <Box
            bg={concentracion_alerta ? '#fffbeb' : '#f0fdf4'}
            border="1px solid"
            borderColor={concentracion_alerta ? '#f59e0b' : '#22c55e'}
            borderRadius="lg"
            p={4}
            mb={4}
          >
            <Flex justify="space-between" align="flex-start" wrap="wrap" gap={3}>
              <Box flex="1">
                <Text fontSize="sm" fontWeight="semibold" color="gray.700" mb={1}>
                  {concentracion_alerta
                    ? `Riesgo: el ${fmt(concentracion_top3_pct, 1)}% de tus ventas viene de solo 3 clientes`
                    : `Tus ventas están bien distribuidas (${fmt(concentracion_top3_pct, 1)}% viene de tus top 3)`}
                </Text>
                <Text fontSize="xs" color="gray.500">
                  {concentracion_alerta
                    ? 'Si pierdes a uno de ellos tu negocio se resiente. Busca diversificar tu cartera de clientes.'
                    : 'Ningún cliente tiene demasiado peso. Eso es sano — no dependes de uno solo.'}
                </Text>

                {top3_clientes.length > 0 && (
                  <HStack spacing={4} mt={3} flexWrap="wrap">
                    {top3_clientes.map((c, i) => (
                      <Box key={i}>
                        <Text fontSize="10px" color="gray.400">#{i + 1}</Text>
                        <Text fontSize="sm" fontWeight="medium" color="gray.700" noOfLines={1}>{c.nombre}</Text>
                        <Text fontSize="xs" color="gray.500">S/ {fmtK(c.total)}</Text>
                      </Box>
                    ))}
                  </HStack>
                )}
              </Box>

              <Button
                size="sm"
                variant="outline"
                borderColor={concentracion_alerta ? '#f59e0b' : '#22c55e'}
                color={concentracion_alerta ? '#92400e' : '#166534'}
                leftIcon={<Icon as={FiUsers} />}
                onClick={() => navigate('/app/clientes')}
                flexShrink={0}
                fontSize="xs"
              >
                Ver top clientes
              </Button>
            </Flex>
          </Box>

          {/* Índice de morosidad */}
          <Box
            bg={indice_morosidad_pct > 30 ? '#fff7ed' : '#f0fdf4'}
            border="1px solid"
            borderColor={indice_morosidad_pct > 50 ? '#ef4444' : indice_morosidad_pct > 30 ? '#f97316' : '#22c55e'}
            borderRadius="lg"
            p={4}
          >
            <Flex justify="space-between" align="center" wrap="wrap" gap={3}>
              <Box>
                <Text fontSize="sm" fontWeight="semibold" color="gray.700" mb={0.5}>
                  {`El ${fmt(indice_morosidad_pct, 0)}% de lo que te deben ya está vencido`}
                </Text>
                <Text fontSize="xs" color="gray.500">
                  {indice_morosidad_pct > 30
                    ? 'Nivel alto. Vale la pena hacer llamadas esta semana.'
                    : 'Nivel normal. Sigue así con tus cobranzas.'}
                </Text>
              </Box>
              {indice_morosidad_pct > 10 && (
                <Button
                  size="sm"
                  colorScheme={indice_morosidad_pct > 30 ? 'orange' : 'green'}
                  variant="outline"
                  onClick={() => navigate('/app/ventas')}
                  flexShrink={0}
                  fontSize="xs"
                >
                  Ver morosos
                </Button>
              )}
            </Flex>
          </Box>

        </Box>
      </Collapse>
    </Box>
  );
};

export default KPIsAvanzados;
