import React, { useEffect, useState } from 'react';
import { Box, Heading, Spinner, Table, Thead, Tbody, Tr, Th, Td } from '@chakra-ui/react';
import { dashboardService } from '../../services/dashboard.service';

const UtilidadStats = () => {
  const [utilidades, setUtilidades] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const now = new Date();
    dashboardService.getUtilityData(now.getFullYear(), now.getMonth() + 1)
      .then(data => {
        // data.labels = días, data.utilidades = utilidad diaria
        const rows = data.labels.map((label, idx) => ({ dia: label, utilidad: data.utilidades[idx] }));
        setUtilidades(rows);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner size="md" />;

  return (
    <Box p={4} borderWidth={1} borderRadius="md">
      <Heading size="md" mb={4}>Utilidad Diaria (mes actual)</Heading>
      <Table size="sm">
        <Thead>
          <Tr>
            <Th>Día</Th>
            <Th isNumeric>Utilidad</Th>
          </Tr>
        </Thead>
        <Tbody>
          {utilidades.map((item, idx) => (
            <Tr key={idx}>
              <Td>{item.dia}</Td>
              <Td isNumeric>S/ {item.utilidad}</Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
    </Box>
  );
};

export default UtilidadStats; 