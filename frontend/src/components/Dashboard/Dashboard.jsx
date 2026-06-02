import React from 'react';
import {
  Box, Flex, Text, SimpleGrid, useColorModeValue,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';

// Dashboard sub-components
import QuickActions       from '../dashboard/QuickActions';
import HeroChart          from '../dashboard/HeroChart';
import StatCardsCarousel  from '../dashboard/StatCardsCarousel';
import RecentSales        from '../dashboard/RecentSales';
import TopProducts        from '../dashboard/TopProducts';
import AlertsBar          from '../dashboard/AlertsBar';
import { DashboardSkeleton } from '../common/SkeletonLoaders';
import ServiciosWidget    from '../Servicios/ServiciosWidget';

// ─── Formatters ───────────────────────────────────────────────────────────────
const fmt  = (n, d = 2) => typeof n === 'number'
  ? n.toLocaleString('es-PE', { minimumFractionDigits: d, maximumFractionDigits: d })
  : '—';
const fmtI = (n) => typeof n === 'number'
  ? n.toLocaleString('es-PE', { maximumFractionDigits: 0 })
  : '—';

// ─── Build alert list from resumen ────────────────────────────────────────────
const buildAlerts = (resumen) => {
  const alerts = [];
  const iv     = resumen?.inventario ?? {};
  const ig     = resumen?.impuestos  ?? {};
  const cuentas = resumen?.cuentas   ?? {};

  if ((iv.productos_bajo_stock ?? 0) > 0) {
    alerts.push({
      level: 'urgent',
      message: `${iv.productos_bajo_stock} producto${iv.productos_bajo_stock > 1 ? 's' : ''} bajo el stock mínimo`,
      actionLabel: 'Ver inventario',
      actionPath: '/app/inventario',
    });
  }

  if ((ig.por_pagar ?? 0) > 500) {
    alerts.push({
      level: 'warning',
      message: `IGV por declarar: S/ ${fmt(ig.por_pagar)} (ventas − compras del mes)`,
      actionLabel: 'Ver cuentas',
      actionPath: '/app/cuentas/por-cobrar',
    });
  }

  if ((cuentas.compras_borrador_count ?? 0) > 0) {
    alerts.push({
      level: 'warning',
      message: `${cuentas.compras_borrador_count} compra${cuentas.compras_borrador_count > 1 ? 's' : ''} en borrador (S/ ${fmt(cuentas.compras_borrador_total ?? 0)}) no están incluidas en la utilidad. Apruébalas para ver la utilidad real.`,
      actionLabel: 'Ver compras',
      actionPath: '/app/compras',
    });
  }

  return alerts;
};

// ─── Dashboard ────────────────────────────────────────────────────────────────
const Dashboard = () => {
  const bg = useColorModeValue('gray.50', 'gray.900');

  const { data: resumen, isLoading } = useQuery({
    queryKey: ['dashboard-resumen'],
    queryFn: () => api.get('/api/dashboard/resumen/').then(r => r.data),
    staleTime: 2 * 60 * 1000,
  });

  // Also fetch utility data for sparklines (daily data for current month)
  const { data: utilData } = useQuery({
    queryKey: ['dashboard-utility'],
    queryFn: () => {
      const now = new Date();
      return api.get('/api/dashboard/utility/', {
        params: { year: now.getFullYear(), month: now.getMonth() + 1 },
      }).then(r => r.data);
    },
    staleTime: 5 * 60 * 1000,
  });

  // Finanzas: resumen de gastos del mes actual (para mostrar utilidad neta si hay gastos)
  const { data: resumenFinanzas } = useQuery({
    queryKey: ['finanzas-resumen-gastos'],
    queryFn: () => {
      const now = new Date();
      const fecha = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
      return api.get('/api/finanzas/gastos/resumen/', { params: { fecha } }).then(r => r.data);
    },
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) return <DashboardSkeleton />;

  const v      = resumen?.ventas    ?? {};
  const c      = resumen?.compras   ?? {};
  const u      = resumen?.utilidad  ?? {};
  const ig     = resumen?.impuestos ?? {};
  const iv     = resumen?.inventario ?? {};
  const cuentas = resumen?.cuentas  ?? {};

  // Sparkline data: last 7 values from daily utility data
  const ventasSpark  = (utilData?.ventas     ?? []).slice(-7);
  const comprasSpark = (utilData?.compras    ?? []).slice(-7);
  const utilSpark    = (utilData?.utilidades ?? []).slice(-7);
  const stockNum     = iv.productos_bajo_stock ?? 0;

  // Utilidad neta vs bruta según disponibilidad de gastos registrados
  const hayGastos        = (resumenFinanzas?.total_gastos ?? 0) > 0;
  const utilidadNeta     = resumenFinanzas?.utilidad_neta_del_periodo;
  const utilidadDisplay  = hayGastos && utilidadNeta != null ? utilidadNeta : (u.total ?? 0);
  const utilidadLabel    = hayGastos && utilidadNeta != null
    ? `Margen neto ${resumenFinanzas?.margen_neto_pct ?? 0}%`
    : `Utilidad bruta* · sin gastos op.`;

  const statCards = [
    {
      label:       'Por cobrar',
      value:       `S/ ${fmt(cuentas.por_cobrar ?? 0)}`,
      sub:         'Ventas pendientes de cobro',
      sparkData:   ventasSpark,
      accentColor: '#f59e0b',
    },
    {
      label:       'Por pagar',
      value:       `S/ ${fmt(cuentas.por_pagar ?? 0)}`,
      sub:         'Compras pendientes de pago',
      sparkData:   comprasSpark,
      accentColor: '#7c3aed',
    },
    {
      label:       'Utilidad del mes',
      value:       `S/ ${fmt(utilidadDisplay)}`,
      sub:         utilidadLabel,
      sparkData:   utilSpark,
      trend:       hayGastos ? (resumenFinanzas?.margen_neto_pct ?? undefined) : (u.margen ?? undefined),
      accentColor: '#22c55e',
    },
    {
      label:      'Stock crítico',
      value:      `${fmtI(iv.total_productos ?? 0)} productos`,
      sub:        `${fmtI(iv.total_cantidad ?? 0)} unidades totales`,
      sparkData:  [],
      alert:      stockNum > 0 ? `${stockNum} bajo mínimo` : undefined,
      pulseBadge: stockNum > 0,
      accentColor:'#ef4444',
    },
  ];

  const alerts = buildAlerts(resumen);

  return (
    <Box bg={bg} minH="100vh" px={{ base: 4, md: 6 }} py={6}>

      {/* ── Header ── */}
      <Flex justify="space-between" align="center" mb={5}>
        <Text fontSize="lg" fontWeight="semibold" color="gray.800">
          Dashboard
        </Text>
        <Text fontSize="xs" color="gray.400">Últimos 30 días</Text>
      </Flex>

      {/* ── Sección 0: Quick Actions ── */}
      <Box mb={6}>
        <QuickActions />
      </Box>

      {/* ── Alertas (si existen) ── */}
      {alerts.length > 0 && (
        <Box mb={6}>
          <AlertsBar alerts={alerts} />
        </Box>
      )}

      {/* ── Sección 1: Hero Chart (ventas del mes) ── */}
      <Box mb={6}>
        <HeroChart resumen={resumen} />
      </Box>

      {/* ── Sección 2: Stat Cards (4 métricas clave) ── */}
      <Box mb={6}>
        <StatCardsCarousel cards={statCards} />
      </Box>

      {/* ── Sección 3: Dos columnas — últimas ventas + top productos ── */}
      <SimpleGrid columns={{ base: 1, lg: 5 }} spacing={6} mb={6}>
        {/* 60%: tabla de ventas recientes */}
        <Box gridColumn={{ lg: 'span 3' }}>
          <RecentSales />
        </Box>

        {/* 40%: ranking de productos */}
        <Box gridColumn={{ lg: 'span 2' }}>
          <TopProducts />
        </Box>
      </SimpleGrid>

      {/* ── Sección 4: Widget Órdenes de Servicio ── */}
      <SimpleGrid columns={{ base: 1, lg: 3 }} spacing={6}>
        <Box gridColumn={{ lg: 'span 1' }}>
          <ServiciosWidget />
        </Box>
      </SimpleGrid>

    </Box>
  );
};

export default Dashboard;
