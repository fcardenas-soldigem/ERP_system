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
  FormControl,
  FormLabel,
  Input,
  VStack,
  useToast,
} from '@chakra-ui/react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { comprasAPI } from '../../api';

const CrearEmpresa = ({ isOpen, onClose, onSuccess }) => {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [empresa, setEmpresa] = useState({
    nombre: '',
    ruc: '',
    direccion: '',
    telefono: '',
    email: ''
  });

  const createEmpresaMutation = useMutation({
    mutationFn: async (data) => {
      const response = await comprasAPI.createEmpresa(data);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries(['empresas']);
      toast({
        title: 'Empresa creada exitosamente',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      onSuccess && onSuccess(data);
      onClose();
    },
    onError: (error) => {
      console.error('Error detallado:', error.response?.data);
      toast({
        title: 'Error al crear empresa',
        description: error.response?.data?.detail || 'Error al crear la empresa',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!empresa.nombre || !empresa.ruc) {
      toast({
        title: 'Error de validación',
        description: 'Nombre y RUC son obligatorios',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }
    createEmpresaMutation.mutate(empresa);
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <ModalOverlay />
      <ModalContent>
        <form onSubmit={handleSubmit}>
          <ModalHeader>Crear Nueva Empresa</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel>Nombre/Razón Social</FormLabel>
                <Input
                  value={empresa.nombre}
                  onChange={(e) => setEmpresa(prev => ({
                    ...prev,
                    nombre: e.target.value
                  }))}
                />
              </FormControl>

              <FormControl isRequired>
                <FormLabel>RUC</FormLabel>
                <Input
                  value={empresa.ruc}
                  onChange={(e) => setEmpresa(prev => ({
                    ...prev,
                    ruc: e.target.value
                  }))}
                  maxLength={11}
                />
              </FormControl>

              <FormControl>
                <FormLabel>Dirección</FormLabel>
                <Input
                  value={empresa.direccion}
                  onChange={(e) => setEmpresa(prev => ({
                    ...prev,
                    direccion: e.target.value
                  }))}
                />
              </FormControl>

              <FormControl>
                <FormLabel>Teléfono</FormLabel>
                <Input
                  value={empresa.telefono}
                  onChange={(e) => setEmpresa(prev => ({
                    ...prev,
                    telefono: e.target.value
                  }))}
                  maxLength={9}
                />
              </FormControl>

              <FormControl>
                <FormLabel>Email</FormLabel>
                <Input
                  type="email"
                  value={empresa.email}
                  onChange={(e) => setEmpresa(prev => ({
                    ...prev,
                    email: e.target.value
                  }))}
                />
              </FormControl>
            </VStack>
          </ModalBody>

          <ModalFooter>
            <Button colorScheme="blue" mr={3} type="submit">
              Crear Empresa
            </Button>
            <Button onClick={onClose}>Cancelar</Button>
          </ModalFooter>
        </form>
      </ModalContent>
    </Modal>
  );
};

export default CrearEmpresa; 