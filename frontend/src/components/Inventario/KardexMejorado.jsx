import React, { useState, useEffect } from 'react';
import {
    Box,
    Table,
    Thead,
    Tbody,
    Tr,
    Th,
    Td,
    TableContainer,
    Heading,
    Text,
    Button,
    Flex,
    HStack,
    VStack,
    Select,
    Input,
    Badge,
    useToast,
    Spinner,
    Card,
    CardHeader,
    CardBody,
} from '@chakra-ui/react';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { DownloadIcon, SearchIcon } from '@chakra-ui/icons';
import { api } from '../../api';

const KardexMejorado = () => {
    const [movimientos, setMovimientos] = useState([]);
    const [productos, setProductos] = useState([]);
    const [almacenes, setAlmacenes] = useState([]);
    const [loading, setLoading] = useState(false);
    const [saldoInicial, setSaldoInicial] = useState(null);
    const [infoSeleccion, setInfoSeleccion] = useState(null);
    const toast = useToast();

    const [filtros, setFiltros] = useState({
        producto_id: '',
        almacen_id: '',
        fecha_inicio: '',
        fecha_fin: ''
    });

    useEffect(() => {
        cargarDatosIniciales();
    }, []);

    const cargarDatosIniciales = async () => {
        try {
            const [productosRes, almacenesRes] = await Promise.all([
                api.get('/api/inventario/productos/'),
                api.get('/api/inventario/almacenes/')
            ]);
            
            setProductos(productosRes.data.results || productosRes.data);
            setAlmacenes(almacenesRes.data.results || almacenesRes.data);
        } catch (error) {
            console.error('Error cargando datos iniciales:', error);
            toast({
                title: 'Error',
                description: 'No se pudieron cargar los datos iniciales',
                status: 'error',
                duration: 3000,
            });
        }
    };

    const cargarKardex = async () => {
        if (!filtros.producto_id || !filtros.almacen_id) {
            toast({
                title: 'Campos requeridos',
                description: 'Debe seleccionar un producto y un almacén',
                status: 'warning',
                duration: 3000,
            });
            return;
        }

        setLoading(true);
        try {
            const params = new URLSearchParams();
            Object.keys(filtros).forEach(key => {
                if (filtros[key]) {
                    params.append(key, filtros[key]);
                }
            });

            // Obtener los movimientos del kardex
            const response = await api.get(`/api/inventario/kardex/kardex_producto/?${params.toString()}`);
            const data = response.data;
            
            console.log('Respuesta completa del kardex:', data);
            
            // Usar el saldo inicial calculado por el backend
            if (data.saldo_inicial) {
                setSaldoInicial({
                    cantidad: parseFloat(data.saldo_inicial.cantidad || 0),
                    costo_unitario: parseFloat(data.saldo_inicial.costo_unitario || 0),
                    costo_total: parseFloat(data.saldo_inicial.costo_total || 0)
                });
                
                console.log('Saldo inicial desde backend:', data.saldo_inicial);
            } else {
                setSaldoInicial({ cantidad: 0, costo_unitario: 0, costo_total: 0 });
            }
            
            // Usar los movimientos del backend
            const movimientosData = data.movimientos || [];
            setMovimientos(movimientosData);
            
            // Guardar información de la selección actual
            setInfoSeleccion({
                producto: data.producto,
                almacen: data.almacen,
                totalMovimientos: data.total_movimientos || movimientosData.length,
                rangoFechas: filtros.fecha_inicio && filtros.fecha_fin ? 
                    `${filtros.fecha_inicio} al ${filtros.fecha_fin}` : 'Todas las fechas'
            });
            
            console.log(`Cargados ${movimientosData.length} movimientos para el producto ${data.producto?.sku} en ${data.almacen?.nombre}`);
            
        } catch (error) {
            console.error('Error cargando kardex:', error);
            toast({
                title: 'Error al cargar Kardex',
                description: error.response?.data?.detail || error.message || 'Hubo un error al cargar los movimientos',
                status: 'error',
                duration: 5000,
            });
        } finally {
            setLoading(false);
        }
    };

    const exportarExcel = async () => {
        if (!filtros.producto_id || !filtros.almacen_id) {
            toast({
                title: 'Campos requeridos',
                description: 'Debe seleccionar un producto y un almacén para exportar',
                status: 'warning',
                duration: 3000,
            });
            return;
        }
        
        try {
            const params = new URLSearchParams();
            Object.keys(filtros).forEach(key => {
                if (filtros[key]) {
                    params.append(key, filtros[key]);
                }
            });

            toast({
                title: 'Exportando...',
                description: 'Generando archivo Excel, por favor espere...',
                status: 'info',
                duration: 3000,
            });

            const response = await api.get(
                `/api/inventario/kardex/exportar_excel/?${params.toString()}`,
                { 
                    responseType: 'blob',
                    timeout: 30000 // 30 segundos de timeout
                }
            );

            // Crear el blob con el tipo correcto
            const blob = new Blob([response.data], {
                type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            });

            // Obtener información del producto y almacén para el nombre del archivo
            const productoSeleccionado = productos.find(p => p.id == filtros.producto_id);
            const almacenSeleccionado = almacenes.find(a => a.id == filtros.almacen_id);
            
            const fechaActual = new Date().toISOString().slice(0, 10);
            const nombreProducto = productoSeleccionado ? productoSeleccionado.sku : 'producto';
            const nombreAlmacen = almacenSeleccionado ? almacenSeleccionado.nombre.replace(/\s+/g, '_') : 'almacen';
            
            let nombreArchivo = `Kardex_${nombreProducto}_${nombreAlmacen}_${fechaActual}.xlsx`;

            // Si hay filtro de fechas, incluirlo en el nombre
            if (filtros.fecha_inicio && filtros.fecha_fin) {
                nombreArchivo = `Kardex_${nombreProducto}_${nombreAlmacen}_${filtros.fecha_inicio}_${filtros.fecha_fin}.xlsx`;
            }

            // Crear y descargar el archivo
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', nombreArchivo);
            document.body.appendChild(link);
            link.click();
            
            // Limpiar
            setTimeout(() => {
                document.body.removeChild(link);
                window.URL.revokeObjectURL(url);
            }, 100);

            toast({
                title: '¡Exportación exitosa!',
                description: `El archivo ${nombreArchivo} se ha descargado correctamente`,
                status: 'success',
                duration: 5000,
            });
            
        } catch (error) {
            console.error('Error exportando kardex:', error);
            
            let errorMessage = 'No se pudo exportar el kardex';
            if (error.response?.status === 404) {
                errorMessage = 'No se encontraron datos para exportar';
            } else if (error.response?.status === 500) {
                errorMessage = 'Error interno del servidor';
            } else if (error.code === 'ECONNABORTED') {
                errorMessage = 'La exportación está tomando demasiado tiempo. Intente con un rango de fechas más pequeño';
            }
            
            toast({
                title: 'Error en la exportación',
                description: errorMessage,
                status: 'error',
                duration: 5000,
            });
        }
    };

    const formatearMoneda = (valor) => {
        return new Intl.NumberFormat('es-PE', {
            style: 'currency',
            currency: 'PEN'
        }).format(valor || 0);
    };

    const formatearCantidad = (cantidad) => {
        return parseFloat(cantidad || 0).toLocaleString('es-PE', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    };

    const formatearFecha = (fecha) => {
        return format(new Date(fecha), 'dd-MMM', { locale: es });
    };

    const getColorMovimiento = (tipo) => {
        if (tipo.includes('entrada') || tipo === 'devolucion_venta') return 'green';
        if (tipo.includes('salida') || tipo === 'devolucion_compra') return 'red';
        return 'blue';
    };

    return (
        <Box p={6}>
            {/* Header */}
            <Flex justify="space-between" align="center" mb={6}>
                <VStack align="start" spacing={1}>
                    <Heading size="lg" color="gray.800">📊 Kardex de Inventario</Heading>
                    <Text color="gray.600">Control detallado de entradas, salidas y saldos con método FIFO</Text>
                </VStack>
                <Button
                    leftIcon={<DownloadIcon />}
                    colorScheme="green"
                    onClick={exportarExcel}
                    isDisabled={movimientos.length === 0}
                >
                    Exportar Excel
                </Button>
            </Flex>

            {/* Filtros */}
            <Card mb={6}>
                <CardHeader>
                    <Heading size="md">🔍 Filtros de Consulta</Heading>
                </CardHeader>
                <CardBody>
                    <VStack spacing={4}>
                        <HStack spacing={4} width="100%">
                            <Box flex="1">
                                <Text mb={2} fontWeight="medium">Producto *</Text>
                                <Select
                                    placeholder="Seleccionar producto"
                                    value={filtros.producto_id}
                                    onChange={(e) => setFiltros({...filtros, producto_id: e.target.value})}
                                >
                                    {productos.map(producto => (
                                        <option key={producto.id} value={producto.id}>
                                            {producto.sku} - {producto.nombre}
                                        </option>
                                    ))}
                                </Select>
                            </Box>
                            <Box flex="1">
                                <Text mb={2} fontWeight="medium">Almacén *</Text>
                                <Select
                                    placeholder="Seleccionar almacén"
                                    value={filtros.almacen_id}
                                    onChange={(e) => setFiltros({...filtros, almacen_id: e.target.value})}
                                >
                                    {almacenes.map(almacen => (
                                        <option key={almacen.id} value={almacen.id}>
                                            {almacen.nombre}
                                        </option>
                                    ))}
                                </Select>
                            </Box>
                        </HStack>
                        
                        <HStack spacing={4} width="100%">
                            <Box flex="1">
                                <Text mb={2} fontWeight="medium">Fecha Inicio</Text>
                                <Input
                                    type="date"
                                    value={filtros.fecha_inicio}
                                    onChange={(e) => setFiltros({...filtros, fecha_inicio: e.target.value})}
                                />
                            </Box>
                            <Box flex="1">
                                <Text mb={2} fontWeight="medium">Fecha Fin</Text>
                                <Input
                                    type="date"
                                    value={filtros.fecha_fin}
                                    onChange={(e) => setFiltros({...filtros, fecha_fin: e.target.value})}
                                />
                            </Box>
                        </HStack>

                        <HStack spacing={4}>
                            <Button
                                leftIcon={<SearchIcon />}
                                colorScheme="blue"
                                onClick={cargarKardex}
                                isLoading={loading}
                            >
                                Consultar Kardex
                            </Button>
                            <Button
                                variant="outline"
                                onClick={() => {
                                    setFiltros({
                                        producto_id: '',
                                        almacen_id: '',
                                        fecha_inicio: '',
                                        fecha_fin: ''
                                    });
                                    setMovimientos([]);
                                    setSaldoInicial(null);
                                    setInfoSeleccion(null);
                                }}
                            >
                                Limpiar
                            </Button>
                        </HStack>
                    </VStack>
                </CardBody>
            </Card>

            {/* Información de la consulta actual */}
            {infoSeleccion && (
                <Card mb={4} bg="blue.50" borderColor="blue.200">
                    <CardBody py={3}>
                        <HStack spacing={8} wrap="wrap">
                            <VStack align="start" spacing={1}>
                                <Text fontSize="xs" fontWeight="bold" color="blue.600">PRODUCTO</Text>
                                <Text fontSize="sm" fontWeight="medium">
                                    {infoSeleccion.producto.sku} - {infoSeleccion.producto.nombre}
                                </Text>
                            </VStack>
                            <VStack align="start" spacing={1}>
                                <Text fontSize="xs" fontWeight="bold" color="blue.600">ALMACÉN</Text>
                                <Text fontSize="sm" fontWeight="medium">
                                    {infoSeleccion.almacen.nombre}
                                </Text>
                            </VStack>
                            <VStack align="start" spacing={1}>
                                <Text fontSize="xs" fontWeight="bold" color="blue.600">PERÍODO</Text>
                                <Text fontSize="sm" fontWeight="medium">
                                    {infoSeleccion.rangoFechas}
                                </Text>
                            </VStack>
                            <VStack align="start" spacing={1}>
                                <Text fontSize="xs" fontWeight="bold" color="blue.600">MOVIMIENTOS</Text>
                                <Text fontSize="sm" fontWeight="medium">
                                    {infoSeleccion.totalMovimientos} registros
                                </Text>
                            </VStack>
                        </HStack>
                    </CardBody>
                </Card>
            )}

            {/* Tabla Kardex */}
            {loading ? (
                <Flex justify="center" align="center" h="200px">
                    <Spinner size="xl" />
                </Flex>
            ) : movimientos.length > 0 ? (
                <Card>
                    <CardBody p={0}>
                        <TableContainer>
                            <Table variant="simple" size="md" style={{borderCollapse: 'collapse'}}>
                                <Thead bg="gray.100">
                                    <Tr>
                                        <Th 
                                            rowSpan={2} 
                                            textAlign="center" 
                                            verticalAlign="middle" 
                                            borderRight="3px solid #2D3748"
                                            fontWeight="bold"
                                            fontSize="sm"
                                        >
                                            FECHA
                                        </Th>
                                        <Th 
                                            colSpan={3} 
                                            textAlign="center" 
                                            bg="green.100" 
                                            borderRight="3px solid #2D3748"
                                            fontWeight="bold"
                                            fontSize="sm"
                                        >
                                            ENTRADAS
                                        </Th>
                                        <Th 
                                            colSpan={3} 
                                            textAlign="center" 
                                            bg="red.100" 
                                            borderRight="3px solid #2D3748"
                                            fontWeight="bold"
                                            fontSize="sm"
                                        >
                                            SALIDAS
                                        </Th>
                                        <Th 
                                            colSpan={3} 
                                            textAlign="center" 
                                            bg="blue.100"
                                            fontWeight="bold"
                                            fontSize="sm"
                                        >
                                            SALDOS
                                        </Th>
                                    </Tr>
                                    <Tr>
                                        <Th textAlign="center" bg="green.50" fontSize="xs" fontWeight="bold">CANTIDAD</Th>
                                        <Th textAlign="center" bg="green.50" fontSize="xs" fontWeight="bold">COSTO UNITARIO</Th>
                                        <Th textAlign="center" bg="green.50" borderRight="3px solid #2D3748" fontSize="xs" fontWeight="bold">COSTO TOTAL</Th>
                                        <Th textAlign="center" bg="red.50" fontSize="xs" fontWeight="bold">CANTIDAD</Th>
                                        <Th textAlign="center" bg="red.50" fontSize="xs" fontWeight="bold">COSTO UNITARIO</Th>
                                        <Th textAlign="center" bg="red.50" borderRight="3px solid #2D3748" fontSize="xs" fontWeight="bold">COSTO TOTAL</Th>
                                        <Th textAlign="center" bg="blue.50" fontSize="xs" fontWeight="bold">CANTIDAD</Th>
                                        <Th textAlign="center" bg="blue.50" fontSize="xs" fontWeight="bold">COSTO UNITARIO</Th>
                                        <Th textAlign="center" bg="blue.50" fontSize="xs" fontWeight="bold">COSTO TOTAL</Th>
                                    </Tr>
                                </Thead>
                                <Tbody>
                                    {/* Saldo Inicial */}
                                    {saldoInicial && (
                                        <Tr bg="yellow.100" borderBottom="2px solid #2D3748">
                                            <Td borderRight="3px solid #2D3748" fontWeight="bold">
                                                <Badge colorScheme="yellow" fontSize="xs">SALDO INICIAL</Badge>
                                            </Td>
                                            {/* Entradas vacías */}
                                            <Td textAlign="center" bg="green.25">-</Td>
                                            <Td textAlign="center" bg="green.25">-</Td>
                                            <Td textAlign="center" bg="green.25" borderRight="3px solid #2D3748">-</Td>
                                            {/* Salidas vacías */}
                                            <Td textAlign="center" bg="red.25">-</Td>
                                            <Td textAlign="center" bg="red.25">-</Td>
                                            <Td textAlign="center" bg="red.25" borderRight="3px solid #2D3748">-</Td>
                                            {/* Saldo inicial */}
                                            <Td textAlign="center" bg="blue.25" fontWeight="bold">{formatearCantidad(saldoInicial.cantidad)}</Td>
                                            <Td textAlign="center" bg="blue.25" fontWeight="bold">{formatearMoneda(saldoInicial.costo_unitario)}</Td>
                                            <Td textAlign="center" bg="blue.25" fontWeight="bold">{formatearMoneda(saldoInicial.costo_total)}</Td>
                                        </Tr>
                                    )}

                                    {/* Movimientos */}
                                    {movimientos.map((movimiento, index) => (
                                        <Tr key={movimiento.id} _hover={{ bg: 'gray.50' }} borderBottom="1px solid #E2E8F0">
                                            <Td borderRight="3px solid #2D3748" py={3}>
                                                <VStack align="start" spacing={1}>
                                                    <Text fontWeight="medium" fontSize="sm">{formatearFecha(movimiento.fecha)}</Text>
                                                    <Badge 
                                                        size="sm" 
                                                        colorScheme={getColorMovimiento(movimiento.tipo_movimiento)}
                                                        fontSize="xs"
                                                    >
                                                        {movimiento.tipo_movimiento_display || movimiento.tipo_movimiento}
                                                    </Badge>
                                                    {movimiento.numero_documento && (
                                                        <Text fontSize="xs" color="gray.600">
                                                            Doc: {movimiento.numero_documento}
                                                        </Text>
                                                    )}
                                                    {movimiento.tipo_documento_display && (
                                                        <Text fontSize="xs" color="blue.600" fontWeight="medium">
                                                            {movimiento.tipo_documento_display}
                                                        </Text>
                                                    )}
                                                    {movimiento.observaciones && (
                                                        <Text fontSize="xs" color="gray.500" noOfLines={2}>
                                                            {movimiento.observaciones}
                                                        </Text>
                                                    )}
                                                </VStack>
                                            </Td>

                                            {/* ENTRADAS */}
                                            <Td textAlign="center" bg="green.25" fontSize="sm">
                                                {movimiento.cantidad_entrada > 0 ? formatearCantidad(movimiento.cantidad_entrada) : '-'}
                                            </Td>
                                            <Td textAlign="center" bg="green.25" fontSize="sm">
                                                {movimiento.cantidad_entrada > 0 ? formatearMoneda(movimiento.costo_unitario) : '-'}
                                            </Td>
                                            <Td textAlign="center" bg="green.25" borderRight="3px solid #2D3748" fontSize="sm">
                                                {movimiento.cantidad_entrada > 0 ? formatearMoneda(movimiento.costo_total_entrada) : '-'}
                                            </Td>

                                            {/* SALIDAS */}
                                            <Td textAlign="center" bg="red.25" fontSize="sm">
                                                {movimiento.cantidad_salida > 0 ? formatearCantidad(movimiento.cantidad_salida) : '-'}
                                            </Td>
                                            <Td textAlign="center" bg="red.25" fontSize="sm">
                                                {movimiento.cantidad_salida > 0 ? formatearMoneda(movimiento.costo_unitario) : '-'}
                                            </Td>
                                            <Td textAlign="center" bg="red.25" borderRight="3px solid #2D3748" fontSize="sm">
                                                {movimiento.cantidad_salida > 0 ? formatearMoneda(movimiento.costo_total_salida) : '-'}
                                            </Td>

                                            {/* SALDOS */}
                                            <Td textAlign="center" bg="blue.25" fontWeight="bold" fontSize="sm">
                                                {formatearCantidad(movimiento.cantidad_saldo)}
                                            </Td>
                                            <Td textAlign="center" bg="blue.25" fontWeight="bold" fontSize="sm">
                                                {formatearMoneda(movimiento.costo_promedio)}
                                            </Td>
                                            <Td textAlign="center" bg="blue.25" fontWeight="bold" fontSize="sm">
                                                {formatearMoneda(movimiento.costo_saldo)}
                                            </Td>
                                        </Tr>
                                    ))}
                                </Tbody>
                            </Table>
                        </TableContainer>
                    </CardBody>
                </Card>
            ) : (
                <Card>
                    <CardBody>
                        <Flex direction="column" align="center" justify="center" py={10}>
                            <Text fontSize="lg" color="gray.500" mb={4}>
                                📋 No hay movimientos para mostrar
                            </Text>
                            <Text fontSize="sm" color="gray.400">
                                Seleccione un producto y almacén, luego haga clic en "Consultar Kardex"
                            </Text>
                        </Flex>
                    </CardBody>
                </Card>
            )}
        </Box>
    );
};

export default KardexMejorado; 