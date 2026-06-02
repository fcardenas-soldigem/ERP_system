import React, { useState, useCallback } from 'react';
import { TableSkeleton } from '../common/SkeletonLoaders';
import {
  Box, Button, Table, Thead, Tbody, Tr, Th, Td,
  Badge, IconButton, Menu, MenuButton, MenuList, MenuItem,
  useToast, Flex, Heading, Input, Select, HStack, Text,
  Center, AlertDialog, AlertDialogOverlay, AlertDialogContent,
  AlertDialogHeader, AlertDialogBody, AlertDialogFooter,
  useDisclosure, Tooltip,
} from '@chakra-ui/react';
import {
  FaPlus, FaEllipsisV, FaEye, FaEdit, FaFilePdf, FaTrash,
  FaChevronLeft, FaChevronRight, FaExchangeAlt,
} from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { comprasService } from '../../services/compras.service';

const PAGE_SIZE = 20;

const ESTADO_CONFIG = {
  borrador:   { label: 'Borrador',   color: 'gray'   },
  enviada:    { label: 'Enviada',    color: 'blue'   },
  aprobada:   { label: 'Aprobada',   color: 'green'  },
  rechazada:  { label: 'Rechazada',  color: 'red'    },
  completada: { label: 'Completada', color: 'teal'   },
};

// Map from display value back to key for transitions
const ESTADO_KEY = (raw) => {
  if (!raw) return 'borrador';
  const lower = raw.toLowerCase();
  return ESTADO_CONFIG[lower] ? lower : lower;
};

const TRANSICIONES = {
  borrador:   ['enviada', 'aprobada'],
  enviada:    ['aprobada', 'rechazada'],
  aprobada:   ['completada', 'rechazada'],
  rechazada:  [],
  completada: [],
};

const formatCurrency = (amount) => {
  const n = parseFloat(amount) || 0;
  return new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(n);
};

const formatDate = (d) => {
  if (!d) return '—';
  try { return new Date(d).toLocaleDateString('es-PE', { day: '2-digit', month: '2-digit', year: 'numeric' }); }
  catch { return d; }
};

const EstadoBadge = ({ estado }) => {
  const key = ESTADO_KEY(estado);
  const cfg = ESTADO_CONFIG[key] ?? { label: estado, color: 'gray' };
  return <Badge colorScheme={cfg.color} borderRadius="full" px={3}>{cfg.label}</Badge>;
};

const OrdenesCompraList = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [filtros, setFiltros] = useState({ search: '', estado: '' });
  const [ordenToDelete, setOrdenToDelete] = useState(null);
  const { isOpen: isDeleteOpen, onOpen: onDeleteOpen, onClose: onDeleteClose } = useDisclosure();
  const cancelRef = React.useRef();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['ordenes-compra', page, filtros],
    queryFn: () => {
      const params = { page, page_size: PAGE_SIZE };
      if (filtros.estado) params.estado = filtros.estado;
      if (filtros.search) params.search = filtros.search;
      return comprasService.getOrdenes(params);
    },
    staleTime: 30_000,
    keepPreviousData: true,
  });

  const ordenes = data?.results ?? (Array.isArray(data) ? data : []);
  const totalCount = data?.count ?? ordenes.length;
  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));

  const cambiarEstadoMutation = useMutation({
    mutationFn: ({ id, estado }) => comprasService.cambiarEstadoOrden(id, estado),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ordenes-compra'] });
      toast({ title: 'Estado actualizado', status: 'success', duration: 3000 });
    },
    onError: (err) => toast({
      title: 'Error al cambiar estado',
      description: err.response?.data?.error ?? err.message,
      status: 'error', duration: 5000,
    }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => comprasService.deleteOrden(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ordenes-compra'] });
      toast({ title: 'Orden eliminada', status: 'success', duration: 3000 });
      onDeleteClose();
    },
    onError: (err) => toast({
      title: 'Error al eliminar',
      description: err.response?.data?.detail ?? err.message,
      status: 'error', duration: 5000,
    }),
  });

  const handleExportarPDF = async (orden) => {
    try {
      await comprasService.exportarPDFOrden(orden);
      toast({ title: 'PDF descargado', status: 'success', duration: 3000 });
    } catch (err) {
      toast({ title: 'Error al generar PDF', description: err.message, status: 'error', duration: 5000 });
    }
  };

  const confirmDelete = (orden) => {
    setOrdenToDelete(orden);
    onDeleteOpen();
  };

  const handleFiltroChange = (key, value) => {
    setFiltros(prev => ({ ...prev, [key]: value }));
    setPage(1);
  };

  const paginationPages = () => {
    return Array.from({ length: totalPages }, (_, i) => i + 1)
      .filter(p => p === 1 || p === totalPages || Math.abs(p - page) <= 2)
      .reduce((acc, p, idx, arr) => {
        if (idx > 0 && p - arr[idx - 1] > 1) acc.push('…');
        acc.push(p);
        return acc;
      }, []);
  };

  return (
    <Box p={6}>
      {/* Header */}
      <Flex justify="space-between" align="center" mb={6}>
        <Box>
          <Heading size="lg">Órdenes de Compra</Heading>
          <Text color="gray.500" fontSize="sm" mt={0.5}>
            Gestiona tus órdenes de compra a proveedores
          </Text>
        </Box>
        <Button
          leftIcon={<FaPlus />}
          colorScheme="blue"
          onClick={() => navigate('/app/compras/orden-compra/nueva')}
        >
          Nueva Orden
        </Button>
      </Flex>

      {/* Filtros */}
      <HStack spacing={4} mb={6} flexWrap="wrap">
        <Input
          placeholder="Buscar por número o proveedor..."
          value={filtros.search}
          onChange={(e) => handleFiltroChange('search', e.target.value)}
          maxW="360px"
        />
        <Select
          placeholder="Todos los estados"
          value={filtros.estado}
          onChange={(e) => handleFiltroChange('estado', e.target.value)}
          maxW="200px"
        >
          {Object.entries(ESTADO_CONFIG).map(([key, cfg]) => (
            <option key={key} value={key}>{cfg.label}</option>
          ))}
        </Select>
        {(filtros.search || filtros.estado) && (
          <Button size="sm" variant="ghost" onClick={() => { setFiltros({ search: '', estado: '' }); setPage(1); }}>
            Limpiar filtros
          </Button>
        )}
      </HStack>

      {/* Tabla */}
      {isLoading ? (
        <Box py={4}><TableSkeleton rows={8} columns={6} /></Box>
      ) : isError ? (
        <Box p={6} bg="red.50" borderRadius="lg" borderWidth={1} borderColor="red.200">
          <Text color="red.700" fontSize="sm">{error?.message ?? 'Error al cargar órdenes'}</Text>
          <Button mt={3} size="sm" colorScheme="blue" onClick={() => window.location.reload()}>Recargar</Button>
        </Box>
      ) : ordenes.length === 0 ? (
        <Center py={14} bg="gray.50" borderRadius="xl">
          <Box textAlign="center">
            <Text color="gray.400" mb={3}>No hay órdenes de compra</Text>
            <Button size="sm" colorScheme="blue" leftIcon={<FaPlus />}
              onClick={() => navigate('/app/compras/orden-compra/nueva')}>
              Crear primera orden
            </Button>
          </Box>
        </Center>
      ) : (
        <Box overflowX="auto" bg="white" borderRadius="lg" shadow="sm" border="1px solid" borderColor="gray.100">
          <Table variant="simple" size="sm">
            <Thead bg="gray.50">
              <Tr>
                <Th>Número</Th>
                <Th>Proveedor</Th>
                <Th>Fecha Emisión</Th>
                <Th>Fecha Entrega</Th>
                <Th>Estado</Th>
                <Th isNumeric>Total</Th>
                <Th w="48px"></Th>
              </Tr>
            </Thead>
            <Tbody>
              {ordenes.map((orden) => {
                const estadoKey = ESTADO_KEY(orden.estado);
                const transiciones = TRANSICIONES[estadoKey] ?? [];
                return (
                  <Tr
                    key={orden.id}
                    _hover={{ bg: 'gray.50' }}
                    cursor="pointer"
                  >
                    <Td
                      fontWeight="semibold"
                      color="blue.600"
                      onClick={() => navigate(`/app/compras/ordenes/${orden.id}`)}
                    >
                      OC-{orden.numero || orden.id}
                    </Td>
                    <Td
                      maxW="200px"
                      onClick={() => navigate(`/app/compras/ordenes/${orden.id}`)}
                    >
                      <Text noOfLines={1} title={orden.proveedor_nombre}>
                        {orden.proveedor_nombre || '—'}
                      </Text>
                    </Td>
                    <Td whiteSpace="nowrap" onClick={() => navigate(`/app/compras/ordenes/${orden.id}`)}>
                      {formatDate(orden.fecha_creacion)}
                    </Td>
                    <Td whiteSpace="nowrap" onClick={() => navigate(`/app/compras/ordenes/${orden.id}`)}>
                      {formatDate(orden.fecha_entrega)}
                    </Td>
                    <Td onClick={() => navigate(`/app/compras/ordenes/${orden.id}`)}>
                      <EstadoBadge estado={orden.estado} />
                    </Td>
                    <Td isNumeric fontWeight="semibold" whiteSpace="nowrap"
                      onClick={() => navigate(`/app/compras/ordenes/${orden.id}`)}>
                      {formatCurrency(orden.total)}
                    </Td>
                    <Td>
                      <HStack spacing={1}>
                        <Tooltip label="Exportar PDF" hasArrow>
                          <IconButton
                            icon={<FaFilePdf />}
                            size="xs"
                            variant="ghost"
                            colorScheme="red"
                            aria-label="Exportar PDF"
                            onClick={(e) => { e.stopPropagation(); handleExportarPDF(orden); }}
                          />
                        </Tooltip>
                      <Menu>
                        <MenuButton
                          as={IconButton}
                          icon={<FaEllipsisV />}
                          variant="ghost"
                          size="xs"
                          aria-label="Acciones"
                          onClick={(e) => e.stopPropagation()}
                        />
                        <MenuList fontSize="sm">
                          <MenuItem icon={<FaEye />}
                            onClick={() => navigate(`/app/compras/ordenes/${orden.id}`)}>
                            Ver Detalle
                          </MenuItem>
                          {estadoKey === 'borrador' && (
                            <MenuItem icon={<FaEdit />}
                              onClick={() => navigate(`/app/compras/orden-compra/${orden.id}/editar`)}>
                              Editar
                            </MenuItem>
                          )}
                          <MenuItem icon={<FaFilePdf />} onClick={() => handleExportarPDF(orden)}>
                            Exportar PDF
                          </MenuItem>
                          {transiciones.map((est) => (
                            <MenuItem key={est} icon={<FaExchangeAlt />}
                              onClick={() => cambiarEstadoMutation.mutate({ id: orden.id, estado: est })}>
                              Marcar como {ESTADO_CONFIG[est]?.label ?? est}
                            </MenuItem>
                          ))}
                          {estadoKey === 'borrador' && (
                            <MenuItem icon={<FaTrash />} color="red.500"
                              onClick={() => confirmDelete(orden)}>
                              Eliminar
                            </MenuItem>
                          )}
                        </MenuList>
                      </Menu>
                      </HStack>
                    </Td>
                  </Tr>
                );
              })}
            </Tbody>
          </Table>
        </Box>
      )}

      {/* Paginación */}
      {!isLoading && totalPages > 1 && (
        <Flex justify="space-between" align="center" mt={4} px={1}>
          <Text fontSize="sm" color="gray.500">
            Mostrando{' '}
            <b>{Math.min((page - 1) * PAGE_SIZE + 1, totalCount)}–{Math.min(page * PAGE_SIZE, totalCount)}</b>{' '}
            de <b>{totalCount}</b> órdenes
          </Text>
          <HStack spacing={1}>
            <IconButton icon={<FaChevronLeft />} size="sm" variant="outline"
              aria-label="Anterior" isDisabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))} />
            {paginationPages().map((p, idx) =>
              p === '…' ? (
                <Text key={`el-${idx}`} px={2} color="gray.400" fontSize="sm">…</Text>
              ) : (
                <Button key={p} size="sm"
                  variant={p === page ? 'solid' : 'outline'}
                  colorScheme={p === page ? 'blue' : 'gray'}
                  minW="36px"
                  onClick={() => setPage(p)}>
                  {p}
                </Button>
              )
            )}
            <IconButton icon={<FaChevronRight />} size="sm" variant="outline"
              aria-label="Siguiente" isDisabled={page >= totalPages} onClick={() => setPage(p => Math.min(totalPages, p + 1))} />
          </HStack>
        </Flex>
      )}

      {/* Confirm delete dialog */}
      <AlertDialog isOpen={isDeleteOpen} leastDestructiveRef={cancelRef} onClose={onDeleteClose} isCentered>
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader>Eliminar Orden de Compra</AlertDialogHeader>
            <AlertDialogBody>
              ¿Eliminar <strong>OC-{ordenToDelete?.numero}</strong> de {ordenToDelete?.proveedor_nombre}? Esta acción no se puede deshacer.
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={onDeleteClose}>Cancelar</Button>
              <Button colorScheme="red" ml={3} isLoading={deleteMutation.isPending}
                onClick={() => deleteMutation.mutate(ordenToDelete?.id)}>
                Eliminar
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </Box>
  );
};

export default OrdenesCompraList;
