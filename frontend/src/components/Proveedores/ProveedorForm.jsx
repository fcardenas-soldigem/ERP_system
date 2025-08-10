import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Button,
  FormControl,
  FormLabel,
  Input,
  VStack,
  useToast,
  Switch,
  FormErrorMessage,
  Container,
  Card,
  CardBody,
  Heading,
  HStack,
  Spinner,
  Textarea,
  Text,
  Badge,
} from '@chakra-ui/react';
import { SearchIcon } from '@chakra-ui/icons';
import { useForm } from 'react-hook-form';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { proveedoresService } from '../../services/proveedores.service';

const ProveedorForm = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();
  const { id } = useParams();
  const [isConsultingRuc, setIsConsultingRuc] = useState(false);
  const [rucData, setRucData] = useState(null);
  
  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm({
    defaultValues: {
      razon_social: '',
      ruc: '',
      direccion: '',
      telefono: '',
      email: '',
      activo: true,
    },
  });

  const watchedRuc = watch('ruc');

  const { data: proveedor, isLoading: isLoadingProveedor } = useQuery({
    queryKey: ['proveedor', id],
    queryFn: () => proveedoresService.getProveedor(id),
    enabled: !!id,
  });

  // Effect para resetear el formulario cuando se carga el proveedor
  useEffect(() => {
    if (proveedor) {
      reset(proveedor);
    }
  }, [proveedor, reset]);

  const handleConsultarRuc = async () => {
    const ruc = watchedRuc;
    
    if (!ruc || ruc.length !== 11) {
      toast({
        title: 'RUC inválido',
        description: 'El RUC debe tener 11 dígitos',
        status: 'warning',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    setIsConsultingRuc(true);
    try {
      const response = await proveedoresService.consultarRuc(ruc);
      
      if (response.success && response.data) {
        const { razon_social, direccion } = response.data;
        
        // Llenar automáticamente los campos
        setValue('razon_social', razon_social || '');
        setValue('direccion', direccion || '');
        
        setRucData(response.data);
        
        toast({
          title: 'RUC consultado exitosamente',
          description: `Datos de ${razon_social} cargados automáticamente`,
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
      }
    } catch (error) {
      console.error('Error consultando RUC:', error);
      toast({
        title: 'Error al consultar RUC',
        description: error.response?.data?.error || 'No se pudo consultar el RUC',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsConsultingRuc(false);
    }
  };

  const mutation = useMutation({
    mutationFn: (data) => {
      if (id) {
        return proveedoresService.actualizarProveedor(id, data);
      }
      return proveedoresService.crearProveedor(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['proveedores']);
      toast({
        title: `Proveedor ${id ? 'actualizado' : 'creado'} exitosamente`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      navigate('/proveedores');
    },
    onError: (error) => {
      toast({
        title: `Error al ${id ? 'actualizar' : 'crear'} el proveedor`,
        description: error.message,
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    },
  });

  const onSubmit = (data) => {
    mutation.mutate(data);
  };

  if (id && isLoadingProveedor) {
    return (
      <Container maxW="container.md" py={5}>
        <Card>
          <CardBody>
            <VStack spacing={5} align="center">
              <Spinner size="xl" />
            </VStack>
          </CardBody>
        </Card>
      </Container>
    );
  }

  return (
    <Container maxW="container.md" py={5}>
      <Card>
        <CardBody>
          <VStack spacing={5} align="stretch">
            <Heading size="lg">{id ? 'Editar' : 'Nuevo'} Proveedor</Heading>
            
            <form onSubmit={handleSubmit(onSubmit)}>
              <VStack spacing={4}>
                <FormControl isInvalid={errors.razon_social}>
                  <FormLabel>Razón Social</FormLabel>
                  <Input
                    {...register('razon_social', {
                      required: 'La razón social es requerida',
                    })}
                    placeholder="Ingrese la razón social"
                  />
                  <FormErrorMessage>
                    {errors.razon_social && errors.razon_social.message}
                  </FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={errors.ruc}>
                  <FormLabel>RUC</FormLabel>
                  <HStack>
                    <Input
                      {...register('ruc', {
                        required: 'El RUC es requerido',
                        pattern: {
                          value: /^\d{11}$/,
                          message: 'El RUC debe tener 11 dígitos',
                        },
                      })}
                      placeholder="Ingrese RUC (11 dígitos)"
                      maxLength={11}
                    />
                    <Button
                      leftIcon={isConsultingRuc ? <Spinner size="sm" /> : <SearchIcon />}
                      colorScheme="blue"
                      onClick={handleConsultarRuc}
                      disabled={isConsultingRuc || !watchedRuc || watchedRuc.length !== 11}
                      minWidth="120px"
                    >
                      {isConsultingRuc ? 'Consultando...' : 'Consultar'}
                    </Button>
                  </HStack>
                  {rucData && (
                    <Text fontSize="sm" color="green.500" mt={1}>
                      ✓ RUC válido - {rucData.estado} - {rucData.condicion}
                    </Text>
                  )}
                  <FormErrorMessage>
                    {errors.ruc && errors.ruc.message}
                  </FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={errors.direccion}>
                  <FormLabel>Dirección</FormLabel>
                  <Textarea
                    {...register('direccion')}
                    placeholder="Ingrese la dirección (opcional)"
                    rows={3}
                  />
                  <FormErrorMessage>
                    {errors.direccion && errors.direccion.message}
                  </FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={errors.telefono}>
                  <FormLabel>Teléfono</FormLabel>
                  <Input
                    {...register('telefono', {
                      minLength: {
                        value: 7,
                        message: 'El teléfono debe tener al menos 7 dígitos',
                      },
                    })}
                    placeholder="Ingrese el teléfono (opcional)"
                  />
                  <FormErrorMessage>
                    {errors.telefono && errors.telefono.message}
                  </FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={errors.email}>
                  <FormLabel>Email</FormLabel>
                  <Input
                    type="email"
                    {...register('email', {
                      pattern: {
                        value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                        message: 'Ingrese un email válido',
                      },
                    })}
                    placeholder="Ingrese el email (opcional)"
                  />
                  <FormErrorMessage>
                    {errors.email && errors.email.message}
                  </FormErrorMessage>
                </FormControl>

                <FormControl display="flex" alignItems="center">
                  <FormLabel htmlFor="activo" mb="0">
                    Activo
                  </FormLabel>
                  <Switch
                    id="activo"
                    {...register('activo')}
                  />
                </FormControl>

                <HStack justify="flex-end" spacing={4} pt={4} width="100%">
                  <Button variant="ghost" onClick={() => navigate('/proveedores')}>
                    Cancelar
                  </Button>
                  <Button
                    colorScheme="blue"
                    type="submit"
                    isLoading={mutation.isLoading}
                  >
                    {id ? 'Actualizar' : 'Crear'} Proveedor
                  </Button>
                </HStack>
              </VStack>
            </form>
          </VStack>
        </CardBody>
      </Card>
    </Container>
  );
};

export default ProveedorForm; 