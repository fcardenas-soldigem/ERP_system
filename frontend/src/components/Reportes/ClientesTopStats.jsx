import React, { useEffect, useState } from 'react';
import { Box, Heading, Spinner, Select, HStack } from '@chakra-ui/react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';
import { ventasService } from '../../services/ventas.service';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const ClientesTopStats = () => {
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tipoRanking, setTipoRanking] = useState('facturacion'); // 'facturacion' o 'cantidad'

  useEffect(() => {
    setLoading(true);
    ventasService.getMejoresClientes()
      .then(data => {
        let ranking = tipoRanking === 'facturacion' ? data.ranking_facturacion : data.ranking_recurrencia;
        setChartData({
          labels: ranking.map(c => c.cliente__nombre),
          datasets: [
            {
              label: tipoRanking === 'facturacion' ? 'Total Facturado (S/)' : 'Cantidad de Compras',
              data: tipoRanking === 'facturacion' ? ranking.map(c => c.total_facturado) : ranking.map(c => c.cantidad_compras),
              backgroundColor: 'rgba(255, 159, 64, 0.6)',
              borderColor: 'rgba(255, 159, 64, 1)',
              borderWidth: 1
            }
          ]
        });
        setLoading(false);
      })
      .catch(() => {
        setChartData(null);
        setLoading(false);
      });
  }, [tipoRanking]);

  if (loading) return <Spinner size="md" />;
  if (!chartData) return <Box>No hay datos de clientes.</Box>;

  return (
    <Box p={4} borderWidth={1} borderRadius="md">
      <HStack mb={2} spacing={4}>
        <Heading size="md">Mejores Clientes</Heading>
        <Select value={tipoRanking} onChange={e => setTipoRanking(e.target.value)} w="auto">
          <option value="facturacion">Facturación</option>
          <option value="cantidad">Cantidad de compras</option>
        </Select>
      </HStack>
      <Bar 
        data={chartData} 
        options={{ 
          responsive: true, 
          plugins: { legend: { position: 'top' } },
          animation: {
            duration: 1200,
            easing: 'easeOutQuart'
          }
        }} 
      />
    </Box>
  );
};

export default ClientesTopStats; 