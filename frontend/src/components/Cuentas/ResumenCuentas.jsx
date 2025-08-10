import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Stack,
  LinearProgress,
  Divider
} from '@mui/material';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import PaidIcon from '@mui/icons-material/Paid';
import ReceiptLongIcon from '@mui/icons-material/ReceiptLong';
import { useNavigate } from 'react-router-dom';

const ResumenCuentas = () => {
  const [resumen, setResumen] = useState({
    total_por_cobrar: 0,
    total_por_pagar: 0,
    ventas_pendientes: 0,
    compras_pendientes: 0,
    proximos_vencimientos_cobrar: [],
    proximos_vencimientos_pagar: []
  });
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchResumen();
  }, []);

  const fetchResumen = async () => {
    try {
      const response = await fetch('/api/cuentas/resumen/');
      const data = await response.json();
      setResumen(data);
    } catch (error) {
      console.error('Error al obtener el resumen:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('es-PE', {
      style: 'currency',
      currency: 'PEN'
    }).format(amount);
  };

  if (loading) {
    return (
      <Box sx={{ width: '100%', mt: 2 }}>
        <LinearProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Resumen de Cuentas
      </Typography>

      <Grid container spacing={3}>
        {/* Tarjetas de resumen */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Stack direction="row" spacing={2} alignItems="center">
                <AccountBalanceIcon color="primary" sx={{ fontSize: 40 }} />
                <Box>
                  <Typography variant="h6" gutterBottom>
                    Balance General
                  </Typography>
                  <Typography variant="h4" color="primary">
                    {formatCurrency(resumen.total_por_cobrar - resumen.total_por_pagar)}
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Stack direction="row" spacing={2} alignItems="center">
                <PaidIcon color="success" sx={{ fontSize: 40 }} />
                <Box>
                  <Typography variant="h6" gutterBottom>
                    Por Cobrar
                  </Typography>
                  <Typography variant="h4" color="success.main">
                    {formatCurrency(resumen.total_por_cobrar)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {resumen.ventas_pendientes} ventas pendientes
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Stack direction="row" spacing={2} alignItems="center">
                <ReceiptLongIcon color="error" sx={{ fontSize: 40 }} />
                <Box>
                  <Typography variant="h6" gutterBottom>
                    Por Pagar
                  </Typography>
                  <Typography variant="h4" color="error.main">
                    {formatCurrency(resumen.total_por_pagar)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {resumen.compras_pendientes} compras pendientes
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Acciones rápidas */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Acciones Rápidas
              </Typography>
              <Stack direction="row" spacing={2}>
                <Button
                  variant="contained"
                  color="primary"
                  onClick={() => navigate('/cuentas/por-cobrar')}
                >
                  Ver Cuentas por Cobrar
                </Button>
                <Button
                  variant="contained"
                  color="secondary"
                  onClick={() => navigate('/cuentas/por-pagar')}
                >
                  Ver Cuentas por Pagar
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Próximos vencimientos */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Próximos Vencimientos por Cobrar
              </Typography>
              <Divider sx={{ my: 2 }} />
              {resumen.proximos_vencimientos_cobrar.map((vencimiento) => (
                <Box key={vencimiento.id} sx={{ mb: 2 }}>
                  <Typography variant="subtitle1">
                    {vencimiento.cliente} - {formatCurrency(vencimiento.monto)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Vence el: {new Date(vencimiento.fecha_vencimiento).toLocaleDateString()}
                  </Typography>
                </Box>
              ))}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Próximos Vencimientos por Pagar
              </Typography>
              <Divider sx={{ my: 2 }} />
              {resumen.proximos_vencimientos_pagar.map((vencimiento) => (
                <Box key={vencimiento.id} sx={{ mb: 2 }}>
                  <Typography variant="subtitle1">
                    {vencimiento.proveedor} - {formatCurrency(vencimiento.monto)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Vence el: {new Date(vencimiento.fecha_vencimiento).toLocaleDateString()}
                  </Typography>
                </Box>
              ))}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default ResumenCuentas; 