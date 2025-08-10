import React from 'react';
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
  useToast,
  VStack
} from '@chakra-ui/react';
import { useForm } from 'react-hook-form';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { inventarioService } from '../../services/inventario.service';

const CategoriaForm = ({ isOpen, onClose }) => {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { register, handleSubmit, reset, formState: { errors } } = useForm();

  const createCategoriaMutation = useMutation({
    mutationFn: inventarioService.crearCategoria,
    onSuccess: () => {
      queryClient.invalidateQueries(['categorias']);
      toast({
        title: 'Categoría creada',
        status: 'success',
        duration: 3000,
      });
      reset();
      onClose();
    },
    onError: (error) => {
      toast({
        title: 'Error al crear la categoría',
        description: error.message,
        status: 'error',
        duration: 3000,
      });
    }
  });

  const onSubmit = (data) => {
    createCategoriaMutation.mutate(data);
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Nueva Categoría</ModalHeader>
        <ModalCloseButton />
        <form onSubmit={handleSubmit(onSubmit)}>
          <ModalBody>
            <VStack spacing={4}>
              <FormControl isRequired isInvalid={errors.nombre}>
                <FormLabel>Nombre</FormLabel>
                <Input
                  {...register('nombre', { required: 'Este campo es requerido' })}
                  placeholder="Nombre de la categoría"
                />
              </FormControl>
              <FormControl>
                <FormLabel>Descripción</FormLabel>
                <Input
                  {...register('descripcion')}
                  placeholder="Descripción de la categoría"
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
              type="submit"
              isLoading={createCategoriaMutation.isLoading}
            >
              Crear
            </Button>
          </ModalFooter>
        </form>
      </ModalContent>
    </Modal>
  );
};

export default CategoriaForm; 