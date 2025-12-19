import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Spinner,
  Alert,
  AlertIcon,
  AlertDescription,
  Text,
  Heading,
  Grid,
  GridItem,
  Card,
  CardBody,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  VStack,
  useToast,
} from '@chakra-ui/react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import mlService from '../../services/mlService';

const COLORS = {
  'Champions': '#4caf50',
  'Loyal Customers': '#2196f3',
  'Potential': '#ff9800',
  'At Risk': '#ff5722',
  'Lost': '#9e9e9e',
};

const CustomerSegmentation = ({ status }) => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const toast = useToast();

  const hasModel = status?.models?.find(m => m.type === 'rfm_segmentation')?.has_model;

  useEffect(() => {
    if (hasModel) {
      loadSegmentation();
    }
  }, [hasModel]);

  const loadSegmentation = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await mlService.predictRFM();
      setData(response.data);
    } catch (err) {
      console.error('Error cargando segmentación:', err);
      setError(err.response?.data?.error || 'Error al cargar segmentación');
    } finally {
      setLoading(false);
    }
  };

  if (!hasModel) {
    return (
      <Alert status="warning">
        <AlertIcon />
        <AlertDescription>
          El modelo de segmentación RFM no ha sido entrenado aún. Haz clic en "Entrenar Modelos" para comenzar.
        </AlertDescription>
      </Alert>
    );
  }

  if (loading) {
    return (
      <Box textAlign="center" py={10}>
        <Spinner size="xl" />
        <Text mt={4}>Cargando segmentación...</Text>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert status="error">
        <AlertIcon />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (!data) {
    return (
      <Box textAlign="center" py={10}>
        <Text color="gray.500">No hay datos disponibles</Text>
        <Button mt={4} colorScheme="blue" onClick={loadSegmentation}>
          Cargar Segmentación
        </Button>
      </Box>
    );
  }

  // Preparar datos para el gráfico
  const chartData = data.segments?.map(seg => ({
    name: seg.segment,
    value: seg.count,
    percentage: seg.percentage
  })) || [];

  return (
    <VStack spacing={6} align="stretch">
      <Box>
        <Heading size="md" mb={2}>Segmentación RFM de Clientes</Heading>
        <Text color="gray.600">
          Análisis basado en Recency (recencia), Frequency (frecuencia) y Monetary (valor monetario)
        </Text>
      </Box>

      {/* Gráfico de Pastel */}
      {chartData.length > 0 && (
        <Card>
          <CardBody>
            <Heading size="sm" mb={4}>Distribución de Segmentos</Heading>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percentage }) => `${name}: ${percentage}%`}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[entry.name] || '#999'} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardBody>
        </Card>
      )}

      {/* Tabla de Segmentos */}
      {data.segments && data.segments.length > 0 && (
        <Card>
          <CardBody>
            <Heading size="sm" mb={4}>Detalles por Segmento</Heading>
            <Table variant="simple">
              <Thead>
                <Tr>
                  <Th>Segmento</Th>
                  <Th isNumeric>Clientes</Th>
                  <Th isNumeric>Porcentaje</Th>
                  <Th isNumeric>Valor Promedio</Th>
                </Tr>
              </Thead>
              <Tbody>
                {data.segments.map((seg, index) => (
                  <Tr key={index}>
                    <Td>
                      <Badge colorScheme={
                        seg.segment === 'Champions' ? 'green' :
                        seg.segment === 'Loyal Customers' ? 'blue' :
                        seg.segment === 'Potential' ? 'orange' :
                        seg.segment === 'At Risk' ? 'red' : 'gray'
                      }>
                        {seg.segment}
                      </Badge>
                    </Td>
                    <Td isNumeric>{seg.count}</Td>
                    <Td isNumeric>{seg.percentage}%</Td>
                    <Td isNumeric>S/ {seg.avg_monetary?.toFixed(2) || '0.00'}</Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </CardBody>
        </Card>
      )}

      {/* Top Clientes */}
      {data.top_customers && data.top_customers.length > 0 && (
        <Card>
          <CardBody>
            <Heading size="sm" mb={4}>Top 10 Clientes (Champions)</Heading>
            <Table variant="simple" size="sm">
              <Thead>
                <Tr>
                  <Th>Cliente</Th>
                  <Th isNumeric>Recencia (días)</Th>
                  <Th isNumeric>Frecuencia</Th>
                  <Th isNumeric>Valor Total</Th>
                </Tr>
              </Thead>
              <Tbody>
                {data.top_customers.slice(0, 10).map((customer, index) => (
                  <Tr key={index}>
                    <Td>{customer.nombre || `Cliente ${customer.cliente_id}`}</Td>
                    <Td isNumeric>{customer.recency}</Td>
                    <Td isNumeric>{customer.frequency}</Td>
                    <Td isNumeric>S/ {customer.monetary?.toFixed(2)}</Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </CardBody>
        </Card>
      )}
    </VStack>
  );
};

export default CustomerSegmentation;
