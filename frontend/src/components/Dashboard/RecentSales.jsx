import React from 'react';
import {
  Box, Flex, Text, Badge, Button,
  Table, Tbody, Tr, Td,
  Skeleton, SkeletonText,
  useColorModeValue,
} from '@chakra-ui/react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

const ESTADO_COLORS = {
  pagado:   'green',
  pendiente:'yellow',
  borrador: 'gray',
  anulado:  'red',
};

const ESTADO_LABELS = {
  pagado:   'Pagado',
  pendiente:'Pendiente',
  borrador: 'Borrador',
  anulado:  'Anulado',
};

const RecentSales = () => {
  const navigate = useNavigate();
  const border   = useColorModeValue('gray.50', 'gray.700');
  const hoverBg  = useColorModeValue('gray.50', 'gray.750');
  const subColor = useColorModeValue('gray.400', 'gray.500');

  const { data, isLoading } = useQuery({
    queryKey: ['dashboard-recent-sales'],
    queryFn: () => api.get('/api/ventas/', { params: { page: 1, page_size: 5 } })
      .then(r => r.data?.results ?? r.data ?? []),
    staleTime: 2 * 60 * 1000,
  });

  const ventas = Array.isArray(data) ? data : [];

  const fmt = (n) => Number(n).toLocaleString('es-PE', {
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  });

  return (
    <Box
      bg={useColorModeValue('white', 'gray.800')}
      border="1px solid"
      borderColor={useColorModeValue('gray.100', 'gray.700')}
      borderRadius="xl"
      overflow="hidden"
    >
      {/* Header */}
      <Flex justify="space-between" align="center" px={5} py={4} borderBottom="1px solid" borderColor={border}>
        <Text fontSize="sm" fontWeight="semibold" color="gray.700">
          Últimas ventas
        </Text>
        <Button
          size="xs"
          variant="ghost"
          colorScheme="blue"
          fontWeight="medium"
          onClick={() => navigate('/app/ventas')}
        >
          Ver todas →
        </Button>
      </Flex>

      {/* Table */}
      {isLoading ? (
        <Box p={5}>
          {[1, 2, 3, 4, 5].map(i => (
            <Flex key={i} justify="space-between" align="center" py={3}>
              <SkeletonText noOfLines={2} w="40%" skeletonHeight="12px" spacing={2} />
              <Skeleton h="20px" w="80px" borderRadius="sm" />
            </Flex>
          ))}
        </Box>
      ) : ventas.length === 0 ? (
        <Flex justify="center" align="center" py={10}>
          <Text color={subColor} fontSize="sm">Sin ventas registradas</Text>
        </Flex>
      ) : (
        <Table size="sm" variant="unstyled">
          <Tbody>
            {ventas.map((v) => (
              <Tr
                key={v.id}
                _hover={{ bg: hoverBg }}
                cursor="pointer"
                onClick={() => navigate(`/app/ventas/${v.id}`)}
                transition="background 0.1s"
              >
                <Td px={5} py={3} borderBottom="1px solid" borderColor={border}>
                  <Text fontSize="sm" fontWeight="medium" color="gray.800" noOfLines={1}>
                    {v.cliente?.nombre ?? v.cliente_nombre ?? '—'}
                  </Text>
                  <Text fontSize="xs" color={subColor}>
                    {v.numero} · {v.fecha_emision
                      ? format(new Date(v.fecha_emision), 'd MMM', { locale: es })
                      : '—'}
                  </Text>
                </Td>

                <Td px={5} py={3} textAlign="right" borderBottom="1px solid" borderColor={border}>
                  <Text fontSize="sm" fontWeight="semibold" color="gray.900"
                        fontVariantNumeric="tabular-nums">
                    {v.moneda === 'USD' ? '$' : 'S/'} {fmt(v.total)}
                  </Text>
                  <Flex justify="flex-end" gap={2} align="center" mt={0.5}>
                    <Badge
                      colorScheme={ESTADO_COLORS[v.estado] ?? 'gray'}
                      variant="subtle"
                      fontSize="10px"
                      borderRadius="sm"
                      textTransform="none"
                    >
                      {ESTADO_LABELS[v.estado] ?? v.estado}
                    </Badge>
                    {v.estado === 'pendiente' && (
                      <Button
                        size="xs"
                        colorScheme="green"
                        variant="solid"
                        borderRadius="full"
                        h="18px"
                        fontSize="10px"
                        px={2}
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/app/ventas/${v.id}/pagos/nuevo`);
                        }}
                      >
                        Cobrar
                      </Button>
                    )}
                  </Flex>
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      )}
    </Box>
  );
};

export default RecentSales;
