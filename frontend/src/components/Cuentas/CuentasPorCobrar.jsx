import React, { useState } from 'react';
import {
  Box,
  Container,
  Heading,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Button,
  HStack,
  VStack,
  Text,
  useToast,
  Spinner,
  Flex,
  Spacer,
  IconButton,
  Tooltip,
  Card,
  CardBody,
  Stat,
  StatLabel,
  StatNumber,
  StatGroup,
  Input,
  InputGroup,
  InputLeftElement
} from '@chakra-ui/react';
import { SearchIcon, ViewIcon } from '@chakra-ui/icons';
import { useQuery } from '@tanstack/react-query';
import { ventasService } from '../../services/ventas.service';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { useNavigate } from 'react-router-dom';

const CuentasPorCobrar = () => {
  const [page, setPage] = useState(1);
  const pageSize = 10;
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const toast = useToast();

  // Consulta para obtener las ventas pendientes
  const { data: ventasResponse, isLoading, error } = useQuery({
    queryKey: ['ventas-pendientes', page],
    queryFn: () => ventasService.getVentasPendientes(),
    refetchInterval: 5000 // Refrescar cada 5 segundos
  });

  // Extraer ventas del response
  const ventas = ventasResponse?.ventas || [];
  const totalGeneralPen = ventasResponse?.total_general_pen || 0;
  const tipoCambio = ventasResponse?.tipo_cambio || 3.8;

  const handleSearch = (event) => {
    const term = event.target.value.toLowerCase();
    setSearchTerm(term);
  };

  const filteredVentas = React.useMemo(() => {
    if (!ventas) return [];
    return ventas.filter(venta => 
      venta.numero?.toLowerCase().includes(searchTerm) ||
      venta.cliente?.nombre?.toLowerCase().includes(searchTerm) ||
      venta.cliente?.documento?.toLowerCase().includes(searchTerm)
    );
  }, [ventas, searchTerm]);

  const getEstadoColor = (diasRestantes) => {
    if (diasRestantes < 0) return 'red';
    if (diasRestantes === 0) return 'orange';
    if (diasRestantes <= 5) return 'yellow';
    return 'green';
  };

  const getEstadoLabel = (diasRestantes) => {
    if (diasRestantes < 0) return `VENCIDO (${Math.abs(diasRestantes)} días)`;
    if (diasRestantes === 0) return 'VENCE HOY';
    return `${diasRestantes} DÍAS RESTANTES`;
  };

  if (isLoading) {
    return (
      <Flex justify="center" align="center" minH="400px">
        <Spinner size="xl" />
      </Flex>
    );
  }

  if (error) {
    return <Box p={4}>Error al cargar las cuentas por cobrar</Box>;
  }

  // Función para formatear moneda
  const formatCurrency = (amount, currency = 'PEN') => {
    const symbol = currency === 'USD' ? '$' : 'S/';
    return `${symbol} ${parseFloat(amount || 0).toFixed(2)}`;
  };

  return (
    <Box p={5}>
      <Heading mb={5}>Cuentas por Cobrar</Heading>
      <Text mb={4} color="gray.600" fontSize="sm">
        Este módulo muestra únicamente las ventas a crédito (30 o 60 días) que tienen saldo pendiente por cobrar.
      </Text>

      <HStack spacing={4} mb={5}>
        <Card flex="1">
          <CardBody>
            <StatGroup>
              <Stat>
                <StatLabel>Total por Cobrar (en Soles)</StatLabel>
                <StatNumber>S/ {totalGeneralPen.toFixed(2)}</StatNumber>
                <Text fontSize="xs" color="gray.500">
                  Tipo de cambio: S/ {tipoCambio}
                </Text>
              </Stat>
            </StatGroup>
          </CardBody>
        </Card>
        <Card flex="1">
          <CardBody>
            <StatGroup>
              <Stat>
                <StatLabel>Ventas Pendientes</StatLabel>
                <StatNumber>{filteredVentas.length}</StatNumber>
              </Stat>
            </StatGroup>
          </CardBody>
        </Card>
      </HStack>

      <Card>
        <CardBody>
          <Flex mb={4} align="center">
            <Heading size="md">Listado de Cuentas por Cobrar</Heading>
            <Spacer />
            <InputGroup maxW="300px">
              <InputLeftElement pointerEvents="none">
                <SearchIcon color="gray.300" />
              </InputLeftElement>
              <Input
                placeholder="Buscar por número, cliente o documento..."
                value={searchTerm}
                onChange={handleSearch}
              />
            </InputGroup>
          </Flex>

          {filteredVentas.length === 0 ? (
            <Box textAlign="center" py={10}>
              <Text fontSize="lg" color="gray.500">
                No hay ventas a crédito pendientes por cobrar
              </Text>
              <Text fontSize="sm" color="gray.400" mt={2}>
                Las ventas a crédito aparecerán aquí cuando tengan saldo pendiente
              </Text>
            </Box>
          ) : (
            <Table variant="simple">
              <Thead>
                <Tr>
                  <Th>N° VENTA</Th>
                  <Th>CLIENTE</Th>
                  <Th>DOCUMENTO</Th>
                  <Th>FECHA EMISIÓN</Th>
                  <Th>FECHA VENCIMIENTO</Th>
                  <Th>PLAZO CRÉDITO</Th>
                  <Th>TOTAL</Th>
                  <Th>SALDO PENDIENTE</Th>
                  <Th>ESTADO</Th>
                  <Th>ACCIONES</Th>
                </Tr>
              </Thead>
              <Tbody>
                {filteredVentas.map((venta) => (
                  <Tr key={venta.id}>
                    <Td>{venta.numero}</Td>
                    <Td>{venta.cliente?.nombre || 'N/A'}</Td>
                    <Td>{venta.cliente?.documento || 'N/A'}</Td>
                    <Td>{format(new Date(venta.fecha_emision), 'dd/MM/yyyy', { locale: es })}</Td>
                    <Td>
                      {venta.fecha_vencimiento ? 
                        format(new Date(venta.fecha_vencimiento), 'dd/MM/yyyy', { locale: es }) :
                        'N/A'}
                    </Td>
                    <Td>
                      <Badge colorScheme="blue">
                        {venta.tipo_venta === 'credito_30' ? '30' : '60'} días
                      </Badge>
                    </Td>
                    <Td>{formatCurrency(venta.total, venta.moneda)}</Td>
                    <Td>{formatCurrency(venta.saldo_pendiente, venta.moneda)}</Td>
                    <Td>
                      <Badge
                        colorScheme={getEstadoColor(venta.dias_restantes)}
                        p={2}
                        borderRadius="md"
                      >
                        {getEstadoLabel(venta.dias_restantes)}
                      </Badge>
                    </Td>
                    <Td>
                      <HStack spacing={2}>
                        <Tooltip label="Ver detalle">
                          <IconButton
                            size="sm"
                            icon={<ViewIcon />}
                            onClick={() => navigate(`/ventas/${venta.id}`)}
                          />
                        </Tooltip>
                        <Button
                          size="sm"
                          colorScheme="green"
                          onClick={() => navigate(`/cuentas/por-cobrar/${venta.id}/registrar-pago`)}
                          isDisabled={parseFloat(venta.saldo_pendiente || 0) <= 0}
                        >
                          Registrar Pago
                        </Button>
                      </HStack>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          )}
        </CardBody>
      </Card>
    </Box>
  );
};

export default CuentasPorCobrar; 