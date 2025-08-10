import React, { useEffect, useState } from 'react';
import { Box, Heading, Spinner } from '@chakra-ui/react';
import { dashboardService } from '../../services/dashboard.service';

const InventarioReport = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboardService.getInventarioData()
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner size="md" />;

  return (
    <Box p={4} borderWidth={1} borderRadius="md">
      <Heading size="md" mb={2}>Inventario</Heading>
      {/* Aquí puedes agregar un gráfico o tabla, por ahora solo mostramos los datos */}
      <pre style={{ fontSize: 12 }}>{JSON.stringify(data, null, 2)}</pre>
    </Box>
  );
};

export default InventarioReport; 