import React from 'react';
import {
  Box, Flex, Text, HStack, VStack, Button, Icon,
  Tooltip as ChakraTooltip, useColorModeValue,
} from '@chakra-ui/react';
import { FiInfo } from 'react-icons/fi';

const SEMAFORO = {
  verde:    { border: '#22c55e', accent: '#166534', bg: 'white' },
  amarillo: { border: '#f59e0b', accent: '#92400e', bg: 'white' },
  rojo:     { border: '#ef4444', accent: '#991b1b', bg: '#fff1f2' },
  neutro:   { border: '#e5e7eb', accent: '#374151', bg: 'white' },
};

const KPICard = ({
  titulo,
  valor,
  valor_tecnico,
  insight,
  insightColor,
  tooltip,
  accion,
  semaforo = 'neutro',
  children,
}) => {
  const base = useColorModeValue('gray.100', 'gray.700');
  const cfg = SEMAFORO[semaforo] ?? SEMAFORO.neutro;
  const borderColor = semaforo !== 'neutro' ? cfg.border : base;

  return (
    <Box
      bg={cfg.bg}
      border="1px solid"
      borderColor={borderColor}
      borderRadius="xl"
      p={5}
      h="100%"
      display="flex"
      flexDirection="column"
      justifyContent="space-between"
    >
      <VStack align="flex-start" spacing={2} flex="1">

        {/* Título en lenguaje cotidiano */}
        <HStack spacing={1.5} align="flex-start">
          <Text fontSize="sm" fontWeight="semibold" color="gray.700" lineHeight="snug">
            {titulo}
          </Text>
          {tooltip && (
            <ChakraTooltip label={tooltip} hasArrow placement="top" fontSize="xs" maxW="240px">
              <span style={{ marginTop: '2px', flexShrink: 0 }}>
                <Icon as={FiInfo} color="gray.300" boxSize="12px" cursor="help" />
              </span>
            </ChakraTooltip>
          )}
        </HStack>

        {/* Valor principal */}
        {valor && (
          <Text fontSize="2xl" fontWeight="bold" color="gray.900" fontVariantNumeric="tabular-nums" lineHeight="1">
            {valor}
          </Text>
        )}

        {/* Dato técnico como subtexto */}
        {valor_tecnico && (
          <Text fontSize="10px" color="gray.400" fontWeight="medium" letterSpacing="wide">
            {valor_tecnico}
          </Text>
        )}

        {/* Insight accionable */}
        {insight && (
          <Text fontSize="xs" color={insightColor ?? cfg.accent} fontWeight="medium" lineHeight="short">
            {insight}
          </Text>
        )}

        {children}
      </VStack>

      {/* Botón de acción */}
      {accion && (
        <Button
          size="sm"
          variant="outline"
          borderColor={borderColor}
          color={cfg.accent}
          _hover={{ bg: semaforo !== 'neutro' ? cfg.border : 'gray.50', color: semaforo !== 'neutro' ? 'white' : 'gray.900' }}
          onClick={accion.onClick}
          mt={4}
          fontSize="xs"
          fontWeight="semibold"
          w="full"
        >
          {accion.label}
        </Button>
      )}
    </Box>
  );
};

export default KPICard;
