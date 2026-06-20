import React, { useState, useEffect, useRef, useCallback } from 'react';
import * as XLSX from 'xlsx';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Input,
  Select,
  Textarea,
  Grid,
  GridItem,
  Heading,
  VStack,
  HStack,
  IconButton,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  NumberInput,
  NumberInputField,
  useToast,
  Flex,
  Text,
  Switch,
  Divider,
  InputGroup,
  InputRightElement,
  Alert,
  AlertIcon,
  Badge,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  useDisclosure,
  Checkbox,
} from '@chakra-ui/react';
import {
  FaPlus, FaTrash, FaSave, FaArrowLeft, FaSearch, FaTools,
  FaFileExcel, FaClipboardList, FaDownload,
} from 'react-icons/fa';
import { useNavigate, useParams } from 'react-router-dom';
import { proveedoresService } from '../../services/proveedores.service';
import comprasService from '../../services/compras.service';

const EQUIPO_VACIO = {
  numero_serie: '',
  modelo: '',
  marca: '',
  trabajo: '',
  cantidad: 1,
  costo_unitario: 0,
};

// ── Parsers de importación ─────────────────────────────────────────────────────
// Formato Excel: numero_serie | modelo | trabajo | cantidad | valor_unitario
// Las filas siguientes del mismo equipo dejan numero_serie y modelo vacíos (fill-down).

const normKey = (k) => String(k || '').trim().toLowerCase().replace(/\s+/g, '_');

const buildRowMap = (row) => {
  const map = {};
  Object.entries(row || {}).forEach(([k, v]) => {
    map[normKey(k)] = v;
  });
  return map;
};

const getField = (rowMap, aliases) => {
  for (const alias of aliases) {
    const val = rowMap[normKey(alias)];
    if (val !== undefined && val !== null && String(val).trim() !== '') {
      return String(val).trim();
    }
  }
  return '';
};

const parseNumero = (raw, fallback = 0) => {
  const n = parseFloat(String(raw ?? '').replace(/[^0-9.]/g, ''));
  return Number.isFinite(n) ? n : fallback;
};

const ALIAS = {
  serie: ['numero_serie', 'n_serie', 'serie', 'n°_serie', 's/n', 'sn'],
  modelo: ['modelo', 'model'],
  marca: ['marca', 'brand'],
  trabajo: ['trabajo', 'falla', 'servicio', 'descripcion', 'estado_ingreso', 'estado'],
  cantidad: ['cantidad', 'cant', 'qty', 'cant.'],
  valor: ['valor_unitario', 'valor', 'costo_unitario', 'costo', 'precio', 'precio_unitario'],
};

const parseFilasImportacion = (rawRows) => {
  let lastSerie = '';
  let lastModelo = '';
  const items = [];

  rawRows.forEach((row, idx) => {
    const m = buildRowMap(row);
    const serieRaw = getField(m, ALIAS.serie);
    const modeloRaw = getField(m, ALIAS.modelo);
    const trabajo = getField(m, ALIAS.trabajo);
    const cantidad = parseNumero(getField(m, ALIAS.cantidad), 1) || 1;
    const valor = parseNumero(getField(m, ALIAS.valor), 0);
    const marca = getField(m, ALIAS.marca);

    if (serieRaw) lastSerie = serieRaw;
    if (modeloRaw) lastModelo = modeloRaw;

    if (!trabajo && !serieRaw && !modeloRaw) return;

    const numero_serie = lastSerie;
    const modelo = lastModelo;

    if (!trabajo) return;

    items.push({
      id_temp: idx,
      numero_serie,
      modelo,
      marca,
      trabajo,
      cantidad,
      costo_unitario: valor,
      valido: Boolean(trabajo),
      seleccionado: true,
    });
  });

  return items.filter(r => r.valido);
};

const parseExcel = (file) => new Promise((resolve) => {
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const wb = XLSX.read(e.target.result, { type: 'array' });
      const ws = wb.Sheets[wb.SheetNames[0]];
      const data = XLSX.utils.sheet_to_json(ws, { defval: '' });
      resolve(parseFilasImportacion(data));
    } catch {
      resolve([]);
    }
  };
  reader.readAsArrayBuffer(file);
});

const parseTSV = (text) => {
  const lines = text.trim().split('\n');
  if (lines.length < 2) return [];

  const headers = lines[0].split('\t').map(h => normKey(h));
  const col = (aliases) => headers.findIndex(h => aliases.some(a => h === normKey(a)));

  const idxSerie = col(ALIAS.serie);
  const idxModelo = col(ALIAS.modelo);
  const idxMarca = col(ALIAS.marca);
  const idxTrabajo = col(ALIAS.trabajo);
  const idxCantidad = col(ALIAS.cantidad);
  const idxValor = col(ALIAS.valor);

  const rawRows = lines.slice(1).filter(l => l.trim()).map((line) => {
    const cols = line.split('\t').map(c => c.trim());
    const pick = (i) => (i >= 0 ? cols[i] : '');
    return {
      numero_serie: pick(idxSerie >= 0 ? idxSerie : 0),
      modelo: pick(idxModelo >= 0 ? idxModelo : 1),
      marca: pick(idxMarca),
      trabajo: pick(idxTrabajo >= 0 ? idxTrabajo : 2),
      cantidad: pick(idxCantidad),
      valor_unitario: pick(idxValor >= 0 ? idxValor : 4),
    };
  });

  return parseFilasImportacion(rawRows);
};

const descargarPlantilla = () => {
  const header = [['numero_serie', 'modelo', 'trabajo', 'cantidad', 'valor_unitario']];
  const ejemplo = [
    ['5CD208KGPB', 'LAPTOP HP 640-G8', 'Mantenimiento de hardware', 1, 95],
    ['', '', 'Teclado', 1, 245],
    ['', '', 'Batería', 1, 255],
    ['5CD2213RM4', 'LAPTOP HP 640-G8', 'Mantenimiento de hardware', 1, 95],
    ['', '', 'Teclado', 1, 245],
    ['', '', 'Batería', 1, 255],
  ];
  const wb = XLSX.utils.book_new();
  const ws = XLSX.utils.aoa_to_sheet([...header, ...ejemplo]);
  XLSX.utils.book_append_sheet(wb, ws, 'Reparaciones');
  XLSX.writeFile(wb, 'plantilla_oc_servicio.xlsx');
};

const OrdenCompraServicioForm = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const esEdicion = Boolean(id);
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [cargandoOrden, setCargandoOrden] = useState(esEdicion);

  const [formData, setFormData] = useState({
    proveedor_nombre: '',
    proveedor_id: '',
    contacto_nombre: '',
    contacto_email: '',
    fecha_entrega: (() => {
      const d = new Date();
      d.setDate(d.getDate() + 30);
      return d.toISOString().split('T')[0];
    })(),
    estado: 'borrador',
    moneda: 'USD',
    igv_incluido: false,
    porcentaje_igv: 18,
    referencia: '',
    forma_pago: 'Contado',
    notas: '',
  });

  const [equipos, setEquipos] = useState([{ ...EQUIPO_VACIO }]);

  // Proveedores
  const [busquedaProveedor, setBusquedaProveedor] = useState('');
  const [resultadosProveedores, setResultadosProveedores] = useState([]);
  const [mostrarResultados, setMostrarResultados] = useState(false);
  const [proveedores, setProveedores] = useState([]);
  const dropdownRef = useRef(null);

  // Importación
  const fileInputRef = useRef(null);
  const [importPreview, setImportPreview] = useState([]);
  const [importLoading, setImportLoading] = useState(false);
  const { isOpen: isExcelOpen, onOpen: onExcelOpen, onClose: onExcelClose } = useDisclosure();
  const [tsvText, setTsvText] = useState('');
  const [tsvPreview, setTsvPreview] = useState([]);
  const { isOpen: isPasteOpen, onOpen: onPasteOpen, onClose: onPasteClose } = useDisclosure();

  useEffect(() => {
    const cargarProveedores = async () => {
      try {
        const data = await proveedoresService.getProveedores();
        setProveedores(Array.isArray(data) ? data : []);
      } catch {
        setProveedores([]);
      }
    };
    cargarProveedores();
  }, []);

  // Cargar orden existente en modo edición
  useEffect(() => {
    if (!esEdicion) return;
    const cargar = async () => {
      try {
        setCargandoOrden(true);
        const orden = await comprasService.getOrdenServicio(id);
        setFormData({
          proveedor_nombre: orden.proveedor_nombre || '',
          proveedor_id: orden.proveedor || '',
          contacto_nombre: orden.contacto_nombre || '',
          contacto_email: orden.contacto_email || '',
          fecha_entrega: orden.fecha_entrega || '',
          estado: orden.estado || 'borrador',
          moneda: orden.moneda || 'USD',
          igv_incluido: orden.igv_incluido || false,
          porcentaje_igv: parseFloat(orden.porcentaje_igv) || 18,
          referencia: orden.referencia || '',
          forma_pago: orden.forma_pago || 'Contado',
          notas: orden.notas || '',
        });
        setEquipos(
          (orden.items || []).length
            ? orden.items.map(it => ({
                numero_serie: it.numero_serie || '',
                modelo: it.modelo || '',
                marca: it.marca || '',
                trabajo: it.trabajo || '',
                cantidad: parseFloat(it.cantidad) || 1,
                costo_unitario: parseFloat(it.costo_unitario) || 0,
              }))
            : [{ ...EQUIPO_VACIO }]
        );
      } catch (error) {
        toast({ title: 'No se pudo cargar la orden', status: 'error', duration: 4000 });
        navigate('/app/compras/ordenes-servicio');
      } finally {
        setCargandoOrden(false);
      }
    };
    cargar();
  }, [esEdicion, id, navigate, toast]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setMostrarResultados(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleBuscarProveedor = useCallback((termino) => {
    setBusquedaProveedor(termino);
    if (termino.length >= 2) {
      const normed = termino.toLowerCase();
      const filtered = proveedores.filter(
        p => (p.razon_social || '').toLowerCase().includes(normed) ||
             (p.nombre || '').toLowerCase().includes(normed) ||
             (p.ruc || '').includes(normed),
      ).slice(0, 8);
      setResultadosProveedores(filtered);
      setMostrarResultados(true);
    } else {
      setResultadosProveedores([]);
      setMostrarResultados(false);
    }
  }, [proveedores]);

  const seleccionarProveedor = (p) => {
    setFormData(prev => ({
      ...prev,
      proveedor_id: p.id,
      proveedor_nombre: p.razon_social || p.nombre || '',
      contacto_nombre: prev.contacto_nombre || p.telefono || '',
      contacto_email: prev.contacto_email || p.email || '',
    }));
    setBusquedaProveedor('');
    setMostrarResultados(false);
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  // ── Equipos ─────────────────────────────────────────────────────────────────
  const agregarEquipo = () => setEquipos(prev => [...prev, { ...EQUIPO_VACIO }]);
  const eliminarEquipo = (index) => {
    if (equipos.length === 1) return;
    setEquipos(prev => prev.filter((_, i) => i !== index));
  };
  const updateEquipo = (index, field, value) => {
    setEquipos(prev => prev.map((eq, i) => (i === index ? { ...eq, [field]: value } : eq)));
  };

  const calcularSubtotalEquipo = (eq) => {
    const sub = (parseFloat(eq.cantidad) || 0) * (parseFloat(eq.costo_unitario) || 0);
    return sub > 0 ? sub : 0;
  };

  const calcularTotales = () => {
    const subtotalBruto = equipos.reduce((sum, eq) => sum + calcularSubtotalEquipo(eq), 0);
    let baseImponible, igv, total;
    if (formData.igv_incluido) {
      baseImponible = subtotalBruto / (1 + (formData.porcentaje_igv / 100));
      igv = subtotalBruto - baseImponible;
      total = subtotalBruto;
    } else {
      baseImponible = subtotalBruto;
      igv = subtotalBruto * (formData.porcentaje_igv / 100);
      total = subtotalBruto + igv;
    }
    return {
      subtotal: subtotalBruto.toFixed(2),
      baseImponible: Math.max(0, baseImponible).toFixed(2),
      igv: Math.max(0, igv).toFixed(2),
      total: Math.max(0, total).toFixed(2),
    };
  };

  // ── Importación Excel / pegar ────────────────────────────────────────────────
  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImportLoading(true);
    const eq = await parseExcel(file);
    setImportPreview(eq);
    setImportLoading(false);
    e.target.value = '';
  };

  const aplicarImportados = (lista) => {
    const nuevos = lista.map(({ id_temp, valido, seleccionado, ...rest }) => rest);
    setEquipos(prev => {
      const base = prev.length === 1 && !prev[0].numero_serie && !prev[0].modelo && !prev[0].trabajo ? [] : prev;
      return [...base, ...nuevos];
    });
  };

  const handleImportarExcel = () => {
    const sel = importPreview.filter(e => e.seleccionado);
    aplicarImportados(sel);
    setImportPreview([]);
    onExcelClose();
    toast({ title: `${sel.length} línea(s) importadas`, status: 'success', duration: 2500 });
  };

  const handleTsvChange = (text) => {
    setTsvText(text);
    setTsvPreview(text.includes('\t') ? parseTSV(text) : []);
  };

  const handlePasteConfirm = () => {
    const sel = tsvPreview.filter(e => e.seleccionado);
    aplicarImportados(sel);
    setTsvText('');
    setTsvPreview([]);
    onPasteClose();
    toast({ title: `${sel.length} línea(s) agregadas`, status: 'success', duration: 2500 });
  };

  // ── Guardar ──────────────────────────────────────────────────────────────────
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.proveedor_nombre.trim()) {
      toast({ title: 'Error', description: 'Debe seleccionar el proveedor de reparación', status: 'error', duration: 3000 });
      return;
    }
    const equiposValidos = equipos.filter(
      eq => (eq.numero_serie || '').trim() || (eq.modelo || '').trim() || (eq.marca || '').trim() || (eq.trabajo || '').trim()
    );
    if (equiposValidos.length === 0) {
      toast({
        title: 'Error',
        description: 'Agrega al menos un equipo con serie, modelo, marca o trabajo',
        status: 'error',
        duration: 4000,
      });
      return;
    }

    const payload = {
      proveedor: formData.proveedor_id ? parseInt(formData.proveedor_id) : null,
      proveedor_nombre: formData.proveedor_nombre,
      contacto_nombre: formData.contacto_nombre || null,
      contacto_email: formData.contacto_email || null,
      fecha_entrega: formData.fecha_entrega || null,
      estado: formData.estado,
      moneda: formData.moneda,
      forma_pago: formData.forma_pago,
      referencia: formData.referencia || null,
      igv_incluido: formData.igv_incluido,
      porcentaje_igv: formData.porcentaje_igv,
      notas: formData.notas,
      items: equiposValidos.map(eq => ({
        numero_serie: (eq.numero_serie || '').trim() || null,
        modelo: (eq.modelo || '').trim() || null,
        marca: (eq.marca || '').trim() || null,
        trabajo: (eq.trabajo || '').trim() || null,
        cantidad: parseFloat(eq.cantidad) || 1,
        costo_unitario: parseFloat(eq.costo_unitario) || 0,
      })),
    };

    try {
      setLoading(true);
      const orden = esEdicion
        ? await comprasService.updateOrdenServicio(id, payload)
        : await comprasService.createOrdenServicio(payload);
      toast({
        title: esEdicion ? 'Orden actualizada' : 'Orden de compra de servicio creada',
        status: 'success',
        duration: 3000,
      });
      navigate(`/app/compras/ordenes-servicio/${orden.id}`);
    } catch (error) {
      toast({
        title: 'Error al guardar',
        description: error.response?.data?.detail || JSON.stringify(error.response?.data || {}).slice(0, 200) || error.message,
        status: 'error',
        duration: 6000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  const totales = calcularTotales();
  const simbolo = formData.moneda === 'USD' ? '$' : 'S/';

  if (cargandoOrden) {
    return (
      <Box p={6}>
        <Text color="gray.400">Cargando orden...</Text>
      </Box>
    );
  }

  return (
    <Box p={6}>
      <Flex justify="space-between" align="center" mb={6}>
        <HStack spacing={3}>
          <Box p={2} bg="purple.50" borderRadius="lg">
            <FaTools size={16} color="var(--chakra-colors-purple-500)" />
          </Box>
          <Box>
            <Heading size="lg">
              {esEdicion ? 'Editar Orden de Compra de Servicio' : 'Nueva Orden de Compra de Servicio'}
            </Heading>
            <Text fontSize="sm" color="gray.500">Orden de reparación dirigida a tu proveedor — descargable en PDF</Text>
          </Box>
        </HStack>
        <Button leftIcon={<FaArrowLeft />} variant="ghost" onClick={() => navigate('/app/compras/ordenes-servicio')}>
          Volver
        </Button>
      </Flex>

      <form onSubmit={handleSubmit}>
        <VStack spacing={6} align="stretch">

          {/* ── Proveedor de reparación ── */}
          <Box bg="white" p={6} borderRadius="lg" shadow="sm">
            <Heading size="md" mb={4}>Proveedor de Reparación</Heading>
            <Grid templateColumns="repeat(2, 1fr)" gap={4}>
              <GridItem colSpan={2}>
                <FormControl>
                  <FormLabel>Buscar Proveedor</FormLabel>
                  <Box position="relative" ref={dropdownRef}>
                    <InputGroup>
                      <Input
                        value={busquedaProveedor}
                        onChange={(e) => handleBuscarProveedor(e.target.value)}
                        placeholder="Buscar por nombre o RUC..."
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
                        {resultadosProveedores.length === 0 ? (
                          <Text py={2} px={3} fontSize="sm" color="gray.500">No se encontraron proveedores</Text>
                        ) : (
                          resultadosProveedores.map((p) => (
                            <Box
                              key={p.id} py={2} px={3} cursor="pointer" _hover={{ bg: 'purple.50' }}
                              onClick={() => seleccionarProveedor(p)}
                              borderBottom="1px solid" borderColor="gray.100" _last={{ borderBottom: 'none' }}
                            >
                              <Text fontSize="sm" fontWeight="bold">{p.razon_social || p.nombre}</Text>
                              <Text fontSize="xs" color="gray.500">{p.ruc || ''}</Text>
                            </Box>
                          ))
                        )}
                      </Box>
                    )}
                  </Box>
                </FormControl>
              </GridItem>

              <GridItem colSpan={2}>
                <FormControl isRequired>
                  <FormLabel>Proveedor</FormLabel>
                  {proveedores.length > 0 ? (
                    <Select
                      value={formData.proveedor_id}
                      onChange={(e) => {
                        const prov = proveedores.find(p => p.id === parseInt(e.target.value));
                        setFormData(prev => ({
                          ...prev,
                          proveedor_id: e.target.value,
                          proveedor_nombre: prov ? (prov.razon_social || prov.nombre) : prev.proveedor_nombre,
                          contacto_nombre: prev.contacto_nombre || (prov ? prov.telefono || '' : ''),
                          contacto_email: prev.contacto_email || (prov ? prov.email || '' : ''),
                        }));
                      }}
                      placeholder="Seleccione un proveedor"
                    >
                      {proveedores.map(p => (
                        <option key={p.id} value={p.id}>
                          {p.razon_social || p.nombre} {p.ruc ? `- ${p.ruc}` : ''}
                        </option>
                      ))}
                    </Select>
                  ) : (
                    <Alert status="warning" borderRadius="md" py={2} px={3} fontSize="sm">
                      <AlertIcon />
                      No hay proveedores registrados.
                      <Text as="span" color="blue.500" cursor="pointer" fontWeight="semibold"
                        onClick={() => navigate('/app/proveedores/nuevo')} ml={1}>
                        Crear uno primero →
                      </Text>
                    </Alert>
                  )}
                </FormControl>
              </GridItem>

              <FormControl>
                <FormLabel>Contacto</FormLabel>
                <Input name="contacto_nombre" value={formData.contacto_nombre} onChange={handleChange} placeholder="Nombre del contacto" />
              </FormControl>
              <FormControl>
                <FormLabel>Email contacto</FormLabel>
                <Input type="email" name="contacto_email" value={formData.contacto_email} onChange={handleChange} placeholder="email@proveedor.com" />
              </FormControl>

              <GridItem colSpan={2}>
                <FormControl>
                  <FormLabel>Referencia</FormLabel>
                  <Input name="referencia" value={formData.referencia} onChange={handleChange} placeholder="Ej: Guía de remisión, N° de ingreso interno" />
                </FormControl>
              </GridItem>
            </Grid>
          </Box>

          {/* ── Configuración ── */}
          <Box bg="white" p={6} borderRadius="lg" shadow="sm">
            <Heading size="md" mb={4}>Configuración</Heading>
            <Grid templateColumns="repeat(3, 1fr)" gap={4}>
              <FormControl>
                <FormLabel>Fecha Estimada de Entrega</FormLabel>
                <Input type="date" name="fecha_entrega" value={formData.fecha_entrega} onChange={handleChange} />
              </FormControl>
              <FormControl isRequired>
                <FormLabel>Estado</FormLabel>
                <Select name="estado" value={formData.estado} onChange={handleChange}>
                  <option value="borrador">Borrador</option>
                  <option value="enviada">Enviada</option>
                  <option value="aprobada">Aprobada</option>
                  <option value="rechazada">Rechazada</option>
                  <option value="completada">Completada</option>
                </Select>
              </FormControl>
              <FormControl isRequired>
                <FormLabel>Moneda</FormLabel>
                <Select name="moneda" value={formData.moneda} onChange={handleChange}>
                  <option value="USD">Dólares ($)</option>
                  <option value="PEN">Soles (S/)</option>
                </Select>
              </FormControl>

              <FormControl display="flex" flexDirection="column" alignItems="flex-start">
                <HStack spacing={3} mb={1}>
                  <FormLabel mb="0">IGV Incluido</FormLabel>
                  <Switch name="igv_incluido" isChecked={formData.igv_incluido} onChange={handleChange} colorScheme="green" />
                </HStack>
                <Text fontSize="xs" color="gray.600">
                  {formData.igv_incluido ? '✓ El costo ya incluye IGV' : '✗ El IGV se sumará al costo'}
                </Text>
              </FormControl>
              <FormControl>
                <FormLabel>Forma de Pago</FormLabel>
                <Input name="forma_pago" value={formData.forma_pago} onChange={handleChange} placeholder="Ej: Contado, 50% adelantado" />
              </FormControl>
              <FormControl>
                <FormLabel>Porcentaje IGV (%)</FormLabel>
                <NumberInput
                  value={formData.porcentaje_igv}
                  onChange={(value) => setFormData(prev => ({ ...prev, porcentaje_igv: parseFloat(value) || 0 }))}
                  min={0} max={100}
                >
                  <NumberInputField />
                </NumberInput>
              </FormControl>
            </Grid>
          </Box>

          {/* ── Equipos a reparar ── */}
          <Box bg="white" p={6} borderRadius="lg" shadow="sm">
            <Flex justify="space-between" align="center" mb={4} flexWrap="wrap" gap={2}>
              <HStack spacing={3}>
                <Heading size="md">Equipos / Trabajos</Heading>
                <Badge colorScheme="purple" variant="subtle" fontSize="sm">{equipos.length}</Badge>
              </HStack>
              <HStack spacing={2} flexWrap="wrap">
                <Button leftIcon={<FaPlus />} colorScheme="purple" size="sm" variant="outline" onClick={agregarEquipo}>
                  Agregar
                </Button>
                <Button leftIcon={<FaFileExcel />} colorScheme="green" size="sm" variant="outline"
                  onClick={() => { setImportPreview([]); onExcelOpen(); }}>
                  Excel
                </Button>
                <Button leftIcon={<FaClipboardList />} colorScheme="teal" size="sm" variant="outline"
                  onClick={() => { setTsvText(''); setTsvPreview([]); onPasteOpen(); }}>
                  Pegar tabla
                </Button>
              </HStack>
            </Flex>

            <Box overflowX="auto">
              <Table size="sm">
                <Thead>
                  <Tr>
                    <Th>N° Serie</Th>
                    <Th>Modelo</Th>
                    <Th>Marca</Th>
                    <Th>Trabajo</Th>
                    <Th>Cant.</Th>
                    <Th>Costo ({simbolo})</Th>
                    <Th>Subtotal</Th>
                    <Th></Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {equipos.map((eq, i) => (
                    <Tr key={i}>
                      <Td minW="130px">
                        <Input size="sm" value={eq.numero_serie} fontFamily="mono"
                          onChange={e => updateEquipo(i, 'numero_serie', e.target.value)} placeholder="SN-XXXX" />
                      </Td>
                      <Td minW="150px">
                        <Input size="sm" value={eq.modelo}
                          onChange={e => updateEquipo(i, 'modelo', e.target.value)} placeholder="Modelo" />
                      </Td>
                      <Td minW="110px">
                        <Input size="sm" value={eq.marca}
                          onChange={e => updateEquipo(i, 'marca', e.target.value)} placeholder="HP / Apple..." />
                      </Td>
                      <Td minW="220px">
                        <Input size="sm" value={eq.trabajo}
                          onChange={e => updateEquipo(i, 'trabajo', e.target.value)} placeholder="Cambio de pantalla, reparación de placa..." />
                      </Td>
                      <Td minW="80px">
                        <NumberInput size="sm" min={1} value={eq.cantidad}
                          onChange={v => updateEquipo(i, 'cantidad', v)}>
                          <NumberInputField />
                        </NumberInput>
                      </Td>
                      <Td minW="110px">
                        <NumberInput size="sm" min={0} precision={2} value={eq.costo_unitario}
                          onChange={v => updateEquipo(i, 'costo_unitario', v)}>
                          <NumberInputField />
                        </NumberInput>
                      </Td>
                      <Td fontWeight="bold" whiteSpace="nowrap">
                        {simbolo} {calcularSubtotalEquipo(eq).toFixed(2)}
                      </Td>
                      <Td>
                        <IconButton icon={<FaTrash />} size="sm" colorScheme="red" variant="ghost"
                          onClick={() => eliminarEquipo(i)} isDisabled={equipos.length === 1} aria-label="Eliminar equipo" />
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </Box>

            {/* ── Totales ── */}
            <Box mt={4} p={4} bg="gray.50" borderRadius="md">
              <Grid templateColumns="1fr auto" gap={2} maxW="420px" ml="auto" alignItems="center">
                <Text fontWeight="bold">Subtotal:</Text>
                <Text textAlign="right">{simbolo} {totales.subtotal}</Text>

                {formData.igv_incluido && (
                  <>
                    <Text fontWeight="bold" fontSize="sm" color="gray.600">Base Imponible:</Text>
                    <Text textAlign="right" fontSize="sm" color="gray.600">{simbolo} {totales.baseImponible}</Text>
                  </>
                )}

                <Text fontWeight="bold">IGV ({formData.porcentaje_igv}%):</Text>
                <Text textAlign="right">{simbolo} {totales.igv}</Text>

                <Divider gridColumn="1 / -1" my={2} />

                <Text fontSize="xl" fontWeight="bold" color="purple.600">TOTAL:</Text>
                <Text fontSize="xl" fontWeight="bold" color="purple.600" textAlign="right">{simbolo} {totales.total}</Text>
              </Grid>
            </Box>
          </Box>

          {/* ── Notas ── */}
          <Box bg="white" p={6} borderRadius="lg" shadow="sm">
            <Heading size="md" mb={4}>Notas / Observaciones</Heading>
            <FormControl>
              <Textarea
                name="notas" value={formData.notas} onChange={handleChange}
                placeholder="Instrucciones especiales, condiciones de la reparación, garantía..." rows={3}
              />
            </FormControl>
          </Box>

          {/* ── Botones ── */}
          <Flex justify="flex-end" gap={4}>
            <Button variant="outline" onClick={() => navigate('/app/compras/ordenes-servicio')}>Cancelar</Button>
            <Button type="submit" colorScheme="purple" leftIcon={<FaSave />} isLoading={loading} loadingText="Guardando...">
              {esEdicion ? 'Guardar Cambios' : 'Crear Orden'}
            </Button>
          </Flex>
        </VStack>
      </form>

      {/* ── Modal: Importar Excel ── */}
      <Modal isOpen={isExcelOpen} onClose={onExcelClose} size="2xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Importar equipos desde Excel</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4} align="stretch">
              <HStack spacing={3}>
                <Button size="sm" leftIcon={<FaDownload />} variant="outline" onClick={descargarPlantilla}>
                  Descargar plantilla
                </Button>
                <Text fontSize="xs" color="gray.500">
                  Columnas: numero_serie · modelo · trabajo · cantidad · valor_unitario
                  {' '}(serie/modelo solo en la 1ª fila de cada equipo)
                </Text>
              </HStack>
              <Box border="2px dashed" borderColor="purple.200" borderRadius="lg" p={6} textAlign="center"
                cursor="pointer" _hover={{ bg: 'purple.50' }} onClick={() => fileInputRef.current?.click()}>
                <input ref={fileInputRef} type="file" accept=".xlsx,.xls,.csv" style={{ display: 'none' }} onChange={handleFileChange} />
                <FaFileExcel size={28} color="var(--chakra-colors-green-500)" style={{ margin: '0 auto 8px' }} />
                <Text fontSize="sm" fontWeight="medium">
                  {importLoading ? 'Procesando...' : 'Haz click para seleccionar archivo .xlsx / .xls / .csv'}
                </Text>
              </Box>
              {importPreview.length > 0 && (
                <Box overflowX="auto" maxH="240px" overflowY="auto">
                  <Table size="sm" variant="simple">
                    <Thead bg="gray.50" position="sticky" top={0}>
                      <Tr>
                        <Th w="36px">
                          <Checkbox
                            isChecked={importPreview.every(e => e.seleccionado)}
                            isIndeterminate={importPreview.some(e => e.seleccionado) && !importPreview.every(e => e.seleccionado)}
                            onChange={(ev) => setImportPreview(p => p.map(e => ({ ...e, seleccionado: ev.target.checked })))}
                          />
                        </Th>
                        <Th>Serie</Th><Th>Modelo</Th><Th>Trabajo</Th><Th>Cant.</Th><Th>Valor unit.</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {importPreview.map((eq, i) => (
                        <Tr key={i} opacity={eq.seleccionado ? 1 : 0.4}>
                          <Td>
                            <Checkbox isChecked={eq.seleccionado}
                              onChange={(ev) => setImportPreview(p => p.map((e, idx) => idx === i ? { ...e, seleccionado: ev.target.checked } : e))} />
                          </Td>
                          <Td fontFamily="mono" fontSize="xs">{eq.numero_serie || '↑'}</Td>
                          <Td fontSize="xs">{eq.modelo || '↑'}</Td>
                          <Td fontSize="xs"><Text noOfLines={1}>{eq.trabajo || '—'}</Text></Td>
                          <Td fontSize="xs" isNumeric>{eq.cantidad || 1}</Td>
                          <Td fontSize="xs" isNumeric>{eq.costo_unitario || 0}</Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                </Box>
              )}
            </VStack>
          </ModalBody>
          <ModalFooter gap={2}>
            <Button variant="ghost" onClick={onExcelClose}>Cancelar</Button>
            <Button colorScheme="purple" isDisabled={importPreview.filter(e => e.seleccionado).length === 0} onClick={handleImportarExcel}>
              Importar {importPreview.filter(e => e.seleccionado).length} líneas
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
                Pega desde Excel/Sheets. Encabezados: numero_serie · modelo · trabajo · cantidad · valor_unitario.
                Deja serie/modelo vacíos en las filas adicionales del mismo equipo.
              </Text>
              <Textarea
                value={tsvText}
                onChange={(e) => handleTsvChange(e.target.value)}
                onPaste={(e) => handleTsvChange(e.clipboardData.getData('text/plain'))}
                placeholder={'numero_serie\tmodelo\ttrabajo\tcantidad\tvalor_unitario\n5CD208KGPB\tLAPTOP HP 640-G8\tMantenimiento de hardware\t1\t95\n\t\tTeclado\t1\t245'}
                rows={7} fontFamily="mono" fontSize="xs"
              />
              {tsvPreview.length > 0 && (
                <Box overflowX="auto" maxH="200px" overflowY="auto">
                  <Table size="sm" variant="simple">
                    <Thead bg="gray.50" position="sticky" top={0}>
                      <Tr>
                        <Th w="36px">
                          <Checkbox
                            isChecked={tsvPreview.every(e => e.seleccionado)}
                            isIndeterminate={tsvPreview.some(e => e.seleccionado) && !tsvPreview.every(e => e.seleccionado)}
                            onChange={(ev) => setTsvPreview(p => p.map(e => ({ ...e, seleccionado: ev.target.checked })))}
                          />
                        </Th>
                        <Th>Serie</Th><Th>Modelo</Th><Th>Trabajo</Th><Th>Cant.</Th><Th>Valor unit.</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {tsvPreview.map((eq, i) => (
                        <Tr key={i} opacity={eq.seleccionado ? 1 : 0.4}>
                          <Td>
                            <Checkbox isChecked={eq.seleccionado}
                              onChange={(ev) => setTsvPreview(p => p.map((e, idx) => idx === i ? { ...e, seleccionado: ev.target.checked } : e))} />
                          </Td>
                          <Td fontFamily="mono" fontSize="xs">{eq.numero_serie || '↑'}</Td>
                          <Td fontSize="xs">{eq.modelo || '↑'}</Td>
                          <Td fontSize="xs">{eq.trabajo || '—'}</Td>
                          <Td fontSize="xs" isNumeric>{eq.cantidad || 1}</Td>
                          <Td fontSize="xs" isNumeric>{eq.costo_unitario || 0}</Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                </Box>
              )}
            </VStack>
          </ModalBody>
          <ModalFooter gap={2}>
            <Button variant="ghost" onClick={onPasteClose}>Cancelar</Button>
            <Button colorScheme="teal" isDisabled={tsvPreview.filter(e => e.seleccionado).length === 0} onClick={handlePasteConfirm}>
              Agregar {tsvPreview.filter(e => e.seleccionado).length} líneas
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default OrdenCompraServicioForm;
