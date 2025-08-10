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
import { cuentasService } from '../../services/cuentas.service';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { useNavigate } from 'react-router-dom';

const CuentasPorPagar = () => {
  const [page, setPage] = useState(1);
  const pageSize = 10;
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const toast = useToast();

  // Consulta para obtener las compras pendientes
  const { data, isLoading, error } = useQuery({
    queryKey: ['cuentas-por-pagar', page],
    queryFn: () => cuentasService.getCuentasPorPagar({ page, pageSize }),
    refetchInterval: 5000 // Refrescar cada 5 segundos
  });

  const compras = data?.results || [];
  const totalGeneralPen = data?.total_general_pen || 0;
  const tipoCambio = data?.tipo_cambio || 3.8;

  const handleSearch = (event) => {
    const term = event.target.value.toLowerCase();
    setSearchTerm(term);
  };

  const filteredCompras = React.useMemo(() => {
    if (!compras) return [];
    return compras.filter(compra => 
      compra.numero?.toLowerCase().includes(searchTerm) ||
      compra.proveedor?.razon_social?.toLowerCase().includes(searchTerm) ||
      compra.proveedor?.ruc?.toLowerCase().includes(searchTerm)
    );
  }, [compras, searchTerm]);

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
    return <Box p={4}>Error al cargar las cuentas por pagar</Box>;
  }

  // Función para formatear moneda
  const formatCurrency = (amount, currency = 'PEN') => {
    const symbol = currency === 'USD' ? '$' : 'S/';
    return `${symbol} ${parseFloat(amount || 0).toFixed(2)}`;
  };

  return (
    <Box p={5}>
      <Heading mb={5}>Cuentas por Pagar</Heading>
      <Text mb={4} color="gray.600" fontSize="sm">
        Este módulo muestra únicamente las compras a crédito (30 o 60 días) que tienen saldo pendiente por pagar.
      </Text>

      <HStack spacing={4} mb={5}>
        <Card flex="1">
          <CardBody>
            <StatGroup>
              <Stat>
                <StatLabel>Total por Pagar (en Soles)</StatLabel>
                <StatNumber>S/ {totalGeneralPen.toFixed(2)}</StatNumber>
                <Text fontSize="xs" color="gray.500" mt={1}>
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
                <StatLabel>Compras Pendientes</StatLabel>
                <StatNumber>{filteredCompras.length}</StatNumber>
              </Stat>
            </StatGroup>
          </CardBody>
        </Card>
      </HStack>

      <Card>
        <CardBody>
          <Flex mb={4} align="center">
            <Heading size="md">Listado de Cuentas por Pagar</Heading>
            <Spacer />
            <InputGroup maxW="300px">
              <InputLeftElement pointerEvents="none">
                <SearchIcon color="gray.300" />
              </InputLeftElement>
              <Input
                placeholder="Buscar por número, proveedor o RUC..."
                value={searchTerm}
                onChange={handleSearch}
              />
            </InputGroup>
          </Flex>

          {filteredCompras.length === 0 ? (
            <Box textAlign="center" py={10}>
              <Text fontSize="lg" color="gray.500">
                No hay compras a crédito pendientes por pagar
              </Text>
              <Text fontSize="sm" color="gray.400" mt={2}>
                Las compras a crédito aparecerán aquí cuando tengan saldo pendiente
              </Text>
            </Box>
          ) : (
            <Table variant="simple">
              <Thead>
                <Tr>
                  <Th>N° COMPRA</Th>
                  <Th>PROVEEDOR</Th>
                  <Th>RUC</Th>
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
                {filteredCompras.map((compra) => (
                  <Tr key={compra.id}>
                    <Td>{compra.numero}</Td>
                    <Td>{compra.proveedor?.razon_social}</Td>
                    <Td>{compra.proveedor?.ruc}</Td>
                    <Td>{format(new Date(compra.fecha_emision), 'dd/MM/yyyy', { locale: es })}</Td>
                    <Td>
                      {compra.fecha_vencimiento ? 
                        format(new Date(compra.fecha_vencimiento), 'dd/MM/yyyy', { locale: es }) :
                        'N/A'}
                    </Td>
                    <Td>
                      <Badge colorScheme="blue">
                        {compra.tipo_compra === 'credito_30' ? '30' : '60'} días
                      </Badge>
                    </Td>
                    <Td>
                      {formatCurrency(compra.total, compra.moneda)}
                      {compra.moneda === 'USD' && (
                        <Text fontSize="xs" color="gray.500">
                          ≈ S/ {compra.total_pen?.toFixed(2)}
                        </Text>
                      )}
                    </Td>
                    <Td>
                      {formatCurrency(compra.saldo_pendiente, compra.moneda)}
                      {compra.moneda === 'USD' && (
                        <Text fontSize="xs" color="gray.500">
                          ≈ S/ {compra.saldo_pendiente_pen?.toFixed(2)}
                        </Text>
                      )}
                    </Td>
                    <Td>
                      <Badge
                        colorScheme={getEstadoColor(compra.dias_restantes)}
                        p={2}
                        borderRadius="md"
                      >
                        {getEstadoLabel(compra.dias_restantes)}
                      </Badge>
                    </Td>
                    <Td>
                      <HStack spacing={2}>
                        <Tooltip label="Ver detalle">
                          <IconButton
                            size="sm"
                            icon={<ViewIcon />}
                            onClick={() => navigate(`/compras/${compra.id}`)}
                          />
                        </Tooltip>
                        <Button
                          size="sm"
                          colorScheme="green"
                          onClick={() => navigate(`/cuentas/por-pagar/${compra.id}/registrar-pago`)}
                          isDisabled={parseFloat(compra.saldo_pendiente || 0) <= 0}
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

export default CuentasPorPagar; 