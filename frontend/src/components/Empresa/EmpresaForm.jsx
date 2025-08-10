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
  FormErrorMessage,
  VStack,
  HStack,
} from '@chakra-ui/react';
import { useForm } from 'react-hook-form';
import { useMutation } from '@tanstack/react-query';
import api from '../../api';
import { toast } from 'react-toastify';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

const EmpresaForm = ({ isOpen, onClose }) => {
  const { user, setUser, checkAuth } = useAuth();
  const navigate = useNavigate();
  
  const { register, handleSubmit, formState: { errors } } = useForm({
    defaultValues: {
      razon_social: 'Soldigem',
      ruc: '20123456789',
      email: 'contacto@soldigem.com',
      direccion: 'Av. Principal 123',
      telefono: '987654321'
    }
  });

  const mutation = useMutation({
    mutationFn: async (formData) => {
      try {
        // 1. Crear empresa
        console.log('1. Intentando crear empresa con datos:', formData);
        const empresaResponse = await api.post('/api/empresas/', formData);
        console.log('2. Empresa creada exitosamente:', empresaResponse.data);
        
        // 2. Obtener perfil actualizado
        console.log('3. Obteniendo perfil actualizado');
        const profileResponse = await api.get('/api/auth/profile/');
        console.log('4. Perfil obtenido:', profileResponse.data);

        // 3. Actualizar usuario en el contexto
        const updatedUser = {
          ...profileResponse.data,
          empresa: empresaResponse.data
        };
        console.log('5. Usuario actualizado:', updatedUser);
        
        setUser(updatedUser);
        
        return empresaResponse.data;
      } catch (error) {
        console.error('Error:', error);
        throw error;
      }
    },
    onSuccess: async (data) => {
      console.log('6. Mutación completada exitosamente:', data);
      toast.success('Empresa creada exitosamente');
      await checkAuth();
      onClose();
      navigate('/dashboard');
    },
    onError: (error) => {
      const errorMessage = error.response?.data?.detail || 'Error al crear la empresa';
      toast.error(errorMessage);
    }
  });

  const onSubmit = async (data) => {
    console.log('Formulario enviado con:', data);
    mutation.mutate(data);
  };

  // Si el usuario ya tiene una empresa, redirigir al dashboard
  React.useEffect(() => {
    if (user?.empresa) {
      navigate('/dashboard');
    }
  }, [user, navigate]);

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose}
      closeOnOverlayClick={true}
      isCentered
    >
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Crear Empresa</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <form id="empresa-form" onSubmit={handleSubmit(onSubmit)}>
            <VStack spacing={4}>
              <FormControl isInvalid={errors.razon_social}>
                <FormLabel>Razón Social</FormLabel>
                <Input {...register('razon_social', { required: 'Este campo es requerido' })} />
              </FormControl>

              <FormControl isInvalid={errors.ruc}>
                <FormLabel>RUC</FormLabel>
                <Input {...register('ruc', { 
                  required: 'Este campo es requerido',
                  pattern: {
                    value: /^\d{11}$/,
                    message: 'El RUC debe tener 11 dígitos'
                  }
                })} />
              </FormControl>

              <FormControl isInvalid={errors.email}>
                <FormLabel>Email</FormLabel>
                <Input type="email" {...register('email', { 
                  required: 'Este campo es requerido',
                  pattern: {
                    value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                    message: 'Email inválido'
                  }
                })} />
              </FormControl>

              <FormControl isInvalid={errors.direccion}>
                <FormLabel>Dirección</FormLabel>
                <Input {...register('direccion', { required: 'Este campo es requerido' })} />
              </FormControl>

              <FormControl isInvalid={errors.telefono}>
                <FormLabel>Teléfono</FormLabel>
                <Input {...register('telefono', { 
                  required: 'Este campo es requerido',
                  pattern: {
                    value: /^\d{9}$/,
                    message: 'El teléfono debe tener 9 dígitos'
                  }
                })} />
              </FormControl>
            </VStack>
          </form>
        </ModalBody>
        <ModalFooter>
          <HStack spacing={3}>
            <Button onClick={onClose}>Cancelar</Button>
            <Button
              type="submit"
              form="empresa-form"
              colorScheme="blue"
              isLoading={mutation.isLoading}
            >
              Crear Empresa
            </Button>
          </HStack>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default EmpresaForm; 