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
  Progress,
  useToast,
} from '@chakra-ui/react';
import mlService from '../../services/mlService';

const ChurnPrediction = ({ status }) => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const toast = useToast();

  const hasModel = status?.models?.find(m => m.type === 'churn_prediction')?.has_model;

  useEffect(() => {
    if (hasModel) {
      loadPredictions();
    }
  }, [hasModel]);

  const loadPredictions = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await mlService.predictChurn();
      setData(response.data);
    } catch (err) {
      console.error('Error cargando predicciones:', err);
      setError(err.response?.data?.error || 'Error al cargar predicciones de churn');
    } finally {
      setLoading(false);
    }
  };

  if (!hasModel) {
    return (
      <Alert status="warning">
        <AlertIcon />
        <AlertDescription>
          El modelo de predicción de churn no ha sido entrenado aún. Haz clic en "Entrenar Modelos" para comenzar.
        </AlertDescription>
      </Alert>
    );
  }

  if (loading) {
    return (
      <Box textAlign="center" py={10}>
        <Spinner size="xl" />
        <Text mt={4}>Analizando clientes...</Text>
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
        <Button mt={4} colorScheme="blue" onClick={loadPredictions}>
          Analizar Clientes
        </Button>
      </Box>
    );
  }

  const getRiskColor = (probability) => {
    if (probability >= 0.7) return 'red';
    if (probability >= 0.4) return 'orange';
    return 'green';
  };

  const getRiskLabel = (probability) => {
    if (probability >= 0.7) return 'Alto Riesgo';
    if (probability >= 0.4) return 'Riesgo Medio';
    return 'Bajo Riesgo';
  };

  return (
    <VStack spacing={6} align="stretch">
      <Box>
        <Heading size="md" mb={2}>Predicción de Churn</Heading>
        <Text color="gray.600">
          Identificación de clientes en riesgo de abandono
        </Text>
      </Box>

      {/* Estadísticas Generales */}
      {data.summary && (
        <Card>
          <CardBody>
            <Heading size="sm" mb={4}>Resumen</Heading>
            <VStack align="stretch" spacing={3}>
              <Box>
                <Text fontSize="sm" color="gray.600">Total de Clientes Analizados</Text>
                <Text fontSize="2xl" fontWeight="bold">{data.summary.total_customers || 0}</Text>
              </Box>
              <Box>
                <Text fontSize="sm" color="gray.600">Clientes en Alto Riesgo</Text>
                <Text fontSize="2xl" fontWeight="bold" color="red.500">
                  {data.summary.high_risk_count || 0}
                </Text>
              </Box>
              <Box>
                <Text fontSize="sm" color="gray.600">Precisión del Modelo</Text>
                <Text fontSize="2xl" fontWeight="bold" color="green.500">
                  {((data.summary.accuracy || 0) * 100).toFixed(1)}%
                </Text>
              </Box>
            </VStack>
          </CardBody>
        </Card>
      )}

      {/* Clientes en Riesgo */}
      {data.at_risk_customers && data.at_risk_customers.length > 0 && (
        <Card>
          <CardBody>
            <Heading size="sm" mb={4}>Clientes en Riesgo</Heading>
            <Table variant="simple" size="sm">
              <Thead>
                <Tr>
                  <Th>Cliente</Th>
                  <Th>Probabilidad de Churn</Th>
                  <Th>Nivel de Riesgo</Th>
                  <Th>Días sin Comprar</Th>
                </Tr>
              </Thead>
              <Tbody>
                {data.at_risk_customers.map((customer, index) => (
                  <Tr key={index}>
                    <Td>{customer.nombre || `Cliente ${customer.cliente_id}`}</Td>
                    <Td>
                      <Box>
                        <Progress
                          value={customer.churn_probability * 100}
                          colorScheme={getRiskColor(customer.churn_probability)}
                          size="sm"
                          mb={1}
                        />
                        <Text fontSize="xs">
                          {(customer.churn_probability * 100).toFixed(1)}%
                        </Text>
                      </Box>
                    </Td>
                    <Td>
                      <Badge colorScheme={getRiskColor(customer.churn_probability)}>
                        {getRiskLabel(customer.churn_probability)}
                      </Badge>
                    </Td>
                    <Td>{customer.days_since_last_purchase || 'N/A'}</Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </CardBody>
        </Card>
      )}

      {/* Factores de Riesgo */}
      {data.feature_importance && data.feature_importance.length > 0 && (
        <Card>
          <CardBody>
            <Heading size="sm" mb={4}>Factores Principales de Riesgo</Heading>
            <VStack align="stretch" spacing={3}>
              {data.feature_importance.slice(0, 5).map((feature, index) => (
                <Box key={index}>
                  <Text fontSize="sm" mb={1}>{feature.feature}</Text>
                  <Progress
                    value={feature.importance * 100}
                    colorScheme="blue"
                    size="sm"
                  />
                  <Text fontSize="xs" color="gray.500" mt={1}>
                    Importancia: {(feature.importance * 100).toFixed(1)}%
                  </Text>
                </Box>
              ))}
            </VStack>
          </CardBody>
        </Card>
      )}
    </VStack>
  );
};

export default ChurnPrediction;
