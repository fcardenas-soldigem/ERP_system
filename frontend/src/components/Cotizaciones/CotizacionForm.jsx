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
} from '@chakra-ui/react';
import { FaPlus, FaTrash, FaSave, FaArrowLeft, FaSearch } from 'react-icons/fa';
import { useNavigate, useParams } from 'react-router-dom';
import cotizacionesService from '../../services/cotizacionesService';
import { clientesService } from '../../services/clientes.service';
import { productosService } from '../../services/productos.service';

const CotizacionForm = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [clientes, setClientes] = useState([]);
  const [productos, setProductos] = useState([]);

  const [formData, setFormData] = useState({
    cliente: '',
    contacto_nombre: '',
    contacto_email: '',
    asunto: '',
    descripcion: '',
    fecha_vencimiento: '',
    moneda: 'PEN',
    incluye_igv: false,
    porcentaje_igv: 18,
    descuento: 0,
    forma_pago: 'Contado',
    tiempo_entrega: '',
    lugar_entrega: '',
    validez_oferta: '30 días',
    notas: '',
    terminos_condiciones: '',
    detalles: [],
  });

  // ── Búsqueda de clientes ──
  const [busquedaCliente, setBusquedaCliente] = useState('');
  const [resultadosClientes, setResultadosClientes] = useState([]);
  const [mostrarResultados, setMostrarResultados] = useState(false);
  const dropdownRef = useRef(null);

  // ── Descuento ──
  const [descuento_tipo, setDescuentoTipo] = useState('porcentaje');
  const [descuento_valor, setDescuentoValor] = useState(0);

  useEffect(() => {
    cargarDatos();
    if (id) {
      cargarCotizacion();
    } else {
      const fecha = new Date();
      fecha.setDate(fecha.getDate() + 30);
      setFormData(prev => ({
        ...prev,
        fecha_vencimiento: fecha.toISOString().split('T')[0],
      }));
    }
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

  const cargarDatos = async () => {
    try {
      const [clientesData, productosData] = await Promise.all([
        clientesService.getClientes(),
        productosService.getProductosParaVenta(),
      ]);
      const clientesArray = Array.isArray(clientesData?.results)
        ? clientesData.results
        : Array.isArray(clientesData) ? clientesData : [];
      const productosArray = Array.isArray(productosData?.results)
        ? productosData.results
        : Array.isArray(productosData) ? productosData : [];
      setClientes(clientesArray);
      setProductos(productosArray);
    } catch (error) {
      console.error('Error al cargar datos:', error);
      setClientes([]);
      setProductos([]);
      toast({
        title: 'Error al cargar datos',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const cargarCotizacion = async () => {
    try {
      setLoading(true);
      const data = await cotizacionesService.getById(id);
      setFormData({
        ...data,
        cliente: data.cliente,
        fecha_vencimiento: data.fecha_vencimiento,
        incluye_igv: !!data.precios_incluyen_igv,
      });
      // Cargar descuento
      if (data.descuento_tipo) {
        setDescuentoTipo(data.descuento_tipo);
        setDescuentoValor(parseFloat(data.descuento_valor) || 0);
      } else if (data.descuento && parseFloat(data.descuento) > 0) {
        setDescuentoTipo('monto');
        setDescuentoValor(parseFloat(data.descuento) || 0);
      }
    } catch (error) {
      toast({
        title: 'Error al cargar cotización',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
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
    setFormData(prev => ({
      ...prev,
      cliente: c.id,
      contacto_nombre: prev.contacto_nombre || c.telefono || '',
      contacto_email: prev.contacto_email || c.email || '',
    }));
    setBusquedaCliente('');
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
      detalles: [
        ...prev.detalles,
        {
          producto: '',
          codigo: '',
          descripcion: '',
          cantidad: 1,
          precio_unitario: 0,
          descuento_item: 0,
          orden: prev.detalles.length,
        },
      ],
    }));
  };

  const eliminarDetalle = (index) => {
    setFormData(prev => ({
      ...prev,
      detalles: prev.detalles.filter((_, i) => i !== index),
    }));
  };

  const handleDetalleChange = (index, field, value) => {
    setFormData(prev => {
      const nuevosDetalles = [...prev.detalles];
      nuevosDetalles[index] = { ...nuevosDetalles[index], [field]: value };
      if (field === 'producto' && value) {
        const producto = productos.find(p => p.id === parseInt(value));
        if (producto) {
          nuevosDetalles[index] = {
            ...nuevosDetalles[index],
            codigo: producto.sku || '',
            descripcion: producto.nombre,
            precio_unitario: producto.precio_venta || 0,
          };
        }
      }
      return { ...prev, detalles: nuevosDetalles };
    });
  };

  const calcularSubtotalDetalle = (detalle) => {
    const sub = (detalle.cantidad * detalle.precio_unitario) - (detalle.descuento_item || 0);
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
    if (!formData.cliente) {
      toast({ title: 'Error', description: 'Debe seleccionar un cliente', status: 'error', duration: 3000 });
      return;
    }
    if (formData.detalles.length === 0) {
      toast({ title: 'Error', description: 'Debe agregar al menos un producto o servicio', status: 'error', duration: 3000 });
      return;
    }
    const totales = calcularTotales();
    const submitData = {
      ...formData,
      incluye_igv: true,
      precios_incluyen_igv: !!formData.incluye_igv,
      descuento: parseFloat(totales.montoDescuento) || 0,
      descuento_tipo,
      descuento_valor: parseFloat(descuento_valor) || 0,
      descuento_monto: parseFloat(totales.montoDescuento) || 0,
      detalles: formData.detalles.map(d => ({
        ...d,
        producto: d.producto || null,
        codigo: d.codigo || null,
        descripcion: (d.descripcion || '').replace(/ /g, '').trim(),
      })),
    };
    try {
      setLoading(true);
      if (id) {
        await cotizacionesService.update(id, submitData);
        toast({ title: 'Cotización actualizada', status: 'success', duration: 3000 });
      } else {
        await cotizacionesService.create(submitData);
        toast({ title: 'Cotización creada', status: 'success', duration: 3000 });
      }
      navigate('/app/cotizaciones');
    } catch (error) {
      const errData = error.response?.data;
      const description = errData?.detail
        || (typeof errData === 'object' ? JSON.stringify(errData) : null)
        || error.message;
      toast({
        title: 'Error al guardar',
        description,
        status: 'error',
        duration: 7000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  const totales = calcularTotales();
  const simboloMoneda = formData.moneda === 'PEN' ? 'S/' : '$';

  return (
    <Box p={6}>
      <Flex justify="space-between" align="center" mb={6}>
        <Heading size="lg">{id ? 'Editar' : 'Nueva'} Cotización</Heading>
        <Button leftIcon={<FaArrowLeft />} variant="ghost" onClick={() => navigate('/app/cotizaciones')}>
          Volver
        </Button>
      </Flex>

      <form onSubmit={handleSubmit}>
        <VStack spacing={6} align="stretch">
          {/* ── Información del Cliente ── */}
          <Box bg="white" p={6} borderRadius="lg" shadow="sm">
            <Heading size="md" mb={4}>Información del Cliente</Heading>
            <Grid templateColumns="repeat(2, 1fr)" gap={4}>

              {/* Búsqueda por nombre */}
              <GridItem colSpan={2}>
                <FormControl>
                  <FormLabel>Buscar Cliente Existente</FormLabel>
                  <Box position="relative" ref={dropdownRef}>
                    <InputGroup>
                      <Input
                        value={busquedaCliente}
                        onChange={(e) => handleBuscarCliente(e.target.value)}
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
                </FormControl>
              </GridItem>

              <GridItem colSpan={2}>
                <FormControl isRequired>
                  <FormLabel>Cliente</FormLabel>
                  <Select
                    name="cliente"
                    value={formData.cliente}
                    onChange={(e) => {
                      const cli = clientes.find(c => c.id === parseInt(e.target.value));
                      setFormData(prev => ({
                        ...prev,
                        cliente: e.target.value,
                        contacto_nombre: prev.contacto_nombre || (cli ? cli.telefono || '' : ''),
                        contacto_email: prev.contacto_email || (cli ? cli.email || '' : ''),
                      }));
                    }}
                    placeholder="Seleccione un cliente"
                  >
                    {clientes.map(cliente => (
                      <option key={cliente.id} value={cliente.id}>
                        {cliente.nombre} - {cliente.documento}
                      </option>
                    ))}
                  </Select>
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
                  placeholder="email@cliente.com"
                />
              </FormControl>

              <GridItem colSpan={2}>
                <FormControl isRequired>
                  <FormLabel>Asunto</FormLabel>
                  <Input
                    name="asunto"
                    value={formData.asunto}
                    onChange={handleChange}
                    placeholder="Ej: Propuesta de servicios de consultoría"
                  />
                </FormControl>
              </GridItem>

              <GridItem colSpan={2}>
                <FormControl>
                  <FormLabel>Descripción</FormLabel>
                  <Textarea
                    name="descripcion"
                    value={formData.descripcion}
                    onChange={handleChange}
                    placeholder="Descripción adicional de la cotización"
                    rows={3}
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
                <FormLabel>Fecha de Vencimiento</FormLabel>
                <Input
                  type="date"
                  name="fecha_vencimiento"
                  value={formData.fecha_vencimiento}
                  onChange={handleChange}
                />
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Moneda</FormLabel>
                <Select name="moneda" value={formData.moneda} onChange={handleChange}>
                  <option value="PEN">Soles (S/)</option>
                  <option value="USD">Dólares ($)</option>
                </Select>
              </FormControl>

              <FormControl>
                <FormLabel>Validez de la Oferta</FormLabel>
                <Input
                  name="validez_oferta"
                  value={formData.validez_oferta}
                  onChange={handleChange}
                  placeholder="Ej: 30 días"
                />
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

          {/* ── Productos/Servicios ── */}
          <Box bg="white" p={6} borderRadius="lg" shadow="sm">
            <Flex justify="space-between" align="center" mb={4}>
              <Heading size="md">Productos / Servicios</Heading>
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
                      <Th>Código</Th>
                      <Th>Descripción</Th>
                      <Th>Cant.</Th>
                      <Th>P. Unit.</Th>
                      <Th>Desc.</Th>
                      <Th>Subtotal</Th>
                      <Th></Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {formData.detalles.map((detalle, index) => (
                      <Tr key={index}>
                        <Td>
                          <Select
                            size="sm"
                            value={detalle.producto}
                            onChange={(e) => handleDetalleChange(index, 'producto', e.target.value)}
                            placeholder="Seleccionar"
                          >
                            {productos.map(prod => (
                              <option key={prod.id} value={prod.id}>{prod.nombre}</option>
                            ))}
                          </Select>
                        </Td>
                        <Td>
                          <Input
                            size="sm"
                            value={detalle.codigo}
                            onChange={(e) => handleDetalleChange(index, 'codigo', e.target.value)}
                            placeholder="Código"
                          />
                        </Td>
                        <Td>
                          <Input
                            size="sm"
                            value={detalle.descripcion}
                            onChange={(e) => handleDetalleChange(index, 'descripcion', e.target.value)}
                            placeholder="Descripción"
                            isRequired
                          />
                        </Td>
                        <Td>
                          <NumberInput
                            size="sm"
                            value={detalle.cantidad}
                            onChange={(value) => handleDetalleChange(index, 'cantidad', parseFloat(value) || 1)}
                            min={0.01}
                            step={0.01}
                          >
                            <NumberInputField />
                          </NumberInput>
                        </Td>
                        <Td>
                          <NumberInput
                            size="sm"
                            value={detalle.precio_unitario}
                            onChange={(value) => handleDetalleChange(index, 'precio_unitario', parseFloat(value) || 0)}
                            min={0}
                            step={0.01}
                          >
                            <NumberInputField />
                          </NumberInput>
                        </Td>
                        <Td>
                          <NumberInput
                            size="sm"
                            value={detalle.descuento_item}
                            onChange={(value) => handleDetalleChange(index, 'descuento_item', parseFloat(value) || 0)}
                            min={0}
                            step={0.01}
                          >
                            <NumberInputField />
                          </NumberInput>
                        </Td>
                        <Td fontWeight="bold">
                          {simboloMoneda} {calcularSubtotalDetalle(detalle).toFixed(2)}
                        </Td>
                        <Td>
                          <IconButton
                            icon={<FaTrash />}
                            size="sm"
                            colorScheme="red"
                            variant="ghost"
                            onClick={() => eliminarDetalle(index)}
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
                <Text textAlign="right">{simboloMoneda} {totales.subtotal}</Text>

                {/* Descuento con selector tipo */}
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
                    <option value="monto">{simboloMoneda}</option>
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

                {/* Monto descontado en gris si es porcentaje */}
                {descuento_tipo === 'porcentaje' && parseFloat(totales.montoDescuento) > 0 && (
                  <>
                    <Box />
                    <Text fontSize="xs" color="gray.500" textAlign="right">
                      - {simboloMoneda} {totales.montoDescuento}
                    </Text>
                  </>
                )}

                {parseFloat(totales.montoDescuento) > 0 && (
                  <>
                    <Text fontWeight="medium" color="gray.600">Subtotal neto:</Text>
                    <Text fontWeight="semibold" textAlign="right" color="gray.700">
                      {simboloMoneda} {totales.baseImponible}
                    </Text>
                  </>
                )}

                {formData.incluye_igv && (
                  <>
                    <Text fontWeight="bold" fontSize="sm" color="gray.600">Base Imponible:</Text>
                    <Text textAlign="right" fontSize="sm" color="gray.600">
                      {simboloMoneda} {totales.baseImponible}
                    </Text>
                  </>
                )}

                <Text fontWeight="bold">IGV ({formData.porcentaje_igv}%):</Text>
                <Text textAlign="right">{simboloMoneda} {totales.igv}</Text>

                <Divider gridColumn="1 / -1" my={2} />

                <Text fontSize="xl" fontWeight="bold" color="green.600">TOTAL:</Text>
                <Text fontSize="xl" fontWeight="bold" color="green.600" textAlign="right">
                  {simboloMoneda} {totales.total}
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
                  placeholder="Notas adicionales para el cliente"
                  rows={3}
                />
              </FormControl>

              <FormControl>
                <FormLabel>Términos y Condiciones</FormLabel>
                <Textarea
                  name="terminos_condiciones"
                  value={formData.terminos_condiciones}
                  onChange={handleChange}
                  placeholder="Términos y condiciones de la cotización"
                  rows={4}
                />
              </FormControl>
            </VStack>
          </Box>

          {/* ── Botones ── */}
          <Flex justify="flex-end" gap={4}>
            <Button variant="outline" onClick={() => navigate('/app/cotizaciones')}>
              Cancelar
            </Button>
            <Button
              type="submit"
              colorScheme="blue"
              leftIcon={<FaSave />}
              isLoading={loading}
            >
              {id ? 'Actualizar' : 'Crear'} Cotización
            </Button>
          </Flex>
        </VStack>
      </form>
    </Box>
  );
};

export default CotizacionForm;
