import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Box,
    Button,
    Table,
    Thead,
    Tbody,
    Tr,
    Th,
    Td,
    VStack,
    Heading,
    Text,
    Badge,
    Card,
    CardBody,
    IconButton,
    Tooltip,
    HStack,
    Spinner,
    useToast
} from '@chakra-ui/react';
import { AddIcon, ViewIcon } from '@chakra-ui/icons';
import { useQuery } from '@tanstack/react-query';
import { ventasService } from '../../services/ventas.service';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { ESTADOS_DISPLAY, TIPOS_VENTA_DISPLAY, METODOS_PAGO_DISPLAY } from './constants';

const VentaPagos = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const toast = useToast();

    // Función para obtener el símbolo de moneda
    const getSimboloMoneda = (moneda) => {
        const simbolos = {
            'PEN': 'S/',
            'USD': '$'
        };
        return simbolos[moneda] || 'S/';
    };

    const { data: venta, isLoading: isLoadingVenta } = useQuery({
        queryKey: ['venta', id],
        queryFn: () => ventasService.getVenta(id)
    });

    const { data: pagos, isLoading: isLoadingPagos } = useQuery({
        queryKey: ['pagos', id],
        queryFn: () => ventasService.getPagosVenta(id)
    });

    const { data: saldoPendiente, isLoading: isLoadingSaldo } = useQuery({
        queryKey: ['saldo', id],
        queryFn: () => ventasService.getSaldoPendiente(id)
    });

    if (isLoadingVenta || isLoadingPagos || isLoadingSaldo) {
        return (
            <Box display="flex" justifyContent="center" alignItems="center" minH="200px">
                <Spinner size="xl" />
            </Box>
        );
    }

    const simboloMoneda = getSimboloMoneda(venta?.moneda);

    return (
        <Box p={4}>
            <VStack spacing={6} align="stretch">
                <HStack justify="space-between">
                    <Heading size="lg">Pagos de Venta #{venta?.numero}</Heading>
                    {venta?.tipo_venta !== 'contado' && venta?.estado !== 'pagado' && (
                        <Button
                            leftIcon={<AddIcon />}
                            colorScheme="blue"
                            onClick={() => navigate(`/app/ventas/${id}/pagos/nuevo`)}
                        >
                            Nuevo Pago
                        </Button>
                    )}
                </HStack>

                <Card>
                    <CardBody>
                        <VStack spacing={4} align="stretch">
                            <HStack justify="space-between">
                                <Text fontSize="lg" fontWeight="bold">
                                    Cliente: {venta?.cliente_nombre}
                                </Text>
                                <Badge
                                    colorScheme={venta?.estado === 'pagado' ? 'green' : 'yellow'}
                                    fontSize="md"
                                    p={2}
                                >
                                    {ESTADOS_DISPLAY[venta?.estado]}
                                </Badge>
                            </HStack>
                            <HStack justify="space-between">
                                <Text>
                                    Fecha de emisión:{' '}
                                    {venta?.fecha_emision && format(new Date(venta.fecha_emision), 'PPP', { locale: es })}
                                </Text>
                                <Text>
                                    Tipo de venta: {TIPOS_VENTA_DISPLAY[venta?.tipo_venta]}
                                </Text>
                            </HStack>
                            {venta?.fecha_vencimiento && (
                                <Text>
                                    Fecha de vencimiento:{' '}
                                    {format(new Date(venta.fecha_vencimiento), 'PPP', { locale: es })}
                                </Text>
                            )}
                            <HStack justify="space-between">
                                <Text fontWeight="bold">Total: {simboloMoneda} {venta?.total}</Text>
                                <Text fontWeight="bold" color={saldoPendiente > 0 ? 'red.500' : 'green.500'}>
                                    Saldo pendiente: {simboloMoneda} {saldoPendiente}
                                </Text>
                            </HStack>
                        </VStack>
                    </CardBody>
                </Card>

                <Card>
                    <CardBody>
                        <Table variant="simple">
                            <Thead>
                                <Tr>
                                    <Th>Fecha</Th>
                                    <Th>Método</Th>
                                    <Th isNumeric>Monto</Th>
                                    <Th>Referencia</Th>
                                    <Th>Comprobante</Th>
                                    <Th>Notas</Th>
                                </Tr>
                            </Thead>
                            <Tbody>
                                {pagos?.map((pago) => (
                                    <Tr key={pago.id}>
                                        <Td>{format(new Date(pago.fecha), 'PPP', { locale: es })}</Td>
                                        <Td>{METODOS_PAGO_DISPLAY[pago.metodo_pago]}</Td>
                                        <Td isNumeric>{simboloMoneda} {pago.monto}</Td>
                                        <Td>{pago.referencia}</Td>
                                        <Td>
                                            {pago.comprobante && (
                                                <Tooltip label="Ver comprobante">
                                                    <IconButton
                                                        icon={<ViewIcon />}
                                                        variant="ghost"
                                                        onClick={() => window.open(pago.comprobante)}
                                                    />
                                                </Tooltip>
                                            )}
                                        </Td>
                                        <Td>{pago.notas}</Td>
                                    </Tr>
                                ))}
                            </Tbody>
                        </Table>
                    </CardBody>
                </Card>
            </VStack>
        </Box>
    );
};

export default VentaPagos; 