import React, { useState, useRef } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Button,
  VStack,
  HStack,
  Box,
  Text,
  Alert,
  AlertIcon,
  Progress,
  Divider,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  useToast,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Code,
  UnorderedList,
  ListItem,
  Flex,
  Spacer,
  Icon,
  Input,
  FormControl,
  FormLabel
} from '@chakra-ui/react';
import { 
  AttachmentIcon, 
  CheckCircleIcon, 
  WarningIcon, 
  InfoIcon, 
  DownloadIcon 
} from '@chakra-ui/icons';
import { clientesService } from '../../services/clientes.service';

const ImportarClientes = ({ isOpen, onClose, onSuccess }) => {
  const [archivo, setArchivo] = useState(null);
  const [arrastrando, setArrastrando] = useState(false);
  const [cargando, setCargando] = useState(false);
  const [resultados, setResultados] = useState(null);
  const [etapa, setEtapa] = useState('seleccion'); // 'seleccion', 'procesando', 'resultados'
  const fileInputRef = useRef(null);
  const toast = useToast();

  const resetear = () => {
    setArchivo(null);
    setResultados(null);
    setEtapa('seleccion');
    setCargando(false);
    setArrastrando(false);
  };

  const handleClose = () => {
    resetear();
    onClose();
  };

  const handleArchivoSeleccionado = (file) => {
    // Validar tipo de archivo
    const extension = file.name.split('.').pop().toLowerCase();
    if (!['csv', 'xlsx', 'xls'].includes(extension)) {
      toast({
        title: 'Archivo no válido',
        description: 'Solo se aceptan archivos CSV, XLSX o XLS',
        status: 'error',
        duration: 4000,
        isClosable: true,
      });
      return;
    }

    // Validar tamaño (máximo 10MB)
    if (file.size > 10 * 1024 * 1024) {
      toast({
        title: 'Archivo muy grande',
        description: 'El archivo no puede exceder 10MB',
        status: 'error',
        duration: 4000,
        isClosable: true,
      });
      return;
    }

    setArchivo(file);
  };

  const handleInputChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleArchivoSeleccionado(e.target.files[0]);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setArrastrando(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleArchivoSeleccionado(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setArrastrando(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setArrastrando(false);
  };

  const procesarImportacion = async () => {
    if (!archivo) {
      toast({
        title: 'Error',
        description: 'Debe seleccionar un archivo',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    setEtapa('procesando');
    setCargando(true);

    try {
      const resultado = await clientesService.importarClientes(archivo);
      setResultados(resultado);
      setEtapa('resultados');

      if (resultado.success) {
        toast({
          title: 'Importación exitosa',
          description: resultado.mensaje,
          status: 'success',
          duration: 5000,
          isClosable: true,
        });
        
        // Notificar al componente padre para actualizar la lista
        if (onSuccess) {
          onSuccess();
        }
      }
    } catch (error) {
      console.error('Error en importación:', error);
      
      let errorMessage = 'Error al procesar el archivo';
      if (error.response?.data?.error) {
        errorMessage = error.response.data.error;
      }

      setResultados({
        success: false,
        error: errorMessage,
        detalles_errores: error.response?.data?.detalles_errores || []
      });
      setEtapa('resultados');

      toast({
        title: 'Error en importación',
        description: errorMessage,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setCargando(false);
    }
  };

  const descargarPlantillaCSV = () => {
    const csvContent = `nombre,documento,tipo_documento,direccion,telefono,email
Juan Pérez García,12345678,dni,Av. Principal 123,987654321,juan@email.com
Empresa SAC,20123456789,ruc,Jr. Comercio 456,987123456,contacto@empresa.com
María González,87654321,dni,Calle Los Rosales 789,965874123,maria@email.com`;

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', 'plantilla_clientes.csv');
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    toast({
      title: 'Plantilla CSV descargada',
      description: 'Use esta plantilla como ejemplo para importar sus clientes',
      status: 'info',
      duration: 3000,
      isClosable: true,
    });
  };

  const descargarPlantillaExcel = async () => {
    try {
      await clientesService.descargarPlantillaExcel();
      toast({
        title: 'Plantilla Excel descargada',
        description: 'Archivo Excel con ejemplos e instrucciones completas',
        status: 'success',
        duration: 4000,
        isClosable: true,
      });
    } catch (error) {
      console.error('Error al descargar plantilla Excel:', error);
      toast({
        title: 'Error al descargar plantilla',
        description: 'No se pudo descargar la plantilla Excel',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent maxW="800px">
        <ModalHeader>
          <HStack spacing={3}>
            <Icon as={AttachmentIcon} color="blue.500" />
            <Text>Importar Clientes Masivamente</Text>
          </HStack>
        </ModalHeader>
        <ModalCloseButton />
        
        <ModalBody>
          <VStack spacing={6} align="stretch">
            
            {/* Instrucciones y plantilla */}
            {etapa === 'seleccion' && (
              <>
                <Alert status="info" borderRadius="md">
                  <AlertIcon />
                  <Box>
                    <Text fontWeight="bold" mb={1}>
                      📋 Instrucciones para importar clientes
                    </Text>
                    <UnorderedList spacing={1} fontSize="sm">
                      <ListItem><strong>Formatos soportados:</strong> Excel (.xlsx, .xls) recomendado, CSV</ListItem>
                      <ListItem><strong>Columnas requeridas:</strong> nombre, documento, tipo_documento</ListItem>
                      <ListItem><strong>Columnas opcionales:</strong> direccion, telefono, email</ListItem>
                      <ListItem><strong>tipo_documento:</strong> debe ser "dni" o "ruc"</ListItem>
                      <ListItem><strong>Límite:</strong> 10MB máximo por archivo</ListItem>
                    </UnorderedList>
                  </Box>
                </Alert>

                <HStack spacing={3}>
                  <Button
                    leftIcon={<DownloadIcon />}
                    colorScheme="green"
                    onClick={descargarPlantillaExcel}
                    size="sm"
                  >
                    📊 Descargar Plantilla Excel
                  </Button>
                  <Button
                    leftIcon={<DownloadIcon />}
                    colorScheme="blue"
                    variant="outline"
                    onClick={descargarPlantillaCSV}
                    size="sm"
                  >
                    📄 Descargar Plantilla CSV
                  </Button>
                  <Spacer />
                </HStack>

                <Divider />

                {/* Área de carga de archivo */}
                <FormControl>
                  <FormLabel>Seleccionar archivo:</FormLabel>
                  <Box
                    border="2px dashed"
                    borderColor={arrastrando ? "blue.400" : archivo ? "green.400" : "gray.300"}
                    borderRadius="lg"
                    p={8}
                    textAlign="center"
                    bg={arrastrando ? "blue.50" : archivo ? "green.50" : "gray.50"}
                    cursor="pointer"
                    transition="all 0.2s"
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <VStack spacing={3}>
                      <Icon 
                        as={AttachmentIcon} 
                        w={8} 
                        h={8} 
                        color={archivo ? "green.500" : "gray.400"} 
                      />
                      
                      {archivo ? (
                        <VStack spacing={1}>
                          <Text fontWeight="bold" color="green.600">
                            ✅ Archivo seleccionado
                          </Text>
                          <Text fontSize="sm" color="gray.600">
                            {archivo.name} ({(archivo.size / 1024).toFixed(1)} KB)
                          </Text>
                          <Text fontSize="xs" color="gray.500">
                            Haga clic para cambiar archivo
                          </Text>
                        </VStack>
                      ) : (
                        <VStack spacing={1}>
                          <Text fontWeight="bold" color="gray.600">
                            {arrastrando ? "Suelte el archivo aquí" : "Arrastra un archivo aquí o haz clic para seleccionar"}
                          </Text>
                          <Text fontSize="sm" color="gray.500">
                            Excel (.xlsx, .xls) recomendado, CSV - Máximo 10MB
                          </Text>
                        </VStack>
                      )}
                    </VStack>

                    <Input
                      ref={fileInputRef}
                      type="file"
                      accept=".csv,.xlsx,.xls"
                      onChange={handleInputChange}
                      style={{ display: 'none' }}
                    />
                  </Box>
                </FormControl>
              </>
            )}

            {/* Progreso de procesamiento */}
            {etapa === 'procesando' && (
              <VStack spacing={4}>
                <Alert status="info" borderRadius="md">
                  <AlertIcon />
                  <Text>Procesando archivo... Por favor espere.</Text>
                </Alert>
                <Progress size="lg" isIndeterminate colorScheme="blue" />
                <Text fontSize="sm" color="gray.600">
                  Validando datos y creando clientes...
                </Text>
              </VStack>
            )}

            {/* Resultados de la importación */}
            {etapa === 'resultados' && resultados && (
              <VStack spacing={4} align="stretch">
                {resultados.success ? (
                  <Alert status="success" borderRadius="md">
                    <AlertIcon />
                    <Box>
                      <Text fontWeight="bold">✅ Importación completada exitosamente</Text>
                      <Text fontSize="sm">{resultados.mensaje}</Text>
                    </Box>
                  </Alert>
                ) : (
                  <Alert status="error" borderRadius="md">
                    <AlertIcon />
                    <Box>
                      <Text fontWeight="bold">❌ Error en la importación</Text>
                      <Text fontSize="sm">{resultados.error}</Text>
                    </Box>
                  </Alert>
                )}

                {/* Estadísticas */}
                {resultados.estadisticas && (
                  <Box p={4} bg="gray.50" borderRadius="md">
                    <Text fontWeight="bold" mb={3}>📊 Resumen de importación:</Text>
                    <HStack spacing={6} wrap="wrap">
                      <Badge colorScheme="green" p={2} borderRadius="md">
                        ✅ Exitosos: {resultados.estadisticas.exitosos}
                      </Badge>
                      <Badge colorScheme="red" p={2} borderRadius="md">
                        ❌ Errores: {resultados.estadisticas.errores}
                      </Badge>
                      <Badge colorScheme="orange" p={2} borderRadius="md">
                        🔄 Duplicados: {resultados.estadisticas.duplicados}
                      </Badge>
                      <Badge colorScheme="blue" p={2} borderRadius="md">
                        📄 Total filas: {resultados.estadisticas.total_filas}
                      </Badge>
                    </HStack>
                  </Box>
                )}

                {/* Detalles en acordeones */}
                <Accordion allowMultiple>
                  
                  {/* Clientes exitosos */}
                  {resultados.detalles_exitosos && resultados.detalles_exitosos.length > 0 && (
                    <AccordionItem>
                      <AccordionButton>
                        <Box flex="1" textAlign="left">
                          <HStack>
                            <CheckCircleIcon color="green.500" />
                            <Text fontWeight="bold">
                              Clientes creados exitosamente ({resultados.detalles_exitosos.length})
                            </Text>
                          </HStack>
                        </Box>
                        <AccordionIcon />
                      </AccordionButton>
                      <AccordionPanel pb={4}>
                        <Table size="sm" variant="striped">
                          <Thead>
                            <Tr>
                              <Th>Fila</Th>
                              <Th>Nombre</Th>
                              <Th>Documento</Th>
                              <Th>Tipo</Th>
                            </Tr>
                          </Thead>
                          <Tbody>
                            {resultados.detalles_exitosos.slice(0, 20).map((cliente, index) => (
                              <Tr key={index}>
                                <Td>{cliente.fila}</Td>
                                <Td>{cliente.nombre}</Td>
                                <Td>{cliente.documento}</Td>
                                <Td>
                                  <Badge colorScheme={cliente.tipo_documento === 'dni' ? 'blue' : 'purple'}>
                                    {cliente.tipo_documento.toUpperCase()}
                                  </Badge>
                                </Td>
                              </Tr>
                            ))}
                          </Tbody>
                        </Table>
                        {resultados.detalles_exitosos.length > 20 && (
                          <Text fontSize="sm" color="gray.500" mt={2}>
                            ... y {resultados.detalles_exitosos.length - 20} más
                          </Text>
                        )}
                      </AccordionPanel>
                    </AccordionItem>
                  )}

                  {/* Errores */}
                  {resultados.detalles_errores && resultados.detalles_errores.length > 0 && (
                    <AccordionItem>
                      <AccordionButton>
                        <Box flex="1" textAlign="left">
                          <HStack>
                            <WarningIcon color="red.500" />
                            <Text fontWeight="bold">
                              Errores encontrados ({resultados.detalles_errores.length})
                            </Text>
                          </HStack>
                        </Box>
                        <AccordionIcon />
                      </AccordionButton>
                      <AccordionPanel pb={4}>
                        <VStack align="stretch" spacing={2}>
                          {resultados.detalles_errores.slice(0, 10).map((error, index) => (
                            <Alert key={index} status="error" size="sm" borderRadius="md">
                              <AlertIcon />
                              <Text fontSize="sm">{error}</Text>
                            </Alert>
                          ))}
                        </VStack>
                        {resultados.detalles_errores.length > 10 && (
                          <Text fontSize="sm" color="gray.500" mt={2}>
                            ... y {resultados.detalles_errores.length - 10} errores más
                          </Text>
                        )}
                      </AccordionPanel>
                    </AccordionItem>
                  )}

                  {/* Duplicados */}
                  {resultados.detalles_duplicados && resultados.detalles_duplicados.length > 0 && (
                    <AccordionItem>
                      <AccordionButton>
                        <Box flex="1" textAlign="left">
                          <HStack>
                            <InfoIcon color="orange.500" />
                            <Text fontWeight="bold">
                              Duplicados omitidos ({resultados.detalles_duplicados.length})
                            </Text>
                          </HStack>
                        </Box>
                        <AccordionIcon />
                      </AccordionButton>
                      <AccordionPanel pb={4}>
                        <VStack align="stretch" spacing={2}>
                          {resultados.detalles_duplicados.slice(0, 10).map((duplicado, index) => (
                            <Alert key={index} status="warning" size="sm" borderRadius="md">
                              <AlertIcon />
                              <Text fontSize="sm">{duplicado}</Text>
                            </Alert>
                          ))}
                        </VStack>
                        {resultados.detalles_duplicados.length > 10 && (
                          <Text fontSize="sm" color="gray.500" mt={2}>
                            ... y {resultados.detalles_duplicados.length - 10} duplicados más
                          </Text>
                        )}
                      </AccordionPanel>
                    </AccordionItem>
                  )}

                </Accordion>
              </VStack>
            )}

          </VStack>
        </ModalBody>

        <ModalFooter>
          <HStack spacing={3}>
            {etapa === 'seleccion' && (
              <>
                <Button variant="ghost" onClick={handleClose}>
                  Cancelar
                </Button>
                <Button
                  colorScheme="blue"
                  onClick={procesarImportacion}
                  disabled={!archivo || cargando}
                  leftIcon={<AttachmentIcon />}
                >
                  Importar Clientes
                </Button>
              </>
            )}

            {etapa === 'procesando' && (
              <Button variant="ghost" onClick={handleClose} disabled={cargando}>
                Cancelar
              </Button>
            )}

            {etapa === 'resultados' && (
              <>
                <Button
                  variant="ghost"
                  onClick={() => {
                    setEtapa('seleccion');
                    setArchivo(null);
                    setResultados(null);
                  }}
                >
                  Importar Otro Archivo
                </Button>
                <Button colorScheme="blue" onClick={handleClose}>
                  Cerrar
                </Button>
              </>
            )}
          </HStack>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default ImportarClientes; 