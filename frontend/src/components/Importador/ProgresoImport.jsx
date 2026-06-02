import React from 'react';
import {
  VStack, HStack, Box, Text, Progress, Icon, Badge,
  Button, Divider, SimpleGrid, Stat, StatLabel, StatNumber,
  Accordion, AccordionItem, AccordionButton, AccordionPanel, AccordionIcon,
  Table, Thead, Tbody, Tr, Th, Td, TableContainer,
  useColorModeValue,
} from '@chakra-ui/react';
import {
  FiCheckCircle, FiAlertTriangle, FiAlertCircle,
  FiArrowRight, FiDownload,
} from 'react-icons/fi';
import { useNavigate } from 'react-router-dom';

const FASES = [
  'Leyendo archivo...',
  'Creando proveedores...',
  'Creando productos...',
  'Generando compras...',
  'Generando ventas...',
  'Actualizando inventario...',
  'Finalizando...',
];

function StatCard({ label, value, color }) {
  const bg     = useColorModeValue(`${color}.50`, `${color}.900`);
  const textC  = useColorModeValue(`${color}.700`, `${color}.200`);
  return (
    <Box bg={bg} borderRadius="xl" px={5} py={4}>
      <Stat>
        <StatLabel fontSize="xs" color={textC} textTransform="uppercase" letterSpacing="wider">
          {label}
        </StatLabel>
        <StatNumber fontSize="2xl" color={textC}>{value}</StatNumber>
      </Stat>
    </Box>
  );
}

export default function ProgresoImport({ estado, resultado, onReset }) {
  const navigate    = useNavigate();
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const subText     = useColorModeValue('gray.500', 'gray.400');

  const isLoading   = estado === 'importando' || estado === 'procesando';
  const isCompleted = estado === 'completado' || estado === 'parcial';
  const isError     = estado === 'error';

  // Simula fase durante la carga
  const [faseIdx, setFaseIdx] = React.useState(0);
  React.useEffect(() => {
    if (!isLoading) return;
    const timer = setInterval(() => {
      setFaseIdx(prev => (prev < FASES.length - 1 ? prev + 1 : prev));
    }, 1200);
    return () => clearInterval(timer);
  }, [isLoading]);

  const downloadErrorReport = () => {
    if (!resultado?.errores_json?.length) return;
    const rows = [
      ['Hoja', 'Fila', 'Producto', 'Error'],
      ...(resultado.errores_json.map(e => [e.hoja, e.fila, e.producto, e.error])),
    ];
    const csv = rows.map(r => r.map(c => `"${c || ''}"`).join(',')).join('\n');
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = 'errores_importacion.csv'; a.click();
    URL.revokeObjectURL(url);
  };

  // Loading state
  if (isLoading) {
    return (
      <VStack spacing={8} py={12} align="center">
        <VStack spacing={3}>
          <Text fontSize="xl" fontWeight="semibold">Importando datos...</Text>
          <Text fontSize="sm" color={subText}>{FASES[faseIdx]}</Text>
        </VStack>
        <Box w="full" maxW="md">
          <Progress
            isIndeterminate
            colorScheme="blue"
            borderRadius="full"
            h="6px"
          />
        </Box>
        <Text fontSize="xs" color={subText}>
          No cierres esta ventana. El proceso puede tomar unos minutos.
        </Text>
      </VStack>
    );
  }

  // Error state
  if (isError) {
    return (
      <VStack spacing={6} py={10} align="center">
        <Icon as={FiAlertCircle} boxSize={14} color="red.400" />
        <VStack spacing={1}>
          <Text fontSize="xl" fontWeight="semibold">Error en la importación</Text>
          <Text fontSize="sm" color={subText} textAlign="center" maxW="400px">
            {resultado?.errores_json?.[0]?.error || 'Ocurrió un error inesperado'}
          </Text>
        </VStack>
        <Button variant="outline" onClick={onReset} size="sm">
          Intentar de nuevo
        </Button>
      </VStack>
    );
  }

  // Completed state
  const errores = resultado?.errores_json || [];
  const hasErrors = errores.length > 0;

  return (
    <VStack spacing={8} align="stretch">
      {/* Success header */}
      <VStack spacing={3} pt={6} align="center">
        <Icon
          as={hasErrors ? FiAlertTriangle : FiCheckCircle}
          boxSize={14}
          color={hasErrors ? 'yellow.400' : 'green.400'}
        />
        <VStack spacing={1}>
          <Text fontSize="xl" fontWeight="semibold">
            {hasErrors ? 'Importación con advertencias' : 'Importación completada'}
          </Text>
          <Text fontSize="sm" color={subText}>
            {resultado?.filas_importadas || 0} de {resultado?.total_filas || 0} operaciones importadas
          </Text>
        </VStack>
      </VStack>

      {/* Stats grid */}
      <SimpleGrid columns={{ base: 2, md: 4 }} spacing={3}>
        <StatCard label="Proveedores" value={resultado?.proveedores_creados || 0} color="orange" />
        <StatCard label="Productos" value={resultado?.productos_creados || 0} color="purple" />
        <StatCard label="Compras" value={resultado?.compras_creadas || 0} color="blue" />
        <StatCard label="Ventas" value={resultado?.ventas_creadas || 0} color="green" />
      </SimpleGrid>

      {/* Error details */}
      {hasErrors && (
        <Box>
          <Accordion allowToggle>
            <AccordionItem
              border="1px solid"
              borderColor="yellow.200"
              borderRadius="xl"
              overflow="hidden"
            >
              <AccordionButton px={5} py={3} bg="yellow.50" _hover={{ bg: 'yellow.100' }}>
                <HStack flex={1} spacing={2}>
                  <Icon as={FiAlertTriangle} boxSize={4} color="yellow.500" />
                  <Text fontSize="sm" fontWeight="medium" color="yellow.700">
                    {errores.length} filas con error — no fueron importadas
                  </Text>
                </HStack>
                <AccordionIcon />
              </AccordionButton>
              <AccordionPanel p={0}>
                <TableContainer maxH="220px" overflowY="auto">
                  <Table size="sm" variant="simple">
                    <Thead>
                      <Tr>
                        <Th fontSize="10px">Hoja</Th>
                        <Th fontSize="10px">Fila</Th>
                        <Th fontSize="10px">Producto</Th>
                        <Th fontSize="10px">Error</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {errores.map((e, i) => (
                        <Tr key={i}>
                          <Td fontSize="11px">{e.hoja}</Td>
                          <Td fontSize="11px">{e.fila}</Td>
                          <Td fontSize="11px" maxW="120px">
                            <Text isTruncated>{e.producto}</Text>
                          </Td>
                          <Td fontSize="11px" maxW="200px">
                            <Text isTruncated color="red.500">{e.error}</Text>
                          </Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                </TableContainer>
              </AccordionPanel>
            </AccordionItem>
          </Accordion>
        </Box>
      )}

      {/* Actions */}
      <HStack spacing={3} justify="end">
        {hasErrors && (
          <Button
            size="sm"
            variant="outline"
            leftIcon={<FiDownload />}
            onClick={downloadErrorReport}
          >
            Descargar reporte de errores
          </Button>
        )}
        <Button
          size="sm"
          variant="outline"
          onClick={onReset}
        >
          Nueva importación
        </Button>
        <Button
          size="sm"
          colorScheme="blue"
          rightIcon={<FiArrowRight />}
          onClick={() => navigate('/app/inventario')}
        >
          Ir a inventario
        </Button>
      </HStack>
    </VStack>
  );
}
