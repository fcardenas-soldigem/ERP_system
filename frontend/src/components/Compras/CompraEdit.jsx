import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Select,
  Spinner,
  Text,
  VStack,
  useToast,
  Card,
  CardBody,
  Heading,
  Input,
  FormHelperText,
  Badge,
  HStack,
  Divider,
  Flex
} from '@chakra-ui/react';
import { comprasService } from '../../services/compras.service';
import { format, addDays } from 'date-fns';
import { es } from 'date-fns/locale';
import { ESTADOS_COMPRA, METODOS_PAGO, ESTADOS_DISPLAY, METODOS_PAGO_DISPLAY } from './constants';

const CompraEdit = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [compra, setCompra] = useState(null);
  const [estado, setEstado] = useState('');
  const [metodoPago, setMetodoPago] = useState('');
  const [fechaVencimiento, setFechaVencimiento] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const fetchCompra = async () => {
      try {
        console.log('Obteniendo datos de la compra:', id);
        const data = await comprasService.getCompra(id);
        console.log('Datos de compra recibidos:', data);
        
        setCompra(data);
        setEstado(data.estado);
        setMetodoPago(data.metodo_pago);
        setFechaVencimiento(data.fecha_vencimiento);
      } catch (error) {
        console.error('Error al cargar la compra:', error);
        toast({
          title: 'Error',
          description: 'No se pudo cargar la información de la compra',
          status: 'error',
          duration: 3000,
        });
      } finally {
        setIsLoading(false);
      }
    };
    fetchCompra();
  }, [id, toast]);

  const handleMetodoPagoChange = (e) => {
    const nuevoMetodoPago = e.target.value;
    let nuevaFechaVencimiento = null;
    let nuevoEstado = estado;

    if (nuevoMetodoPago === METODOS_PAGO.CREDITO_30) {
      nuevaFechaVencimiento = addDays(new Date(compra.fecha_emision), 30).toISOString().split('T')[0];
      nuevoEstado = 'pendiente';
    } else if (nuevoMetodoPago === METODOS_PAGO.CREDITO_60) {
      nuevaFechaVencimiento = addDays(new Date(compra.fecha_emision), 60).toISOString().split('T')[0];
      nuevoEstado = 'pendiente';
    } else {
      nuevoEstado = 'pagada';
    }

    setMetodoPago(nuevoMetodoPago);
    setFechaVencimiento(nuevaFechaVencimiento);
    setEstado(nuevoEstado);
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      console.log('Actualizando compra:', id);
      await comprasService.updateCompraEstado(id, {
        estado,
        metodo_pago: metodoPago,
        fecha_vencimiento: fechaVencimiento
      });
      
      toast({
        title: 'Compra actualizada',
        description: 'Los cambios se guardaron correctamente',
        status: 'success',
        duration: 2000,
      });
      navigate('/compras');
    } catch (error) {
      console.error('Error al actualizar la compra:', error);
      toast({
        title: 'Error',
        description: 'No se pudo actualizar la compra. Por favor, intente nuevamente.',
        status: 'error',
        duration: 3000,
      });
    } finally {
      setIsSaving(false);
    }
  };

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

  const formatDate = (dateString) => {
    if (!dateString) return '';
    try {
      return format(new Date(dateString), 'dd/MM/yyyy', { locale: es });
    } catch (error) {
      console.error('Error al formatear fecha:', error);
      return dateString;
    }
  };

  if (isLoading) {
    return (
      <Flex justify="center" align="center" minH="200px">
        <Spinner size="xl" />
      </Flex>
    );
  }

  if (!compra) {
    return (
      <Box p={4}>
        <Text>No se encontró la compra solicitada.</Text>
        <Button mt={4} onClick={() => navigate('/compras')}>
          Volver a Compras
        </Button>
      </Box>
    );
  }

  return (
    <Box p={4}>
      <Card>
        <CardBody>
          <VStack spacing={6} align="stretch">
            <Heading size="md">Editar Compra</Heading>

            <Box>
              <Text><strong>Número:</strong> {compra.numero}</Text>
              <Text><strong>Proveedor:</strong> {compra.proveedor_nombre}</Text>
              <Text><strong>Fecha de Emisión:</strong> {formatDate(compra.fecha_emision)}</Text>
              <Text><strong>Total:</strong> {formatCurrency(compra.total, compra.moneda)}</Text>
            </Box>

            <Divider />

            <FormControl>
              <FormLabel>Estado</FormLabel>
              <Select
                value={estado}
                onChange={(e) => setEstado(e.target.value)}
                isDisabled={metodoPago.startsWith('credito_') && estado === 'pendiente'}
              >
                {Object.entries(ESTADOS_DISPLAY).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </Select>
              {metodoPago.startsWith('credito_') && estado === 'pendiente' && (
                <FormHelperText color="orange.500">
                  El estado no se puede cambiar mientras haya un saldo pendiente
                </FormHelperText>
              )}
            </FormControl>

            <FormControl>
              <FormLabel>Método de Pago</FormLabel>
              <Select
                value={metodoPago}
                onChange={handleMetodoPagoChange}
              >
                {Object.entries(METODOS_PAGO_DISPLAY).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </Select>
            </FormControl>

            {metodoPago.startsWith('credito_') && (
              <FormControl>
                <FormLabel>Fecha de Vencimiento</FormLabel>
                <Input
                  type="date"
                  value={fechaVencimiento || ''}
                  isReadOnly
                />
                <FormHelperText>
                  Fecha calculada automáticamente según el plazo de crédito
                </FormHelperText>
              </FormControl>
            )}

            <HStack justify="flex-end" spacing={4} pt={4}>
              <Button onClick={() => navigate('/compras')}>
                Cancelar
              </Button>
              <Button
                colorScheme="blue"
                onClick={handleSave}
                isLoading={isSaving}
              >
                Guardar Cambios
              </Button>
            </HStack>
          </VStack>
        </CardBody>
      </Card>
    </Box>
  );
};

export default CompraEdit; 