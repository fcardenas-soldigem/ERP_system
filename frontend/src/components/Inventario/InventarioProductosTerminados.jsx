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
    IconButton,
    Spinner,
    useToast,
    Badge,
    HStack,
    Stat,
    StatLabel,
    StatNumber,
    StatHelpText,
    SimpleGrid,
    Select,
    useDisclosure,
    Modal,
    ModalOverlay,
    ModalContent,
    ModalHeader,
    ModalBody,
    ModalFooter,
    ModalCloseButton,
    FormControl,
    FormLabel,
    NumberInput,
    NumberInputField,
    Textarea,
    Alert,
    AlertIcon,
    AlertTitle,
    AlertDescription,
    Progress,
    Tooltip,
    InputGroup,
    InputLeftAddon,
    VStack
} from '@chakra-ui/react';
import { AddIcon, EditIcon, WarningIcon, RepeatIcon, ViewIcon } from '@chakra-ui/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { inventarioService } from '../../services/inventario.service';

const InventarioProductosTerminados = () => {
    const toast = useToast();
    const queryClient = useQueryClient();
    const [almacenFiltro, setAlmacenFiltro] = useState("");
    const [itemSeleccionado, setItemSeleccionado] = useState(null);
    
    const { isOpen: isAjusteOpen, onOpen: onAjusteOpen, onClose: onAjusteClose } = useDisclosure();
    const { isOpen: isDetalleOpen, onOpen: onDetalleOpen, onClose: onDetalleClose } = useDisclosure();

    // Queries
    const { data: inventario = [], isLoading, refetch } = useQuery({
        queryKey: ['inventario-productos-terminados'],
        queryFn: inventarioService.getProductosTerminados,
        onError: (error) => {
            toast({
                title: 'Error',
                description: 'No se pudieron cargar los datos de inventario',
                status: 'error',
                duration: 3000,
            });
        }
    });

    const { data: almacenes = [] } = useQuery({
        queryKey: ['almacenes'],
        queryFn: inventarioService.getAlmacenes
    });

    const { data: alertas = [] } = useQuery({
        queryKey: ['alertas-productos-terminados'],
        queryFn: inventarioService.getProductosTerminadosAlertas
    });

    const { data: valorTotal = { valor_total: 0 } } = useQuery({
        queryKey: ['valor-total-productos-terminados'],
        queryFn: inventarioService.getValorTotalProductosTerminados
    });

    // Mutations
    const ajustarMutation = useMutation({
        mutationFn: inventarioService.ajustarInventarioProductoTerminado,
        onSuccess: () => {
            queryClient.invalidateQueries(['inventario-productos-terminados']);
            queryClient.invalidateQueries(['valor-total-productos-terminados']);
            queryClient.invalidateQueries(['alertas-productos-terminados']);
            toast({
                title: 'Ajuste registrado',
                status: 'success',
                duration: 3000,
            });
            onAjusteClose();
        },
        onError: (error) => {
            toast({
                title: 'Error al ajustar inventario',
                description: error.response?.data?.error || error.message,
                status: 'error',
                duration: 5000,
            });
        }
    });

    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('es-PE', {
            style: 'currency',
            currency: 'PEN',
            minimumFractionDigits: 2
        }).format(amount || 0);
    };

    const formatNumber = (num) => {
        return new Intl.NumberFormat('es-PE', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 4
        }).format(num || 0);
    };

    const inventarioFiltrado = almacenFiltro 
        ? inventario.filter(item => item.almacen?.toString() === almacenFiltro)
        : inventario;

    const itemsStockBajo = inventario.filter(item => 
        parseFloat(item.cantidad_disponible) <= parseFloat(item.stock_minimo) && 
        parseFloat(item.stock_minimo) > 0
    ).length;

    // Calcular valor total de venta potencial
    const valorVentaPotencial = inventario.reduce((total, item) => {
        return total + (parseFloat(item.cantidad_disponible) * parseFloat(item.precio_venta_sugerido || 0));
    }, 0);

    const handleAjuste = (item) => {
        setItemSeleccionado({
            ...item,
            cantidad_ajuste: 0,
            motivo: ''
        });
        onAjusteOpen();
    };

    const handleVerDetalle = (item) => {
        setItemSeleccionado(item);
        onDetalleOpen();
    };

    const submitAjuste = () => {
        if (!itemSeleccionado) return;
        
        ajustarMutation.mutate({
            producto_id: itemSeleccionado.producto,
            almacen_id: itemSeleccionado.almacen,
            cantidad: parseFloat(itemSeleccionado.cantidad_ajuste),
            motivo: itemSeleccionado.motivo
        });
    };

    const getEstadoStock = (item) => {
        const disponible = parseFloat(item.cantidad_disponible);
        const minimo = parseFloat(item.stock_minimo);
        const maximo = parseFloat(item.stock_maximo);
        
        if (disponible <= 0) return { color: 'red', label: 'Sin Stock', progress: 0 };
        if (disponible <= minimo) return { color: 'orange', label: 'Stock Bajo', progress: 25 };
        if (maximo > 0 && disponible >= maximo) return { color: 'blue', label: 'Stock Máximo', progress: 100 };
        if (maximo > 0) {
            const progress = Math.min((disponible / maximo) * 100, 100);
            return { color: 'green', label: 'Disponible', progress };
        }
        return { color: 'green', label: 'Disponible', progress: 50 };
    };

    const calcularMargen = (item) => {
        const costo = parseFloat(item.costo_produccion_unitario) || 0;
        const venta = parseFloat(item.precio_venta_sugerido) || 0;
        if (costo === 0 || venta === 0) return null;
        return ((venta - costo) / venta * 100).toFixed(1);
    };

    if (isLoading) {
        return (
            <Flex justify="center" align="center" h="200px">
                <Spinner size="lg" />
            </Flex>
        );
    }

    return (
        <Box p={4}>
            <Flex justify="space-between" align="center" mb={6}>
                <Box>
                    <Heading size="lg">Inventario de Productos Terminados</Heading>
                    <Text color="gray.600">
                        Gestiona el inventario de productos terminados listos para venta
                    </Text>
                </Box>
                <HStack>
                    <Button
                        leftIcon={<RepeatIcon />}
                        onClick={() => refetch()}
                        variant="outline"
                    >
                        Actualizar
                    </Button>
                </HStack>
            </Flex>

            {/* Alertas */}
            {alertas.length > 0 && (
                <Alert status="warning" mb={4} borderRadius="md">
                    <AlertIcon />
                    <Box>
                        <AlertTitle>Alertas de Inventario</AlertTitle>
                        <AlertDescription>
                            Hay {alertas.length} alerta(s) activa(s). {itemsStockBajo} productos con stock bajo.
                        </AlertDescription>
                    </Box>
                </Alert>
            )}

            {/* Estadísticas */}
            <SimpleGrid columns={{ base: 1, md: 4 }} spacing={4} mb={6}>
                <Stat
                    px={4}
                    py={5}
                    shadow="sm"
                    border="1px solid"
                    borderColor="gray.200"
                    rounded="lg"
                >
                    <StatLabel fontWeight="medium">Total Items</StatLabel>
                    <StatNumber fontSize="2xl">{inventario.length}</StatNumber>
                    <StatHelpText>Productos terminados</StatHelpText>
                </Stat>

                <Stat
                    px={4}
                    py={5}
                    shadow="sm"
                    border="1px solid"
                    borderColor="gray.200"
                    rounded="lg"
                >
                    <StatLabel fontWeight="medium">Valor al Costo</StatLabel>
                    <StatNumber fontSize="2xl" color="blue.600">
                        {formatCurrency(valorTotal?.valor_total)}
                    </StatNumber>
                    <StatHelpText>Cantidad × Costo producción</StatHelpText>
                </Stat>

                <Stat
                    px={4}
                    py={5}
                    shadow="sm"
                    border="1px solid"
                    borderColor="gray.200"
                    rounded="lg"
                >
                    <StatLabel fontWeight="medium">Valor Venta Potencial</StatLabel>
                    <StatNumber fontSize="2xl" color="green.600">
                        {formatCurrency(valorVentaPotencial)}
                    </StatNumber>
                    <StatHelpText>Cantidad × Precio venta</StatHelpText>
                </Stat>

                <Stat
                    px={4}
                    py={5}
                    shadow="sm"
                    border="1px solid"
                    borderColor={itemsStockBajo > 0 ? 'orange.300' : 'gray.200'}
                    rounded="lg"
                    bg={itemsStockBajo > 0 ? 'orange.50' : 'white'}
                >
                    <StatLabel fontWeight="medium">Stock Bajo</StatLabel>
                    <StatNumber fontSize="2xl" color={itemsStockBajo > 0 ? 'orange.500' : 'green.500'}>
                        {itemsStockBajo}
                    </StatNumber>
                    <StatHelpText>Productos bajo mínimo</StatHelpText>
                </Stat>
            </SimpleGrid>

            {/* Filtros */}
            <Flex justify="space-between" align="center" mb={4}>
                <Select
                    placeholder="Filtrar por almacén"
                    maxW="300px"
                    value={almacenFiltro}
                    onChange={(e) => setAlmacenFiltro(e.target.value)}
                >
                    <option value="">Todos los almacenes</option>
                    {almacenes.map(almacen => (
                        <option key={almacen.id} value={almacen.id}>
                            {almacen.nombre}
                        </option>
                    ))}
                </Select>
                <Text color="gray.500" fontSize="sm">
                    Mostrando {inventarioFiltrado.length} de {inventario.length} items
                </Text>
            </Flex>

            {/* Tabla */}
            <Box overflowX="auto">
                <Table variant="simple" size="sm">
                    <Thead bg="gray.50">
                        <Tr>
                            <Th>Producto</Th>
                            <Th>Almacén</Th>
                            <Th>Lote Prod.</Th>
                            <Th isNumeric>Disponible</Th>
                            <Th isNumeric>Reservado</Th>
                            <Th isNumeric>Costo Prod.</Th>
                            <Th isNumeric>Precio Venta</Th>
                            <Th isNumeric>Margen</Th>
                            <Th>Estado</Th>
                            <Th>Acciones</Th>
                        </Tr>
                    </Thead>
                    <Tbody>
                        {inventarioFiltrado.map((item) => {
                            const estado = getEstadoStock(item);
                            const margen = calcularMargen(item);
                            
                            return (
                                <Tr key={item.id} _hover={{ bg: 'gray.50' }}>
                                    <Td>
                                        <VStack align="start" spacing={0}>
                                            <Text fontWeight="medium">{item.producto_nombre}</Text>
                                            <Text fontSize="xs" color="gray.500">{item.producto_sku}</Text>
                                        </VStack>
                                    </Td>
                                    <Td>{item.almacen_nombre}</Td>
                                    <Td>{item.lote_produccion || '-'}</Td>
                                    <Td isNumeric fontWeight="bold">{formatNumber(item.cantidad_disponible)}</Td>
                                    <Td isNumeric color="orange.500">{formatNumber(item.cantidad_reservada)}</Td>
                                    <Td isNumeric>{formatCurrency(item.costo_produccion_unitario)}</Td>
                                    <Td isNumeric color="green.600" fontWeight="medium">
                                        {formatCurrency(item.precio_venta_sugerido)}
                                    </Td>
                                    <Td isNumeric>
                                        {margen ? (
                                            <Badge colorScheme={parseFloat(margen) >= 20 ? 'green' : 'orange'}>
                                                {margen}%
                                            </Badge>
                                        ) : '-'}
                                    </Td>
                                    <Td>
                                        <Tooltip label={`Mín: ${item.stock_minimo} / Máx: ${item.stock_maximo || 'N/A'}`}>
                                            <Box>
                                                <Badge colorScheme={estado.color} mb={1}>
                                                    {estado.label}
                                                </Badge>
                                                <Progress 
                                                    value={estado.progress} 
                                                    size="xs" 
                                                    colorScheme={estado.color}
                                                    borderRadius="full"
                                                />
                                            </Box>
                                        </Tooltip>
                                    </Td>
                                    <Td>
                                        <HStack spacing={1}>
                                            <Tooltip label="Ver detalles">
                                                <IconButton
                                                    icon={<ViewIcon />}
                                                    aria-label="Ver"
                                                    size="xs"
                                                    variant="ghost"
                                                    onClick={() => handleVerDetalle(item)}
                                                />
                                            </Tooltip>
                                            <Tooltip label="Ajustar inventario">
                                                <IconButton
                                                    icon={<AddIcon />}
                                                    aria-label="Ajustar"
                                                    size="xs"
                                                    variant="ghost"
                                                    colorScheme="blue"
                                                    onClick={() => handleAjuste(item)}
                                                />
                                            </Tooltip>
                                        </HStack>
                                    </Td>
                                </Tr>
                            );
                        })}
                    </Tbody>
                </Table>
            </Box>

            {inventarioFiltrado.length === 0 && (
                <Box textAlign="center" py={10}>
                    <Text color="gray.500">No hay datos de inventario disponibles</Text>
                </Box>
            )}

            {/* Modal de Ajuste */}
            <Modal isOpen={isAjusteOpen} onClose={onAjusteClose}>
                <ModalOverlay />
                <ModalContent>
                    <ModalHeader>Ajustar Inventario</ModalHeader>
                    <ModalCloseButton />
                    <ModalBody>
                        {itemSeleccionado && (
                            <VStack spacing={4}>
                                <Box w="full" p={3} bg="gray.50" borderRadius="md">
                                    <Text fontWeight="bold">{itemSeleccionado.producto_nombre}</Text>
                                    <Text fontSize="sm" color="gray.600">
                                        Stock actual: {formatNumber(itemSeleccionado.cantidad_disponible)}
                                    </Text>
                                </Box>
                                
                                <FormControl isRequired>
                                    <FormLabel>Cantidad de Ajuste</FormLabel>
                                    <InputGroup>
                                        <InputLeftAddon>+/-</InputLeftAddon>
                                        <NumberInput 
                                            value={itemSeleccionado.cantidad_ajuste}
                                            onChange={(valueString) => setItemSeleccionado({
                                                ...itemSeleccionado,
                                                cantidad_ajuste: valueString
                                            })}
                                            w="full"
                                        >
                                            <NumberInputField />
                                        </NumberInput>
                                    </InputGroup>
                                    <Text fontSize="xs" color="gray.500" mt={1}>
                                        Positivo para agregar, negativo para reducir
                                    </Text>
                                </FormControl>

                                <FormControl isRequired>
                                    <FormLabel>Motivo del Ajuste</FormLabel>
                                    <Textarea
                                        value={itemSeleccionado.motivo}
                                        onChange={(e) => setItemSeleccionado({
                                            ...itemSeleccionado,
                                            motivo: e.target.value
                                        })}
                                        placeholder="Describe el motivo del ajuste..."
                                    />
                                </FormControl>
                            </VStack>
                        )}
                    </ModalBody>
                    <ModalFooter>
                        <Button variant="ghost" mr={3} onClick={onAjusteClose}>
                            Cancelar
                        </Button>
                        <Button 
                            colorScheme="blue" 
                            onClick={submitAjuste}
                            isLoading={ajustarMutation.isLoading}
                            isDisabled={!itemSeleccionado?.cantidad_ajuste || !itemSeleccionado?.motivo}
                        >
                            Registrar Ajuste
                        </Button>
                    </ModalFooter>
                </ModalContent>
            </Modal>

            {/* Modal de Detalle */}
            <Modal isOpen={isDetalleOpen} onClose={onDetalleClose} size="lg">
                <ModalOverlay />
                <ModalContent>
                    <ModalHeader>Detalle de Producto Terminado</ModalHeader>
                    <ModalCloseButton />
                    <ModalBody>
                        {itemSeleccionado && (
                            <SimpleGrid columns={2} spacing={4}>
                                <Box>
                                    <Text fontSize="sm" color="gray.500">Producto</Text>
                                    <Text fontWeight="bold">{itemSeleccionado.producto_nombre}</Text>
                                </Box>
                                <Box>
                                    <Text fontSize="sm" color="gray.500">SKU</Text>
                                    <Text>{itemSeleccionado.producto_sku}</Text>
                                </Box>
                                <Box>
                                    <Text fontSize="sm" color="gray.500">Almacén</Text>
                                    <Text>{itemSeleccionado.almacen_nombre}</Text>
                                </Box>
                                <Box>
                                    <Text fontSize="sm" color="gray.500">Ubicación</Text>
                                    <Text>{itemSeleccionado.ubicacion_almacen || '-'}</Text>
                                </Box>
                                <Box>
                                    <Text fontSize="sm" color="gray.500">Cantidad Disponible</Text>
                                    <Text fontWeight="bold" fontSize="lg" color="green.500">
                                        {formatNumber(itemSeleccionado.cantidad_disponible)}
                                    </Text>
                                </Box>
                                <Box>
                                    <Text fontSize="sm" color="gray.500">Cantidad Reservada</Text>
                                    <Text fontWeight="bold" fontSize="lg" color="orange.500">
                                        {formatNumber(itemSeleccionado.cantidad_reservada)}
                                    </Text>
                                </Box>
                                <Box>
                                    <Text fontSize="sm" color="gray.500">Costo de Producción</Text>
                                    <Text fontWeight="bold">{formatCurrency(itemSeleccionado.costo_produccion_unitario)}</Text>
                                </Box>
                                <Box>
                                    <Text fontSize="sm" color="gray.500">Precio de Venta Sugerido</Text>
                                    <Text fontWeight="bold" color="green.500">
                                        {formatCurrency(itemSeleccionado.precio_venta_sugerido)}
                                    </Text>
                                </Box>
                                <Box>
                                    <Text fontSize="sm" color="gray.500">Valor al Costo</Text>
                                    <Text fontWeight="bold" color="blue.500">
                                        {formatCurrency(itemSeleccionado.valor_inventario)}
                                    </Text>
                                </Box>
                                <Box>
                                    <Text fontSize="sm" color="gray.500">Valor Venta Potencial</Text>
                                    <Text fontWeight="bold" color="green.600">
                                        {formatCurrency(itemSeleccionado.valor_venta_potencial)}
                                    </Text>
                                </Box>
                                <Box>
                                    <Text fontSize="sm" color="gray.500">Stock Mínimo</Text>
                                    <Text>{formatNumber(itemSeleccionado.stock_minimo)}</Text>
                                </Box>
                                <Box>
                                    <Text fontSize="sm" color="gray.500">Stock Máximo</Text>
                                    <Text>{itemSeleccionado.stock_maximo ? formatNumber(itemSeleccionado.stock_maximo) : '-'}</Text>
                                </Box>
                                <Box>
                                    <Text fontSize="sm" color="gray.500">Lote Producción</Text>
                                    <Text>{itemSeleccionado.lote_produccion || '-'}</Text>
                                </Box>
                                <Box>
                                    <Text fontSize="sm" color="gray.500">Fecha Producción</Text>
                                    <Text>{itemSeleccionado.fecha_produccion || '-'}</Text>
                                </Box>
                                <Box>
                                    <Text fontSize="sm" color="gray.500">Orden de Producción</Text>
                                    <Text>{itemSeleccionado.orden_produccion_id ? `#${itemSeleccionado.orden_produccion_id}` : '-'}</Text>
                                </Box>
                                <Box>
                                    <Text fontSize="sm" color="gray.500">Margen de Utilidad</Text>
                                    <Badge colorScheme={parseFloat(calcularMargen(itemSeleccionado) || 0) >= 20 ? 'green' : 'orange'}>
                                        {calcularMargen(itemSeleccionado) || '0'}%
                                    </Badge>
                                </Box>
                                <Box gridColumn="span 2">
                                    <Text fontSize="sm" color="gray.500">Última Actualización</Text>
                                    <Text>{new Date(itemSeleccionado.ultima_actualizacion).toLocaleString()}</Text>
                                </Box>
                            </SimpleGrid>
                        )}
                    </ModalBody>
                    <ModalFooter>
                        <Button onClick={onDetalleClose}>Cerrar</Button>
                    </ModalFooter>
                </ModalContent>
            </Modal>
        </Box>
    );
};

export default InventarioProductosTerminados;
