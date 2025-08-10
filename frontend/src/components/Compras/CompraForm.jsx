import React, { useState, useEffect } from 'react';
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
  Container,
  Heading,
  Card,
  CardBody,
} from '@chakra-ui/react';
import { AddIcon, DeleteIcon } from '@chakra-ui/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { comprasService } from '../../services/compras.service';
import ProveedorSelect from '../Proveedores/ProveedorSelect';
import { TIPOS_COMPRA, METODOS_PAGO, TIPOS_COMPRA_DISPLAY, METODOS_PAGO_DISPLAY } from './constants';
import { addDays } from 'date-fns';

// Función para formatear moneda según la moneda seleccionada
const formatCurrency = (amount, moneda = 'PEN') => {
  const formatters = {
    'PEN': new Intl.NumberFormat('es-PE', {
      style: 'currency',
      currency: 'PEN'
    }),
    'USD': new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    })
  };
  
  return formatters[moneda] ? formatters[moneda].format(amount) : `${moneda} ${amount.toFixed(2)}`;
};

const CompraForm = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [igvIncluido, setIgvIncluido] = useState(false);
  const [comprobante, setComprobante] = useState(null);
  const [formData, setFormData] = useState({
    proveedor: '',
    almacen: '',
    fecha_emision: new Date().toISOString().split('T')[0],
    fecha_vencimiento: null,
    estado: 'pagada',
    tipo_compra: 'contado',
    metodo_pago: 'efectivo',
    igv_incluido: false,
    moneda: 'PEN',
    referencia: '',
    comprobante: null,
    detalles: [{
      producto: '',
      cantidad: 1,
      precio_unitario: 0
    }]
  });
  const queryClient = useQueryClient();

  // Obtener lista de almacenes
  const { data: almacenesData = [], isLoading: isLoadingAlmacenes } = useQuery({
    queryKey: ['almacenes'],
    queryFn: () => comprasService.getAlmacenes(),
  });

  // Asegurar que almacenes siempre sea un array
  const almacenes = Array.isArray(almacenesData) ? almacenesData : [];

  // Obtener lista de productos
  const { data: productosData = [], isLoading: isLoadingProductos } = useQuery({
    queryKey: ['productos'],
    queryFn: () => comprasService.getProductos(),
  });

  // Asegurar que productos siempre sea un array
  const productos = Array.isArray(productosData) ? productosData : [];

  // Limpiar caché al montar el componente
  useEffect(() => {
    queryClient.invalidateQueries(['proveedores']);
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

  const crearCompraMutation = useMutation({
    mutationFn: comprasService.createCompra,
    onSuccess: () => {
      queryClient.invalidateQueries(['compras']);
      queryClient.invalidateQueries(['productos']);
      queryClient.invalidateQueries(['proveedores']);
      toast({
        title: 'Compra creada',
        description: 'La compra se ha creado exitosamente',
        status: 'success',
        duration: 2000
      });
      navigate('/compras');
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
          precio_unitario: Number(producto.precio_compra) || 0
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

  const handleTipoCompraChange = (e) => {
    const { value } = e.target;
    let fecha_vencimiento = null;
    let nuevoEstado = 'pagada'; // Por defecto pagada para contado

    if (value === 'credito_30') {
      fecha_vencimiento = addDays(new Date(formData.fecha_emision), 30).toISOString().split('T')[0];
      nuevoEstado = 'pendiente';
    } else if (value === 'credito_60') {
      fecha_vencimiento = addDays(new Date(formData.fecha_emision), 60).toISOString().split('T')[0];
      nuevoEstado = 'pendiente';
    }

    setFormData(prev => ({
      ...prev,
      tipo_compra: value,
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
      // Validar proveedor
      if (!formData.proveedor) {
        toast({
          title: 'Error',
          description: 'Debe seleccionar un proveedor',
          status: 'error',
          duration: 2000
        });
        setIsSubmitting(false);
        return;
      }

      // Validar almacén
      if (!formData.almacen) {
        toast({
          title: 'Error',
          description: 'Debe seleccionar un almacén',
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

      // Procesar los detalles
      const detalles = formData.detalles
        .filter(detalle => detalle.producto && detalle.cantidad && detalle.precio_unitario)
        .map(detalle => ({
          producto: parseInt(detalle.producto),
          cantidad: parseFloat(detalle.cantidad),
          precio_unitario: parseFloat(detalle.precio_unitario)
        }));

      // Crear FormData
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
      
      // Agregar fecha de vencimiento si es compra a crédito
      if (formData.tipo_compra !== 'contado' && formData.fecha_vencimiento) {
        compraDataToSend.append('fecha_vencimiento', formData.fecha_vencimiento);
      }

      if (formData.comprobante) {
        compraDataToSend.append('comprobante', formData.comprobante);
      }

      await crearCompraMutation.mutateAsync(compraDataToSend);
      
      toast({
        title: 'Éxito',
        description: 'Compra creada correctamente',
        status: 'success',
        duration: 2000
      });
      
      navigate('/compras');
    } catch (error) {
      console.error('Error al crear la compra:', error);
      toast({
        title: 'Error',
        description: error.message || 'Error al crear la compra',
        status: 'error',
        duration: 2000
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Container maxW="container.xl" py={5}>
      <Card>
        <CardBody>
          <VStack spacing={5} align="stretch">
            <Heading size="lg">Nueva Factura de Compra</Heading>
            <form onSubmit={handleSubmit}>
              <VStack spacing={4} align="stretch">
                <ProveedorSelect
                  value={formData.proveedor}
                  onChange={(value) => setFormData(prev => ({ ...prev, proveedor: value }))}
                />

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
                      {almacenes.map(almacen => (
                        <option key={almacen.id} value={almacen.id}>
                          {almacen.nombre}
                        </option>
                      ))}
                    </Select>
                  )}
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
                      value={formData.estado}
                      onChange={handleChange}
                      name="estado"
                    >
                      <option value="borrador">Borrador</option>
                      <option value="pendiente">Pendiente</option>
                      <option value="pagada">Pagada</option>
                      <option value="anulada">Anulada</option>
                    </Select>
                  </FormControl>
                </HStack>

                <HStack spacing={4} align="stretch">
                  <FormControl isRequired flex="1">
                    <FormLabel>Tipo de Compra</FormLabel>
                    <Select
                      value={formData.tipo_compra}
                      onChange={handleTipoCompraChange}
                      name="tipo_compra"
                    >
                      {Object.entries(TIPOS_COMPRA_DISPLAY).map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </Select>
                  </FormControl>

                  <FormControl isRequired flex="1">
                    <FormLabel>Método de Pago</FormLabel>
                    <Select
                      value={formData.metodo_pago}
                      onChange={handleChange}
                      name="metodo_pago"
                    >
                      {Object.entries(METODOS_PAGO_DISPLAY).map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </Select>
                  </FormControl>
                </HStack>

                {formData.tipo_compra !== 'contado' && (
                  <FormControl>
                    <FormLabel>Fecha de Vencimiento</FormLabel>
                    <Input
                      type="date"
                      value={formData.fecha_vencimiento || ''}
                      isReadOnly
                      name="fecha_vencimiento"
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
                      sx={{
                        '::file-selector-button': {
                          height: '100%',
                          padding: '0 20px',
                          background: 'gray.100',
                          border: 'none',
                          borderRight: '1px solid',
                          borderColor: 'gray.200',
                          cursor: 'pointer',
                          '&:hover': {
                            background: 'gray.200'
                          }
                        }
                      }}
                    />
                    <FormHelperText>
                      Formatos permitidos: PDF, JPG, PNG. Tamaño máximo: 5MB
                    </FormHelperText>
                  </FormControl>
                </HStack>

                <FormControl>
                  <FormLabel>Referencia de Pago</FormLabel>
                  <Input 
                    name="referencia"
                    value={formData.referencia}
                    onChange={handleChange}
                    placeholder="Número de operación, cheque, etc." 
                  />
                </FormControl>

                <Table size="sm" variant="simple">
                  <Thead>
                    <Tr>
                      <Th>Producto</Th>
                      <Th>Cantidad</Th>
                      <Th>Precio Unit.</Th>
                      <Th>Subtotal</Th>
                      <Th></Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {(formData.detalles.length > 0 ? formData.detalles : [{ producto: '', cantidad: 1, precio_unitario: 0 }]).map((detalle, index) => (
                      <Tr key={index}>
                        <Td>
                          <Select
                            value={detalle.producto ? detalle.producto.toString() : ''}
                            onChange={(e) => handleDetalleChange(index, 'producto', e.target.value)}
                          >
                            <option value="">Seleccione un producto</option>
                            {productos.map(producto => (
                              <option key={producto.id} value={producto.id}>
                                {producto.nombre} - {producto.sku}
                              </option>
                            ))}
                          </Select>
                        </Td>
                        <Td>
                          <NumberInput
                            min={1}
                            value={detalle?.cantidad || 1}
                            onChange={(value) => handleDetalleChange(index, 'cantidad', value)}
                          >
                            <NumberInputField />
                          </NumberInput>
                        </Td>
                        <Td>
                          <NumberInput
                            min={0}
                            precision={2}
                            value={detalle?.precio_unitario || 0}
                            onChange={(value) => handleDetalleChange(index, 'precio_unitario', value)}
                            isInvalid={Number(detalle?.precio_unitario) === 0}
                          >
                            <NumberInputField />
                          </NumberInput>
                          {Number(detalle?.precio_unitario) === 0 && (
                            <Text color="red.500" fontSize="xs">Ingrese un precio válido</Text>
                          )}
                        </Td>
                        <Td>
                          {formatCurrency((detalle?.cantidad || 0) * (detalle?.precio_unitario || 0), formData.moneda)}
                        </Td>
                        <Td>
                          <IconButton
                            icon={<DeleteIcon />}
                            size="sm"
                            onClick={() => {
                              if (formData.detalles.length > 1) {
                                setFormData(prev => ({
                                  ...prev,
                                  detalles: prev.detalles.filter((_, i) => i !== index)
                                }));
                              }
                            }}
                            isDisabled={formData.detalles.length === 1}
                          />
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>

                <Button
                  leftIcon={<AddIcon />}
                  onClick={agregarProducto}
                >
                  Agregar Producto
                </Button>

                <FormControl>
                  <FormLabel>IGV Incluido</FormLabel>
                  <Switch
                    isChecked={formData.igv_incluido}
                    onChange={(e) => {
                      setFormData(prev => ({
                        ...prev,
                        igv_incluido: e.target.checked
                      }));
                    }}
                    name="igv_incluido"
                  />
                  <FormHelperText>
                    {formData.igv_incluido 
                      ? "Los precios ingresados incluyen IGV" 
                      : "Los precios ingresados no incluyen IGV"}
                  </FormHelperText>
                </FormControl>

                <Box borderTop="1px" borderColor="gray.200" pt={4} mt={4}>
                  <VStack align="flex-end" spacing={2}>
                    <Text>Subtotal: {formatCurrency(calcularSubtotal(), formData.moneda)}</Text>
                    <Text>IGV (18%): {formatCurrency(calcularIGV(), formData.moneda)}</Text>
                    <Text fontWeight="bold" fontSize="lg">
                      Total: {formatCurrency(calcularTotal(), formData.moneda)}
                    </Text>
                  </VStack>
                </Box>

                <HStack justify="flex-end" spacing={4} pt={4}>
                  <Button onClick={() => navigate('/compras')}>Cancelar</Button>
                  <Button
                    type="submit"
                    colorScheme="blue"
                    isLoading={isSubmitting}
                  >
                    Crear Compra
                  </Button>
                </HStack>
              </VStack>
            </form>
          </VStack>
        </CardBody>
      </Card>
    </Container>
  );
};

export default CompraForm;