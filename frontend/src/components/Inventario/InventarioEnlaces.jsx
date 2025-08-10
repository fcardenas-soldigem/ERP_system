import React from 'react';
import { Box, Button, SimpleGrid, Text, VStack, Icon } from '@chakra-ui/react';
import { useNavigate } from 'react-router-dom';
import { FaClipboardList, FaHistory, FaPlus } from 'react-icons/fa';

const InventarioEnlaces = () => {
    const navigate = useNavigate();

    const enlaces = [
        {
            titulo: 'Kardex Mejorado',
            descripcion: 'Control detallado de entradas, salidas y saldos con formato profesional',
            icono: FaClipboardList,
            ruta: '/inventario/kardex-mejorado',
            color: 'blue'
        },
        {
            titulo: 'Kardex Clásico',
            descripcion: 'Vista tradicional de movimientos de inventario',
            icono: FaHistory,
            ruta: '/inventario',
            color: 'green'
        },
        {
            titulo: 'Agregar Producto',
            descripcion: 'Registrar nuevos productos en el inventario',
            icono: FaPlus,
            ruta: '/inventario/nuevo',
            color: 'orange'
        }
    ];

    return (
        <Box p={6}>
            <VStack spacing={6} align="start">
                <Box>
                    <Text fontSize="2xl" fontWeight="bold" color="gray.800">
                        📦 Gestión de Inventario
                    </Text>
                    <Text color="gray.600">
                        Accesos rápidos a las diferentes funcionalidades del módulo de inventario
                    </Text>
                </Box>

                <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6} width="100%">
                    {enlaces.map((enlace, index) => (
                        <Box
                            key={index}
                            p={6}
                            borderRadius="md"
                            borderWidth={1}
                            borderColor="gray.200"
                            bg="white"
                            _hover={{ 
                                transform: 'translateY(-2px)',
                                shadow: 'lg',
                                borderColor: `${enlace.color}.300`
                            }}
                            transition="all 0.2s"
                            cursor="pointer"
                            onClick={() => navigate(enlace.ruta)}
                        >
                            <VStack spacing={4} align="start">
                                <Icon as={enlace.icono} w={8} h={8} color={`${enlace.color}.500`} />
                                <VStack spacing={2} align="start">
                                    <Text fontWeight="bold" fontSize="lg" color="gray.800">
                                        {enlace.titulo}
                                    </Text>
                                    <Text fontSize="sm" color="gray.600" noOfLines={3}>
                                        {enlace.descripcion}
                                    </Text>
                                </VStack>
                                <Button
                                    colorScheme={enlace.color}
                                    size="sm"
                                    width="100%"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        navigate(enlace.ruta);
                                    }}
                                >
                                    Acceder
                                </Button>
                            </VStack>
                        </Box>
                    ))}
                </SimpleGrid>
            </VStack>
        </Box>
    );
};

export default InventarioEnlaces; 