import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardBody,
  Heading,
  VStack,
  Text,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Spinner,
  Button,
  Flex,
  Badge
} from '@chakra-ui/react';
import { ventasService } from '../../services/ventas.service';
import { getSimboloMoneda } from '../../utils/currency';

const VentaDetalle = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [venta, setVenta] = useState(null);
  const [detalles, setDetalles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchVenta = async () => {
      try {
        const data = await ventasService.getVenta(id);
        setVenta(data);
        setDetalles(data.detalles || []);
      } catch (error) {
        setVenta(null);
      } finally {
        setIsLoading(false);
      }
    };
    fetchVenta();
  }, [id]);

  if (isLoading) return <Spinner size="xl" />;
  if (!venta) return <Text>No se encontró la venta.</Text>;

  const simboloMoneda = getSimboloMoneda(venta.moneda);

  return (
    <Box maxW="container.md" mx="auto" py={8}>
      <Card>
        <CardBody>
          <VStack spacing={6} align="stretch">
            <Heading size="md">Detalle de Venta</Heading>
            <Text><b>Número:</b> {venta.numero}</Text>
            <Text><b>Cliente:</b> {venta.cliente_nombre}</Text>
            <Text><b>Fecha de Emisión:</b> {venta.fecha_emision}</Text>
            <Text><b>Estado:</b> <Badge colorScheme="blue">{venta.estado}</Badge></Text>
            <Text><b>Método de Pago:</b> {venta.estado_pago}</Text>
            <Text><b>Subtotal:</b> {simboloMoneda} {venta.subtotal}</Text>
            <Text><b>IGV:</b> {simboloMoneda} {venta.igv}</Text>
            <Text><b>Total:</b> <b>{simboloMoneda} {venta.total}</b></Text>
            <Heading size="sm" mt={4}>Productos</Heading>
            <Table size="sm" variant="simple">
              <Thead>
                <Tr>
                  <Th>Producto</Th>
                  <Th>Cantidad</Th>
                  <Th>Precio Unitario</Th>
                  <Th>Subtotal</Th>
                </Tr>
              </Thead>
              <Tbody>
                {detalles.length === 0 ? (
                  <Tr><Td colSpan={4}>Sin productos</Td></Tr>
                ) : (
                  detalles.map((detalle) => (
                    <Tr key={detalle.id}>
                      <Td>{detalle.producto_nombre}</Td>
                      <Td>{detalle.cantidad}</Td>
                      <Td>{simboloMoneda} {detalle.precio_unitario}</Td>
                      <Td>{simboloMoneda} {(detalle.cantidad * detalle.precio_unitario).toFixed(2)}</Td>
                    </Tr>
                  ))
                )}
              </Tbody>
            </Table>
            <Flex justify="flex-end">
              <Button onClick={() => navigate('/app/ventas')}>Volver</Button>
            </Flex>
          </VStack>
        </CardBody>
      </Card>
    </Box>
  );
};

export default VentaDetalle; 