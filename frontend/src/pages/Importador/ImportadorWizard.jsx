import React, { useState, useCallback } from 'react';
import {
  Box, VStack, HStack, Text, Button, Icon,
  Badge, Switch, Spinner,
  useToast, useColorModeValue,
} from '@chakra-ui/react';
import { FiUploadCloud, FiList, FiCheckSquare, FiChevronRight } from 'react-icons/fi';
import api from '../../lib/api';
import DropZone from '../../components/Importador/DropZone';
import HojaPreview from '../../components/Importador/HojaPreview';
import ProgresoImport from '../../components/Importador/ProgresoImport';

// Timeout extendido para operaciones de importación (2 min)
const IMPORT_TIMEOUT = 600_000; // 10 min — remote DB can be slow with large datasets

// ─── Step indicator (sin hooks condicionales) ──────────────────────────────────

const STEPS = [
  { id: 1, label: 'Subir archivo',         icon: FiUploadCloud },
  { id: 2, label: 'Revisar y configurar',  icon: FiList },
  { id: 3, label: 'Importar',              icon: FiCheckSquare },
];

function StepIndicator({ current }) {
  // Todos los hooks al tope — sin condicionales
  const activeColor   = useColorModeValue('blue.600',  'blue.300');
  const doneColor     = useColorModeValue('green.500', 'green.300');
  const inactiveColor = useColorModeValue('gray.400',  'gray.500');
  const lineColor     = useColorModeValue('gray.200',  'gray.600');

  return (
    <HStack spacing={0} mb={8} align="center" justify="center">
      {STEPS.map((step, idx) => (
        <React.Fragment key={step.id}>
          <VStack spacing={1} minW="80px">
            <Box
              w={9} h={9}
              borderRadius="full"
              display="flex" alignItems="center" justifyContent="center"
              bg={current > step.id ? doneColor : current === step.id ? activeColor : 'transparent'}
              border="2px solid"
              borderColor={current > step.id ? doneColor : current === step.id ? activeColor : lineColor}
            >
              <Icon
                as={step.icon}
                boxSize={4}
                color={current >= step.id ? 'white' : inactiveColor}
              />
            </Box>
            <Text
              fontSize="10px"
              fontWeight={current === step.id ? 'semibold' : 'normal'}
              color={current >= step.id ? activeColor : inactiveColor}
              textAlign="center"
              maxW="80px"
            >
              {step.label}
            </Text>
          </VStack>
          {idx < STEPS.length - 1 && (
            <Box
              flex={1} h="2px"
              bg={current > step.id ? doneColor : lineColor}
              mt={-4} mx={2}
            />
          )}
        </React.Fragment>
      ))}
    </HStack>
  );
}

// ─── Main wizard ───────────────────────────────────────────────────────────────

export default function ImportadorWizard() {
  // ── TODOS los hooks al tope, sin excepciones ──────────────────────────────
  const toast = useToast();

  // Colores — declarados aquí, nunca dentro de JSX
  const bg             = useColorModeValue('white',      'gray.800');
  const borderColor    = useColorModeValue('gray.200',   'gray.700');
  const subText        = useColorModeValue('gray.500',   'gray.400');
  const lighterSubText = useColorModeValue('gray.400',   'gray.500');

  // Estado del wizard
  const [step,          setStep]          = useState(1);
  const [loading,       setLoading]       = useState(false);
  const [importacionId, setImportacionId] = useState(null);
  const [preview,       setPreview]       = useState(null);
  const [ctx,           setCtx]           = useState(null);
  const [hojaState,     setHojaState]     = useState({});
  const [resultado,     setResultado]     = useState(null);
  const [modoImport,    setModoImport]    = useState('parcial');

  // ── Step 1: Upload ────────────────────────────────────────────────────────

  const handleFile = useCallback(async (file) => {
    setLoading(true);
    const formData = new FormData();
    formData.append('archivo', file);

    try {
      const { data } = await api.post('/api/importador/upload/', formData, {
        timeout: IMPORT_TIMEOUT,
      });

      setImportacionId(data.id);
      setPreview(data.preview);
      setCtx(data.defaults_ctx);

      const initial = {};
      for (const hoja of data.preview?.hojas || []) {
        initial[hoja.nombre] = {
          incluir:  true,
          mapeo:    { ...(hoja.mapeo_detectado || {}) },
          defaults: {},
        };
      }
      setHojaState(initial);
      setStep(2);
    } catch (err) {
      toast({
        title:       'Error al procesar el archivo',
        description: err.response?.data?.error || err.message,
        status:      'error',
        duration:    7000,
        isClosable:  true,
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  // ── Step 2: handlers ──────────────────────────────────────────────────────

  const updateMapeo = useCallback((nombreHoja, col, field) => {
    setHojaState(prev => ({
      ...prev,
      [nombreHoja]: {
        ...prev[nombreHoja],
        mapeo: { ...prev[nombreHoja].mapeo, [col]: field },
      },
    }));
  }, []);

  const updateDefaults = useCallback((nombreHoja, key, value) => {
    setHojaState(prev => ({
      ...prev,
      [nombreHoja]: {
        ...prev[nombreHoja],
        defaults: { ...prev[nombreHoja].defaults, [key]: value },
      },
    }));
  }, []);

  const toggleHoja = useCallback((nombreHoja, val) => {
    setHojaState(prev => ({
      ...prev,
      [nombreHoja]: { ...prev[nombreHoja], incluir: val },
    }));
  }, []);

  // Proyectos no son una entidad del ERP (sin modelo propio), se ignoran silenciosamente
  const hojasVisibles = (preview?.hojas || []).filter(h => h.tipo_hoja !== 'proyectos');

  const hojasIncluidas = hojasVisibles.filter(
    h => hojaState[h.nombre]?.incluir
  );

  // El botón "Confirmar" se habilita solo cuando todas las hojas activas
  // tienen sus campos obligatorios cubiertos (igual que el badge verde).
  const isReadyToImport = hojasIncluidas.length > 0 && hojasIncluidas.every(hoja => {
    const state   = hojaState[hoja.nombre] || {};
    const mapeo   = state.mapeo   || {};
    const defs    = state.defaults || {};
    const mapped  = new Set(Object.values(mapeo).filter(Boolean));
    const tipo    = hoja.tipo_hoja;

    const hasProd    = mapped.has('producto_nombre') || mapped.has('id_producto');
    const hasFechaC  = mapped.has('fecha_compra');
    const hasFechaV  = mapped.has('fecha_entrega');
    const hasCliente = mapped.has('cliente_nombre') || mapped.has('id_cliente') || !!defs.cliente_id;

    if (tipo === 'proveedores') return mapped.has('proveedor_nombre') || mapped.has('producto_nombre');
    if (tipo === 'productos')   return hasProd;
    if (tipo === 'compras')     return hasProd && !!defs.almacen_id && (hasFechaC || !!defs.fecha);
    if (tipo === 'ventas')      return hasProd && hasCliente && (hasFechaV || !!defs.fecha);
    // standard
    return hasProd && !!defs.almacen_id && hasCliente;
  });

  // ── Step 3: Confirm ───────────────────────────────────────────────────────

  const handleConfirmar = useCallback(async () => {
    if (hojasIncluidas.length === 0) {
      toast({ title: 'Selecciona al menos una hoja', status: 'warning', duration: 3000 });
      return;
    }

    const hojas_config = (preview?.hojas || []).map(hoja => ({
      nombre_hoja:    hoja.nombre,
      tipo_hoja:      hoja.tipo_hoja || 'standard',
      incluir:        hojaState[hoja.nombre]?.incluir ?? true,
      mapeo_columnas: hojaState[hoja.nombre]?.mapeo || {},
      defaults:       hojaState[hoja.nombre]?.defaults || {},
    }));

    setStep(3);
    setResultado({ estado: 'importando' });

    try {
      const { data } = await api.post(
        `/api/importador/confirmar/${importacionId}/`,
        { hojas_config, modo_parcial: modoImport === 'parcial' },
        { timeout: IMPORT_TIMEOUT },
      );
      setResultado(data);
    } catch (err) {
      setResultado({
        estado: 'error',
        errores_json: [{
          hoja: '—', fila: 0, producto: '',
          error: err.response?.data?.error || err.message,
        }],
      });
    }
  }, [hojasIncluidas, preview, hojaState, importacionId, modoImport, toast]);

  // ── Reset ─────────────────────────────────────────────────────────────────

  const handleReset = useCallback(() => {
    setStep(1);
    setImportacionId(null);
    setPreview(null);
    setCtx(null);
    setHojaState({});
    setResultado(null);
  }, []);

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <Box maxW="860px" mx="auto">
      {/* Encabezado */}
      <VStack align="start" spacing={1} mb={8}>
        <Text fontSize="2xl" fontWeight="bold">Importar desde Excel</Text>
        <Text fontSize="sm" color={subText}>
          Carga el histórico de operaciones desde tu archivo Excel multi-hoja
        </Text>
      </VStack>

      {/* Card principal */}
      <Box bg={bg} border="1px solid" borderColor={borderColor} borderRadius="2xl" p={8} shadow="sm">
        <StepIndicator current={step} />

        {/* PASO 1 ── Subir archivo */}
        {step === 1 && (
          <VStack spacing={6} align="stretch">
            <VStack align="start" spacing={1}>
              <Text fontWeight="semibold">Selecciona tu archivo</Text>
              <Text fontSize="sm" color={subText}>
                Se aceptan .xlsx, .xls y .csv. El sistema detecta hojas y columnas automáticamente.
              </Text>
            </VStack>

            {loading ? (
              <VStack py={12} spacing={3}>
                <Spinner size="lg" color="blue.500" thickness="3px" />
                <Text fontSize="sm" color={subText}>
                  Analizando archivo… esto puede tomar unos segundos
                </Text>
              </VStack>
            ) : (
              <DropZone onFile={handleFile} disabled={loading} />
            )}
          </VStack>
        )}

        {/* PASO 2 ── Revisar y configurar */}
        {step === 2 && preview && (
          <VStack spacing={5} align="stretch">
            <HStack justify="space-between" align="start">
              <VStack align="start" spacing={1}>
                <Text fontWeight="semibold">Revisa y configura las hojas</Text>
                <Text fontSize="sm" color={subText}>
                  Ajusta el mapeo de columnas y completa los datos faltantes por hoja.
                </Text>
              </VStack>
              <Badge colorScheme="blue" variant="subtle" px={3} py={1} borderRadius="full">
                {preview.hojas.length} hojas detectadas
              </Badge>
            </HStack>

            {/* Hojas de tipo "proyectos" se omiten — no tienen modelo en el ERP */}
            {hojasVisibles.map(hoja => (
              <HojaPreview
                key={hoja.nombre}
                hoja={hoja}
                mapeo={hojaState[hoja.nombre]?.mapeo || {}}
                defaults={hojaState[hoja.nombre]?.defaults || {}}
                incluir={hojaState[hoja.nombre]?.incluir ?? true}
                ctx={ctx}
                onMapeoChange={(col, field) => updateMapeo(hoja.nombre, col, field)}
                onDefaultsChange={(key, value) => updateDefaults(hoja.nombre, key, value)}
                onToggle={(val) => toggleHoja(hoja.nombre, val)}
              />
            ))}

            {/* Modo importación */}
            <Box p={4} border="1px solid" borderColor={borderColor} borderRadius="xl">
              <HStack justify="space-between">
                <VStack align="start" spacing={0}>
                  <Text fontSize="sm" fontWeight="medium">
                    Importar parcialmente en caso de errores
                  </Text>
                  <Text fontSize="xs" color={subText}>
                    Activo: importa filas válidas y reporta errores. Inactivo: cancela todo si falla algo.
                  </Text>
                </VStack>
                <Switch
                  isChecked={modoImport === 'parcial'}
                  onChange={e => setModoImport(e.target.checked ? 'parcial' : 'total')}
                  colorScheme="blue"
                />
              </HStack>
            </Box>

            {/* Acciones */}
            <HStack justify="space-between" pt={2}>
              <Button size="sm" variant="ghost" onClick={handleReset}>
                Cancelar
              </Button>
              <HStack spacing={3}>
                <Text fontSize="xs" color={lighterSubText}>
                  {hojasIncluidas.length} de {hojasVisibles.length} hojas seleccionadas
                </Text>
                <Button
                  colorScheme="blue"
                  size="sm"
                  rightIcon={<FiChevronRight />}
                  onClick={handleConfirmar}
                  isDisabled={!isReadyToImport}
                  title={!isReadyToImport ? 'Completa los campos requeridos en todas las hojas activas' : undefined}
                >
                  Confirmar importación
                </Button>
              </HStack>
            </HStack>
          </VStack>
        )}

        {/* PASO 3 ── Progreso y resultado */}
        {step === 3 && (
          <ProgresoImport
            estado={resultado?.estado || 'importando'}
            resultado={resultado}
            onReset={handleReset}
          />
        )}
      </Box>
    </Box>
  );
}
