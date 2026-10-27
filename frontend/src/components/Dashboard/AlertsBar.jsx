import React from 'react';
import { Box, Flex, Text, Button, Icon } from '@chakra-ui/react';
import { useNavigate } from 'react-router-dom';
import { FiAlertTriangle, FiClock, FiPackage, FiChevronRight } from 'react-icons/fi';

const LEVEL_STYLES = {
  urgent:  { border: '#ef4444', bg: '#fef2f2', icon: FiAlertTriangle, iconColor: '#ef4444' },
  warning: { border: '#f59e0b', bg: '#fffbeb', icon: FiClock,         iconColor: '#f59e0b' },
  info:    { border: '#3b6feb', bg: '#eff4ff', icon: FiPackage,        iconColor: '#3b6feb' },
};

const AlertCard = ({ message, actionLabel, actionPath, level = 'warning' }) => {
  const navigate = useNavigate();
  const { border, bg, icon, iconColor } = LEVEL_STYLES[level] ?? LEVEL_STYLES.info;

  return (
    <Box
      bg={bg}
      borderLeft="3px solid"
      borderLeftColor={border}
      borderRadius="lg"
      px={4}
      py={3}
      minW={{ base: '80vw', sm: '260px', lg: '220px' }}
      maxW={{ base: '80vw', sm: '300px', lg: '280px' }}
      flexShrink={0}
      scrollSnapAlign="start"
    >
      <Flex align="flex-start" gap={2.5}>
        <Icon as={icon} color={iconColor} mt="2px" flexShrink={0} />
        <Box flex="1" minW={0}>
          <Text fontSize="xs" fontWeight="medium" color="gray.700" lineHeight="short">
            {message}
          </Text>
          {actionLabel && actionPath && (
            <Button
              size="xs"
              variant="link"
              color={iconColor}
              fontWeight="semibold"
              mt={1.5}
              p={0}
              h="auto"
              onClick={() => navigate(actionPath)}
            >
              {actionLabel} →
            </Button>
          )}
        </Box>
      </Flex>
    </Box>
  );
};

// Móvil: una fila tocable por alerta dentro de una sola tarjeta blanca.
// El color queda solo en el ícono — menos ruido que cuatro fondos de color.
const AlertRow = ({ message, actionLabel, actionPath, level = 'warning', primera }) => {
  const navigate = useNavigate();
  const { icon, iconColor } = LEVEL_STYLES[level] ?? LEVEL_STYLES.info;
  return (
    <Flex
      as="button"
      type="button"
      aria-label={actionLabel ? `${message}. ${actionLabel}` : message}
      onClick={() => actionPath && navigate(actionPath)}
      w="100%"
      minH="52px"
      px={4}
      py={3}
      gap={3}
      align="center"
      textAlign="left"
      borderTop={primera ? 'none' : '1px solid'}
      borderColor="neutral.100"
      _dark={{ borderColor: 'gray.700' }}
      _active={{ bg: 'neutral.50', _dark: { bg: 'whiteAlpha.100' } }}
      sx={{ WebkitTapHighlightColor: 'transparent' }}
    >
      <Icon as={icon} color={iconColor} boxSize="16px" flexShrink={0} />
      <Text flex="1" fontSize="13px" lineHeight="18px" color="neutral.700" _dark={{ color: 'neutral.200' }}>
        {message}
      </Text>
      {actionPath && <Icon as={FiChevronRight} color="neutral.400" boxSize="16px" flexShrink={0} />}
    </Flex>
  );
};

/**
 * AlertsBar — horizontal scrollable strip of alert cards.
 * Only renders if there are alerts.
 *
 * alerts: Array<{ message, actionLabel, actionPath, level }>
 */
const AlertsBar = ({ alerts = [], apiladas = false }) => {
  if (!alerts.length) return null;

  // Móvil: una debajo de otra, ancho completo — sin carrusel que esconda alertas.
  if (apiladas) {
    return (
      <Box
        bg="white"
        border="1px solid"
        borderColor="neutral.200"
        borderRadius="xl"
        overflow="hidden"
        _dark={{ bg: 'gray.800', borderColor: 'gray.700' }}
      >
        {alerts.map((a, i) => <AlertRow key={i} {...a} primera={i === 0} />)}
      </Box>
    );
  }

  return (
    <Box>
      <Text fontSize="xs" fontWeight="semibold" color="gray.400"
            textTransform="uppercase" letterSpacing="wider" mb={3}>
        Alertas
      </Text>
      <Box position="relative">
        {/* Right fade — transparent to gray.50 matches Dashboard bg (F-009 fix) */}
        <Box
          position="absolute"
          right={0} top={0} bottom={0}
          w="48px"
          bgGradient="linear(to-r, transparent, gray.50)"
          _dark={{ bgGradient: 'linear(to-r, transparent, gray.900)' }}
          zIndex={1}
          pointerEvents="none"
        />
        <Flex
          gap={3}
          overflowX="auto"
          pb={1}
          sx={{
            scrollSnapType: 'x mandatory',
            scrollBehavior: 'smooth',
            '&::-webkit-scrollbar': { display: 'none' },
            msOverflowStyle: 'none',
            scrollbarWidth: 'none',
          }}
        >
          {alerts.map((a, i) => (
            <AlertCard key={i} {...a} />
          ))}
        </Flex>
      </Box>
    </Box>
  );
};

export default AlertsBar;
