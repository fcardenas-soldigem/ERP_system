import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Grid,
  GridItem,
  Card,
  CardBody,
  Heading,
  Text,
  Button,
  Spinner,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Badge,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  VStack,
  HStack,
  useToast,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Icon,
  Flex,
  Divider,
} from '@chakra-ui/react';
import { FiRefreshCw, FiCheck, FiAlertTriangle, FiX, FiUsers, FiShoppingCart } from 'react-icons/fi';
import mlService from '../../services/mlService';
import CustomerSegmentation from './CustomerSegmentation';
import ChurnPrediction from './ChurnPrediction';
import ProductRecommendations from './ProductRecommendations';

const MLDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [training, setTraining] = useState(false);
  const toast = useToast();

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await mlService.checkStatus();
      setStatus(response.data);
    } catch (err) {
      console.error('Error cargando estado ML:', err);
      console.error('Detalles del error:', err.response?.data);
      setError(err.response?.data?.error || err.message || 'Error al cargar el estado de los modelos ML');
      // Establecer un estado por defecto para mostrar el botón de entrenamiento
      setStatus({
        empresa: { ventas_count: 0, clientes_count: 0, productos_count: 0 },
        models: [
          { type: 'rfm_segmentation', has_model: false, needs_retraining: false },
          { type: 'churn_prediction', has_model: false, needs_retraining: false },
          { type: 'product_recommendations', has_model: false, needs_retraining: false },
        ]
      });
    } finally {
      setLoading(false);
    }
  };

  const handleTrainAll = async () => {
    try {
      setTraining(true);
      setError(null);
      await mlService.trainAllModels();
      toast({
        title: 'Entrenamiento iniciado',
        description: 'Esto puede tardar varios minutos.',
        status: 'info',
        duration: 5000,
        isClosable: true,
      });
      // Recargar estado después de 5 segundos
      setTimeout(() => {
        loadStatus();
      }, 5000);
    } catch (err) {
      console.error('Error entrenando modelos:', err);
      setError(err.response?.data?.error || 'Error al entrenar modelos');
    } finally {
      setTraining(false);
    }
  };

  const getModelStatusIcon = (model) => {
    if (!model.has_model) return FiX;
    if (model.needs_retraining) return FiAlertTriangle;
    return FiCheck;
  };

  const getModelStatusColor = (model) => {
    if (!model.has_model) return 'red';
    if (model.needs_retraining) return 'yellow';
    return 'green';
  };

  const getModelStatusText = (model) => {
    if (!model.has_model) return 'Sin entrenar';
    if (model.needs_retraining) return 'Requiere reentrenamiento';
    return 'Activo';
  };

  if (loading) {
    return (
      <Flex justify="center" align="center" minH="400px">
        <Spinner size="xl" />
      </Flex>
    );
  }

  return (
    <Container maxW="container.xl" py={8}>
      {/* Header */}
      <VStack align="stretch" spacing={6}>
        <Box>
          <Heading size="xl" mb={2}>
            🤖 Machine Learning Dashboard
          </Heading>
          <Text color="gray.600">
            Análisis inteligente basado en tus datos reales del ERP
          </Text>
        </Box>

        {error && (
          <Alert status="error">
            <AlertIcon />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Status Cards */}
        {status && (
          <>
            <Grid templateColumns="repeat(4, 1fr)" gap={6}>
              {/* Datos Disponibles */}
              <GridItem>
                <Card>
                  <CardBody>
                    <Stat>
                      <HStack mb={2}>
                        <Icon as={FiUsers} color="blue.500" />
                        <StatLabel>Datos</StatLabel>
                      </HStack>
                      <StatNumber>{status.empresa?.ventas_count || 0}</StatNumber>
                      <StatHelpText>Ventas registradas</StatHelpText>
                      <Text fontSize="xs" color="gray.500" mt={2}>
                        {status.empresa?.clientes_count || 0} clientes • {status.empresa?.productos_count || 0} productos
                      </Text>
                    </Stat>
                  </CardBody>
                </Card>
              </GridItem>

              {/* Estado de Modelos */}
              {status.models?.map((model, index) => (
                <GridItem key={index}>
                  <Card>
                    <CardBody>
                      <HStack justify="space-between" mb={2}>
                        <Text fontWeight="bold" fontSize="sm">
                          {model.type === 'rfm_segmentation' && '👥 Segmentación'}
                          {model.type === 'churn_prediction' && '⚠️ Churn'}
                          {model.type === 'product_recommendations' && '🛒 Recomendaciones'}
                        </Text>
                        <Icon as={getModelStatusIcon(model)} color={`${getModelStatusColor(model)}.500`} />
                      </HStack>
                      <Badge colorScheme={getModelStatusColor(model)} mb={2}>
                        {getModelStatusText(model)}
                      </Badge>
                      {model.has_model && (
                        <Text fontSize="xs" color="gray.500">
                          Versión {model.version}
                          {model.trained_at && ` • ${new Date(model.trained_at).toLocaleDateString()}`}
                        </Text>
                      )}
                      {model.needs_retraining && (
                        <Text fontSize="xs" color="orange.500" mt={1}>
                          {model.retraining_reason}
                        </Text>
                      )}
                    </CardBody>
                  </Card>
                </GridItem>
              ))}
            </Grid>

            {/* Acción de Entrenamiento */}
            {status.models?.some(m => !m.has_model || m.needs_retraining) && (
              <Alert status="info">
                <AlertIcon />
                <Box flex="1">
                  <AlertTitle>Algunos modelos requieren entrenamiento o actualización</AlertTitle>
                  <AlertDescription>
                    Haz clic en "Entrenar Modelos" para comenzar. El proceso puede tardar varios minutos.
                  </AlertDescription>
                </Box>
                <Button
                  colorScheme="blue"
                  leftIcon={training ? <Spinner size="sm" /> : <Icon as={FiRefreshCw} />}
                  onClick={handleTrainAll}
                  isLoading={training}
                  ml={4}
                >
                  {training ? 'Entrenando...' : 'Entrenar Modelos'}
                </Button>
              </Alert>
            )}
          </>
        )}

        {/* Tabs de Modelos */}
        <Card>
          <CardBody>
            <Tabs>
              <TabList>
                <Tab>👥 Segmentación de Clientes</Tab>
                <Tab>⚠️ Predicción de Churn</Tab>
                <Tab>🛒 Recomendaciones</Tab>
              </TabList>

              <TabPanels>
                <TabPanel>
                  <CustomerSegmentation status={status} />
                </TabPanel>
                <TabPanel>
                  <ChurnPrediction status={status} />
                </TabPanel>
                <TabPanel>
                  <ProductRecommendations status={status} />
                </TabPanel>
              </TabPanels>
            </Tabs>
          </CardBody>
        </Card>
      </VStack>
    </Container>
  );
};

export default MLDashboard;


