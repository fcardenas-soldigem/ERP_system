import React, { useEffect, useState } from 'react';
import { Box, Heading, Spinner, Select, HStack, Button, ButtonGroup } from '@chakra-ui/react';
import { Line } from 'react-chartjs-2';
import { dashboardService } from '../../services/dashboard.service';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

const getYears = () => {
  const now = new Date();
  const years = [];
  for (let y = now.getFullYear(); y >= now.getFullYear() - 5; y--) {
    years.push(y);
  }
  return years;
};

const MONTHS = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

const UtilidadStats = () => {
  const now = new Date();
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [year, setYear] = useState(now.getFullYear());
  const [viewMode, setViewMode] = useState('monthly'); // 'monthly' o 'annual'

  const loadData = async () => {
    setLoading(true);
    try {
      let data;
      if (viewMode === 'annual') {
        data = await dashboardService.getUtilidadAnual(year);
        setChartData({
          labels: data.labels,
          datasets: [
            {
              label: 'Utilidad Mensual',
              data: data.utilidades,
              borderColor: 'rgba(75,192,192,1)',
              backgroundColor: 'rgba(75,192,192,0.2)',
              fill: true,
              tension: 0.4
            },
            {
              label: 'Ventas Mensual',
              data: data.ventas,
              borderColor: 'rgba(54, 162, 235, 1)',
              backgroundColor: 'rgba(54, 162, 235, 0.1)',
              fill: false,
              tension: 0.4
            },
            {
              label: 'Compras Mensual',
              data: data.compras,
              borderColor: 'rgba(255, 99, 132, 1)',
              backgroundColor: 'rgba(255, 99, 132, 0.1)',
              fill: false,
              tension: 0.4
            }
          ]
        });
      } else {
        data = await dashboardService.getUtilityData(year, month);
        setChartData({
          labels: data.labels,
          datasets: [
            {
              label: 'Utilidad Diaria',
              data: data.utilidades,
              borderColor: 'rgba(75,192,192,1)',
              backgroundColor: 'rgba(75,192,192,0.2)',
              fill: true,
              tension: 0.4
            }
          ]
        });
      }
    } catch (error) {
      console.error('Error al cargar datos de utilidad:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [month, year, viewMode]);

  if (loading) return <Spinner size="md" />;
  if (!chartData) return <Box>No hay datos de utilidad.</Box>;

  return (
    <Box p={4} borderWidth={1} borderRadius="md">
      <HStack mb={4} spacing={4} align="center" wrap="wrap">
        <Heading size="md">
          {viewMode === 'annual' ? 'Utilidad Anual' : 'Utilidad Diaria'}
        </Heading>
        
        <ButtonGroup size="sm" isAttached variant="outline">
          <Button 
            colorScheme={viewMode === 'monthly' ? 'blue' : 'gray'}
            onClick={() => setViewMode('monthly')}
          >
            Mensual
          </Button>
          <Button 
            colorScheme={viewMode === 'annual' ? 'blue' : 'gray'}
            onClick={() => setViewMode('annual')}
          >
            Anual
          </Button>
        </ButtonGroup>

        {viewMode === 'monthly' && (
          <Select value={month} onChange={e => setMonth(Number(e.target.value))} w="auto">
            {MONTHS.map((name, i) => (
              <option key={i + 1} value={i + 1}>{name}</option>
            ))}
          </Select>
        )}
        
        <Select value={year} onChange={e => setYear(Number(e.target.value))} w="auto">
          {getYears().map(y => (
            <option key={y} value={y}>{y}</option>
          ))}
        </Select>
      </HStack>
      
      <Box>
        <Line 
          data={chartData} 
          options={{ 
            responsive: true, 
            plugins: { 
              legend: { position: 'top' },
              title: {
                display: true,
                text: viewMode === 'annual' 
                  ? `Utilidad, Ventas y Compras por mes - ${year}`
                  : `Utilidad por día - ${MONTHS[month - 1]} ${year}`
              }
            },
            scales: {
              y: {
                beginAtZero: true,
                ticks: {
                  callback: function(value) {
                    return 'S/ ' + value.toLocaleString('es-PE');
                  }
                }
              }
            },
            animation: {
              duration: 1200,
              easing: 'easeOutQuart'
            }
          }} 
        />
      </Box>
    </Box>
  );
};

export default UtilidadStats; 