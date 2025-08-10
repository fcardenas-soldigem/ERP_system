import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Input,
  VStack,
  useToast,
  Select,
  Textarea,
  Text,
  InputGroup,
  InputLeftElement,
  Card,
  CardBody,
  Heading,
  HStack,
  Spinner,
  Flex
} from '@chakra-ui/react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { cuentasService } from '../../services/cuentas.service';
import { format } from 'date-fns';

const RegistrarPagoVenta = () => {
  const { ventaId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();

  const [formData, setFormData] = useState({
    fecha: format(new Date(), 'yyyy-MM-dd'),
    monto: '',
    moneda_pago: 'PEN',
    metodo_pago: 'efectivo',
    referencia: '',
    notas: '',
    comprobante: null
  });

  const [tipoCambio, setTipoCambio] = useState(3.8);
  const [error, setError] = useState('');

  // Obtener detalles de la cuenta por cobrar
  const { data: cuenta, isLoading, error: queryError } = useQuery({
    queryKey: ['cuenta-por-cobrar-detalle', ventaId],
    queryFn: () => cuentasService.getCuentaPorCobrarDetalle(ventaId),
    onError: (err) => {
      console.error('Error al cargar cuenta por cobrar:', err);
    }
  });

  // Obtener tipo de cambio
  const { data: tipoCambioData } = useQuery({
    queryKey: ['tipo-cambio'],
    queryFn: async () => {
      try {
        const response = await fetch('/api/core/tipo-cambio/');
        const data = await response.json();
        return data.tipo_cambio_venta || 3.8;
      } catch {
        return 3.8;
      }
    },
    onSuccess: (data) => {
      setTipoCambio(data);
    }
  });

  const saldoPendiente = cuenta?.saldo_pendiente || 0;
  const montoMaximo = saldoPendiente;

  // Función para formatear moneda
  const formatCurrency = (amount, currency = 'PEN') => {
    const symbol = currency === 'USD' ? '$' : 'S/';
    return `${symbol} ${parseFloat(amount || 0).toFixed(2)}`;
  };

  // Verificar si la cuenta ya está pagada
  useEffect(() => {
    if (cuenta && saldoPendiente <= 0.01) {
      toast({
        title: 'Cuenta pagada',
        description: 'Esta venta ya está completamente pagada',
        status: 'info',
        duration: 5000,
        isClosable: true
      });
      navigate('/cuentas/por-cobrar');
    }
  }, [cuenta, saldoPendiente, navigate, toast]);

  // Mutation para registrar el pago
  const registrarPagoMutation = useMutation({
    mutationFn: (data) => cuentasService.registrarPagoCuentaPorCobrar(ventaId, data),
    onSuccess: (result) => {
      queryClient.invalidateQueries(['cuenta-por-cobrar-detalle', ventaId]);
      queryClient.invalidateQueries(['cuentas-por-cobrar']);
      queryClient.invalidateQueries(['ventas']);
      
      const mensaje = result.venta_completamente_pagada 
        ? 'Pago registrado. La venta ha sido marcada como pagada.'
        : `Pago registrado. Saldo restante: ${formatCurrency(result.saldo_restante, cuenta?.moneda)}`;
      
      toast({
        title: 'Pago registrado exitosamente',
        description: mensaje,
        status: 'success',
        duration: 5000,
        isClosable: true
      });
      navigate('/cuentas/por-cobrar');
    },
    onError: (error) => {
      toast({
        title: 'Error al registrar el pago',
        description: error.message || 'Ocurrió un error al registrar el pago',
        status: 'error',
        duration: 5000,
        isClosable: true
      });
    }
  });

  const handleInputChange = (e) => {
    const { name, value, files } = e.target;
    
    if (name === 'comprobante' && files) {
      setFormData(prev => ({
        ...prev,
        [name]: files[0]
      }));
    } else if (name === 'monto') {
      const montoNumerico = parseFloat(value);
      if (!isNaN(montoNumerico)) {
        if (montoNumerico > montoMaximo) {
          setError(`El monto no puede ser mayor a ${formatCurrency(montoMaximo, cuenta?.moneda)}`);
        } else {
          setError('');
        }
      }
      setFormData(prev => ({
        ...prev,
        [name]: value
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: value
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const montoNumerico = parseFloat(formData.monto);
    if (isNaN(montoNumerico) || montoNumerico <= 0) {
      setError('El monto debe ser un número válido mayor a 0');
      return;
    }

    if (montoNumerico > montoMaximo) {
      setError(`El monto no puede ser mayor a ${formatCurrency(montoMaximo, cuenta?.moneda)}`);
      return;
    }

    const data = {
      ...formData,
      monto: montoNumerico,
      moneda: formData.moneda_pago,
      venta: ventaId,
      fecha: formData.fecha
    };
    delete data.moneda_pago;

    registrarPagoMutation.mutate(data);
  };

  if (isLoading) {
    return (
      <Flex justify="center" align="center" minH="400px">
        <VStack spacing={4}>
          <Spinner size="xl" />
          <Text>Cargando cuenta por cobrar #{ventaId}...</Text>
        </VStack>
      </Flex>
    );
  }

  if (queryError) {
    return (
      <Box p={5}>
        <Text color="red.500" mb={4}>Error al cargar la cuenta por cobrar: {queryError.message}</Text>
        <Button mt={4} onClick={() => navigate('/cuentas/por-cobrar')}>
          Volver al listado
        </Button>
      </Box>
    );
  }

  if (!cuenta) {
    return (
      <Box p={5}>
        <Text mb={2}>No se encontró la cuenta por cobrar</Text>
        <Button mt={4} onClick={() => navigate('/cuentas/por-cobrar')}>
          Volver al listado
        </Button>
      </Box>
    );
  }

  return (
    <Box p={5}>
      <Card mb={5}>
        <CardBody>
          <VStack align="stretch" spacing={4}>
            <Heading size="md">Registrar Nuevo Pago</Heading>
            
            <HStack justify="space-between">
              <Box>
                <Text fontSize="sm" color="gray.600">Venta N°</Text>
                <Text fontSize="lg" fontWeight="bold">{cuenta?.numero}</Text>
              </Box>
              <Box>
                <Text fontSize="sm" color="gray.600">Cliente</Text>
                <Text fontSize="lg">{cuenta?.cliente?.nombre}</Text>
              </Box>
              <Box>
                <Text fontSize="sm" color="gray.600">Total Venta</Text>
                <Text fontSize="lg">{formatCurrency(cuenta?.total, cuenta?.moneda)}</Text>
              </Box>
              <Box>
                <Text fontSize="sm" color="gray.600">Saldo Pendiente</Text>
                <Text fontSize="lg" color="red.500" fontWeight="bold">
                  {formatCurrency(montoMaximo, cuenta?.moneda)}
                </Text>
              </Box>
            </HStack>
          </VStack>
        </CardBody>
      </Card>

      <Card>
        <CardBody>
          <form onSubmit={handleSubmit}>
            <VStack spacing={4} align="stretch">
              <FormControl isRequired>
                <FormLabel>Fecha del Pago</FormLabel>
                <Input
                  type="date"
                  name="fecha"
                  value={formData.fecha}
                  onChange={handleInputChange}
                />
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Monto del Pago</FormLabel>
                <InputGroup>
                  <InputLeftElement 
                    pointerEvents="none"
                    children={formData.moneda_pago === 'USD' ? '$' : 'S/'}
                  />
                  <Input
                    type="number"
                    step="0.01"
                    name="monto"
                    value={formData.monto}
                    onChange={handleInputChange}
                    placeholder="0.00"
                    max={montoMaximo}
                  />
                </InputGroup>
                <Text fontSize="xs" color="gray.500">
                  Monto máximo: {formatCurrency(montoMaximo, cuenta?.moneda)}
                </Text>
                {error && (
                  <Text color="red.500" fontSize="sm" mt={1}>
                    {error}
                  </Text>
                )}
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Moneda del Pago</FormLabel>
                <Select
                  name="moneda_pago"
                  value={formData.moneda_pago}
                  onChange={handleInputChange}
                >
                  <option value="PEN">Sol Peruano (S/)</option>
                  <option value="USD">Dólar Americano ($)</option>
                </Select>
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Método de Pago</FormLabel>
                <Select
                  name="metodo_pago"
                  value={formData.metodo_pago}
                  onChange={handleInputChange}
                >
                  <option value="efectivo">Efectivo</option>
                  <option value="transferencia">Transferencia</option>
                  <option value="cheque">Cheque</option>
                  <option value="tarjeta">Tarjeta</option>
                </Select>
              </FormControl>

              <FormControl>
                <FormLabel>Referencia</FormLabel>
                <Input
                  name="referencia"
                  value={formData.referencia}
                  onChange={handleInputChange}
                  placeholder="Número de operación, cheque, etc."
                />
              </FormControl>

              <FormControl>
                <FormLabel>Notas</FormLabel>
                <Textarea
                  name="notas"
                  value={formData.notas}
                  onChange={handleInputChange}
                  placeholder="Notas adicionales..."
                />
              </FormControl>

              <FormControl>
                <FormLabel>Comprobante</FormLabel>
                <Input
                  type="file"
                  name="comprobante"
                  onChange={handleInputChange}
                  accept=".pdf,.jpg,.jpeg,.png"
                />
              </FormControl>

              <HStack spacing={4} justify="flex-end">
                <Button
                  variant="outline"
                  onClick={() => navigate('/cuentas/por-cobrar')}
                >
                  Cancelar
                </Button>
                <Button
                  colorScheme="blue"
                  type="submit"
                  isLoading={registrarPagoMutation.isLoading}
                >
                  Registrar Pago
                </Button>
              </HStack>
            </VStack>
          </form>
        </CardBody>
      </Card>
    </Box>
  );
};

export default RegistrarPagoVenta; 