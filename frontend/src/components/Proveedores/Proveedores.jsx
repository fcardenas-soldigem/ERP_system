import React from 'react';
import { Box, Heading, Text, Button, Flex, useToast } from '@chakra-ui/react';
import { AddIcon, DownloadIcon } from '@chakra-ui/icons';
import { useNavigate } from 'react-router-dom';
import ProveedoresList from './ProveedoresList';
import { proveedoresService } from '../../services/proveedores.service';

const Proveedores = () => {
  const navigate = useNavigate();
  const toast = useToast();

  const handleExportExcel = async () => {
    try {
      const blob = await proveedoresService.exportarProveedores();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Proveedores_${new Date().toISOString().slice(0,10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast({
        title: 'Exportación exitosa',
        description: 'El archivo se ha descargado correctamente',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      toast({
        title: 'Error al exportar',
        description: error.message || 'No se pudo exportar el archivo',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  return (
    <Box p={4}>
      <Flex justify="space-between" align="center" mb={6}>
        <Box>
          <Heading size="lg">Proveedores</Heading>
          <Text color="gray.600">
            Gestiona tus proveedores y mantén actualizada su información
          </Text>
        </Box>
        <Flex gap={2}>
          <Button
            leftIcon={<DownloadIcon />}
            colorScheme="green"
            onClick={handleExportExcel}
          >
            Exportar Excel
          </Button>
          <Button 
            colorScheme="teal" 
            leftIcon={<AddIcon />}
            onClick={() => navigate('/proveedores/nuevo')}
          >
            Nuevo Proveedor
          </Button>
        </Flex>
      </Flex>

      <ProveedoresList />
    </Box>
  );
};

export default Proveedores; 