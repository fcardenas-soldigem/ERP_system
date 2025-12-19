import React, { useState, useEffect } from 'react';
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
  Divider
} from '@chakra-ui/react';
import { FaPlus, FaTrash, FaSave, FaArrowLeft } from 'react-icons/fa';
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
    asunto: '',
    descripcion: '',
    fecha_vencimiento: '',
    moneda: 'PEN',
    incluye_igv: true,
    porcentaje_igv: 18,
    descuento: 0,
    forma_pago: 'Contado',
    tiempo_entrega: '',
    lugar_entrega: '',
    validez_oferta: '30 días',
    notas: '',
    terminos_condiciones: '',
    detalles: []
  });

  useEffect(() => {
    cargarDatos();
    if (id) {
      cargarCotizacion();
    } else {
      // Fecha de vencimiento por defecto: 30 días
      const fecha = new Date();
      fecha.setDate(fecha.getDate() + 30);
      setFormData(prev => ({
        ...prev,
        fecha_vencimiento: fecha.toISOString().split('T')[0]
      }));
    }
  }, [id]);

  const cargarDatos = async () => {
    try {
      const [clientesData, productosData] = await Promise.all([
        clientesService.getClientes(),
        productosService.getProductos()
      ]);
      
      // Manejar respuestas paginadas
      const clientesArray = Array.isArray(clientesData?.results) 
        ? clientesData.results 
        : Array.isArray(clientesData) 
          ? clientesData 
          : [];
      
      const productosArray = Array.isArray(productosData?.results) 
        ? productosData.results 
        : Array.isArray(productosData) 
          ? productosData 
          : [];
      
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
        fecha_vencimiento: data.fecha_vencimiento
      });
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

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
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
          orden: prev.detalles.length
        }
      ]
    }));
  };

  const eliminarDetalle = (index) => {
    setFormData(prev => ({
      ...prev,
      detalles: prev.detalles.filter((_, i) => i !== index)
    }));
  };

  const handleDetalleChange = (index, field, value) => {
    setFormData(prev => {
      const nuevosDetalles = [...prev.detalles];
      nuevosDetalles[index] = {
        ...nuevosDetalles[index],
        [field]: value
      };

      // Si se selecciona un producto, autocompletar datos
      if (field === 'producto' && value) {
        const producto = productos.find(p => p.id === parseInt(value));
        if (producto) {
          nuevosDetalles[index] = {
            ...nuevosDetalles[index],
            codigo: producto.sku || '',  // Usar 'sku' en lugar de 'codigo'
            descripcion: producto.nombre,
            precio_unitario: producto.precio_venta || 0
          };
        }
      }

      return { ...prev, detalles: nuevosDetalles };
    });
  };

  const calcularSubtotalDetalle = (detalle) => {
    const subtotal = (detalle.cantidad * detalle.precio_unitario) - (detalle.descuento_item || 0);
    return subtotal > 0 ? subtotal : 0;
  };

  const calcularTotales = () => {
    const subtotal = formData.detalles.reduce((sum, detalle) => {
      return sum + calcularSubtotalDetalle(detalle);
    }, 0);

    const subtotalConDescuento = subtotal - (parseFloat(formData.descuento) || 0);
    
    let baseImponible, igv, total;
    
    if (formData.incluye_igv) {
      // Si el IGV está INCLUIDO en el precio
      // El subtotal ya tiene el IGV incluido, debemos extraerlo
      baseImponible = subtotalConDescuento / (1 + (formData.porcentaje_igv / 100));
      igv = subtotalConDescuento - baseImponible;
      total = subtotalConDescuento;
    } else {
      // Si el IGV NO está incluido
      // El IGV se suma al subtotal
      baseImponible = subtotalConDescuento;
      igv = subtotalConDescuento * (formData.porcentaje_igv / 100);
      total = subtotalConDescuento + igv;
    }

    return {
      subtotal: subtotal.toFixed(2),
      baseImponible: baseImponible.toFixed(2),
      igv: igv.toFixed(2),
      total: total.toFixed(2)
    };
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validaciones
    if (!formData.cliente) {
      toast({
        title: 'Error',
        description: 'Debe seleccionar un cliente',
        status: 'error',
        duration: 3000,
      });
      return;
    }

    if (formData.detalles.length === 0) {
      toast({
        title: 'Error',
        description: 'Debe agregar al menos un producto o servicio',
        status: 'error',
        duration: 3000,
      });
      return;
    }

    try {
      setLoading(true);
      if (id) {
        await cotizacionesService.update(id, formData);
        toast({
          title: 'Cotización actualizada',
          status: 'success',
          duration: 3000,
        });
      } else {
        await cotizacionesService.create(formData);
        toast({
          title: 'Cotización creada',
          status: 'success',
          duration: 3000,
        });
      }
      navigate('/app/cotizaciones');
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
  const simboloMoneda = formData.moneda === 'PEN' ? 'S/' : '$';

  return (
    <Box p={6}>
      <Flex justify="space-between" align="center" mb={6}>
        <Heading size="lg">{id ? 'Editar' : 'Nueva'} Cotización</Heading>
        <Button
          leftIcon={<FaArrowLeft />}
          variant="ghost"
          onClick={() => navigate('/app/cotizaciones')}
        >
          Volver
        </Button>
      </Flex>

      <form onSubmit={handleSubmit}>
        <VStack spacing={6} align="stretch">
          {/* Información del Cliente */}
          <Box bg="white" p={6} borderRadius="lg" shadow="sm">
            <Heading size="md" mb={4}>Información del Cliente</Heading>
            <Grid templateColumns="repeat(2, 1fr)" gap={4}>
              <GridItem colSpan={2}>
                <FormControl isRequired>
                  <FormLabel>Cliente</FormLabel>
                  <Select
                    name="cliente"
                    value={formData.cliente}
                    onChange={handleChange}
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

          {/* Configuración */}
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

              <FormControl display="flex" alignItems="center" flexDirection="column" alignItems="flex-start">
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

          {/* Productos/Servicios */}
          <Box bg="white" p={6} borderRadius="lg" shadow="sm">
            <Flex justify="space-between" align="center" mb={4}>
              <Heading size="md">Productos / Servicios</Heading>
              <Button
                leftIcon={<FaPlus />}
                colorScheme="blue"
                size="sm"
                onClick={agregarDetalle}
              >
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
                              <option key={prod.id} value={prod.id}>
                                {prod.nombre}
                              </option>
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

            {/* Totales */}
            <Box mt={4} p={4} bg="gray.50" borderRadius="md">
              <Grid templateColumns="1fr auto" gap={2} maxW="400px" ml="auto">
                <Text fontWeight="bold">Subtotal:</Text>
                <Text textAlign="right">{simboloMoneda} {totales.subtotal}</Text>

                <Text fontWeight="bold">Descuento:</Text>
                <NumberInput
                  size="sm"
                  value={formData.descuento}
                  onChange={(value) => setFormData(prev => ({ ...prev, descuento: parseFloat(value) || 0 }))}
                  min={0}
                  maxW="150px"
                >
                  <NumberInputField />
                </NumberInput>

                {formData.incluye_igv && (
                  <>
                    <Text fontWeight="bold" fontSize="sm" color="gray.600">
                      Base Imponible:
                    </Text>
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

          {/* Condiciones Comerciales */}
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

          {/* Notas y Términos */}
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

          {/* Botones */}
          <Flex justify="flex-end" gap={4}>
            <Button
              variant="outline"
              onClick={() => navigate('/app/cotizaciones')}
            >
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

