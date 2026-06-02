import React, { useState, useEffect, useCallback } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  Button,
  FormControl,
  FormLabel,
  Input,
  Select,
  Textarea,
  VStack,
  HStack,
  Text,
  Box,
  Divider,
  Badge,
  useToast,
  InputGroup,
  InputLeftAddon,
  Spinner,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import { FaBoxOpen, FaSave } from 'react-icons/fa';
import { inventarioAPI } from '../../lib/api';
import cotizacionesService from '../../services/cotizacionesService';

const UNIDADES_MEDIDA = [
  { value: 'unidad', label: 'Unidad' },
  { value: 'kilo', label: 'Kilogramo' },
  { value: 'gramo', label: 'Gramo' },
  { value: 'litro', label: 'Litro' },
  { value: 'metro', label: 'Metro' },
  { value: 'decena', label: 'Decena' },
  { value: 'docena', label: 'Docena' },
  { value: 'centenar', label: 'Centenar' },
  { value: 'millar', label: 'Millar' },
];

const ProductoForm = ({ producto, index, moneda, onChange, categorias, almacenes }) => {
  const simbolo = moneda === 'USD' ? '$' : 'S/';

  const handleChange = (field, value) => {
    onChange(index, { ...producto, [field]: value });
  };

  return (
    <Box
      border="1px solid"
      borderColor="gray.200"
      borderRadius="lg"
      p={5}
      bg="white"
    >
      <HStack mb={4} spacing={3}>
        <Box p={2} bg="blue.50" borderRadius="md">
          <FaBoxOpen color="var(--chakra-colors-blue-500)" />
        </Box>
        <Box flex="1">
          <Text fontWeight="600" fontSize="sm" color="gray.800">
            {producto.descripcion}
          </Text>
          <HStack spacing={2} mt={1}>
            <Badge colorScheme="gray" fontSize="xs">
              Cant: {producto.cantidad}
            </Badge>
            <Badge colorScheme="blue" fontSize="xs">
              {simbolo} {parseFloat(producto.precio_unitario).toFixed(2)}
            </Badge>
          </HStack>
        </Box>
      </HStack>

      <VStack spacing={3}>
        <HStack spacing={3} w="full">
          <FormControl isRequired>
            <FormLabel fontSize="xs" fontWeight="500" color="gray.600" mb={1}>
              Nombre del producto
            </FormLabel>
            <Input
              size="sm"
              value={producto.nombre}
              onChange={(e) => handleChange('nombre', e.target.value)}
              borderRadius="md"
            />
          </FormControl>
          <FormControl isRequired>
            <FormLabel fontSize="xs" fontWeight="500" color="gray.600" mb={1}>
              SKU
            </FormLabel>
            <Input
              size="sm"
              placeholder="Ej: PROD-001"
              value={producto.sku}
              onChange={(e) => handleChange('sku', e.target.value)}
              borderRadius="md"
            />
          </FormControl>
        </HStack>

        <FormControl>
          <FormLabel fontSize="xs" fontWeight="500" color="gray.600" mb={1}>
            Descripción
          </FormLabel>
          <Textarea
            size="sm"
            rows={2}
            value={producto.descripcionProducto}
            onChange={(e) => handleChange('descripcionProducto', e.target.value)}
            borderRadius="md"
          />
        </FormControl>

        <HStack spacing={3} w="full">
          <FormControl>
            <FormLabel fontSize="xs" fontWeight="500" color="gray.600" mb={1}>
              Precio de venta
            </FormLabel>
            <InputGroup size="sm">
              <InputLeftAddon>{simbolo}</InputLeftAddon>
              <Input
                type="number"
                step="0.01"
                value={producto.precio_venta}
                onChange={(e) => handleChange('precio_venta', e.target.value)}
                borderRadius="md"
              />
            </InputGroup>
          </FormControl>
          <FormControl>
            <FormLabel fontSize="xs" fontWeight="500" color="gray.600" mb={1}>
              Precio de compra
            </FormLabel>
            <InputGroup size="sm">
              <InputLeftAddon>{simbolo}</InputLeftAddon>
              <Input
                type="number"
                step="0.01"
                placeholder="0.00"
                value={producto.precio_compra}
                onChange={(e) => handleChange('precio_compra', e.target.value)}
                borderRadius="md"
              />
            </InputGroup>
          </FormControl>
        </HStack>

        <HStack spacing={3} w="full">
          <FormControl>
            <FormLabel fontSize="xs" fontWeight="500" color="gray.600" mb={1}>
              Categoría
            </FormLabel>
            <Select
              size="sm"
              placeholder="Seleccionar..."
              value={producto.categoria_id}
              onChange={(e) => handleChange('categoria_id', e.target.value)}
              borderRadius="md"
            >
              {categorias.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.nombre}
                </option>
              ))}
            </Select>
          </FormControl>
          <FormControl>
            <FormLabel fontSize="xs" fontWeight="500" color="gray.600" mb={1}>
              Almacén
            </FormLabel>
            <Select
              size="sm"
              placeholder="Seleccionar..."
              value={producto.almacen_id}
              onChange={(e) => handleChange('almacen_id', e.target.value)}
              borderRadius="md"
            >
              {almacenes.map((alm) => (
                <option key={alm.id} value={alm.id}>
                  {alm.nombre}
                </option>
              ))}
            </Select>
          </FormControl>
          <FormControl>
            <FormLabel fontSize="xs" fontWeight="500" color="gray.600" mb={1}>
              Unidad de medida
            </FormLabel>
            <Select
              size="sm"
              value={producto.unidad_medida}
              onChange={(e) => handleChange('unidad_medida', e.target.value)}
              borderRadius="md"
            >
              {UNIDADES_MEDIDA.map((u) => (
                <option key={u.value} value={u.value}>
                  {u.label}
                </option>
              ))}
            </Select>
          </FormControl>
        </HStack>
      </VStack>
    </Box>
  );
};

const CrearProductosCotizacionModal = ({
  isOpen,
  onClose,
  productosFaltantes,
  cotizacionId,
  moneda,
  onConversionExitosa,
}) => {
  const toast = useToast();
  const [productos, setProductos] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [almacenes, setAlmacenes] = useState([]);
  const [saving, setSaving] = useState(false);
  const [loadingCatalogos, setLoadingCatalogos] = useState(true);

  const cargarCatalogos = useCallback(async () => {
    try {
      setLoadingCatalogos(true);
      const [catRes, almRes] = await Promise.all([
        inventarioAPI.getCategorias(),
        inventarioAPI.getAlmacenes(),
      ]);
      setCategorias(catRes.data?.results || catRes.data || []);
      setAlmacenes(almRes.data?.results || almRes.data || []);
    } catch (err) {
      console.error('Error cargando catálogos:', err);
    } finally {
      setLoadingCatalogos(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen && productosFaltantes?.length > 0) {
      cargarCatalogos();
      setProductos(
        productosFaltantes.map((pf) => ({
          detalle_id: pf.detalle_id,
          descripcion: pf.descripcion,
          codigo: pf.codigo,
          cantidad: pf.cantidad,
          precio_unitario: pf.precio_unitario,
          nombre: pf.descripcion,
          descripcionProducto: pf.descripcion,
          precio_venta: pf.precio_unitario,
          precio_compra: '',
          sku: pf.codigo || '',
          categoria_id: '',
          almacen_id: '',
          unidad_medida: 'unidad',
        }))
      );
    }
  }, [isOpen, productosFaltantes, cargarCatalogos]);

  const handleProductoChange = (index, updated) => {
    setProductos((prev) => prev.map((p, i) => (i === index ? updated : p)));
  };

  const validar = () => {
    for (let i = 0; i < productos.length; i++) {
      const p = productos[i];
      if (!p.nombre?.trim()) return `Producto ${i + 1}: falta nombre`;
      if (!p.sku?.trim()) return `Producto ${i + 1}: falta SKU`;
    }
    return null;
  };

  const handleGuardar = async () => {
    const errorMsg = validar();
    if (errorMsg) {
      toast({
        title: 'Campos requeridos',
        description: errorMsg,
        status: 'warning',
        duration: 4000,
        isClosable: true,
      });
      return;
    }

    setSaving(true);
    try {
      for (const prod of productos) {
        const payload = {
          nombre: prod.nombre.trim(),
          descripcion: prod.descripcionProducto || '',
          sku: prod.sku.trim(),
          precio_venta: parseFloat(prod.precio_venta) || 0,
          precio_compra: parseFloat(prod.precio_compra) || 0,
          moneda: moneda || 'PEN',
          tipo_producto: 'FINISHED',
          unidad_medida: prod.unidad_medida || 'unidad',
          ...(prod.categoria_id ? { categoria: parseInt(prod.categoria_id) } : {}),
          ...(prod.almacen_id ? { almacen: parseInt(prod.almacen_id) } : {}),
        };

        const createRes = await inventarioAPI.createProducto(payload);
        const nuevoProductoId = createRes.data?.id || createRes.data?.producto?.id;

        if (!nuevoProductoId) {
          throw new Error(`No se recibió ID al crear el producto "${prod.nombre}"`);
        }

        await cotizacionesService.vincularProducto(
          cotizacionId,
          prod.detalle_id,
          nuevoProductoId
        );
      }

      toast({
        title: 'Productos creados',
        description: `${productos.length} producto(s) registrado(s). Convirtiendo a venta...`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });

      const result = await cotizacionesService.convertirVenta(cotizacionId);

      toast({
        title: 'Venta creada',
        description: result.message || `Venta ${result.venta_numero} creada exitosamente`,
        status: 'success',
        duration: 4000,
        isClosable: true,
      });

      onClose();
      if (onConversionExitosa) {
        onConversionExitosa(result);
      }
    } catch (err) {
      console.error('Error al crear productos / convertir:', err);
      const detail =
        err.response?.data?.error ||
        err.response?.data?.detail ||
        err.response?.data?.sku?.[0] ||
        err.message;

      if (err.response?.data?.error === 'productos_faltantes') {
        toast({
          title: 'Aún faltan productos',
          description: 'Verifica que todos los productos se hayan creado correctamente.',
          status: 'warning',
          duration: 5000,
          isClosable: true,
        });
      } else {
        toast({
          title: 'Error',
          description: detail || 'Ocurrió un error inesperado',
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      size="3xl"
      scrollBehavior="inside"
      closeOnOverlayClick={!saving}
    >
      <ModalOverlay bg="blackAlpha.400" backdropFilter="blur(4px)" />
      <ModalContent borderRadius="xl" mx={4}>
        <ModalHeader pb={2}>
          <VStack align="start" spacing={1}>
            <Text fontSize="lg" fontWeight="700" color="gray.800">
              Productos por registrar
            </Text>
            <Text fontSize="sm" fontWeight="400" color="gray.500">
              Estos ítems de la cotización no tienen un producto asociado en el inventario.
              Completa los datos para crearlos y continuar con la conversión a venta.
            </Text>
          </VStack>
        </ModalHeader>
        <ModalCloseButton isDisabled={saving} />

        <ModalBody pb={4}>
          {loadingCatalogos ? (
            <Box textAlign="center" py={10}>
              <Spinner size="lg" color="blue.400" />
              <Text mt={3} color="gray.500" fontSize="sm">
                Cargando catálogos...
              </Text>
            </Box>
          ) : (
            <VStack spacing={4}>
              {productos.length > 1 && (
                <Alert status="info" borderRadius="md" fontSize="sm">
                  <AlertIcon />
                  {productos.length} productos por registrar
                </Alert>
              )}
              {productos.map((prod, idx) => (
                <ProductoForm
                  key={prod.detalle_id}
                  producto={prod}
                  index={idx}
                  moneda={moneda}
                  onChange={handleProductoChange}
                  categorias={categorias}
                  almacenes={almacenes}
                />
              ))}
            </VStack>
          )}
        </ModalBody>

        <Divider />

        <ModalFooter>
          <HStack spacing={3}>
            <Button
              variant="ghost"
              onClick={onClose}
              isDisabled={saving}
              size="sm"
            >
              Cancelar
            </Button>
            <Button
              colorScheme="blue"
              leftIcon={saving ? <Spinner size="xs" /> : <FaSave />}
              onClick={handleGuardar}
              isLoading={saving}
              loadingText="Creando productos..."
              size="sm"
            >
              Crear productos y convertir
            </Button>
          </HStack>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default CrearProductosCotizacionModal;
