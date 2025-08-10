import React, { useEffect, useState } from 'react';
import { Box, Heading, Spinner, Table, Thead, Tbody, Tr, Th, Td } from '@chakra-ui/react';
import { dashboardService } from '../../services/dashboard.service';

const VentasStats = () => {
  const [ventas, setVentas] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboardService.getVentasData()
      .then(data => {
        // data.labels = meses o días, data.data = montos
        const rows = data.labels.map((label, idx) => ({ fecha: label, total: data.data[idx] }));
        setVentas(rows);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner size="md" />;

  return (
    <Box p={4} borderWidth={1} borderRadius="md">
      <Heading size="md" mb={4}>Estadísticas de Ventas (últimos 30 días)</Heading>
      <Table size="sm">
        <Thead>
          <Tr>
            <Th>Fecha</Th>
            <Th isNumeric>Monto Total</Th>
          </Tr>
        </Thead>
        <Tbody>
          {ventas.map((venta, idx) => (
            <Tr key={idx}>
              <Td>{venta.fecha}</Td>
              <Td isNumeric>S/ {venta.total}</Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
    </Box>
  );
};

export default VentasStats; 