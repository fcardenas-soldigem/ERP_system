import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  IconButton,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  useToast,
  Flex,
  Heading,
  Input,
  Select,
  HStack,
  Text,
  Spinner,
  Center
} from '@chakra-ui/react';
import {
  FaPlus,
  FaEllipsisV,
  FaEye,
  FaEdit,
  FaFilePdf,
  FaCopy,
  FaExchangeAlt,
  FaTrash
} from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';
import cotizacionesService from '../../services/cotizacionesService';

const CotizacionList = () => {
  const [cotizaciones, setCotizaciones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtros, setFiltros] = useState({
    search: '',
    estado: ''
  });
  const navigate = useNavigate();
  const toast = useToast();

  useEffect(() => {
    cargarCotizaciones();
  }, [filtros]);

  const cargarCotizaciones = async () => {
    try {
      setLoading(true);
      const data = await cotizacionesService.getAll(filtros);
      // Si la respuesta es paginada, extraer los resultados
      if (data && Array.isArray(data.results)) {
        setCotizaciones(data.results);
      } else if (Array.isArray(data)) {
        setCotizaciones(data);
      } else {
        setCotizaciones([]);
      }
    } catch (error) {
      console.error('Error al cargar cotizaciones:', error);
      setCotizaciones([]);
      toast({
        title: 'Error al cargar cotizaciones',
        description: error.response?.data?.detail || error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleExportarPDF = async (id) => {
    try {
      await cotizacionesService.exportarPDF(id);
      toast({
        title: 'PDF generado',
        description: 'La cotización se ha descargado correctamente',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      toast({
        title: 'Error al generar PDF',
        description: error.response?.data?.detail || error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const handleDuplicar = async (id) => {
    try {
      const nuevaCotizacion = await cotizacionesService.duplicar(id);
      toast({
        title: 'Cotización duplicada',
        description: `Nueva cotización: ${nuevaCotizacion.numero}`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      cargarCotizaciones();
    } catch (error) {
      toast({
        title: 'Error al duplicar',
        description: error.response?.data?.detail || error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const handleConvertirVenta = async (id) => {
    try {
      const result = await cotizacionesService.convertirVenta(id);
      toast({
        title: 'Convertida a venta',
        description: result.message,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      cargarCotizaciones();
    } catch (error) {
      toast({
        title: 'Error al convertir',
        description: error.response?.data?.detail || error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const handleEliminar = async (id) => {
    if (window.confirm('¿Está seguro de eliminar esta cotización?')) {
      try {
        await cotizacionesService.delete(id);
        toast({
          title: 'Cotización eliminada',
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
        cargarCotizaciones();
      } catch (error) {
        toast({
          title: 'Error al eliminar',
          description: error.response?.data?.detail || error.message,
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
      }
    }
  };

  const getEstadoBadge = (estado) => {
    const colores = {
      borrador: 'gray',
      enviada: 'blue',
      aceptada: 'green',
      rechazada: 'red',
      vencida: 'orange',
      convertida: 'purple'
    };
    return <Badge colorScheme={colores[estado] || 'gray'}>{estado.toUpperCase()}</Badge>;
  };

  return (
    <Box p={6}>
      <Flex justify="space-between" align="center" mb={6}>
        <Heading size="lg">Cotizaciones</Heading>
        <Button
          leftIcon={<FaPlus />}
          colorScheme="blue"
          onClick={() => navigate('/app/cotizaciones/nueva')}
        >
          Nueva Cotización
        </Button>
      </Flex>

      {/* Filtros */}
      <HStack spacing={4} mb={6}>
        <Input
          placeholder="Buscar por número, asunto o cliente..."
          value={filtros.search}
          onChange={(e) => setFiltros({ ...filtros, search: e.target.value })}
          maxW="400px"
        />
        <Select
          placeholder="Todos los estados"
          value={filtros.estado}
          onChange={(e) => setFiltros({ ...filtros, estado: e.target.value })}
          maxW="200px"
        >
          <option value="borrador">Borrador</option>
          <option value="enviada">Enviada</option>
          <option value="aceptada">Aceptada</option>
          <option value="rechazada">Rechazada</option>
          <option value="vencida">Vencida</option>
          <option value="convertida">Convertida</option>
        </Select>
      </HStack>

      {/* Tabla */}
      {loading ? (
        <Center py={10}>
          <Spinner size="xl" color="blue.500" />
        </Center>
      ) : cotizaciones.length === 0 ? (
        <Center py={10}>
          <Text color="gray.500">No hay cotizaciones registradas</Text>
        </Center>
      ) : (
        <Box overflowX="auto" bg="white" borderRadius="lg" shadow="sm">
          <Table variant="simple">
            <Thead bg="gray.50">
              <Tr>
                <Th>Número</Th>
                <Th>Cliente</Th>
                <Th>Asunto</Th>
                <Th>Fecha Emisión</Th>
                <Th>Vencimiento</Th>
                <Th>Estado</Th>
                <Th isNumeric>Total</Th>
                <Th>Acciones</Th>
              </Tr>
            </Thead>
            <Tbody>
              {cotizaciones.map((cotizacion) => (
                <Tr key={cotizacion.id} _hover={{ bg: 'gray.50' }}>
                  <Td fontWeight="bold">{cotizacion.numero}</Td>
                  <Td>{cotizacion.cliente_nombre}</Td>
                  <Td maxW="300px" isTruncated>{cotizacion.asunto}</Td>
                  <Td>{new Date(cotizacion.fecha_emision).toLocaleDateString()}</Td>
                  <Td>{new Date(cotizacion.fecha_vencimiento).toLocaleDateString()}</Td>
                  <Td>{getEstadoBadge(cotizacion.estado)}</Td>
                  <Td isNumeric fontWeight="bold">
                    {cotizacion.moneda === 'PEN' ? 'S/' : '$'} {parseFloat(cotizacion.total || 0).toFixed(2)}
                  </Td>
                  <Td>
                    <Menu>
                      <MenuButton
                        as={IconButton}
                        icon={<FaEllipsisV />}
                        variant="ghost"
                        size="sm"
                      />
                      <MenuList>
                        <MenuItem
                          icon={<FaEye />}
                          onClick={() => navigate(`/app/cotizaciones/${cotizacion.id}`)}
                        >
                          Ver Detalle
                        </MenuItem>
                        <MenuItem
                          icon={<FaEdit />}
                          onClick={() => navigate(`/app/cotizaciones/${cotizacion.id}/editar`)}
                        >
                          Editar
                        </MenuItem>
                        <MenuItem
                          icon={<FaFilePdf />}
                          onClick={() => handleExportarPDF(cotizacion.id)}
                        >
                          Exportar PDF
                        </MenuItem>
                        <MenuItem
                          icon={<FaCopy />}
                          onClick={() => handleDuplicar(cotizacion.id)}
                        >
                          Duplicar
                        </MenuItem>
                        {cotizacion.estado !== 'convertida' && (
                          <MenuItem
                            icon={<FaExchangeAlt />}
                            onClick={() => handleConvertirVenta(cotizacion.id)}
                          >
                            Convertir a Venta
                          </MenuItem>
                        )}
                        <MenuItem
                          icon={<FaTrash />}
                          color="red.500"
                          onClick={() => handleEliminar(cotizacion.id)}
                        >
                          Eliminar
                        </MenuItem>
                      </MenuList>
                    </Menu>
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      )}
    </Box>
  );
};

export default CotizacionList;

