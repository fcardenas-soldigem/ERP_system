import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  VStack,
  HStack,
  FormControl,
  FormLabel,
  Input,
  Button,
  Select,
  NumberInput,
  NumberInputField,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  IconButton,
  useToast,
  Box,
  Text,
  Switch,
  FormHelperText,
  Spinner,
  Heading,
  Grid,
  GridItem,
  Flex,
  Textarea,
  Divider,
  InputGroup,
  InputRightElement,
} from '@chakra-ui/react';
import { FaPlus, FaTrash, FaSave, FaArrowLeft, FaSearch } from 'react-icons/fa';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { comprasService } from '../../services/compras.service';
import { proveedoresService } from '../../services/proveedores.service';
import { TIPOS_COMPRA_DISPLAY, METODOS_PAGO_DISPLAY } from './constants';
import { addDays } from 'date-fns';

const CompraForm = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [formData, setFormData] = useState({
    proveedor: '',
    almacen: '',
    fecha_emision: new Date().toISOString().split('T')[0],
    fecha_vencimiento: null,
    estado: 'pagada',
    tipo_compra: 'contado',
    metodo_pago: 'efectivo',
    igv_incluido: false,
    porcentaje_igv: 18,
    moneda: 'USD',
    referencia: '',
    comprobante: null,
    forma_pago: 'Contado',
    tiempo_entrega: '',
    lugar_entrega: '',
    notas: '',
    terminos_condiciones: '',
    detalles: [{ producto: '', cantidad: 1, precio_unitario: 0, descuento_item: 0 }],
  });

  // Descuento global
  const [descuento_tipo, setDescuentoTipo] = useState('porcentaje');
  const [descuento_valor, setDescuentoValor] = useState(0);

  // Proveedor search
  const [busquedaProveedor, setBusquedaProveedor] = useState('');
  const [resultadosProveedores, setResultadosProveedores] = useState([]);
  const [mostrarResultados, setMostrarResultados] = useState(false);
  const [proveedores, setProveedores] = useState([]);
  const dropdownRef = useRef(null);

  const { data: almacenesData = [], isLoading: isLoadingAlmacenes } = useQuery({
    queryKey: ['almacenes'],
    queryFn: () => comprasService.getAlmacenes(),
  });
  const almacenes = Array.isArray(almacenesData) ? almacenesData : [];

  const { data: productosData = [] } = useQuery({
    queryKey: ['productos'],
    queryFn: () => comprasService.getProductos(),
  });
  const productos = Array.isArray(productosData) ? productosData : [];

  useEffect(() => {
    queryClient.invalidateQueries(['proveedores']);
    queryClient.invalidateQueries(['productos']);
    const cargarProveedores = async () => {
      try {
        const data = await proveedoresService.getProveedores();
        setProveedores(Array.isArray(data) ? data : []);
      } catch {
        setProveedores([]);
      }
    };
    cargarProveedores();
  }, [queryClient]);

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
        p => (p.nombre || '').toLowerCase().includes(normed) ||
             (p.ruc || '').includes(normed) ||
             (p.razon_social || '').toLowerCase().includes(normed)
      ).slice(0, 8);
      setResultadosProveedores(filtered);
      setMostrarResultados(true);
    } else {
      setResultadosProveedores([]);
      setMostrarResultados(false);
    }
  }, [proveedores]);

  const seleccionarProveedor = (p) => {
    setFormData(prev => ({ ...prev, proveedor: p.id }));
    setBusquedaProveedor('');
    setMostrarResultados(false);
  };

  const crearCompraMutation = useMutation({
    mutationFn: comprasService.createCompra,
    onSuccess: () => {
      queryClient.invalidateQueries(['compras']);
      queryClient.invalidateQueries(['productos']);
      toast({ title: 'Compra creada exitosamente', status: 'success', duration: 2000 });
      navigate('/app/compras');
    },
    onError: (error) => {
      toast({ title: 'Error', description: error.message, status: 'error', duration: 3000 });
    },
  });

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
  };

  const handleDetalleChange = (index, field, value) => {
    const newDetalles = [...formData.detalles];
    if (field === 'cantidad' || field === 'precio_unitario' || field === 'descuento_item') {
      value = value === '' ? '' : Number(value);
    } else if (field === 'producto') {
      value = value === '' ? '' : String(value);
      const producto = productos.find(p => p.id === parseInt(value));
      if (producto) {
        newDetalles[index] = {
          ...newDetalles[index],
          producto: value,
          precio_unitario: Number(producto.precio_compra) || 0,
        };
        setFormData(prev => ({ ...prev, detalles: newDetalles }));
        return;
      }
    }
    newDetalles[index] = { ...newDetalles[index], [field]: value };
    setFormData(prev => ({ ...prev, detalles: newDetalles }));
  };

  const agregarProducto = () => {
    setFormData(prev => ({
      ...prev,
      detalles: [...prev.detalles, { producto: '', cantidad: 1, precio_unitario: 0, descuento_item: 0 }],
    }));
  };

  const eliminarProducto = (index) => {
    if (formData.detalles.length > 1) {
      setFormData(prev => ({
        ...prev,
        detalles: prev.detalles.filter((_, i) => i !== index),
      }));
    }
  };

  const calcularSubtotalDetalle = (d) => {
    const sub = ((d.cantidad || 0) * (d.precio_unitario || 0)) - (d.descuento_item || 0);
    return sub > 0 ? sub : 0;
  };

  const calcularTotales = () => {
    const subtotal = formData.detalles.reduce((sum, d) => sum + calcularSubtotalDetalle(d), 0);

    const montoDesc = descuento_tipo === 'porcentaje'
      ? subtotal * ((parseFloat(descuento_valor) || 0) / 100)
      : Math.min(parseFloat(descuento_valor) || 0, subtotal);

    const subtotalConDescuento = Math.max(0, subtotal - montoDesc);

    let baseImponible, igv, total;
    if (formData.igv_incluido) {
      baseImponible = subtotalConDescuento / (1 + (formData.porcentaje_igv / 100));
      igv = subtotalConDescuento - baseImponible;
      total = subtotalConDescuento;
    } else {
      baseImponible = subtotalConDescuento;
      igv = subtotalConDescuento * (formData.porcentaje_igv / 100);
      total = subtotalConDescuento + igv;
    }

    return {
      subtotal: subtotal.toFixed(2),
      montoDescuento: montoDesc.toFixed(2),
      baseImponible: Math.max(0, baseImponible).toFixed(2),
      igv: Math.max(0, igv).toFixed(2),
      total: Math.max(0, total).toFixed(2),
    };
  };

  const handleDescuentoValorChange = (v) => {
    const val = parseFloat(v) || 0;
    const t = calcularTotales();
    if (descuento_tipo === 'porcentaje' && val > 100) return;
    if (descuento_tipo === 'monto' && val > parseFloat(t.subtotal)) return;
    setDescuentoValor(val);
  };

  const handleTipoCompraChange = (e) => {
    const { value } = e.target;
    let fecha_vencimiento = null;
    let nuevoEstado = 'pagada';
    if (value === 'credito_30') {
      fecha_vencimiento = addDays(new Date(formData.fecha_emision), 30).toISOString().split('T')[0];
      nuevoEstado = 'pendiente';
    } else if (value === 'credito_60') {
      fecha_vencimiento = addDays(new Date(formData.fecha_emision), 60).toISOString().split('T')[0];
      nuevoEstado = 'pendiente';
    }
    setFormData(prev => ({ ...prev, tipo_compra: value, fecha_vencimiento, estado: nuevoEstado }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (isSubmitting) return;
    setIsSubmitting(true);

    try {
      if (!formData.proveedor) {
        toast({ title: 'Error', description: 'Debe seleccionar un proveedor', status: 'error', duration: 2000 });
        return;
      }
      if (!formData.almacen) {
        toast({ title: 'Error', description: 'Debe seleccionar un almacén', status: 'error', duration: 2000 });
        return;
      }
      const detallesInvalidos = formData.detalles.some(
        d => !d.producto || !d.cantidad || d.cantidad <= 0 || !d.precio_unitario || d.precio_unitario <= 0,
      );
      if (detallesInvalidos) {
        toast({ title: 'Error', description: 'Todos los productos deben tener cantidad y precio mayor a 0', status: 'error', duration: 2000 });
        return;
      }

      const detalles = formData.detalles
        .filter(d => d.producto && d.cantidad && d.precio_unitario)
        .map(d => ({ producto: parseInt(d.producto), cantidad: parseFloat(d.cantidad), precio_unitario: parseFloat(d.precio_unitario) }));

      const compraDataToSend = new FormData();
      compraDataToSend.append('proveedor', formData.proveedor);
      compraDataToSend.append('almacen', formData.almacen);
      compraDataToSend.append('fecha_emision', formData.fecha_emision);
      compraDataToSend.append('tipo_compra', formData.tipo_compra);
      compraDataToSend.append('estado', formData.estado);
      compraDataToSend.append('metodo_pago', formData.metodo_pago);
      compraDataToSend.append('igv_incluido', String(formData.igv_incluido));
      compraDataToSend.append('moneda', formData.moneda);
      compraDataToSend.append('referencia', formData.referencia || '');
      compraDataToSend.append('detalles', JSON.stringify(detalles));
      if (formData.tipo_compra !== 'contado' && formData.fecha_vencimiento) {
        compraDataToSend.append('fecha_vencimiento', formData.fecha_vencimiento);
      }
      if (formData.comprobante) {
        compraDataToSend.append('comprobante', formData.comprobante);
      }

      await crearCompraMutation.mutateAsync(compraDataToSend);
    } catch (error) {
      console.error('Error al crear la compra:', error);
      toast({ title: 'Error', description: error.message || 'Error al crear la compra', status: 'error', duration: 2000 });
    } finally {
      setIsSubmitting(false);
    }
  };

  const totales = calcularTotales();
  const simbolo = formData.moneda === 'USD' ? '$' : 'S/';

  return (
    <Box p={6}>
      <Flex justify="space-between" align="center" mb={6}>
        <Heading size="lg">Nueva Factura de Compra</Heading>
        <Button leftIcon={<FaArrowLeft />} variant="ghost" onClick={() => navigate('/app/compras')}>
          Volver
        </Button>
      </Flex>

      <form onSubmit={handleSubmit}>
        <VStack spacing={6} align="stretch">

          {/* ── Información del Proveedor ── */}
          <Box bg="white" p={6} borderRadius="lg" shadow="sm">
            <Heading size="md" mb={4}>Información del Proveedor</Heading>
            <Grid templateColumns="repeat(2, 1fr)" gap={4}>

              <GridItem colSpan={2}>
                <FormControl>
                  <FormLabel>Buscar Proveedor Existente</FormLabel>
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
                              key={p.id} py={2} px={3} cursor="pointer"
                              _hover={{ bg: 'blue.50' }}
                              onClick={() => seleccionarProveedor(p)}
                              borderBottom="1px solid" borderColor="gray.100"
                              _last={{ borderBottom: 'none' }}
                            >
                              <Text fontSize="sm" fontWeight="bold">{p.nombre || p.razon_social}</Text>
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
                      value={formData.proveedor}
                      onChange={(e) => setFormData(prev => ({ ...prev, proveedor: e.target.value }))}
                      placeholder="Seleccione un proveedor"
                    >
                      {proveedores.map(p => (
                        <option key={p.id} value={p.id}>
                          {p.nombre || p.razon_social} {p.ruc ? `- ${p.ruc}` : ''}
                        </option>
                      ))}
                    </Select>
                  ) : (
                    <Spinner size="sm" />
                  )}
                </FormControl>
              </GridItem>

              <FormControl isRequired>
                <FormLabel>Almacén</FormLabel>
                {isLoadingAlmacenes ? (
                  <Spinner size="sm" />
                ) : (
                  <Select
                    value={formData.almacen}
                    onChange={handleChange}
                    name="almacen"
                    placeholder="Seleccione un almacén"
                  >
                    {almacenes.map(a => (
                      <option key={a.id} value={a.id}>{a.nombre}</option>
                    ))}
                  </Select>
                )}
              </FormControl>

              <FormControl>
                <FormLabel>Referencia de Pago</FormLabel>
                <Input
                  name="referencia"
                  value={formData.referencia}
                  onChange={handleChange}
                  placeholder="Número de operación, cheque, etc."
                />
              </FormControl>
            </Grid>
          </Box>

          {/* ── Configuración ── */}
          <Box bg="white" p={6} borderRadius="lg" shadow="sm">
            <Heading size="md" mb={4}>Configuración</Heading>
            <Grid templateColumns="repeat(3, 1fr)" gap={4}>
              <FormControl isRequired>
                <FormLabel>Fecha de Emisión</FormLabel>
                <Input type="date" name="fecha_emision" value={formData.fecha_emision} onChange={handleChange} />
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Tipo de Compra</FormLabel>
                <Select value={formData.tipo_compra} onChange={handleTipoCompraChange} name="tipo_compra">
                  {Object.entries(TIPOS_COMPRA_DISPLAY).map(([v, l]) => (
                    <option key={v} value={v}>{l}</option>
                  ))}
                </Select>
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Método de Pago</FormLabel>
                <Select value={formData.metodo_pago} onChange={handleChange} name="metodo_pago">
                  {Object.entries(METODOS_PAGO_DISPLAY).map(([v, l]) => (
                    <option key={v} value={v}>{l}</option>
                  ))}
                </Select>
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Moneda</FormLabel>
                <Select name="moneda" value={formData.moneda} onChange={handleChange}>
                  <option value="USD">Dólares ($)</option>
                  <option value="PEN">Soles (S/)</option>
                </Select>
              </FormControl>

              <FormControl>
                <FormLabel>Estado</FormLabel>
                <Select value={formData.estado} onChange={handleChange} name="estado">
                  <option value="borrador">Borrador</option>
                  <option value="pendiente">Pendiente</option>
                  <option value="pagada">Pagada</option>
                  <option value="anulada">Anulada</option>
                </Select>
              </FormControl>

              <FormControl>
                <FormLabel>Comprobante</FormLabel>
                <Input
                  type="file"
                  onChange={(e) => setFormData(prev => ({ ...prev, comprobante: e.target.files[0] }))}
                  accept=".pdf,.jpg,.jpeg,.png"
                  pt={1}
                  sx={{
                    '::file-selector-button': {
                      height: '32px', px: 4, bg: 'gray.100', border: 'none',
                      borderRight: '1px solid', borderColor: 'gray.200', cursor: 'pointer',
                      _hover: { bg: 'gray.200' },
                    },
                  }}
                />
              </FormControl>

              {formData.tipo_compra !== 'contado' && (
                <FormControl>
                  <FormLabel>Fecha de Vencimiento</FormLabel>
                  <Input type="date" value={formData.fecha_vencimiento || ''} isReadOnly />
                  <FormHelperText>Calculada según el plazo de crédito</FormHelperText>
                </FormControl>
              )}

              <FormControl display="flex" flexDirection="column" alignItems="flex-start">
                <HStack spacing={3} mb={1}>
                  <FormLabel mb="0">IGV Incluido en Precio</FormLabel>
                  <Switch
                    isChecked={formData.igv_incluido}
                    onChange={(e) => setFormData(prev => ({ ...prev, igv_incluido: e.target.checked }))}
                    colorScheme="green"
                  />
                </HStack>
                <Text fontSize="xs" color="gray.600">
                  {formData.igv_incluido
                    ? '✓ Los precios ya incluyen IGV'
                    : '✗ El IGV se sumará a los precios'}
                </Text>
              </FormControl>

              <FormControl>
                <FormLabel>Porcentaje IGV (%)</FormLabel>
                <NumberInput
                  value={formData.porcentaje_igv}
                  onChange={(v) => setFormData(prev => ({ ...prev, porcentaje_igv: parseFloat(v) || 18 }))}
                  min={0} max={100}
                >
                  <NumberInputField />
                </NumberInput>
              </FormControl>
            </Grid>
          </Box>

          {/* ── Productos ── */}
          <Box bg="white" p={6} borderRadius="lg" shadow="sm">
            <Flex justify="space-between" align="center" mb={4}>
              <Heading size="md">Productos</Heading>
              <Button leftIcon={<FaPlus />} colorScheme="blue" size="sm" onClick={agregarProducto}>
                Agregar Producto
              </Button>
            </Flex>

            {formData.detalles.length === 0 ? (
              <Text color="gray.500" textAlign="center" py={4}>
                No hay productos. Haga clic en "Agregar Producto" para comenzar.
              </Text>
            ) : (
              <Box overflowX="auto">
                <Table size="sm">
                  <Thead>
                    <Tr>
                      <Th>Producto</Th>
                      <Th>Cant.</Th>
                      <Th>P. Unit. ({simbolo})</Th>
                      <Th>Desc.</Th>
                      <Th>Subtotal</Th>
                      <Th></Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {formData.detalles.map((det, i) => (
                      <Tr key={i}>
                        <Td minW="200px">
                          <Select
                            size="sm"
                            value={det.producto ? det.producto.toString() : ''}
                            onChange={(e) => handleDetalleChange(i, 'producto', e.target.value)}
                            placeholder="Seleccionar"
                          >
                            {productos.map(p => (
                              <option key={p.id} value={p.id}>{p.nombre} - {p.sku}</option>
                            ))}
                          </Select>
                        </Td>
                        <Td minW="90px">
                          <NumberInput
                            size="sm" min={1}
                            value={det.cantidad || 1}
                            onChange={(v) => handleDetalleChange(i, 'cantidad', v)}
                          >
                            <NumberInputField />
                          </NumberInput>
                        </Td>
                        <Td minW="120px">
                          <NumberInput
                            size="sm" min={0} precision={2}
                            value={det.precio_unitario || 0}
                            onChange={(v) => handleDetalleChange(i, 'precio_unitario', v)}
                          >
                            <NumberInputField />
                          </NumberInput>
                        </Td>
                        <Td minW="90px">
                          <NumberInput
                            size="sm" min={0} step={0.01}
                            value={det.descuento_item || 0}
                            onChange={(v) => handleDetalleChange(i, 'descuento_item', parseFloat(v) || 0)}
                          >
                            <NumberInputField />
                          </NumberInput>
                        </Td>
                        <Td fontWeight="bold">
                          {simbolo} {calcularSubtotalDetalle(det).toFixed(2)}
                        </Td>
                        <Td>
                          <IconButton
                            icon={<FaTrash />}
                            size="sm" colorScheme="red" variant="ghost"
                            onClick={() => eliminarProducto(i)}
                            isDisabled={formData.detalles.length === 1}
                            aria-label="Eliminar"
                          />
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </Box>
            )}

            {/* ── Totales ── */}
            <Box mt={4} p={4} bg="gray.50" borderRadius="md">
              <Grid templateColumns="1fr auto" gap={2} maxW="420px" ml="auto" alignItems="center">
                <Text fontWeight="bold">Subtotal:</Text>
                <Text textAlign="right">{simbolo} {totales.subtotal}</Text>

                <HStack spacing={1}>
                  <Text fontWeight="bold" whiteSpace="nowrap">Descuento:</Text>
                  <Select
                    size="xs" w="60px" flexShrink={0}
                    value={descuento_tipo}
                    onChange={(e) => { setDescuentoTipo(e.target.value); setDescuentoValor(0); }}
                  >
                    <option value="porcentaje">%</option>
                    <option value="monto">{simbolo}</option>
                  </Select>
                </HStack>
                <NumberInput
                  size="sm" value={descuento_valor} min={0}
                  max={descuento_tipo === 'porcentaje' ? 100 : parseFloat(totales.subtotal)}
                  step={descuento_tipo === 'porcentaje' ? 1 : 0.01}
                  onChange={handleDescuentoValorChange}
                  maxW="150px" ml="auto"
                >
                  <NumberInputField />
                </NumberInput>

                {descuento_tipo === 'porcentaje' && parseFloat(totales.montoDescuento) > 0 && (
                  <>
                    <Box />
                    <Text fontSize="xs" color="gray.500" textAlign="right">- {simbolo} {totales.montoDescuento}</Text>
                  </>
                )}

                {parseFloat(totales.montoDescuento) > 0 && (
                  <>
                    <Text fontWeight="medium" color="gray.600">Subtotal neto:</Text>
                    <Text fontWeight="semibold" textAlign="right" color="gray.700">{simbolo} {totales.baseImponible}</Text>
                  </>
                )}

                {formData.igv_incluido && (
                  <>
                    <Text fontWeight="bold" fontSize="sm" color="gray.600">Base Imponible:</Text>
                    <Text textAlign="right" fontSize="sm" color="gray.600">{simbolo} {totales.baseImponible}</Text>
                  </>
                )}

                <Text fontWeight="bold">IGV ({formData.porcentaje_igv}%):</Text>
                <Text textAlign="right">{simbolo} {totales.igv}</Text>

                <Divider gridColumn="1 / -1" my={2} />

                <Text fontSize="xl" fontWeight="bold" color="blue.600">TOTAL:</Text>
                <Text fontSize="xl" fontWeight="bold" color="blue.600" textAlign="right">{simbolo} {totales.total}</Text>

                {formData.igv_incluido && (
                  <Text gridColumn="1 / -1" fontSize="xs" color="gray.500" textAlign="right" mt={1}>
                    * Precio incluye IGV
                  </Text>
                )}
              </Grid>
            </Box>
          </Box>

          {/* ── Condiciones Comerciales ── */}
          <Box bg="white" p={6} borderRadius="lg" shadow="sm">
            <Heading size="md" mb={4}>Condiciones Comerciales</Heading>
            <Grid templateColumns="repeat(2, 1fr)" gap={4}>
              <FormControl>
                <FormLabel>Forma de Pago</FormLabel>
                <Input name="forma_pago" value={formData.forma_pago} onChange={handleChange} placeholder="Ej: Contado, 50% adelantado" />
              </FormControl>
              <FormControl>
                <FormLabel>Tiempo de Entrega</FormLabel>
                <Input name="tiempo_entrega" value={formData.tiempo_entrega} onChange={handleChange} placeholder="Ej: 15 días hábiles" />
              </FormControl>
              <GridItem colSpan={2}>
                <FormControl>
                  <FormLabel>Lugar de Entrega</FormLabel>
                  <Textarea name="lugar_entrega" value={formData.lugar_entrega} onChange={handleChange} placeholder="Dirección de entrega" rows={2} />
                </FormControl>
              </GridItem>
            </Grid>
          </Box>

          {/* ── Notas y Términos ── */}
          <Box bg="white" p={6} borderRadius="lg" shadow="sm">
            <Heading size="md" mb={4}>Notas y Términos</Heading>
            <VStack spacing={4}>
              <FormControl>
                <FormLabel>Notas</FormLabel>
                <Textarea name="notas" value={formData.notas} onChange={handleChange} placeholder="Notas adicionales" rows={3} />
              </FormControl>
              <FormControl>
                <FormLabel>Términos y Condiciones</FormLabel>
                <Textarea name="terminos_condiciones" value={formData.terminos_condiciones} onChange={handleChange} placeholder="Términos y condiciones de la compra" rows={4} />
              </FormControl>
            </VStack>
          </Box>

          {/* ── Botones ── */}
          <Flex justify="flex-end" gap={4}>
            <Button variant="outline" onClick={() => navigate('/app/compras')}>Cancelar</Button>
            <Button type="submit" colorScheme="blue" leftIcon={<FaSave />} isLoading={isSubmitting}>
              Crear Compra
            </Button>
          </Flex>

        </VStack>
      </form>
    </Box>
  );
};

export default CompraForm;
