import React, { useState } from 'react';
import {
  Box,
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
  Button,
  useDisclosure,
  Spinner,
  Flex,
  Text,
  Tooltip
} from '@chakra-ui/react';
import { ChevronDownIcon, EditIcon, DeleteIcon, DownloadIcon, AddIcon, ViewIcon, ChevronLeftIcon, ChevronRightIcon, InfoIcon } from '@chakra-ui/icons';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ventasService } from '../../services/ventas.service';
import ImportExcelModal from '../common/ImportExcelModal';
import { useNavigate } from 'react-router-dom';
import { ESTADOS_VENTA, TIPOS_VENTA, METODOS_PAGO, ESTADOS_DISPLAY, TIPOS_VENTA_DISPLAY, METODOS_PAGO_DISPLAY } from './constants';

// Constantes para colores de badges
const ESTADOS_BADGE_COLORS = {
  [ESTADOS_VENTA.BORRADOR]: 'gray',
  [ESTADOS_VENTA.PENDIENTE]: 'yellow',
  [ESTADOS_VENTA.PAGADO]: 'green',
  [ESTADOS_VENTA.ANULADO]: 'red'
};

const TIPOS_VENTA_BADGE_COLORS = {
  [TIPOS_VENTA.CONTADO]: 'green',
  [TIPOS_VENTA.CREDITO_30]: 'orange',
  [TIPOS_VENTA.CREDITO_60]: 'red'
};

const METODOS_PAGO_BADGE_COLORS = {
  [METODOS_PAGO.EFECTIVO]: 'green',
  [METODOS_PAGO.TRANSFERENCIA]: 'blue',
  [METODOS_PAGO.CHEQUE]: 'purple',
  [METODOS_PAGO.TARJETA]: 'orange'
};

const VentaList = () => {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // Consulta para obtener las ventas
  const { data: ventas, isLoading, error } = useQuery({
    queryKey: ['ventas', page, pageSize],
    queryFn: () => ventasService.getVentas(page, pageSize),
    onSuccess: (data) => {
      console.log('Datos de ventas recibidos:', data);
    }
  });

  // Mutación para cambiar el estado de una venta
  const cambiarEstadoMutation = useMutation({
    mutationFn: ({ numero, nuevoEstado }) => ventasService.cambiarEstado(numero, nuevoEstado),
    onSuccess: (data) => {
      queryClient.invalidateQueries(['ventas']);
      toast({
        title: 'Estado actualizado',
        description: `La venta se ha actualizado a estado: ${ESTADOS_DISPLAY[data.estado]}`,
        status: 'success',
        duration: 3000,
      });
    },
    onError: (error) => {
      console.error('Error al cambiar estado:', error);
      toast({
        title: 'Error al actualizar estado',
        description: error.response?.data?.error || 'Ocurrió un error al actualizar el estado de la venta',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    },
  });

  // Mutación para eliminar una venta
  const eliminarVentaMutation = useMutation({
    mutationFn: (id) => ventasService.deleteVenta(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['ventas']);
      toast({
        title: 'Venta eliminada',
        description: 'La venta se ha eliminado correctamente',
        status: 'success',
        duration: 3000,
      });
    },
    onError: (error) => {
      console.error('Error al eliminar venta:', error);
      toast({
        title: 'Error al eliminar',
        description: error.message || 'No se pudo eliminar la venta',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    },
  });

  // Mutación para crear una venta
  const crearVentaMutation = useMutation({
    mutationFn: (ventaData) => ventasService.crearVenta(ventaData),
    onSuccess: (data) => {
      queryClient.invalidateQueries(['ventas']);
      toast({
        title: 'Venta creada',
        description: 'La venta se ha creado exitosamente',
        status: 'success',
        duration: 3000,
      });
      
      // Si es una venta a crédito, redirigir al módulo de pagos
      if (data.esCredito) {
        navigate(`/ventas/${data.id}/pagos`);
      } else {
        navigate('/ventas');
      }
    },
    onError: (error) => {
      toast({
        title: 'Error al crear venta',
        description: error.message || 'Ocurrió un error al crear la venta',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    },
  });

  // Manejador para cambio de estado
  const handleEstadoChange = async (numero, nuevoEstado) => {
    try {
      await cambiarEstadoMutation.mutateAsync({ numero, nuevoEstado });
    } catch (error) {
      console.error('Error en handleEstadoChange:', error);
    }
  };

  // Manejador para eliminar venta
  const handleEliminarVenta = async (id) => {
    if (!id) {
      toast({
        title: 'Error',
        description: 'No se pudo identificar la venta a eliminar',
        status: 'error',
        duration: 3000,
      });
      return;
    }
    
    if (window.confirm('¿Está seguro de que desea eliminar esta venta?')) {
      try {
        await eliminarVentaMutation.mutateAsync(id);
      } catch (error) {
        console.error('Error en handleEliminarVenta:', error);
      }
    }
  };

  const formatCurrency = (amount, moneda = 'PEN') => {
    return new Intl.NumberFormat('es-PE', {
      style: 'currency',
      currency: moneda
    }).format(amount || 0);
  };

  const formatDate = (dateString) => {
    return format(new Date(dateString), 'dd/MM/yyyy', { locale: es });
  };

  const getEstadoBadge = (estado) => {
    return (
      <Badge colorScheme={ESTADOS_BADGE_COLORS[estado]} variant="solid">
        {ESTADOS_DISPLAY[estado]}
      </Badge>
    );
  };

  const getTipoVentaBadge = (tipoVenta) => {
    return (
      <Badge colorScheme={TIPOS_VENTA_BADGE_COLORS[tipoVenta]} variant="solid">
        {TIPOS_VENTA_DISPLAY[tipoVenta]}
      </Badge>
    );
  };

  const getMetodoPagoBadge = (metodoPago) => {
    return (
      <Badge colorScheme={METODOS_PAGO_BADGE_COLORS[metodoPago]} variant="solid">
        {METODOS_PAGO_DISPLAY[metodoPago]}
      </Badge>
    );
  };

  const getFechaVencimientoDisplay = (venta) => {
    if (!venta.fecha_vencimiento) return null;
    
    const fechaVencimiento = new Date(venta.fecha_vencimiento);
    const hoy = new Date();
    const diasRestantes = Math.ceil((fechaVencimiento - hoy) / (1000 * 60 * 60 * 24));
    
    let color = 'gray';
    if (diasRestantes < 0) color = 'red';
    else if (diasRestantes <= 5) color = 'orange';
    else if (diasRestantes <= 15) color = 'yellow';
    else color = 'green';

    return (
      <Tooltip label={`Vence el ${format(fechaVencimiento, 'dd/MM/yyyy')}`}>
        <Badge colorScheme={color} variant="outline">
          {diasRestantes < 0 
            ? `Vencido hace ${Math.abs(diasRestantes)} días`
            : `${diasRestantes} días restantes`}
        </Badge>
      </Tooltip>
    );
  };

  const handleRegistrarPago = (venta) => {
    if (venta.metodo_pago === 'credito') {
        // Si es venta a crédito, redirigir a cuentas por cobrar
        navigate('/cuentas/por-cobrar');
        toast({
            title: 'Venta a Crédito',
            description: 'Los pagos de ventas a crédito deben realizarse desde el módulo de Cuentas por Cobrar',
            status: 'info',
            duration: 5000,
            isClosable: true
        });
        return;
    }
    // Si no es a crédito, proceder normalmente
    navigate(`/ventas/${venta.id}/pagos/nuevo`);
  };

  if (isLoading) {
    return <Box p={4} display="flex" justifyContent="center"><Spinner size="xl" /></Box>;
  }

  if (error) {
    return <Box p={4}>Error al cargar las ventas: {error.message}</Box>;
  }

  return (
    <Box>
      <HStack spacing={4} mb={4} justify="flex-end">
        <Button
          leftIcon={<AddIcon />}
          colorScheme="blue"
          onClick={() => navigate('/ventas/nueva')}
        >
          Nueva Venta
        </Button>
        <Button
          leftIcon={<DownloadIcon />}
          colorScheme="green"
          onClick={() => ventasService.exportarExcel()}
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

      <Table variant="simple">
        <Thead>
          <Tr>
            <Th>Número</Th>
            <Th>Cliente</Th>
            <Th>Fecha</Th>
            <Th>Tipo Venta</Th>
            <Th>Método Pago</Th>
            <Th>Estado</Th>
            <Th>Total</Th>
            <Th>Acciones</Th>
          </Tr>
        </Thead>
        <Tbody>
          {ventas?.results?.map((venta) => (
            <Tr key={venta.id}>
              <Td>{venta.numero}</Td>
              <Td>{venta.cliente_nombre}</Td>
              <Td>{formatDate(venta.fecha_emision)}</Td>
              <Td>{getTipoVentaBadge(venta.tipo_venta)}</Td>
              <Td>{getMetodoPagoBadge(venta.metodo_pago)}</Td>
              <Td>{getEstadoBadge(venta.estado)}</Td>
              <Td>{formatCurrency(venta.total, venta.moneda)}</Td>
              <Td>
                <Menu>
                  <MenuButton
                    as={IconButton}
                    icon={<ChevronDownIcon />}
                    variant="outline"
                    size="sm"
                  />
                  <MenuList>
                    <MenuItem icon={<ViewIcon />} onClick={() => navigate(`/ventas/${venta.id}`)}>
                      Ver Detalles
                    </MenuItem>
                    <MenuItem icon={<EditIcon />} onClick={() => navigate(`/ventas/${venta.id}/editar`)}>
                      Editar
                    </MenuItem>
                    {venta.tipo_venta !== 'contado' && venta.estado !== 'pagado' && (
                      <MenuItem icon={<AddIcon />} onClick={() => handleRegistrarPago(venta)}>
                        Registrar Pago
                      </MenuItem>
                    )}
                    {venta.estado !== 'anulado' && (
                      <MenuItem icon={<DeleteIcon />} onClick={() => handleEliminarVenta(venta.id)}>
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
          Mostrando {ventas?.results?.length || 0} de {ventas?.count || 0} ventas
        </Text>
        <HStack>
          <Button
            leftIcon={<ChevronLeftIcon />}
            onClick={() => setPage(page > 1 ? page - 1 : 1)}
            isDisabled={!ventas?.previous}
          >
            Anterior
          </Button>
          <Button
            rightIcon={<ChevronRightIcon />}
            onClick={() => setPage(page + 1)}
            isDisabled={!ventas?.next}
          >
            Siguiente
          </Button>
        </HStack>
      </Flex>

      <ImportExcelModal
        isOpen={isOpen}
        onClose={onClose}
        onImport={(file) => ventasService.importarExcel(file)}
        onSuccess={() => {
          queryClient.invalidateQueries(['ventas']);
          toast({
            title: 'Importación exitosa',
            status: 'success',
            duration: 3000,
          });
        }}
      />
    </Box>
  );
};

export default VentaList;