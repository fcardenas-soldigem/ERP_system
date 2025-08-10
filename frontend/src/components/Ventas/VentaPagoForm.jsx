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
  Badge
} from '@chakra-ui/react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { cuentasService } from '../../services/cuentas.service';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { ventasService } from '../../services/ventas.service';

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

  // Mutation para registrar el pago
  const registrarPagoMutation = useMutation({
    mutationFn: (data) => cuentasService.registrarPago(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['cuenta-por-cobrar', id]);
      queryClient.invalidateQueries(['cuentas-por-cobrar']);
      queryClient.invalidateQueries(['ventas']);
      queryClient.invalidateQueries(['venta', id]);
      toast({
        title: 'Pago registrado',
        description: 'El pago se ha registrado correctamente',
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

  // Obtener detalles de la venta y sus pagos
  const { data: venta, isLoading } = useQuery({
    queryKey: ['venta', id],
    queryFn: () => ventasService.getVenta(id),
    onSuccess: (data) => {
      if (!data.estado_pago?.startsWith('credito_')) {
        toast({
          title: 'Venta no es a crédito',
          description: 'Esta venta no es a crédito, será redirigido al listado de ventas',
          status: 'warning',
          duration: 5000,
          isClosable: true
        });
        navigate('/ventas');
      }
    }
  });

  // Obtener los pagos realizados
  const { data: pagos = [] } = useQuery({
    queryKey: ['pagos-venta', id],
    queryFn: () => ventasService.getPagosVenta(id)
  });

  // Calcular saldo pendiente
  const totalPagado = React.useMemo(() => {
    return pagos.reduce((sum, pago) => sum + parseFloat(pago.monto || 0), 0);
  }, [pagos]);

  const saldoPendiente = React.useMemo(() => {
    if (!venta) return 0;
    return parseFloat(venta.total || 0) - totalPagado;
  }, [venta, totalPagado]);

  useEffect(() => {
    if (venta && saldoPendiente <= 0) {
      toast({
        title: 'Venta pagada',
        description: 'Esta venta ya está completamente pagada',
        status: 'info',
        duration: 5000,
        isClosable: true
      });
      navigate('/cuentas/por-cobrar');
    }
  }, [venta, saldoPendiente, navigate]);

  const montoMaximo = saldoPendiente;
  const [error, setError] = useState('');

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
          setError(`El monto no puede ser mayor a ${cuentasService.formatCurrency(montoMaximo)}`);
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
      setError(`El monto no puede ser mayor a ${cuentasService.formatCurrency(montoMaximo)}`);
      return;
    }

    const data = {
      ...formData,
      monto: montoNumerico,
      completar_pago: montoNumerico >= montoMaximo
    };

    registrarPagoMutation.mutate(data);
  };

  if (isLoading) {
    return <Box p={4}>Cargando...</Box>;
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
                <Text fontSize="lg" fontWeight="bold">{venta?.numero}</Text>
              </Box>
              <Box>
                <Text fontSize="sm" color="gray.600">Cliente</Text>
                <Text fontSize="lg">{venta?.cliente?.nombre}</Text>
              </Box>
              <Box>
                <Text fontSize="sm" color="gray.600">Total Venta</Text>
                <Text fontSize="lg">{cuentasService.formatCurrency(venta?.total)}</Text>
              </Box>
              <Box>
                <Text fontSize="sm" color="gray.600">Saldo Pendiente</Text>
                <Text fontSize="lg" color="red.500" fontWeight="bold">
                  {cuentasService.formatCurrency(montoMaximo)}
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
                    S/
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
                  Monto máximo: {cuentasService.formatCurrency(montoMaximo)}
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
                  <option value="deposito">Depósito</option>
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

export default VentaPagoForm; 