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

const VentaPagoForm = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();

  const [formData, setFormData] = useState({
    fecha: format(new Date(), 'yyyy-MM-dd'),
    monto: '',
    metodo_pago: 'efectivo',
    referencia: '',
    notas: '',
    comprobante: null
  });



  // Obtener detalles de la cuenta por cobrar (venta a crédito)
  const { data: cuenta, isLoading, error: queryError } = useQuery({
    queryKey: ['cuenta-por-cobrar-detalle', id],
    queryFn: () => cuentasService.getCuentaPorCobrarDetalle(id),
    onError: (err) => {
      console.error('Error al cargar cuenta por cobrar:', err);
    }
  });



  // El saldo pendiente ya viene calculado del servicio
  const montoMaximo = cuenta?.saldo_pendiente || 0;
  const [error, setError] = useState('');
  const [toastShown, setToastShown] = useState(false);

  // Verificar si la cuenta ya está pagada
  useEffect(() => {
    if (cuenta && cuenta.saldo_pendiente !== undefined && !toastShown && cuenta.saldo_pendiente <= 0.01) {
      setToastShown(true);
      toast({
        title: 'Cuenta pagada',
        description: 'Esta cuenta ya está completamente pagada',
        status: 'info',
        duration: 5000,
        isClosable: true
      });
      navigate('/app/cuentas/por-cobrar');
    }
  }, [cuenta, navigate, toast, toastShown]);

  // Mutation para registrar el pago desde cuentas por cobrar
  const registrarPagoMutation = useMutation({
    mutationFn: (data) => cuentasService.registrarPagoCuentaPorCobrar(id, data),
    onSuccess: (result) => {
      queryClient.invalidateQueries(['cuenta-por-cobrar-detalle', id]);
      queryClient.invalidateQueries(['cuentas-por-cobrar']);
      queryClient.invalidateQueries(['ventas']);
      
      const mensaje = result.venta_completamente_pagada 
        ? 'Pago registrado. La venta ha sido marcada como pagada.'
        : `Pago registrado. Saldo restante: ${cuentasService.formatCurrency(result.saldo_restante, cuenta?.moneda)}`;
      
      toast({
        title: 'Pago registrado exitosamente',
        description: mensaje,
        status: 'success',
        duration: 5000,
        isClosable: true
      });
      navigate('/app/cuentas/por-cobrar');
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
      setError(`El monto no puede ser mayor a ${cuentasService.formatCurrency(montoMaximo, cuenta?.moneda)}`);
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
      setError(`El monto no puede ser mayor a ${cuentasService.formatCurrency(montoMaximo, cuenta?.moneda)}`);
      return;
    }

    // Validar que la fecha no sea anterior a la fecha de emisión de la venta
    const fechaPago = new Date(formData.fecha);
    const fechaEmision = new Date(cuenta.fecha_emision);
    if (fechaPago < fechaEmision) {
      setError('La fecha del pago no puede ser anterior a la fecha de emisión de la venta');
      return;
    }

    const data = {
      ...formData,
      monto: montoNumerico,
      venta: id,
      fecha: formData.fecha // Ya está en formato YYYY-MM-DD
    };


    
    registrarPagoMutation.mutate(data);
  };

  if (isLoading) {
    return (
      <Flex justify="center" align="center" minH="400px">
        <VStack spacing={4}>
          <Spinner size="xl" />
          <Text>Cargando cuenta por cobrar #{id}...</Text>
        </VStack>
      </Flex>
    );
  }

  if (queryError) {
    return (
      <Box p={5}>
        <Text color="red.500" mb={4}>Error al cargar la cuenta por cobrar: {queryError.message}</Text>
        <Text mb={4}>ID solicitado: {id}</Text>
        <Button mt={4} onClick={() => navigate('/app/cuentas/por-cobrar')}>
          Volver al listado
        </Button>
      </Box>
    );
  }

  if (!cuenta) {
    return (
      <Box p={5}>
        <Text mb={2}>No se encontró la cuenta por cobrar con ID: {id}</Text>
        <Text mb={4} fontSize="sm" color="gray.600">
          Esto puede ocurrir si la venta no es a crédito o ya está completamente pagada.
        </Text>
        <Button mt={4} onClick={() => navigate('/app/cuentas/por-cobrar')}>
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
                <Text fontSize="sm" color="gray.600">Plazo Crédito</Text>
                <Text fontSize="lg">{cuenta?.plazo_credito} días</Text>
              </Box>
              <Box>
                <Text fontSize="sm" color="gray.600">Total Venta</Text>
                <Text fontSize="lg">{cuentasService.formatCurrency(cuenta?.total, cuenta?.moneda)}</Text>
              </Box>
              <Box>
                <Text fontSize="sm" color="gray.600">Saldo Pendiente</Text>
                <Text fontSize="lg" color="red.500" fontWeight="bold">
                  {cuentasService.formatCurrency(montoMaximo, cuenta?.moneda)}
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

              <FormControl isRequired isInvalid={!!error}>
                <FormLabel>Monto</FormLabel>
                <InputGroup>
                  <InputLeftElement pointerEvents="none" color="gray.300">
                    {cuenta?.moneda === 'USD' ? '$' : 'S/'}
                  </InputLeftElement>
                  <Input
                    type="number"
                    name="monto"
                    value={formData.monto}
                    onChange={handleInputChange}
                    placeholder="0.00"
                    step="0.01"
                    min="0"
                    max={montoMaximo}
                  />
                </InputGroup>
                <Text fontSize="sm" color="gray.600">
                  Monto máximo: {cuentasService.formatCurrency(montoMaximo, cuenta?.moneda)}
                </Text>
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
                  onClick={() => navigate('/app/cuentas/por-cobrar')}
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

export default VentaPagoForm; 