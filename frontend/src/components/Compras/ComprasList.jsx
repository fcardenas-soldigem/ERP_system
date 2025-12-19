import React, { useState } from 'react';
import {
    Box,
    Heading,
    Text,
    Button,
    Flex,
    Table,
    Thead,
    Tbody,
    Tr,
    Th,
    Td,
    Menu,
    MenuButton,
    MenuList,
    MenuItem,
    IconButton,
    useToast,
    Badge,
    HStack,
    useDisclosure,
    Spinner,
} from '@chakra-ui/react';
import { ChevronDownIcon, EditIcon, DeleteIcon, DownloadIcon, AddIcon, ViewIcon } from '@chakra-ui/icons';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { comprasService } from '../../services/compras.service';
import ImportarCompras from './ImportarCompras';
import { useNavigate } from 'react-router-dom';
import { ESTADOS_DISPLAY, METODOS_PAGO_DISPLAY } from './constants';

const ComprasList = () => {
    const toast = useToast();
    const queryClient = useQueryClient();
    const { isOpen, onOpen, onClose } = useDisclosure();
    const navigate = useNavigate();
    const [page, setPage] = useState(1);
    const pageSize = 10;

    // Consulta para obtener las compras
    const { data: comprasData, isLoading, error, isError } = useQuery({
        queryKey: ['compras', page, pageSize],
        queryFn: () => comprasService.getCompras(page, pageSize),
        retry: (failureCount, error) => {
            // No reintentar si es un problema de empresa_id o autenticación
            if (error.message.includes('empresa') || error.message.includes('Sesión expirada')) {
                return false;
            }
            return failureCount < 2;
        },
        onError: (error) => {
            console.error('Error al cargar compras:', error);
            
            let title = 'Error al cargar las compras';
            let description = error.message || 'Hubo un error al cargar las compras';
            
            // Personalizar el mensaje según el tipo de error
            if (error.message.includes('empresa')) {
                title = 'Problema con la configuración de empresa';
                description = error.message;
            } else if (error.message.includes('Sesión expirada')) {
                title = 'Sesión expirada';
                description = 'Su sesión ha expirado. Por favor, inicie sesión nuevamente.';
            }
            
            toast({
                title: title,
                description: description,
                status: 'error',
                duration: 7000,
                isClosable: true,
            });
        }
    });

    // Función para formatear moneda según la moneda seleccionada
    const formatCurrency = (amount, moneda = 'PEN') => {
        const formatters = {
            'PEN': new Intl.NumberFormat('es-PE', {
                style: 'currency',
                currency: 'PEN'
            }),
            'USD': new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD'
            })
        };
        
        return formatters[moneda] ? formatters[moneda].format(amount) : `${moneda} ${amount.toFixed(2)}`;
    };

    const formatDate = (dateString) => {
        if (!dateString) return '';
        try {
            return format(new Date(dateString), 'dd/MM/yyyy', { locale: es });
        } catch (error) {
            console.error('Error al formatear fecha:', error);
            return dateString;
        }
    };

    const getEstadoBadge = (estado) => {
        const estadoLower = estado?.toLowerCase() || '';
        return (
            <Badge colorScheme={getEstadoColor(estadoLower)}>
                {ESTADOS_DISPLAY[estadoLower] || estado}
            </Badge>
        );
    };

    const getEstadoColor = (estado) => {
        switch (estado) {
            case 'borrador': return 'gray';
            case 'pendiente': return 'yellow';
            case 'pagada': return 'green';
            case 'anulada': return 'red';
            default: return 'gray';
        }
    };

    const getMetodoPagoBadge = (metodoPago) => {
        return (
            <Badge colorScheme={getMetodoPagoColor(metodoPago)}>
                {METODOS_PAGO_DISPLAY[metodoPago] || metodoPago}
            </Badge>
        );
    };

    const getMetodoPagoColor = (metodoPago) => {
        switch (metodoPago) {
            case 'efectivo': return 'green';
            case 'transferencia': return 'blue';
            case 'cheque': return 'purple';
            case 'tarjeta': return 'orange';
            case 'credito_30': return 'pink';
            case 'credito_60': return 'red';
            default: return 'gray';
        }
    };

    const getTipoCompraBadge = (tipoCompra) => {
        const tiposDisplay = {
            'contado': 'Contado',
            'credito_30': 'Crédito 30 días',
            'credito_60': 'Crédito 60 días'
        };
        
        return (
            <Badge colorScheme={getTipoCompraColor(tipoCompra)}>
                {tiposDisplay[tipoCompra] || tipoCompra}
            </Badge>
        );
    };

    const getTipoCompraColor = (tipoCompra) => {
        switch (tipoCompra) {
            case 'contado': return 'green';
            case 'credito_30': return 'orange';
            case 'credito_60': return 'red';
            default: return 'gray';
        }
    };

    const handleEliminarCompra = async (id) => {
        try {
            await comprasService.cambiarEstado(id, 'anulada');
            queryClient.invalidateQueries(['compras']);
            toast({
                title: 'Compra anulada',
                description: 'La compra ha sido anulada exitosamente',
                status: 'success',
                duration: 3000,
            });
        } catch (error) {
            toast({
                title: 'Error al anular la compra',
                description: error.message,
                status: 'error',
                duration: 5000,
            });
        }
    };

    return (
        <Box p={4}>
            <Flex justify="space-between" align="center" mb={6}>
                <Box>
                    <Heading size="lg">Facturas de compra</Heading>
                    <Text color="gray.600">
                        Registra las compras que realizas a tus proveedores y actualiza tu inventario de forma automática
                    </Text>
                </Box>
                <HStack spacing={4}>
                    <Button
                        leftIcon={<AddIcon />}
                        colorScheme="blue"
                        onClick={() => navigate('/app/compras/nueva')}
                    >
                        Nueva Compra
                    </Button>
                    <Button
                        leftIcon={<DownloadIcon />}
                        colorScheme="green"
                        onClick={() => comprasService.exportarExcel()}
                    >
                        Exportar Excel
                    </Button>
                    <Button 
                        colorScheme="orange" 
                        onClick={onOpen}
                    >
                        Importar Excel
                    </Button>
                </HStack>
            </Flex>

            {isLoading ? (
                <Flex justify="center" align="center" h="200px">
                    <Spinner size="xl" />
                </Flex>
            ) : isError ? (
                <Box p={6} borderWidth={1} borderRadius="md" borderColor="red.200" bg="red.50">
                    <Heading size="md" color="red.600" mb={3}>
                        Error al cargar las compras
                    </Heading>
                    <Text color="red.700" mb={3}>
                        {error?.message || 'Error desconocido'}
                    </Text>
                    <Text fontSize="sm" color="gray.600" mb={4}>
                        Si el problema persiste, intente lo siguiente:
                    </Text>
                    <Box as="ul" pl={4} fontSize="sm" color="gray.600">
                        <li>• Cerrar sesión e iniciar sesión nuevamente</li>
                        <li>• Verificar que su usuario tenga una empresa asignada</li>
                        <li>• Contactar al administrador del sistema</li>
                    </Box>
                    <Button 
                        mt={4} 
                        colorScheme="blue" 
                        size="sm"
                        onClick={() => window.location.reload()}
                    >
                        Recargar página
                    </Button>
                </Box>
            ) : !comprasData?.results?.length ? (
                <Box p={4} textAlign="center">
                    <Text>No hay compras registradas</Text>
                </Box>
            ) : (
                <>
                    <Table variant="simple">
                        <Thead>
                            <Tr>
                                <Th>Número</Th>
                                <Th>Proveedor</Th>
                                <Th>Fecha</Th>
                                <Th>Tipo Compra</Th>
                                <Th>Estado</Th>
                                <Th>Método de Pago</Th>
                                <Th>Total</Th>
                                <Th>Acciones</Th>
                            </Tr>
                        </Thead>
                        <Tbody>
                            {comprasData.results.map((compra) => (
                                <Tr key={compra.id}>
                                    <Td>{compra.numero}</Td>
                                    <Td>{compra.proveedor_nombre}</Td>
                                    <Td>{formatDate(compra.fecha_emision)}</Td>
                                    <Td>{getTipoCompraBadge(compra.tipo_compra)}</Td>
                                    <Td>{getEstadoBadge(compra.estado)}</Td>
                                    <Td>{getMetodoPagoBadge(compra.metodo_pago)}</Td>
                                    <Td>{formatCurrency(compra.total, compra.moneda)}</Td>
                                    <Td>
                                        <Menu>
                                            <MenuButton
                                                as={IconButton}
                                                icon={<ChevronDownIcon />}
                                                variant="outline"
                                                size="sm"
                                            />
                                            <MenuList>
                                                <MenuItem 
                                                    icon={<ViewIcon />} 
                                                    onClick={() => navigate(`/app/compras/${compra.id}`)}
                                                >
                                                    Ver Detalles
                                                </MenuItem>
                                                <MenuItem 
                                                    icon={<EditIcon />} 
                                                    onClick={() => navigate(`/app/compras/${compra.id}/editar`)}
                                                >
                                                    Editar
                                                </MenuItem>
                                                {compra.estado !== 'anulada' && (
                                                    <MenuItem 
                                                        icon={<DeleteIcon />} 
                                                        onClick={() => handleEliminarCompra(compra.id)}
                                                    >
                                                        Anular
                                                    </MenuItem>
                                                )}
                                            </MenuList>
                                        </Menu>
                                    </Td>
                                </Tr>
                            ))}
                        </Tbody>
                    </Table>

                    <Flex justify="space-between" align="center" mt={4}>
                        <Text>
                            Mostrando {comprasData.results.length} de {comprasData.count || 0} compras
                        </Text>
                        <HStack>
                            <Button
                                onClick={() => setPage(page > 1 ? page - 1 : 1)}
                                isDisabled={!comprasData.previous}
                            >
                                Anterior
                            </Button>
                            <Button
                                onClick={() => setPage(page + 1)}
                                isDisabled={!comprasData.next}
                            >
                                Siguiente
                            </Button>
                        </HStack>
                    </Flex>
                </>
            )}

            <ImportarCompras isOpen={isOpen} onClose={onClose} />
        </Box>
    );
};

export default ComprasList;

