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
    VStack,
    Textarea
} from '@chakra-ui/react';
import { useForm } from 'react-hook-form';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { inventarioService } from '../../services/inventario.service';

const AlmacenForm = ({ isOpen, onClose }) => {
    const toast = useToast();
    const queryClient = useQueryClient();
    const { register, handleSubmit, reset, formState: { errors } } = useForm();

    const createAlmacenMutation = useMutation({
        mutationFn: inventarioService.crearAlmacen,
        onSuccess: () => {
            queryClient.invalidateQueries(['almacenes']);
            toast({
                title: 'Almacén creado',
                status: 'success',
                duration: 3000,
            });
            reset();
            onClose();
        },
        onError: (error) => {
            toast({
                title: 'Error al crear el almacén',
                description: error.message,
                status: 'error',
                duration: 3000,
            });
        }
    });

    const onSubmit = (data) => {
        createAlmacenMutation.mutate(data);
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose}>
            <ModalOverlay />
            <ModalContent>
                <ModalHeader>Nuevo Almacén</ModalHeader>
                <ModalCloseButton />
                <form onSubmit={handleSubmit(onSubmit)}>
                    <ModalBody>
                        <VStack spacing={4}>
                            <FormControl isRequired isInvalid={errors.nombre}>
                                <FormLabel>Nombre</FormLabel>
                                <Input
                                    {...register('nombre', { required: 'Este campo es requerido' })}
                                    placeholder="Nombre del almacén"
                                />
                            </FormControl>
                            <FormControl isRequired isInvalid={errors.direccion}>
                                <FormLabel>Dirección</FormLabel>
                                <Textarea
                                    {...register('direccion', { required: 'Este campo es requerido' })}
                                    placeholder="Dirección del almacén"
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
                            isLoading={createAlmacenMutation.isLoading}
                        >
                            Crear
                        </Button>
                    </ModalFooter>
                </form>
            </ModalContent>
        </Modal>
    );
};

export default AlmacenForm; 