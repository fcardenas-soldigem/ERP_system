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
  Input,
  FormControl,
  FormLabel,
  useToast,
  Text,
  VStack,
  Link,
} from '@chakra-ui/react';
import { comprasService } from '../../services/compras.service';
import { useQueryClient } from '@tanstack/react-query';

const ImportarCompras = ({ isOpen, onClose }) => {
  const [file, setFile] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const toast = useToast();
  const queryClient = useQueryClient();

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      if (selectedFile.size > 5 * 1024 * 1024) { // 5MB
        toast({
          title: 'Archivo muy grande',
          description: 'El archivo no debe superar los 5MB',
          status: 'error',
          duration: 3000,
        });
        return;
      }
      setFile(selectedFile);
    }
  };

  const handleDownloadTemplate = async () => {
    try {
      await comprasService.descargarTemplateCompras();
    } catch (error) {
      toast({
        title: 'Error al descargar el template',
        description: error.message,
        status: 'error',
        duration: 3000,
      });
    }
  };

  const handleSubmit = async () => {
    if (!file) {
      toast({
        title: 'Archivo requerido',
        description: 'Por favor seleccione un archivo para importar',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    try {
      setIsLoading(true);
      const formData = new FormData();
      formData.append('file', file);
      await comprasService.importarExcel(formData);
      
      queryClient.invalidateQueries(['compras']);
      
      toast({
        title: 'Importación exitosa',
        description: 'Las compras se han importado correctamente',
        status: 'success',
        duration: 3000,
      });
      
      onClose();
      setFile(null);
    } catch (error) {
      toast({
        title: 'Error en la importación',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Importar Compras desde Excel</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4}>
            <Text>
              Descargue la plantilla y llénela con sus datos antes de importar.
            </Text>
            <Link
              color="blue.500"
              onClick={handleDownloadTemplate}
              cursor="pointer"
            >
              Descargar plantilla
            </Link>
            <FormControl>
              <FormLabel>Seleccionar archivo</FormLabel>
              <Input
                type="file"
                accept=".xlsx,.xls,.csv"
                onChange={handleFileChange}
                sx={{
                  '::file-selector-button': {
                    height: '100%',
                    padding: '0 20px',
                    background: 'gray.100',
                    border: 'none',
                    borderRight: '1px solid',
                    borderColor: 'gray.200',
                    cursor: 'pointer',
                    '&:hover': {
                      background: 'gray.200'
                    }
                  }
                }}
              />
            </FormControl>
          </VStack>
        </ModalBody>

        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose}>
            Cancelar
          </Button>
          <Button
            colorScheme="blue"
            onClick={handleSubmit}
            isLoading={isLoading}
          >
            Importar
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default ImportarCompras; 