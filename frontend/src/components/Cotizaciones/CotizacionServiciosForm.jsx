import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box, Button, FormControl, FormLabel, Input, Select, Grid, GridItem,
  Heading, VStack, HStack, IconButton, Table, Thead, Tbody, Tr, Th, Td,
  useToast, Flex, Text, Divider, Card, CardBody, CardHeader, Textarea,
  Badge, Tooltip, InputGroup, InputRightElement,
  NumberInput, NumberInputField,
} from '@chakra-ui/react';
import {
  FaPlus, FaTrash, FaFilePdf, FaArrowLeft, FaSave, FaSearch,
  FaFileExcel, FaDownload, FaUpload, FaTools, FaChevronDown, FaChevronUp,
} from 'react-icons/fa';
import * as XLSX from 'xlsx';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import useConsultaDocumentos from '../../hooks/useConsultaDocumentos';
import cotizacionesService from '../../services/cotizacionesService';
import { clientesService } from '../../services/clientes.service';
import { api } from '../../lib/api';

const EMPTY_TRABAJO = { descripcion: '', cantidad: 1, valor_unitario: 0 };
const EMPTY_EQUIPO = {
  numero_serie: '',
  modelo: '',
  trabajos: [{ ...EMPTY_TRABAJO }],
};

const CotizacionServiciosForm = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { user } = useAuth();
  const { consultarRUC, loading: rucLoading } = useConsultaDocumentos();
  const [loading, setLoading] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const importRef = useRef(null);

  const [cliente, setCliente] = useState({
    clienteId: '', nombre: '', ruc: '', direccion: '', contacto: '', email: '',
  });

  const [company, setCompany] = useState({ nombre: '', ruc: '', direccion: '' });

  const [config, setConfig] = useState({
    moneda: 'USD',
    forma_pago: 'CREDITO 30 DIAS',
    pago_facturas: 'Viernes de 09:00 - 13:00',
    fecha_emision: new Date().toISOString().split('T')[0],
    fecha_vencimiento: (() => {
      const d = new Date(); d.setDate(d.getDate() + 30); return d.toISOString().split('T')[0];
    })(),
    validez_oferta: '30 días',
  });

  const [equipos, setEquipos] = useState([{ ...EMPTY_EQUIPO, trabajos: [{ ...EMPTY_TRABAJO }] }]);
  const [expandedRows, setExpandedRows] = useState(new Set([0]));

  const [extra, setExtra] = useState({ tiempo_entrega: '', lugar_entrega: '', notas: '' });

  // ── Búsqueda de clientes ──
  const [busquedaCliente, setBusquedaCliente] = useState('');
  const [resultadosClientes, setResultadosClientes] = useState([]);
  const [mostrarResultados, setMostrarResultados] = useState(false);
  const dropdownRef = useRef(null);

  // ── Descuento ──
  const [descuento_tipo, setDescuentoTipo] = useState('porcentaje');
  const [descuento_valor, setDescuentoValor] = useState(0);

  // ── IGV incluido en precios ──
  const [incluyeIgv, setIncluyeIgv] = useState(false);

  // ── Auto-fill empresa ──
  useEffect(() => {
    const info = user?.empresa_info;
    if (info) {
      setCompany({
        nombre: info.nombre || info.razon_social || '',
        ruc: info.ruc || '',
        direccion: info.direccion || '',
      });
    }
  }, [user]);

  useEffect(() => {
    if (id) loadCotizacion();
  }, [id]);

  // Cerrar dropdown al hacer click fuera
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setMostrarResultados(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // ── Cargar cotizacion existente ──
  const loadCotizacion = async () => {
    try {
      const cot = await cotizacionesService.getById(id);
      if (cot.cliente_info || cot.cliente) {
        const c = cot.cliente_info || {};
        setCliente({
          clienteId: cot.cliente || '',
          nombre: c.nombre || '',
          ruc: c.documento || '',
          direccion: c.direccion || '',
          contacto: '',
          email: '',
        });
      }
      setConfig({
        moneda: cot.moneda || 'USD',
        forma_pago: cot.forma_pago || '',
        pago_facturas: cot.pago_facturas || '',
        fecha_emision: cot.fecha_emision || '',
        fecha_vencimiento: cot.fecha_vencimiento || '',
        validez_oferta: cot.validez_oferta || '30 días',
      });
      setExtra({
        tiempo_entrega: cot.tiempo_entrega || '',
        lugar_entrega: cot.lugar_entrega || '',
        notas: cot.notas || '',
      });
      // Cargar descuento
      if (cot.descuento_tipo) {
        setDescuentoTipo(cot.descuento_tipo);
        setDescuentoValor(parseFloat(cot.descuento_valor) || 0);
      } else if (cot.descuento && parseFloat(cot.descuento) > 0) {
        setDescuentoTipo('monto');
        setDescuentoValor(parseFloat(cot.descuento) || 0);
      }
      setIncluyeIgv(!!cot.precios_incluyen_igv);
      if (cot.detalles?.length) {
        const parsedEquipos = cot.detalles.map((d) => {
          const lines = (d.descripcion || '').split('\n');
          const firstLine = lines[0] || '';
          const snMatch = firstLine.match(/\|\s*SN:\s*(.+)$/);
          const numero_serie = snMatch ? snMatch[1].trim() : (d.codigo || '');
          const modeloStr = snMatch ? firstLine.replace(/\|.*$/, '').trim() : firstLine.trim();
          const trabajos = lines.slice(1)
            .filter((l) => l.trim())
            .map((l) => {
              const lineClean = l.replace(/^-\s*/, '');
              const colonIdx = lineClean.lastIndexOf(':');
              if (colonIdx > -1) {
                const desc = lineClean.substring(0, colonIdx).trim();
                const priceStr = lineClean.substring(colonIdx + 1).trim();
                const price = parseFloat(priceStr.replace(/[^0-9.]/g, '')) || 0;
                return { descripcion: desc, cantidad: 1, valor_unitario: price };
              }
              return { descripcion: lineClean, cantidad: 1, valor_unitario: 0 };
            });
          if (!trabajos.length) {
            trabajos.push({
              descripcion: d.descripcion || '',
              cantidad: 1,
              valor_unitario: parseFloat(d.precio_unitario) || 0,
            });
          }
          return { numero_serie, modelo: modeloStr, trabajos };
        });
        setEquipos(parsedEquipos.length ? parsedEquipos : [{ ...EMPTY_EQUIPO, trabajos: [{ ...EMPTY_TRABAJO }] }]);
        setExpandedRows(new Set(parsedEquipos.map((_, i) => i)));
      }
    } catch (e) {
      toast({ title: 'Error al cargar cotización', description: e.message, status: 'error', duration: 5000 });
    }
  };

  // ── Búsqueda de clientes por nombre/RUC ──
  const handleBuscarCliente = useCallback(async (termino) => {
    setBusquedaCliente(termino);
    if (termino.length >= 3) {
      try {
        const data = await clientesService.getClientes({ search: termino });
        const arr = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
        setResultadosClientes(arr.slice(0, 6));
        setMostrarResultados(true);
      } catch {
        setResultadosClientes([]);
        setMostrarResultados(false);
      }
    } else {
      setResultadosClientes([]);
      setMostrarResultados(false);
    }
  }, []);

  const seleccionarCliente = (c) => {
    setCliente({
      clienteId: c.id || '',
      nombre: c.nombre || '',
      ruc: c.documento || c.ruc || '',
      direccion: c.direccion || '',
      contacto: '',
      email: '',
    });
    setBusquedaCliente('');
    setMostrarResultados(false);
  };

  // ── RUC lookup ──
  const handleRucLookup = useCallback(async () => {
    const ruc = cliente.ruc.trim();
    if (ruc.length !== 11) {
      toast({ title: 'El RUC debe tener 11 dígitos', status: 'warning', duration: 3000 });
      return;
    }
    const data = await consultarRUC(ruc);
    if (data) {
      setCliente((prev) => ({
        ...prev,
        nombre: data.razon_social || prev.nombre,
        direccion: data.direccion || prev.direccion,
      }));
      toast({ title: 'Datos encontrados', description: data.razon_social, status: 'success', duration: 3000 });
    } else {
      toast({ title: 'No se encontraron datos para este RUC', status: 'error', duration: 3000 });
    }
  }, [cliente.ruc, consultarRUC, toast]);

  // ── Equipo operations ──
  const toggleRow = useCallback((idx) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  }, []);

  const addEquipo = useCallback(() => {
    setEquipos((prev) => [...prev, { ...EMPTY_EQUIPO, trabajos: [{ ...EMPTY_TRABAJO }] }]);
    setExpandedRows((prev) => new Set([...prev, equipos.length]));
  }, [equipos.length]);

  const removeEquipo = useCallback((idx) => {
    if (equipos.length <= 1) return;
    setEquipos((prev) => prev.filter((_, i) => i !== idx));
    setExpandedRows((prev) => {
      const next = new Set();
      prev.forEach((r) => { if (r < idx) next.add(r); else if (r > idx) next.add(r - 1); });
      return next;
    });
  }, [equipos.length]);

  const updateEquipo = useCallback((idx, field, value) => {
    setEquipos((prev) => {
      const copy = [...prev];
      copy[idx] = { ...copy[idx], [field]: value };
      return copy;
    });
  }, []);

  // ── Trabajo operations ──
  const addTrabajo = useCallback((eqIdx) => {
    setEquipos((prev) => {
      const copy = [...prev];
      copy[eqIdx] = { ...copy[eqIdx], trabajos: [...copy[eqIdx].trabajos, { ...EMPTY_TRABAJO }] };
      return copy;
    });
  }, []);

  const removeTrabajo = useCallback((eqIdx, trIdx) => {
    setEquipos((prev) => {
      const copy = [...prev];
      const trabajos = copy[eqIdx].trabajos.filter((_, i) => i !== trIdx);
      copy[eqIdx] = { ...copy[eqIdx], trabajos: trabajos.length ? trabajos : [{ ...EMPTY_TRABAJO }] };
      return copy;
    });
  }, []);

  const updateTrabajo = useCallback((eqIdx, trIdx, field, value) => {
    setEquipos((prev) => {
      const copy = [...prev];
      const trabajosCopy = [...copy[eqIdx].trabajos];
      trabajosCopy[trIdx] = { ...trabajosCopy[trIdx], [field]: value };
      copy[eqIdx] = { ...copy[eqIdx], trabajos: trabajosCopy };
      return copy;
    });
  }, []);

  // ── Calculations ──
  const calcTrabajo = (t) => {
    const q = parseFloat(t.cantidad) || 0;
    const v = parseFloat(t.valor_unitario) || 0;
    return parseFloat((q * v).toFixed(2));
  };

  const calcEquipoTotal = (equipo) =>
    parseFloat(equipo.trabajos.reduce((s, t) => s + calcTrabajo(t), 0).toFixed(2));

  const subtotal = equipos.reduce((s, eq) => s + calcEquipoTotal(eq), 0);
  const montoDescuento = descuento_tipo === 'porcentaje'
    ? subtotal * ((parseFloat(descuento_valor) || 0) / 100)
    : Math.min(parseFloat(descuento_valor) || 0, subtotal);
  const netoConDesc = Math.max(0, subtotal - montoDescuento);
  const base_imponible = incluyeIgv
    ? parseFloat((netoConDesc / 1.18).toFixed(2))
    : netoConDesc;
  const igv = incluyeIgv
    ? parseFloat((netoConDesc - base_imponible).toFixed(2))
    : parseFloat((netoConDesc * 0.18).toFixed(2));
  const total = incluyeIgv ? netoConDesc : netoConDesc + igv;
  const sym = config.moneda === 'PEN' ? 'S/' : 'US$';
  const fmtNum = (n) => (parseFloat(n) || 0).toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  const handleDescuentoValorChange = (v) => {
    const val = parseFloat(v) || 0;
    if (descuento_tipo === 'porcentaje' && val > 100) {
      toast({ title: 'El descuento no puede superar el 100%', status: 'warning', duration: 2000 });
      return;
    }
    if (descuento_tipo === 'monto' && val > subtotal) {
      toast({ title: 'El descuento no puede ser mayor al subtotal', status: 'warning', duration: 2000 });
      return;
    }
    setDescuentoValor(val);
  };

  // ── Validate ──
  const validate = () => {
    if (!cliente.nombre.trim()) return 'Ingrese el nombre del cliente';
    if (!cliente.ruc.trim()) return 'Ingrese el RUC del cliente';
    const validEquipos = equipos.filter((eq) => eq.numero_serie.trim() || eq.modelo.trim());
    if (!validEquipos.length) return 'Agregue al menos un equipo';
    for (const eq of validEquipos) {
      const validTrabajos = eq.trabajos.filter((t) => t.descripcion.trim());
      if (!validTrabajos.length) {
        return `El equipo "${eq.modelo || eq.numero_serie}" debe tener al menos un trabajo`;
      }
      for (const t of validTrabajos) {
        if ((parseFloat(t.valor_unitario) || 0) <= 0) {
          return `Trabajo "${t.descripcion}": el valor unitario debe ser > 0`;
        }
      }
    }
    return null;
  };

  // ── Build payload ──
  const parseErrorMsg = (e) => {
    console.error('API Error:', e.response?.status, JSON.stringify(e.response?.data));
    const data = e.response?.data;
    if (!data) return e.message;
    if (typeof data === 'string') return data;
    if (data.detail) return data.detail;
    if (data.message) return data.message;
    // DRF field errors: { campo: ["msg1", "msg2"], ... }
    const entries = Object.entries(data);
    if (entries.length) {
      return entries.map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`).join(' | ');
    }
    return e.message;
  };

  const buildPayload = () => ({
    ...(cliente.clienteId ? { cliente: cliente.clienteId } : {}),
    cliente_nombre: cliente.nombre,
    cliente_ruc: cliente.ruc,
    cliente_direccion: cliente.direccion,
    cliente_email: (cliente.email || '').includes('@') ? cliente.email : '',
    cliente_contacto: cliente.contacto,
    fecha_vencimiento: config.fecha_vencimiento,
    moneda: config.moneda,
    forma_pago: config.forma_pago,
    pago_facturas: config.pago_facturas,
    validez_oferta: config.validez_oferta,
    tiempo_entrega: extra.tiempo_entrega,
    lugar_entrega: extra.lugar_entrega,
    notas: extra.notas,
    asunto: `Cotización Servicios para ${cliente.nombre || cliente.ruc || 'Cliente'}`,
    incluye_igv: true,
    precios_incluyen_igv: incluyeIgv,
    porcentaje_igv: 18,
    descuento: parseFloat(montoDescuento.toFixed(2)),
    descuento_tipo,
    descuento_valor: parseFloat(descuento_valor) || 0,
    descuento_monto: parseFloat(montoDescuento.toFixed(2)),
    detalles: equipos
      .filter((eq) => eq.numero_serie.trim() || eq.modelo.trim())
      .map((eq, idx) => {
        const eqTotal = calcEquipoTotal(eq);
        const trabajosDesc = eq.trabajos
          .filter((t) => t.descripcion.trim())
          .map((t) => `- ${t.descripcion}: ${sym} ${fmtNum(calcTrabajo(t))}`)
          .join('\n');
        const snPart = eq.numero_serie ? ` | SN: ${eq.numero_serie}` : '';
        return {
          producto: null,
          codigo: '',
          descripcion: `${eq.modelo}${snPart}\n${trabajosDesc}`,
          cantidad: 1,
          precio_unitario: parseFloat(eqTotal.toFixed(2)),
          descuento_item: 0,
          orden: idx,
        };
      }),
  });

  // ── Actions ──
  const handleSave = async () => {
    const err = validate();
    if (err) return toast({ title: err, status: 'warning', duration: 3000 });
    try {
      setLoading(true);
      if (id) {
        await cotizacionesService.update(id, buildPayload());
        toast({ title: 'Cotización actualizada', status: 'success', duration: 3000 });
      } else {
        await cotizacionesService.create(buildPayload());
        toast({ title: 'Cotización creada', status: 'success', duration: 3000 });
      }
      navigate('/app/cotizaciones');
    } catch (e) {
      toast({ title: 'Error al guardar', description: parseErrorMsg(e), status: 'error', duration: 8000 });
    } finally { setLoading(false); }
  };

  const handleGeneratePDF = async () => {
    if (!id) {
      const err = validate();
      if (err) return toast({ title: err, status: 'warning', duration: 3000 });
      try {
        setLoading(true);
        const res = await cotizacionesService.create(buildPayload());
        const newId = res.id;
        setPdfLoading(true);
        setLoading(false);
        const pdfRes = await api.get(`/api/cotizaciones/${newId}/exportar-pdf/`, { responseType: 'blob' });
        const url = window.URL.createObjectURL(new Blob([pdfRes.data], { type: 'application/pdf' }));
        const link = document.createElement('a');
        link.href = url;
        link.download = `Cotizacion_${newId}.pdf`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
        toast({ title: 'PDF generado', status: 'success', duration: 4000 });
        navigate(`/app/cotizaciones/servicios/${newId}/editar`);
      } catch (e) {
        toast({ title: 'Error al generar PDF', description: parseErrorMsg(e), status: 'error', duration: 8000 });
      } finally { setPdfLoading(false); setLoading(false); }
    } else {
      try {
        setPdfLoading(true);
        await cotizacionesService.update(id, buildPayload());
        const pdfRes = await api.get(`/api/cotizaciones/${id}/exportar-pdf/`, { responseType: 'blob' });
        const url = window.URL.createObjectURL(new Blob([pdfRes.data], { type: 'application/pdf' }));
        const link = document.createElement('a');
        link.href = url;
        link.download = `Cotizacion_${id}.pdf`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
        toast({ title: 'PDF generado', status: 'success', duration: 4000 });
      } catch (e) {
        toast({ title: 'Error al generar PDF', description: parseErrorMsg(e), status: 'error', duration: 8000 });
      } finally { setPdfLoading(false); }
    }
  };

  // ── Excel template ──
  const handleDownloadTemplate = () => {
    const headers = [['numero_serie', 'modelo', 'trabajo', 'cantidad', 'valor_unitario']];
    const example = [
      ['5CD208KGPM', 'LAPTOP HP 640-G8', 'Mantenimiento de hardware', 1, 95],
      ['', '', 'Teclado', 1, 260],
      ['', '', 'Batería', 1, 270],
      ['5CD208KGZD', 'LAPTOP HP 640-G8', 'Mantenimiento de hardware', 1, 95],
      ['', '', 'Teclado', 1, 260],
    ];
    const ws = XLSX.utils.aoa_to_sheet([...headers, ...example]);
    ws['!cols'] = [{ wch: 18 }, { wch: 22 }, { wch: 35 }, { wch: 10 }, { wch: 14 }];
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Equipos y Servicios');
    XLSX.writeFile(wb, 'template_cotizacion_servicios.xlsx');
    toast({ title: 'Template descargado', status: 'success', duration: 2000 });
  };

  // ── Excel import ──
  const handleImportExcel = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = '';

    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const wb = XLSX.read(evt.target.result, { type: 'array' });
        const ws = wb.Sheets[wb.SheetNames[0]];
        const rows = XLSX.utils.sheet_to_json(ws, { defval: '' });

        if (!rows.length) {
          toast({ title: 'El archivo está vacío', status: 'warning', duration: 3000 });
          return;
        }

        const parsePrice = (v) => {
          if (!v && v !== 0) return 0;
          const s = String(v).replace(/[$S/.\s]/g, '').replace(',', '.');
          return parseFloat(s) || 0;
        };

        const COL = {
          numero_serie: ['numero_serie', 'numero serie', 'serial', 'serie', 'sn', 's/n'],
          modelo: ['modelo', 'model', 'equipo', 'descripcion equipo'],
          trabajo: ['trabajo', 'descripcion', 'servicio', 'service', 'detalle', 'item'],
          cantidad: ['cantidad', 'qty', 'quantity', 'cant', 'unidades'],
          valor_unitario: ['valor_unitario', 'valor unitario', 'precio', 'price', 'importe', 'costo', 'valor'],
        };

        const findCol = (keys, row) => {
          const rowLower = Object.fromEntries(
            Object.entries(row).map(([k, v]) => [k.toLowerCase().trim(), v])
          );
          for (const alias of keys) {
            if (rowLower[alias] !== undefined) return rowLower[alias];
          }
          return '';
        };

        const importedEquipos = [];
        let currentEquipo = null;

        for (const row of rows) {
          const sn = String(findCol(COL.numero_serie, row)).trim().toUpperCase();
          const modelo = String(findCol(COL.modelo, row)).trim();
          const trabajo = String(findCol(COL.trabajo, row)).trim();
          const cantidad = parseFloat(findCol(COL.cantidad, row)) || 1;
          const valorUnitario = parsePrice(findCol(COL.valor_unitario, row));

          if (!trabajo) continue;

          if (sn) {
            currentEquipo = { numero_serie: sn, modelo, trabajos: [] };
            importedEquipos.push(currentEquipo);
          } else if (!currentEquipo) {
            currentEquipo = { numero_serie: '', modelo: modelo || 'Equipo sin identificar', trabajos: [] };
            importedEquipos.push(currentEquipo);
          }

          currentEquipo.trabajos.push({ descripcion: trabajo, cantidad, valor_unitario: valorUnitario });
        }

        if (!importedEquipos.length) {
          toast({ title: 'No se encontraron equipos válidos', description: 'Verifica que el archivo tenga columna "trabajo"', status: 'warning', duration: 4000 });
          return;
        }

        setEquipos((prev) => {
          const base = prev.filter((eq) => eq.numero_serie.trim() || eq.modelo.trim());
          return base.length ? [...base, ...importedEquipos] : importedEquipos;
        });
        setExpandedRows(new Set(importedEquipos.map((_, i) => i)));

        const totalTrabajos = importedEquipos.reduce((s, eq) => s + eq.trabajos.length, 0);
        toast({ title: `${importedEquipos.length} equipo(s) importados (${totalTrabajos} trabajos)`, status: 'success', duration: 3000 });
      } catch (err) {
        toast({ title: 'Error al leer el archivo', description: err.message, status: 'error', duration: 5000 });
      }
    };
    reader.readAsArrayBuffer(file);
  };

  return (
    <Box maxW="1400px" mx="auto">
      {/* ── HEADER ── */}
      <Flex justify="space-between" align="center" mb={5}>
        <HStack spacing={3}>
          <Heading size="lg">{id ? 'Editar Cot. Servicios' : 'Nueva Cot. Servicios'}</Heading>
          <Badge colorScheme="green" fontSize="sm" px={3} py={1} borderRadius="md">
            {id ? 'EDITANDO' : 'NUEVO'}
          </Badge>
        </HStack>
        <Button variant="ghost" leftIcon={<FaArrowLeft />} onClick={() => navigate('/app/cotizaciones')}>
          Volver
        </Button>
      </Flex>

      <VStack spacing={4} align="stretch">
        {/* ── CLIENTE ── */}
        <Card size="sm">
          <CardHeader py={2} px={4} bg="blue.600" borderTopRadius="md">
            <Text fontSize="sm" fontWeight="bold" color="white">DATOS DEL CLIENTE</Text>
          </CardHeader>
          <CardBody py={3}>
            {/* Búsqueda por nombre */}
            <Box mb={3} position="relative" ref={dropdownRef}>
              <FormControl>
                <FormLabel fontSize="xs" mb={1}>Buscar Cliente Existente</FormLabel>
                <InputGroup size="sm">
                  <Input
                    value={busquedaCliente}
                    onChange={(e) => handleBuscarCliente(e.target.value)}
                    placeholder="Buscar por nombre o RUC..."
                  />
                  <InputRightElement pointerEvents="none">
                    <FaSearch color="gray" size={12} />
                  </InputRightElement>
                </InputGroup>
              </FormControl>
              {mostrarResultados && (
                <Box
                  position="absolute"
                  top="100%"
                  left={0}
                  right={0}
                  zIndex={1000}
                  bg="white"
                  borderRadius="md"
                  shadow="lg"
                  border="1px solid"
                  borderColor="gray.200"
                  mt={1}
                >
                  {resultadosClientes.length === 0 ? (
                    <Text py={2} px={3} fontSize="sm" color="gray.500">No se encontraron clientes</Text>
                  ) : (
                    resultadosClientes.map((c) => (
                      <Box
                        key={c.id}
                        py={2}
                        px={3}
                        cursor="pointer"
                        _hover={{ bg: 'blue.50' }}
                        onClick={() => seleccionarCliente(c)}
                        borderBottom="1px solid"
                        borderColor="gray.100"
                        _last={{ borderBottom: 'none' }}
                      >
                        <Text fontSize="sm" fontWeight="bold">{c.nombre}</Text>
                        <Text fontSize="xs" color="gray.500">{c.documento || c.ruc || ''}</Text>
                      </Box>
                    ))
                  )}
                </Box>
              )}
            </Box>

            <Grid templateColumns="repeat(3, 1fr)" gap={3}>
              <FormControl isRequired>
                <FormLabel fontSize="xs" mb={1}>RUC</FormLabel>
                <InputGroup size="sm">
                  <Input
                    value={cliente.ruc}
                    onChange={(e) => setCliente((p) => ({ ...p, ruc: e.target.value.replace(/\D/g, '') }))}
                    onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleRucLookup(); } }}
                    placeholder="20XXXXXXXXX" maxLength={11}
                  />
                  <InputRightElement width="auto" pr={1}>
                    <Button size="xs" h="1.5rem" colorScheme="blue" variant="solid"
                      onClick={handleRucLookup} isLoading={rucLoading}
                      isDisabled={cliente.ruc.length !== 11}
                      leftIcon={!rucLoading ? <FaSearch /> : undefined}>
                      {rucLoading ? '' : 'Buscar'}
                    </Button>
                  </InputRightElement>
                </InputGroup>
              </FormControl>
              <GridItem colSpan={2}>
                <FormControl isRequired>
                  <FormLabel fontSize="xs" mb={1}>Razón Social</FormLabel>
                  <Input size="sm" value={cliente.nombre}
                    onChange={(e) => setCliente((p) => ({ ...p, nombre: e.target.value }))}
                    placeholder="Nombre del cliente" />
                </FormControl>
              </GridItem>
              <FormControl>
                <FormLabel fontSize="xs" mb={1}>Dirección</FormLabel>
                <Input size="sm" value={cliente.direccion}
                  onChange={(e) => setCliente((p) => ({ ...p, direccion: e.target.value }))} />
              </FormControl>
              <FormControl>
                <FormLabel fontSize="xs" mb={1}>Contacto</FormLabel>
                <Input size="sm" value={cliente.contacto}
                  onChange={(e) => setCliente((p) => ({ ...p, contacto: e.target.value }))} />
              </FormControl>
              <FormControl>
                <FormLabel fontSize="xs" mb={1}>Email</FormLabel>
                <Input size="sm" type="email" value={cliente.email}
                  onChange={(e) => setCliente((p) => ({ ...p, email: e.target.value }))} />
              </FormControl>
            </Grid>
          </CardBody>
        </Card>

        {/* ── EMPRESA ── */}
        <Card size="sm">
          <CardHeader py={2} px={4} bg="blue.600" borderTopRadius="md">
            <Text fontSize="sm" fontWeight="bold" color="white">DATOS DE LA COMPAÑÍA</Text>
          </CardHeader>
          <CardBody py={3}>
            <Grid templateColumns="repeat(3, 1fr)" gap={3}>
              <FormControl>
                <FormLabel fontSize="xs" mb={1}>Empresa</FormLabel>
                <Input size="sm" value={company.nombre} isReadOnly bg="gray.50" />
              </FormControl>
              <FormControl>
                <FormLabel fontSize="xs" mb={1}>RUC</FormLabel>
                <Input size="sm" value={company.ruc} isReadOnly bg="gray.50" />
              </FormControl>
              <FormControl>
                <FormLabel fontSize="xs" mb={1}>Dirección</FormLabel>
                <Input size="sm" value={company.direccion} isReadOnly bg="gray.50" />
              </FormControl>
            </Grid>
          </CardBody>
        </Card>

        {/* ── CONDICIONES ── */}
        <Card size="sm">
          <CardHeader py={2} px={4} bg="blue.600" borderTopRadius="md">
            <Text fontSize="sm" fontWeight="bold" color="white">CONDICIONES COMERCIALES</Text>
          </CardHeader>
          <CardBody py={3}>
            <Grid templateColumns="repeat(4, 1fr)" gap={3}>
              <FormControl>
                <FormLabel fontSize="xs" mb={1}>Moneda</FormLabel>
                <Select size="sm" value={config.moneda}
                  onChange={(e) => setConfig((p) => ({ ...p, moneda: e.target.value }))}>
                  <option value="USD">Dólares (US$)</option>
                  <option value="PEN">Soles (S/)</option>
                </Select>
              </FormControl>
              <FormControl>
                <FormLabel fontSize="xs" mb={1}>Forma de Pago</FormLabel>
                <Input size="sm" value={config.forma_pago}
                  onChange={(e) => setConfig((p) => ({ ...p, forma_pago: e.target.value }))}
                  placeholder="Ej: CREDITO 30 DIAS" />
              </FormControl>
              <FormControl isRequired>
                <FormLabel fontSize="xs" mb={1}>Fecha Emisión</FormLabel>
                <Input size="sm" type="date" value={config.fecha_emision}
                  onChange={(e) => setConfig((p) => ({ ...p, fecha_emision: e.target.value }))} />
              </FormControl>
              <FormControl>
                <FormLabel fontSize="xs" mb={1}>Válido Hasta</FormLabel>
                <Input size="sm" type="date" value={config.fecha_vencimiento}
                  onChange={(e) => setConfig((p) => ({ ...p, fecha_vencimiento: e.target.value }))} />
              </FormControl>
            </Grid>
            <Grid templateColumns="repeat(3, 1fr)" gap={3} mt={3}>
              <FormControl>
                <FormLabel fontSize="xs" mb={1}>Pago de Facturas</FormLabel>
                <Input size="sm" value={config.pago_facturas}
                  onChange={(e) => setConfig((p) => ({ ...p, pago_facturas: e.target.value }))}
                  placeholder="Ej: Viernes de 09:00 - 13:00" />
              </FormControl>
              <FormControl>
                <FormLabel fontSize="xs" mb={1}>Validez Oferta</FormLabel>
                <Input size="sm" value={config.validez_oferta}
                  onChange={(e) => setConfig((p) => ({ ...p, validez_oferta: e.target.value }))} />
              </FormControl>
            </Grid>
          </CardBody>
        </Card>

        {/* ── EQUIPOS Y SERVICIOS ── */}
        <input
          ref={importRef}
          type="file"
          accept=".xlsx,.xls,.csv"
          style={{ display: 'none' }}
          onChange={handleImportExcel}
        />
        <Card size="sm">
          <CardHeader py={2} px={4} bg="blue.600" borderTopRadius="md">
            <Flex justify="space-between" align="center">
              <HStack spacing={2}>
                <FaTools color="white" />
                <Text fontSize="sm" fontWeight="bold" color="white">EQUIPOS Y SERVICIOS</Text>
              </HStack>
              <HStack spacing={2}>
                <Tooltip label="Descargar template Excel">
                  <Button size="xs" colorScheme="whiteAlpha" variant="outline"
                    leftIcon={<FaDownload />} onClick={handleDownloadTemplate}>
                    Template
                  </Button>
                </Tooltip>
                <Tooltip label="Importar desde Excel">
                  <Button size="xs" colorScheme="whiteAlpha" variant="outline"
                    leftIcon={<FaFileExcel />} onClick={() => importRef.current?.click()}>
                    Importar Excel
                  </Button>
                </Tooltip>
                <Button size="xs" colorScheme="whiteAlpha" variant="solid"
                  leftIcon={<FaPlus />} onClick={addEquipo}>
                  Agregar Equipo
                </Button>
              </HStack>
            </Flex>
          </CardHeader>
          <CardBody p={0}>
            <Box overflowX="auto">
              <Table size="sm" variant="simple">
                <Thead bg="gray.100">
                  <Tr>
                    <Th w="40px" textAlign="center" fontSize="xs">N°</Th>
                    <Th minW="140px" fontSize="xs">Número de Serie</Th>
                    <Th minW="200px" fontSize="xs">Modelo</Th>
                    <Th w="90px" textAlign="center" fontSize="xs">N° Trabajos</Th>
                    <Th w="140px" textAlign="right" fontSize="xs">Total Equipo</Th>
                    <Th w="80px" textAlign="center" fontSize="xs">Acciones</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {equipos.map((equipo, eqIdx) => {
                    const eqTotal = calcEquipoTotal(equipo);
                    const isExpanded = expandedRows.has(eqIdx);
                    return (
                      <React.Fragment key={eqIdx}>
                        {/* ── Fila principal del equipo ── */}
                        <Tr
                          bg={isExpanded ? 'blue.50' : 'white'}
                          _hover={{ bg: 'blue.50' }}
                          cursor="pointer"
                          onClick={() => toggleRow(eqIdx)}
                        >
                          <Td textAlign="center" color="gray.500" fontSize="sm">{eqIdx + 1}</Td>
                          <Td p={1} onClick={(e) => e.stopPropagation()}>
                            <Input
                              size="sm" variant="flushed"
                              placeholder="SN-XXXXXXXX"
                              value={equipo.numero_serie}
                              onChange={(e) => updateEquipo(eqIdx, 'numero_serie', e.target.value.toUpperCase())}
                            />
                          </Td>
                          <Td p={1} onClick={(e) => e.stopPropagation()}>
                            <Input
                              size="sm" variant="flushed"
                              placeholder="Modelo del equipo"
                              value={equipo.modelo}
                              onChange={(e) => updateEquipo(eqIdx, 'modelo', e.target.value)}
                            />
                          </Td>
                          <Td textAlign="center">
                            <Badge colorScheme="blue" fontSize="xs">
                              {equipo.trabajos.filter((t) => t.descripcion.trim()).length} trab.
                            </Badge>
                          </Td>
                          <Td textAlign="right" fontSize="sm" fontWeight="semibold" color="gray.700">
                            {sym} {fmtNum(eqTotal)}
                          </Td>
                          <Td p={1} onClick={(e) => e.stopPropagation()}>
                            <HStack spacing={1} justify="center">
                              <IconButton
                                icon={isExpanded ? <FaChevronUp /> : <FaChevronDown />}
                                size="xs" variant="ghost" colorScheme="blue"
                                onClick={() => toggleRow(eqIdx)}
                                aria-label={isExpanded ? 'Colapsar' : 'Expandir'}
                              />
                              <IconButton
                                icon={<FaTrash />} size="xs" variant="ghost" colorScheme="red"
                                isDisabled={equipos.length <= 1}
                                onClick={() => removeEquipo(eqIdx)}
                                aria-label="Eliminar equipo"
                              />
                            </HStack>
                          </Td>
                        </Tr>

                        {/* ── Sub-tabla de trabajos (expandible) ── */}
                        {isExpanded && (
                          <Tr>
                            <Td colSpan={7} p={0} borderBottom="2px solid" borderColor="blue.200">
                              <Box bg="gray.50" px={6} py={3}>
                                <Flex justify="space-between" align="center" mb={2}>
                                  <Text fontSize="xs" fontWeight="bold" color="blue.700" textTransform="uppercase">
                                    Trabajos / Servicios del equipo
                                  </Text>
                                  <Button size="xs" colorScheme="green" variant="outline"
                                    leftIcon={<FaPlus />} onClick={() => addTrabajo(eqIdx)}>
                                    Agregar trabajo
                                  </Button>
                                </Flex>
                                <Table size="xs" variant="simple">
                                  <Thead>
                                    <Tr bg="gray.200">
                                      <Th fontSize="xs" minW="280px">Descripción del trabajo</Th>
                                      <Th fontSize="xs" w="90px" textAlign="center">Cantidad</Th>
                                      <Th fontSize="xs" w="130px" textAlign="right">Valor Unitario</Th>
                                      <Th fontSize="xs" w="120px" textAlign="right">Total</Th>
                                      <Th w="40px"></Th>
                                    </Tr>
                                  </Thead>
                                  <Tbody>
                                    {equipo.trabajos.map((trabajo, trIdx) => (
                                      <Tr key={trIdx} _hover={{ bg: 'blue.50' }}>
                                        <Td p={1}>
                                          <Input
                                            size="sm" variant="flushed"
                                            placeholder="Descripción del trabajo o servicio"
                                            value={trabajo.descripcion}
                                            onChange={(e) => updateTrabajo(eqIdx, trIdx, 'descripcion', e.target.value)}
                                          />
                                        </Td>
                                        <Td p={1}>
                                          <NumberInput
                                            size="sm" min={0} precision={2} step={1}
                                            value={trabajo.cantidad}
                                            onChange={(val) => updateTrabajo(eqIdx, trIdx, 'cantidad', val)}>
                                            <NumberInputField textAlign="center" px={2} />
                                          </NumberInput>
                                        </Td>
                                        <Td p={1}>
                                          <NumberInput
                                            size="sm" min={0} precision={2} step={0.01}
                                            value={trabajo.valor_unitario}
                                            onChange={(val) => updateTrabajo(eqIdx, trIdx, 'valor_unitario', val)}>
                                            <NumberInputField textAlign="right" px={2} />
                                          </NumberInput>
                                        </Td>
                                        <Td textAlign="right" fontSize="sm" fontWeight="medium" color="gray.700" pr={2}>
                                          {sym} {fmtNum(calcTrabajo(trabajo))}
                                        </Td>
                                        <Td p={0}>
                                          <IconButton
                                            icon={<FaTrash />} size="xs" variant="ghost" colorScheme="red"
                                            isDisabled={equipo.trabajos.length <= 1}
                                            onClick={() => removeTrabajo(eqIdx, trIdx)}
                                            aria-label="Eliminar trabajo"
                                          />
                                        </Td>
                                      </Tr>
                                    ))}
                                  </Tbody>
                                </Table>
                              </Box>
                            </Td>
                          </Tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </Tbody>
              </Table>
            </Box>

            {/* ── Totales ── */}
            <Flex justify="flex-end" p={4} bg="gray.50" borderTop="1px" borderColor="gray.200">
              <Box w="340px">
                <Flex justify="flex-end" mb={2}>
                  <Button
                    size="xs"
                    colorScheme={incluyeIgv ? 'green' : 'gray'}
                    variant={incluyeIgv ? 'solid' : 'outline'}
                    onClick={() => setIncluyeIgv(p => !p)}
                  >
                    {incluyeIgv ? '✓ Precios incl. IGV' : 'Precios incl. IGV'}
                  </Button>
                </Flex>
                <Grid templateColumns="1fr auto" gap={2} alignItems="center">
                  <Text fontSize="sm" fontWeight="medium">
                    {incluyeIgv ? 'Sub Total (c/IGV):' : 'Sub Total:'}
                  </Text>
                  <Text fontSize="sm" fontWeight="medium" textAlign="right">{sym} {fmtNum(subtotal)}</Text>

                  {/* Descuento */}
                  <HStack spacing={1}>
                    <Text fontSize="sm" fontWeight="medium" whiteSpace="nowrap">Descuento:</Text>
                    <Select
                      size="xs"
                      w="58px"
                      flexShrink={0}
                      value={descuento_tipo}
                      onChange={(e) => { setDescuentoTipo(e.target.value); setDescuentoValor(0); }}
                    >
                      <option value="porcentaje">%</option>
                      <option value="monto">{sym}</option>
                    </Select>
                  </HStack>
                  <NumberInput
                    size="sm"
                    value={descuento_valor}
                    min={0}
                    max={descuento_tipo === 'porcentaje' ? 100 : subtotal}
                    step={descuento_tipo === 'porcentaje' ? 1 : 0.01}
                    onChange={handleDescuentoValorChange}
                    w="110px"
                    ml="auto"
                  >
                    <NumberInputField textAlign="right" />
                  </NumberInput>

                  {descuento_tipo === 'porcentaje' && montoDescuento > 0 && (
                    <>
                      <Box />
                      <Text fontSize="xs" color="gray.500" textAlign="right">
                        - {sym} {fmtNum(montoDescuento)}
                      </Text>
                    </>
                  )}

                  {montoDescuento > 0 && (
                    <>
                      <Text fontSize="sm" fontWeight="medium" color="gray.600">Subtotal neto:</Text>
                      <Text fontSize="sm" fontWeight="semibold" textAlign="right" color="gray.700">
                        {sym} {fmtNum(netoConDesc)}
                      </Text>
                    </>
                  )}

                  {incluyeIgv && (
                    <>
                      <Text fontSize="sm" fontWeight="medium" color="gray.600">Base imponible:</Text>
                      <Text fontSize="sm" fontWeight="medium" textAlign="right" color="gray.600">
                        {sym} {fmtNum(base_imponible)}
                      </Text>
                    </>
                  )}

                  <Text fontSize="sm" fontWeight="medium">
                    IGV (18%){incluyeIgv ? ' (incluido)' : ''}:
                  </Text>
                  <Text fontSize="sm" fontWeight="medium" textAlign="right">{sym} {fmtNum(igv)}</Text>
                  <Divider gridColumn="1 / -1" borderColor="blue.500" borderWidth="2px" />
                  <Text fontSize="lg" fontWeight="bold" color="blue.700">TOTAL:</Text>
                  <Text fontSize="lg" fontWeight="bold" color="blue.700" textAlign="right">
                    {sym} {fmtNum(total)}
                  </Text>
                </Grid>
              </Box>
            </Flex>
          </CardBody>
        </Card>

        {/* ── ENTREGA + NOTAS ── */}
        <Grid templateColumns="1fr 1fr" gap={4}>
          <Card size="sm">
            <CardHeader py={2} px={4} bg="blue.600" borderTopRadius="md">
              <Text fontSize="sm" fontWeight="bold" color="white">ENTREGA</Text>
            </CardHeader>
            <CardBody py={3}>
              <VStack spacing={2}>
                <FormControl>
                  <FormLabel fontSize="xs" mb={1}>Tiempo de Entrega</FormLabel>
                  <Input size="sm" value={extra.tiempo_entrega}
                    onChange={(e) => setExtra((p) => ({ ...p, tiempo_entrega: e.target.value }))}
                    placeholder="Ej: 15 días hábiles" />
                </FormControl>
                <FormControl>
                  <FormLabel fontSize="xs" mb={1}>Lugar de Entrega</FormLabel>
                  <Input size="sm" value={extra.lugar_entrega}
                    onChange={(e) => setExtra((p) => ({ ...p, lugar_entrega: e.target.value }))}
                    placeholder="Dirección de entrega" />
                </FormControl>
              </VStack>
            </CardBody>
          </Card>
          <Card size="sm">
            <CardHeader py={2} px={4} bg="blue.600" borderTopRadius="md">
              <Text fontSize="sm" fontWeight="bold" color="white">NOTAS / OBSERVACIONES</Text>
            </CardHeader>
            <CardBody py={3}>
              <Textarea size="sm" rows={3} value={extra.notas}
                onChange={(e) => setExtra((p) => ({ ...p, notas: e.target.value }))}
                placeholder="Observaciones o notas adicionales..." />
            </CardBody>
          </Card>
        </Grid>

        {/* ── ACTIONS ── */}
        <Flex justify="flex-end" gap={3} pt={2} pb={8}>
          <Button variant="outline" colorScheme="gray" onClick={() => navigate('/app/cotizaciones')}>
            Cancelar
          </Button>
          <Button leftIcon={<FaSave />} colorScheme="blue" variant="outline" onClick={handleSave}
            isLoading={loading} loadingText="Guardando...">
            Guardar
          </Button>
          <Button leftIcon={<FaFilePdf />} colorScheme="blue" onClick={handleGeneratePDF}
            isLoading={pdfLoading} loadingText="Generando...">
            Generar PDF
          </Button>
        </Flex>
      </VStack>
    </Box>
  );
};

export default CotizacionServiciosForm;
