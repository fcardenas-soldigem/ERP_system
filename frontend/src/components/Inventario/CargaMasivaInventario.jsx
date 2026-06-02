import React, { useState, useCallback } from 'react';
import {
  Box,
  VStack,
  HStack,
  Heading,
  Text,
  Button,
  Input,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Progress,
  Badge,
  Card,
  CardHeader,
  CardBody,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Icon,
  Divider,
  useToast,
  useColorModeValue,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  List,
  ListItem,
  ListIcon,
  Flex,
  Spinner,
  Tooltip,
} from '@chakra-ui/react';
import {
  FiDownload,
  FiUpload,
  FiCheck,
  FiX,
  FiAlertTriangle,
  FiInfo,
  FiFileText,
  FiPackage,
  FiBox,
  FiCheckCircle,
  FiXCircle,
} from 'react-icons/fi';
import { useQueryClient } from '@tanstack/react-query';
import api from '../../lib/api';

const CargaMasivaInventario = () => {
  const [archivo, setArchivo] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [validando, setValidando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [preview, setPreview] = useState(null);
  const [paso, setPaso] = useState(1);
  
  const toast = useToast();
  const queryClient = useQueryClient();
  const bgCard = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  // Descargar plantilla
  const descargarPlantilla = async () => {
    try {
      const response = await api.get('/api/inventario/carga-masiva/plantilla/', {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'plantilla_carga_inventario.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast({
        title: 'Plantilla descargada',
        description: 'Revisa las instrucciones en la primera hoja',
        status: 'success',
        duration: 3000,
      });
    } catch (error) {
      toast({
        title: 'Error al descargar',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    }
  };

  // Manejar selección de archivo
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
        toast({
          title: 'Formato inválido',
          description: 'Solo se permiten archivos Excel (.xlsx, .xls)',
          status: 'error',
          duration: 3000,
        });
        return;
      }
      setArchivo(file);
      setResultado(null);
      setPreview(null);
      setPaso(2);
    }
  };

  // Validar archivo (preview)
  const validarArchivo = async () => {
    if (!archivo) return;
    
    setValidando(true);
    const formData = new FormData();
    formData.append('archivo', archivo);

    try {
      const response = await api.post('/api/inventario/carga-masiva/validar/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setPreview(response.data);
      setPaso(3);
      
      if (response.data.success) {
        toast({
          title: 'Validación exitosa',
          description: 'El archivo está listo para cargar',
          status: 'success',
          duration: 3000,
        });
      } else {
        toast({
          title: 'Se encontraron errores',
          description: 'Revisa los errores antes de continuar',
          status: 'warning',
          duration: 5000,
        });
      }
    } catch (error) {
      toast({
        title: 'Error al validar',
        description: error.response?.data?.error || error.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setValidando(false);
    }
  };

  // Procesar carga
  const procesarCarga = async () => {
    if (!archivo) return;
    
    setCargando(true);
    const formData = new FormData();
    formData.append('archivo', archivo);

    try {
      const response = await api.post('/api/inventario/carga-masiva/cargar/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setResultado(response.data);
      setPaso(4);
      
      if (response.data.success) {
        // Invalidar todas las queries relacionadas con inventario
        queryClient.invalidateQueries(['productos']);
        queryClient.invalidateQueries(['resumen-inventarios-separados']);
        queryClient.invalidateQueries(['inventario-materias-primas']);
        queryClient.invalidateQueries(['inventario-productos-terminados']);
        queryClient.invalidateQueries(['alertas-materias-primas']);
        queryClient.invalidateQueries(['alertas-productos-terminados']);
        queryClient.invalidateQueries(['valor-total-materias-primas']);
        queryClient.invalidateQueries(['valor-total-productos-terminados']);
        
        toast({
          title: 'Carga completada',
          description: `Se crearon ${response.data.resumen.productos_validos} productos`,
          status: 'success',
          duration: 5000,
        });
      }
    } catch (error) {
      const errorData = error.response?.data;
      if (errorData) {
        setResultado(errorData);
        setPaso(4);
      }
      toast({
        title: 'Error en la carga',
        description: errorData?.errores?.[0] || error.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setCargando(false);
    }
  };

  // Reiniciar proceso
  const reiniciar = () => {
    setArchivo(null);
    setResultado(null);
    setPreview(null);
    setPaso(1);
  };

  return (
    <Box p={6} maxW="1200px" mx="auto">
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <Box>
          <Heading size="lg" mb={2}>Carga Masiva de Inventario</Heading>
          <Text color="gray.500">
            Carga múltiples productos desde un archivo Excel con detección automática de tipo
          </Text>
        </Box>

        {/* Indicador de pasos */}
        <HStack spacing={4} justify="center">
          {[
            { num: 1, label: 'Descargar Plantilla' },
            { num: 2, label: 'Seleccionar Archivo' },
            { num: 3, label: 'Validar' },
            { num: 4, label: 'Resultado' }
          ].map((step) => (
            <HStack key={step.num}>
              <Box
                w={8}
                h={8}
                borderRadius="full"
                bg={paso >= step.num ? 'blue.500' : 'gray.200'}
                color={paso >= step.num ? 'white' : 'gray.500'}
                display="flex"
                alignItems="center"
                justifyContent="center"
                fontWeight="bold"
              >
                {paso > step.num ? <Icon as={FiCheck} /> : step.num}
              </Box>
              <Text 
                fontSize="sm" 
                fontWeight={paso === step.num ? 'bold' : 'normal'}
                color={paso >= step.num ? 'blue.500' : 'gray.500'}
              >
                {step.label}
              </Text>
              {step.num < 4 && <Box w={8} h={1} bg={paso > step.num ? 'blue.500' : 'gray.200'} />}
            </HStack>
          ))}
        </HStack>

        {/* Paso 1: Descargar Plantilla */}
        <Card bg={bgCard} borderColor={borderColor} borderWidth="1px">
          <CardHeader pb={2}>
            <HStack>
              <Icon as={FiDownload} color="blue.500" boxSize={5} />
              <Heading size="md">Paso 1: Descargar Plantilla</Heading>
            </HStack>
          </CardHeader>
          <CardBody>
            <VStack align="start" spacing={4}>
              <Text>
                Descarga la plantilla Excel con las instrucciones y ejemplos de cómo llenar los datos.
              </Text>
              
              <Alert status="info" borderRadius="md">
                <AlertIcon />
                <Box>
                  <AlertTitle>Detección Automática de Tipo</AlertTitle>
                  <AlertDescription>
                    El sistema detecta automáticamente si un producto es <strong>Materia Prima</strong> o 
                    <strong> Producto Terminado</strong> basándose en la categoría que especifiques.
                  </AlertDescription>
                </Box>
              </Alert>

              <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4} w="100%">
                <Box p={4} bg="purple.50" borderRadius="md">
                  <HStack mb={2}>
                    <Icon as={FiBox} color="purple.500" />
                    <Text fontWeight="bold" color="purple.700">Materia Prima</Text>
                  </HStack>
                  <Text fontSize="sm" color="purple.600">
                    Categorías: MP, Materia Prima, Insumo, Material
                  </Text>
                  <Text fontSize="xs" color="purple.500" mt={1}>
                    precio_venta se ignora (será 0)
                  </Text>
                </Box>
                
                <Box p={4} bg="green.50" borderRadius="md">
                  <HStack mb={2}>
                    <Icon as={FiPackage} color="green.500" />
                    <Text fontWeight="bold" color="green.700">Producto Terminado</Text>
                  </HStack>
                  <Text fontSize="sm" color="green.600">
                    Cualquier otra categoría (Muebles, Electrónicos, etc.)
                  </Text>
                  <Text fontSize="xs" color="green.500" mt={1}>
                    precio_venta es OBLIGATORIO
                  </Text>
                </Box>
              </SimpleGrid>

              <Button 
                leftIcon={<FiDownload />} 
                colorScheme="blue" 
                onClick={descargarPlantilla}
              >
                Descargar Plantilla Excel
              </Button>
            </VStack>
          </CardBody>
        </Card>

        {/* Paso 2: Seleccionar Archivo */}
        <Card bg={bgCard} borderColor={borderColor} borderWidth="1px">
          <CardHeader pb={2}>
            <HStack>
              <Icon as={FiFileText} color="blue.500" boxSize={5} />
              <Heading size="md">Paso 2: Seleccionar Archivo</Heading>
            </HStack>
          </CardHeader>
          <CardBody>
            <VStack align="start" spacing={4}>
              <Text>Selecciona el archivo Excel con los productos a cargar.</Text>
              
              <Input
                type="file"
                accept=".xlsx,.xls"
                onChange={handleFileChange}
                p={1}
              />
              
              {archivo && (
                <HStack>
                  <Icon as={FiCheck} color="green.500" />
                  <Text color="green.500" fontWeight="medium">
                    Archivo seleccionado: {archivo.name}
                  </Text>
                  <Badge colorScheme="blue">
                    {(archivo.size / 1024).toFixed(1)} KB
                  </Badge>
                </HStack>
              )}

              {archivo && (
                <Button
                  leftIcon={validando ? <Spinner size="sm" /> : <FiCheck />}
                  colorScheme="teal"
                  onClick={validarArchivo}
                  isLoading={validando}
                  loadingText="Validando..."
                >
                  Validar Archivo
                </Button>
              )}
            </VStack>
          </CardBody>
        </Card>

        {/* Paso 3: Preview/Validación */}
        {preview && (
          <Card bg={bgCard} borderColor={borderColor} borderWidth="1px">
            <CardHeader pb={2}>
              <HStack>
                <Icon 
                  as={preview.success ? FiCheckCircle : FiAlertTriangle} 
                  color={preview.success ? 'green.500' : 'orange.500'} 
                  boxSize={5} 
                />
                <Heading size="md">
                  Paso 3: Resultado de Validación
                </Heading>
              </HStack>
            </CardHeader>
            <CardBody>
              <VStack align="stretch" spacing={4}>
                {/* Resumen */}
                <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
                  <Stat>
                    <StatLabel>Filas Encontradas</StatLabel>
                    <StatNumber>{preview.resumen.filas_encontradas}</StatNumber>
                  </Stat>
                  <Stat>
                    <StatLabel>Materias Primas</StatLabel>
                    <StatNumber color="purple.500">
                      {preview.resumen.materias_primas}
                    </StatNumber>
                  </Stat>
                  <Stat>
                    <StatLabel>Productos Terminados</StatLabel>
                    <StatNumber color="green.500">
                      {preview.resumen.productos_terminados}
                    </StatNumber>
                  </Stat>
                  <Stat>
                    <StatLabel>Errores</StatLabel>
                    <StatNumber color={preview.resumen.errores > 0 ? 'red.500' : 'green.500'}>
                      {preview.resumen.errores}
                    </StatNumber>
                  </Stat>
                </SimpleGrid>

                {/* Errores */}
                {preview.errores.length > 0 && (
                  <Alert status="error" borderRadius="md">
                    <AlertIcon />
                    <Box flex="1">
                      <AlertTitle>Errores encontrados</AlertTitle>
                      <List spacing={1} mt={2}>
                        {preview.errores.map((error, idx) => (
                          <ListItem key={idx} fontSize="sm">
                            <ListIcon as={FiX} color="red.500" />
                            {error}
                          </ListItem>
                        ))}
                      </List>
                    </Box>
                  </Alert>
                )}

                {/* Warnings */}
                {preview.warnings.length > 0 && (
                  <Alert status="warning" borderRadius="md">
                    <AlertIcon />
                    <Box flex="1">
                      <AlertTitle>Advertencias</AlertTitle>
                      <List spacing={1} mt={2}>
                        {preview.warnings.map((warning, idx) => (
                          <ListItem key={idx} fontSize="sm">
                            <ListIcon as={FiAlertTriangle} color="orange.500" />
                            {warning}
                          </ListItem>
                        ))}
                      </List>
                    </Box>
                  </Alert>
                )}

                {/* Preview de productos */}
                {preview.preview && preview.preview.length > 0 && (
                  <Accordion allowToggle>
                    <AccordionItem>
                      <AccordionButton>
                        <Box flex="1" textAlign="left" fontWeight="medium">
                          Vista previa de productos ({preview.preview.length})
                        </Box>
                        <AccordionIcon />
                      </AccordionButton>
                      <AccordionPanel>
                        <Box overflowX="auto">
                          <Table size="sm">
                            <Thead>
                              <Tr>
                                <Th>Fila</Th>
                                <Th>SKU</Th>
                                <Th>Nombre</Th>
                                <Th>Tipo Detectado</Th>
                                <Th>Estado</Th>
                              </Tr>
                            </Thead>
                            <Tbody>
                              {preview.preview.slice(0, 20).map((item, idx) => (
                                <Tr key={idx}>
                                  <Td>{item.fila}</Td>
                                  <Td fontFamily="mono">{item.sku}</Td>
                                  <Td>{item.nombre}</Td>
                                  <Td>
                                    <Badge 
                                      colorScheme={item.tipo_detectado === 'Materia Prima' ? 'purple' : 'green'}
                                    >
                                      {item.tipo_detectado}
                                    </Badge>
                                  </Td>
                                  <Td>
                                    <Icon 
                                      as={item.valido ? FiCheckCircle : FiXCircle}
                                      color={item.valido ? 'green.500' : 'red.500'}
                                    />
                                  </Td>
                                </Tr>
                              ))}
                            </Tbody>
                          </Table>
                          {preview.preview.length > 20 && (
                            <Text fontSize="sm" color="gray.500" mt={2}>
                              ... y {preview.preview.length - 20} más
                            </Text>
                          )}
                        </Box>
                      </AccordionPanel>
                    </AccordionItem>
                  </Accordion>
                )}

                {/* Botón de carga */}
                {preview.success && (
                  <Button
                    leftIcon={cargando ? <Spinner size="sm" /> : <FiUpload />}
                    colorScheme="green"
                    size="lg"
                    onClick={procesarCarga}
                    isLoading={cargando}
                    loadingText="Cargando productos..."
                  >
                    Cargar {preview.resumen.filas_encontradas} Productos
                  </Button>
                )}
              </VStack>
            </CardBody>
          </Card>
        )}

        {/* Paso 4: Resultado Final */}
        {resultado && (
          <Card 
            bg={bgCard} 
            borderColor={resultado.success ? 'green.500' : 'red.500'} 
            borderWidth="2px"
          >
            <CardHeader pb={2}>
              <HStack>
                <Icon 
                  as={resultado.success ? FiCheckCircle : FiXCircle} 
                  color={resultado.success ? 'green.500' : 'red.500'} 
                  boxSize={6} 
                />
                <Heading size="md" color={resultado.success ? 'green.500' : 'red.500'}>
                  {resultado.success ? 'Carga Completada' : 'Carga con Errores'}
                </Heading>
              </HStack>
            </CardHeader>
            <CardBody>
              <VStack align="stretch" spacing={4}>
                {/* Estadísticas finales */}
                <SimpleGrid columns={{ base: 2, md: 5 }} spacing={4}>
                  <Stat>
                    <StatLabel>Procesadas</StatLabel>
                    <StatNumber>{resultado.resumen.filas_procesadas}</StatNumber>
                  </Stat>
                  <Stat>
                    <StatLabel>Creados</StatLabel>
                    <StatNumber color="green.500">
                      {resultado.resumen.productos_validos}
                    </StatNumber>
                  </Stat>
                  <Stat>
                    <StatLabel>Materias Primas</StatLabel>
                    <StatNumber color="purple.500">
                      {resultado.resumen.materias_primas}
                    </StatNumber>
                  </Stat>
                  <Stat>
                    <StatLabel>Prod. Terminados</StatLabel>
                    <StatNumber color="blue.500">
                      {resultado.resumen.productos_terminados}
                    </StatNumber>
                  </Stat>
                  <Stat>
                    <StatLabel>Errores</StatLabel>
                    <StatNumber color="red.500">
                      {resultado.resumen.errores}
                    </StatNumber>
                  </Stat>
                </SimpleGrid>

                {/* Lista de productos creados */}
                {resultado.productos_creados && resultado.productos_creados.length > 0 && (
                  <Alert status="success" borderRadius="md">
                    <AlertIcon />
                    <Box>
                      <AlertTitle>Productos creados exitosamente</AlertTitle>
                      <Accordion allowToggle mt={2}>
                        <AccordionItem border="none">
                          <AccordionButton px={0}>
                            <Text fontSize="sm">Ver lista de productos</Text>
                            <AccordionIcon />
                          </AccordionButton>
                          <AccordionPanel px={0}>
                            <List spacing={1}>
                              {resultado.productos_creados.map((prod, idx) => (
                                <ListItem key={idx} fontSize="sm">
                                  <ListIcon as={FiCheck} color="green.500" />
                                  <Badge 
                                    size="sm" 
                                    colorScheme={prod.tipo === 'RAW' ? 'purple' : 'green'}
                                    mr={2}
                                  >
                                    {prod.tipo === 'RAW' ? 'MP' : 'PT'}
                                  </Badge>
                                  {prod.sku} - {prod.nombre}
                                </ListItem>
                              ))}
                            </List>
                          </AccordionPanel>
                        </AccordionItem>
                      </Accordion>
                    </Box>
                  </Alert>
                )}

                {/* Botón reiniciar */}
                <Button
                  leftIcon={<FiUpload />}
                  variant="outline"
                  onClick={reiniciar}
                >
                  Cargar Otro Archivo
                </Button>
              </VStack>
            </CardBody>
          </Card>
        )}
      </VStack>
    </Box>
  );
};

export default CargaMasivaInventario;
