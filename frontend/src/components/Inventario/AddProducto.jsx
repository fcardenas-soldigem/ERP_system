import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Input,
  Textarea,
  VStack,
  useToast,
  Select,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  Checkbox,
  Heading,
  Card,
  CardBody,
  Divider,
  Switch,
  Spinner,
  FormHelperText,
  Alert,
  AlertIcon,
  AlertDescription,
  Tooltip,
  Icon,
  HStack,
  Text,
  Badge
} from '@chakra-ui/react';
import { InfoIcon, WarningIcon } from '@chakra-ui/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { inventarioService } from '../../services/inventario.service';

// Nombres de categorías que se consideran materias primas o insumos
const CATEGORIAS_MATERIA_PRIMA = [
  'materia prima',
  'materias primas',
  'materia_prima',
  'insumo',
  'insumos',
  'raw',
  'raw material',
  'supplies'
];

const AddProducto = () => {
  const toast = useToast();
  const navigate = useNavigate();
  const { id } = useParams();
  const queryClient = useQueryClient();
  const [isLoading, setIsLoading] = useState(false);
  const [producto, setProducto] = useState({
    sku: '',
    nombre: '',
    descripcion: '',
    categoria: '',
    almacen: '',
    precio_compra: '',
    precio_venta: '',
    margen_ganancia: '',
    stock: '',
    stock_total: '',
    stock_minimo: '',
    stock_maximo: '',
    alerta_stock: false,
    activo: true,
    unidad_medida: 'unidad',
    tipo_producto: 'FINISHED' // Por defecto producto terminado
  });

  // Obtener categorías
  const { data: categorias = [], isLoading: isLoadingCategorias, error: errorCategorias } = useQuery({
    queryKey: ['categorias'],
    queryFn: async () => {
      try {
        const response = await inventarioService.getCategorias();
        console.log('Respuesta categorías:', response); // Para debugging
        if (response && response.results) {
          return response.results;
        } else if (Array.isArray(response)) {
          return response;
        }
        return [];
      } catch (error) {
        console.error('Error detallado categorías:', error);
        throw error;
      }
    }
  });

  // Obtener almacenes
  const { data: almacenes = [], isLoading: isLoadingAlmacenes, error: errorAlmacenes } = useQuery({
    queryKey: ['almacenes'],
    queryFn: async () => {
      try {
        const response = await inventarioService.getAlmacenes();
        console.log('Respuesta almacenes:', response); // Para debugging
        if (response && response.results) {
          return response.results;
        } else if (Array.isArray(response)) {
          return response;
        }
        return [];
      } catch (error) {
        console.error('Error detallado almacenes:', error);
        throw error;
      }
    }
  });

  useEffect(() => {
    if (id) {
      inventarioService.getProducto(id).then(data => {
        setProducto(data);
      });
    }
  }, [id]);

  // Detectar si la categoría seleccionada es Materia Prima o Insumo
  const esMateriaPrima = useMemo(() => {
    if (!producto.categoria || !categorias.length) return false;
    
    const categoriaSeleccionada = categorias.find(cat => 
      cat.id === parseInt(producto.categoria) || cat.id === producto.categoria
    );
    
    if (!categoriaSeleccionada) return false;
    
    const nombreCategoria = categoriaSeleccionada.nombre?.toLowerCase().trim() || '';
    
    return CATEGORIAS_MATERIA_PRIMA.some(mp => 
      nombreCategoria.includes(mp) || mp.includes(nombreCategoria)
    );
  }, [producto.categoria, categorias]);

  // Efecto para limpiar campos de venta cuando se selecciona materia prima
  useEffect(() => {
    if (esMateriaPrima) {
      setProducto(prev => ({
        ...prev,
        precio_venta: '',
        margen_ganancia: '',
        tipo_producto: 'RAW' // Marcar como materia prima
      }));
    } else if (producto.tipo_producto === 'RAW') {
      // Si cambia de MP a otra categoría, restaurar tipo
      setProducto(prev => ({
        ...prev,
        tipo_producto: 'FINISHED'
      }));
    }
  }, [esMateriaPrima]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    if (type === 'checkbox') {
      setProducto(prev => ({
        ...prev,
        [name]: checked
      }));
    } else if (name.includes('precio') || name.includes('stock') || name.includes('margen')) {
      // Para campos numéricos, convertir a número y manejar valores vacíos
      const numeroValue = value === '' ? 0 : parseFloat(value);
      setProducto(prev => ({
        ...prev,
        [name]: isNaN(numeroValue) ? 0 : numeroValue
      }));
    } else {
      setProducto(prev => ({
        ...prev,
        [name]: value
      }));
    }
  };

  const handleNumberChange = (name, valueString) => {
    setProducto(prev => ({
      ...prev,
      [name]: valueString
    }));
  };

  const handlePrecioChange = (name, valueString) => {
    setProducto(prev => ({
      ...prev,
      [name]: valueString
    }));
    // Cálculo de margen y precio de venta solo si ambos valores son válidos
    if (name === 'precio_compra' && valueString !== '' && producto.precio_venta !== '') {
      const nuevoMargen = calcularMargen(parseFloat(valueString), parseFloat(producto.precio_venta));
      setProducto(prev => ({ ...prev, margen_ganancia: isNaN(nuevoMargen) ? '' : nuevoMargen.toString() }));
    } else if (name === 'precio_venta' && valueString !== '' && producto.precio_compra !== '') {
      const nuevoMargen = calcularMargen(parseFloat(producto.precio_compra), parseFloat(valueString));
      setProducto(prev => ({ ...prev, margen_ganancia: isNaN(nuevoMargen) ? '' : nuevoMargen.toString() }));
    } else if (name === 'margen_ganancia' && valueString !== '' && producto.precio_compra !== '') {
      const nuevoPrecioVenta = calcularPrecioVenta(parseFloat(producto.precio_compra), parseFloat(valueString));
      setProducto(prev => ({ ...prev, precio_venta: isNaN(nuevoPrecioVenta) ? '' : nuevoPrecioVenta.toString() }));
    }
  };

  const calcularMargen = (precioCompraParam, precioVentaParam) => {
    // Convertir a números y asegurar 2 decimales
    const precioCompra = Math.round(parseFloat(precioCompraParam) * 100) / 100;
    const precioVenta = Math.round(parseFloat(precioVentaParam) * 100) / 100;

    if (precioCompra > 0 && !isNaN(precioVenta) && precioVenta > 0) {
      // Utilidad = Precio de venta - Precio de compra
      const utilidad = Math.round((precioVenta - precioCompra) * 100) / 100;
      // Margen de utilidad (%) = (Utilidad / Precio de venta) × 100
      const margen = Math.round((utilidad / precioVenta * 100) * 100) / 100;
      
      console.log('Calculando margen:', {
        precioCompra: precioCompra.toFixed(2),
        precioVenta: precioVenta.toFixed(2),
        utilidad: utilidad.toFixed(2),
        margen: margen.toFixed(2),
        formula: '((precioVenta - precioCompra) / precioVenta) * 100'
      });
      
      return margen;
    }
    return 0;
  };

  const calcularPrecioVenta = (precioCompraParam, margenParam) => {
    // Convertir a números y asegurar 2 decimales
    const precioCompra = Math.round(parseFloat(precioCompraParam) * 100) / 100;
    const margen = Math.round(parseFloat(margenParam) * 100) / 100;

    if (precioCompra > 0 && !isNaN(margen)) {
      // Si el margen es un porcentaje del precio de venta:
      // PV - PC = margen * PV
      // PV - PC = (margen/100) * PV
      // PV - (margen/100 * PV) = PC
      // PV * (1 - margen/100) = PC
      // PV = PC / (1 - margen/100)
      const precioVenta = Math.round((precioCompra / (1 - margen/100)) * 100) / 100;
      
      console.log('Calculando precio de venta:', {
        precioCompra: precioCompra.toFixed(2),
        margen: margen.toFixed(2),
        precioVenta: precioVenta.toFixed(2),
        formula: 'precioCompra / (1 - margen/100)'
      });
      
      return precioVenta;
    }
    return 0;
  };

  const createMutation = useMutation({
    mutationFn: async (data) => {
      // Determinar si es materia prima
      const esMPData = data.tipo_producto === 'RAW' || data.tipo_producto === 'SEMIFINISHED';
      
      // Validación de precio de compra (siempre requerido)
      if (isNaN(parseFloat(data.precio_compra)) || parseFloat(data.precio_compra) <= 0) {
        throw new Error('El precio de compra debe ser un número válido mayor a 0');
      }
      
      // Validación de precio de venta solo para productos terminados
      if (!esMPData) {
        if (isNaN(parseFloat(data.precio_venta)) || parseFloat(data.precio_venta) <= 0) {
          throw new Error('El precio de venta debe ser un número válido mayor a 0');
        }
      }
      
      // Validación de stock
      if (data.stock_total && (isNaN(parseFloat(data.stock_total)) || parseFloat(data.stock_total) < 0)) {
        throw new Error('El stock total debe ser un número válido mayor o igual a 0');
      }
      
      const productoData = {
        ...data,
        stock: parseFloat(data.stock_total) || 0,
        stock_total: parseFloat(data.stock_total) || 0,
        precio_venta: esMPData ? null : parseFloat(data.precio_venta),
        precio_compra: parseFloat(data.precio_compra),
        margen_ganancia: esMPData ? null : (parseFloat(data.margen_ganancia) || null),
        stock_minimo: parseFloat(data.stock_minimo) || 0,
        stock_maximo: parseFloat(data.stock_maximo) || 0,
        empresa: parseInt(localStorage.getItem('empresa_id')),
        activo: Boolean(data.activo),
        tipo_producto: data.tipo_producto || 'FINISHED'
      };

      console.log('Datos del producto a crear/actualizar:', productoData);
      console.log('Es materia prima:', esMPData);

      if (id) {
        return inventarioService.actualizarProducto(id, productoData);
      }

      // Verificar SKU antes de crear
      try {
        const response = await inventarioService.getProductos();
        const productos = Array.isArray(response) ? response : [];
        
        const skuExists = productos.some(
          p => p.sku === productoData.sku && (!id || p.id !== id)
        );
        
        if (skuExists) {
          throw new Error('Ya existe un producto con este SKU');
        }
        
        const result = await inventarioService.crearProducto(productoData);
        console.log('Respuesta de creación de producto:', result);
        return result;
      } catch (error) {
        console.error('Error completo al crear producto:', error);
        throw error;
      }
    },
    onSuccess: () => {
      // Invalidar todas las queries relacionadas con inventario
      queryClient.invalidateQueries(['productos']);
      queryClient.invalidateQueries(['resumen-inventarios-separados']);
      queryClient.invalidateQueries(['inventario-materias-primas']);
      queryClient.invalidateQueries(['inventario-productos-terminados']);
      queryClient.invalidateQueries(['alertas-materias-primas']);
      queryClient.invalidateQueries(['alertas-productos-terminados']);
      queryClient.invalidateQueries(['valor-total-materias-primas']);
      queryClient.invalidateQueries(['valor-total-productos-terminados']);
      
      toast({
        title: id ? 'Producto actualizado' : 'Producto creado',
        description: 'El producto se ha guardado correctamente',
        status: 'success',
        duration: 3000,
      });
      navigate('/app/inventario');
    },
    onError: (error) => {
      console.error('Error en mutación:', error);
      const errorMessage = error.response?.data?.error 
        || error.message 
        || 'Error al procesar el producto';
      
      toast({
        title: 'Error',
        description: errorMessage,
        status: 'error',
        duration: 3000,
      });
    }
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Validaciones base (siempre aplicables)
    const validacionesBase = [
      { condition: !producto.nombre?.trim(), message: 'El nombre es requerido' },
      { condition: !producto.sku?.trim(), message: 'El SKU es requerido' },
      { condition: !producto.categoria, message: 'La categoría es requerida' },
      { condition: !producto.almacen, message: 'El almacén es requerido' },
      { condition: isNaN(parseFloat(producto.precio_compra)) || parseFloat(producto.precio_compra) <= 0,
        message: 'El precio de compra debe ser un número válido mayor a 0' },
    ];

    // Validaciones adicionales según tipo de producto
    let validaciones = [...validacionesBase];
    
    if (esMateriaPrima) {
      // Para materias primas: NO requiere precio de venta
      validaciones.push({
        condition: producto.precio_venta && parseFloat(producto.precio_venta) > 0,
        message: 'Las materias primas no deben tener precio de venta definido'
      });
    } else {
      // Para productos terminados: SÍ requiere precio de venta
      validaciones.push({
        condition: isNaN(parseFloat(producto.precio_venta)) || parseFloat(producto.precio_venta) <= 0, 
        message: 'El precio de venta debe ser un número válido mayor a 0'
      });
    }

    const error = validaciones.find(v => v.condition);
    if (error) {
      toast({
        title: 'Error de validación',
        description: error.message,
        status: 'error',
        duration: 3000,
      });
      return;
    }

    // Preparar datos según tipo
    // NOTA: precio_venta debe ser 0 (no null) para materias primas porque el modelo no permite null
    const productoAEnviar = {
      ...producto,
      tipo_producto: esMateriaPrima ? 'RAW' : 'FINISHED',
      precio_venta: esMateriaPrima ? 0 : producto.precio_venta,
      margen_ganancia: esMateriaPrima ? 0 : producto.margen_ganancia,
    };

    console.log('Producto a enviar:', productoAEnviar);
    createMutation.mutate(productoAEnviar);
  };

  return (
    <Box p={4}>
      <Card>
        <CardBody>
          <VStack spacing={6} as="form" onSubmit={handleSubmit}>
            <Heading size="md">Información Básica</Heading>
            
            <FormControl isRequired>
              <FormLabel>SKU</FormLabel>
              <Input
                name="sku"
                value={producto.sku}
                onChange={handleChange}
                placeholder="Código SKU del producto"
              />
            </FormControl>

            <FormControl isRequired>
              <FormLabel>Nombre</FormLabel>
              <Input
                name="nombre"
                value={producto.nombre}
                onChange={handleChange}
                placeholder="Nombre del producto"
              />
            </FormControl>

            <FormControl>
              <FormLabel>Descripción</FormLabel>
              <Textarea
                name="descripcion"
                value={producto.descripcion}
                onChange={handleChange}
                placeholder="Descripción del producto"
              />
            </FormControl>

            <FormControl isRequired>
              <FormLabel>Categoría</FormLabel>
              {isLoadingCategorias ? (
                <Spinner size="sm" />
              ) : (
                <Select
                  name="categoria"
                  value={producto.categoria}
                  onChange={handleChange}
                  placeholder="Seleccione una categoría"
                >
                  {categorias && categorias.map(cat => (
                    <option key={cat.id} value={cat.id}>
                      {cat.nombre}
                    </option>
                  ))}
                </Select>
              )}
              {errorCategorias && (
                <FormHelperText color="red.500">
                  Error al cargar las categorías
                </FormHelperText>
              )}
            </FormControl>

            <FormControl isRequired>
              <FormLabel>Almacén</FormLabel>
              {isLoadingAlmacenes ? (
                <Spinner size="sm" />
              ) : (
                <Select
                  name="almacen"
                  value={producto.almacen}
                  onChange={handleChange}
                  placeholder="Seleccione un almacén"
                >
                  {almacenes && almacenes.map(alm => (
                    <option key={alm.id} value={alm.id}>
                      {alm.nombre}
                    </option>
                  ))}
                </Select>
              )}
              {errorAlmacenes && (
                <FormHelperText color="red.500">
                  Error al cargar los almacenes
                </FormHelperText>
              )}
            </FormControl>

            <Divider />
            <HStack justify="space-between" w="full">
              <Heading size="md">Precios</Heading>
              {esMateriaPrima && (
                <Badge colorScheme="blue" fontSize="sm" px={3} py={1} borderRadius="full">
                  🏭 Materia Prima
                </Badge>
              )}
            </HStack>

            {/* Mensaje informativo para materias primas */}
            {esMateriaPrima && (
              <Alert status="info" borderRadius="lg" variant="left-accent">
                <AlertIcon />
                <Box>
                  <Text fontWeight="bold" fontSize="sm">
                    Has seleccionado una categoría de Materia Prima
                  </Text>
                  <AlertDescription fontSize="sm">
                    Este tipo de producto se utiliza para fabricar otros productos y no se vende directamente. 
                    Los campos de precio de venta y margen han sido deshabilitados.
                  </AlertDescription>
                </Box>
              </Alert>
            )}

            <FormControl isRequired>
              <FormLabel>Precio de Compra</FormLabel>
              <NumberInput
                min={0}
                precision={2}
                step={0.01}
                value={producto.precio_compra}
                onChange={(valueString) => handlePrecioChange('precio_compra', valueString)}
                format={val => val}
                parse={val => val.replace(/[^\d.]/g, '')}
              >
                <NumberInputField />
                <NumberInputStepper>
                  <NumberIncrementStepper />
                  <NumberDecrementStepper />
                </NumberInputStepper>
              </NumberInput>
              <FormHelperText>
                {esMateriaPrima 
                  ? 'Costo al que adquieres del proveedor (obligatorio para materias primas)'
                  : 'Precio al que compras el producto'
                }
              </FormHelperText>
            </FormControl>

            <FormControl isDisabled={esMateriaPrima}>
              <HStack>
                <FormLabel mb={0}>Margen de Utilidad (%)</FormLabel>
                {esMateriaPrima && (
                  <Tooltip 
                    label="Campo no disponible para materias primas. Solo los productos terminados tienen margen de venta."
                    placement="top"
                  >
                    <InfoIcon color="gray.400" boxSize={4} />
                  </Tooltip>
                )}
              </HStack>
              <NumberInput
                precision={2}
                step={0.01}
                max={99.99}
                value={esMateriaPrima ? '' : producto.margen_ganancia}
                onChange={(valueString) => !esMateriaPrima && handlePrecioChange('margen_ganancia', valueString)}
                format={val => val}
                parse={val => val.replace(/[^\d.]/g, '')}
                isDisabled={esMateriaPrima}
                bg={esMateriaPrima ? 'gray.100' : 'white'}
              >
                <NumberInputField 
                  bg={esMateriaPrima ? 'gray.100' : 'white'}
                  cursor={esMateriaPrima ? 'not-allowed' : 'text'}
                />
                <NumberInputStepper>
                  <NumberIncrementStepper />
                  <NumberDecrementStepper />
                </NumberInputStepper>
              </NumberInput>
              <FormHelperText color={esMateriaPrima ? 'gray.400' : 'gray.600'}>
                {esMateriaPrima 
                  ? 'No aplica para materias primas'
                  : 'Porcentaje de utilidad sobre el precio de venta. Ejemplo: Si el precio de compra es 100 y el precio de venta es 200, el margen es 50%.'
                }
              </FormHelperText>
            </FormControl>

            <FormControl isRequired={!esMateriaPrima} isDisabled={esMateriaPrima}>
              <HStack>
                <FormLabel mb={0}>Precio de Venta</FormLabel>
                {esMateriaPrima && (
                  <Tooltip 
                    label="Las materias primas no se venden directamente. Solo los productos terminados tienen precio de venta."
                    placement="top"
                  >
                    <InfoIcon color="gray.400" boxSize={4} />
                  </Tooltip>
                )}
              </HStack>
              <NumberInput
                min={0}
                precision={2}
                step={0.01}
                value={esMateriaPrima ? '' : producto.precio_venta}
                onChange={(valueString) => !esMateriaPrima && handlePrecioChange('precio_venta', valueString)}
                format={val => val}
                parse={val => val.replace(/[^\d.]/g, '')}
                isDisabled={esMateriaPrima}
                bg={esMateriaPrima ? 'gray.100' : 'white'}
              >
                <NumberInputField 
                  bg={esMateriaPrima ? 'gray.100' : 'white'}
                  cursor={esMateriaPrima ? 'not-allowed' : 'text'}
                />
                <NumberInputStepper>
                  <NumberIncrementStepper />
                  <NumberDecrementStepper />
                </NumberInputStepper>
              </NumberInput>
              <FormHelperText color={esMateriaPrima ? 'gray.400' : 'gray.600'}>
                {esMateriaPrima 
                  ? 'No aplica para materias primas - se utilizan en producción, no en ventas directas'
                  : 'Precio al que vendes el producto'
                }
              </FormHelperText>
            </FormControl>

            <FormControl isRequired>
              <FormLabel>Moneda</FormLabel>
              <Select
                name="moneda"
                value={producto.moneda || 'PEN'}
                onChange={handleChange}
              >
                <option value="PEN">Sol Peruano (S/)</option>
                <option value="USD">Dólar Americano ($)</option>
              </Select>
              <FormHelperText>Moneda para precios de compra y venta</FormHelperText>
            </FormControl>

            <FormControl isRequired>
              <FormLabel>Unidad de Medida</FormLabel>
              <Select
                name="unidad_medida"
                value={producto.unidad_medida}
                onChange={handleChange}
              >
                <option value="unidad">Unidad</option>
                <option value="kilo">Kilogramo (Kg)</option>
                <option value="gramo">Gramo (g)</option>
                <option value="litro">Litro (L)</option>
                <option value="metro">Metro (m)</option>
                <option value="decena">Decena</option>
                <option value="docena">Docena (12 unidades)</option>
                <option value="centenar">Centenar (100 unidades)</option>
                <option value="millar">Millar (1000 unidades)</option>
              </Select>
              <FormHelperText>Unidad en la que se mide el producto</FormHelperText>
            </FormControl>

            <Divider />
            <Heading size="md">Stock</Heading>

            <FormControl isRequired>
              <FormLabel>Stock Total</FormLabel>
              <NumberInput
                min={0}
                precision={2}
                step={0.01}
                value={producto.stock_total}
                onChange={(valueString) => handleNumberChange('stock_total', valueString)}
                format={val => val}
                parse={val => val.replace(/[^\d.]/g, '')}
              >
                <NumberInputField />
                <NumberInputStepper>
                  <NumberIncrementStepper />
                  <NumberDecrementStepper />
                </NumberInputStepper>
              </NumberInput>
            </FormControl>

            <FormControl>
              <FormLabel>Stock Mínimo</FormLabel>
              <NumberInput
                min={0}
                precision={2}
                step={0.01}
                value={producto.stock_minimo}
                onChange={(valueString) => handleNumberChange('stock_minimo', valueString)}
                format={val => val}
                parse={val => val.replace(/[^\d.]/g, '')}
              >
                <NumberInputField />
                <NumberInputStepper>
                  <NumberIncrementStepper />
                  <NumberDecrementStepper />
                </NumberInputStepper>
              </NumberInput>
            </FormControl>

            <FormControl>
              <FormLabel>Stock Máximo</FormLabel>
              <NumberInput
                min={0}
                precision={2}
                step={0.01}
                value={producto.stock_maximo}
                onChange={(valueString) => handleNumberChange('stock_maximo', valueString)}
                format={val => val}
                parse={val => val.replace(/[^\d.]/g, '')}
              >
                <NumberInputField />
                <NumberInputStepper>
                  <NumberIncrementStepper />
                  <NumberDecrementStepper />
                </NumberInputStepper>
              </NumberInput>
            </FormControl>

            <FormControl display="flex" alignItems="center">
              <FormLabel mb="0">Alerta de Stock</FormLabel>
              <Switch
                name="alerta_stock"
                isChecked={producto.alerta_stock}
                onChange={handleChange}
              />
            </FormControl>

            <Divider />
            <Heading size="md">Estado</Heading>

            <FormControl display="flex" alignItems="center">
              <FormLabel mb="0">Activo</FormLabel>
              <Switch
                name="activo"
                isChecked={producto.activo}
                onChange={handleChange}
              />
            </FormControl>

            <Button
              mt={4}
              colorScheme="blue"
              type="submit"
              isLoading={createMutation.isLoading}
              width="full"
            >
              {id ? 'Actualizar Producto' : 'Crear Producto'}
            </Button>
          </VStack>
        </CardBody>
      </Card>
    </Box>
  );
};

export default AddProducto; 