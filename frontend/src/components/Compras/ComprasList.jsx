import React, { useState, useCallback, useMemo } from 'react';
import { TableSkeleton } from '../common/SkeletonLoaders';
import { keyframes } from '@emotion/react';
import {
    Box, Heading, Text, Button, Flex, Table, Thead, Tbody, Tr, Th, Td,
    Menu, MenuButton, MenuList, MenuItem, IconButton, useToast, Badge,
    HStack, useDisclosure, Checkbox, Modal, ModalOverlay, ModalContent,
    ModalHeader, ModalBody, ModalFooter, ModalCloseButton, Divider,
    VStack, Spinner, Tooltip,
} from '@chakra-ui/react';
import {
    ChevronDownIcon, EditIcon, DeleteIcon, DownloadIcon, AddIcon,
    ViewIcon, CheckIcon, TimeIcon, CloseIcon,
} from '@chakra-ui/icons';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { comprasService } from '../../services/compras.service';
import { api } from '../../lib/api';
import ImportarCompras from './ImportarCompras';
import { useNavigate } from 'react-router-dom';
import { ESTADOS_DISPLAY, METODOS_PAGO_DISPLAY } from './constants';

// ── Slide-up animation for floating bar ──────────────────────────────────────
const slideUp = keyframes`
  from { transform: translateY(80px); opacity: 0; }
  to   { transform: translateY(0);    opacity: 1; }
`;

// ── Valid state transitions ───────────────────────────────────────────────────
const VALID_TRANSITIONS = {
    borrador:  new Set(['pendiente', 'pagada', 'anulada']),
    pendiente: new Set(['pagada', 'anulada']),
    pagada:    new Set(['anulada']),
    anulada:   new Set(),
};

const canTransition = (compras, targetEstado) =>
    compras.every(c => VALID_TRANSITIONS[c.estado]?.has(targetEstado));

// ── Helpers ───────────────────────────────────────────────────────────────────
const ESTADO_CONFIG = {
    borrador:  { label: 'Borrador',  color: 'gray'   },
    pendiente: { label: 'Pendiente', color: 'yellow'  },
    pagada:    { label: 'Pagada',    color: 'green'   },
    anulada:   { label: 'Anulada',   color: 'red'     },
};

const TABS = [
    { key: 'todas',    label: 'Todas'     },
    { key: 'borrador', label: 'Borrador'  },
    { key: 'pendiente',label: 'Pendiente' },
    { key: 'pagada',   label: 'Pagada'    },
    { key: 'anulada',  label: 'Anulada'   },
];

const formatCurrency = (amount, moneda = 'PEN') => {
    const formatters = {
        PEN: new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }),
        USD: new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }),
    };
    return formatters[moneda]?.format(amount) ?? `${moneda} ${Number(amount).toFixed(2)}`;
};

const formatDate = (dateString) => {
    if (!dateString) return '';
    try { return format(new Date(dateString), 'dd/MM/yyyy', { locale: es }); }
    catch { return dateString; }
};

// ── EstadoBadge ───────────────────────────────────────────────────────────────
const EstadoBadge = ({ estado }) => {
    const cfg = ESTADO_CONFIG[estado?.toLowerCase()] ?? { label: estado, color: 'gray' };
    return <Badge colorScheme={cfg.color}>{cfg.label}</Badge>;
};

// ── StatusTabs ────────────────────────────────────────────────────────────────
const StatusTabs = ({ active, counts, onSelect }) => (
    <HStack spacing={2} mb={4} flexWrap="wrap">
        {TABS.map(tab => {
            const count = tab.key === 'todas' ? counts.todas : (counts[tab.key] ?? 0);
            const isActive = active === tab.key;
            return (
                <Button
                    key={tab.key}
                    size="sm"
                    borderRadius="full"
                    px={4}
                    fontWeight={isActive ? 'semibold' : 'normal'}
                    bg={isActive ? 'blue.500' : 'gray.100'}
                    color={isActive ? 'white' : 'gray.600'}
                    _hover={{ bg: isActive ? 'blue.600' : 'gray.200' }}
                    onClick={() => onSelect(tab.key)}
                >
                    {tab.label}
                    <Box
                        as="span"
                        ml={1.5}
                        px={1.5}
                        py={0.5}
                        bg={isActive ? 'blue.600' : 'gray.200'}
                        color={isActive ? 'white' : 'gray.500'}
                        borderRadius="full"
                        fontSize="10px"
                        lineHeight="1.4"
                    >
                        {count}
                    </Box>
                </Button>
            );
        })}
    </HStack>
);

// ── FloatingActionBar ─────────────────────────────────────────────────────────
const FloatingActionBar = ({ count, onMarkPagada, onMarkPendiente, onCancel, isLoading }) => (
    <Box
        position="fixed"
        bottom={6}
        left="50%"
        transform="translateX(-50%)"
        zIndex={100}
        bg="white"
        borderRadius="xl"
        boxShadow="0 8px 32px rgba(0,0,0,0.18)"
        border="1px solid"
        borderColor="gray.100"
        px={6}
        py={4}
        animation={`${slideUp} 0.22s ease`}
        w={{ base: 'calc(100vw - 32px)', md: 'auto' }}
    >
        <Flex align="center" gap={4} flexWrap="wrap" justify="center">
            <Text fontWeight="semibold" color="gray.700" whiteSpace="nowrap">
                {count} compra{count !== 1 ? 's' : ''} seleccionada{count !== 1 ? 's' : ''}
            </Text>
            <Divider orientation="vertical" h="24px" />
            <Button
                leftIcon={<CheckIcon />}
                colorScheme="blue"
                size="sm"
                onClick={() => onMarkPagada('pagada')}
                isLoading={isLoading === 'pagada'}
                loadingText="Procesando..."
            >
                Marcar como Pagada
            </Button>
            <Button
                leftIcon={<TimeIcon />}
                colorScheme="yellow"
                size="sm"
                onClick={() => onMarkPendiente('pendiente')}
                isLoading={isLoading === 'pendiente'}
                loadingText="Procesando..."
            >
                Marcar como Pendiente
            </Button>
            <Button
                leftIcon={<CloseIcon boxSize={2.5} />}
                variant="ghost"
                size="sm"
                onClick={onCancel}
            >
                Cancelar
            </Button>
        </Flex>
    </Box>
);

// ── ConfirmModal ──────────────────────────────────────────────────────────────
const ConfirmModal = ({ isOpen, onClose, compras, targetEstado, onConfirm, isLoading }) => {
    const LABELS = { pagada: 'Pagada', pendiente: 'Pendiente', anulada: 'Anulada' };
    const visible = compras.slice(0, 5);
    const extras  = compras.length - visible.length;

    return (
        <Modal isOpen={isOpen} onClose={onClose} isCentered size="md">
            <ModalOverlay bg="blackAlpha.400" backdropFilter="blur(2px)" />
            <ModalContent borderRadius="xl" mx={4}>
                <ModalHeader fontSize="lg" fontWeight="semibold" pb={2}>
                    Confirmar cambio de estado
                </ModalHeader>
                <ModalCloseButton />
                <Divider />
                <ModalBody py={5}>
                    <Text color="gray.600" mb={4} fontSize="sm">
                        Vas a marcar <strong>{compras.length}</strong> compra{compras.length !== 1 ? 's' : ''} como{' '}
                        <Badge colorScheme={targetEstado === 'pagada' ? 'green' : 'yellow'}>
                            {LABELS[targetEstado]}
                        </Badge>.
                        Esta acción actualizará el estado de las siguientes compras:
                    </Text>
                    <VStack align="stretch" spacing={2} maxH="200px" overflowY="auto">
                        {visible.map(c => (
                            <Flex
                                key={c.id}
                                justify="space-between"
                                align="center"
                                p={2}
                                bg="gray.50"
                                borderRadius="md"
                                fontSize="sm"
                            >
                                <HStack>
                                    <Text fontWeight="medium" color="gray.700">{c.numero}</Text>
                                    <Text color="gray.500" noOfLines={1}>{c.proveedor_nombre}</Text>
                                </HStack>
                                <Text fontWeight="medium" color="gray.700">
                                    {formatCurrency(c.total, c.moneda)}
                                </Text>
                            </Flex>
                        ))}
                        {extras > 0 && (
                            <Text fontSize="xs" color="gray.400" textAlign="center" pt={1}>
                                + {extras} compra{extras !== 1 ? 's' : ''} más
                            </Text>
                        )}
                    </VStack>
                </ModalBody>
                <Divider />
                <ModalFooter gap={3}>
                    <Button variant="ghost" onClick={onClose} isDisabled={isLoading}>
                        Cancelar
                    </Button>
                    <Button
                        colorScheme="blue"
                        onClick={onConfirm}
                        isLoading={isLoading}
                        loadingText="Guardando..."
                    >
                        Confirmar
                    </Button>
                </ModalFooter>
            </ModalContent>
        </Modal>
    );
};

// ── ComprasList ───────────────────────────────────────────────────────────────
const ComprasList = () => {
    const toast        = useToast();
    const queryClient  = useQueryClient();
    const navigate     = useNavigate();
    const { isOpen: isImportOpen, onOpen: onImportOpen, onClose: onImportClose } = useDisclosure();

    const [page, setPage]               = useState(1);
    const [filtroEstado, setFiltroEstado] = useState('todas');
    const [selectedIds, setSelectedIds] = useState(new Set());
    const [targetEstado, setTargetEstado] = useState(null);   // 'pagada' | 'pendiente'
    const [bulkLoading, setBulkLoading] = useState(null);     // 'pagada' | 'pendiente' | null
    const { isOpen: isConfirmOpen, onOpen: onConfirmOpen, onClose: onConfirmClose } = useDisclosure();

    const pageSize = 20;

    // ── Data ──────────────────────────────────────────────────────────────────
    const { data: comprasData, isLoading, isError, error } = useQuery({
        queryKey: ['compras', page, pageSize, filtroEstado],
        queryFn: async () => {
            const empresaId = localStorage.getItem('empresa_id');
            const params = { page, page_size: pageSize, empresa: empresaId };
            if (filtroEstado !== 'todas') params.estado = filtroEstado;
            const res = await api.get('/api/compras/compras/', { params });
            return res.data;
        },
        staleTime: 30_000,
    });

    // Count all states (always fetches all for badge counts)
    const { data: counts = { todas: 0, borrador: 0, pendiente: 0, pagada: 0, anulada: 0 } } = useQuery({
        queryKey: ['compras-counts'],
        queryFn: comprasService.getCountByEstado,
        staleTime: 60_000,
    });

    const compras = comprasData?.results ?? [];

    // ── Selection ─────────────────────────────────────────────────────────────
    const allPageIds   = useMemo(() => new Set(compras.map(c => c.id)), [compras]);
    const allSelected  = allPageIds.size > 0 && [...allPageIds].every(id => selectedIds.has(id));
    const someSelected = [...allPageIds].some(id => selectedIds.has(id)) && !allSelected;

    const toggleAll = useCallback(() => {
        setSelectedIds(prev => {
            const next = new Set(prev);
            if (allSelected) { allPageIds.forEach(id => next.delete(id)); }
            else             { allPageIds.forEach(id => next.add(id));    }
            return next;
        });
    }, [allSelected, allPageIds]);

    const toggleOne = useCallback((id) => {
        setSelectedIds(prev => {
            const next = new Set(prev);
            next.has(id) ? next.delete(id) : next.add(id);
            return next;
        });
    }, []);

    const clearSelection = () => setSelectedIds(new Set());

    // ── Selected compras objects (for modal) ──────────────────────────────────
    const selectedCompras = useMemo(
        () => compras.filter(c => selectedIds.has(c.id)),
        [compras, selectedIds]
    );

    // ── Bulk mutation ─────────────────────────────────────────────────────────
    const bulkMutation = useMutation({
        mutationFn: ({ ids, estado }) => comprasService.bulkCambiarEstado(ids, estado),
        onSuccess: (data) => {
            queryClient.invalidateQueries(['compras']);
            queryClient.invalidateQueries(['compras-counts']);
            clearSelection();
            onConfirmClose();
            toast({
                title: `${data.actualizadas} compra${data.actualizadas !== 1 ? 's' : ''} actualizada${data.actualizadas !== 1 ? 's' : ''}`,
                description: data.errores?.length
                    ? `${data.errores.length} compra(s) no pudieron cambiar de estado.`
                    : 'Estado actualizado correctamente.',
                status: data.errores?.length ? 'warning' : 'success',
                duration: 4000,
                isClosable: true,
            });
        },
        onError: (err) => {
            toast({
                title: 'Error al cambiar estados',
                description: err.response?.data?.detail ?? err.message,
                status: 'error',
                duration: 6000,
                isClosable: true,
            });
        },
    });

    const openConfirm = (estado) => {
        setTargetEstado(estado);
        onConfirmOpen();
    };

    const handleConfirm = () => {
        bulkMutation.mutate({ ids: [...selectedIds], estado: targetEstado });
    };

    // ── Per-row quick state change ────────────────────────────────────────────
    const handleEstadoRapido = async (compra, nuevoEstado) => {
        try {
            await comprasService.bulkCambiarEstado([compra.id], nuevoEstado);
            queryClient.invalidateQueries(['compras']);
            queryClient.invalidateQueries(['compras-counts']);
            toast({
                title: 'Estado actualizado',
                description: `${compra.numero} → ${ESTADO_CONFIG[nuevoEstado]?.label}`,
                status: 'success', duration: 3000,
            });
        } catch (err) {
            toast({
                title: 'Error',
                description: err.response?.data?.detail ?? err.message,
                status: 'error', duration: 5000,
            });
        }
    };

    const handleAnular = async (id) => {
        try {
            await comprasService.cambiarEstado(id, 'anulada');
            queryClient.invalidateQueries(['compras']);
            queryClient.invalidateQueries(['compras-counts']);
            toast({ title: 'Compra anulada', status: 'success', duration: 3000 });
        } catch (err) {
            toast({ title: 'Error al anular', description: err.message, status: 'error', duration: 5000 });
        }
    };

    const handleExportarPDF = async (compra) => {
        try {
            const response = await api.get(`/api/compras/compras/${compra.id}/exportar-pdf/`, { responseType: 'blob' });
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `OC_${compra.numero}.pdf`);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch (err) {
            toast({ title: 'Error al exportar PDF', description: err.response?.data?.error ?? err.message, status: 'error', duration: 5000 });
        }
    };

    // ── Filter change → reset selection + page ────────────────────────────────
    const handleFiltroChange = (key) => {
        setFiltroEstado(key);
        setPage(1);
        clearSelection();
    };

    // ── Render ────────────────────────────────────────────────────────────────
    return (
        <Box p={4} pb={selectedIds.size > 0 ? 32 : 4}>

            {/* ── Header ─────────────────────────────────────────────────── */}
            <Flex justify="space-between" align="flex-start" mb={6} flexWrap="wrap" gap={4}>
                <Box>
                    <Heading size="lg">Facturas de compra</Heading>
                    <Text color="gray.500" fontSize="sm" mt={0.5}>
                        Registra compras y actualiza inventario automáticamente
                    </Text>
                </Box>
                <HStack spacing={3} flexShrink={0}>
                    <Menu>
                        <MenuButton as={Button} leftIcon={<AddIcon />} rightIcon={<ChevronDownIcon />} colorScheme="blue" size="sm">
                            Nueva Compra
                        </MenuButton>
                        <MenuList>
                            <MenuItem icon={<AddIcon />} onClick={() => navigate('/app/compras/nueva')}>Factura de Compra</MenuItem>
                            <MenuItem icon={<DownloadIcon />} onClick={() => navigate('/app/compras/orden-compra/nueva')}>Orden de Compra (OC)</MenuItem>
                        </MenuList>
                    </Menu>
                    <Button leftIcon={<DownloadIcon />} colorScheme="green" size="sm" onClick={() => comprasService.exportarExcel()}>
                        Excel
                    </Button>
                    <Button colorScheme="orange" size="sm" onClick={onImportOpen}>
                        Importar
                    </Button>
                </HStack>
            </Flex>

            {/* ── Status tabs ────────────────────────────────────────────── */}
            <StatusTabs active={filtroEstado} counts={counts} onSelect={handleFiltroChange} />

            {/* ── Table area ─────────────────────────────────────────────── */}
            {isLoading ? (
                <Box py={4}><TableSkeleton rows={8} columns={8} /></Box>
            ) : isError ? (
                <Box p={6} borderWidth={1} borderRadius="md" borderColor="red.200" bg="red.50">
                    <Heading size="md" color="red.600" mb={2}>Error al cargar las compras</Heading>
                    <Text color="red.700" fontSize="sm">{error?.message ?? 'Error desconocido'}</Text>
                    <Button mt={4} colorScheme="blue" size="sm" onClick={() => window.location.reload()}>Recargar</Button>
                </Box>
            ) : !compras.length ? (
                <Box p={10} textAlign="center" bg="gray.50" borderRadius="xl">
                    <Text color="gray.400" fontSize="sm">
                        {filtroEstado === 'todas'
                            ? 'No hay compras registradas'
                            : `No hay compras en estado "${ESTADO_CONFIG[filtroEstado]?.label ?? filtroEstado}"`}
                    </Text>
                </Box>
            ) : (
                <>
                    <Box overflowX="auto" borderRadius="lg" border="1px solid" borderColor="gray.100">
                        <Table variant="simple" size="sm">
                            <Thead bg="gray.50">
                                <Tr>
                                    <Th w="40px" px={3}>
                                        <Checkbox
                                            isChecked={allSelected}
                                            isIndeterminate={someSelected}
                                            onChange={toggleAll}
                                        />
                                    </Th>
                                    <Th>Número</Th>
                                    <Th>Proveedor</Th>
                                    <Th>Fecha</Th>
                                    <Th>Tipo</Th>
                                    <Th>Estado</Th>
                                    <Th>Pago</Th>
                                    <Th isNumeric>Total</Th>
                                    <Th w="60px"></Th>
                                </Tr>
                            </Thead>
                            <Tbody>
                                {compras.map(compra => {
                                    const isSelected = selectedIds.has(compra.id);
                                    return (
                                        <Tr
                                            key={compra.id}
                                            bg={isSelected ? 'blue.50' : 'white'}
                                            borderLeft={isSelected ? '3px solid' : '3px solid transparent'}
                                            borderLeftColor={isSelected ? 'blue.400' : 'transparent'}
                                            _hover={{ bg: isSelected ? 'blue.50' : 'gray.50' }}
                                            transition="background 0.12s"
                                        >
                                            <Td px={3}>
                                                <Checkbox
                                                    isChecked={isSelected}
                                                    onChange={() => toggleOne(compra.id)}
                                                />
                                            </Td>
                                            <Td fontWeight="medium" color="blue.600" cursor="pointer"
                                                onClick={() => navigate(`/app/compras/${compra.id}`)}>
                                                {compra.numero}
                                            </Td>
                                            <Td maxW="180px">
                                                <Text noOfLines={1} title={compra.proveedor_nombre}>{compra.proveedor_nombre}</Text>
                                            </Td>
                                            <Td whiteSpace="nowrap">{formatDate(compra.fecha_emision)}</Td>
                                            <Td>
                                                <Badge colorScheme={
                                                    compra.tipo_compra === 'contado' ? 'green'
                                                    : compra.tipo_compra === 'credito_30' ? 'orange'
                                                    : 'red'
                                                }>
                                                    {compra.tipo_compra === 'contado' ? 'Contado'
                                                     : compra.tipo_compra === 'credito_30' ? 'Crédito 30d'
                                                     : 'Crédito 60d'}
                                                </Badge>
                                            </Td>
                                            <Td><EstadoBadge estado={compra.estado} /></Td>
                                            <Td>
                                                <Badge colorScheme={
                                                    compra.metodo_pago === 'efectivo' ? 'green'
                                                    : compra.metodo_pago === 'transferencia' ? 'blue'
                                                    : compra.metodo_pago === 'cheque' ? 'purple'
                                                    : compra.metodo_pago === 'tarjeta' ? 'orange'
                                                    : 'gray'
                                                }>
                                                    {METODOS_PAGO_DISPLAY[compra.metodo_pago] ?? compra.metodo_pago}
                                                </Badge>
                                            </Td>
                                            <Td isNumeric fontWeight="semibold" whiteSpace="nowrap">
                                                {formatCurrency(compra.total, compra.moneda)}
                                            </Td>
                                            <Td>
                                                <HStack spacing={1}>
                                                <Tooltip label="Exportar PDF" hasArrow>
                                                    <IconButton
                                                        icon={<DownloadIcon />}
                                                        size="xs"
                                                        variant="ghost"
                                                        colorScheme="red"
                                                        aria-label="Exportar PDF"
                                                        onClick={() => handleExportarPDF(compra)}
                                                    />
                                                </Tooltip>
                                                <Menu>
                                                    <MenuButton
                                                        as={IconButton}
                                                        icon={<ChevronDownIcon />}
                                                        variant="ghost"
                                                        size="xs"
                                                    />
                                                    <MenuList fontSize="sm">
                                                        <MenuItem icon={<ViewIcon />} onClick={() => navigate(`/app/compras/${compra.id}`)}>
                                                            Ver Detalles
                                                        </MenuItem>
                                                        <MenuItem icon={<DownloadIcon />} onClick={() => handleExportarPDF(compra)}>
                                                            Exportar PDF
                                                        </MenuItem>
                                                        <MenuItem icon={<EditIcon />} onClick={() => navigate(`/app/compras/${compra.id}/editar`)}>
                                                            Editar
                                                        </MenuItem>
                                                        {/* ── Quick state transitions ── */}
                                                        {VALID_TRANSITIONS[compra.estado]?.has('pagada') && (
                                                            <MenuItem icon={<CheckIcon color="green.500" />}
                                                                onClick={() => handleEstadoRapido(compra, 'pagada')}>
                                                                Marcar como Pagada
                                                            </MenuItem>
                                                        )}
                                                        {VALID_TRANSITIONS[compra.estado]?.has('pendiente') && (
                                                            <MenuItem icon={<TimeIcon color="yellow.500" />}
                                                                onClick={() => handleEstadoRapido(compra, 'pendiente')}>
                                                                Marcar como Pendiente
                                                            </MenuItem>
                                                        )}
                                                        {compra.estado !== 'anulada' && (
                                                            <MenuItem icon={<DeleteIcon color="red.400" />}
                                                                onClick={() => handleAnular(compra.id)}
                                                                color="red.500">
                                                                Anular
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

                    {/* ── Pagination ───────────────────────────────────────── */}
                    <Flex justify="space-between" align="center" mt={4} flexWrap="wrap" gap={2}>
                        <Text fontSize="sm" color="gray.500">
                            {compras.length} de {comprasData?.count ?? 0} compras
                            {filtroEstado !== 'todas' && ` (filtro: ${ESTADO_CONFIG[filtroEstado]?.label})`}
                        </Text>
                        <HStack>
                            <Button size="sm" onClick={() => { setPage(p => Math.max(1, p - 1)); clearSelection(); }}
                                isDisabled={!comprasData?.previous}>
                                Anterior
                            </Button>
                            <Text fontSize="sm" color="gray.500">Pág. {page}</Text>
                            <Button size="sm" onClick={() => { setPage(p => p + 1); clearSelection(); }}
                                isDisabled={!comprasData?.next}>
                                Siguiente
                            </Button>
                        </HStack>
                    </Flex>
                </>
            )}

            {/* ── Floating action bar ─────────────────────────────────────── */}
            {selectedIds.size > 0 && (
                <FloatingActionBar
                    count={selectedIds.size}
                    onMarkPagada={() => openConfirm('pagada')}
                    onMarkPendiente={() => openConfirm('pendiente')}
                    onCancel={clearSelection}
                    isLoading={bulkMutation.isPending ? targetEstado : null}
                />
            )}

            {/* ── Confirm modal ───────────────────────────────────────────── */}
            <ConfirmModal
                isOpen={isConfirmOpen}
                onClose={onConfirmClose}
                compras={selectedCompras}
                targetEstado={targetEstado}
                onConfirm={handleConfirm}
                isLoading={bulkMutation.isPending}
            />

            {/* ── Import modal ────────────────────────────────────────────── */}
            <ImportarCompras isOpen={isImportOpen} onClose={onImportClose} />
        </Box>
    );
};

export default ComprasList;
