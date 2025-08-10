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
import { comprasService } from '../../services/compras.service';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { METODOS_PAGO_DISPLAY } from './constants';

const CompraPagos = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const toast = useToast();

    const { data: compra, isLoading: isLoadingCompra } = useQuery(
        ['compra', id],
        () => comprasService.getCompra(id)
    );

    const { data: pagos, isLoading: isLoadingPagos } = useQuery(
        ['pagos-compra', id],
        () => comprasService.getPagosCompra(id)
    );

    const { data: saldoPendiente, isLoading: isLoadingSaldo } = useQuery(
        ['saldo-pendiente-compra', id],
        () => comprasService.getSaldoPendiente(id)
    );

    if (isLoadingCompra || isLoadingPagos || isLoadingSaldo) {
        return (
            <Box display="flex" justifyContent="center" alignItems="center" minH="200px">
                <Spinner size="xl" />
            </Box>
        );
    }

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

    return (
        <Box p={4}>
            <VStack spacing={6} align="stretch">
                <HStack justify="space-between">
                    <Heading size="lg">Pagos de Compra #{compra?.numero}</Heading>
                    <Button
                        leftIcon={<AddIcon />}
                        colorScheme="blue"
                        onClick={() => navigate(`/compras/${id}/pagos/nuevo`)}
                    >
                        Nuevo Pago
                    </Button>
                </HStack>

                <Card>
                    <CardBody>
                        <VStack spacing={4} align="stretch">
                            <HStack justify="space-between">
                                <Text fontSize="lg" fontWeight="bold">
                                    Proveedor: {compra?.proveedor_nombre}
                                </Text>
                                <Badge
                                    colorScheme={compra?.estado === 'pagada' ? 'green' : 'yellow'}
                                    fontSize="md"
                                    p={2}
                                >
                                    {compra?.estado === 'pagada' ? 'Pagada' : 'Pendiente'}
                                </Badge>
                            </HStack>
                            <HStack justify="space-between">
                                <Text>
                                    Fecha de emisión:{' '}
                                    {format(new Date(compra?.fecha_emision), 'PPP', { locale: es })}
                                </Text>
                                <Text>
                                    Método de pago: {METODOS_PAGO_DISPLAY[compra?.metodo_pago]}
                                </Text>
                            </HStack>
                            <HStack justify="space-between">
                                <Text fontWeight="bold">Total: {formatCurrency(compra?.total, compra?.moneda)}</Text>
                                <Text fontWeight="bold" color={saldoPendiente > 0 ? 'red.500' : 'green.500'}>
                                    Saldo pendiente: {formatCurrency(saldoPendiente, compra?.moneda)}
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
                                </Tr>
                            </Thead>
                            <Tbody>
                                {pagos?.map((pago) => (
                                    <Tr key={pago.id}>
                                        <Td>{format(new Date(pago.fecha), 'PPP', { locale: es })}</Td>
                                        <Td>{METODOS_PAGO_DISPLAY[pago.metodo_pago]}</Td>
                                        <Td isNumeric>{formatCurrency(pago.monto, compra?.moneda)}</Td>
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

export default CompraPagos; 