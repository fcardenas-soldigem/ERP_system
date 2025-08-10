import React from 'react';
import { Box, SimpleGrid, Stat, StatLabel, StatNumber, StatHelpText, Heading, Spinner, Flex, useColorModeValue } from '@chakra-ui/react';
import { dashboardService } from '../../services/dashboard.service';
import UtilidadStats from '../Reportes/UtilidadStats';
import VentasStats from '../Reportes/VentasStats';
import ComprasStats from '../Reportes/ComprasStats';
import ProductosTopStats from '../Reportes/ProductosTopStats';
import ClientesTopStats from '../Reportes/ClientesTopStats';

function formatNumber(num, decimals = 2) {
  if (typeof num !== 'number') return num;
  return num.toLocaleString('es-PE', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function formatInteger(num) {
  if (typeof num !== 'number') return num;
  return num.toLocaleString('es-PE', { maximumFractionDigits: 0, minimumFractionDigits: 0 });
}

const Dashboard = () => {
  const [resumen, setResumen] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const boxBg = useColorModeValue('white', 'gray.800');
  const boxShadow = useColorModeValue('md', 'dark-lg');

  React.useEffect(() => {
    dashboardService.getResumen().then(data => {
      setResumen(data);
      setLoading(false);
    }).catch(error => {
      console.error('Error cargando el dashboard:', error);
      setLoading(false);
    });
  }, []);

  if (loading) return <Spinner size="xl" />;

  return (
    <Box p={6}>
      <Heading mb={6}>Dashboard General</Heading>
      <SimpleGrid columns={{ base: 1, md: 5 }} spacing={6} mb={8}>
        <Stat p={4} bg={boxBg} boxShadow={boxShadow} borderRadius="lg">
          <StatLabel fontSize="lg">Ventas</StatLabel>
          <StatNumber fontSize="2xl" color="blue.500">S/ {formatNumber(resumen.ventas?.total ?? 0)}</StatNumber>
          <StatHelpText>{formatInteger(resumen.ventas?.cantidad ?? 0)} ventas</StatHelpText>
        </Stat>
        <Stat p={4} bg={boxBg} boxShadow={boxShadow} borderRadius="lg">
          <StatLabel fontSize="lg">Compras</StatLabel>
          <StatNumber fontSize="2xl" color="green.500">S/ {formatNumber(resumen?.compras?.total ?? 0)}</StatNumber>
          <StatHelpText>{formatInteger(resumen?.compras?.cantidad ?? 0)} compras del mes</StatHelpText>
        </Stat>
        <Stat p={4} bg={boxBg} boxShadow={boxShadow} borderRadius="lg">
          <StatLabel fontSize="lg">Utilidad</StatLabel>
          <StatNumber fontSize="2xl" color="purple.500">S/ {formatNumber(resumen.utilidad?.total ?? 0)}</StatNumber>
          <StatHelpText>Margen: {formatNumber(resumen.utilidad?.margen ?? 0)}%</StatHelpText>
          <StatHelpText color="purple.700">Utilidad Bruta: S/ {formatNumber(resumen.utilidad?.utilidad_bruta ?? 0)}</StatHelpText>
          <StatHelpText color="red.600">Impuestos (18%): S/ {formatNumber(resumen.utilidad?.impuestos ?? 0)}</StatHelpText>
        </Stat>
        <Stat p={4} bg={boxBg} boxShadow={boxShadow} borderRadius="lg">
          <StatLabel fontSize="lg">Impuesto por Pagar (IGV)</StatLabel>
          <StatNumber fontSize="2xl" color="red.500">
            S/ {formatNumber(resumen.impuestos?.por_pagar ?? 0)}
          </StatNumber>
          <StatHelpText>IGV ventas: S/ {formatNumber(resumen.impuestos?.igv_ventas ?? 0)}<br/>IGV compras: S/ {formatNumber(resumen.impuestos?.igv_compras ?? 0)}</StatHelpText>
          <StatHelpText>IGV ventas - IGV compras (últimos 30 días)</StatHelpText>
        </Stat>
        <Stat p={4} bg={boxBg} boxShadow={boxShadow} borderRadius="lg">
          <StatLabel fontSize="lg">Inventario</StatLabel>
          <StatNumber fontSize="2xl" color="orange.500">{formatInteger(resumen.inventario?.total_productos ?? 0)} productos</StatNumber>
          <StatHelpText>
            Total: {formatInteger(resumen.inventario?.total_cantidad ?? 0)} unidades<br/>
            <Box as="span" color="red.500">
              {formatInteger(resumen.inventario?.productos_bajo_stock ?? 0)} bajos en stock
            </Box>
          </StatHelpText>
        </Stat>
      </SimpleGrid>
      <Flex direction={{ base: 'column', md: 'row' }} gap={6} mb={6}>
        <Box flex={1}>
          <UtilidadStats />
        </Box>
        <Box flex={1}>
          <VentasStats />
        </Box>
      </Flex>
      <Flex direction={{ base: 'column', md: 'row' }} gap={6} mb={6}>
        <Box flex={1}>
          <ComprasStats />
        </Box>
        <Box flex={1}>
          <ProductosTopStats />
        </Box>
      </Flex>
      <Flex direction={{ base: 'column', md: 'row' }} gap={6}>
        <Box flex={1}>
          <ClientesTopStats />
        </Box>
      </Flex>
    </Box>
  );
};

export default Dashboard; 