import React from 'react';
import { Box, Flex, Text, VStack, HStack, Badge, Icon } from '@chakra-ui/react';
import { FiAlertTriangle, FiCheckCircle, FiAlertOctagon } from 'react-icons/fi';

const CONFIG = {
  verde:    { bg: '#f0fdf5', border: '#22c55e', text: '#166534', icon: FiCheckCircle,    iconColor: '#22c55e' },
  amarillo: { bg: '#fffbeb', border: '#f59e0b', text: '#92400e', icon: FiAlertTriangle,  iconColor: '#f59e0b' },
  rojo:     { bg: '#fff1f2', border: '#ef4444', text: '#991b1b', icon: FiAlertOctagon,   iconColor: '#ef4444' },
};

const NIVEL_COLORS = { rojo: 'red', amarillo: 'orange', verde: 'green' };

const SemaforoFinanciero = ({ semaforo }) => {
  if (!semaforo) return null;
  const { color, puntuacion, mensaje, alertas = [] } = semaforo;
  const cfg = CONFIG[color] ?? CONFIG.amarillo;

  return (
    <Box
      bg={cfg.bg}
      border="1px solid"
      borderColor={cfg.border}
      borderRadius="xl"
      p={5}
      mb={6}
    >
      <Flex align="center" justify="space-between" wrap="wrap" gap={4}>
        <HStack spacing={3}>
          <Icon as={cfg.icon} color={cfg.iconColor} boxSize="24px" />
          <VStack align="flex-start" spacing={0}>
            <Text fontWeight="bold" color={cfg.text} fontSize="md">
              {mensaje}
            </Text>
            <Text fontSize="xs" color={cfg.text} opacity={0.7}>
              Salud financiera: {puntuacion}/100
            </Text>
          </VStack>
        </HStack>

        {alertas.length > 0 && (
          <HStack spacing={2} flexWrap="wrap">
            {alertas.map((a, i) => (
              <Badge
                key={i}
                colorScheme={NIVEL_COLORS[a.nivel] ?? 'gray'}
                variant="subtle"
                fontSize="xs"
                borderRadius="full"
                px={3}
                py={1}
              >
                {a.mensaje}
              </Badge>
            ))}
          </HStack>
        )}
      </Flex>
    </Box>
  );
};

export default SemaforoFinanciero;
