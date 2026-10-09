import React from 'react';
import { Text, Tooltip, Icon, HStack, Box } from '@chakra-ui/react';
import { FaInfoCircle, FaExclamationTriangle } from 'react-icons/fa';

/**
 * MontoConsolidado — muestra un monto YA consolidado a PEN por el backend.
 *
 * El frontend NUNCA suma montos. Recibe:
 *   value    : total_pen (number | string) ya consolidado en soles.
 *   desglose : { pen, usd, tc_promedio, tiene_usd, tc_estimado } (opcional).
 *
 * - Siempre renderiza "S/ x".
 * - Si desglose.tiene_usd → ícono ⓘ con tooltip de composición:
 *     "S/ 12,000 + $ 3,400 · TC prom. 3.45"
 * - Si desglose.tc_estimado → ícono ⚠ (algún documento USD sin TC histórico,
 *   valorizado con el TC actual estimado).
 */

const fmt = (n, d = 2) => {
  const num = Number(n) || 0;
  return num.toLocaleString('es-PE', { minimumFractionDigits: d, maximumFractionDigits: d });
};

// Versión string para contextos no-JSX (callbacks de ejes de gráficos, etc.)
export const formatPEN = (value, d = 2) => `S/ ${fmt(value, d)}`;

export const composicionTexto = (desglose) => {
  if (!desglose) return '';
  const partes = [];
  if (Number(desglose.pen) > 0) partes.push(`S/ ${fmt(desglose.pen)}`);
  if (Number(desglose.usd) > 0) partes.push(`$ ${fmt(desglose.usd)}`);
  let txt = partes.join(' + ');
  if (desglose.tc_promedio) txt += ` · TC prom. ${Number(desglose.tc_promedio).toFixed(3)}`;
  return txt;
};

const MontoConsolidado = ({
  value,
  desglose = null,
  decimals = 2,
  fontSize,
  fontWeight,
  color,
  ...rest
}) => {
  const tieneUsd    = desglose?.tiene_usd;
  const tcEstimado  = desglose?.tc_estimado;

  return (
    <HStack spacing={1} display="inline-flex" align="center" {...rest}>
      <Text as="span" fontSize={fontSize} fontWeight={fontWeight} color={color}>
        {formatPEN(value, decimals)}
      </Text>

      {tieneUsd && (
        <Tooltip
          hasArrow
          placement="top"
          label={
            <Box fontSize="xs" lineHeight="short">
              <Text fontWeight="bold" mb={0.5}>Equivalente en soles</Text>
              <Text>{composicionTexto(desglose)}</Text>
              <Text mt={1} opacity={0.8}>
                Cada documento en USD se valoriza al TC de su fecha de emisión.
              </Text>
            </Box>
          }
        >
          <span style={{ display: 'inline-flex' }}>
            <Icon as={FaInfoCircle} boxSize={3} color="blue.400" aria-label="Composición del monto" />
          </span>
        </Tooltip>
      )}

      {tcEstimado && (
        <Tooltip
          hasArrow
          placement="top"
          label="Incluye documentos en USD sin tipo de cambio histórico guardado; valorizados con el TC actual (estimado)."
        >
          <span style={{ display: 'inline-flex' }}>
            <Icon as={FaExclamationTriangle} boxSize={3} color="orange.400" aria-label="Tipo de cambio estimado" />
          </span>
        </Tooltip>
      )}
    </HStack>
  );
};

export default MontoConsolidado;
