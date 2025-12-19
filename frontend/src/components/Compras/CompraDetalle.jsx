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
  Badge,
  HStack,
  IconButton,
  Tooltip,
  Divider,
  useToast
} from '@chakra-ui/react';
import { InfoIcon, ViewIcon } from '@chakra-ui/icons';
import { comprasService } from '../../services/compras.service';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { ESTADOS_COMPRA, METODOS_PAGO, ESTADOS_DISPLAY, METODOS_PAGO_DISPLAY } from './constants';

const CompraDetalle = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [compra, setCompra] = useState(null);
  const [detalles, setDetalles] = useState([]);
  const [pagos, setPagos] = useState([]);
  const [saldoPendiente, setSaldoPendiente] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        console.log('Obteniendo datos de la compra:', id);
        const compraData = await comprasService.getCompra(id);
        console.log('Datos de compra recibidos:', compraData);
        
        setCompra(compraData);
        setDetalles(compraData.detalles || []);

        if (compraData.tipo_compra.startsWith('credito_')) {
          try {
            const [pagosData, saldoData] = await Promise.all([
              comprasService.getPagosCompra(id),
              comprasService.getSaldoPendiente(id)
            ]);
            setPagos(pagosData || []);
            setSaldoPendiente(saldoData || 0);
          } catch (error) {
            console.error('Error al obtener pagos o saldo:', error);
            toast({
              title: 'Error',
              description: 'No se pudieron cargar los pagos o el saldo pendiente',
              status: 'warning',
              duration: 5000,
            });
          }
        }
      } catch (error) {
        console.error('Error al cargar datos de la compra:', error);
        toast({
          title: 'Error',
          description: 'No se pudo cargar la información de la compra',
          status: 'error',
          duration: 5000,
        });
        setCompra(null);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [id, toast]);

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
    return format(new Date(dateString), 'dd/MM/yyyy', { locale: es });
  };

  const getEstadoBadge = (estado) => {
    const estadoLower = estado?.toLowerCase() || '';
    return (
      <Badge colorScheme={getEstadoColor(estadoLower)}>
        {ESTADOS_DISPLAY[estadoLower] || estado}
      </Badge>
    );
  };

  const getEstadoColor = (estado) => {
    switch (estado) {
      case 'borrador': return 'gray';
      case 'pendiente': return 'yellow';
      case 'pagada': return 'green';
      case 'anulada': return 'red';
      default: return 'gray';
    }
  };

  const getMetodoPagoBadge = (metodoPago) => {
    return (
      <Badge colorScheme={getMetodoPagoColor(metodoPago)}>
        {METODOS_PAGO_DISPLAY[metodoPago] || metodoPago}
      </Badge>
    );
  };

  const getMetodoPagoColor = (metodoPago) => {
    switch (metodoPago) {
      case 'efectivo': return 'green';
      case 'transferencia': return 'blue';
      case 'cheque': return 'purple';
      case 'tarjeta': return 'orange';
      case 'credito_30': return 'pink';
      case 'credito_60': return 'red';
      default: return 'gray';
    }
  };

  const getFechaVencimientoDisplay = (compra) => {
    if (!compra.fecha_vencimiento) return null;
    
    const fechaVencimiento = new Date(compra.fecha_vencimiento);
    const hoy = new Date();
    const diasRestantes = Math.ceil((fechaVencimiento - hoy) / (1000 * 60 * 60 * 24));
    
    let color = 'gray';
    if (diasRestantes < 0) color = 'red';
    else if (diasRestantes <= 5) color = 'orange';
    else if (diasRestantes <= 15) color = 'yellow';
    else color = 'green';

    return (
      <Tooltip label={`Vence el ${formatDate(compra.fecha_vencimiento)}`}>
        <Badge colorScheme={color} variant="outline">
          {diasRestantes < 0 
            ? `Vencido hace ${Math.abs(diasRestantes)} días`
            : `${diasRestantes} días restantes`}
        </Badge>
      </Tooltip>
    );
  };

  if (isLoading) return <Spinner size="xl" />;
  if (!compra) return <Text>No se encontró la compra.</Text>;

  return (
    <Box p={4}>
      <VStack spacing={6} align="stretch">
        <Card>
          <CardBody>
            <VStack spacing={4} align="stretch">
              <Heading size="md">Detalles de la Compra</Heading>
              <Flex justify="space-between" wrap="wrap" gap={4}>
                <Box flex="1" minW="300px">
                  <Text><strong>Número:</strong> {compra.numero}</Text>
                  <Text><strong>Proveedor:</strong> {compra.proveedor_nombre}</Text>
                  <Text><strong>Fecha de Emisión:</strong> {formatDate(compra.fecha_emision)}</Text>
                  {compra.fecha_vencimiento && (
                    <Text>
                      <strong>Fecha de Vencimiento:</strong> {formatDate(compra.fecha_vencimiento)}
                      {getFechaVencimientoDisplay(compra)}
                    </Text>
                  )}
                </Box>
                <Box flex="1" minW="300px">
                  <Text><strong>Estado:</strong> {getEstadoBadge(compra.estado)}</Text>
                  <Text>
                    <strong>Método de Pago:</strong> {getMetodoPagoBadge(compra.metodo_pago)}
                  </Text>
                  <Text><strong>Total:</strong> {formatCurrency(compra.total, compra.moneda)}</Text>
                  {compra.metodo_pago.startsWith('credito_') && (
                    <Text><strong>Saldo Pendiente:</strong> {formatCurrency(saldoPendiente, compra.moneda)}</Text>
                  )}
                </Box>
              </Flex>
            </VStack>
          </CardBody>
        </Card>

        {compra.metodo_pago.startsWith('credito_') && (
          <Card>
            <CardBody>
              <VStack spacing={4} align="stretch">
                <HStack justify="space-between">
                  <Heading size="md">Pagos Realizados</Heading>
                  {saldoPendiente > 0 && (
                    <Button
                      colorScheme="blue"
                      onClick={() => navigate(`/app/compras/${id}/pagos/nuevo`)}
                    >
                      Registrar Nuevo Pago
                    </Button>
                  )}
                </HStack>

                <Table variant="simple">
                  <Thead>
                    <Tr>
                      <Th>Fecha</Th>
                      <Th>Monto</Th>
                      <Th>Método de Pago</Th>
                      <Th>Referencia</Th>
                      <Th>Acciones</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {pagos && pagos.length > 0 ? (
                      pagos.map((pago) => (
                        <Tr key={pago.id}>
                          <Td>{formatDate(pago.fecha)}</Td>
                          <Td>{formatCurrency(pago.monto, compra.moneda)}</Td>
                          <Td>
                            <Badge colorScheme="blue">
                              {pago.metodo_pago}
                            </Badge>
                          </Td>
                          <Td>{pago.referencia}</Td>
                          <Td>
                            {pago.comprobante && (
                              <Tooltip label="Ver comprobante">
                                <IconButton
                                  icon={<ViewIcon />}
                                  aria-label="Ver comprobante"
                                  size="sm"
                                  onClick={() => window.open(pago.comprobante, '_blank')}
                                />
                              </Tooltip>
                            )}
                          </Td>
                        </Tr>
                      ))
                    ) : (
                      <Tr>
                        <Td colSpan={5} textAlign="center">No hay pagos registrados</Td>
                      </Tr>
                    )}
                  </Tbody>
                </Table>
              </VStack>
            </CardBody>
          </Card>
        )}

        <Card>
          <CardBody>
            <VStack spacing={4} align="stretch">
              <Heading size="md">Detalles de Productos</Heading>
              <Table variant="simple">
                <Thead>
                  <Tr>
                    <Th>Producto</Th>
                    <Th>Cantidad</Th>
                    <Th>Precio Unitario</Th>
                    <Th>Subtotal</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {detalles.map((detalle, index) => (
                    <Tr key={index}>
                      <Td>{detalle.producto_nombre}</Td>
                      <Td>{detalle.cantidad}</Td>
                                              <Td>{formatCurrency(detalle.precio_unitario, compra.moneda)}</Td>
                        <Td>{formatCurrency(detalle.cantidad * detalle.precio_unitario, compra.moneda)}</Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>

              <Divider />

              <Box alignSelf="flex-end">
                <Text><strong>Subtotal:</strong> {formatCurrency(compra.subtotal, compra.moneda)}</Text>
                <Text><strong>IGV (18%):</strong> {formatCurrency(compra.igv, compra.moneda)}</Text>
                <Text fontSize="lg"><strong>Total:</strong> {formatCurrency(compra.total, compra.moneda)}</Text>
              </Box>
            </VStack>
          </CardBody>
        </Card>

        <HStack justify="flex-end" spacing={4}>
          <Button onClick={() => navigate('/app/compras')}>
            Volver a Compras
          </Button>
          {compra.estado !== 'anulada' && (
            <Button
              colorScheme="blue"
              onClick={() => navigate(`/app/compras/${id}/editar`)}
            >
              Editar Compra
            </Button>
          )}
          {compra.metodo_pago.startsWith('credito_') && saldoPendiente > 0 && (
            <Button
              colorScheme="green"
              onClick={() => navigate(`/app/compras/${id}/pagos`)}
            >
              Ver Pagos
            </Button>
          )}
        </HStack>
      </VStack>
    </Box>
  );
};

export default CompraDetalle; 