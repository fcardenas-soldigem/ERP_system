import React, { useState } from 'react';
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
  Text,
  Input,
  useToast,
  Alert,
  AlertIcon,
  Box,
  Link,
  Progress
} from '@chakra-ui/react';
import { DownloadIcon, AttachmentIcon } from '@chakra-ui/icons';
import { useQueryClient } from '@tanstack/react-query';
import { inventarioService } from '../../services/inventario.service';

const ImportarProductosModal = ({ isOpen, onClose }) => {
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const toast = useToast();
  const queryClient = useQueryClient();

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && selectedFile.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') {
      setFile(selectedFile);
    } else {
      toast({
        title: 'Error',
        description: 'Por favor seleccione un archivo Excel (.xlsx)',
        status: 'error',
        duration: 3000,
      });
    }
  };

  const handleDownloadTemplate = async () => {
    try {
      await inventarioService.descargarTemplate();
      toast({
        title: 'Template descargado',
        description: 'El template se ha descargado correctamente',
        status: 'success',
        duration: 3000,
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'No se pudo descargar el template',
        status: 'error',
        duration: 3000,
      });
    }
  };

  const handleUpload = async () => {
    if (!file) {
      toast({
        title: 'Error',
        description: 'Por favor seleccione un archivo',
        status: 'error',
        duration: 3000,
      });
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);

    try {
      // Simular progreso de carga
      const interval = setInterval(() => {
        setUploadProgress(prev => Math.min(prev + 10, 90));
      }, 200);

      const response = await inventarioService.importarProductos(file);
      
      clearInterval(interval);
      setUploadProgress(100);

      // Construir mensaje de éxito con detalles
      let successMessage = `${response.productos_creados} productos importados correctamente`;
      
      if (response.categorias_creadas && response.categorias_creadas.length > 0) {
        successMessage += `\n\nCategorías creadas automáticamente: ${response.categorias_creadas.join(', ')}`;
      }
      
      if (response.almacenes_creados && response.almacenes_creados.length > 0) {
        successMessage += `\n\nAlmacenes creados automáticamente: ${response.almacenes_creados.join(', ')}`;
      }

      if (response.errores && response.errores.length > 0) {
        successMessage += `\n\nAdvertencias: ${response.errores.length} productos no se pudieron importar`;
      }

      toast({
        title: 'Importación exitosa',
        description: successMessage,
        status: 'success',
        duration: 8000,
        isClosable: true,
      });

      // Invalidar queries para actualizar los datos
      queryClient.invalidateQueries(['productos']);
      queryClient.invalidateQueries(['valorTotal']);
      queryClient.invalidateQueries(['categorias']);

      setTimeout(() => {
        onClose();
        setFile(null);
        setUploadProgress(0);
      }, 1000);

    } catch (error) {
      let errorMessage = 'Error al importar los productos';
      
      if (error.response?.data?.errores) {
        errorMessage += `\n\nErrores:\n${error.response.data.errores.slice(0, 5).join('\n')}`;
        if (error.response.data.errores.length > 5) {
          errorMessage += `\n... y ${error.response.data.errores.length - 5} errores más`;
        }
      } else if (error.response?.data?.error) {
        errorMessage = error.response.data.error;
      }

      toast({
        title: 'Error',
        description: errorMessage,
        status: 'error',
        duration: 8000,
        isClosable: true,
      });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Importar Productos</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4} align="stretch">
            <Alert status="info">
              <AlertIcon />
              <VStack spacing={2} align="start">
                <Text>
                  Descargue el template de Excel, llénelo con sus productos y súbalo para importarlos masivamente.
                </Text>
                <Text fontSize="sm" color="blue.600">
                  ✅ Las categorías que no existan se crearán automáticamente<br />
                  ✅ Los almacenes que no existan se crearán automáticamente<br />
                  ✅ Soporte para múltiples monedas (PEN/USD)
                </Text>
                <Link color="blue.500" onClick={handleDownloadTemplate} cursor="pointer">
                  <DownloadIcon mr={2} />
                  Descargar template
                </Link>
              </VStack>
            </Alert>

            <Box>
              <Text mb={2}>Seleccione el archivo Excel (.xlsx):</Text>
              <Input
                type="file"
                accept=".xlsx"
                onChange={handleFileChange}
                disabled={isUploading}
              />
            </Box>

            {file && (
              <Text color="green.500">
                Archivo seleccionado: {file.name}
              </Text>
            )}

            {uploadProgress > 0 && (
              <Box>
                <Text mb={2}>Progreso: {uploadProgress}%</Text>
                <Progress value={uploadProgress} size="sm" colorScheme="blue" />
              </Box>
            )}
          </VStack>
        </ModalBody>

        <ModalFooter>
          <Button
            colorScheme="blue"
            mr={3}
            onClick={handleUpload}
            isLoading={isUploading}
            leftIcon={<AttachmentIcon />}
            disabled={!file}
          >
            Importar
          </Button>
          <Button variant="ghost" onClick={onClose} disabled={isUploading}>
            Cancelar
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default ImportarProductosModal; 