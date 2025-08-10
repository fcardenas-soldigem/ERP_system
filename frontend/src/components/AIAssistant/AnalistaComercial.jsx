import React, { useState } from 'react';
import {
  Box,
  VStack,
  HStack,
  Button,
  Text,
  Heading,
  Card,
  CardBody,
  CardHeader,
  Textarea,
  Select,
  Alert,
  AlertIcon,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  useToast,
  Badge
} from '@chakra-ui/react';
import { api } from '../../api';

const AnalistaComercial = () => {
  const [loading, setLoading] = useState(false);
  const [reporteVentas, setReporteVentas] = useState('');
  const [analisisInventario, setAnalisisInventario] = useState('');
  const [oportunidades, setOportunidades] = useState('');
  const [consulta, setConsulta] = useState('');
  const [respuestaConsulta, setRespuestaConsulta] = useState('');
  const [periodo, setPeriodo] = useState('último_mes');
  const toast = useToast();

  const formatearRespuesta = (texto) => {
    if (!texto) return '';
    
    return texto
      .split('\n')
      .map((linea, index) => {
        if (linea.includes('📊') || linea.includes('📈') || linea.includes('🎯') || 
            linea.includes('👥') || linea.includes('⚠️') || linea.includes('💡') ||
            linea.includes('🔴') || linea.includes('🟡') || linea.includes('🆕') ||
            linea.includes('🤝') || linea.includes('💰')) {
          return (
            <Text key={index} fontWeight="bold" fontSize="lg" color="blue.600" mt={4} mb={2}>
              {linea}
            </Text>
          );
        }
        
        if (linea.match(/^\d+\./) || linea.match(/^-/) || linea.match(/^\*/)) {
          return (
            <Text key={index} ml={4} mb={1}>
              {linea}
            </Text>
          );
        }
        
        return linea.trim() ? (
          <Text key={index} mb={2}>
            {linea}
          </Text>
        ) : (
          <Box key={index} h={2} />
        );
      });
  };

  const generarReporteVentas = async () => {
    setLoading(true);
    try {
      const response = await api.post('/api/ai/analista/reporte-ventas/', {
        periodo: periodo
      });

      if (response.data.success) {
        setReporteVentas(response.data.reporte);
        toast({
          title: 'Reporte generado',
          description: `Análisis de ventas para ${periodo} completado`,
          status: 'success',
          duration: 3000,
        });
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: error.response?.data?.error || 'Error al generar reporte',
        status: 'error',
        duration: 5000,
      });
    } finally {
      setLoading(false);
    }
  };

  const analizarInventario = async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/ai/analista/inventario/');

      if (response.data.success) {
        setAnalisisInventario(response.data.analisis);
        toast({
          title: 'Análisis completado',
          description: 'Análisis de inventario con predicciones generado',
          status: 'success',
          duration: 3000,
        });
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: error.response?.data?.error || 'Error al analizar inventario',
        status: 'error',
        duration: 5000,
      });
    } finally {
      setLoading(false);
    }
  };

  const detectarOportunidades = async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/ai/analista/oportunidades/');

      if (response.data.success) {
        setOportunidades(response.data.oportunidades);
        toast({
          title: 'Análisis completado',
          description: 'Oportunidades comerciales identificadas',
          status: 'success',
          duration: 3000,
        });
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: error.response?.data?.error || 'Error al detectar oportunidades',
        status: 'error',
        duration: 5000,
      });
    } finally {
      setLoading(false);
    }
  };

  const realizarConsulta = async () => {
    if (!consulta.trim()) {
      toast({
        title: 'Consulta requerida',
        description: 'Por favor ingresa una consulta',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    setLoading(true);
    try {
      const response = await api.post('/api/ai/analista/consulta/', {
        consulta: consulta
      });

      if (response.data.success) {
        setRespuestaConsulta(response.data.respuesta);
        toast({
          title: 'Consulta procesada',
          description: 'El analista ha respondido tu consulta',
          status: 'success',
          duration: 3000,
        });
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: error.response?.data?.error || 'Error al procesar consulta',
        status: 'error',
        duration: 5000,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box p={6} maxW="1200px" mx="auto">
      <VStack spacing={6} align="stretch">
        <Box textAlign="center">
          <Heading size="lg" color="blue.600" mb={2}>
            🤖 Analista Comercial IA
          </Heading>
          <Text color="gray.600">
            Powered by Claude 3.5 Sonnet - Análisis inteligente de tu negocio
          </Text>
          <Badge colorScheme="green" mt={2}>
            Modelo: Claude 3.5 Sonnet (Superior para análisis comercial)
          </Badge>
        </Box>

        <Tabs variant="enclosed" colorScheme="blue">
          <TabList>
            <Tab>📊 Reporte de Ventas</Tab>
            <Tab>📦 Análisis de Inventario</Tab>
            <Tab>🎯 Oportunidades</Tab>
            <Tab>💬 Consulta Libre</Tab>
          </TabList>

          <TabPanels>
            <TabPanel>
              <Card>
                <CardHeader>
                  <Heading size="md">Análisis Inteligente de Ventas</Heading>
                  <Text color="gray.600">
                    Claude analiza tus ventas y proporciona insights estratégicos
                  </Text>
                </CardHeader>
                <CardBody>
                  <VStack spacing={4} align="stretch">
                    <HStack>
                      <Select 
                        value={periodo} 
                        onChange={(e) => setPeriodo(e.target.value)}
                        width="200px"
                      >
                        <option value="último_mes">Último Mes</option>
                        <option value="último_trimestre">Último Trimestre</option>
                        <option value="último_año">Último Año</option>
                      </Select>
                      <Button 
                        colorScheme="blue" 
                        onClick={generarReporteVentas}
                        isLoading={loading}
                        loadingText="Analizando..."
                      >
                        Generar Reporte
                      </Button>
                    </HStack>

                    {reporteVentas && (
                      <Box 
                        p={4} 
                        bg="gray.50" 
                        borderRadius="md" 
                        border="1px" 
                        borderColor="gray.200"
                      >
                        <VStack align="stretch" spacing={2}>
                          {formatearRespuesta(reporteVentas)}
                        </VStack>
                      </Box>
                    )}
                  </VStack>
                </CardBody>
              </Card>
            </TabPanel>

            <TabPanel>
              <Card>
                <CardHeader>
                  <Heading size="md">Análisis Predictivo de Inventario</Heading>
                  <Text color="gray.600">
                    Predicciones de stock, alertas y recomendaciones
                  </Text>
                </CardHeader>
                <CardBody>
                  <VStack spacing={4} align="stretch">
                    <Button 
                      colorScheme="orange" 
                      onClick={analizarInventario}
                      isLoading={loading}
                      loadingText="Analizando inventario..."
                    >
                      Analizar Inventario
                    </Button>

                    {analisisInventario && (
                      <Box 
                        p={4} 
                        bg="orange.50" 
                        borderRadius="md" 
                        border="1px" 
                        borderColor="orange.200"
                      >
                        <VStack align="stretch" spacing={2}>
                          {formatearRespuesta(analisisInventario)}
                        </VStack>
                      </Box>
                    )}
                  </VStack>
                </CardBody>
              </Card>
            </TabPanel>

            <TabPanel>
              <Card>
                <CardHeader>
                  <Heading size="md">Detector de Oportunidades</Heading>
                  <Text color="gray.600">
                    Identifica oportunidades de crecimiento y expansión
                  </Text>
                </CardHeader>
                <CardBody>
                  <VStack spacing={4} align="stretch">
                    <Button 
                      colorScheme="green" 
                      onClick={detectarOportunidades}
                      isLoading={loading}
                      loadingText="Detectando oportunidades..."
                    >
                      Detectar Oportunidades
                    </Button>

                    {oportunidades && (
                      <Box 
                        p={4} 
                        bg="green.50" 
                        borderRadius="md" 
                        border="1px" 
                        borderColor="green.200"
                      >
                        <VStack align="stretch" spacing={2}>
                          {formatearRespuesta(oportunidades)}
                        </VStack>
                      </Box>
                    )}
                  </VStack>
                </CardBody>
              </Card>
            </TabPanel>

            <TabPanel>
              <Card>
                <CardHeader>
                  <Heading size="md">Consulta al Analista</Heading>
                  <Text color="gray.600">
                    Pregunta cualquier cosa sobre tu negocio
                  </Text>
                </CardHeader>
                <CardBody>
                  <VStack spacing={4} align="stretch">
                    <Textarea
                      placeholder="Ejemplo: ¿Cuáles son mis productos más rentables? ¿Qué estrategia de precios me recomiendas? ¿Cómo puedo mejorar mi flujo de caja?"
                      value={consulta}
                      onChange={(e) => setConsulta(e.target.value)}
                      rows={3}
                    />
                    <Button 
                      colorScheme="purple" 
                      onClick={realizarConsulta}
                      isLoading={loading}
                      loadingText="Claude está analizando..."
                    >
                      Consultar Analista
                    </Button>

                    {respuestaConsulta && (
                      <Box 
                        p={4} 
                        bg="purple.50" 
                        borderRadius="md" 
                        border="1px" 
                        borderColor="purple.200"
                      >
                        <VStack align="stretch" spacing={2}>
                          {formatearRespuesta(respuestaConsulta)}
                        </VStack>
                      </Box>
                    )}
                  </VStack>
                </CardBody>
              </Card>
            </TabPanel>
          </TabPanels>
        </Tabs>

        <Alert status="info" borderRadius="md">
          <AlertIcon />
          <VStack align="start" spacing={1}>
            <Text fontWeight="bold">Claude 3.5 Sonnet - Tu Analista Comercial IA</Text>
            <Text fontSize="sm">
              Este analista usa Claude 3.5 Sonnet, especializado en análisis empresarial. 
              Proporciona insights precisos basados en tus datos reales y tendencias del mercado.
            </Text>
          </VStack>
        </Alert>
      </VStack>
    </Box>
  );
};

export default AnalistaComercial; 