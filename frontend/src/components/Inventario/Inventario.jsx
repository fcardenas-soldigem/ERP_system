import React, { useState, useMemo, useEffect } from 'react';
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
    Menu,
    MenuButton,
    MenuList,
    MenuItem,
    Spinner,
    useToast,
    Badge,
    HStack,
    Stat,
    StatLabel,
    StatNumber,
    SimpleGrid,
    Select,
    useDisclosure,
    Divider
} from '@chakra-ui/react';
import { AddIcon, EditIcon, DeleteIcon, AttachmentIcon, DownloadIcon } from '@chakra-ui/icons';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { inventarioService } from '../../services/inventario.service';
import CategoriaForm from './CategoriaForm';
import AlmacenForm from './AlmacenForm';
import ImportarProductosModal from './ImportarProductosModal';
import ExportarKardexModal from './ExportarKardexModal';

const Inventario = () => {
    const navigate = useNavigate();
    const toast = useToast();
    const queryClient = useQueryClient();
    const [categoriaSeleccionada, setCategoriaSeleccionada] = useState("");
    const { 
        isOpen: isCategoriaOpen, 
        onOpen: onCategoriaOpen, 
        onClose: onCategoriaClose 
    } = useDisclosure();
    const { 
        isOpen: isAlmacenOpen, 
        onOpen: onAlmacenOpen, 
        onClose: onAlmacenClose 
    } = useDisclosure();
    const { 
        isOpen: isImportOpen, 
        onOpen: onImportOpen, 
        onClose: onImportClose 
    } = useDisclosure();
    const { 
        isOpen: isKardexOpen, 
        onOpen: onKardexOpen, 
        onClose: onKardexClose 
    } = useDisclosure();

    const { data: productos, isLoading: isLoadingProductos, refetch: refetchProductos } = useQuery({
        queryKey: ['productos'],
        queryFn: async () => {
            try {
                const response = await inventarioService.getProductos();
                console.log('Respuesta raw de productos en Inventario:', response);
                return response;
            } catch (error) {
                console.error('Error al obtener productos en Inventario:', error);
                throw error;
            }
        },
        refetchInterval: 5000, // Refrescar cada 5 segundos
        refetchOnMount: true,
        refetchOnWindowFocus: true,
        onError: (error) => {
            console.error('Error al cargar productos:', error);
            toast({
                title: 'Error',
                description: 'No se pudieron cargar los productos',
                status: 'error',
                duration: 3000,
            });
        }
    });

    // Efecto para refrescar los datos cuando se monta el componente
    useEffect(() => {
        console.log('Refrescando datos de productos...');
        refetchProductos();
    }, [refetchProductos]);

    const { data: categorias = [], isLoading: isLoadingCategorias } = useQuery({
        queryKey: ['categorias'],
        queryFn: async () => {
            try {
                const response = await inventarioService.getCategorias();
                console.log('Respuesta categorías:', response);
                // Asegurarnos de que siempre devolvemos un array
                if (Array.isArray(response)) {
                    return response;
                } else if (response && Array.isArray(response.results)) {
                    return response.results;
                } else if (response && Array.isArray(response.data)) {
                    return response.data;
                }
                console.warn('La respuesta de categorías no es un array:', response);
                return [];
            } catch (error) {
                console.error('Error al obtener categorías:', error);
                return [];
            }
        }
    });

    const { data: almacenes = [] } = useQuery({
        queryKey: ['almacenes'],
        queryFn: async () => {
            try {
                const response = await inventarioService.getAlmacenes();
                if (Array.isArray(response)) {
                    return response;
                } else if (response && Array.isArray(response.results)) {
                    return response.results;
                } else if (response && Array.isArray(response.data)) {
                    return response.data;
                }
                return [];
            } catch (error) {
                console.error('Error al obtener almacenes:', error);
                return [];
            }
        }
    });

    const { data: valorTotal = { valor_total: 0 } } = useQuery({
        queryKey: ['valorTotal'],
        queryFn: inventarioService.getValorTotalInventario,
        onError: (error) => {
            console.error('Error al obtener valor total:', error);
            toast({
                title: 'Error',
                description: 'No se pudo cargar el valor total del inventario',
                status: 'error',
                duration: 3000,
            });
        }
    });

    const eliminarProductoMutation = useMutation({
        mutationFn: inventarioService.eliminarProducto,
        onSuccess: () => {
            queryClient.invalidateQueries(['productos']);
            queryClient.invalidateQueries(['valorTotal']);
            toast({
                title: 'Producto eliminado',
                status: 'success',
                duration: 3000,
            });
        },
        onError: (error) => {
            toast({
                title: 'Error al eliminar el producto',
                description: error.message,
                status: 'error',
                duration: 3000,
            });
        }
    });

    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('es-PE', {
            style: 'currency',
            currency: 'PEN',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount || 0);
    };

    const productosFiltrados = useMemo(() => {
        if (!productos) {
            console.log('No hay productos disponibles');
            return [];
        }
        if (!categoriaSeleccionada) {
            console.log('Mostrando todos los productos:', productos);
            return productos;
        }
        const filtrados = productos.filter(producto => 
            producto.categoria?.toString() === categoriaSeleccionada
        );
        console.log('Productos filtrados por categoría:', filtrados);
        return filtrados;
    }, [productos, categoriaSeleccionada]);

    if (isLoadingProductos || isLoadingCategorias) {
        return (
            <Flex justify="center" align="center" h="200px">
                <Spinner />
            </Flex>
        );
    }

    const productosConStockBajo = productos?.filter(p => 
        Math.floor(p.stock_total) <= Math.floor(p.stock_minimo)
    ).length || 0;



    return (
        <Box p={4}>
            <Flex justify="space-between" align="center" mb={6}>
                <Box>
                    <Heading size="lg">Inventario</Heading>
                    <Text color="gray.600">
                        Gestiona tu inventario y mantén un control de tus productos
                    </Text>
                </Box>
            </Flex>

            <SimpleGrid columns={3} spacing={4} mb={6}>
                <Stat
                    px={{ base: 2, md: 4 }}
                    py={'5'}
                    shadow={'sm'}
                    border={'1px solid'}
                    borderColor={'gray.200'}
                    rounded={'lg'}
                >
                    <StatLabel fontWeight={'medium'}>Total Productos</StatLabel>
                    <StatNumber fontSize={'2xl'}>{productos?.length || 0}</StatNumber>
                </Stat>

                <Stat
                    px={{ base: 2, md: 4 }}
                    py={'5'}
                    shadow={'sm'}
                    border={'1px solid'}
                    borderColor={'gray.200'}
                    rounded={'lg'}
                >
                    <StatLabel fontWeight={'medium'}>Valor Total del Inventario</StatLabel>
                    <StatNumber fontSize={'2xl'}>
                        {formatCurrency(valorTotal?.valor_total)}
                        <Text fontSize="sm" color="gray.500">
                            Basado en precio de compra × stock
                        </Text>
                    </StatNumber>
                </Stat>

                <Stat
                    px={{ base: 2, md: 4 }}
                    py={'5'}
                    shadow={'sm'}
                    border={'1px solid'}
                    borderColor={'gray.200'}
                    rounded={'lg'}
                >
                    <StatLabel fontWeight={'medium'}>Productos Bajos en Stock</StatLabel>
                    <StatNumber fontSize={'2xl'} color={productosConStockBajo > 0 ? 'red.500' : 'green.500'}>
                        {productosConStockBajo}
                    </StatNumber>
                </Stat>
            </SimpleGrid>

            <Flex justify="space-between" align="center" mb={6}>
                <Select
                    placeholder="Filtrar por categoría"
                    maxW="300px"
                    value={categoriaSeleccionada}
                    onChange={(e) => setCategoriaSeleccionada(e.target.value)}
                >
                    <option value="">Todas las categorías</option>
                    {Array.isArray(categorias) && categorias.map(categoria => (
                        <option key={categoria.id} value={categoria.id}>
                            {categoria.nombre}
                        </option>
                    ))}
                </Select>

                <HStack spacing={4}>
                    <Button
                        colorScheme="teal"
                        leftIcon={<AddIcon />}
                        onClick={() => navigate('/inventario/nuevo')}
                    >
                        Nuevo Producto
                    </Button>
                    <Button
                        colorScheme="blue"
                        leftIcon={<AddIcon />}
                        onClick={onCategoriaOpen}
                    >
                        Nueva Categoría
                    </Button>
                    <Button
                        colorScheme="purple"
                        leftIcon={<AddIcon />}
                        onClick={onAlmacenOpen}
                    >
                        Nuevo Almacén
                    </Button>
                    <Divider orientation="vertical" />
                    <Button
                        colorScheme="green"
                        leftIcon={<AttachmentIcon />}
                        onClick={onImportOpen}
                    >
                        Importar Productos
                    </Button>
                    <Button
                        colorScheme="orange"
                        leftIcon={<DownloadIcon />}
                        onClick={onKardexOpen}
                    >
                        Descargar Kardex
                    </Button>
                </HStack>
            </Flex>

            <Table variant="simple">
                <Thead>
                    <Tr>
                        <Th>SKU</Th>
                        <Th>NOMBRE</Th>
                        <Th>DESCRIPCIÓN</Th>
                        <Th isNumeric>STOCK TOTAL</Th>
                        <Th isNumeric>STOCK MÍNIMO</Th>
                        <Th>ESTADO</Th>
                        <Th>CATEGORÍA</Th>
                        <Th>ACCIONES</Th>
                    </Tr>
                </Thead>
                <Tbody>
                    {productosFiltrados.map((producto) => {
                        const stockTotal = parseInt(producto.stock) || parseInt(producto.stock_total) || 0;
                        const stockMinimo = parseInt(producto.stock_minimo) || 0;
                        console.log(`Renderizando producto ${producto.nombre}:`, {
                            stock: producto.stock,
                            stock_total: producto.stock_total,
                            stock_procesado: stockTotal,
                            stock_minimo: stockMinimo
                        });

                        return (
                        <Tr key={producto.id}>
                            <Td>{producto.sku}</Td>
                            <Td>{producto.nombre}</Td>
                            <Td>{producto.descripcion}</Td>
                                <Td isNumeric>{Math.floor(stockTotal)}</Td>
                                <Td isNumeric>{Math.floor(stockMinimo)}</Td>
                            <Td>
                                <Badge 
                                    colorScheme={
                                            stockTotal <= 0 ? 'red' :
                                            stockTotal <= stockMinimo ? 'yellow' :
                                        'green'
                                    }
                                >
                                        {stockTotal <= 0 ? 'Sin stock' :
                                         stockTotal <= stockMinimo ? 'Stock bajo' :
                                     'Disponible'}
                                </Badge>
                            </Td>
                                <Td>
                                    {Array.isArray(categorias) && 
                                     categorias.find(c => c.id === parseInt(producto.categoria))?.nombre || 'Sin categoría'}
                                </Td>
                            <Td>
                                <HStack spacing={2}>
                                    <IconButton
                                        icon={<EditIcon />}
                                        aria-label="Editar"
                                        size="sm"
                                        onClick={() => navigate(`/inventario/${producto.id}/editar`)}
                                    />
                                    <IconButton
                                        icon={<DeleteIcon />}
                                        aria-label="Eliminar"
                                        size="sm"
                                        colorScheme="red"
                                            onClick={() => {
                                                eliminarProductoMutation.mutate(producto.id);
                                                refetchProductos(); // Refrescar después de eliminar
                                            }}
                                    />
                                </HStack>
                            </Td>
                        </Tr>
                        );
                    })}
                </Tbody>
            </Table>

            <CategoriaForm 
                isOpen={isCategoriaOpen} 
                onClose={() => {
                    onCategoriaClose();
                    refetchProductos(); // Refrescar después de crear/editar categoría
                }} 
            />
            <AlmacenForm 
                isOpen={isAlmacenOpen} 
                onClose={() => {
                    onAlmacenClose();
                    refetchProductos(); // Refrescar después de crear/editar almacén
                }} 
            />
            <ImportarProductosModal
                isOpen={isImportOpen}
                onClose={() => {
                    onImportClose();
                    refetchProductos();
                }}
            />
            <ExportarKardexModal
                isOpen={isKardexOpen}
                onClose={onKardexClose}
                productos={productos || []}
                almacenes={almacenes || []}
            />
        </Box>
    );
};

export default Inventario;



