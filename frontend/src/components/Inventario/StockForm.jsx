import React, { useState, useEffect } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Button,
  FormControl,
  FormLabel,
  Input,
  Select,
  useToast,
} from '@chakra-ui/react';
import { api } from '../../api.jsx';
import { useAuth } from '../context/AuthContext';

const StockForm = ({ isOpen, onClose, stock, almacenes = [], onSuccess }) => {
  const { user } = useAuth();
  const [formData, setFormData] = useState({
    producto: '',
    almacen: '',
    cantidad: '',
  });
  const [productos, setProductos] = useState([]);
  const [loading, setLoading] = useState(false);
  const toast = useToast();

  useEffect(() => {
    const fetchProductos = async () => {
      try {
        const response = await api.get('/api/inventario/productos/');
        setProductos(response.data);
      } catch (error) {
        console.error('Error al cargar productos:', error);
        toast({
          title: 'Error',
          description: 'No se pudieron cargar los productos',
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
      }
    };

    fetchProductos();
  }, [toast]);

  useEffect(() => {
    if (stock) {
      setFormData({
        producto: stock.producto,
        almacen: stock.almacen,
        cantidad: stock.cantidad,
      });
    } else {
      setFormData({
        producto: '',
        almacen: '',
        cantidad: '',
      });
    }
  }, [stock]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (stock) {
        await api.put(`/api/inventario/stocks/${stock.id}/`, formData);
        toast({
          title: 'Éxito',
          description: 'Stock actualizado correctamente',
          status: 'success',
          duration: 2000,
          isClosable: true,
        });
      } else {
        await api.post('/api/inventario/stocks/', formData);
        toast({
          title: 'Éxito',
          description: 'Stock creado correctamente',
          status: 'success',
          duration: 2000,
          isClosable: true,
        });
      }
      onSuccess();
      onClose();
    } catch (error) {
      console.error('Error al guardar stock:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.message || 'Error al guardar el stock',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>{stock ? 'Editar Stock' : 'Nuevo Stock'}</ModalHeader>
        <ModalCloseButton />
        <form onSubmit={handleSubmit}>
          <ModalBody>
            <FormControl mb={4}>
              <FormLabel>Producto</FormLabel>
              <Select
                name="producto"
                value={formData.producto}
                onChange={handleChange}
                placeholder="Seleccione un producto"
              >
                {Array.isArray(productos) && productos.map(producto => (
                  <option key={producto.id} value={producto.id}>
                    {producto.nombre}
                  </option>
                ))}
              </Select>
            </FormControl>

            <FormControl mb={4}>
              <FormLabel>Almacén</FormLabel>
              <Select
                name="almacen"
                value={formData.almacen}
                onChange={handleChange}
                placeholder="Seleccione un almacén"
              >
                {Array.isArray(almacenes) && almacenes.map(almacen => (
                  <option key={almacen.id} value={almacen.id}>
                    {almacen.nombre}
                  </option>
                ))}
              </Select>
            </FormControl>

            <FormControl mb={4}>
              <FormLabel>Cantidad</FormLabel>
              <Input
                name="cantidad"
                type="number"
                value={formData.cantidad}
                onChange={handleChange}
              />
            </FormControl>
          </ModalBody>

          <ModalFooter>
            <Button colorScheme="blue" mr={3} type="submit" isLoading={loading}>
              {stock ? 'Actualizar' : 'Crear'}
            </Button>
            <Button variant="ghost" onClick={onClose}>Cancelar</Button>
          </ModalFooter>
        </form>
      </ModalContent>
    </Modal>
  );
};

export default StockForm;