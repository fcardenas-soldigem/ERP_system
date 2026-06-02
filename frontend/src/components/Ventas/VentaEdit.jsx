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
  Badge
} from '@chakra-ui/react';
import { ventasService } from '../../services/ventas.service';
import { getSimboloMoneda } from '../../utils/currency';

const estados = [
  { value: 'borrador', label: 'Borrador' },
  { value: 'pendiente', label: 'Pendiente' },
  { value: 'pagado', label: 'Pagado' },
  { value: 'anulado', label: 'Anulado' },
];

const VentaEdit = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [venta, setVenta] = useState(null);
  const [estado, setEstado] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const fetchVenta = async () => {
      try {
        const data = await ventasService.getVenta(id);
        setVenta(data);
        setEstado(data.estado);
      } catch (error) {
        toast({
          title: 'Error',
          description: 'No se pudo cargar la venta',
          status: 'error',
          duration: 3000,
        });
      } finally {
        setIsLoading(false);
      }
    };
    fetchVenta();
  }, [id, toast]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await ventasService.cambiarEstado(id, estado);
      toast({
        title: 'Estado actualizado',
        status: 'success',
        duration: 2000,
      });
      navigate('/app/ventas');
    } catch (error) {
      toast({
        title: 'Error',
        description: 'No se pudo actualizar el estado',
        status: 'error',
        duration: 3000,
      });
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return <Spinner size="xl" />;
  }

  if (!venta) {
    return <Text>No se encontró la venta.</Text>;
  }

  return (
    <Box maxW="container.md" mx="auto" py={8}>
      <Card>
        <CardBody>
          <VStack spacing={6} align="stretch">
            <Heading size="md">Editar Estado de Venta</Heading>
            <Text><b>Número:</b> {venta.numero}</Text>
            <Text><b>Cliente:</b> {venta.cliente_nombre}</Text>
            <Text><b>Fecha de Emisión:</b> {venta.fecha_emision}</Text>
            <Text><b>Estado actual:</b> <Badge colorScheme="blue">{venta.estado}</Badge></Text>
            <Text><b>Método de Pago:</b> {venta.estado_pago}</Text>
            <Text><b>Total:</b> {getSimboloMoneda(venta.moneda)} {venta.total}</Text>
            <FormControl>
              <FormLabel>Estado</FormLabel>
              <Select value={estado} onChange={e => setEstado(e.target.value)}>
                {estados.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </Select>
            </FormControl>
            <Button colorScheme="blue" onClick={handleSave} isLoading={isSaving}>
              Guardar Cambios
            </Button>
            <Button variant="ghost" onClick={() => navigate('/app/ventas')}>Cancelar</Button>
          </VStack>
        </CardBody>
      </Card>
    </Box>
  );
};

export default VentaEdit; 