import React, { useState } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  Button,
  Input,
  Text,
  Box,
  useToast,
} from '@chakra-ui/react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ventasService } from '../../services/ventas.service';

const ImportExcelModal = ({ isOpen, onClose }) => {
  const [file, setFile] = useState(null);
  const [resultado, setResultado] = useState(null);
  const toast = useToast();
  const queryClient = useQueryClient();

  const importMutation = useMutation({
    mutationFn: (file) => ventasService.importarExcel(file),
    onSuccess: () => {
      queryClient.invalidateQueries(['ventas']);
      toast({
        title: 'Importación exitosa',
        description: 'Las ventas se han importado correctamente',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      onClose();
      setFile(null);
    },
    onError: (error) => {
      let mensaje = 'Error al importar el archivo';
      if (error.response && error.response.data) {
        if (typeof error.response.data === 'string') {
          mensaje = error.response.data;
        } else if (error.response.data.error) {
          mensaje = error.response.data.error;
        } else if (error.response.data.mensaje) {
          mensaje = error.response.data.mensaje;
        } else {
          mensaje = JSON.stringify(error.response.data);
        }
      }
      toast({
        title: 'Error al importar',
        description: mensaje,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    },
  });

  const handleImport = async () => {
    if (!file) {
      toast({
        title: 'Error',
        description: 'Por favor seleccione un archivo',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }
    try {
      const result = await importMutation.mutateAsync(file);
      setResultado(result);
    } catch (error) {
      setResultado(null);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Importar Ventas desde Excel</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <Box bg="blue.50" p={4} borderRadius="md" mb={4}>
            <Text>
              Descargue el template de Excel, llénelo con sus ventas y súbalo para importarlas masivamente.
            </Text>
            <Button
              colorScheme="blue"
              variant="link"
              mt={2}
              onClick={async () => {
                try {
                  await ventasService.descargarTemplate();
                } catch (error) {
                  toast({
                    title: 'Error al descargar el template',
                    description: 'No se pudo descargar el archivo. Intente de nuevo.',
                    status: 'error',
                    duration: 3000,
                    isClosable: true,
                  });
                }
              }}
            >
              Descargar template
            </Button>
          </Box>
          <Input
            type="file"
            accept=".xlsx,.xls,.csv"
            onChange={(e) => setFile(e.target.files[0])}
            mb={4}
          />
          <Box fontSize="sm" color="gray.600" mb={2}>
            El archivo debe contener las siguientes columnas:
          </Box>
          <Box as="ul" pl={5} mt={2} fontSize="sm" color="gray.700">
            <Box as="li">cliente_nombre</Box>
            <Box as="li">cliente_documento</Box>
            <Box as="li">fecha_emision (YYYY-MM-DD)</Box>
            <Box as="li">productos (SKUs separados por comas)</Box>
            <Box as="li">cantidades (separadas por comas)</Box>
            <Box as="li">precios_unitarios (separados por comas)</Box>
            <Box as="li">metodo_pago</Box>
            <Box as="li">igv_incluido (Sí/No)</Box>
            <Box as="li">estado</Box>
            <Box as="li">referencia (opcional)</Box>
          </Box>
          {resultado && (
            <Box mt={4} p={3} bg="gray.50" borderRadius="md">
              {resultado.mensaje && (
                <Text fontWeight="bold" color="green.700">{resultado.mensaje}</Text>
              )}
              {resultado.ventas_creadas && resultado.ventas_creadas.length > 0 && (
                <Text color="green.600">Ventas creadas: {resultado.ventas_creadas.length}</Text>
              )}
              {resultado.errores && resultado.errores.length > 0 && (
                <Box mt={2}>
                  <Text fontWeight="bold" color="red.700">Errores encontrados:</Text>
                  <ul style={{ paddingLeft: 20 }}>
                    {resultado.errores.map((error, idx) => (
                      <li key={idx} style={{ color: '#C53030' }}>{error}</li>
                    ))}
                  </ul>
                </Box>
              )}
            </Box>
          )}
        </ModalBody>
        <ModalFooter>
          <Button
            colorScheme="blue"
            mr={3}
            onClick={handleImport}
            isLoading={importMutation.isLoading}
            loadingText="Importando..."
          >
            Importar
          </Button>
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default ImportExcelModal; 