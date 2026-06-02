import React, { useState } from 'react';
import {
  Box, Flex, Text, Heading, HStack, Button,
  Select, Skeleton, VStack, useColorModeValue, Divider,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { finanzasService } from '../../services/finanzas.service';

import IGVCard             from '../../components/Finanzas/IGVCard';
import SemaforoFinanciero  from '../../components/Finanzas/SemaforoFinanciero';
import FlujoCajaChart      from '../../components/Finanzas/FlujoCajaChart';
import AgingTable          from '../../components/Finanzas/AgingTable';
import RentabilidadSection from '../../components/Finanzas/RentabilidadSection';
import CrecimientoSection  from '../../components/Finanzas/CrecimientoSection';
import KPIsAvanzados       from '../../components/Finanzas/KPIsAvanzados';

const SectionTitle = ({ children }) => (
  <Text
    fontSize="xs"
    fontWeight="semibold"
    color="gray.400"
    textTransform="uppercase"
    letterSpacing="wider"
    mb={4}
  >
    {children}
  </Text>
);

const LoadingSkeleton = () => (
  <VStack spacing={4} align="stretch">
    <Skeleton h="100px" borderRadius="xl" />
    <Skeleton h="80px"  borderRadius="xl" />
    <Skeleton h="220px" borderRadius="xl" />
    <HStack spacing={4}>
      <Skeleton flex="1" h="130px" borderRadius="xl" />
      <Skeleton flex="1" h="130px" borderRadius="xl" />
    </HStack>
    <HStack spacing={4}>
      <Skeleton flex="1" h="110px" borderRadius="xl" />
      <Skeleton flex="1" h="110px" borderRadius="xl" />
      <Skeleton flex="1" h="110px" borderRadius="xl" />
    </HStack>
    <Skeleton h="300px" borderRadius="xl" />
  </VStack>
);

const FinanzasPage = () => {
  const [periodo, setPeriodo] = useState('mes');
  const bg = useColorModeValue('gray.50', 'gray.900');

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['finanzas-dashboard', periodo],
    queryFn: () => finanzasService.getDashboard({ periodo }),
    staleTime: 5 * 60 * 1000,
    retry: 2,
  });

  return (
    <Box bg={bg} minH="100vh" px={{ base: 4, md: 6 }} py={6}>

      {/* ── Header ── */}
      <Flex justify="space-between" align="center" mb={6} wrap="wrap" gap={3}>
        <Box>
          <Heading size="md" fontWeight="semibold">Finanzas</Heading>
          <Text fontSize="xs" color="gray.400" mt={0.5}>
            Cómo está tu negocio hoy
          </Text>
        </Box>

        <HStack spacing={3}>
          <Select
            size="sm"
            value={periodo}
            onChange={e => setPeriodo(e.target.value)}
            w="140px"
            borderRadius="lg"
            fontSize="sm"
          >
            <option value="semana">Esta semana</option>
            <option value="mes">Este mes</option>
            <option value="trimestre">Este trimestre</option>
          </Select>
          <Button size="sm" variant="ghost" onClick={refetch} fontSize="sm">
            Actualizar
          </Button>
        </HStack>
      </Flex>

      {isLoading && <LoadingSkeleton />}

      {error && !isLoading && (
        <Box bg="red.50" border="1px solid" borderColor="red.200" borderRadius="xl" p={6} textAlign="center">
          <Text color="red.700" fontWeight="medium">No se pudieron cargar los indicadores.</Text>
          <Button size="sm" colorScheme="red" variant="outline" mt={3} onClick={refetch}>
            Reintentar
          </Button>
        </Box>
      )}

      {data && !isLoading && (
        <VStack spacing={6} align="stretch">

          {/* ════════════════════════════════════════
              NIVEL PRINCIPAL — siempre visible
          ════════════════════════════════════════ */}

          {/* 1. IGV por pagar — lo primero para cualquier negocio en Perú */}
          <IGVCard obligaciones={data.obligaciones_fiscales} />

          {/* 2. Semáforo — diagnóstico instantáneo */}
          <SemaforoFinanciero semaforo={data.semaforo} />

          {/* 3. Flujo de caja */}
          <Box>
            <SectionTitle>Tu caja este mes</SectionTitle>
            <FlujoCajaChart flujo={data.flujo_caja} />
          </Box>

          {/* 4. Cobros y pagos — DSO/DPO en lenguaje llano + WhatsApp */}
          <Box>
            <SectionTitle>Lo que te deben y lo que debes</SectionTitle>
            <AgingTable cxc={data.cuentas_cobrar} cxp={data.cuentas_pagar} />
          </Box>

          {/* 5. Rentabilidad — margen en lenguaje llano */}
          <Box>
            <SectionTitle>Cuánto te queda después de costos</SectionTitle>
            <RentabilidadSection rentabilidad={data.rentabilidad} />
          </Box>

          {/* 6. Crecimiento */}
          <Box>
            <SectionTitle>Cómo está creciendo tu negocio</SectionTitle>
            <CrecimientoSection crecimiento={data.crecimiento} />
          </Box>

          <Divider borderColor="gray.200" />

          {/* ════════════════════════════════════════
              NIVEL AVANZADO — colapsado por default
          ════════════════════════════════════════ */}
          <KPIsAvanzados avanzados={data.avanzados} />

          {/* Footer */}
          <Text fontSize="xs" color="gray.300" textAlign="center" pb={2}>
            Datos al {data.meta?.generado_en} · Período: {data.meta?.fecha_inicio} → {data.meta?.fecha_fin}
          </Text>

        </VStack>
      )}
    </Box>
  );
};

export default FinanzasPage;
