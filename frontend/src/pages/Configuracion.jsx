import React from 'react';
import {
    Box,
    Heading,
    VStack,
    FormControl,
    FormLabel,
    Input,
    Button,
    useToast,
    Select,
    Text,
    Divider,
    HStack,
    Switch,
    FormHelperText,
} from '@chakra-ui/react';

const Configuracion = () => {
    const toast = useToast();

    const handleSubmit = (e) => {
        e.preventDefault();
        toast({
            title: 'Configuración guardada',
            description: 'Los cambios se han guardado correctamente',
            status: 'success',
            duration: 3000,
            isClosable: true,
        });
    };

    return (
        <Box p={5}>
            <Heading mb={5}>Configuración del Sistema</Heading>
            
            <VStack spacing={5} align="stretch">
                <Box p={5} borderWidth="1px" borderRadius="lg">
                    <Heading size="md" mb={4}>Configuración General</Heading>
                    <form onSubmit={handleSubmit}>
                        <VStack spacing={4}>
                            <FormControl>
                                <FormLabel>Nombre de la Empresa</FormLabel>
                                <Input placeholder="Ingrese el nombre de la empresa" />
                            </FormControl>

                            <FormControl>
                                <FormLabel>RUC</FormLabel>
                                <Input placeholder="Ingrese el RUC de la empresa" />
                            </FormControl>

                            <FormControl>
                                <FormLabel>Dirección</FormLabel>
                                <Input placeholder="Ingrese la dirección de la empresa" />
                            </FormControl>

                            <FormControl>
                                <FormLabel>Teléfono</FormLabel>
                                <Input placeholder="Ingrese el teléfono de la empresa" />
                            </FormControl>

                            <FormControl>
                                <FormLabel>Email</FormLabel>
                                <Input type="email" placeholder="Ingrese el email de la empresa" />
                            </FormControl>
                        </VStack>
                    </form>
                </Box>

                <Box p={5} borderWidth="1px" borderRadius="lg">
                    <Heading size="md" mb={4}>Configuración de Facturación</Heading>
                    <VStack spacing={4}>
                        <FormControl>
                            <FormLabel>Serie de Facturación</FormLabel>
                            <Input placeholder="Ej: F001" />
                        </FormControl>

                        <FormControl>
                            <FormLabel>Número de Factura Inicial</FormLabel>
                            <Input type="number" placeholder="Ej: 1" />
                        </FormControl>

                        <FormControl>
                            <FormLabel>Formato de Factura</FormLabel>
                            <Select placeholder="Seleccione el formato">
                                <option value="A4">A4</option>
                                <option value="TICKET">Ticket</option>
                            </Select>
                        </FormControl>
                    </VStack>
                </Box>

                <Box p={5} borderWidth="1px" borderRadius="lg">
                    <Heading size="md" mb={4}>Preferencias del Sistema</Heading>
                    <VStack spacing={4}>
                        <FormControl display="flex" alignItems="center">
                            <FormLabel mb="0">Notificaciones por Email</FormLabel>
                            <Switch colorScheme="blue" />
                        </FormControl>

                        <FormControl display="flex" alignItems="center">
                            <FormLabel mb="0">Backup Automático</FormLabel>
                            <Switch colorScheme="blue" />
                        </FormControl>

                        <FormControl display="flex" alignItems="center">
                            <FormLabel mb="0">Modo Oscuro</FormLabel>
                            <Switch colorScheme="blue" />
                        </FormControl>
                    </VStack>
                </Box>

                <HStack justify="flex-end" mt={5}>
                    <Button colorScheme="gray" variant="outline">
                        Cancelar
                    </Button>
                    <Button colorScheme="blue" onClick={handleSubmit}>
                        Guardar Cambios
                    </Button>
                </HStack>
            </VStack>
        </Box>
    );
};

export default Configuracion; 