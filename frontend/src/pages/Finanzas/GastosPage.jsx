import React, { useState, useRef } from 'react';
import {
  Box, Flex, Heading, Text, HStack, VStack, SimpleGrid,
  Button, IconButton, Badge, Select, Input, NumberInput,
  NumberInputField, NumberInputStepper, NumberIncrementStepper,
  NumberDecrementStepper, RadioGroup, Radio, Stack, Tooltip,
  useDisclosure, Modal, ModalOverlay, ModalContent, ModalHeader,
  ModalBody, ModalFooter, ModalCloseButton, FormControl, FormLabel,
  Skeleton, SkeletonText, useToast, AlertIcon, Alert, AlertDescription,
  ButtonGroup, Menu, MenuButton, MenuList, MenuItem, Divider,
  useColorModeValue, Tag, TagLabel,
} from '@chakra-ui/react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FiChevronLeft, FiChevronRight, FiPlus, FiRepeat, FiEdit2,
  FiTrash2, FiMoreVertical, FiDollarSign, FiUsers, FiHome,
  FiZap, FiTruck, FiTrendingUp, FiTool, FiMoreHorizontal,
  FiFileText, FiAlertTriangle,
} from 'react-icons/fi';
import { gastosService } from '../../services/gastos.service';

// ─── Helpers ──────────────────────────────────────────────────────────────────

const mesLabel = (año, mes) => {
  const fecha = new Date(año, mes - 1, 1);
  return fecha.toLocaleDateString('es-PE', { month: 'long', year: 'numeric' });
};

const fechaParam = (año, mes) =>
  `${año}-${String(mes).padStart(2, '0')}`;

const fmtCurrency = (amount, currency = 'PEN') =>
  new Intl.NumberFormat('es-PE', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(Number(amount ?? 0));

const todayISO = () => new Date().toISOString().split('T')[0];

// ─── Category icon map ────────────────────────────────────────────────────────
const ICONO_MAP = {
  FiUsers: FiUsers,
  FiHome: FiHome,
  FiZap: FiZap,
  FiTruck: FiTruck,
  FiDollarSign: FiDollarSign,
  FiTrendingUp: FiTrendingUp,
  FiTool: FiTool,
  FiMoreHorizontal: FiMoreHorizontal,
  FiFileText: FiFileText,
};

const CatIcon = ({ icono }) => {
  const C = ICONO_MAP[icono] ?? FiDollarSign;
  return <C size={14} />;
};

// ─── Estado badge ─────────────────────────────────────────────────────────────
const ESTADO_COLOR = {
  pagado: 'green',
  pendiente: 'yellow',
  programado: 'gray',
};

const ESTADO_LABEL = {
  pagado: 'Pagado',
  pendiente: 'Pendiente',
  programado: 'Programado',
};

// ─── Stat card ────────────────────────────────────────────────────────────────
const StatCard = ({ label, value, sub, colorScheme, alerta }) => {
  const bg = useColorModeValue(`${colorScheme}.50`, `${colorScheme}.900`);
  const borderColor = useColorModeValue(`${colorScheme}.200`, `${colorScheme}.700`);
  const textColor = useColorModeValue(`${colorScheme}.700`, `${colorScheme}.200`);

  return (
    <Box bg={bg} border="1px solid" borderColor={borderColor} borderRadius="xl" p={5}>
      <Text fontSize="10px" fontWeight="semibold" color={textColor} textTransform="uppercase" letterSpacing="wider" mb={1}>
        {label}
      </Text>
      <Text fontSize="2xl" fontWeight="bold" color={textColor} fontVariantNumeric="tabular-nums">
        {value}
      </Text>
      {sub && (
        <Text fontSize="xs" color={textColor} opacity={0.7} mt={0.5}>
          {sub}
        </Text>
      )}
      {alerta && (
        <HStack mt={2} spacing={1}>
          <FiAlertTriangle size={12} color="#991b1b" />
          <Text fontSize="xs" color="red.700" fontWeight="medium">{alerta}</Text>
        </HStack>
      )}
    </Box>
  );
};

// ─── Barra de distribución ────────────────────────────────────────────────────
const DistribucionBar = ({ distribucion }) => {
  if (!distribucion || distribucion.length === 0) return null;
  const total = distribucion.reduce((acc, d) => acc + Number(d.total ?? 0), 0);
  if (total === 0) return null;

  return (
    <Box>
      <Text fontSize="xs" fontWeight="semibold" color="gray.500" textTransform="uppercase" letterSpacing="wider" mb={2}>
        Distribución por categoría
      </Text>
      <Flex width="100%" height="12px" borderRadius="full" overflow="hidden">
        {distribucion.map((d, i) => {
          const pct = total > 0 ? ((Number(d.total) / total) * 100).toFixed(1) : 0;
          return (
            <Tooltip
              key={i}
              label={`${d.nombre}: ${fmtCurrency(d.total)} (${pct}%)`}
              hasArrow
              placement="top"
            >
              <Box
                flex={Number(d.total) / total}
                bg={d.color || `hsl(${(i * 60) % 360}, 65%, 55%)`}
                cursor="default"
                _hover={{ opacity: 0.85 }}
                transition="opacity 0.15s"
              />
            </Tooltip>
          );
        })}
      </Flex>
      <Flex wrap="wrap" gap={3} mt={2}>
        {distribucion.map((d, i) => {
          const pct = total > 0 ? ((Number(d.total) / total) * 100).toFixed(0) : 0;
          return (
            <HStack key={i} spacing={1.5}>
              <Box
                w="10px" h="10px" borderRadius="full" flexShrink={0}
                bg={d.color || `hsl(${(i * 60) % 360}, 65%, 55%)`}
              />
              <Text fontSize="xs" color="gray.600">{d.nombre}</Text>
              <Text fontSize="xs" color="gray.400">{pct}%</Text>
            </HStack>
          );
        })}
      </Flex>
    </Box>
  );
};

// ─── Formulario gasto (usado en modal crear y editar) ─────────────────────────
const GastoForm = ({ form, setForm, categorias }) => {
  const tieneComprobante = form.comprobante_tipo !== 'sin_comprobante';

  return (
    <VStack spacing={4} align="stretch">
      {/* Categoría */}
      <FormControl isRequired>
        <FormLabel fontSize="sm">Categoría</FormLabel>
        <Select
          value={form.categoria || ''}
          onChange={e => setForm(f => ({ ...f, categoria: e.target.value }))}
          placeholder="Selecciona categoría"
          size="sm"
        >
          {(categorias || []).map(c => (
            <option key={c.id} value={c.id}>
              {c.nombre}
            </option>
          ))}
        </Select>
      </FormControl>

      {/* Descripción */}
      <FormControl isRequired>
        <FormLabel fontSize="sm">Descripción</FormLabel>
        <Input
          value={form.descripcion || ''}
          onChange={e => setForm(f => ({ ...f, descripcion: e.target.value }))}
          placeholder="Ej: Sueldo Juan Pérez junio 2026"
          size="sm"
        />
      </FormControl>

      {/* Monto + Moneda */}
      <SimpleGrid columns={2} spacing={3}>
        <FormControl isRequired>
          <FormLabel fontSize="sm">Monto</FormLabel>
          <NumberInput
            value={form.monto || ''}
            onChange={val => setForm(f => ({ ...f, monto: val }))}
            min={0}
            precision={2}
            size="sm"
          >
            <NumberInputField placeholder="0.00" />
            <NumberInputStepper>
              <NumberIncrementStepper />
              <NumberDecrementStepper />
            </NumberInputStepper>
          </NumberInput>
        </FormControl>

        <FormControl>
          <FormLabel fontSize="sm">Moneda</FormLabel>
          <ButtonGroup size="sm" isAttached variant="outline" w="full">
            <Button
              flex="1"
              colorScheme={form.moneda === 'PEN' ? 'blue' : 'gray'}
              variant={form.moneda === 'PEN' ? 'solid' : 'outline'}
              onClick={() => setForm(f => ({ ...f, moneda: 'PEN' }))}
            >
              PEN
            </Button>
            <Button
              flex="1"
              colorScheme={form.moneda === 'USD' ? 'blue' : 'gray'}
              variant={form.moneda === 'USD' ? 'solid' : 'outline'}
              onClick={() => setForm(f => ({ ...f, moneda: 'USD' }))}
            >
              USD
            </Button>
          </ButtonGroup>
        </FormControl>
      </SimpleGrid>

      {/* Fecha */}
      <FormControl isRequired>
        <FormLabel fontSize="sm">Fecha</FormLabel>
        <Input
          type="date"
          value={form.fecha || todayISO()}
          onChange={e => setForm(f => ({ ...f, fecha: e.target.value }))}
          size="sm"
        />
      </FormControl>

      {/* Proveedor */}
      <FormControl>
        <FormLabel fontSize="sm">Proveedor <Text as="span" color="gray.400" fontWeight="normal">(opcional)</Text></FormLabel>
        <Input
          value={form.proveedor || ''}
          onChange={e => setForm(f => ({ ...f, proveedor: e.target.value }))}
          placeholder="¿A quién le pagaste?"
          size="sm"
        />
      </FormControl>

      {/* Comprobante tipo */}
      <FormControl>
        <FormLabel fontSize="sm">Tipo de comprobante</FormLabel>
        <Select
          value={form.comprobante_tipo || 'sin_comprobante'}
          onChange={e => setForm(f => ({ ...f, comprobante_tipo: e.target.value, numero_comprobante: '' }))}
          size="sm"
        >
          <option value="factura">Factura</option>
          <option value="boleta">Boleta</option>
          <option value="recibo_honorarios">Recibo x Hon.</option>
          <option value="sin_comprobante">Sin comprobante</option>
        </Select>
      </FormControl>

      {/* N° comprobante — solo si no es sin comprobante */}
      {tieneComprobante && (
        <FormControl>
          <FormLabel fontSize="sm">N° de comprobante</FormLabel>
          <Input
            value={form.numero_comprobante || ''}
            onChange={e => setForm(f => ({ ...f, numero_comprobante: e.target.value }))}
            placeholder="Ej: F001-00123"
            size="sm"
          />
        </FormControl>
      )}

      {/* Estado */}
      <FormControl>
        <FormLabel fontSize="sm">Estado</FormLabel>
        <RadioGroup
          value={form.estado || 'pagado'}
          onChange={val => setForm(f => ({ ...f, estado: val }))}
        >
          <Stack direction="row" spacing={4}>
            <Radio value="pagado" colorScheme="green" size="sm">Pagado</Radio>
            <Radio value="pendiente" colorScheme="yellow" size="sm">Pendiente</Radio>
            <Radio value="programado" colorScheme="gray" size="sm">Programado</Radio>
          </Stack>
        </RadioGroup>
      </FormControl>

      {/* Adjunto */}
      <FormControl>
        <FormLabel fontSize="sm">Adjunto <Text as="span" color="gray.400" fontWeight="normal">(opcional)</Text></FormLabel>
        <Input
          type="file"
          accept=".pdf,.jpg,.jpeg,.png"
          size="sm"
          p={1}
          onChange={e => setForm(f => ({ ...f, adjunto: e.target.files?.[0] || null }))}
        />
      </FormControl>
    </VStack>
  );
};

// ─── Modal Gasto ──────────────────────────────────────────────────────────────
const ModalGasto = ({ isOpen, onClose, gastoEditar, categorias, onSaved }) => {
  const [form, setForm] = useState({
    categoria: '',
    descripcion: '',
    monto: '',
    moneda: 'PEN',
    fecha: todayISO(),
    proveedor: '',
    comprobante_tipo: 'sin_comprobante',
    numero_comprobante: '',
    estado: 'pagado',
    adjunto: null,
  });
  const toast = useToast();
  const queryClient = useQueryClient();

  React.useEffect(() => {
    if (isOpen) {
      if (gastoEditar) {
        setForm({
          categoria: gastoEditar.categoria || '',
          descripcion: gastoEditar.descripcion || '',
          monto: String(gastoEditar.monto || ''),
          moneda: gastoEditar.moneda || 'PEN',
          fecha: gastoEditar.fecha || todayISO(),
          proveedor: gastoEditar.proveedor || '',
          comprobante_tipo: gastoEditar.comprobante_tipo || 'sin_comprobante',
          numero_comprobante: gastoEditar.numero_comprobante || '',
          estado: gastoEditar.estado || 'pagado',
          adjunto: null,
        });
      } else {
        setForm({
          categoria: '',
          descripcion: '',
          monto: '',
          moneda: 'PEN',
          fecha: todayISO(),
          proveedor: '',
          comprobante_tipo: 'sin_comprobante',
          numero_comprobante: '',
          estado: 'pagado',
          adjunto: null,
        });
      }
    }
  }, [isOpen, gastoEditar]);

  const buildPayload = () => {
    if (form.adjunto) {
      const fd = new FormData();
      Object.entries(form).forEach(([k, v]) => {
        if (k === 'adjunto' && v) fd.append(k, v);
        else if (v !== null && v !== undefined && v !== '') fd.append(k, v);
      });
      return fd;
    }
    const { adjunto, ...rest } = form;
    return rest;
  };

  const mutation = useMutation({
    mutationFn: (data) =>
      gastoEditar
        ? gastosService.updateGasto(gastoEditar.id, data)
        : gastosService.createGasto(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gastos'] });
      queryClient.invalidateQueries({ queryKey: ['gastos-resumen'] });
      toast({
        title: gastoEditar ? 'Gasto actualizado' : 'Gasto registrado',
        status: 'success',
        duration: 2500,
        isClosable: true,
      });
      onSaved?.();
    },
    onError: () => {
      toast({
        title: 'Error al guardar el gasto',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    },
  });

  const handleSave = (andNew = false) => {
    if (!form.categoria || !form.descripcion || !form.monto) {
      toast({ title: 'Completa los campos requeridos', status: 'warning', duration: 2500 });
      return;
    }
    mutation.mutate(buildPayload(), {
      onSuccess: () => {
        if (andNew) {
          setForm({
            categoria: form.categoria,
            descripcion: '',
            monto: '',
            moneda: form.moneda,
            fecha: form.fecha,
            proveedor: '',
            comprobante_tipo: 'sin_comprobante',
            numero_comprobante: '',
            estado: 'pagado',
            adjunto: null,
          });
        } else {
          onClose();
        }
      },
    });
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="md" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader fontSize="md">
          {gastoEditar ? 'Editar gasto' : 'Nuevo gasto'}
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={2}>
          <GastoForm form={form} setForm={setForm} categorias={categorias} />
        </ModalBody>
        <ModalFooter gap={2}>
          <Button size="sm" variant="ghost" onClick={onClose}>Cancelar</Button>
          {!gastoEditar && (
            <Button
              size="sm"
              variant="outline"
              colorScheme="blue"
              isLoading={mutation.isPending}
              onClick={() => handleSave(true)}
            >
              Guardar y otro
            </Button>
          )}
          <Button
            size="sm"
            colorScheme="blue"
            isLoading={mutation.isPending}
            onClick={() => handleSave(false)}
          >
            Guardar
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

// ─── Modal Recurrentes ────────────────────────────────────────────────────────
const FORM_RECURRENTE_INIT = {
  categoria: '',
  descripcion: '',
  monto: '',
  moneda: 'PEN',
  proveedor: '',
  frecuencia: 'mensual',
  dia_del_mes: 1,
  estado: 'pagado',
};

const ModalRecurrentes = ({ isOpen, onClose, categorias }) => {
  const [showNuevo, setShowNuevo] = useState(false);
  const [form, setForm] = useState(FORM_RECURRENTE_INIT);
  const toast = useToast();
  const queryClient = useQueryClient();

  const { data: recurrentes, isLoading } = useQuery({
    queryKey: ['recurrentes'],
    queryFn: gastosService.getRecurrentes,
    enabled: isOpen,
  });

  const crearMutation = useMutation({
    mutationFn: gastosService.createRecurrente,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurrentes'] });
      setShowNuevo(false);
      setForm(FORM_RECURRENTE_INIT);
      toast({ title: 'Gasto recurrente creado', status: 'success', duration: 2000 });
    },
    onError: () => {
      toast({ title: 'Error al crear recurrente', status: 'error', duration: 3000 });
    },
  });

  const generarMutation = useMutation({
    mutationFn: (id) => gastosService.generarMes(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gastos'] });
      queryClient.invalidateQueries({ queryKey: ['gastos-resumen'] });
      toast({ title: 'Gastos del mes generados', status: 'success', duration: 2000 });
    },
    onError: () => {
      toast({ title: 'Error al generar gastos', status: 'error', duration: 3000 });
    },
  });

  const handleCrear = () => {
    if (!form.categoria || !form.descripcion || !form.monto) {
      toast({ title: 'Completa los campos requeridos', status: 'warning', duration: 2500 });
      return;
    }
    crearMutation.mutate(form);
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader fontSize="md">Gastos Recurrentes</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          {!showNuevo ? (
            <VStack spacing={3} align="stretch">
              <Button
                size="sm"
                leftIcon={<FiPlus />}
                colorScheme="blue"
                variant="outline"
                alignSelf="flex-start"
                onClick={() => setShowNuevo(true)}
              >
                Nuevo recurrente
              </Button>

              {isLoading && (
                <VStack spacing={2}>
                  <Skeleton h="60px" borderRadius="md" />
                  <Skeleton h="60px" borderRadius="md" />
                </VStack>
              )}

              {!isLoading && (!recurrentes || recurrentes.length === 0) && (
                <Box textAlign="center" py={8}>
                  <FiRepeat size={28} style={{ margin: '0 auto 8px', color: '#9ca3af' }} />
                  <Text color="gray.400" fontSize="sm">No hay gastos recurrentes configurados.</Text>
                  <Text color="gray.400" fontSize="xs" mt={1}>
                    Agrégalos para no tener que ingresarlos cada mes.
                  </Text>
                </Box>
              )}

              {(recurrentes || []).map((r) => (
                <Box
                  key={r.id}
                  border="1px solid"
                  borderColor="gray.200"
                  borderRadius="lg"
                  p={4}
                >
                  <Flex justify="space-between" align="center">
                    <VStack align="flex-start" spacing={0}>
                      <Text fontSize="sm" fontWeight="semibold">{r.descripcion}</Text>
                      <Text fontSize="xs" color="gray.400">
                        {fmtCurrency(r.monto, r.moneda || 'PEN')} · Día {r.dia_del_mes} de cada mes
                      </Text>
                    </VStack>
                    <Button
                      size="xs"
                      colorScheme="green"
                      variant="outline"
                      leftIcon={<FiRepeat size={11} />}
                      isLoading={generarMutation.isPending}
                      onClick={() => generarMutation.mutate(r.id)}
                    >
                      Generar este mes
                    </Button>
                  </Flex>
                </Box>
              ))}
            </VStack>
          ) : (
            <VStack spacing={4} align="stretch">
              <Button size="xs" variant="link" colorScheme="gray" alignSelf="flex-start" onClick={() => setShowNuevo(false)}>
                ← Volver a la lista
              </Button>
              <GastoForm form={form} setForm={setForm} categorias={categorias} />

              <SimpleGrid columns={2} spacing={3}>
                <FormControl>
                  <FormLabel fontSize="sm">Frecuencia</FormLabel>
                  <Select
                    value={form.frecuencia}
                    onChange={e => setForm(f => ({ ...f, frecuencia: e.target.value }))}
                    size="sm"
                  >
                    <option value="mensual">Mensual</option>
                    <option value="quincenal">Quincenal</option>
                    <option value="semanal">Semanal</option>
                  </Select>
                </FormControl>
                <FormControl>
                  <FormLabel fontSize="sm">Día del mes</FormLabel>
                  <NumberInput
                    value={form.dia_del_mes}
                    onChange={val => setForm(f => ({ ...f, dia_del_mes: Number(val) }))}
                    min={1} max={31} size="sm"
                  >
                    <NumberInputField />
                    <NumberInputStepper>
                      <NumberIncrementStepper />
                      <NumberDecrementStepper />
                    </NumberInputStepper>
                  </NumberInput>
                </FormControl>
              </SimpleGrid>
            </VStack>
          )}
        </ModalBody>
        {showNuevo && (
          <ModalFooter gap={2}>
            <Button size="sm" variant="ghost" onClick={() => setShowNuevo(false)}>Cancelar</Button>
            <Button
              size="sm"
              colorScheme="blue"
              isLoading={crearMutation.isPending}
              onClick={handleCrear}
            >
              Crear recurrente
            </Button>
          </ModalFooter>
        )}
      </ModalContent>
    </Modal>
  );
};

// ─── Tabla de gastos ──────────────────────────────────────────────────────────
const TablaGastos = ({ gastos, categorias, onEditar, onEliminar, mesLabel: labelMes }) => {
  const border = useColorModeValue('gray.100', 'gray.700');
  const rowHover = useColorModeValue('gray.50', 'gray.800');

  const getCat = (id) => (categorias || []).find(c => String(c.id) === String(id));

  if (!gastos || gastos.length === 0) {
    return (
      <Box
        border="1px solid"
        borderColor={border}
        borderRadius="xl"
        p={10}
        textAlign="center"
      >
        <FiFileText size={36} style={{ margin: '0 auto 12px', color: '#9ca3af' }} />
        <Text color="gray.500" fontWeight="medium">No hay gastos en {labelMes}</Text>
        <Text color="gray.400" fontSize="sm" mt={1}>
          Agrega el primero usando el botón "+ Nuevo Gasto"
        </Text>
      </Box>
    );
  }

  return (
    <Box border="1px solid" borderColor={border} borderRadius="xl" overflow="hidden">
      {/* Table header */}
      <Box overflowX="auto">
        <Box minW="700px">
          <Flex
            bg={useColorModeValue('gray.50', 'gray.800')}
            borderBottom="1px solid"
            borderColor={border}
            px={4} py={2.5}
          >
            {['Categoría', 'Descripción', 'Proveedor', 'Fecha', 'Monto', 'Estado', ''].map((h, i) => (
              <Text
                key={i}
                fontSize="10px"
                fontWeight="semibold"
                color="gray.500"
                textTransform="uppercase"
                letterSpacing="wider"
                flex={[2, 3, 2, 1.5, 1.5, 1.2, 0.6][i]}
                minW={0}
              >
                {h}
              </Text>
            ))}
          </Flex>

          {gastos.map((g) => {
            const cat = getCat(g.categoria);
            return (
              <Flex
                key={g.id}
                px={4}
                py={3}
                align="center"
                borderBottom="1px solid"
                borderColor={border}
                _hover={{ bg: rowHover }}
                transition="background 0.1s"
              >
                {/* Categoría */}
                <Flex flex={2} align="center" gap={2} minW={0} pr={2}>
                  {cat ? (
                    <Tag
                      size="sm"
                      borderRadius="full"
                      bg={cat.color ? `${cat.color}20` : 'blue.50'}
                      color={cat.color || 'blue.700'}
                      border="1px solid"
                      borderColor={cat.color ? `${cat.color}40` : 'blue.200'}
                    >
                      <CatIcon icono={cat.icono} />
                      <TagLabel ml={1} fontSize="xs">{cat.nombre}</TagLabel>
                    </Tag>
                  ) : (
                    <Badge colorScheme="gray" fontSize="xs">Sin cat.</Badge>
                  )}
                </Flex>

                {/* Descripción */}
                <Text flex={3} fontSize="sm" noOfLines={1} minW={0} pr={2}>
                  {g.descripcion}
                </Text>

                {/* Proveedor */}
                <Text flex={2} fontSize="sm" color="gray.500" noOfLines={1} minW={0} pr={2}>
                  {g.proveedor || '—'}
                </Text>

                {/* Fecha */}
                <Text flex={1.5} fontSize="sm" color="gray.500" minW={0} pr={2}>
                  {g.fecha
                    ? new Date(g.fecha + 'T12:00:00').toLocaleDateString('es-PE', { day: '2-digit', month: 'short' })
                    : '—'}
                </Text>

                {/* Monto */}
                <Text flex={1.5} fontSize="sm" fontWeight="semibold" minW={0} pr={2} fontVariantNumeric="tabular-nums">
                  {fmtCurrency(g.monto, g.moneda || 'PEN')}
                </Text>

                {/* Estado */}
                <Box flex={1.2} pr={2}>
                  <Badge
                    colorScheme={ESTADO_COLOR[g.estado] || 'gray'}
                    fontSize="xs"
                    borderRadius="full"
                  >
                    {ESTADO_LABEL[g.estado] || g.estado}
                  </Badge>
                </Box>

                {/* Acciones */}
                <Box flex={0.6}>
                  <Menu>
                    <MenuButton
                      as={IconButton}
                      icon={<FiMoreVertical />}
                      size="xs"
                      variant="ghost"
                      aria-label="Acciones"
                    />
                    <MenuList minW="130px" fontSize="sm">
                      <MenuItem icon={<FiEdit2 size={13} />} onClick={() => onEditar(g)}>
                        Editar
                      </MenuItem>
                      <Divider />
                      <MenuItem
                        icon={<FiTrash2 size={13} />}
                        color="red.500"
                        onClick={() => onEliminar(g)}
                      >
                        Eliminar
                      </MenuItem>
                    </MenuList>
                  </Menu>
                </Box>
              </Flex>
            );
          })}
        </Box>
      </Box>
    </Box>
  );
};

// ─── Modal confirmar eliminación ──────────────────────────────────────────────
const ModalEliminar = ({ gasto, onClose, onConfirm, isLoading }) => (
  <Modal isOpen={!!gasto} onClose={onClose} size="sm">
    <ModalOverlay />
    <ModalContent>
      <ModalHeader fontSize="md">Eliminar gasto</ModalHeader>
      <ModalCloseButton />
      <ModalBody>
        <Text fontSize="sm">
          ¿Estás seguro de que quieres eliminar{' '}
          <Text as="span" fontWeight="semibold">"{gasto?.descripcion}"</Text>?
          Esta acción no se puede deshacer.
        </Text>
      </ModalBody>
      <ModalFooter gap={2}>
        <Button size="sm" variant="ghost" onClick={onClose}>Cancelar</Button>
        <Button size="sm" colorScheme="red" isLoading={isLoading} onClick={onConfirm}>
          Eliminar
        </Button>
      </ModalFooter>
    </ModalContent>
  </Modal>
);

// ─── GastosPage ───────────────────────────────────────────────────────────────
const GastosPage = () => {
  const now = new Date();
  const [mesActual, setMesActual] = useState({
    año: now.getFullYear(),
    mes: now.getMonth() + 1,
  });
  const [gastoEditar, setGastoEditar] = useState(null);
  const [gastoEliminar, setGastoEliminar] = useState(null);
  const [filtroCategoria, setFiltroCategoria] = useState('');
  const [filtroEstado, setFiltroEstado] = useState('');

  const { isOpen: isGastoOpen, onOpen: onGastoOpen, onClose: onGastoClose } = useDisclosure();
  const { isOpen: isRecurrenteOpen, onOpen: onRecurrenteOpen, onClose: onRecurrenteClose } = useDisclosure();

  const toast = useToast();
  const queryClient = useQueryClient();
  const bg = useColorModeValue('gray.50', 'gray.900');

  // Navegación de mes
  const navegarMes = (delta) => {
    setMesActual(prev => {
      let mes = prev.mes + delta;
      let año = prev.año;
      if (mes > 12) { mes = 1; año += 1; }
      if (mes < 1)  { mes = 12; año -= 1; }
      return { año, mes };
    });
  };

  const fechaQ = fechaParam(mesActual.año, mesActual.mes);

  // Queries
  const { data: categorias } = useQuery({
    queryKey: ['gastos-categorias'],
    queryFn: gastosService.getCategorias,
    staleTime: 10 * 60 * 1000,
  });

  const { data: gastosData, isLoading: isLoadingGastos } = useQuery({
    queryKey: ['gastos', mesActual.año, mesActual.mes, filtroCategoria, filtroEstado],
    queryFn: () => {
      const params = { fecha: fechaQ };
      if (filtroCategoria) params.categoria = filtroCategoria;
      if (filtroEstado) params.estado = filtroEstado;
      return gastosService.getGastos(params);
    },
    staleTime: 2 * 60 * 1000,
  });

  const { data: resumen, isLoading: isLoadingResumen } = useQuery({
    queryKey: ['gastos-resumen', mesActual.año, mesActual.mes],
    queryFn: () => gastosService.getResumen(fechaQ),
    staleTime: 2 * 60 * 1000,
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id) => gastosService.deleteGasto(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gastos'] });
      queryClient.invalidateQueries({ queryKey: ['gastos-resumen'] });
      toast({ title: 'Gasto eliminado', status: 'success', duration: 2000 });
      setGastoEliminar(null);
    },
    onError: () => {
      toast({ title: 'Error al eliminar el gasto', status: 'error', duration: 3000 });
    },
  });

  // gastos list (may come as array or paginated)
  const gastosList = Array.isArray(gastosData)
    ? gastosData
    : (gastosData?.results ?? []);

  // Sorted descending by date
  const gastosOrdenados = [...gastosList].sort((a, b) =>
    (b.fecha || '').localeCompare(a.fecha || '')
  );

  const label = mesLabel(mesActual.año, mesActual.mes);

  // Resumen values
  const totalMes       = resumen?.total_gastos ?? 0;
  const gastosFijos    = resumen?.total_fijos ?? 0;
  const gastosVariables = resumen?.total_variables ?? 0;
  const utilidadNeta   = resumen?.utilidad_neta_del_periodo ?? null;
  const distribucion   = resumen?.por_categoria ?? [];
  const tendenciaVsMes = resumen?.variacion_pct ?? null;

  const utilidadNegativa = utilidadNeta !== null && utilidadNeta < 0;

  const handleEditar = (gasto) => {
    setGastoEditar(gasto);
    onGastoOpen();
  };

  const handleNuevo = () => {
    setGastoEditar(null);
    onGastoOpen();
  };

  const handleCloseGasto = () => {
    setGastoEditar(null);
    onGastoClose();
  };

  return (
    <Box bg={bg} minH="100vh" px={{ base: 4, md: 6 }} py={6}>

      {/* ── Header ── */}
      <Flex justify="space-between" align="center" mb={6} wrap="wrap" gap={3}>
        <Heading size="lg" fontWeight="semibold">Gastos Operativos</Heading>
        <HStack spacing={3} wrap="wrap">
          {/* Navegador de mes */}
          <HStack spacing={1}>
            <IconButton
              icon={<FiChevronLeft />}
              size="sm"
              variant="ghost"
              aria-label="Mes anterior"
              onClick={() => navegarMes(-1)}
            />
            <Text fontSize="sm" fontWeight="medium" minW="140px" textAlign="center">
              {label.charAt(0).toUpperCase() + label.slice(1)}
            </Text>
            <IconButton
              icon={<FiChevronRight />}
              size="sm"
              variant="ghost"
              aria-label="Mes siguiente"
              onClick={() => navegarMes(1)}
            />
          </HStack>

          <Button
            size="sm"
            leftIcon={<FiRepeat size={14} />}
            variant="outline"
            onClick={onRecurrenteOpen}
          >
            Recurrentes
          </Button>

          <Button
            size="sm"
            leftIcon={<FiPlus size={14} />}
            colorScheme="blue"
            onClick={handleNuevo}
          >
            Nuevo Gasto
          </Button>
        </HStack>
      </Flex>

      {/* ── Stat cards ── */}
      {isLoadingResumen ? (
        <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4} mb={6}>
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} h="100px" borderRadius="xl" />
          ))}
        </SimpleGrid>
      ) : (
        <>
          {utilidadNegativa && (
            <Alert status="error" borderRadius="xl" mb={4} fontSize="sm">
              <AlertIcon />
              <AlertDescription>
                Los gastos superan los ingresos del período. Revisa tu estructura de costos.
              </AlertDescription>
            </Alert>
          )}
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4} mb={6}>
            <StatCard
              label="Total del mes"
              value={fmtCurrency(totalMes)}
              sub={tendenciaVsMes !== null
                ? `${tendenciaVsMes >= 0 ? '+' : ''}${tendenciaVsMes.toFixed(1)}% vs mes ant.`
                : 'Total de gastos'}
              colorScheme="blue"
            />
            <StatCard
              label="Gastos fijos"
              value={fmtCurrency(gastosFijos)}
              sub="Lo que pagas sí o sí"
              colorScheme="orange"
            />
            <StatCard
              label="Gastos variables"
              value={fmtCurrency(gastosVariables)}
              sub="Lo que puedes optimizar"
              colorScheme="green"
            />
            <StatCard
              label="Utilidad neta"
              value={utilidadNeta !== null ? fmtCurrency(utilidadNeta) : '—'}
              sub="Lo que realmente te queda"
              colorScheme={utilidadNegativa ? 'red' : 'purple'}
              alerta={utilidadNegativa ? 'Gastos superan ingresos del período' : undefined}
            />
          </SimpleGrid>
        </>
      )}

      {/* ── Barra de distribución ── */}
      {distribucion.length > 0 && (
        <Box
          bg="white"
          border="1px solid"
          borderColor={useColorModeValue('gray.100', 'gray.700')}
          borderRadius="xl"
          p={5}
          mb={6}
        >
          <DistribucionBar distribucion={distribucion} />
        </Box>
      )}

      {/* ── Filtros ── */}
      <Flex gap={3} mb={4} wrap="wrap" align="center">
        <Text fontSize="sm" fontWeight="medium" color="gray.600">Filtrar:</Text>
        <Select
          size="sm"
          value={filtroCategoria}
          onChange={e => setFiltroCategoria(e.target.value)}
          placeholder="Todas las categorías"
          w="200px"
          borderRadius="lg"
        >
          {(categorias || []).map(c => (
            <option key={c.id} value={c.id}>{c.nombre}</option>
          ))}
        </Select>
        <Select
          size="sm"
          value={filtroEstado}
          onChange={e => setFiltroEstado(e.target.value)}
          placeholder="Todos los estados"
          w="180px"
          borderRadius="lg"
        >
          <option value="pagado">Pagado</option>
          <option value="pendiente">Pendiente</option>
          <option value="programado">Programado</option>
        </Select>
        {(filtroCategoria || filtroEstado) && (
          <Button
            size="sm"
            variant="ghost"
            colorScheme="gray"
            onClick={() => { setFiltroCategoria(''); setFiltroEstado(''); }}
          >
            Limpiar filtros
          </Button>
        )}
      </Flex>

      {/* ── Tabla de gastos ── */}
      {isLoadingGastos ? (
        <VStack spacing={2} align="stretch">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} h="52px" borderRadius="lg" />
          ))}
        </VStack>
      ) : (
        <TablaGastos
          gastos={gastosOrdenados}
          categorias={categorias}
          onEditar={handleEditar}
          onEliminar={setGastoEliminar}
          mesLabel={label}
        />
      )}

      {/* ── Modales ── */}
      <ModalGasto
        isOpen={isGastoOpen}
        onClose={handleCloseGasto}
        gastoEditar={gastoEditar}
        categorias={categorias}
        onSaved={() => {}}
      />

      <ModalRecurrentes
        isOpen={isRecurrenteOpen}
        onClose={onRecurrenteClose}
        categorias={categorias}
      />

      <ModalEliminar
        gasto={gastoEliminar}
        onClose={() => setGastoEliminar(null)}
        onConfirm={() => gastoEliminar && deleteMutation.mutate(gastoEliminar.id)}
        isLoading={deleteMutation.isPending}
      />
    </Box>
  );
};

export default GastosPage;
