import React from 'react';
import { 
    Box, 
    Heading, 
    Text, 
    Flex, 
    useToast,
    Badge,
    HStack,
    Stat,
    StatLabel,
    StatNumber,
    StatHelpText,
    StatArrow,
    SimpleGrid,
    Card,
    CardHeader,
    CardBody,
    Button,
    Alert,
    AlertIcon,
    AlertTitle,
    AlertDescription,
    Table,
    Thead,
    Tbody,
    Tr,
    Th,
    Td,
    Divider,
    Icon,
    VStack,
    Progress,
    useColorModeValue
} from '@chakra-ui/react';
import { keyframes } from '@emotion/react';
import { WarningIcon, RepeatIcon, ChevronRightIcon } from '@chakra-ui/icons';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { inventarioService } from '../../services/inventario.service';
import { FiPackage, FiBox, FiAlertTriangle, FiTrendingUp, FiDollarSign, FiShoppingCart } from 'react-icons/fi';
import { StatsCard, StatsGrid, AlertCard } from '../common/StatsCard';
import { DashboardSkeleton, FadeInBox } from '../common/SkeletonLoaders';

// Animación de pulso suave
const pulseAnimation = keyframes`
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
`;

const ResumenInventariosSeparados = () => {
    const toast = useToast();
    const navigate = useNavigate();
    const cardBg = useColorModeValue('white', 'gray.800');
    const borderColor = useColorModeValue('gray.200', 'gray.600');

    // Query para resumen general - con actualización automática
    const { data: resumen, isLoading, refetch, isFetching } = useQuery({
        queryKey: ['resumen-inventarios-separados'],
        queryFn: inventarioService.getResumenInventariosSeparados,
        refetchInterval: 30000, // Actualizar cada 30 segundos
        refetchOnWindowFocus: true, // Actualizar cuando el usuario vuelve a la pestaña
        staleTime: 10000, // Considerar datos frescos por 10 segundos
        onError: (error) => {
            toast({
                title: 'Error',
                description: 'No se pudo cargar el resumen de inventarios',
                status: 'error',
                duration: 3000,
            });
        }
    });

    // Queries individuales para alertas - con actualización automática
    const { data: alertasMP = [] } = useQuery({
        queryKey: ['alertas-materias-primas'],
        queryFn: inventarioService.getMateriasPrimasAlertas,
        refetchInterval: 30000,
        refetchOnWindowFocus: true,
        staleTime: 10000,
    });

    const { data: alertasPT = [] } = useQuery({
        queryKey: ['alertas-productos-terminados'],
        queryFn: inventarioService.getProductosTerminadosAlertas,
        refetchInterval: 30000,
        refetchOnWindowFocus: true,
        staleTime: 10000,
    });

    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('es-PE', {
            style: 'currency',
            currency: 'PEN',
            minimumFractionDigits: 2
        }).format(amount || 0);
    };

    if (isLoading) {
        return (
            <Box p={4}>
                <DashboardSkeleton />
            </Box>
        );
    }

    // Mapear datos del backend a la estructura esperada por el componente
    const mp = {
        total_items: resumen?.total_materias_primas || 0,
        valor_total: resumen?.valor_total_materias_primas || 0,
        stock_bajo: resumen?.materias_primas_stock_bajo || 0,
        por_vencer: resumen?.materias_primas_por_vencer || 0,
    };
    
    const pt = {
        total_items: resumen?.total_productos_terminados || 0,
        valor_costo: resumen?.valor_total_productos_terminados || 0,
        stock_bajo: resumen?.productos_terminados_stock_bajo || 0,
        valor_venta: resumen?.valor_venta_potencial || 0,
    };
    
    const totalAlertas = (alertasMP?.length || 0) + (alertasPT?.length || 0);

    return (
        <Box p={4}>
            {/* Header con animación */}
            <FadeInBox delay={0}>
                <Flex justify="space-between" align="center" mb={6}>
                    <Box>
                        <Heading size="lg" bgGradient="linear(to-r, blue.600, purple.600)" bgClip="text">
                            Resumen de Inventarios
                        </Heading>
                        <Text color="gray.600" mt={1}>
                            Vista consolidada de materias primas y productos terminados
                        </Text>
                    </Box>
                    <HStack spacing={3}>
                        <Button
                            leftIcon={<RepeatIcon />}
                            onClick={() => refetch()}
                            variant="outline"
                            colorScheme="blue"
                            size="md"
                            isLoading={isFetching}
                            loadingText="Actualizando"
                            _hover={{ transform: 'translateY(-2px)', boxShadow: 'md' }}
                            transition="all 0.2s"
                        >
                            Actualizar
                        </Button>
                    </HStack>
                </Flex>
            </FadeInBox>

            {/* Alertas Generales con animación de pulso */}
            {totalAlertas > 0 && (
                <FadeInBox delay={0.1}>
                    <Alert 
                        status="warning" 
                        mb={6} 
                        borderRadius="xl"
                        flexDirection={{ base: 'column', md: 'row' }}
                        alignItems="start"
                        boxShadow="md"
                        animation={`${pulseAnimation} 3s ease-in-out infinite`}
                    >
                        <AlertIcon boxSize={6} />
                        <Box flex="1">
                            <AlertTitle fontSize="md" fontWeight="bold">Se requiere atención</AlertTitle>
                            <AlertDescription fontSize="sm">
                                Hay <Text as="span" fontWeight="bold">{totalAlertas}</Text> alerta(s) activa(s) en tu inventario. 
                                Revisa los productos con stock bajo o próximos a vencer.
                            </AlertDescription>
                        </Box>
                        <Button 
                            size="sm" 
                            colorScheme="orange" 
                            variant="solid"
                            onClick={() => navigate('/app/inventario/kardex')}
                            ml={{ base: 0, md: 4 }}
                            mt={{ base: 2, md: 0 }}
                        >
                            Ver Alertas
                        </Button>
                    </Alert>
                </FadeInBox>
            )}

            {/* Cards de Resumen Principal */}
            <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6} mb={6}>
                {/* Card Materias Primas */}
                <FadeInBox delay={0.15}>
                    <Card 
                        bg={cardBg} 
                        borderWidth="1px" 
                        borderColor={borderColor} 
                        shadow="md"
                        borderRadius="xl"
                        overflow="hidden"
                        transition="all 0.3s ease"
                        _hover={{ transform: 'translateY(-4px)', shadow: 'lg' }}
                    >
                        {/* Gradient accent bar */}
                        <Box h="4px" bgGradient="linear(to-r, blue.400, blue.600)" />
                        <CardHeader pb={2}>
                            <Flex justify="space-between" align="center">
                                <HStack spacing={3}>
                                    <Flex 
                                        w="40px" 
                                        h="40px" 
                                        bg="blue.50" 
                                        borderRadius="lg" 
                                        align="center" 
                                        justify="center"
                                    >
                                        <Icon as={FiBox} boxSize={5} color="blue.500" />
                                    </Flex>
                                    <Heading size="md" color="gray.700">Materias Primas</Heading>
                                </HStack>
                                <Button 
                                    size="sm" 
                                    rightIcon={<ChevronRightIcon />}
                                    variant="ghost"
                                    colorScheme="blue"
                                    onClick={() => navigate('/app/inventario/materias-primas')}
                                    _hover={{ bg: 'blue.50' }}
                                >
                                    Ver Todo
                                </Button>
                            </Flex>
                        </CardHeader>
                    <CardBody>
                        <SimpleGrid columns={2} spacing={4}>
                            <Stat>
                                <StatLabel>Total Items</StatLabel>
                                <StatNumber>{mp.total_items || 0}</StatNumber>
                            </Stat>
                            <Stat>
                                <StatLabel>Valor Total</StatLabel>
                                <StatNumber color="blue.500">
                                    {formatCurrency(mp.valor_total)}
                                </StatNumber>
                            </Stat>
                            <Stat>
                                <StatLabel>Stock Bajo</StatLabel>
                                <StatNumber color={mp.stock_bajo > 0 ? 'orange.500' : 'green.500'}>
                                    {mp.stock_bajo || 0}
                                </StatNumber>
                            </Stat>
                            <Stat>
                                <StatLabel>Por Vencer</StatLabel>
                                <StatNumber color={mp.por_vencer > 0 ? 'red.500' : 'green.500'}>
                                    {mp.por_vencer || 0}
                                </StatNumber>
                            </Stat>
                        </SimpleGrid>

                        {/* Mini tabla de alertas MP */}
                        {alertasMP.length > 0 && (
                            <Box mt={4}>
                                <Text fontWeight="medium" mb={2} fontSize="sm" color="gray.600">
                                    Alertas Recientes
                                </Text>
                                <VStack align="stretch" spacing={2}>
                                    {alertasMP.slice(0, 3).map((alerta, idx) => (
                                        <Flex 
                                            key={idx} 
                                            p={2} 
                                            bg={alerta.tipo === 'stock_bajo' ? 'orange.50' : 'red.50'}
                                            borderRadius="md"
                                            align="center"
                                            justify="space-between"
                                        >
                                            <HStack>
                                                <WarningIcon 
                                                    color={alerta.tipo === 'stock_bajo' ? 'orange.500' : 'red.500'} 
                                                    boxSize={3}
                                                />
                                                <Text fontSize="sm" noOfLines={1}>{alerta.producto_nombre}</Text>
                                            </HStack>
                                            <Badge 
                                                colorScheme={alerta.tipo === 'stock_bajo' ? 'orange' : 'red'}
                                                fontSize="xs"
                                            >
                                                {alerta.tipo === 'stock_bajo' ? 'Stock Bajo' : 'Por Vencer'}
                                            </Badge>
                                        </Flex>
                                    ))}
                                </VStack>
                            </Box>
                        )}
                    </CardBody>
                    </Card>
                </FadeInBox>

                {/* Card Productos Terminados */}
                <FadeInBox delay={0.2}>
                    <Card 
                        bg={cardBg} 
                        borderWidth="1px" 
                        borderColor={borderColor} 
                        shadow="md"
                        borderRadius="xl"
                        overflow="hidden"
                        transition="all 0.3s ease"
                        _hover={{ transform: 'translateY(-4px)', shadow: 'lg' }}
                    >
                        {/* Gradient accent bar */}
                        <Box h="4px" bgGradient="linear(to-r, green.400, green.600)" />
                        <CardHeader pb={2}>
                            <Flex justify="space-between" align="center">
                                <HStack spacing={3}>
                                    <Flex 
                                        w="40px" 
                                        h="40px" 
                                        bg="green.50" 
                                        borderRadius="lg" 
                                        align="center" 
                                        justify="center"
                                    >
                                        <Icon as={FiPackage} boxSize={5} color="green.500" />
                                    </Flex>
                                    <Heading size="md" color="gray.700">Productos Terminados</Heading>
                                </HStack>
                                <Button 
                                    size="sm" 
                                    rightIcon={<ChevronRightIcon />}
                                    variant="ghost"
                                    colorScheme="green"
                                    onClick={() => navigate('/app/inventario/productos-terminados')}
                                    _hover={{ bg: 'green.50' }}
                                >
                                    Ver Todo
                                </Button>
                            </Flex>
                        </CardHeader>
                        <CardBody>
                        <SimpleGrid columns={2} spacing={4}>
                            <Stat>
                                <StatLabel>Total Items</StatLabel>
                                <StatNumber>{pt.total_items || 0}</StatNumber>
                            </Stat>
                            <Stat>
                                <StatLabel>Valor al Costo</StatLabel>
                                <StatNumber color="blue.500">
                                    {formatCurrency(pt.valor_costo)}
                                </StatNumber>
                            </Stat>
                            <Stat>
                                <StatLabel>Valor Venta</StatLabel>
                                <StatNumber color="green.500">
                                    {formatCurrency(pt.valor_venta)}
                                </StatNumber>
                            </Stat>
                            <Stat>
                                <StatLabel>Stock Bajo</StatLabel>
                                <StatNumber color={pt.stock_bajo > 0 ? 'orange.500' : 'green.500'}>
                                    {pt.stock_bajo || 0}
                                </StatNumber>
                            </Stat>
                        </SimpleGrid>

                        {/* Mini tabla de alertas PT */}
                        {alertasPT.length > 0 && (
                            <Box mt={4}>
                                <Text fontWeight="medium" mb={2} fontSize="sm" color="gray.600">
                                    Alertas Recientes
                                </Text>
                                <VStack align="stretch" spacing={2}>
                                    {alertasPT.slice(0, 3).map((alerta, idx) => (
                                        <Flex 
                                            key={idx} 
                                            p={2} 
                                            bg="orange.50"
                                            borderRadius="md"
                                            align="center"
                                            justify="space-between"
                                        >
                                            <HStack>
                                                <WarningIcon color="orange.500" boxSize={3} />
                                                <Text fontSize="sm" noOfLines={1}>{alerta.producto_nombre}</Text>
                                            </HStack>
                                            <Badge colorScheme="orange" fontSize="xs">
                                                Stock Bajo
                                            </Badge>
                                        </Flex>
                                    ))}
                                </VStack>
                            </Box>
                        )}
                    </CardBody>
                    </Card>
                </FadeInBox>
            </SimpleGrid>

            {/* Totales Consolidados */}
            <FadeInBox delay={0.25}>
                <Card 
                    bg={cardBg} 
                    borderWidth="1px" 
                    borderColor={borderColor} 
                    shadow="md" 
                    mb={6}
                    borderRadius="xl"
                    overflow="hidden"
                >
                    <Box h="4px" bgGradient="linear(to-r, purple.400, purple.600)" />
                    <CardHeader>
                        <Heading size="md" color="gray.700">Resumen Consolidado</Heading>
                    </CardHeader>
                    <CardBody>
                        <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
                            <Stat 
                                textAlign="center" 
                                p={4} 
                                bg="blue.50" 
                                borderRadius="xl"
                                transition="all 0.2s"
                                _hover={{ transform: 'scale(1.02)' }}
                            >
                                <StatLabel fontSize="xs" color="gray.600" fontWeight="medium">
                                    Valor Total Inventario
                                </StatLabel>
                                <StatNumber fontSize="xl" color="blue.600" fontWeight="bold">
                                    {formatCurrency((mp.valor_total || 0) + (pt.valor_costo || 0))}
                                </StatNumber>
                                <StatHelpText fontSize="xs">MP + PT al costo</StatHelpText>
                            </Stat>
                            
                            <Stat 
                                textAlign="center" 
                                p={4} 
                                bg="green.50" 
                                borderRadius="xl"
                                transition="all 0.2s"
                                _hover={{ transform: 'scale(1.02)' }}
                            >
                                <StatLabel fontSize="xs" color="gray.600" fontWeight="medium">
                                    Potencial de Venta
                                </StatLabel>
                                <StatNumber fontSize="xl" color="green.600" fontWeight="bold">
                                    {formatCurrency(pt.valor_venta || 0)}
                                </StatNumber>
                                <StatHelpText fontSize="xs">Productos terminados</StatHelpText>
                            </Stat>
                            
                            <Stat 
                                textAlign="center" 
                                p={4} 
                                bg="orange.50" 
                                borderRadius="xl"
                                transition="all 0.2s"
                                _hover={{ transform: 'scale(1.02)' }}
                            >
                                <StatLabel fontSize="xs" color="gray.600" fontWeight="medium">
                                    Alertas Totales
                                </StatLabel>
                                <StatNumber fontSize="xl" color="orange.600" fontWeight="bold">
                                    {totalAlertas}
                                </StatNumber>
                                <StatHelpText fontSize="xs">Requieren atención</StatHelpText>
                            </Stat>
                            
                            <Stat 
                                textAlign="center" 
                                p={4} 
                                bg="purple.50" 
                                borderRadius="xl"
                                transition="all 0.2s"
                                _hover={{ transform: 'scale(1.02)' }}
                            >
                                <StatLabel fontSize="xs" color="gray.600" fontWeight="medium">
                                    Total SKUs
                                </StatLabel>
                                <StatNumber fontSize="xl" color="purple.600" fontWeight="bold">
                                    {(mp.total_items || 0) + (pt.total_items || 0)}
                                </StatNumber>
                                <StatHelpText fontSize="xs">Items únicos</StatHelpText>
                            </Stat>
                        </SimpleGrid>
                    </CardBody>
                </Card>
            </FadeInBox>

            {/* Accesos Rápidos */}
            <FadeInBox delay={0.3}>
                <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
                    <Button
                        variant="outline"
                        h="auto"
                        p={5}
                        borderRadius="xl"
                        borderWidth="2px"
                        onClick={() => navigate('/app/inventario/materias-primas')}
                        transition="all 0.3s ease"
                        _hover={{ 
                            transform: 'translateY(-4px)', 
                            shadow: 'lg',
                            borderColor: 'blue.300',
                            bg: 'blue.50'
                        }}
                    >
                        <VStack spacing={3}>
                            <Flex 
                                w="48px" 
                                h="48px" 
                                bg="blue.100" 
                                borderRadius="lg" 
                                align="center" 
                                justify="center"
                            >
                                <Icon as={FiBox} boxSize={6} color="blue.600" />
                            </Flex>
                            <Text fontWeight="medium" color="gray.700">Materias Primas</Text>
                        </VStack>
                    </Button>
                    <Button
                        variant="outline"
                        h="auto"
                        p={5}
                        borderRadius="xl"
                        borderWidth="2px"
                        onClick={() => navigate('/app/inventario/productos-terminados')}
                        transition="all 0.3s ease"
                        _hover={{ 
                            transform: 'translateY(-4px)', 
                            shadow: 'lg',
                            borderColor: 'green.300',
                            bg: 'green.50'
                        }}
                    >
                        <VStack spacing={3}>
                            <Flex 
                                w="48px" 
                                h="48px" 
                                bg="green.100" 
                                borderRadius="lg" 
                                align="center" 
                                justify="center"
                            >
                                <Icon as={FiPackage} boxSize={6} color="green.600" />
                            </Flex>
                            <Text fontWeight="medium" color="gray.700">Prod. Terminados</Text>
                        </VStack>
                    </Button>
                    <Button
                        variant="outline"
                        h="auto"
                        p={5}
                        borderRadius="xl"
                        borderWidth="2px"
                        onClick={() => navigate('/app/inventario')}
                        transition="all 0.3s ease"
                        _hover={{ 
                            transform: 'translateY(-4px)', 
                            shadow: 'lg',
                            borderColor: 'purple.300',
                            bg: 'purple.50'
                        }}
                    >
                        <VStack spacing={3}>
                            <Flex 
                                w="48px" 
                                h="48px" 
                                bg="purple.100" 
                                borderRadius="lg" 
                                align="center" 
                                justify="center"
                            >
                                <Icon as={FiTrendingUp} boxSize={6} color="purple.600" />
                            </Flex>
                            <Text fontWeight="medium" color="gray.700">Inventario General</Text>
                        </VStack>
                    </Button>
                    <Button
                        variant="outline"
                        h="auto"
                        p={5}
                        borderRadius="xl"
                        borderWidth="2px"
                        onClick={() => navigate('/app/inventario/kardex')}
                        transition="all 0.3s ease"
                        _hover={{ 
                            transform: 'translateY(-4px)', 
                            shadow: 'lg',
                            borderColor: 'orange.300',
                            bg: 'orange.50'
                        }}
                    >
                        <VStack spacing={3}>
                            <Flex 
                                w="48px" 
                                h="48px" 
                                bg="orange.100" 
                                borderRadius="lg" 
                                align="center" 
                                justify="center"
                            >
                                <Icon as={FiAlertTriangle} boxSize={6} color="orange.600" />
                            </Flex>
                            <Text fontWeight="medium" color="gray.700">Kardex / Movimientos</Text>
                        </VStack>
                    </Button>
                </SimpleGrid>
            </FadeInBox>
        </Box>
    );
};

export default ResumenInventariosSeparados;
