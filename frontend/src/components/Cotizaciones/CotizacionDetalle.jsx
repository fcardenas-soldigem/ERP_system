import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardBody,
  CardHeader,
  Heading,
  Text,
  Badge,
  Button,
  Flex,
  HStack,
  VStack,
  Divider,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Spinner,
  Center,
  useToast,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  IconButton,
  Alert,
  AlertIcon,
  useColorModeValue
} from '@chakra-ui/react';
import {
  FaArrowLeft,
  FaEdit,
  FaFilePdf,
  FaCopy,
  FaExchangeAlt,
  FaEllipsisV,
  FaEnvelope,
  FaCheck,
  FaTimes,
  FaUser,
  FaCalendar,
  FaFileAlt
} from 'react-icons/fa';
import { useParams, useNavigate } from 'react-router-dom';
import cotizacionesService from '../../services/cotizacionesService';
import CrearProductosCotizacionModal from './CrearProductosCotizacionModal';

const CotizacionDetalle = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [cotizacion, setCotizacion] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [modalProductos, setModalProductos] = useState({
    isOpen: false,
    productos: [],
    moneda: 'PEN',
  });

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  useEffect(() => {
    cargarCotizacion();
  }, [id]);

  const cargarCotizacion = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await cotizacionesService.getById(id);
      setCotizacion(data);
    } catch (err) {
      console.error('Error al cargar cotización:', err);
      setError(err.response?.data?.detail || 'Error al cargar la cotización');
      toast({
        title: 'Error',
        description: err.response?.data?.detail || 'No se pudo cargar la cotización',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleExportarPDF = async () => {
    try {
      await cotizacionesService.exportarPDF(id);
      toast({
        title: 'PDF generado',
        description: 'La cotización se ha descargado correctamente',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (err) {
      toast({
        title: 'Error al generar PDF',
        description: err.response?.data?.detail || 'No se pudo generar el PDF',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const handleCambiarEstado = async (nuevoEstado) => {
    try {
      const result = await cotizacionesService.cambiarEstado(id, nuevoEstado);

      // Si el backend convirtió automáticamente a venta (al aceptar)
      if (result?.venta_creada && result?.venta_id) {
        toast({
          title: 'Cotización aceptada',
          description:
            result.message || `Venta ${result.venta_numero} creada automáticamente`,
          status: 'success',
          duration: 4000,
          isClosable: true,
        });
        navigate(`/app/ventas/${result.venta_id}`);
        return;
      }

      toast({
        title: 'Estado actualizado',
        description: `La cotización ahora está ${nuevoEstado}`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      cargarCotizacion();
    } catch (err) {
      const data = err.response?.data;
      if (data?.error === 'productos_faltantes' && data?.productos_faltantes?.length) {
        setModalProductos({
          isOpen: true,
          productos: data.productos_faltantes,
          moneda: data.moneda || cotizacion?.moneda || 'PEN',
        });
        return;
      }
      toast({
        title: 'Error',
        description:
          data?.error ||
          data?.detail ||
          'No se pudo cambiar el estado',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const handleDuplicar = async () => {
    try {
      const nuevaCotizacion = await cotizacionesService.duplicar(id);
      toast({
        title: 'Cotización duplicada',
        description: `Nueva cotización: ${nuevaCotizacion.numero}`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      navigate(`/app/cotizaciones/${nuevaCotizacion.id}`);
    } catch (err) {
      toast({
        title: 'Error',
        description: err.response?.data?.detail || 'No se pudo duplicar',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const handleConvertirVenta = async () => {
    try {
      const result = await cotizacionesService.convertirVenta(id);
      toast({
        title: 'Convertida a venta',
        description: result.message || 'Cotización convertida exitosamente',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      if (result.venta_id) {
        navigate(`/app/ventas/${result.venta_id}`);
      } else {
        cargarCotizacion();
      }
    } catch (err) {
      const data = err.response?.data;
      if (data?.error === 'productos_faltantes' && data?.productos_faltantes?.length) {
        setModalProductos({
          isOpen: true,
          productos: data.productos_faltantes,
          moneda: data.moneda || cotizacion?.moneda || 'PEN',
        });
        return;
      }
      toast({
        title: 'Error',
        description:
          data?.error ||
          data?.detail ||
          'No se pudo convertir a venta',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const getEstadoBadge = (estado) => {
    const config = {
      borrador: { color: 'gray', icon: FaFileAlt },
      enviada: { color: 'blue', icon: FaEnvelope },
      aceptada: { color: 'green', icon: FaCheck },
      rechazada: { color: 'red', icon: FaTimes },
      vencida: { color: 'orange', icon: FaCalendar },
      convertida: { color: 'purple', icon: FaExchangeAlt }
    };
    const { color } = config[estado] || { color: 'gray' };
    return (
      <Badge colorScheme={color} fontSize="md" px={3} py={1} borderRadius="full">
        {estado?.toUpperCase()}
      </Badge>
    );
  };

  const formatCurrency = (amount, moneda = 'PEN') => {
    const symbol = moneda === 'PEN' ? 'S/' : '$';
    return `${symbol} ${parseFloat(amount || 0).toFixed(2)}`;
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('es-PE', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  if (loading) {
    return (
      <Center py={20}>
        <Spinner size="xl" color="blue.500" thickness="4px" />
      </Center>
    );
  }

  if (error) {
    return (
      <Box p={6}>
        <Alert status="error" borderRadius="lg">
          <AlertIcon />
          {error}
        </Alert>
        <Button mt={4} leftIcon={<FaArrowLeft />} onClick={() => navigate('/app/cotizaciones')}>
          Volver a Cotizaciones
        </Button>
      </Box>
    );
  }

  if (!cotizacion) {
    return (
      <Box p={6}>
        <Alert status="warning" borderRadius="lg">
          <AlertIcon />
          Cotización no encontrada
        </Alert>
        <Button mt={4} leftIcon={<FaArrowLeft />} onClick={() => navigate('/app/cotizaciones')}>
          Volver a Cotizaciones
        </Button>
      </Box>
    );
  }

  return (
    <Box p={6}>
      {/* Header */}
      <Flex justify="space-between" align="center" mb={6}>
        <HStack spacing={4}>
          <IconButton
            icon={<FaArrowLeft />}
            variant="ghost"
            onClick={() => navigate('/app/cotizaciones')}
            aria-label="Volver"
          />
          <VStack align="start" spacing={0}>
            <Heading size="lg">Cotización {cotizacion.numero}</Heading>
            <Text color="gray.500">{cotizacion.asunto}</Text>
          </VStack>
          {getEstadoBadge(cotizacion.estado)}
        </HStack>

        <HStack spacing={3}>
          <Button
            leftIcon={<FaFilePdf />}
            colorScheme="red"
            variant="outline"
            onClick={handleExportarPDF}
          >
            Exportar PDF
          </Button>
          <Button
            leftIcon={<FaEdit />}
            colorScheme="blue"
            onClick={() => navigate(`/app/cotizaciones/${id}/editar`)}
          >
            Editar
          </Button>
          <Menu>
            <MenuButton
              as={IconButton}
              icon={<FaEllipsisV />}
              variant="outline"
            />
            <MenuList>
              <MenuItem icon={<FaCopy />} onClick={handleDuplicar}>
                Duplicar
              </MenuItem>
              {cotizacion.estado !== 'convertida' && !cotizacion.venta_info && (
                <MenuItem icon={<FaExchangeAlt />} onClick={handleConvertirVenta}>
                  Convertir a Venta
                </MenuItem>
              )}
              <Divider />
              <MenuItem icon={<FaEnvelope />} onClick={() => handleCambiarEstado('enviada')}>
                Marcar como Enviada
              </MenuItem>
              <MenuItem icon={<FaCheck />} onClick={() => handleCambiarEstado('aceptada')}>
                Marcar como Aceptada
              </MenuItem>
              <MenuItem icon={<FaTimes />} onClick={() => handleCambiarEstado('rechazada')}>
                Marcar como Rechazada
              </MenuItem>
            </MenuList>
          </Menu>
        </HStack>
      </Flex>

      {/* Banner de venta enlazada */}
      {cotizacion.venta_info && (
        <Alert status="success" borderRadius="lg" mb={4} variant="left-accent">
          <AlertIcon />
          <Box flex="1">
            <Text fontWeight="bold">
              Cotización convertida a venta {cotizacion.venta_info.numero}
            </Text>
            <Text fontSize="sm" color="gray.600">
              Total: {cotizacion.venta_info.moneda === 'PEN' ? 'S/' : '$'}{' '}
              {parseFloat(cotizacion.venta_info.total || 0).toFixed(2)} · Estado:{' '}
              {cotizacion.venta_info.estado}
            </Text>
          </Box>
          <Button
            size="sm"
            colorScheme="green"
            onClick={() => navigate(`/app/ventas/${cotizacion.venta_info.id}`)}
          >
            Ver venta
          </Button>
        </Alert>
      )}

      <SimpleGrid columns={{ base: 1, lg: 3 }} spacing={6} mb={6}>
        {/* Info del Cliente */}
        <Card bg={cardBg} borderWidth="1px" borderColor={borderColor}>
          <CardHeader pb={2}>
            <HStack>
              <FaUser color="blue" />
              <Heading size="sm">Cliente</Heading>
            </HStack>
          </CardHeader>
          <CardBody pt={2}>
            <VStack align="start" spacing={2}>
              <Text fontWeight="bold" fontSize="lg">{cotizacion.cliente_nombre}</Text>
              {cotizacion.cliente_ruc && (
                <Text color="gray.600">RUC: {cotizacion.cliente_ruc}</Text>
              )}
              {cotizacion.cliente_email && (
                <Text color="gray.600">{cotizacion.cliente_email}</Text>
              )}
              {cotizacion.cliente_telefono && (
                <Text color="gray.600">{cotizacion.cliente_telefono}</Text>
              )}
            </VStack>
          </CardBody>
        </Card>

        {/* Fechas */}
        <Card bg={cardBg} borderWidth="1px" borderColor={borderColor}>
          <CardHeader pb={2}>
            <HStack>
              <FaCalendar color="green" />
              <Heading size="sm">Fechas</Heading>
            </HStack>
          </CardHeader>
          <CardBody pt={2}>
            <VStack align="start" spacing={3}>
              <Box>
                <Text color="gray.500" fontSize="sm">Fecha de Emisión</Text>
                <Text fontWeight="semibold">{formatDate(cotizacion.fecha_emision)}</Text>
              </Box>
              <Box>
                <Text color="gray.500" fontSize="sm">Fecha de Vencimiento</Text>
                <Text fontWeight="semibold">{formatDate(cotizacion.fecha_vencimiento)}</Text>
              </Box>
              {cotizacion.dias_validez && (
                <Text color="gray.600" fontSize="sm">
                  Válida por {cotizacion.dias_validez} días
                </Text>
              )}
            </VStack>
          </CardBody>
        </Card>

        {/* Totales */}
        <Card bg={cardBg} borderWidth="1px" borderColor={borderColor}>
          <CardBody>
            <VStack spacing={4}>
              <Stat textAlign="center">
                <StatLabel color="gray.500">Total</StatLabel>
                <StatNumber fontSize="3xl" color="blue.600">
                  {formatCurrency(cotizacion.total, cotizacion.moneda)}
                </StatNumber>
              </Stat>
              <Divider />
              <HStack justify="space-between" w="full">
                <Text color="gray.500">Subtotal:</Text>
                <Text fontWeight="semibold">
                  {formatCurrency(cotizacion.subtotal, cotizacion.moneda)}
                </Text>
              </HStack>
              <HStack justify="space-between" w="full">
                <Text color="gray.500">IGV ({cotizacion.igv_porcentaje || 18}%):</Text>
                <Text fontWeight="semibold">
                  {formatCurrency(cotizacion.igv, cotizacion.moneda)}
                </Text>
              </HStack>
              {cotizacion.descuento > 0 && (
                <HStack justify="space-between" w="full">
                  <Text color="gray.500">Descuento:</Text>
                  <Text fontWeight="semibold" color="red.500">
                    -{formatCurrency(cotizacion.descuento, cotizacion.moneda)}
                  </Text>
                </HStack>
              )}
            </VStack>
          </CardBody>
        </Card>
      </SimpleGrid>

      {/* Detalle de Items */}
      <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} mb={6}>
        <CardHeader>
          <Heading size="md">Detalle de Productos/Servicios</Heading>
        </CardHeader>
        <CardBody pt={0}>
          <Box overflowX="auto">
            <Table variant="simple">
              <Thead bg="gray.50">
                <Tr>
                  <Th>#</Th>
                  <Th>Descripción</Th>
                  <Th isNumeric>Cantidad</Th>
                  <Th isNumeric>P. Unitario</Th>
                  <Th isNumeric>Subtotal</Th>
                </Tr>
              </Thead>
              <Tbody>
                {cotizacion.items?.length > 0 ? (
                  cotizacion.items.map((item, index) => (
                    <Tr key={item.id || index}>
                      <Td>{index + 1}</Td>
                      <Td>
                        <VStack align="start" spacing={0}>
                          <Text fontWeight="semibold">
                            {item.producto_nombre || item.descripcion}
                          </Text>
                          {item.descripcion && item.producto_nombre && (
                            <Text fontSize="sm" color="gray.500">
                              {item.descripcion}
                            </Text>
                          )}
                        </VStack>
                      </Td>
                      <Td isNumeric>{parseFloat(item.cantidad).toFixed(2)}</Td>
                      <Td isNumeric>
                        {formatCurrency(item.precio_unitario, cotizacion.moneda)}
                      </Td>
                      <Td isNumeric fontWeight="semibold">
                        {formatCurrency(item.subtotal, cotizacion.moneda)}
                      </Td>
                    </Tr>
                  ))
                ) : (
                  <Tr>
                    <Td colSpan={5} textAlign="center" color="gray.500">
                      No hay items en esta cotización
                    </Td>
                  </Tr>
                )}
              </Tbody>
            </Table>
          </Box>
        </CardBody>
      </Card>

      {/* Notas y Términos */}
      {(cotizacion.notas || cotizacion.terminos_condiciones) && (
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
          {cotizacion.notas && (
            <Card bg={cardBg} borderWidth="1px" borderColor={borderColor}>
              <CardHeader>
                <Heading size="sm">Notas</Heading>
              </CardHeader>
              <CardBody pt={0}>
                <Text whiteSpace="pre-wrap">{cotizacion.notas}</Text>
              </CardBody>
            </Card>
          )}
          {cotizacion.terminos_condiciones && (
            <Card bg={cardBg} borderWidth="1px" borderColor={borderColor}>
              <CardHeader>
                <Heading size="sm">Términos y Condiciones</Heading>
              </CardHeader>
              <CardBody pt={0}>
                <Text whiteSpace="pre-wrap">{cotizacion.terminos_condiciones}</Text>
              </CardBody>
            </Card>
          )}
        </SimpleGrid>
      )}

      <CrearProductosCotizacionModal
        isOpen={modalProductos.isOpen}
        onClose={() => setModalProductos((prev) => ({ ...prev, isOpen: false }))}
        productosFaltantes={modalProductos.productos}
        cotizacionId={parseInt(id)}
        moneda={modalProductos.moneda}
        onConversionExitosa={(result) => {
          if (result?.venta_id) {
            navigate(`/app/ventas/${result.venta_id}`);
          } else {
            cargarCotizacion();
          }
        }}
      />
    </Box>
  );
};

export default CotizacionDetalle;
