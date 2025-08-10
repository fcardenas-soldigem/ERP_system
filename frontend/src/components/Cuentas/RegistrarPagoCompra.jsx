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
  FormErrorMessage,
  InputGroup,
  InputLeftElement,
  Card,
  CardBody,
  Heading,
  HStack,
  Badge,
  Spinner,
  Flex
} from '@chakra-ui/react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { cuentasService } from '../../services/cuentas.service';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

const RegistrarPagoCompra = () => {
  const { compraId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();

  const [formData, setFormData] = useState({
    fecha: format(new Date(), 'yyyy-MM-dd'),
    monto: '',
    moneda_pago: 'PEN', // Nueva campo para moneda del pago
    metodo_pago: 'efectivo',
    referencia: '',
    notas: '',
    comprobante: null
  });

  const [tipoCambio, setTipoCambio] = useState(3.8);

  // Debug: Verificar que el ID está llegando
  console.log('ID de la cuenta por pagar:', compraId);

  // Obtener detalles de la cuenta por pagar (compra a crédito)
  const { data: cuenta, isLoading, error: queryError } = useQuery({
    queryKey: ['cuenta-por-pagar-detalle', compraId],
    queryFn: () => cuentasService.getCuentaPorPagarDetalle(compraId),
    onError: (err) => {
      console.error('Error al cargar cuenta por pagar:', err);
    }
  });

  // Obtener pagos existentes usando el servicio de cuentas
  const { data: pagosData } = useQuery({
    queryKey: ['pagos-compra', compraId],
    queryFn: () => cuentasService.getPagosCompra(compraId),
    enabled: !!compraId
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

  // Debug: Mostrar datos cargados
  console.log('Cuenta cargada:', cuenta);
  console.log('Query Error:', queryError);

  // Calcular saldo pendiente
  const pagos = Array.isArray(pagosData) ? pagosData : [];
  const totalPagado = pagos.reduce((sum, pago) => sum + parseFloat(pago.monto || 0), 0);
  const saldoPendiente = parseFloat(cuenta?.total || 0) - totalPagado;
  const montoMaximo = saldoPendiente;
  const [error, setError] = useState('');

  // Función para formatear moneda
  const formatCurrency = (amount, currency = 'PEN') => {
    const symbol = currency === 'USD' ? '$' : 'S/';
    return `${symbol} ${parseFloat(amount || 0).toFixed(2)}`;
  };

  // Calcular monto convertido
  const calcularMontoConvertido = () => {
    if (!formData.monto || !cuenta) return 0;
    
    const montoOriginal = parseFloat(formData.monto);
    const monedaCompra = cuenta.moneda;
    const monedaPago = formData.moneda_pago;
    
    if (monedaCompra === monedaPago) {
      return montoOriginal; // Sin conversión
    }
    
    if (monedaCompra === 'USD' && monedaPago === 'PEN') {
      return montoOriginal * tipoCambio; // USD a PEN
    }
    
    if (monedaCompra === 'PEN' && monedaPago === 'USD') {
      return montoOriginal / tipoCambio; // PEN a USD
    }
    
    return montoOriginal;
  };

  // Verificar si la cuenta ya está pagada
  useEffect(() => {
    if (cuenta && saldoPendiente <= 0) {
      toast({
        title: 'Cuenta pagada',
        description: 'Esta compra ya está completamente pagada',
        status: 'info',
        duration: 5000,
        isClosable: true
      });
      navigate('/cuentas/por-pagar');
    }
  }, [cuenta, saldoPendiente, navigate, toast]);

  // Mutation para registrar el pago desde cuentas por pagar
  const registrarPagoMutation = useMutation({
    mutationFn: (data) => cuentasService.registrarPagoCuentaPorPagar(compraId, data),
    onSuccess: (result) => {
      queryClient.invalidateQueries(['cuenta-por-pagar-detalle', compraId]);
      queryClient.invalidateQueries(['cuentas-por-pagar']);
      queryClient.invalidateQueries(['compras']);
      
      const mensaje = result.compra_completamente_pagada 
        ? 'Pago registrado. La compra ha sido marcada como pagada.'
        : `Pago registrado. Saldo restante: ${formatCurrency(result.saldo_restante, cuenta?.moneda)}`;
      
      toast({
        title: 'Pago registrado exitosamente',
        description: mensaje,
        status: 'success',
        duration: 5000,
        isClosable: true
      });
      navigate('/cuentas/por-pagar');
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

    // Validar que la fecha no sea anterior a la fecha de emisión de la compra
    const fechaPago = new Date(formData.fecha);
    const fechaEmision = new Date(cuenta.fecha_emision);
    if (fechaPago < fechaEmision) {
      setError('La fecha del pago no puede ser anterior a la fecha de emisión de la compra');
      return;
    }

    const data = {
      ...formData,
      monto: montoNumerico,
      moneda: formData.moneda_pago, // Enviar la moneda del pago al backend
      compra: compraId,
      fecha: formData.fecha // Ya está en formato YYYY-MM-DD
    };
    delete data.moneda_pago; // Eliminar el campo temporal

    console.log('Datos del pago a enviar desde cuentas por pagar:', data);
    console.log('ID de la cuenta por pagar:', compraId);
    console.log('Saldo pendiente:', montoMaximo);
    
    registrarPagoMutation.mutate(data);
  };

  if (isLoading) {
    return (
      <Flex justify="center" align="center" minH="400px">
        <VStack spacing={4}>
          <Spinner size="xl" />
          <Text>Cargando cuenta por pagar #{compraId}...</Text>
        </VStack>
      </Flex>
    );
  }

  if (queryError) {
    return (
      <Box p={5}>
        <Text color="red.500" mb={4}>Error al cargar la cuenta por pagar: {queryError.message}</Text>
        <Text mb={4}>ID solicitado: {compraId}</Text>
        <Button mt={4} onClick={() => navigate('/cuentas/por-pagar')}>
          Volver al listado
        </Button>
      </Box>
    );
  }

  if (!cuenta) {
    return (
      <Box p={5}>
        <Text mb={2}>No se encontró la cuenta por pagar con ID: {compraId}</Text>
        <Text mb={4} fontSize="sm" color="gray.600">
          Esto puede ocurrir si la compra no es a crédito o ya está completamente pagada.
        </Text>
        <Button mt={4} onClick={() => navigate('/cuentas/por-pagar')}>
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
                <Text fontSize="sm" color="gray.600">Compra N°</Text>
                <Text fontSize="lg" fontWeight="bold">{cuenta?.numero}</Text>
              </Box>
              <Box>
                <Text fontSize="sm" color="gray.600">Proveedor</Text>
                <Text fontSize="lg">{cuenta?.proveedor?.razon_social}</Text>
              </Box>
              <Box>
                <Text fontSize="sm" color="gray.600">Plazo Crédito</Text>
                <Text fontSize="lg">
                  {cuenta?.tipo_compra === 'credito_30' ? '30' : '60'} días
                </Text>
              </Box>
              <Box>
                <Text fontSize="sm" color="gray.600">Total Compra</Text>
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
                <FormLabel>Fecha</FormLabel>
                <Input
                  type="date"
                  name="fecha"
                  value={formData.fecha}
                  onChange={handleInputChange}
                />
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Moneda del Pago</FormLabel>
                <Select
                  name="moneda_pago"
                  value={formData.moneda_pago}
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    moneda_pago: e.target.value,
                    monto: '' // Limpiar monto al cambiar moneda
                  }))}
                >
                  <option value="PEN">Soles (S/)</option>
                  <option value="USD">Dólares ($)</option>
                </Select>
                <Text fontSize="xs" color="gray.500" mt={1}>
                  Compra en: {formatCurrency(cuenta?.total, cuenta?.moneda)} | 
                  Tipo de cambio: S/ {tipoCambio}
                </Text>
              </FormControl>

              <FormControl isRequired isInvalid={!!error}>
                <FormLabel>
                  Monto ({formData.moneda_pago === 'USD' ? 'Dólares' : 'Soles'})
                </FormLabel>
                <InputGroup>
                  <InputLeftElement pointerEvents="none" color="gray.300">
                    {formData.moneda_pago === 'USD' ? '$' : 'S/'}
                  </InputLeftElement>
                  <Input
                    type="number"
                    name="monto"
                    value={formData.monto}
                    onChange={handleInputChange}
                    placeholder={`Ingrese monto en ${formData.moneda_pago}`}
                    step="0.01"
                    min="0"
                  />
                </InputGroup>
                <VStack align="start" spacing={1} mt={2}>
                  {formData.monto && cuenta && formData.moneda_pago !== cuenta.moneda && (
                    <Text fontSize="sm" color="blue.600">
                      Equivale a: {formatCurrency(calcularMontoConvertido(), cuenta.moneda)} en la moneda de la compra
                    </Text>
                  )}
                  <Text fontSize="sm" color="gray.600">
                    Saldo pendiente: {formatCurrency(montoMaximo, cuenta?.moneda)}
                  </Text>
                </VStack>
                {error && <FormErrorMessage>{error}</FormErrorMessage>}
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
                  <option value="tarjeta">Tarjeta</option>
                  <option value="cheque">Cheque</option>
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
                <Text fontSize="xs" color="gray.500">
                  Formatos permitidos: PDF, JPG, PNG. Tamaño máximo: 5MB
                </Text>
              </FormControl>

              <HStack spacing={4} justify="flex-end">
                <Button
                  variant="outline"
                  onClick={() => navigate('/cuentas/por-pagar')}
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

export default RegistrarPagoCompra; 