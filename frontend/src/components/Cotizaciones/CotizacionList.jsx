import React, { useState, useEffect, useCallback } from 'react';
import { TableSkeleton } from '../common/SkeletonLoaders';
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
  Center,
  Tooltip,
} from '@chakra-ui/react';
import {
  FaPlus,
  FaEllipsisV,
  FaEye,
  FaEdit,
  FaFilePdf,
  FaCopy,
  FaExchangeAlt,
  FaTrash,
  FaTools,
  FaChevronLeft,
  FaChevronRight,
} from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';
import cotizacionesService from '../../services/cotizacionesService';
import CrearProductosCotizacionModal from './CrearProductosCotizacionModal';

const PAGE_SIZE = 20;

const CotizacionList = () => {
  const [cotizaciones, setCotizaciones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [paginacion, setPaginacion] = useState({
    count: 0,
    page: 1,
    totalPages: 1,
    hasPrev: false,
    hasNext: false,
  });
  const [filtros, setFiltros] = useState({ search: '', estado: '' });
  const [modalProductos, setModalProductos] = useState({
    isOpen: false,
    productos: [],
    moneda: 'PEN',
    cotizacionId: null,
  });
  const navigate = useNavigate();
  const toast = useToast();

  const cargarCotizaciones = useCallback(async (page = 1) => {
    try {
      setLoading(true);
      const data = await cotizacionesService.getAll({
        ...filtros,
        page,
        page_size: PAGE_SIZE,
      });

      if (data && Array.isArray(data.results)) {
        setCotizaciones(data.results);
        const total = data.count || 0;
        const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
        setPaginacion({
          count: total,
          page,
          totalPages,
          hasPrev: !!data.previous,
          hasNext: !!data.next,
        });
      } else if (Array.isArray(data)) {
        setCotizaciones(data);
        setPaginacion({ count: data.length, page: 1, totalPages: 1, hasPrev: false, hasNext: false });
      } else {
        setCotizaciones([]);
        setPaginacion({ count: 0, page: 1, totalPages: 1, hasPrev: false, hasNext: false });
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
  }, [filtros, toast]);

  useEffect(() => {
    cargarCotizaciones(1);
  }, [filtros]); // eslint-disable-line react-hooks/exhaustive-deps

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
      cargarCotizaciones(paginacion.page);
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

  const handleConvertirVenta = async (cotizacionId) => {
    try {
      const result = await cotizacionesService.convertirVenta(cotizacionId);
      toast({
        title: 'Convertida a venta',
        description: result.message || `Venta ${result.venta_numero} creada exitosamente`,
        status: 'success',
        duration: 4000,
        isClosable: true,
      });
      if (result.venta_id) {
        navigate(`/app/ventas/${result.venta_id}`);
      } else {
        cargarCotizaciones(paginacion.page);
      }
    } catch (error) {
      const data = error.response?.data;
      if (data?.error === 'productos_faltantes' && data?.productos_faltantes?.length) {
        setModalProductos({
          isOpen: true,
          productos: data.productos_faltantes,
          moneda: data.moneda || 'PEN',
          cotizacionId: data.cotizacion_id || cotizacionId,
        });
        return;
      }
      toast({
        title: 'Error al convertir',
        description:
          data?.error ||
          data?.detail ||
          error.message,
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
        // Si era el último item de la página, retroceder una página
        const nuevaPagina =
          cotizaciones.length === 1 && paginacion.page > 1
            ? paginacion.page - 1
            : paginacion.page;
        cargarCotizaciones(nuevaPagina);
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
        <HStack spacing={2}>
          <Button
            leftIcon={<FaTools />}
            colorScheme="green"
            onClick={() => navigate('/app/cotizaciones/servicios/nueva')}
          >
            Nueva Cot. Servicios
          </Button>
          <Button
            leftIcon={<FaPlus />}
            colorScheme="blue"
            onClick={() => navigate('/app/cotizaciones/nueva')}
          >
            Nueva Cotización
          </Button>
        </HStack>
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
        <Box py={4}><TableSkeleton rows={6} columns={6} /></Box>
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
                    <HStack spacing={1}>
                      <Tooltip label="Exportar PDF" hasArrow>
                        <IconButton
                          icon={<FaFilePdf />}
                          size="sm"
                          variant="ghost"
                          colorScheme="red"
                          aria-label="Exportar PDF"
                          onClick={() => handleExportarPDF(cotizacion.id)}
                        />
                      </Tooltip>
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
                    </HStack>
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      )}

      {/* Paginación */}
      {!loading && paginacion.totalPages > 1 && (
        <Flex justify="space-between" align="center" mt={4} px={1}>
          <Text fontSize="sm" color="gray.500">
            Mostrando{' '}
            <b>
              {Math.min((paginacion.page - 1) * PAGE_SIZE + 1, paginacion.count)}–
              {Math.min(paginacion.page * PAGE_SIZE, paginacion.count)}
            </b>{' '}
            de <b>{paginacion.count}</b> cotizaciones
          </Text>
          <HStack spacing={1}>
            <IconButton
              icon={<FaChevronLeft />}
              size="sm"
              variant="outline"
              aria-label="Página anterior"
              isDisabled={!paginacion.hasPrev}
              onClick={() => cargarCotizaciones(paginacion.page - 1)}
            />
            {Array.from({ length: paginacion.totalPages }, (_, i) => i + 1)
              .filter(
                (p) =>
                  p === 1 ||
                  p === paginacion.totalPages ||
                  Math.abs(p - paginacion.page) <= 2
              )
              .reduce((acc, p, idx, arr) => {
                if (idx > 0 && p - arr[idx - 1] > 1) {
                  acc.push('…');
                }
                acc.push(p);
                return acc;
              }, [])
              .map((p, idx) =>
                p === '…' ? (
                  <Text key={`ellipsis-${idx}`} px={2} color="gray.400" fontSize="sm">
                    …
                  </Text>
                ) : (
                  <Button
                    key={p}
                    size="sm"
                    variant={p === paginacion.page ? 'solid' : 'outline'}
                    colorScheme={p === paginacion.page ? 'blue' : 'gray'}
                    minW="36px"
                    onClick={() => cargarCotizaciones(p)}
                  >
                    {p}
                  </Button>
                )
              )}
            <IconButton
              icon={<FaChevronRight />}
              size="sm"
              variant="outline"
              aria-label="Página siguiente"
              isDisabled={!paginacion.hasNext}
              onClick={() => cargarCotizaciones(paginacion.page + 1)}
            />
          </HStack>
        </Flex>
      )}

      <CrearProductosCotizacionModal
        isOpen={modalProductos.isOpen}
        onClose={() => setModalProductos((prev) => ({ ...prev, isOpen: false }))}
        productosFaltantes={modalProductos.productos}
        cotizacionId={modalProductos.cotizacionId}
        moneda={modalProductos.moneda}
        onConversionExitosa={(result) => {
          if (result?.venta_id) {
            navigate(`/app/ventas/${result.venta_id}`);
          } else {
            cargarCotizaciones();
          }
        }}
      />
    </Box>
  );
};

export default CotizacionList;

