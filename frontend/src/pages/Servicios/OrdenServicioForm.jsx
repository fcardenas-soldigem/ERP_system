import React, { useState, useEffect, useRef, useCallback } from 'react';
import * as XLSX from 'xlsx';
import {
  Box, Button, Flex, Heading, HStack, VStack, Text, Input,
  Select, Textarea, FormControl, FormLabel, FormErrorMessage,
  IconButton, Badge, useToast, Card, CardBody,
  Grid, GridItem,
  NumberInput, NumberInputField, NumberInputStepper,
  NumberIncrementStepper, NumberDecrementStepper,
  Alert, AlertIcon, Table, Thead, Tbody, Tr, Th, Td,
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody,
  ModalFooter, ModalCloseButton, useDisclosure, Checkbox,
  Center, InputGroup, InputRightElement, Divider, SimpleGrid,
  Stat, StatLabel, StatNumber,
} from '@chakra-ui/react';
import {
  FaArrowLeft, FaArrowRight, FaCheck, FaPlus, FaTrash,
  FaFileExcel, FaClipboardList, FaDownload, FaSearch, FaTools,
  FaTruck,
} from 'react-icons/fa';
import { useNavigate, useParams } from 'react-router-dom';
import serviciosService from '../../services/serviciosService';
import api from '../../lib/api';

const today = () => new Date().toISOString().split('T')[0];
const addDays = (d, n) => {
  const dt = new Date(d + 'T00:00:00');
  dt.setDate(dt.getDate() + n);
  return dt.toISOString().split('T')[0];
};
const fmtFecha = (d) =>
  d ? new Date(d + 'T00:00:00').toLocaleDateString('es-PE', {
    day: '2-digit', month: 'short', year: 'numeric',
  }) : '—';

const ITEM_VACIO = {
  descripcion: '', numero_serie: '', marca: '', modelo: '',
  falla_cliente: '', estado_item: 'pendiente',
};

// ── Parsers (reutilizados de GuiaForm) ────────────────────────────────────────

const parseExcel = (file) => new Promise((resolve) => {
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const wb   = XLSX.read(e.target.result, { type: 'array' });
      const ws   = wb.Sheets[wb.SheetNames[0]];
      const data = XLSX.utils.sheet_to_json(ws, { defval: '' });
      const equipos = data.map((row, idx) => {
        const serie  = row['SERIE'] || row['serie'] || row['N_SERIE'] || row['S/N'] || '';
        const modelo = row['MODELO'] || row['modelo'] || row['MODEL'] || '';
        const marca  = row['MARCA'] || row['marca'] || '';
        const falla  = row['FALLA'] || row['ESTADO_INGRESO'] || row['Estado'] || row['falla'] || '';
        return {
          id_temp: idx,
          descripcion: String(modelo || serie || 'Equipo').trim(),
          numero_serie: String(serie).trim(),
          modelo: String(modelo).trim(),
          marca: String(marca).trim(),
          falla_cliente: String(falla).trim(),
          estado_item: 'pendiente',
          valido: serie !== '' || modelo !== '',
          seleccionado: true,
        };
      }).filter(r => r.valido);
      resolve(equipos);
    } catch { resolve([]); }
  };
  reader.readAsArrayBuffer(file);
});

const parseTSV = (text) => {
  const lines = text.trim().split('\n');
  if (lines.length < 2) return [];
  const headers = lines[0].split('\t').map(h => h.trim().toUpperCase());
  const idx = {
    serie:  headers.findIndex(h => ['SERIE', 'N_SERIE', 'S/N', 'SN'].includes(h)),
    modelo: headers.findIndex(h => ['MODELO', 'MODEL'].includes(h)),
    marca:  headers.findIndex(h => ['MARCA', 'BRAND'].includes(h)),
    falla:  headers.findIndex(h => ['FALLA', 'ESTADO_INGRESO', 'ESTADO'].includes(h)),
  };
  return lines.slice(1).filter(l => l.trim()).map((line, i) => {
    const cols   = line.split('\t').map(c => c.trim());
    const serie  = idx.serie >= 0 ? cols[idx.serie] : cols[0] || '';
    const modelo = idx.modelo >= 0 ? cols[idx.modelo] : cols[1] || '';
    return {
      id_temp: i,
      descripcion: String(modelo || serie || 'Equipo').trim(),
      numero_serie: serie, modelo,
      marca:        idx.marca >= 0 ? cols[idx.marca] : '',
      falla_cliente: idx.falla >= 0 ? cols[idx.falla] : '',
      estado_item: 'pendiente',
      valido: true, seleccionado: true,
    };
  });
};

const descargarPlantilla = () => {
  const header  = [['SERIE', 'MODELO', 'MARCA', 'FALLA']];
  const ejemplo = [
    ['SN-001', 'Laptop HP ProBook 450', 'HP', 'No enciende'],
    ['SN-002', 'MacBook Air M2', 'Apple', 'Pantalla dañada'],
  ];
  const wb = XLSX.utils.book_new();
  const ws = XLSX.utils.aoa_to_sheet([...header, ...ejemplo]);
  XLSX.utils.book_append_sheet(wb, ws, 'Equipos');
  XLSX.writeFile(wb, 'plantilla_equipos_os.xlsx');
};

// ── Stepper ───────────────────────────────────────────────────────────────────

const Stepper = ({ paso, pasos }) => (
  <HStack spacing={0} mb={6} align="center">
    {pasos.map((label, i) => {
      const n = i + 1;
      return (
        <React.Fragment key={n}>
          <Flex
            w="28px" h="28px" borderRadius="full" flexShrink={0}
            bg={paso > n ? 'green.500' : paso === n ? 'blue.500' : 'gray.200'}
            color="white" align="center" justify="center" fontSize="xs" fontWeight="bold"
          >
            {paso > n ? <FaCheck size={10} /> : n}
          </Flex>
          <Text
            fontSize="sm" fontWeight={paso === n ? 'semibold' : 'normal'}
            color={paso === n ? 'blue.600' : 'gray.500'} ml={2} mr={n < pasos.length ? 2 : 0}
            whiteSpace="nowrap"
          >
            {label}
          </Text>
          {n < pasos.length && (
            <Box flex="1" h="2px" bg={paso > n ? 'green.400' : 'gray.200'} mx={3} />
          )}
        </React.Fragment>
      );
    })}
  </HStack>
);

// ── Component ─────────────────────────────────────────────────────────────────

const OrdenServicioForm = () => {
  const { id }   = useParams();
  const navigate = useNavigate();
  const toast    = useToast();
  const isEdit   = Boolean(id);

  const [paso, setPaso]       = useState(1);
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving]   = useState(false);
  const [errors, setErrors]   = useState({});

  // Catálogos
  const [clientes, setClientes]     = useState([]);
  const [proveedores, setProveedores] = useState([]);
  const [guias, setGuias]           = useState([]);

  // Búsqueda de cliente
  const [busquedaCliente, setBusquedaCliente] = useState('');
  const [resultadosClientes, setResultadosClientes] = useState([]);
  const [mostrarResultados, setMostrarResultados]   = useState(false);
  const dropdownRef = useRef(null);

  // Importar desde guía
  const { isOpen: isGuiaOpen, onOpen: onGuiaOpen, onClose: onGuiaClose } = useDisclosure();
  const [guiaSeleccionadaData, setGuiaSeleccionadaData] = useState(null);

  // Importar Excel
  const fileInputRef = useRef(null);
  const [importPreview, setImportPreview] = useState([]);
  const [importLoading, setImportLoading] = useState(false);
  const { isOpen: isExcelOpen, onOpen: onExcelOpen, onClose: onExcelClose } = useDisclosure();

  // Pegar TSV
  const [tsvText, setTsvText] = useState('');
  const [tsvPreview, setTsvPreview] = useState([]);
  const { isOpen: isPasteOpen, onOpen: onPasteOpen, onClose: onPasteClose } = useDisclosure();

  // ── Datos del formulario ──────────────────────────────────────────────────
  const [datos, setDatos] = useState({
    cliente: '',
    proveedor_reparacion: '',
    prioridad: 'normal',
    fecha_ingreso: today(),
    fecha_entrega_estimada: addDays(today(), 30),
    guia_remision: '',
    notas_internas: '',
  });

  const [items, setItems] = useState([{ ...ITEM_VACIO }]);

  // ── Carga catálogos ───────────────────────────────────────────────────────
  useEffect(() => {
    Promise.allSettled([
      api.get('/api/ventas/clientes/', { params: { page_size: 500 } }),
      api.get('/api/compras/proveedores/', { params: { page_size: 200, activo: true } }),
      api.get('/api/guias/guias/', { params: { page_size: 100, estado: 'emitida' } }),
    ]).then(([cl, pv, gr]) => {
      if (cl.status === 'fulfilled')
        setClientes(cl.value.data?.results || cl.value.data || []);
      if (pv.status === 'fulfilled') {
        const lista = pv.value.data?.results || pv.value.data || [];
        setProveedores(lista);
      } else {
        toast({ title: 'No se pudieron cargar los proveedores', status: 'warning', duration: 4000, isClosable: true });
      }
      if (gr.status === 'fulfilled')
        setGuias(gr.value.data?.results || gr.value.data || []);
    });

    if (isEdit) {
      serviciosService.obtener(id).then(orden => {
        setDatos({
          cliente: orden.cliente ?? '',
          proveedor_reparacion: orden.proveedor_reparacion ?? '',
          prioridad: orden.prioridad ?? 'normal',
          fecha_ingreso: orden.fecha_ingreso ?? today(),
          fecha_entrega_estimada: orden.fecha_entrega_estimada ?? addDays(today(), 30),
          guia_remision: orden.guia_remision ?? '',
          notas_internas: orden.notas_internas ?? '',
        });
        if (orden.items?.length) {
          setItems(orden.items.map(i => ({
            descripcion:   i.descripcion   ?? '',
            numero_serie:  i.numero_serie  ?? '',
            marca:         i.marca         ?? '',
            modelo:        i.modelo        ?? '',
            falla_cliente: i.falla_cliente ?? '',
            estado_item:   i.estado_item   ?? 'pendiente',
          })));
        }
        setLoading(false);
      }).catch(() => { setLoading(false); navigate('/app/servicios'); });
    }
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Cerrar dropdown cliente al click afuera
  useEffect(() => {
    const h = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target))
        setMostrarResultados(false);
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);

  // ── Fecha estimada se actualiza si cambia ingreso ─────────────────────────
  useEffect(() => {
    if (datos.fecha_ingreso) {
      setDatos(d => ({ ...d, fecha_entrega_estimada: addDays(datos.fecha_ingreso, 30) }));
    }
  }, [datos.fecha_ingreso]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Cuando se selecciona guía, ofrecer importar equipos ──────────────────
  useEffect(() => {
    if (!datos.guia_remision) { setGuiaSeleccionadaData(null); return; }
    api.get(`/api/guias/guias/${datos.guia_remision}/`)
      .then(r => setGuiaSeleccionadaData(r.data))
      .catch(() => setGuiaSeleccionadaData(null));
  }, [datos.guia_remision]);

  // ── Búsqueda cliente ──────────────────────────────────────────────────────
  const handleBuscarCliente = useCallback((term) => {
    setBusquedaCliente(term);
    if (term.length >= 2) {
      const n = term.toLowerCase();
      setResultadosClientes(
        clientes.filter(c =>
          (c.nombre || '').toLowerCase().includes(n) || (c.documento || '').includes(n)
        ).slice(0, 8)
      );
      setMostrarResultados(true);
    } else {
      setResultadosClientes([]);
      setMostrarResultados(false);
    }
  }, [clientes]);

  const seleccionarCliente = (cl) => {
    setDatos(d => ({ ...d, cliente: cl.id }));
    const label = cl.nombre + (cl.documento ? ` (${cl.documento})` : '');
    setBusquedaCliente(label);
    setMostrarResultados(false);
  };

  // ── Validaciones ─────────────────────────────────────────────────────────
  const validarPaso1 = () => {
    const e = {};
    if (!datos.cliente)              e.cliente = 'Selecciona un cliente';
    if (!datos.proveedor_reparacion) e.proveedor_reparacion = 'Selecciona el proveedor';
    if (!datos.fecha_ingreso)        e.fecha_ingreso = 'Requerido';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const validarPaso2 = () => {
    const e = {};
    if (items.length === 0) e.items = 'Agrega al menos un equipo';
    items.forEach((item, i) => {
      if (!item.descripcion && !item.numero_serie && !item.modelo)
        e[`item_${i}`] = 'Completa serie, modelo o descripción';
    });
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleNext = (n) => {
    if (n === 2 && !validarPaso1()) return;
    if (n === 3 && !validarPaso2()) return;
    setPaso(n);
  };

  // ── Guardar ───────────────────────────────────────────────────────────────
  const handleSubmit = async () => {
    setSaving(true);
    try {
      const payload = {
        ...datos,
        cliente: datos.cliente || null,
        proveedor_reparacion: datos.proveedor_reparacion || null,
        guia_remision: datos.guia_remision || null,
        items: items.map((item, i) => ({
          ...item,
          numero_item: i + 1,
          descripcion: item.descripcion || item.modelo || item.numero_serie || `Equipo ${i + 1}`,
        })),
      };
      let orden;
      if (isEdit) {
        orden = await serviciosService.actualizar(id, payload);
        toast({ title: 'Orden actualizada', status: 'success', duration: 3000, isClosable: true });
      } else {
        orden = await serviciosService.crear(payload);
        toast({ title: `Orden ${orden.numero} creada`, status: 'success', duration: 3000, isClosable: true });
      }
      navigate(`/app/servicios/${orden.id}`);
    } catch (err) {
      const data = err.response?.data;
      toast({
        title: isEdit ? 'Error al actualizar' : 'Error al crear orden',
        description: data ? JSON.stringify(data).slice(0, 150) : err.message,
        status: 'error', duration: 5000, isClosable: true,
      });
    } finally { setSaving(false); }
  };

  // ── Gestión de items ──────────────────────────────────────────────────────
  const addItem    = () => setItems(prev => [...prev, { ...ITEM_VACIO }]);
  const removeItem = (i) => setItems(prev => prev.filter((_, idx) => idx !== i));
  const updateItem = (i, field, value) =>
    setItems(prev => prev.map((it, idx) => idx === i ? { ...it, [field]: value } : it));

  // ── Importar desde guía ───────────────────────────────────────────────────
  const handleImportarDeGuia = () => {
    if (!guiaSeleccionadaData?.items?.length) return;
    const nuevos = guiaSeleccionadaData.items.map(gi => ({
      descripcion:   gi.descripcion || gi.modelo || gi.serie || 'Equipo',
      numero_serie:  gi.serie    || '',
      marca:         gi.marca    || '',
      modelo:        gi.modelo   || '',
      falla_cliente: gi.estado_ingreso || '',
      estado_item:   'pendiente',
    }));
    setItems(nuevos);
    onGuiaClose();
    toast({
      title: `${nuevos.length} equipo(s) importados de ${guiaSeleccionadaData.numero}`,
      status: 'success', duration: 2500, isClosable: true,
    });
  };

  // ── Importar Excel ────────────────────────────────────────────────────────
  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImportLoading(true);
    const equipos = await parseExcel(file);
    setImportPreview(equipos);
    setImportLoading(false);
    e.target.value = '';
  };

  const handleImportarExcel = () => {
    const sel = importPreview.filter(e => e.seleccionado);
    const nuevos = sel.map(({ id_temp, valido, seleccionado, ...rest }) => rest);
    setItems(prev => {
      const base = prev.length === 1 && !prev[0].numero_serie && !prev[0].modelo ? [] : prev;
      return [...base, ...nuevos];
    });
    setImportPreview([]);
    onExcelClose();
    toast({ title: `${nuevos.length} equipo(s) importados`, status: 'success', duration: 2500, isClosable: true });
  };

  // ── Pegar TSV ─────────────────────────────────────────────────────────────
  const handleTsvChange = (text) => {
    setTsvText(text);
    setTsvPreview(text.includes('\t') ? parseTSV(text) : []);
  };

  const handlePasteConfirm = () => {
    const sel    = tsvPreview.filter(e => e.seleccionado);
    const nuevos = sel.map(({ id_temp, valido, seleccionado, ...rest }) => rest);
    setItems(prev => {
      const base = prev.length === 1 && !prev[0].numero_serie && !prev[0].modelo ? [] : prev;
      return [...base, ...nuevos];
    });
    setTsvText(''); setTsvPreview([]);
    onPasteClose();
    toast({ title: `${nuevos.length} equipo(s) agregados`, status: 'success', duration: 2500, isClosable: true });
  };

  const clienteSeleccionado = clientes.find(c => String(c.id) === String(datos.cliente));
  const proveedorSeleccionado = proveedores.find(p => String(p.id) === String(datos.proveedor_reparacion));

  if (loading) return null;

  return (
    <Box p={6}>
      {/* Header */}
      <Flex justify="space-between" align="center" mb={6}>
        <HStack spacing={3}>
          <Box p={2} bg="blue.50" borderRadius="lg">
            <FaTools size={16} color="var(--chakra-colors-blue-500)" />
          </Box>
          <Box>
            <Heading size="lg">{isEdit ? 'Editar Orden de Servicio' : 'Nueva Orden de Servicio'}</Heading>
            <Text fontSize="sm" color="gray.500">Paso {paso} de 3</Text>
          </Box>
        </HStack>
        <Button leftIcon={<FaArrowLeft />} variant="ghost" onClick={() => navigate('/app/servicios')}>
          Volver
        </Button>
      </Flex>

      {/* Stepper */}
      <Stepper paso={paso} pasos={['Datos Generales', 'Equipos', 'Confirmar']} />

      {/* ═══════════════════════════════════════════════════════════════════
          PASO 1 — Datos generales
      ═══════════════════════════════════════════════════════════════════ */}
      {paso === 1 && (
        <VStack spacing={5} align="stretch">

          {/* Cliente */}
          <Box bg="white" p={6} borderRadius="lg" shadow="sm">
            <Heading size="sm" mb={4} color="blue.600">Cliente y Proveedor</Heading>
            <Grid templateColumns={{ base: '1fr', md: 'repeat(2, 1fr)' }} gap={5}>

              <GridItem colSpan={{ base: 1, md: 2 }}>
                <FormControl isInvalid={!!errors.cliente}>
                  <FormLabel>Buscar cliente</FormLabel>
                  <Box position="relative" ref={dropdownRef}>
                    <InputGroup>
                      <Input
                        value={busquedaCliente}
                        onChange={(e) => handleBuscarCliente(e.target.value)}
                        placeholder="Nombre o RUC/DNI..."
                      />
                      <InputRightElement pointerEvents="none">
                        <FaSearch color="gray" size={12} />
                      </InputRightElement>
                    </InputGroup>
                    {mostrarResultados && (
                      <Box
                        position="absolute" top="100%" left={0} right={0} zIndex={1000}
                        bg="white" borderRadius="md" shadow="lg" border="1px solid" borderColor="gray.200" mt={1}
                      >
                        {resultadosClientes.length === 0 ? (
                          <Text py={2} px={3} fontSize="sm" color="gray.500">No se encontraron clientes</Text>
                        ) : (
                          resultadosClientes.map((c) => (
                            <Box key={c.id} py={2} px={3} cursor="pointer" _hover={{ bg: 'blue.50' }}
                              onClick={() => seleccionarCliente(c)}
                              borderBottom="1px solid" borderColor="gray.100" _last={{ borderBottom: 'none' }}>
                              <Flex justify="space-between" align="center">
                                <Text fontSize="sm" fontWeight="bold">{c.nombre}</Text>
                                <Badge colorScheme={c.tipo_documento === 'ruc' ? 'blue' : 'gray'} fontSize="xs">
                                  {(c.tipo_documento || 'doc').toUpperCase()}
                                </Badge>
                              </Flex>
                              <Text fontSize="xs" color="gray.500">{c.documento || 'Sin documento'}</Text>
                            </Box>
                          ))
                        )}
                      </Box>
                    )}
                  </Box>
                  {!datos.cliente && !busquedaCliente && (
                    <Select
                      mt={2} placeholder="O selecciona de la lista..."
                      onChange={(e) => {
                        const cl = clientes.find(c => String(c.id) === e.target.value);
                        if (cl) seleccionarCliente(cl);
                      }}
                    >
                      {clientes.map(c => (
                        <option key={c.id} value={c.id}>{c.nombre} — {c.documento}</option>
                      ))}
                    </Select>
                  )}
                  <FormErrorMessage>{errors.cliente}</FormErrorMessage>
                </FormControl>
              </GridItem>

              <FormControl isRequired isInvalid={!!errors.proveedor_reparacion}>
                <FormLabel>Proveedor de reparación</FormLabel>
                {proveedores.length === 0 ? (
                  <Alert status="warning" borderRadius="md" py={2} px={3} fontSize="sm">
                    <AlertIcon />
                    No hay proveedores registrados.{' '}
                    <Text as="span" color="blue.500" cursor="pointer" fontWeight="semibold"
                      onClick={() => navigate('/app/proveedores/nuevo')} ml={1}>
                      Crear uno primero →
                    </Text>
                  </Alert>
                ) : (
                  <Select
                    placeholder="Seleccionar proveedor..."
                    value={datos.proveedor_reparacion}
                    onChange={(e) => setDatos(d => ({ ...d, proveedor_reparacion: e.target.value }))}
                  >
                    {proveedores.map(p => (
                      <option key={p.id} value={p.id}>
                        {p.razon_social}{p.ruc ? ` — ${p.ruc}` : ''}
                      </option>
                    ))}
                  </Select>
                )}
                <FormErrorMessage>{errors.proveedor_reparacion}</FormErrorMessage>
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Prioridad</FormLabel>
                <Select
                  value={datos.prioridad}
                  onChange={(e) => setDatos(d => ({ ...d, prioridad: e.target.value }))}
                >
                  <option value="normal">Normal</option>
                  <option value="alta">Alta</option>
                  <option value="urgente">Urgente</option>
                </Select>
              </FormControl>
            </Grid>
          </Box>

          {/* Fechas y SLA */}
          <Box bg="white" p={6} borderRadius="lg" shadow="sm">
            <Heading size="sm" mb={4} color="blue.600">Fechas y SLA</Heading>
            <Grid templateColumns={{ base: '1fr', sm: 'repeat(2, 1fr)' }} gap={5}>
              <FormControl isRequired isInvalid={!!errors.fecha_ingreso}>
                <FormLabel>Fecha de ingreso del equipo</FormLabel>
                <Input
                  type="date"
                  value={datos.fecha_ingreso}
                  onChange={(e) => setDatos(d => ({ ...d, fecha_ingreso: e.target.value }))}
                />
                <FormErrorMessage>{errors.fecha_ingreso}</FormErrorMessage>
              </FormControl>
              <FormControl>
                <FormLabel>Fecha entrega estimada (SLA 30 días)</FormLabel>
                <Input
                  type="date"
                  value={datos.fecha_entrega_estimada}
                  onChange={(e) => setDatos(d => ({ ...d, fecha_entrega_estimada: e.target.value }))}
                />
              </FormControl>
            </Grid>
            {datos.fecha_entrega_estimada && (
              <HStack mt={3} p={2} bg="blue.50" borderRadius="md" spacing={2}>
                <Text fontSize="xs" color="blue.700">SLA:</Text>
                <Text fontSize="xs" fontWeight="bold" color="blue.700">
                  30 días — vence el {fmtFecha(datos.fecha_entrega_estimada)}
                </Text>
              </HStack>
            )}
          </Box>

          {/* Guía de remisión y notas */}
          <Box bg="white" p={6} borderRadius="lg" shadow="sm">
            <Heading size="sm" mb={4} color="blue.600">Opcional</Heading>
            <Grid templateColumns={{ base: '1fr', md: 'repeat(2, 1fr)' }} gap={5}>
              <FormControl>
                <FormLabel>Guía de remisión asociada</FormLabel>
                <Select
                  placeholder="Sin guía asociada"
                  value={datos.guia_remision}
                  onChange={(e) => setDatos(d => ({ ...d, guia_remision: e.target.value }))}
                >
                  {guias.map(g => (
                    <option key={g.id} value={g.id}>
                      {g.numero} — {g.cliente_nombre || g.nombre_destinatario}
                    </option>
                  ))}
                </Select>
                {guiaSeleccionadaData && (
                  <Alert status="info" mt={2} borderRadius="md" py={2} px={3} fontSize="sm">
                    <AlertIcon />
                    <Flex gap={2} align="center" flex="1" justify="space-between">
                      <Text>
                        Guía {guiaSeleccionadaData.numero} — {guiaSeleccionadaData.items?.length ?? 0} equipo(s)
                      </Text>
                      <Button
                        size="xs"
                        colorScheme="blue"
                        leftIcon={<FaTruck />}
                        onClick={onGuiaOpen}
                      >
                        Importar equipos
                      </Button>
                    </Flex>
                  </Alert>
                )}
              </FormControl>

              <FormControl>
                <FormLabel>Notas internas</FormLabel>
                <Textarea
                  value={datos.notas_internas}
                  onChange={(e) => setDatos(d => ({ ...d, notas_internas: e.target.value }))}
                  placeholder="Información relevante, instrucciones especiales..."
                  rows={3}
                />
              </FormControl>
            </Grid>
          </Box>
        </VStack>
      )}

      {/* ═══════════════════════════════════════════════════════════════════
          PASO 2 — Equipos
      ═══════════════════════════════════════════════════════════════════ */}
      {paso === 2 && (
        <Box bg="white" p={6} borderRadius="lg" shadow="sm">
          <Flex justify="space-between" align="center" mb={4}>
            <HStack spacing={3}>
              <Heading size="md">Equipos</Heading>
              <Badge colorScheme="purple" variant="subtle" fontSize="sm">{items.length}</Badge>
            </HStack>
            <HStack spacing={2} flexWrap="wrap">
              {guiaSeleccionadaData?.items?.length > 0 && (
                <Button size="sm" leftIcon={<FaTruck />} colorScheme="teal" variant="outline" onClick={onGuiaOpen}>
                  Importar de guía
                </Button>
              )}
              <Button size="sm" leftIcon={<FaPlus />} colorScheme="blue" variant="outline" onClick={addItem}>
                Agregar equipo
              </Button>
              <Button size="sm" leftIcon={<FaFileExcel />} colorScheme="green" variant="outline"
                onClick={() => { setImportPreview([]); onExcelOpen(); }}>
                Excel
              </Button>
              <Button size="sm" leftIcon={<FaClipboardList />} colorScheme="teal" variant="outline"
                onClick={() => { setTsvText(''); setTsvPreview([]); onPasteOpen(); }}>
                Pegar tabla
              </Button>
            </HStack>
          </Flex>

          {errors.items && (
            <Alert status="error" borderRadius="md" mb={3} py={2}>
              <AlertIcon />{errors.items}
            </Alert>
          )}

          {items.length === 0 ? (
            <Center py={10} flexDir="column" gap={3}>
              <Box fontSize="3xl" color="gray.300">🖥️</Box>
              <Text color="gray.400" fontSize="sm">Agrega equipos manualmente, importa desde Excel o pega tabla</Text>
              <Button size="sm" colorScheme="blue" leftIcon={<FaPlus />} onClick={addItem}>
                Agregar primer equipo
              </Button>
            </Center>
          ) : (
            <Box overflowX="auto">
              <Table size="sm" variant="simple">
                <Thead>
                  <Tr>
                    <Th w="32px" fontSize="xs">#</Th>
                    <Th fontSize="xs">N° Serie</Th>
                    <Th fontSize="xs">Modelo</Th>
                    <Th fontSize="xs">Marca</Th>
                    <Th fontSize="xs">Falla reportada por cliente</Th>
                    <Th w="32px"></Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {items.map((item, i) => (
                    <Tr key={i}>
                      <Td color="gray.400" fontSize="xs" fontWeight="bold">{i + 1}</Td>
                      <Td>
                        <Input size="sm" value={item.numero_serie}
                          onChange={(e) => { updateItem(i, 'numero_serie', e.target.value); updateItem(i, 'descripcion', e.target.value || item.modelo); }}
                          placeholder="SN-XXXX" fontFamily="mono" w="130px" />
                      </Td>
                      <Td>
                        <Input size="sm" value={item.modelo}
                          onChange={(e) => { updateItem(i, 'modelo', e.target.value); if (!item.numero_serie) updateItem(i, 'descripcion', e.target.value); }}
                          placeholder="Modelo" w="150px" />
                      </Td>
                      <Td>
                        <Input size="sm" value={item.marca}
                          onChange={(e) => updateItem(i, 'marca', e.target.value)}
                          placeholder="HP / Apple..." w="100px" />
                      </Td>
                      <Td>
                        <Input size="sm" value={item.falla_cliente}
                          onChange={(e) => updateItem(i, 'falla_cliente', e.target.value)}
                          placeholder="No enciende, pantalla rota..." w="260px" />
                      </Td>
                      <Td>
                        {items.length > 1 && (
                          <IconButton icon={<FaTrash />} size="sm" colorScheme="red" variant="ghost"
                            onClick={() => removeItem(i)} aria-label="Eliminar" />
                        )}
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </Box>
          )}
        </Box>
      )}

      {/* ═══════════════════════════════════════════════════════════════════
          PASO 3 — Resumen y confirmación
      ═══════════════════════════════════════════════════════════════════ */}
      {paso === 3 && (
        <VStack spacing={4} align="stretch">
          <Box bg="white" p={6} borderRadius="lg" shadow="sm">
            <Heading size="sm" mb={4} color="blue.600">Resumen de la Orden</Heading>
            <SimpleGrid columns={{ base: 1, sm: 2, md: 4 }} spacing={4} mb={4}>
              <Box>
                <Text fontSize="xs" color="gray.500" mb={0.5}>Cliente</Text>
                <Text fontWeight="semibold" fontSize="sm">
                  {clienteSeleccionado?.nombre || '—'}
                </Text>
              </Box>
              <Box>
                <Text fontSize="xs" color="gray.500" mb={0.5}>Proveedor reparación</Text>
                <Text fontWeight="semibold" fontSize="sm">
                  {proveedorSeleccionado?.razon_social || '—'}
                </Text>
              </Box>
              <Box>
                <Text fontSize="xs" color="gray.500" mb={0.5}>Prioridad</Text>
                <Badge
                  colorScheme={datos.prioridad === 'urgente' ? 'red' : datos.prioridad === 'alta' ? 'orange' : 'gray'}
                  variant={datos.prioridad === 'urgente' ? 'solid' : 'subtle'}
                >
                  {datos.prioridad?.toUpperCase()}
                </Badge>
              </Box>
              <Box>
                <Text fontSize="xs" color="gray.500" mb={0.5}>Equipos</Text>
                <Badge colorScheme="purple" variant="subtle" fontSize="md" px={2}>
                  {items.length}
                </Badge>
              </Box>
            </SimpleGrid>
            <Divider mb={4} />

            {/* SLA indicator */}
            <Box p={3} bg="blue.50" borderRadius="md" mb={4}>
              <HStack spacing={2}>
                <Text fontSize="sm" fontWeight="bold" color="blue.700">SLA:</Text>
                <Text fontSize="sm" color="blue.700">30 días</Text>
                <Text fontSize="sm" color="blue.500">—</Text>
                <Text fontSize="sm" fontWeight="bold" color="blue.700">
                  Vence el {fmtFecha(datos.fecha_entrega_estimada)}
                </Text>
              </HStack>
            </Box>

            {/* Lista de equipos */}
            <Heading size="xs" color="gray.600" mb={2}>Equipos a reparar</Heading>
            <VStack align="stretch" spacing={1}>
              {items.map((item, i) => (
                <Flex key={i} p={2} bg="gray.50" borderRadius="md" align="center" gap={3}>
                  <Badge colorScheme="gray" variant="subtle" minW="24px" textAlign="center">
                    {i + 1}
                  </Badge>
                  <Text fontFamily="mono" fontSize="xs" color="gray.600" minW="100px">
                    {item.numero_serie || '—'}
                  </Text>
                  <Text fontSize="sm" flex="1">
                    {item.modelo || item.descripcion || 'Equipo'}{item.marca ? ` (${item.marca})` : ''}
                  </Text>
                  {item.falla_cliente && (
                    <Text fontSize="xs" color="gray.500" noOfLines={1} maxW="200px">
                      {item.falla_cliente}
                    </Text>
                  )}
                </Flex>
              ))}
            </VStack>
          </Box>
        </VStack>
      )}

      {/* ── Navegación ────────────────────────────────────────────────────── */}
      <Flex justify="space-between" mt={6} align="center">
        {paso === 1 ? (
          <Button variant="outline" onClick={() => navigate('/app/servicios')}>Cancelar</Button>
        ) : (
          <Button variant="outline" leftIcon={<FaArrowLeft />} onClick={() => setPaso(paso - 1)}>
            Anterior
          </Button>
        )}

        {paso < 3 ? (
          <Button colorScheme="blue" rightIcon={<FaArrowRight />} onClick={() => handleNext(paso + 1)}>
            {paso === 1 ? 'Siguiente: Equipos' : 'Siguiente: Confirmar'}
          </Button>
        ) : (
          <HStack spacing={3}>
            <Button
              variant="outline"
              colorScheme="blue"
              isLoading={saving}
              onClick={handleSubmit}
            >
              Guardar como borrador
            </Button>
            <Button
              colorScheme="blue"
              leftIcon={<FaCheck />}
              isLoading={saving}
              loadingText="Guardando..."
              onClick={handleSubmit}
            >
              {isEdit ? 'Guardar Cambios' : 'Crear Orden'}
            </Button>
          </HStack>
        )}
      </Flex>

      {/* ── Modal: Importar desde guía ───────────────────────────────────── */}
      <Modal isOpen={isGuiaOpen} onClose={onGuiaClose} size="lg">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader fontSize="md">
            Importar equipos de guía {guiaSeleccionadaData?.numero}
          </ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            {guiaSeleccionadaData?.items?.length ? (
              <VStack align="stretch" spacing={3}>
                <Alert status="info" borderRadius="md" py={2} fontSize="sm">
                  <AlertIcon />
                  Se importarán {guiaSeleccionadaData.items.length} equipo(s) de la guía.
                  Los datos actuales de equipos serán reemplazados.
                </Alert>
                <Box overflowX="auto" maxH="280px" overflowY="auto">
                  <Table size="sm" variant="simple">
                    <Thead bg="gray.50" position="sticky" top={0}>
                      <Tr>
                        <Th>N° Serie</Th>
                        <Th>Modelo</Th>
                        <Th>Marca</Th>
                        <Th>Estado ingreso</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {guiaSeleccionadaData.items.map((gi, i) => (
                        <Tr key={i}>
                          <Td fontFamily="mono" fontSize="xs">{gi.serie || '—'}</Td>
                          <Td fontSize="xs">{gi.modelo || '—'}</Td>
                          <Td fontSize="xs">{gi.marca || '—'}</Td>
                          <Td fontSize="xs" maxW="160px">
                            <Text noOfLines={1}>{gi.estado_ingreso || gi.descripcion || '—'}</Text>
                          </Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                </Box>
              </VStack>
            ) : (
              <Text color="gray.500" fontSize="sm">La guía no tiene ítems registrados.</Text>
            )}
          </ModalBody>
          <ModalFooter gap={2}>
            <Button variant="ghost" size="sm" onClick={onGuiaClose}>Cancelar</Button>
            <Button
              colorScheme="blue"
              size="sm"
              leftIcon={<FaTruck />}
              onClick={handleImportarDeGuia}
              isDisabled={!guiaSeleccionadaData?.items?.length}
            >
              Sí, importar {guiaSeleccionadaData?.items?.length ?? 0} equipos
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* ── Modal: Importar Excel ─────────────────────────────────────────── */}
      <Modal isOpen={isExcelOpen} onClose={onExcelClose} size="2xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Importar equipos desde Excel</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4} align="stretch">
              <HStack spacing={3}>
                <Button size="sm" leftIcon={<FaDownload />} variant="outline" colorScheme="gray" onClick={descargarPlantilla}>
                  Descargar plantilla
                </Button>
                <Text fontSize="xs" color="gray.500">Columnas: SERIE · MODELO · MARCA · FALLA</Text>
              </HStack>
              <Box border="2px dashed" borderColor="blue.200" borderRadius="lg" p={6} textAlign="center"
                cursor="pointer" _hover={{ bg: 'blue.50' }} onClick={() => fileInputRef.current?.click()}>
                <input ref={fileInputRef} type="file" accept=".xlsx,.xls,.csv" style={{ display: 'none' }} onChange={handleFileChange} />
                <FaFileExcel size={28} color="var(--chakra-colors-green-500)" style={{ margin: '0 auto 8px' }} />
                <Text fontSize="sm" fontWeight="medium">
                  {importLoading ? 'Procesando...' : 'Haz click para seleccionar archivo .xlsx / .xls / .csv'}
                </Text>
              </Box>
              {importPreview.length > 0 && (
                <>
                  <Text fontSize="sm" fontWeight="semibold" color="blue.600">
                    {importPreview.filter(e => e.seleccionado).length} de {importPreview.length} equipos seleccionados
                  </Text>
                  <Box overflowX="auto" maxH="240px" overflowY="auto">
                    <Table size="xs" variant="simple">
                      <Thead bg="gray.50" position="sticky" top={0}>
                        <Tr>
                          <Th w="36px">
                            <Checkbox
                              isChecked={importPreview.every(e => e.seleccionado)}
                              isIndeterminate={importPreview.some(e => e.seleccionado) && !importPreview.every(e => e.seleccionado)}
                              onChange={(ev) => setImportPreview(p => p.map(e => ({ ...e, seleccionado: ev.target.checked })))}
                            />
                          </Th>
                          <Th>Serie</Th><Th>Modelo</Th><Th>Marca</Th><Th>Falla</Th>
                        </Tr>
                      </Thead>
                      <Tbody>
                        {importPreview.map((eq, i) => (
                          <Tr key={i} opacity={eq.seleccionado ? 1 : 0.4}>
                            <Td>
                              <Checkbox isChecked={eq.seleccionado}
                                onChange={(ev) => setImportPreview(p => p.map((e, idx) => idx === i ? { ...e, seleccionado: ev.target.checked } : e))} />
                            </Td>
                            <Td fontFamily="mono" fontSize="xs">{eq.numero_serie || '—'}</Td>
                            <Td fontSize="xs">{eq.modelo || '—'}</Td>
                            <Td fontSize="xs">{eq.marca || '—'}</Td>
                            <Td fontSize="xs"><Text noOfLines={1}>{eq.falla_cliente || '—'}</Text></Td>
                          </Tr>
                        ))}
                      </Tbody>
                    </Table>
                  </Box>
                </>
              )}
            </VStack>
          </ModalBody>
          <ModalFooter gap={2}>
            <Button variant="ghost" onClick={onExcelClose}>Cancelar</Button>
            <Button colorScheme="blue" isDisabled={importPreview.filter(e => e.seleccionado).length === 0} onClick={handleImportarExcel}>
              Importar {importPreview.filter(e => e.seleccionado).length} equipos
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* ── Modal: Pegar tabla ────────────────────────────────────────────── */}
      <Modal isOpen={isPasteOpen} onClose={onPasteClose} size="2xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Pegar tabla de equipos</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4} align="stretch">
              <Text fontSize="xs" color="gray.500">
                Pega una tabla copiada desde Excel o Google Sheets.
                Primera fila: SERIE · MODELO · MARCA · FALLA
              </Text>
              <Textarea
                value={tsvText}
                onChange={(e) => handleTsvChange(e.target.value)}
                onPaste={(e) => handleTsvChange(e.clipboardData.getData('text/plain'))}
                placeholder={'SERIE\tMODELO\tMARCA\tFALLA\nSN-001\tLaptop HP\tHP\tNo enciende'}
                rows={7} fontFamily="mono" fontSize="xs"
              />
              {tsvPreview.length > 0 && (
                <>
                  <Text fontSize="sm" fontWeight="semibold" color="blue.600">
                    Vista previa — {tsvPreview.filter(e => e.seleccionado).length} equipos
                  </Text>
                  <Box overflowX="auto" maxH="200px" overflowY="auto">
                    <Table size="xs" variant="simple">
                      <Thead bg="gray.50" position="sticky" top={0}>
                        <Tr>
                          <Th w="36px">
                            <Checkbox
                              isChecked={tsvPreview.every(e => e.seleccionado)}
                              isIndeterminate={tsvPreview.some(e => e.seleccionado) && !tsvPreview.every(e => e.seleccionado)}
                              onChange={(ev) => setTsvPreview(p => p.map(e => ({ ...e, seleccionado: ev.target.checked })))}
                            />
                          </Th>
                          <Th>Serie</Th><Th>Modelo</Th><Th>Marca</Th><Th>Falla</Th>
                        </Tr>
                      </Thead>
                      <Tbody>
                        {tsvPreview.map((eq, i) => (
                          <Tr key={i} opacity={eq.seleccionado ? 1 : 0.4}>
                            <Td>
                              <Checkbox isChecked={eq.seleccionado}
                                onChange={(ev) => setTsvPreview(p => p.map((e, idx) => idx === i ? { ...e, seleccionado: ev.target.checked } : e))} />
                            </Td>
                            <Td fontFamily="mono" fontSize="xs">{eq.numero_serie || '—'}</Td>
                            <Td fontSize="xs">{eq.modelo || '—'}</Td>
                            <Td fontSize="xs">{eq.marca || '—'}</Td>
                            <Td fontSize="xs">{eq.falla_cliente || '—'}</Td>
                          </Tr>
                        ))}
                      </Tbody>
                    </Table>
                  </Box>
                </>
              )}
            </VStack>
          </ModalBody>
          <ModalFooter gap={2}>
            <Button variant="ghost" onClick={onPasteClose}>Cancelar</Button>
            <Button colorScheme="teal" isDisabled={tsvPreview.filter(e => e.seleccionado).length === 0} onClick={handlePasteConfirm}>
              Agregar {tsvPreview.filter(e => e.seleccionado).length} equipos
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default OrdenServicioForm;
