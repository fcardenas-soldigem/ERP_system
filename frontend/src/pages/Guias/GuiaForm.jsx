import React, { useState, useEffect, useRef, useCallback } from 'react';
import * as XLSX from 'xlsx';
import {
  Box, Button, Flex, Heading, HStack, VStack, Text, Input,
  Select, Textarea, FormControl, FormLabel, FormErrorMessage,
  IconButton, Divider, Badge, useToast, useColorModeValue,
  Card, CardBody, SimpleGrid, Grid, GridItem,
  NumberInput, NumberInputField, NumberInputStepper,
  NumberIncrementStepper, NumberDecrementStepper,
  Alert, AlertIcon, Table, Thead, Tbody, Tr, Th, Td,
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody,
  ModalFooter, ModalCloseButton, useDisclosure, Checkbox,
  Center, InputGroup, InputRightElement, Switch,
} from '@chakra-ui/react';
import {
  FaArrowLeft, FaArrowRight, FaCheck, FaPlus, FaTrash, FaTruck,
  FaFileExcel, FaClipboardList, FaDownload, FaSearch,
} from 'react-icons/fa';
import { useNavigate, useParams } from 'react-router-dom';
import guiasService from '../../services/guiasService';
import api from '../../lib/api';

const MOTIVOS_SERVICIO = [
  { value: 'ingreso_reparacion', label: 'Ingreso por Reparación' },
  { value: 'devolucion_cliente', label: 'Devolución a Cliente' },
  { value: 'traslado_tecnico',   label: 'Traslado Técnico' },
  { value: 'otro',               label: 'Otro' },
];

const MOTIVOS_VENTA = [
  { value: 'venta', label: 'Despacho de Venta' },
  { value: 'otro',  label: 'Otro' },
];

const today = () => new Date().toISOString().split('T')[0];

const ITEM_VACIO = {
  descripcion: '', serie: '', marca: '', modelo: '',
  cantidad: 1, unidad_medida: 'UNIDAD', estado_ingreso: '', accesorios: '',
};

// ── Parsers ──────────────────────────────────────────────────────────────────

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
        const falla  = row['FALLA'] || row['ESTADO_INGRESO'] || row['Estado'] || '';
        const cantidad = parseInt(row['CANTIDAD'] || row['Cant'] || '1') || 1;
        return {
          id_temp: idx, descripcion: String(modelo || serie || 'Equipo').trim(),
          serie: String(serie).trim(), modelo: String(modelo).trim(),
          marca: String(marca).trim(), estado_ingreso: String(falla).trim(),
          cantidad, unidad_medida: 'UNIDAD', accesorios: '',
          valido: serie !== '' || modelo !== '', seleccionado: true,
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
    serie:    headers.findIndex(h => ['SERIE', 'N_SERIE', 'S/N', 'SN'].includes(h)),
    modelo:   headers.findIndex(h => ['MODELO', 'MODEL'].includes(h)),
    marca:    headers.findIndex(h => ['MARCA', 'BRAND'].includes(h)),
    falla:    headers.findIndex(h => ['FALLA', 'ESTADO_INGRESO', 'ESTADO'].includes(h)),
    cantidad: headers.findIndex(h => ['CANTIDAD', 'CANT', 'QTY'].includes(h)),
  };
  return lines.slice(1).filter(l => l.trim()).map((line, i) => {
    const cols   = line.split('\t').map(c => c.trim());
    const serie  = idx.serie >= 0 ? cols[idx.serie] : cols[0] || '';
    const modelo = idx.modelo >= 0 ? cols[idx.modelo] : cols[1] || '';
    return {
      id_temp: i, descripcion: String(modelo || serie || 'Equipo').trim(),
      serie, modelo,
      marca:          idx.marca >= 0 ? cols[idx.marca] : '',
      estado_ingreso: idx.falla >= 0 ? cols[idx.falla] : '',
      cantidad:       idx.cantidad >= 0 ? (parseInt(cols[idx.cantidad]) || 1) : 1,
      unidad_medida: 'UNIDAD', accesorios: '',
      valido: true, seleccionado: true,
    };
  });
};

const descargarPlantilla = () => {
  const header  = [['SERIE', 'MODELO', 'MARCA', 'FALLA', 'CANTIDAD']];
  const ejemplo = [['SN-001', 'Laptop HP ProBook', 'HP', 'No enciende', 1], ['SN-002', 'Monitor Dell 24"', 'Dell', 'Pantalla rayada', 1]];
  const wb = XLSX.utils.book_new();
  const ws = XLSX.utils.aoa_to_sheet([...header, ...ejemplo]);
  XLSX.utils.book_append_sheet(wb, ws, 'Equipos');
  XLSX.writeFile(wb, 'plantilla_equipos_guia.xlsx');
};

// ── Component ─────────────────────────────────────────────────────────────────

const GuiaForm = () => {
  const { id }   = useParams();
  const navigate = useNavigate();
  const toast    = useToast();
  const isEdit   = Boolean(id);

  const [paso, setPaso]       = useState(1);
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving]   = useState(false);
  const [clientes, setClientes] = useState([]);
  const [errors, setErrors]   = useState({});

  // Client search
  const [busquedaCliente, setBusquedaCliente] = useState('');
  const [resultadosClientes, setResultadosClientes] = useState([]);
  const [mostrarResultados, setMostrarResultados] = useState(false);
  const dropdownRef = useRef(null);

  // Import Excel
  const fileInputRef = useRef(null);
  const [importPreview, setImportPreview] = useState([]);
  const [importLoading, setImportLoading] = useState(false);
  const { isOpen: isExcelOpen, onOpen: onExcelOpen, onClose: onExcelClose } = useDisclosure();

  // Paste TSV
  const [tsvText, setTsvText] = useState('');
  const [tsvPreview, setTsvPreview] = useState([]);
  const { isOpen: isPasteOpen, onOpen: onPasteOpen, onClose: onPasteClose } = useDisclosure();

  // Paso 1
  const [datos, setDatos] = useState({
    tipo: 'servicio', motivo: 'ingreso_reparacion', fecha_emision: today(), fecha_traslado: today(),
    cliente: '', nombre_destinatario: '', ruc_destinatario: '',
    direccion_origen: '', direccion_destino: '', observaciones: '',
  });

  // Paso 2
  const [items, setItems] = useState([{ ...ITEM_VACIO }]);

  useEffect(() => {
    api.get('/api/ventas/clientes/', { params: { page_size: 500 } })
      .then(r => setClientes(r.data?.results || r.data || []))
      .catch(() => {});
    if (isEdit) {
      guiasService.getById(id).then(g => {
        setDatos({
          tipo: g.tipo ?? 'servicio', motivo: g.motivo, fecha_emision: g.fecha_emision, fecha_traslado: g.fecha_traslado,
          cliente: g.cliente ?? '', nombre_destinatario: g.nombre_destinatario,
          ruc_destinatario: g.ruc_destinatario ?? '',
          direccion_origen: g.direccion_origen, direccion_destino: g.direccion_destino,
          observaciones: g.observaciones ?? '',
        });
        if (g.items?.length) {
          setItems(g.items.map(i => ({
            descripcion: i.descripcion, serie: i.serie ?? '', marca: i.marca ?? '',
            modelo: i.modelo ?? '', cantidad: i.cantidad, unidad_medida: i.unidad_medida,
            estado_ingreso: i.estado_ingreso ?? '', accesorios: i.accesorios ?? '',
          })));
        }
        setLoading(false);
      }).catch(() => { setLoading(false); navigate('/app/guias'); });
    }
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setMostrarResultados(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // ── Client search ──
  const handleBuscarCliente = useCallback((termino) => {
    setBusquedaCliente(termino);
    if (termino.length >= 2) {
      const normed = termino.toLowerCase();
      const filtered = clientes.filter(
        c => (c.nombre || '').toLowerCase().includes(normed) ||
             (c.documento || '').includes(normed)
      ).slice(0, 8);
      setResultadosClientes(filtered);
      setMostrarResultados(true);
    } else {
      setResultadosClientes([]);
      setMostrarResultados(false);
    }
  }, [clientes]);

  const seleccionarCliente = (cl) => {
    setDatos(d => ({
      ...d,
      cliente: cl.id,
      nombre_destinatario: cl.nombre || d.nombre_destinatario,
      ruc_destinatario: cl.documento || d.ruc_destinatario,
      direccion_destino: cl.direccion || d.direccion_destino,
    }));
    setBusquedaCliente('');
    setMostrarResultados(false);
  };

  const handleClienteSelectChange = (clienteId) => {
    if (!clienteId) {
      setDatos(d => ({ ...d, cliente: '' }));
      return;
    }
    const cl = clientes.find(c => String(c.id) === String(clienteId));
    if (!cl) return;
    seleccionarCliente(cl);
  };

  const validarPaso1 = () => {
    const e = {};
    if (!datos.motivo)              e.motivo = 'Requerido';
    if (!datos.fecha_traslado)      e.fecha_traslado = 'Requerido';
    if (!datos.nombre_destinatario) e.nombre_destinatario = 'Requerido';
    if (!datos.direccion_origen)    e.direccion_origen = 'Requerido';
    if (!datos.direccion_destino)   e.direccion_destino = 'Requerido';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const validarPaso2 = () => {
    const e = {};
    items.forEach((item, i) => {
      if (!item.descripcion) e[`item_${i}_descripcion`] = 'Requerido';
    });
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleNext = () => { if (validarPaso1()) setPaso(2); };

  const handleSubmit = async () => {
    if (!validarPaso2()) return;
    setSaving(true);
    try {
      const payload = {
        ...datos, cliente: datos.cliente || null,
        items: items.map((item, i) => ({ ...item, numero_item: i + 1 })),
      };
      let guia;
      if (isEdit) {
        guia = await guiasService.update(id, payload);
        toast({ title: 'Guía actualizada', status: 'success', duration: 3000, isClosable: true });
      } else {
        guia = await guiasService.create(payload);
        toast({ title: `Guía ${guia.numero} creada`, status: 'success', duration: 3000, isClosable: true });
      }
      navigate(`/app/guias/${guia.id}`);
    } catch (err) {
      const data = err.response?.data;
      toast({
        title: isEdit ? 'Error al actualizar' : 'Error al crear guía',
        description: data ? JSON.stringify(data).slice(0, 120) : err.message,
        status: 'error', duration: 5000, isClosable: true,
      });
    } finally { setSaving(false); }
  };

  const addItem    = () => setItems(prev => [...prev, { ...ITEM_VACIO }]);
  const removeItem = (i) => setItems(prev => prev.filter((_, idx) => idx !== i));
  const updateItem = (i, field, value) =>
    setItems(prev => prev.map((it, idx) => idx === i ? { ...it, [field]: value } : it));

  // ── Excel handlers ──
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
    const seleccionados = importPreview.filter(e => e.seleccionado);
    const nuevos = seleccionados.map(({ id_temp, valido, seleccionado, ...rest }) => rest);
    setItems(prev => {
      const base = prev.length === 1 && !prev[0].descripcion && !prev[0].serie ? [] : prev;
      return [...base, ...nuevos];
    });
    setImportPreview([]);
    onExcelClose();
    toast({ title: `${nuevos.length} equipo(s) importados`, status: 'success', duration: 2500, isClosable: true });
  };

  // ── TSV handlers ──
  const handleTsvChange = (text) => {
    setTsvText(text);
    setTsvPreview(text.includes('\t') ? parseTSV(text) : []);
  };

  const handlePasteConfirm = () => {
    const seleccionados = tsvPreview.filter(e => e.seleccionado);
    const nuevos = seleccionados.map(({ id_temp, valido, seleccionado, ...rest }) => rest);
    setItems(prev => {
      const base = prev.length === 1 && !prev[0].descripcion && !prev[0].serie ? [] : prev;
      return [...base, ...nuevos];
    });
    setTsvText(''); setTsvPreview([]);
    onPasteClose();
    toast({ title: `${nuevos.length} equipo(s) agregados`, status: 'success', duration: 2500, isClosable: true });
  };

  const clienteSeleccionado = clientes.find(c => String(c.id) === String(datos.cliente));

  if (loading) return null;

  return (
    <Box p={6}>
      {/* Header */}
      <Flex justify="space-between" align="center" mb={6}>
        <HStack spacing={3}>
          <Box p={2} bg="blue.50" borderRadius="lg">
            <FaTruck size={16} color="var(--chakra-colors-blue-500)" />
          </Box>
          <Box>
            <Heading size="lg">{isEdit ? 'Editar Guía' : 'Nueva Guía de Remisión'}</Heading>
            <Text fontSize="sm" color="gray.500">Paso {paso} de 2</Text>
          </Box>
        </HStack>
        <Button leftIcon={<FaArrowLeft />} variant="ghost" onClick={() => navigate('/app/guias')}>
          Volver
        </Button>
      </Flex>

      {/* Stepper */}
      <HStack spacing={0} mb={6} align="center">
        {[1, 2].map((n) => (
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
              color={paso === n ? 'blue.600' : 'gray.500'} ml={2} mr={n < 2 ? 2 : 0}
            >
              {n === 1 ? 'Datos Generales' : datos.tipo === 'venta' ? 'Productos' : 'Equipos'}
            </Text>
            {n < 2 && <Box flex="1" h="2px" bg={paso > 1 ? 'green.400' : 'gray.200'} mx={3} />}
          </React.Fragment>
        ))}
      </HStack>

      {/* ── PASO 1: Datos generales ── */}
      {paso === 1 && (
        <VStack spacing={6} align="stretch">

          {/* Configuración */}
          <Box bg="white" p={6} borderRadius="lg" shadow="sm">
            <Heading size="md" mb={4}>Configuración</Heading>
            <Grid templateColumns="repeat(3, 1fr)" gap={4}>
              <FormControl isRequired>
                <FormLabel>Tipo de Guía</FormLabel>
                <Select
                  value={datos.tipo}
                  onChange={(e) => {
                    const nuevoTipo = e.target.value;
                    setDatos(d => ({
                      ...d,
                      tipo: nuevoTipo,
                      motivo: nuevoTipo === 'venta' ? 'venta' : 'ingreso_reparacion',
                    }));
                  }}
                >
                  <option value="servicio">Servicio</option>
                  <option value="venta">Venta</option>
                </Select>
              </FormControl>

              <FormControl isRequired isInvalid={!!errors.motivo}>
                <FormLabel>Motivo</FormLabel>
                <Select value={datos.motivo} onChange={(e) => setDatos({ ...datos, motivo: e.target.value })}>
                  {(datos.tipo === 'venta' ? MOTIVOS_VENTA : MOTIVOS_SERVICIO).map(m => (
                    <option key={m.value} value={m.value}>{m.label}</option>
                  ))}
                </Select>
                <FormErrorMessage>{errors.motivo}</FormErrorMessage>
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Fecha Emisión</FormLabel>
                <Input type="date" value={datos.fecha_emision} onChange={(e) => setDatos({ ...datos, fecha_emision: e.target.value })} />
              </FormControl>

              <FormControl isRequired isInvalid={!!errors.fecha_traslado}>
                <FormLabel>Fecha de Traslado</FormLabel>
                <Input type="date" value={datos.fecha_traslado} onChange={(e) => setDatos({ ...datos, fecha_traslado: e.target.value })} />
                <FormErrorMessage>{errors.fecha_traslado}</FormErrorMessage>
              </FormControl>
            </Grid>
          </Box>

          {/* Destinatario */}
          <Box bg="white" p={6} borderRadius="lg" shadow="sm">
            <Heading size="md" mb={4}>Destinatario</Heading>
            <Grid templateColumns="repeat(2, 1fr)" gap={4}>

              <GridItem colSpan={2}>
                <FormControl>
                  <FormLabel>Buscar Cliente Existente</FormLabel>
                  <Box position="relative" ref={dropdownRef}>
                    <InputGroup>
                      <Input
                        value={busquedaCliente}
                        onChange={(e) => handleBuscarCliente(e.target.value)}
                        placeholder="Buscar por nombre o RUC/DNI..."
                      />
                      <InputRightElement pointerEvents="none">
                        <FaSearch color="gray" />
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
                            <Box
                              key={c.id} py={2} px={3} cursor="pointer"
                              _hover={{ bg: 'blue.50' }}
                              onClick={() => seleccionarCliente(c)}
                              borderBottom="1px solid" borderColor="gray.100"
                              _last={{ borderBottom: 'none' }}
                            >
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
                </FormControl>
              </GridItem>

              <GridItem colSpan={2}>
                <FormControl>
                  <FormLabel>Cliente del sistema (opcional)</FormLabel>
                  <Select
                    placeholder="Seleccionar cliente..."
                    value={datos.cliente}
                    onChange={(e) => handleClienteSelectChange(e.target.value)}
                  >
                    {clientes.map(c => (
                      <option key={c.id} value={c.id}>
                        {c.nombre} — {c.tipo_documento === 'ruc' ? 'RUC' : 'DNI'}: {c.documento}
                      </option>
                    ))}
                  </Select>
                </FormControl>
              </GridItem>

              <FormControl isRequired isInvalid={!!errors.nombre_destinatario}>
                <FormLabel>Nombre / Razón Social</FormLabel>
                <Input
                  value={datos.nombre_destinatario}
                  onChange={(e) => setDatos({ ...datos, nombre_destinatario: e.target.value })}
                  placeholder="Nombre del destinatario"
                />
                <FormErrorMessage>{errors.nombre_destinatario}</FormErrorMessage>
              </FormControl>

              <FormControl>
                <FormLabel>RUC / DNI</FormLabel>
                <Input
                  value={datos.ruc_destinatario}
                  onChange={(e) => setDatos({ ...datos, ruc_destinatario: e.target.value })}
                  placeholder="Número de documento"
                  maxLength={11}
                />
              </FormControl>
            </Grid>
          </Box>

          {/* Direcciones */}
          <Box bg="white" p={6} borderRadius="lg" shadow="sm">
            <Heading size="md" mb={4}>Direcciones de Traslado</Heading>
            <Grid templateColumns="repeat(2, 1fr)" gap={4}>
              <FormControl isRequired isInvalid={!!errors.direccion_origen}>
                <FormLabel>Punto de Partida</FormLabel>
                <Input
                  value={datos.direccion_origen}
                  onChange={(e) => setDatos({ ...datos, direccion_origen: e.target.value })}
                  placeholder="Dirección de origen"
                />
                <FormErrorMessage>{errors.direccion_origen}</FormErrorMessage>
              </FormControl>

              <FormControl isRequired isInvalid={!!errors.direccion_destino}>
                <FormLabel>Punto de Llegada</FormLabel>
                <Input
                  value={datos.direccion_destino}
                  onChange={(e) => setDatos({ ...datos, direccion_destino: e.target.value })}
                  placeholder="Dirección de destino"
                />
                <FormErrorMessage>{errors.direccion_destino}</FormErrorMessage>
              </FormControl>
            </Grid>
          </Box>

          {/* Observaciones */}
          <Box bg="white" p={6} borderRadius="lg" shadow="sm">
            <Heading size="md" mb={4}>Observaciones</Heading>
            <FormControl>
              <Textarea
                value={datos.observaciones}
                onChange={(e) => setDatos({ ...datos, observaciones: e.target.value })}
                placeholder="Notas adicionales sobre el traslado..."
                rows={3}
              />
            </FormControl>
          </Box>
        </VStack>
      )}

      {/* ── PASO 2: Equipos ── */}
      {paso === 2 && (
        <Box bg="white" p={6} borderRadius="lg" shadow="sm">
          <Flex justify="space-between" align="center" mb={4}>
            <HStack spacing={3}>
              <Heading size="md">{datos.tipo === 'venta' ? 'Productos' : 'Equipos'}</Heading>
              <Badge colorScheme="purple" variant="subtle" fontSize="sm">{items.length}</Badge>
            </HStack>
            <HStack spacing={2}>
              <Button size="sm" leftIcon={<FaPlus />} colorScheme="blue" variant="outline" onClick={addItem}>
                {datos.tipo === 'venta' ? 'Agregar producto' : 'Agregar equipo'}
              </Button>
              <Button size="sm" leftIcon={<FaFileExcel />} colorScheme="green" variant="outline"
                onClick={() => { setImportPreview([]); onExcelOpen(); }}>
                Importar Excel
              </Button>
              <Button size="sm" leftIcon={<FaClipboardList />} colorScheme="teal" variant="outline"
                onClick={() => { setTsvText(''); setTsvPreview([]); onPasteOpen(); }}>
                Pegar tabla
              </Button>
            </HStack>
          </Flex>

          {items.length === 0 ? (
            <Center py={10} flexDir="column" gap={3}>
              <Box fontSize="3xl" color="gray.300">📦</Box>
              <Text color="gray.400" fontSize="sm">
                {datos.tipo === 'venta'
                  ? 'Agrega productos manualmente, importa desde Excel o pega una tabla'
                  : 'Agrega equipos manualmente, importa desde Excel o pega una tabla'}
              </Text>
              <Button size="sm" colorScheme="blue" leftIcon={<FaPlus />} onClick={addItem}>
                {datos.tipo === 'venta' ? 'Agregar primer producto' : 'Agregar primer equipo'}
              </Button>
            </Center>
          ) : (
            <Box overflowX="auto">
              <Table size="sm" variant="simple">
                <Thead>
                  <Tr>
                    <Th w="36px" fontSize="xs">#</Th>
                    <Th fontSize="xs">N° Serie</Th>
                    <Th fontSize="xs">Modelo</Th>
                    <Th fontSize="xs">Marca</Th>
                    <Th fontSize="xs">{datos.tipo === 'venta' ? 'Descripción' : 'Falla / Estado Ingreso'}</Th>
                    <Th fontSize="xs" w="80px">Cant.</Th>
                    <Th w="36px"></Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {items.map((item, i) => (
                    <Tr key={i}>
                      <Td color="gray.400" fontSize="xs" fontWeight="bold">{i + 1}</Td>
                      <Td>
                        <Input size="sm" value={item.serie} onChange={(e) => updateItem(i, 'serie', e.target.value)}
                          placeholder="SN-XXXX" fontFamily="mono" w="130px" />
                      </Td>
                      <Td>
                        <Input size="sm" value={item.modelo} onChange={(e) => updateItem(i, 'modelo', e.target.value)}
                          placeholder="Modelo" w="150px" />
                      </Td>
                      <Td>
                        <Input size="sm" value={item.marca} onChange={(e) => updateItem(i, 'marca', e.target.value)}
                          placeholder="HP / Dell..." w="110px" />
                      </Td>
                      <Td>
                        <FormControl isInvalid={!!errors[`item_${i}_descripcion`]}>
                          <Input size="sm"
                            value={datos.tipo === 'venta' ? item.descripcion : (item.estado_ingreso || item.descripcion)}
                            onChange={(e) => {
                              if (datos.tipo === 'venta') {
                                updateItem(i, 'descripcion', e.target.value);
                              } else {
                                updateItem(i, 'estado_ingreso', e.target.value);
                                updateItem(i, 'descripcion', e.target.value);
                              }
                            }}
                            placeholder={datos.tipo === 'venta' ? 'Nombre del producto...' : 'Descripción de falla...'}
                            w="240px"
                          />
                        </FormControl>
                      </Td>
                      <Td>
                        <NumberInput size="sm" min={1} value={item.cantidad}
                          onChange={(_, v) => updateItem(i, 'cantidad', v || 1)} w="80px">
                          <NumberInputField />
                          <NumberInputStepper>
                            <NumberIncrementStepper />
                            <NumberDecrementStepper />
                          </NumberInputStepper>
                        </NumberInput>
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

          {Object.keys(errors).length > 0 && (
            <Alert status="error" borderRadius="lg" size="sm" mt={3}>
              <AlertIcon />
              Completa los campos requeridos antes de guardar.
            </Alert>
          )}
        </Box>
      )}

      {/* Navegación */}
      <Flex justify="space-between" mt={6}>
        {paso === 1 ? (
          <Button variant="outline" onClick={() => navigate('/app/guias')}>Cancelar</Button>
        ) : (
          <Button variant="outline" leftIcon={<FaArrowLeft />} onClick={() => setPaso(1)}>Anterior</Button>
        )}

        {paso === 1 ? (
          <Button colorScheme="blue" rightIcon={<FaArrowRight />} onClick={handleNext}>
            {datos.tipo === 'venta' ? 'Siguiente: Productos' : 'Siguiente: Equipos'}
          </Button>
        ) : (
          <Button colorScheme="blue" leftIcon={<FaCheck />} onClick={handleSubmit}
            isLoading={saving} loadingText="Guardando...">
            {isEdit ? 'Guardar Cambios' : 'Crear Guía'}
          </Button>
        )}
      </Flex>

      {/* ── Modal: Importar Excel ── */}
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
                <Text fontSize="xs" color="gray.500">Columnas: SERIE · MODELO · MARCA · FALLA · CANTIDAD</Text>
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
                  <Box overflowX="auto" maxH="260px" overflowY="auto">
                    <Table size="xs" variant="simple">
                      <Thead bg="gray.50" position="sticky" top={0}>
                        <Tr>
                          <Th w="36px">
                            <Checkbox
                              isChecked={importPreview.every(e => e.seleccionado)}
                              isIndeterminate={importPreview.some(e => e.seleccionado) && !importPreview.every(e => e.seleccionado)}
                              onChange={(ev) => setImportPreview(prev => prev.map(e => ({ ...e, seleccionado: ev.target.checked })))}
                            />
                          </Th>
                          <Th>Serie</Th><Th>Modelo</Th><Th>Marca</Th><Th>Falla</Th><Th>Cant.</Th>
                        </Tr>
                      </Thead>
                      <Tbody>
                        {importPreview.map((eq, i) => (
                          <Tr key={i} opacity={eq.seleccionado ? 1 : 0.4}>
                            <Td>
                              <Checkbox isChecked={eq.seleccionado}
                                onChange={(ev) => setImportPreview(prev => prev.map((e, idx) => idx === i ? { ...e, seleccionado: ev.target.checked } : e))} />
                            </Td>
                            <Td fontFamily="mono" fontSize="xs">{eq.serie || '—'}</Td>
                            <Td fontSize="xs">{eq.modelo || '—'}</Td>
                            <Td fontSize="xs">{eq.marca || '—'}</Td>
                            <Td fontSize="xs" maxW="160px"><Text noOfLines={1}>{eq.estado_ingreso || '—'}</Text></Td>
                            <Td fontSize="xs">{eq.cantidad}</Td>
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

      {/* ── Modal: Pegar tabla ── */}
      <Modal isOpen={isPasteOpen} onClose={onPasteClose} size="2xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Pegar tabla de equipos</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4} align="stretch">
              <Text fontSize="xs" color="gray.500">
                Pega una tabla copiada desde Excel o Google Sheets.
                La primera fila debe contener encabezados: SERIE · MODELO · MARCA · FALLA · CANTIDAD
              </Text>
              <Textarea
                value={tsvText}
                onChange={(e) => handleTsvChange(e.target.value)}
                onPaste={(e) => handleTsvChange(e.clipboardData.getData('text/plain'))}
                placeholder={'SERIE\tMODELO\tMARCA\tFALLA\tCANTIDAD\nSN-001\tLaptop HP\tHP\tNo enciende\t1'}
                rows={8} fontFamily="mono" fontSize="xs"
              />

              {tsvPreview.length > 0 && (
                <>
                  <Text fontSize="sm" fontWeight="semibold" color="blue.600">
                    Vista previa — {tsvPreview.filter(e => e.seleccionado).length} equipos
                  </Text>
                  <Box overflowX="auto" maxH="220px" overflowY="auto">
                    <Table size="xs" variant="simple">
                      <Thead bg="gray.50" position="sticky" top={0}>
                        <Tr>
                          <Th w="36px">
                            <Checkbox
                              isChecked={tsvPreview.every(e => e.seleccionado)}
                              isIndeterminate={tsvPreview.some(e => e.seleccionado) && !tsvPreview.every(e => e.seleccionado)}
                              onChange={(ev) => setTsvPreview(prev => prev.map(e => ({ ...e, seleccionado: ev.target.checked })))}
                            />
                          </Th>
                          <Th>Serie</Th><Th>Modelo</Th><Th>Marca</Th><Th>Falla</Th><Th>Cant.</Th>
                        </Tr>
                      </Thead>
                      <Tbody>
                        {tsvPreview.map((eq, i) => (
                          <Tr key={i} opacity={eq.seleccionado ? 1 : 0.4}>
                            <Td>
                              <Checkbox isChecked={eq.seleccionado}
                                onChange={(ev) => setTsvPreview(prev => prev.map((e, idx) => idx === i ? { ...e, seleccionado: ev.target.checked } : e))} />
                            </Td>
                            <Td fontFamily="mono" fontSize="xs">{eq.serie || '—'}</Td>
                            <Td fontSize="xs">{eq.modelo || '—'}</Td>
                            <Td fontSize="xs">{eq.marca || '—'}</Td>
                            <Td fontSize="xs">{eq.estado_ingreso || '—'}</Td>
                            <Td fontSize="xs">{eq.cantidad}</Td>
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

export default GuiaForm;
