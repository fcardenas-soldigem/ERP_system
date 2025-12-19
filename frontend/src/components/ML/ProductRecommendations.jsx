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
  HStack,
  useToast,
} from '@chakra-ui/react';
import mlService from '../../services/mlService';

const ProductRecommendations = ({ status }) => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const toast = useToast();

  const hasModel = status?.models?.find(m => m.type === 'product_recommendations')?.has_model;

  useEffect(() => {
    if (hasModel) {
      loadRecommendations();
    }
  }, [hasModel]);

  const loadRecommendations = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await mlService.predictRecommendations();
      setData(response.data);
    } catch (err) {
      console.error('Error cargando recomendaciones:', err);
      setError(err.response?.data?.error || 'Error al cargar recomendaciones');
    } finally {
      setLoading(false);
    }
  };

  if (!hasModel) {
    return (
      <Alert status="warning">
        <AlertIcon />
        <AlertDescription>
          El modelo de recomendaciones no ha sido entrenado aún. Haz clic en "Entrenar Modelos" para comenzar.
        </AlertDescription>
      </Alert>
    );
  }

  if (loading) {
    return (
      <Box textAlign="center" py={10}>
        <Spinner size="xl" />
        <Text mt={4}>Generando recomendaciones...</Text>
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
        <Button mt={4} colorScheme="blue" onClick={loadRecommendations}>
          Generar Recomendaciones
        </Button>
      </Box>
    );
  }

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.7) return 'green';
    if (confidence >= 0.5) return 'blue';
    return 'orange';
  };

  return (
    <VStack spacing={6} align="stretch">
      <Box>
        <Heading size="md" mb={2}>Recomendaciones de Productos</Heading>
        <Text color="gray.600">
          Análisis de asociación de productos basado en patrones de compra
        </Text>
      </Box>

      {/* Estadísticas */}
      {data.summary && (
        <Card>
          <CardBody>
            <Heading size="sm" mb={4}>Resumen</Heading>
            <HStack spacing={8}>
              <Box>
                <Text fontSize="sm" color="gray.600">Reglas Encontradas</Text>
                <Text fontSize="2xl" fontWeight="bold">{data.summary.total_rules || 0}</Text>
              </Box>
              <Box>
                <Text fontSize="sm" color="gray.600">Confianza Promedio</Text>
                <Text fontSize="2xl" fontWeight="bold" color="blue.500">
                  {((data.summary.avg_confidence || 0) * 100).toFixed(1)}%
                </Text>
              </Box>
              <Box>
                <Text fontSize="sm" color="gray.600">Lift Promedio</Text>
                <Text fontSize="2xl" fontWeight="bold" color="green.500">
                  {(data.summary.avg_lift || 0).toFixed(2)}x
                </Text>
              </Box>
            </HStack>
          </CardBody>
        </Card>
      )}

      {/* Top Reglas de Asociación */}
      {data.rules && data.rules.length > 0 && (
        <Card>
          <CardBody>
            <Heading size="sm" mb={4}>Top Reglas de Asociación</Heading>
            <Table variant="simple" size="sm">
              <Thead>
                <Tr>
                  <Th>Si compra...</Th>
                  <Th>Entonces también compra...</Th>
                  <Th>Confianza</Th>
                  <Th>Lift</Th>
                  <Th>Soporte</Th>
                </Tr>
              </Thead>
              <Tbody>
                {data.rules.map((rule, index) => (
                  <Tr key={index}>
                    <Td>
                      <Badge colorScheme="purple">
                        {Array.isArray(rule.antecedent) ? rule.antecedent.join(', ') : rule.antecedent}
                      </Badge>
                    </Td>
                    <Td>
                      <Badge colorScheme="cyan">
                        {Array.isArray(rule.consequent) ? rule.consequent.join(', ') : rule.consequent}
                      </Badge>
                    </Td>
                    <Td>
                      <Badge colorScheme={getConfidenceColor(rule.confidence)}>
                        {(rule.confidence * 100).toFixed(1)}%
                      </Badge>
                    </Td>
                    <Td>
                      <Text fontWeight="bold">{rule.lift?.toFixed(2)}x</Text>
                    </Td>
                    <Td>
                      <Text fontSize="sm">{(rule.support * 100).toFixed(2)}%</Text>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </CardBody>
        </Card>
      )}

      {/* Productos Más Recomendados */}
      {data.top_products && data.top_products.length > 0 && (
        <Card>
          <CardBody>
            <Heading size="sm" mb={4}>Productos Más Frecuentemente Recomendados</Heading>
            <Table variant="simple" size="sm">
              <Thead>
                <Tr>
                  <Th>Producto</Th>
                  <Th isNumeric>Apariciones en Reglas</Th>
                  <Th isNumeric>Confianza Promedio</Th>
                </Tr>
              </Thead>
              <Tbody>
                {data.top_products.map((product, index) => (
                  <Tr key={index}>
                    <Td>{product.name || `Producto ${product.id}`}</Td>
                    <Td isNumeric>
                      <Badge colorScheme="blue">{product.count}</Badge>
                    </Td>
                    <Td isNumeric>
                      <Text fontWeight="bold">
                        {(product.avg_confidence * 100).toFixed(1)}%
                      </Text>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </CardBody>
        </Card>
      )}

      {/* Explicación */}
      <Alert status="info">
        <AlertIcon />
        <Box>
          <Text fontWeight="bold" mb={1}>¿Cómo interpretar estas recomendaciones?</Text>
          <Text fontSize="sm">
            • <strong>Confianza:</strong> Probabilidad de que se compre el producto recomendado cuando se compra el producto base.
            <br />
            • <strong>Lift:</strong> Cuánto más probable es la compra conjunta comparado con la probabilidad individual.
            <br />
            • <strong>Soporte:</strong> Frecuencia con la que aparece esta combinación en todas las transacciones.
          </Text>
        </Box>
      </Alert>
    </VStack>
  );
};

export default ProductRecommendations;
