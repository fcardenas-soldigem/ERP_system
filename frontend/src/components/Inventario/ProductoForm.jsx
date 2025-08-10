import React, { useState, useEffect } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  FormControl,
  FormLabel,
  Input,
  Select,
  Button,
  VStack,
  useToast,
  NumberInput,
  NumberInputField,
  FormErrorMessage,
  Switch,
  FormHelperText,
  Spinner,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper
} from '@chakra-ui/react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { productosService } from '../../services/productos.service';
import { api } from '../../api';

const ProductoForm = ({ isOpen, onClose, productoInicial = null }) => {
  const queryClient = useQueryClient();
  const toast = useToast();

  const [producto, setProducto] = useState({
    nombre: '',
    descripcion: '',
    categoria: '',
    sku: '',
    precio_venta: 0,
    precio_compra: 0,
    stock_minimo: 0,
    stock_maximo: 0,
    stock_inicial: 0,
    almacen: '',
    activo: true,
    ...(productoInicial || {})
  });

  // Obtener categorías
  const { data: categorias = [], isLoading: isLoadingCategorias, error: errorCategorias } = useQuery({
    queryKey: ['categorias'],
    queryFn: async () => {
      const response = await api.get('/api/inventario/categorias/');
      return Array.isArray(response.data) ? response.data : 
             Array.isArray(response.data.results) ? response.data.results : [];
    },
    onError: (error) => {
      console.error('Error al cargar categorías:', error);
      toast({
        title: 'Error al cargar categorías',
        description: error.message,
        status: 'error',
        duration: 3000,
      });
    }
  });

  // Obtener almacenes
  const { data: almacenes = [], isLoading: isLoadingAlmacenes, error: errorAlmacenes } = useQuery({
    queryKey: ['almacenes'],
    queryFn: async () => {
      const response = await api.get('/api/inventario/almacenes/');
      return Array.isArray(response.data) ? response.data : 
             Array.isArray(response.data.results) ? response.data.results : [];
    },
    onError: (error) => {
      console.error('Error al cargar almacenes:', error);
      toast({
        title: 'Error al cargar almacenes',
        description: error.message,
        status: 'error',
        duration: 3000,
      });
    }
  });

  // Agregar console.log para debug
  console.log('Categorías cargadas:', categorias);
  console.log('Almacenes cargados:', almacenes);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    
    if (type === 'checkbox') {
      setProducto(prev => ({
        ...prev,
        [name]: checked
      }));
    } else if (name.includes('precio') || name.includes('stock')) {
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

  const handleNumberChange = (name, value) => {
    setProducto(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const mutation = useMutation({
    mutationFn: async (data) => {
      const productoData = {
        ...data,
        precio_venta: parseFloat(data.precio_venta),
        precio_compra: parseFloat(data.precio_compra),
        stock_minimo: parseFloat(data.stock_minimo),
        stock_maximo: parseFloat(data.stock_maximo),
        stock: parseFloat(data.stock_inicial),
        empresa: parseInt(localStorage.getItem('empresa_id')),
        activo: Boolean(data.activo)
      };

      if (productoInicial) {
        return productosService.updateProducto(productoInicial.id, productoData);
      }

      // Verificar SKU antes de crear
      try {
        const response = await productosService.getProductos();
        const productos = Array.isArray(response) ? response : 
                         Array.isArray(response.data) ? response.data : [];
        
        const skuExists = productos.some(
          p => p.sku === productoData.sku && (!productoInicial || p.id !== productoInicial.id)
        );
        
        if (skuExists) {
          throw new Error('Ya existe un producto con este SKU');
        }
        
        return productosService.createProducto(productoData);
      } catch (error) {
        throw error;
      }
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries(['productos']);
      toast({
        title: productoInicial ? 'Producto actualizado' : 'Producto creado',
        status: 'success',
        duration: 2000,
      });
      onClose();
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validaciones básicas
    const validaciones = [
      { condition: !producto.nombre?.trim(), message: 'El nombre es requerido' },
      { condition: !producto.sku?.trim(), message: 'El SKU es requerido' },
      { condition: !producto.precio_venta || parseFloat(producto.precio_venta) <= 0, message: 'El precio de venta debe ser mayor a 0' },
      { condition: !producto.categoria, message: 'La categoría es requerida' },
      { condition: !producto.almacen, message: 'El almacén es requerido' },
      { condition: producto.stock < 0, message: 'El stock no puede ser negativo' }
    ];

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

    try {
      mutation.mutate(producto);
    } catch (error) {
      console.error('Error al enviar formulario:', error);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>
          {productoInicial ? 'Editar Producto' : 'Nuevo Producto'}
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <form onSubmit={handleSubmit}>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel>SKU</FormLabel>
                <Input
                  name="sku"
                  value={producto.sku}
                  onChange={handleChange}
                />
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Nombre</FormLabel>
                <Input
                  name="nombre"
                  value={producto.nombre}
                  onChange={handleChange}
                />
              </FormControl>

              <FormControl>
                <FormLabel>Descripción</FormLabel>
                <Input
                  name="descripcion"
                  value={producto.descripcion}
                  onChange={handleChange}
                />
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Precio de Venta</FormLabel>
                <NumberInput
                  min={0}
                  precision={2}
                  step={0.01}
                  value={producto.precio_venta}
                  onChange={(value) => handleChange({ target: { name: 'precio_venta', value } })}
                >
                  <NumberInputField />
                  <NumberInputStepper>
                    <NumberIncrementStepper />
                    <NumberDecrementStepper />
                  </NumberInputStepper>
                </NumberInput>
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Precio de Compra</FormLabel>
                <NumberInput
                  min={0}
                  precision={2}
                  step={0.01}
                  value={producto.precio_compra}
                  onChange={(value) => handleChange({ target: { name: 'precio_compra', value } })}
                >
                  <NumberInputField />
                  <NumberInputStepper>
                    <NumberIncrementStepper />
                    <NumberDecrementStepper />
                  </NumberInputStepper>
                </NumberInput>
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
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Stock Inicial</FormLabel>
                <NumberInput
                  min={0}
                  precision={2}
                  step={0.01}
                  value={producto.stock_inicial}
                  onChange={(value) => handleChange({ target: { name: 'stock_inicial', value } })}
                >
                  <NumberInputField />
                  <NumberInputStepper>
                    <NumberIncrementStepper />
                    <NumberDecrementStepper />
                  </NumberInputStepper>
                </NumberInput>
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Stock Mínimo</FormLabel>
                <NumberInput
                  min={0}
                  precision={2}
                  step={0.01}
                  value={producto.stock_minimo}
                  onChange={(value) => handleChange({ target: { name: 'stock_minimo', value } })}
                >
                  <NumberInputField />
                  <NumberInputStepper>
                    <NumberIncrementStepper />
                    <NumberDecrementStepper />
                  </NumberInputStepper>
                </NumberInput>
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Stock Máximo</FormLabel>
                <NumberInput
                  min={0}
                  precision={2}
                  step={0.01}
                  value={producto.stock_maximo}
                  onChange={(value) => handleChange({ target: { name: 'stock_maximo', value } })}
                >
                  <NumberInputField />
                  <NumberInputStepper>
                    <NumberIncrementStepper />
                    <NumberDecrementStepper />
                  </NumberInputStepper>
                </NumberInput>
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
                    {Array.isArray(categorias) && categorias.map(categoria => (
                      <option key={categoria.id} value={categoria.id}>
                        {categoria.nombre}
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
                    {Array.isArray(almacenes) && almacenes.map(alm => (
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

              <FormControl display='flex' alignItems='center'>
                <FormLabel mb='0'>Activo</FormLabel>
                <Switch
                  name="activo"
                  isChecked={producto.activo}
                  onChange={(e) => handleChange({
                    target: {
                      name: 'activo',
                      type: 'checkbox',
                      checked: e.target.checked
                    }
                  })}
                />
              </FormControl>

              <Button
                type="submit"
                colorScheme="blue"
                isLoading={mutation.isLoading}
                width="full"
              >
                {productoInicial ? 'Actualizar' : 'Crear'}
              </Button>
            </VStack>
          </form>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

export default ProductoForm;