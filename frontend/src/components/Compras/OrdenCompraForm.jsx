import React, { useState, useEffect, useRef, useCallback } from 'react';
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
  Spinner,
} from '@chakra-ui/react';
import { FaPlus, FaTrash, FaSave, FaArrowLeft, FaSearch } from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { comprasService } from '../../services/compras.service';
import { proveedoresService } from '../../services/proveedores.service';
import { api } from '../../lib/api';

const OrdenCompraForm = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const [loading, setLoading] = useState(false);

  const [formData, setFormData] = useState({
    proveedor_nombre: '',
    proveedor_id: '',
    contacto_nombre: '',
    contacto_email: '',
    fecha_entrega: (() => {
      const d = new Date();
      d.setDate(d.getDate() + 7);
      return d.toISOString().split('T')[0];
    })(),
    estado: 'borrador',
    moneda: 'USD',
    incluye_igv: false,
    porcentaje_igv: 18,
    referencia: '',
    forma_pago: 'Contado',
    tiempo_entrega: '',
    lugar_entrega: '',
    notas: '',
    terminos_condiciones: '',
    detalles: [{ producto_id: '', descripcion: '', cantidad: 1, precio_unitario: 0, descuento_item: 0 }],
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

  // Productos
  const { data: productosData = [] } = useQuery({
    queryKey: ['productos-oc'],
    queryFn: comprasService.getProductos,
  });
  const productos = Array.isArray(productosData) ? productosData : productosData?.results ?? [];

  // Almacenes
  const { data: almacenesData = [] } = useQuery({
    queryKey: ['almacenes'],
    queryFn: () => comprasService.getAlmacenes(),
  });
  const almacenes = Array.isArray(almacenesData) ? almacenesData : [];

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
    setFormData(prev => ({
      ...prev,
      proveedor_id: p.id,
      proveedor_nombre: p.nombre || p.razon_social || '',
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

  const agregarDetalle = () => {
    setFormData(prev => ({
      ...prev,
      detalles: [...prev.detalles, { producto_id: '', descripcion: '', cantidad: 1, precio_unitario: 0, descuento_item: 0 }],
    }));
  };

  const eliminarDetalle = (index) => {
    if (formData.detalles.length === 1) return;
    setFormData(prev => ({
      ...prev,
      detalles: prev.detalles.filter((_, i) => i !== index),
    }));
  };

  const handleDetalleChange = (index, field, value) => {
    setFormData(prev => {
      const nuevos = [...prev.detalles];
      nuevos[index] = { ...nuevos[index], [field]: value };
      if (field === 'producto_id' && value) {
        const prod = productos.find(p => p.id === parseInt(value));
        if (prod) {
          nuevos[index].descripcion = prod.nombre;
          nuevos[index].precio_unitario = parseFloat(prod.precio_compra) || 0;
        }
      }
      return { ...prev, detalles: nuevos };
    });
  };

  const calcularSubtotalDetalle = (d) => {
    const sub = (parseFloat(d.cantidad) || 0) * (parseFloat(d.precio_unitario) || 0) - (parseFloat(d.descuento_item) || 0);
    return sub > 0 ? sub : 0;
  };

  const calcularTotales = () => {
    const subtotal = formData.detalles.reduce((sum, d) => sum + calcularSubtotalDetalle(d), 0);

    const montoDesc = descuento_tipo === 'porcentaje'
      ? subtotal * ((parseFloat(descuento_valor) || 0) / 100)
      : Math.min(parseFloat(descuento_valor) || 0, subtotal);

    const subtotalConDescuento = Math.max(0, subtotal - montoDesc);

    let baseImponible, igv, total;
    if (formData.incluye_igv) {
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
    const totalesActuales = calcularTotales();
    if (descuento_tipo === 'porcentaje' && val > 100) {
      toast({ title: 'El descuento no puede superar el 100%', status: 'warning', duration: 2000 });
      return;
    }
    if (descuento_tipo === 'monto' && val > parseFloat(totalesActuales.subtotal)) {
      toast({ title: 'El descuento no puede ser mayor al subtotal', status: 'warning', duration: 2000 });
      return;
    }
    setDescuentoValor(val);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.proveedor_nombre.trim()) {
      toast({ title: 'Error', description: 'Debe ingresar o seleccionar un proveedor', status: 'error', duration: 3000 });
      return;
    }
    if (!formData.fecha_entrega) {
      toast({ title: 'Error', description: 'Debe indicar la fecha de entrega', status: 'error', duration: 3000 });
      return;
    }
    const invalido = formData.detalles.some(
      d => !d.descripcion.trim() || !(parseFloat(d.cantidad) > 0) || !(parseFloat(d.precio_unitario) > 0),
    );
    if (invalido) {
      toast({ title: 'Error', description: 'Todos los ítems deben tener descripción, cantidad y precio mayor a 0', status: 'error', duration: 3000 });
      return;
    }
    const totales = calcularTotales();
    try {
      setLoading(true);
      await api.post('/api/compras/ordenes/', {
        proveedor: formData.proveedor_id ? parseInt(formData.proveedor_id) : null,
        proveedor_nombre: formData.proveedor_nombre,
        contacto_nombre: formData.contacto_nombre || null,
        contacto_email: formData.contacto_email || null,
        fecha_entrega: formData.fecha_entrega,
        estado: formData.estado,
        moneda: formData.moneda,
        forma_pago: formData.forma_pago,
        notas: formData.notas,
        subtotal: totales.subtotal,
        igv: totales.igv,
        total: totales.total,
        detalles: formData.detalles.map(d => ({
          producto: d.producto_id ? parseInt(d.producto_id) : null,
          descripcion: d.descripcion,
          cantidad: parseFloat(d.cantidad) || 1,
          precio_unitario: parseFloat(d.precio_unitario) || 0,
        })),
      });
      toast({ title: 'Orden de Compra creada', status: 'success', duration: 3000 });
      navigate('/app/compras');
    } catch (error) {
      toast({
        title: 'Error al guardar',
        description: error.response?.data?.detail || error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  const totales = calcularTotales();
  const simbolo = formData.moneda === 'USD' ? '$' : 'S/';
  const proveedorSeleccionado = proveedores.find(p => p.id === formData.proveedor_id);

  return (
    <Box p={6}>
      <Flex justify="space-between" align="center" mb={6}>
        <Heading size="lg">Nueva Orden de Compra</Heading>
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
                        {resultadosProveedores.length === 0 ? (
                          <Text py={2} px={3} fontSize="sm" color="gray.500">No se encontraron proveedores</Text>
                        ) : (
                          resultadosProveedores.map((p) => (
                            <Box
                              key={p.id}
                              py={2}
                              px={3}
                              cursor="pointer"
                              _hover={{ bg: 'blue.50' }}
                              onClick={() => seleccionarProveedor(p)}
                              borderBottom="1px solid"
                              borderColor="gray.100"
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
                      value={formData.proveedor_id}
                      onChange={(e) => {
                        const prov = proveedores.find(p => p.id === parseInt(e.target.value));
                        setFormData(prev => ({
                          ...prev,
                          proveedor_id: e.target.value,
                          proveedor_nombre: prov ? (prov.nombre || prov.razon_social) : prev.proveedor_nombre,
                          contacto_nombre: prev.contacto_nombre || (prov ? prov.telefono || '' : ''),
                          contacto_email: prev.contacto_email || (prov ? prov.email || '' : ''),
                        }));
                      }}
                      placeholder="Seleccione un proveedor"
                    >
                      {proveedores.map(p => (
                        <option key={p.id} value={p.id}>
                          {p.nombre || p.razon_social} {p.ruc ? `- ${p.ruc}` : ''}
                        </option>
                      ))}
                    </Select>
                  ) : (
                    <Input
                      name="proveedor_nombre"
                      value={formData.proveedor_nombre}
                      onChange={handleChange}
                      placeholder="Nombre o razón social del proveedor"
                    />
                  )}
                </FormControl>
              </GridItem>

              <FormControl>
                <FormLabel>Contacto</FormLabel>
                <Input
                  name="contacto_nombre"
                  value={formData.contacto_nombre}
                  onChange={handleChange}
                  placeholder="Nombre del contacto"
                />
              </FormControl>

              <FormControl>
                <FormLabel>Email contacto</FormLabel>
                <Input
                  type="email"
                  name="contacto_email"
                  value={formData.contacto_email}
                  onChange={handleChange}
                  placeholder="email@proveedor.com"
                />
              </FormControl>

              <GridItem colSpan={2}>
                <FormControl>
                  <FormLabel>Referencia</FormLabel>
                  <Input
                    name="referencia"
                    value={formData.referencia}
                    onChange={handleChange}
                    placeholder="Ej: Número de cotización del proveedor, referencia interna"
                  />
                </FormControl>
              </GridItem>
            </Grid>
          </Box>

          {/* ── Configuración ── */}
          <Box bg="white" p={6} borderRadius="lg" shadow="sm">
            <Heading size="md" mb={4}>Configuración</Heading>
            <Grid templateColumns="repeat(3, 1fr)" gap={4}>
              <FormControl isRequired>
                <FormLabel>Fecha de Entrega</FormLabel>
                <Input
                  type="date"
                  name="fecha_entrega"
                  value={formData.fecha_entrega}
                  onChange={handleChange}
                />
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
                  <FormLabel mb="0">IGV Incluido en Precio</FormLabel>
                  <Switch
                    name="incluye_igv"
                    isChecked={formData.incluye_igv}
                    onChange={handleChange}
                    colorScheme="green"
                  />
                </HStack>
                <Text fontSize="xs" color="gray.600">
                  {formData.incluye_igv
                    ? '✓ El precio ya incluye el 18% de IGV'
                    : '✗ El IGV se sumará al precio (18% adicional)'}
                </Text>
              </FormControl>

              <FormControl>
                <FormLabel>Porcentaje IGV (%)</FormLabel>
                <NumberInput
                  value={formData.porcentaje_igv}
                  onChange={(value) => setFormData(prev => ({ ...prev, porcentaje_igv: parseFloat(value) || 18 }))}
                  min={0}
                  max={100}
                >
                  <NumberInputField />
                </NumberInput>
              </FormControl>
            </Grid>
          </Box>

          {/* ── Ítems solicitados ── */}
          <Box bg="white" p={6} borderRadius="lg" shadow="sm">
            <Flex justify="space-between" align="center" mb={4}>
              <Heading size="md">Ítems Solicitados</Heading>
              <Button leftIcon={<FaPlus />} colorScheme="blue" size="sm" onClick={agregarDetalle}>
                Agregar Ítem
              </Button>
            </Flex>

            {formData.detalles.length === 0 ? (
              <Text color="gray.500" textAlign="center" py={4}>
                No hay ítems agregados. Haga clic en "Agregar Ítem" para comenzar.
              </Text>
            ) : (
              <Box overflowX="auto">
                <Table size="sm">
                  <Thead>
                    <Tr>
                      <Th>Producto</Th>
                      <Th>Descripción</Th>
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
                        <Td minW="160px">
                          <Select
                            size="sm"
                            value={det.producto_id || ''}
                            onChange={e => handleDetalleChange(i, 'producto_id', e.target.value)}
                            placeholder="— seleccionar —"
                          >
                            {productos.map(p => (
                              <option key={p.id} value={p.id}>{p.nombre}</option>
                            ))}
                          </Select>
                        </Td>
                        <Td minW="200px">
                          <Input
                            size="sm"
                            value={det.descripcion}
                            onChange={e => handleDetalleChange(i, 'descripcion', e.target.value)}
                            placeholder="Descripción del ítem"
                          />
                        </Td>
                        <Td minW="90px">
                          <NumberInput
                            size="sm"
                            min={0.01}
                            precision={2}
                            value={det.cantidad}
                            onChange={v => handleDetalleChange(i, 'cantidad', v)}
                          >
                            <NumberInputField />
                          </NumberInput>
                        </Td>
                        <Td minW="120px">
                          <NumberInput
                            size="sm"
                            min={0}
                            precision={2}
                            value={det.precio_unitario}
                            onChange={v => handleDetalleChange(i, 'precio_unitario', v)}
                          >
                            <NumberInputField />
                          </NumberInput>
                        </Td>
                        <Td minW="90px">
                          <NumberInput
                            size="sm"
                            value={det.descuento_item || 0}
                            onChange={v => handleDetalleChange(i, 'descuento_item', parseFloat(v) || 0)}
                            min={0}
                            step={0.01}
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
                            size="sm"
                            colorScheme="red"
                            variant="ghost"
                            onClick={() => eliminarDetalle(i)}
                            isDisabled={formData.detalles.length === 1}
                            aria-label="Eliminar ítem"
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
                    size="xs"
                    w="60px"
                    flexShrink={0}
                    value={descuento_tipo}
                    onChange={(e) => {
                      setDescuentoTipo(e.target.value);
                      setDescuentoValor(0);
                    }}
                  >
                    <option value="porcentaje">%</option>
                    <option value="monto">{simbolo}</option>
                  </Select>
                </HStack>
                <NumberInput
                  size="sm"
                  value={descuento_valor}
                  min={0}
                  max={descuento_tipo === 'porcentaje' ? 100 : parseFloat(totales.subtotal)}
                  step={descuento_tipo === 'porcentaje' ? 1 : 0.01}
                  onChange={handleDescuentoValorChange}
                  maxW="150px"
                  ml="auto"
                >
                  <NumberInputField />
                </NumberInput>

                {descuento_tipo === 'porcentaje' && parseFloat(totales.montoDescuento) > 0 && (
                  <>
                    <Box />
                    <Text fontSize="xs" color="gray.500" textAlign="right">
                      - {simbolo} {totales.montoDescuento}
                    </Text>
                  </>
                )}

                {parseFloat(totales.montoDescuento) > 0 && (
                  <>
                    <Text fontWeight="medium" color="gray.600">Subtotal neto:</Text>
                    <Text fontWeight="semibold" textAlign="right" color="gray.700">
                      {simbolo} {totales.baseImponible}
                    </Text>
                  </>
                )}

                {formData.incluye_igv && (
                  <>
                    <Text fontWeight="bold" fontSize="sm" color="gray.600">Base Imponible:</Text>
                    <Text textAlign="right" fontSize="sm" color="gray.600">
                      {simbolo} {totales.baseImponible}
                    </Text>
                  </>
                )}

                <Text fontWeight="bold">IGV ({formData.porcentaje_igv}%):</Text>
                <Text textAlign="right">{simbolo} {totales.igv}</Text>

                <Divider gridColumn="1 / -1" my={2} />

                <Text fontSize="xl" fontWeight="bold" color="blue.600">TOTAL:</Text>
                <Text fontSize="xl" fontWeight="bold" color="blue.600" textAlign="right">
                  {simbolo} {totales.total}
                </Text>

                {formData.incluye_igv && (
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
                <Input
                  name="forma_pago"
                  value={formData.forma_pago}
                  onChange={handleChange}
                  placeholder="Ej: Contado, 50% adelantado"
                />
              </FormControl>

              <FormControl>
                <FormLabel>Tiempo de Entrega</FormLabel>
                <Input
                  name="tiempo_entrega"
                  value={formData.tiempo_entrega}
                  onChange={handleChange}
                  placeholder="Ej: 15 días hábiles"
                />
              </FormControl>

              <GridItem colSpan={2}>
                <FormControl>
                  <FormLabel>Lugar de Entrega</FormLabel>
                  <Textarea
                    name="lugar_entrega"
                    value={formData.lugar_entrega}
                    onChange={handleChange}
                    placeholder="Dirección de entrega"
                    rows={2}
                  />
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
                <Textarea
                  name="notas"
                  value={formData.notas}
                  onChange={handleChange}
                  placeholder="Notas adicionales para el proveedor"
                  rows={3}
                />
              </FormControl>

              <FormControl>
                <FormLabel>Términos y Condiciones</FormLabel>
                <Textarea
                  name="terminos_condiciones"
                  value={formData.terminos_condiciones}
                  onChange={handleChange}
                  placeholder="Términos y condiciones de la orden de compra"
                  rows={4}
                />
              </FormControl>
            </VStack>
          </Box>

          {/* ── Botones ── */}
          <Flex justify="flex-end" gap={4}>
            <Button variant="outline" onClick={() => navigate('/app/compras')}>
              Cancelar
            </Button>
            <Button
              type="submit"
              colorScheme="blue"
              leftIcon={<FaSave />}
              isLoading={loading}
              loadingText="Guardando..."
            >
              Crear Orden de Compra
            </Button>
          </Flex>

        </VStack>
      </form>
    </Box>
  );
};

export default OrdenCompraForm;
