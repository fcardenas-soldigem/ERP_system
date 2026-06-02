import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Input,
  Select,
  VStack,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  NumberInput,
  NumberInputField,
  Switch,
  Text,
  IconButton,
  FormHelperText,
  useToast,
  Container,
  Heading,
  HStack,
  Spinner,
  Alert,
  AlertIcon,
  List,
  ListItem
} from '@chakra-ui/react';
import { DeleteIcon, SearchIcon } from '@chakra-ui/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ventasService } from '../../services/ventas.service';
import { clientesService } from '../../services/clientes.service';
import { TIPOS_VENTA, METODOS_PAGO, TIPOS_VENTA_DISPLAY, METODOS_PAGO_DISPLAY } from './constants';
import { addDays } from 'date-fns';
import { useClienteSelector } from '../../hooks/useClienteSelector';
import { getSimboloMoneda } from '../../utils/currency';

const NuevaVenta = () => {
  // Core form state — reduced from 11 useState to 2
  const [formData, setFormData] = useState({
    cliente: '',
    fecha_emision: new Date().toISOString().split('T')[0],
    fecha_vencimiento: null,
    estado: 'borrador',
    tipo_venta: 'contado',
    metodo_pago: 'efectivo',
    modo_venta: 'stock',
    igv_incluido: false,
    moneda: 'PEN',
    referencia: '',
    comprobante: null,
    detalles: [{ producto: '', cantidad: 1, precio_unitario: 0 }],
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Limpiar caché al montar el componente
  useEffect(() => {
    queryClient.invalidateQueries(['clientes']);
    queryClient.invalidateQueries(['productos']);
  }, [queryClient]);

  // Efecto para recalcular totales cuando cambie la moneda o IGV incluido
  useEffect(() => {
    // Forzar re-render de los cálculos cuando cambie la moneda o IGV incluido
    if (formData.detalles.length > 0) {
      // No necesitamos hacer nada específico, el re-render automático es suficiente
      // Este useEffect asegura que React detecte los cambios
    }
  }, [formData.moneda, formData.igv_incluido]);

  const { data: clientes = [] } = useQuery({
    queryKey: ['clientes'],
    queryFn: () => ventasService.getClientes(),
    staleTime: 0,
    gcTime: 0
  });

  const { data: productosData = [] } = useQuery({
    queryKey: ['productos'],
    queryFn: () => ventasService.getProductos(),
    staleTime: 0,
    gcTime: 0
  });

  // Ensure arrays
  const productos = Array.isArray(productosData) ? productosData : [];
  const clientesArray = Array.isArray(clientes) ? clientes : [];

  // ── useClienteSelector: replaces 8 useState calls ────────────────────────
  const {
    clienteSearch, showClienteDropdown, filteredClientes, selectedIndex: selectedClienteIndex,
    handleSearchChange: handleClienteSearchChange,
    handleSearchKeyDown,
    selectCliente: handleClienteSelect,
    closeDropdown,
    documentoSearch, setDocumentoSearch,
    tipoDocumento, setTipoDocumento,
    consultando: consultandoDocumento,
    modoDocumento: modoConsultaDocumento,
    toggleModo: toggleModoConsultaDocumento,
    buscarOCrearPorDocumento: handleBuscarOCrearCliente,
  } = useClienteSelector(
    clientesArray,
    toast,
    queryClient,
    (clienteId) => setFormData(prev => ({ ...prev, cliente: clienteId }))
  );

  const crearVentaMutation = useMutation({
    mutationFn: ventasService.crearVenta,
    onSuccess: () => {
      queryClient.invalidateQueries(['ventas']);
      queryClient.invalidateQueries(['productos']);
      queryClient.invalidateQueries(['clientes']);
      toast({
        title: 'Venta creada',
        description: 'La venta se ha creado exitosamente',
        status: 'success',
        duration: 2000
      });
      navigate('/app/ventas');
    },
    onError: (error) => {
      toast({
        title: 'Error',
        description: error.message,
        status: 'error',
        duration: 3000
      });
    }
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleDetalleChange = (index, field, value) => {
    const newDetalles = [...formData.detalles];
    
    // Asegurarse de que el valor sea un número cuando corresponda
    if (field === 'cantidad' || field === 'precio_unitario') {
      value = value === '' ? '' : Number(value);
    } else if (field === 'producto') {
      value = value === '' ? '' : String(value);
      // Actualizar el precio cuando se selecciona un producto
      const producto = productos.find(p => p.id === parseInt(value));
      if (producto) {
        newDetalles[index] = {
          ...newDetalles[index],
          producto: value,
          precio_unitario: Number(producto.precio_venta) || 0
        };
      }
    }

    if (field !== 'producto') {
      newDetalles[index] = {
        ...newDetalles[index],
        [field]: value
      };
    }

    setFormData(prev => ({
      ...prev,
      detalles: newDetalles
    }));
  };

  const handleFileChange = (e) => {
    setFormData(prev => ({
      ...prev,
      comprobante: e.target.files[0]
    }));
  };

  const agregarProducto = () => {
    setFormData(prev => ({
      ...prev,
      detalles: [
        ...prev.detalles,
        { producto: '', cantidad: 1, precio_unitario: 0 }
      ]
    }));
  };

  const eliminarProducto = (index) => {
    if (formData.detalles.length > 1) {
      setFormData(prev => ({
        ...prev,
        detalles: prev.detalles.filter((_, i) => i !== index)
      }));
    }
  };

  const calcularSubtotal = () => {
    const montoTotal = formData.detalles.reduce((acc, detalle) => 
      acc + (detalle.cantidad * detalle.precio_unitario), 0
    );
    
    // Si el IGV está incluido, debemos detraerlo del monto total
    return formData.igv_incluido ? 
      (montoTotal / 1.18) : 
      montoTotal;
  };

  const calcularIGV = () => {
    const subtotal = calcularSubtotal();
    return subtotal * 0.18;
  };

  const calcularTotal = () => {
    const subtotal = calcularSubtotal();
    return subtotal * 1.18;
  };

  const handleTipoVentaChange = (e) => {
    const { value } = e.target;
    let fecha_vencimiento = null;
    let nuevoEstado = 'borrador';

    if (value === 'credito_30') {
      fecha_vencimiento = addDays(new Date(formData.fecha_emision), 30).toISOString().split('T')[0];
      nuevoEstado = 'pendiente';
    } else if (value === 'credito_60') {
      fecha_vencimiento = addDays(new Date(formData.fecha_emision), 60).toISOString().split('T')[0];
      nuevoEstado = 'pendiente';
    }

    setFormData(prev => ({
      ...prev,
      tipo_venta: value,
      fecha_vencimiento,
      estado: nuevoEstado
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    
    if (isSubmitting) {
      return;
    }
    
    setIsSubmitting(true);

    try {
      // Validar cliente
      if (!formData.cliente) {
        toast({
          title: 'Error',
          description: 'Debe seleccionar un cliente',
          status: 'error',
          duration: 2000
        });
        setIsSubmitting(false);
        return;
      }

      // Validar que haya al menos un detalle
      if (!formData.detalles.length) {
        toast({
          title: 'Error',
          description: 'Debe agregar al menos un producto',
          status: 'error',
          duration: 2000
        });
        setIsSubmitting(false);
        return;
      }

      // Validar que todos los detalles tengan producto y cantidad
      const detallesInvalidos = formData.detalles.some(
        detalle => !detalle.producto || !detalle.cantidad || detalle.cantidad <= 0 || !detalle.precio_unitario || detalle.precio_unitario <= 0
      );

      if (detallesInvalidos) {
        toast({
          title: 'Error',
          description: 'Todos los productos deben tener cantidad y precio mayor a 0',
          status: 'error',
          duration: 2000
        });
        setIsSubmitting(false);
        return;
      }

      // Procesar detalles correctamente
      const detallesProcesados = formData.detalles.map(detalle => ({
        producto: parseInt(detalle.producto),
        cantidad: parseFloat(detalle.cantidad),
        precio_unitario: parseFloat(detalle.precio_unitario)
      }));

      await crearVentaMutation.mutateAsync(formData);
    } catch (error) {
      setIsSubmitting(false);
    }
  };

  return (
    <Container maxW="container.xl" py={8}>
      <Box bg="white" p={6} borderRadius="md" boxShadow="sm">
        <Heading size="lg" mb={6} color="blue.600">
          📝 Nueva Venta
        </Heading>
        
        <VStack spacing={4} align="stretch">
          <FormControl isRequired isInvalid={!formData.cliente}>
            <FormLabel>Cliente</FormLabel>
            
            {/* Botones para cambiar entre modos */}
            <HStack mb={3} spacing={2}>
              <Button 
                size="sm" 
                variant={!modoConsultaDocumento ? "solid" : "outline"}
                colorScheme="blue"
                onClick={() => modoConsultaDocumento && toggleModoConsultaDocumento()}
                disabled={!modoConsultaDocumento}
              >
                📝 Buscar por nombre
              </Button>
              <Button 
                size="sm" 
                variant={modoConsultaDocumento ? "solid" : "outline"}
                colorScheme="green"
                onClick={() => !modoConsultaDocumento && toggleModoConsultaDocumento()}
                disabled={modoConsultaDocumento}
              >
                🆔 Buscar/Crear por DNI/RUC
              </Button>
            </HStack>

            {!modoConsultaDocumento ? (
              // Modo búsqueda por nombre (original mejorado)
              <Box position="relative">
                <Input
                  placeholder="Buscar cliente por nombre o documento..."
                  value={clienteSearch}
                  onChange={handleClienteSearchChange}
                  onFocus={() => {
                    if (filteredClientes.length > 0) {
                      setShowClienteDropdown(true);
                    }
                  }}
                  onBlur={() => {
                    setTimeout(() => {
                      setShowClienteDropdown(false);
                      setSelectedClienteIndex(-1);
                    }, 200);
                  }}
                  autoComplete="off"
                />
                {showClienteDropdown && filteredClientes.length > 0 && (
                  <Box
                    position="absolute"
                    top="100%"
                    left="0"
                    right="0"
                    mt={1}
                    bg="white"
                    border="1px solid"
                    borderColor="gray.200"
                    borderRadius="md"
                    boxShadow="lg"
                    zIndex={1000}
                    maxH="200px"
                    overflowY="auto"
                  >
                    <List spacing={0}>
                      {filteredClientes.slice(0, 10).map((cliente, index) => (
                        <ListItem
                          key={cliente.id}
                          p={3}
                          cursor="pointer"
                          bg={selectedClienteIndex === index ? 'blue.50' : 'white'}
                          _hover={{ bg: selectedClienteIndex === index ? 'blue.100' : 'gray.50' }}
                          borderBottom={index < Math.min(filteredClientes.length, 10) - 1 ? '1px solid' : 'none'}
                          borderColor="gray.100"
                          onClick={() => handleClienteSelect(cliente)}
                        >
                          <Text fontSize="sm" fontWeight="medium">
                            {cliente.nombre}
                          </Text>
                          <Text fontSize="xs" color="gray.600">
                            {cliente.documento} • {cliente.email || 'Sin email'}
                          </Text>
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                )}
              </Box>
            ) : (
              // Modo consulta por documento
              <VStack spacing={3} align="stretch">
                <HStack>
                  <Select
                    value={tipoDocumento}
                    onChange={(e) => setTipoDocumento(e.target.value)}
                    width="120px"
                  >
                    <option value="dni">DNI</option>
                    <option value="ruc">RUC</option>
                  </Select>
                  <Input
                    placeholder={`Ingrese ${tipoDocumento.toUpperCase()} ${tipoDocumento === 'dni' ? '(8 dígitos)' : '(11 dígitos)'}`}
                    value={documentoSearch}
                    onChange={(e) => setDocumentoSearch(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && validarDocumento(documentoSearch, tipoDocumento)) {
                        handleBuscarOCrearCliente();
                      }
                    }}
                    maxLength={tipoDocumento === 'dni' ? 8 : 11}
                  />
                  <Button
                    leftIcon={consultandoDocumento ? <Spinner size="sm" /> : <SearchIcon />}
                    colorScheme="green"
                    onClick={handleBuscarOCrearCliente}
                    disabled={consultandoDocumento || !validarDocumento(documentoSearch, tipoDocumento)}
                    minWidth="140px"
                  >
                    {consultandoDocumento ? 'Buscando...' : 'Buscar/Crear'}
                  </Button>
                </HStack>
                
                {errorConsulta && (
                  <Alert status="error" borderRadius="md" fontSize="sm">
                    <AlertIcon />
                    {errorConsulta}
                  </Alert>
                )}
                
                <Text fontSize="sm" color="gray.600">
                  💡 Tip: Si el cliente no está registrado, se creará automáticamente con datos de RENIEC/SUNAT
                </Text>
              </VStack>
            )}

            <FormHelperText>
              {formData.cliente ? 
                `✅ Cliente seleccionado: ${clientesArray.find(c => c.id === parseInt(formData.cliente))?.nombre || 'Desconocido'}` :
                modoConsultaDocumento ? 
                  'Ingrese DNI/RUC para buscar cliente existente o crear uno nuevo automáticamente' :
                  'Escriba para buscar cliente por nombre o documento'
              }
            </FormHelperText>
          </FormControl>
           
          <HStack spacing={4} align="stretch">
            <FormControl isRequired flex="1">
              <FormLabel>Fecha de Emisión</FormLabel>
              <Input
                type="date"
                name="fecha_emision"
                value={formData.fecha_emision}
                onChange={handleChange}
              />
            </FormControl>

            <FormControl flex="1">
              <FormLabel>Estado</FormLabel>
              <Select
                name="estado"
                value={formData.estado}
                onChange={handleChange}
              >
                <option value="borrador">Borrador</option>
                <option value="pendiente">Pendiente</option>
                <option value="pagado">Pagado</option>
                <option value="anulado">Anulado</option>
              </Select>
            </FormControl>
          </HStack>

          <HStack spacing={4} align="stretch">
            <FormControl isRequired flex="1">
              <FormLabel>Tipo de Venta</FormLabel>
              <Select
                name="tipo_venta"
                value={formData.tipo_venta}
                onChange={handleTipoVentaChange}
              >
                {Object.entries(TIPOS_VENTA_DISPLAY).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </Select>
            </FormControl>

            <FormControl flex="1">
              <FormLabel>Modo de Venta</FormLabel>
              <Select
                name="modo_venta"
                value={formData.modo_venta}
                onChange={(e) => setFormData(prev => ({ ...prev, modo_venta: e.target.value }))}
              >
                <option value="stock">Desde Stock (PT disponible)</option>
                <option value="pedido">A Pedido (descontar MP)</option>
              </Select>
              <FormHelperText fontSize="xs">
                {formData.modo_venta === 'pedido' 
                  ? 'Se descontarán las materias primas según la receta' 
                  : 'Se descontará del inventario de productos terminados'}
              </FormHelperText>
            </FormControl>

            <FormControl isRequired flex="1">
              <FormLabel>Método de Pago</FormLabel>
              <Select
                name="metodo_pago"
                value={formData.metodo_pago}
                onChange={handleChange}
              >
                {Object.entries(METODOS_PAGO_DISPLAY).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </Select>
            </FormControl>
          </HStack>

          {formData.tipo_venta !== 'contado' && (
            <FormControl>
              <FormLabel>Fecha de Vencimiento</FormLabel>
              <Input
                type="date"
                name="fecha_vencimiento"
                value={formData.fecha_vencimiento || ''}
                isReadOnly
              />
              <FormHelperText>
                Fecha calculada automáticamente según el plazo de crédito
              </FormHelperText>
            </FormControl>
          )}

          <HStack spacing={4} align="stretch">
            <FormControl isRequired flex="1">
              <FormLabel>Moneda</FormLabel>
              <Select
                name="moneda"
                value={formData.moneda || 'PEN'}
                onChange={handleChange}
              >
                <option value="PEN">Sol Peruano (S/)</option>
                <option value="USD">Dólar Americano ($)</option>
              </Select>
            </FormControl>

            <FormControl flex="1">
              <FormLabel>Comprobante</FormLabel>
              <Input
                type="file"
                onChange={handleFileChange}
                accept=".pdf,.jpg,.jpeg,.png"
              />
            </FormControl>
          </HStack>

          <FormControl>
            <FormLabel>Referencia</FormLabel>
            <Input
              name="referencia"
              value={formData.referencia}
              onChange={handleChange}
              placeholder="Referencia de la venta"
            />
          </FormControl>

          <Box overflowX="auto">
            <Table variant="simple">
              <Thead>
                <Tr>
                  <Th>PRODUCTO</Th>
                  <Th>CANTIDAD</Th>
                  <Th>PRECIO UNIT.</Th>
                  <Th>SUBTOTAL</Th>
                  <Th></Th>
                </Tr>
              </Thead>
              <Tbody>
                {formData.detalles.map((detalle, index) => (
                  <Tr key={index}>
                    <Td>
                      <Select
                        value={detalle.producto}
                        onChange={(e) => handleDetalleChange(index, 'producto', e.target.value)}
                        placeholder="Seleccione un producto"
                      >
                        {Array.isArray(productos) ? productos.map(producto => (
                          <option key={producto.id} value={producto.id}>
                            {producto.nombre} - {producto.sku}
                          </option>
                       )) : null}
                      </Select>
                    </Td>
                    <Td>
                      <NumberInput
                        value={detalle.cantidad}
                        onChange={(value) => handleDetalleChange(index, 'cantidad', value)}
                        min={1}
                      >
                        <NumberInputField />
                      </NumberInput>
                    </Td>
                    <Td>
                      <NumberInput
                        value={detalle.precio_unitario}
                        onChange={(value) => handleDetalleChange(index, 'precio_unitario', value)}
                        min={0}
                      >
                        <NumberInputField />
                      </NumberInput>
                    </Td>
                    <Td>
                      {getSimboloMoneda(formData.moneda)} {(detalle.cantidad * detalle.precio_unitario).toFixed(2)}
                    </Td>
                    <Td>
                      <IconButton
                        icon={<DeleteIcon />}
                        onClick={() => eliminarProducto(index)}
                        isDisabled={formData.detalles.length === 1}
                      />
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Box>

          <Button onClick={agregarProducto} colorScheme="blue">
            Agregar Producto
          </Button>

          <FormControl>
            <FormLabel>IGV Incluido</FormLabel>
            <Switch
              name="igv_incluido"
              isChecked={formData.igv_incluido}
              onChange={(e) => setFormData(prev => ({
                ...prev,
                igv_incluido: e.target.checked
              }))}
            />
          </FormControl>

          <Box textAlign="right">
            <Text>Subtotal: {getSimboloMoneda(formData.moneda)} {calcularSubtotal().toFixed(2)}</Text>
            <Text>IGV (18%): {getSimboloMoneda(formData.moneda)} {calcularIGV().toFixed(2)}</Text>
            <Text fontWeight="bold">Total: {getSimboloMoneda(formData.moneda)} {calcularTotal().toFixed(2)}</Text>
          </Box>

          <Button 
            colorScheme="blue" 
            onClick={handleSubmit}
            isLoading={isSubmitting}
          >
            Guardar Venta
          </Button>
        </VStack>
      </Box>
    </Container>
  );
};

export default NuevaVenta; 