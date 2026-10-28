import React from 'react';
import { Box, Text, Tooltip, Icon, HStack } from '@chakra-ui/react';
import { Info } from 'lucide-react';

/**
 * StatCard — card de métrica estándar.
 * label (caption gris) · valor (tabular-nums) · sublabel · tooltip opcional.
 * valor null/undefined → estado vacío ("—" + sublabel), nunca 0 inventado.
 */
const StatCard = ({ label, value, valueNode, sublabel, tooltip, accent, ...rest }) => {
  const vacio = valueNode == null && (value === null || value === undefined);
  return (
    <Box bg="white" border="1px solid" borderColor="neutral.200" borderRadius="lg" p={5} {...rest}>
      <HStack spacing={1} mb={2}>
        <Text fontSize="xs" fontWeight="semibold" color="neutral.600"
              textTransform="uppercase" letterSpacing="wider">
          {label}
        </Text>
        {tooltip && (
          <Tooltip label={tooltip} hasArrow placement="top" fontSize="xs" maxW="260px">
            <span style={{ display: 'inline-flex' }}>
              <Icon as={Info} boxSize="11px" color="neutral.400" />
            </span>
          </Tooltip>
        )}
      </HStack>
      {valueNode ?? (
        <Text fontSize="2xl" fontWeight="bold" data-stat
              color={vacio ? 'neutral.400' : (accent ?? 'neutral.900')}>
          {vacio ? '—' : value}
        </Text>
      )}
      {sublabel && (
        <Text fontSize="xs" color="neutral.400" mt={1}>{sublabel}</Text>
      )}
    </Box>
  );
};

export default StatCard;
