import React from 'react';
import {
  Box, Flex, Text, Badge, Icon,
  useColorModeValue,
} from '@chakra-ui/react';
import { FiArrowUpRight, FiArrowDownRight } from 'react-icons/fi';
import Sparkline from './Sparkline';

/**
 * Single stat card with sparkline.
 *
 * Props:
 *  label        string
 *  value        string   — already formatted
 *  sub          string   — secondary info
 *  sparkData    number[] — last N days
 *  trend        number   — % change (positive = up)
 *  accentColor  string   — CSS color for sparkline
 *  alert        string?  — red badge text if urgent
 *  pulseBadge   boolean  — pulsing red dot for critical alerts
 */
const StatCard = ({
  label,
  value,
  sub,
  sparkData = [],
  trend,
  accentColor = '#3b6feb',
  alert,
  pulseBadge = false,
}) => {
  const bg     = useColorModeValue('white', 'gray.800');
  const border = useColorModeValue('gray.100', 'gray.700');
  const subCol = useColorModeValue('gray.400', 'gray.500');

  const trendUp      = trend > 0;
  const trendColor   = trend === undefined ? 'gray.400'
    : trendUp ? 'green.500' : 'red.500';
  const TrendIcon    = trendUp ? FiArrowUpRight : FiArrowDownRight;
  const sparkColor   = trend === undefined ? accentColor
    : trendUp ? '#22c55e' : '#ef4444';

  return (
    <Box
      bg={bg}
      border="1px solid"
      borderColor={border}
      borderRadius="xl"
      p={5}
      display="flex"
      flexDirection="column"
      gap={3}
      transition="box-shadow 0.2s, border-color 0.2s"
      cursor="default"
      _hover={{
        boxShadow: '0 4px 20px rgba(0,0,0,0.09)',
        borderColor: 'gray.200',
      }}
      /* mobile carousel: each card takes 75vw so one is always visible */
      minW={{ base: '72vw', sm: 'unset' }}
      scrollSnapAlign={{ base: 'start', sm: 'none' }}
    >
      {/* Label row */}
      <Flex justify="space-between" align="center">
        <Text
          fontSize="10px"
          fontWeight="semibold"
          color={subCol}
          textTransform="uppercase"
          letterSpacing="wider"
        >
          {label}
        </Text>
        {pulseBadge && alert && (
          <Box position="relative" display="inline-flex">
            <Box
              position="absolute"
              borderRadius="full"
              w="8px" h="8px"
              bg="red.500"
              opacity={0.75}
              animation="ping 1.2s cubic-bezier(0,0,0.2,1) infinite"
              sx={{
                '@keyframes ping': {
                  '75%, 100%': { transform: 'scale(2)', opacity: 0 },
                },
              }}
            />
            <Box w="8px" h="8px" borderRadius="full" bg="red.500" />
          </Box>
        )}
      </Flex>

      {/* Value + trend */}
      <Flex align="baseline" gap={2}>
        <Text
          fontSize="2xl"
          fontWeight="bold"
          color="gray.900"
          fontVariantNumeric="tabular-nums"
          lineHeight="1"
        >
          {value}
        </Text>
        {trend !== undefined && (
          <Flex align="center" gap={0.5}>
            <Icon as={TrendIcon} color={trendColor} boxSize="14px" />
            <Text fontSize="xs" fontWeight="semibold" color={trendColor}>
              {Math.abs(trend).toFixed(1)}%
            </Text>
          </Flex>
        )}
      </Flex>

      {/* Sparkline */}
      {sparkData.length > 1 && (
        <Box h="30px" mx={-1}>
          <Sparkline data={sparkData} color={sparkColor} height={30} />
        </Box>
      )}

      {/* Sub text + alert badge */}
      <Flex align="center" justify="space-between" mt="auto">
        {sub && (
          <Text fontSize="xs" color={subCol}>
            {sub}
          </Text>
        )}
        {alert && !pulseBadge && (
          <Badge colorScheme="red" variant="subtle" fontSize="10px" borderRadius="sm">
            {alert}
          </Badge>
        )}
        {alert && pulseBadge && (
          <Text fontSize="xs" fontWeight="semibold" color="red.500">{alert}</Text>
        )}
      </Flex>
    </Box>
  );
};

export default StatCard;
