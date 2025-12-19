import React, { useState } from 'react';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Input,
  VStack,
  NumberInput,
  NumberInputField,
  Select,
  useToast,
  Card,
  CardBody,
  Heading,
  Text,
  FormHelperText,
  HStack
} from '@chakra-ui/react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { comprasService } from '../../services/compras.service';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { METODOS_PAGO, METODOS_PAGO_DISPLAY } from './constants';

const CompraPagoForm = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();

  const [formData, setFormData] = useState({
    fecha: new Date().toISOString().split('T')[0],
    monto: '',
    metodo_pago: METODOS_PAGO.EFECTIVO,
    moneda_pago: 'PEN', // Nueva campo para moneda del pago
    referencia: '',
    notas: '',
    comprobante: null
  });

  const [tipoCambio, setTipoCambio] = useState(3.8);

  const { data: compra } = useQuery({
    queryKey: ['compra', id],
    queryFn: () => comprasService.getCompra(id)
  });

  const { data: saldoPendiente } = useQuery({
    queryKey: ['saldo-pendiente-compra', id],
    queryFn: () => comprasService.getSaldoPendiente(id)
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

  const crearPagoMutation = useMutation({
    mutationFn: (pagoData) => comprasService.crearPagoCompra(id, pagoData),
    onSuccess: () => {
      queryClient.invalidateQueries(['pagos-compra', id]);
      queryClient.invalidateQueries(['saldo-pendiente-compra', id]);
      queryClient.invalidateQueries(['compra', id]);
      toast({
        title: 'Pago registrado',
        description: 'El pago se ha registrado correctamente',
        status: 'success',
        duration: 3000
      });
      navigate(`/app/compras/${id}/pagos`);
    },
    onError: (error) => {
      toast({
        title: 'Error',
        description: error.message || 'Error al registrar el pago',
        status: 'error',
        duration: 3000
      });
    }
  });

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.monto || formData.monto <= 0) {
      toast({
        title: 'Error',
        description: 'El monto debe ser mayor a 0',
        status: 'error',
        duration: 3000
      });
      return;
    }

    if (parseFloat(formData.monto) > saldoPendiente) {
      toast({
        title: 'Error',
        description: 'El monto no puede ser mayor al saldo pendiente',
        status: 'error',
        duration: 3000
      });
      return;
    }

    try {
      // Preparar datos del pago incluyendo la moneda
      const pagoData = {
        ...formData,
        moneda: formData.moneda_pago // Enviar la moneda del pago al backend
      };
      delete pagoData.moneda_pago; // Eliminar el campo temporal
      
      await crearPagoMutation.mutateAsync(pagoData);
    } catch (error) {
      console.error('Error al crear pago:', error);
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const maxSize = 5 * 1024 * 1024; // 5MB
    const allowedTypes = ['image/jpeg', 'image/png', 'application/pdf'];

    if (file.size > maxSize) {
      toast({
        title: 'Error',
        description: 'El archivo es demasiado grande. Máximo 5MB.',
        status: 'error',
        duration: 3000
      });
      e.target.value = '';
      return;
    }

    if (!allowedTypes.includes(file.type)) {
      toast({
        title: 'Error',
        description: 'Tipo de archivo no permitido. Use PDF, JPG o PNG.',
        status: 'error',
        duration: 3000
      });
      e.target.value = '';
      return;
    }

    setFormData(prev => ({
      ...prev,
      comprobante: file
    }));
  };

  const formatCurrency = (amount, moneda = 'PEN') => {
    const symbol = moneda === 'USD' ? '$' : 'S/';
    return `${symbol} ${parseFloat(amount || 0).toFixed(2)}`;
  };

  // Calcular monto convertido
  const calcularMontoConvertido = () => {
    if (!formData.monto || !compra) return 0;
    
    const montoOriginal = parseFloat(formData.monto);
    const monedaCompra = compra.moneda;
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

  return (
    <Box p={4}>
      <Card>
        <CardBody>
          <VStack spacing={6} align="stretch">
            <Heading size="md">Registrar Nuevo Pago</Heading>
            
            {compra && (
              <Box>
                <Text><strong>Compra #:</strong> {compra.numero}</Text>
                <Text><strong>Proveedor:</strong> {compra.proveedor_nombre}</Text>
                <Text><strong>Total:</strong> {formatCurrency(compra.total, compra.moneda)}</Text>
                <Text><strong>Saldo Pendiente:</strong> {formatCurrency(saldoPendiente, compra.moneda)}</Text>
              </Box>
            )}

            <form onSubmit={handleSubmit}>
              <VStack spacing={4}>
                <FormControl isRequired>
                  <FormLabel>Fecha</FormLabel>
                  <Input
                    type="date"
                    value={formData.fecha}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      fecha: e.target.value
                    }))}
                  />
                </FormControl>

                <FormControl isRequired>
                  <FormLabel>Moneda del Pago</FormLabel>
                  <Select
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
                  <FormHelperText>
                    Compra en: {formatCurrency(compra?.total, compra?.moneda)} | 
                    Tipo de cambio: S/ {tipoCambio}
                  </FormHelperText>
                </FormControl>

                <FormControl isRequired>
                  <FormLabel>
                    Monto ({formData.moneda_pago === 'USD' ? 'Dólares' : 'Soles'})
                  </FormLabel>
                  <NumberInput
                    min={0}
                    value={formData.monto}
                    onChange={(value) => setFormData(prev => ({
                      ...prev,
                      monto: value
                    }))}
                  >
                    <NumberInputField placeholder={`Ingrese monto en ${formData.moneda_pago}`} />
                  </NumberInput>
                  <FormHelperText>
                    {formData.monto && compra && formData.moneda_pago !== compra.moneda && (
                      <Text color="blue.600">
                        Equivale a: {formatCurrency(calcularMontoConvertido(), compra.moneda)} en la moneda de la compra
                      </Text>
                    )}
                    <Text>
                      Saldo pendiente: {formatCurrency(saldoPendiente, compra?.moneda)}
                    </Text>
                  </FormHelperText>
                </FormControl>

                <FormControl isRequired>
                  <FormLabel>Método de Pago</FormLabel>
                  <Select
                    value={formData.metodo_pago}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      metodo_pago: e.target.value
                    }))}
                  >
                    <option value={METODOS_PAGO.EFECTIVO}>{METODOS_PAGO_DISPLAY[METODOS_PAGO.EFECTIVO]}</option>
                    <option value={METODOS_PAGO.TRANSFERENCIA}>{METODOS_PAGO_DISPLAY[METODOS_PAGO.TRANSFERENCIA]}</option>
                    <option value={METODOS_PAGO.CHEQUE}>{METODOS_PAGO_DISPLAY[METODOS_PAGO.CHEQUE]}</option>
                    <option value={METODOS_PAGO.TARJETA}>{METODOS_PAGO_DISPLAY[METODOS_PAGO.TARJETA]}</option>
                  </Select>
                </FormControl>

                <FormControl>
                  <FormLabel>Referencia</FormLabel>
                  <Input
                    placeholder="Número de operación, cheque, etc."
                    value={formData.referencia}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      referencia: e.target.value
                    }))}
                  />
                </FormControl>

                <FormControl>
                  <FormLabel>Notas</FormLabel>
                  <Input
                    placeholder="Notas adicionales"
                    value={formData.notas}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      notas: e.target.value
                    }))}
                  />
                </FormControl>

                <FormControl>
                  <FormLabel>Comprobante</FormLabel>
                  <Input
                    type="file"
                    onChange={handleFileChange}
                    accept=".pdf,.jpg,.jpeg,.png"
                  />
                  <FormHelperText>
                    Formatos permitidos: PDF, JPG, PNG. Tamaño máximo: 5MB
                  </FormHelperText>
                </FormControl>

                <HStack justify="flex-end" spacing={4} pt={4}>
                  <Button onClick={() => navigate(`/app/compras/${id}/pagos`)}>
                    Cancelar
                  </Button>
                  <Button
                    type="submit"
                    colorScheme="blue"
                    isLoading={crearPagoMutation.isLoading}
                  >
                    Registrar Pago
                  </Button>
                </HStack>
              </VStack>
            </form>
          </VStack>
        </CardBody>
      </Card>
    </Box>
  );
};

export default CompraPagoForm; 