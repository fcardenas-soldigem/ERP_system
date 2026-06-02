import React, { useState, useEffect } from 'react';
import {
  Box, SimpleGrid, Heading, Text, Button, HStack, VStack,
  Divider, Progress, Stat, StatLabel, StatNumber, StatHelpText,
} from '@chakra-ui/react';
import { FaBalanceScale, FaMoneyBillWave, FaFileInvoice } from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';

const ResumenCuentas = () => {
  const [resumen, setResumen] = useState({
    total_por_cobrar: 0,
    total_por_pagar: 0,
    ventas_pendientes: 0,
    compras_pendientes: 0,
    proximos_vencimientos_cobrar: [],
    proximos_vencimientos_pagar: []
  });
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchResumen();
  }, []);

  const fetchResumen = async () => {
    try {
      const response = await fetch('/api/cuentas/resumen/');
      const data = await response.json();
      setResumen(data);
    } catch (error) {
      console.error('Error al obtener el resumen:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('es-PE', {
      style: 'currency',
      currency: 'PEN'
    }).format(amount);
  };

  if (loading) {
    return <Progress size="sm" isIndeterminate mt={4} />;
  }

  return (
    <Box p={6}>
      <Heading size="lg" mb={6}>Resumen de Cuentas</Heading>

      <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6} mb={6}>
        <Box bg="white" p={5} borderRadius="lg" shadow="sm" border="1px" borderColor="gray.200">
          <HStack spacing={4}>
            <Box as={FaBalanceScale} size="40px" color="blue.500" />
            <Stat>
              <StatLabel>Balance General</StatLabel>
              <StatNumber color="blue.600">
                {formatCurrency(resumen.total_por_cobrar - resumen.total_por_pagar)}
              </StatNumber>
            </Stat>
          </HStack>
        </Box>

        <Box bg="white" p={5} borderRadius="lg" shadow="sm" border="1px" borderColor="gray.200">
          <HStack spacing={4}>
            <Box as={FaMoneyBillWave} size="40px" color="green.500" />
            <Stat>
              <StatLabel>Por Cobrar</StatLabel>
              <StatNumber color="green.500">
                {formatCurrency(resumen.total_por_cobrar)}
              </StatNumber>
              <StatHelpText>{resumen.ventas_pendientes} ventas pendientes</StatHelpText>
            </Stat>
          </HStack>
        </Box>

        <Box bg="white" p={5} borderRadius="lg" shadow="sm" border="1px" borderColor="gray.200">
          <HStack spacing={4}>
            <Box as={FaFileInvoice} size="40px" color="red.500" />
            <Stat>
              <StatLabel>Por Pagar</StatLabel>
              <StatNumber color="red.500">
                {formatCurrency(resumen.total_por_pagar)}
              </StatNumber>
              <StatHelpText>{resumen.compras_pendientes} compras pendientes</StatHelpText>
            </Stat>
          </HStack>
        </Box>
      </SimpleGrid>

      <Box bg="white" p={5} borderRadius="lg" shadow="sm" border="1px" borderColor="gray.200" mb={6}>
        <Heading size="sm" mb={4}>Acciones Rápidas</Heading>
        <HStack spacing={4}>
          <Button colorScheme="blue" onClick={() => navigate('/app/cuentas/por-cobrar')}>
            Ver Cuentas por Cobrar
          </Button>
          <Button colorScheme="purple" onClick={() => navigate('/app/cuentas/por-pagar')}>
            Ver Cuentas por Pagar
          </Button>
        </HStack>
      </Box>

      <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
        <Box bg="white" p={5} borderRadius="lg" shadow="sm" border="1px" borderColor="gray.200">
          <Heading size="sm" mb={3}>Próximos Vencimientos por Cobrar</Heading>
          <Divider mb={3} />
          {resumen.proximos_vencimientos_cobrar.map((v) => (
            <Box key={v.id} mb={3}>
              <Text fontWeight="medium">{v.cliente} - {formatCurrency(v.monto)}</Text>
              <Text fontSize="sm" color="gray.500">
                Vence el: {new Date(v.fecha_vencimiento).toLocaleDateString()}
              </Text>
            </Box>
          ))}
        </Box>

        <Box bg="white" p={5} borderRadius="lg" shadow="sm" border="1px" borderColor="gray.200">
          <Heading size="sm" mb={3}>Próximos Vencimientos por Pagar</Heading>
          <Divider mb={3} />
          {resumen.proximos_vencimientos_pagar.map((v) => (
            <Box key={v.id} mb={3}>
              <Text fontWeight="medium">{v.proveedor} - {formatCurrency(v.monto)}</Text>
              <Text fontSize="sm" color="gray.500">
                Vence el: {new Date(v.fecha_vencimiento).toLocaleDateString()}
              </Text>
            </Box>
          ))}
        </Box>
      </SimpleGrid>
    </Box>
  );
};

export default ResumenCuentas;
