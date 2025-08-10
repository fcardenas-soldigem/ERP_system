import React, { useEffect, useState } from 'react';
import { Box, Heading, Spinner, Select, HStack } from '@chakra-ui/react';
import { Pie } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend
} from 'chart.js';
import { ventasService } from '../../services/ventas.service';

ChartJS.register(ArcElement, Tooltip, Legend);

const ProductosTopStats = () => {
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('historico');

  useEffect(() => {
    setLoading(true);
    ventasService.getProductosMasVendidos(period)
      .then(data => {
        setChartData({
          labels: data.labels,
          datasets: [
            {
              label: 'Cantidad vendida',
              data: data.data,
              backgroundColor: [
                'rgba(255, 99, 132, 0.6)',
                'rgba(54, 162, 235, 0.6)',
                'rgba(255, 206, 86, 0.6)',
                'rgba(75, 192, 192, 0.6)',
                'rgba(153, 102, 255, 0.6)',
                'rgba(255, 159, 64, 0.6)',
                'rgba(199, 199, 199, 0.6)',
                'rgba(83, 102, 255, 0.6)',
                'rgba(255, 99, 71, 0.6)',
                'rgba(60, 179, 113, 0.6)'
              ],
              borderColor: [
                'rgba(255, 99, 132, 1)',
                'rgba(54, 162, 235, 1)',
                'rgba(255, 206, 86, 1)',
                'rgba(75, 192, 192, 1)',
                'rgba(153, 102, 255, 1)',
                'rgba(255, 159, 64, 1)',
                'rgba(199, 199, 199, 1)',
                'rgba(83, 102, 255, 1)',
                'rgba(255, 99, 71, 1)',
                'rgba(60, 179, 113, 1)'
              ],
              borderWidth: 1
            }
          ]
        });
      })
      .finally(() => setLoading(false));
  }, [period]);

  if (loading) return <Spinner size="md" />;
  if (!chartData || !chartData.labels || chartData.labels.length === 0) return <Box>No hay datos de productos.</Box>;

  return (
    <Box p={4} borderWidth={1} borderRadius="md">
      <HStack mb={2} spacing={4}>
        <Heading size="md">Productos Más Vendidos</Heading>
        <Select value={period} onChange={e => setPeriod(e.target.value)} w="auto">
          <option value="historico">Histórico</option>
          <option value="mes">Mes actual</option>
        </Select>
      </HStack>
      <Pie 
        data={chartData} 
        options={{ 
          responsive: true, 
          plugins: { legend: { position: 'right' } },
          animation: {
            animateRotate: true,
            animateScale: true,
            duration: 1200,
            easing: 'easeOutQuart'
          }
        }} 
      />
    </Box>
  );
};

export default ProductosTopStats; 