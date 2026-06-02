import React from 'react';
import {
  Box, Flex, Text, Progress,
  Skeleton, useColorModeValue,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';

const RANK_COLORS = ['#3b6feb', '#7c3aed', '#0891b2', '#059669', '#d97706'];

const TopProducts = () => {
  const border  = useColorModeValue('gray.100', 'gray.700');
  const subCol  = useColorModeValue('gray.400', 'gray.500');

  const { data, isLoading } = useQuery({
    queryKey: ['dashboard-top-products'],
    queryFn: () => api.get('/api/ventas/productos_mas_vendidos/')
      .then(r => {
        const labels = r.data?.labels ?? [];
        const vals   = r.data?.data   ?? [];
        return labels.map((name, i) => ({ name, qty: vals[i] ?? 0 }));
      }),
    staleTime: 5 * 60 * 1000,
  });

  const products = (data ?? []).slice(0, 5);
  const maxQty   = products[0]?.qty ?? 1;

  return (
    <Box
      bg={useColorModeValue('white', 'gray.800')}
      border="1px solid"
      borderColor={border}
      borderRadius="xl"
      overflow="hidden"
    >
      <Flex px={5} py={4} borderBottom="1px solid" borderColor={border}>
        <Text fontSize="sm" fontWeight="semibold" color="gray.700">
          Top productos del mes
        </Text>
      </Flex>

      <Box px={5} py={3}>
        {isLoading
          ? [1, 2, 3, 4, 5].map(i => (
              <Flex key={i} align="center" gap={3} py={2.5}>
                <Skeleton w="20px" h="20px" borderRadius="sm" />
                <Box flex="1">
                  <Skeleton h="12px" w="60%" mb={1.5} />
                  <Skeleton h="6px" borderRadius="full" />
                </Box>
              </Flex>
            ))
          : products.length === 0
          ? (
            <Flex justify="center" py={8}>
              <Text fontSize="sm" color={subCol}>Sin datos este mes</Text>
            </Flex>
          )
          : products.map(({ name, qty }, i) => (
              <Flex key={name} align="center" gap={3} py={2.5}>
                {/* Rank number */}
                <Text
                  w="20px"
                  textAlign="center"
                  fontSize="xs"
                  fontWeight="bold"
                  color={RANK_COLORS[i]}
                >
                  #{i + 1}
                </Text>

                <Box flex="1" minW={0}>
                  <Flex justify="space-between" mb={1.5}>
                    <Text
                      fontSize="sm"
                      fontWeight="medium"
                      color="gray.800"
                      noOfLines={1}
                    >
                      {name}
                    </Text>
                    <Text
                      fontSize="xs"
                      fontWeight="semibold"
                      color={subCol}
                      ml={2}
                      flexShrink={0}
                    >
                      {qty} un.
                    </Text>
                  </Flex>

                  <Progress
                    value={(qty / maxQty) * 100}
                    size="xs"
                    colorScheme="blue"
                    borderRadius="full"
                    bg="gray.100"
                    sx={{
                      '& > div': {
                        background: RANK_COLORS[i],
                        borderRadius: 'full',
                        transition: 'width 0.6s ease',
                      }
                    }}
                  />
                </Box>
              </Flex>
            ))
        }
      </Box>
    </Box>
  );
};

export default TopProducts;
