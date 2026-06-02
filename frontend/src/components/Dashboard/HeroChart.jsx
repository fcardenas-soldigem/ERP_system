import React, { useState, useMemo } from 'react';
import {
  Box, Flex, Text, HStack, Button, Skeleton,
  useColorModeValue,
} from '@chakra-ui/react';
import {
  ResponsiveContainer, AreaChart, Area, XAxis, Tooltip,
} from 'recharts';
import { api } from '../../lib/api';

const PERIODS = [
  { label: '7D',  mode: 'weekly' },
  { label: '30D', mode: 'monthly' },
  { label: '3M',  mode: 'quarter' },
  { label: '1A',  mode: 'annual' },
];

// ─── Custom dark tooltip ──────────────────────────────────────────────────────
const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <Box
      bg="gray.900"
      color="white"
      px={3}
      py={2}
      borderRadius="md"
      fontSize="sm"
      boxShadow="lg"
      pointerEvents="none"
    >
      <Text fontWeight="semibold" fontVariantNumeric="tabular-nums">
        S/ {Number(payload[0].value).toLocaleString('es-PE', { minimumFractionDigits: 2 })}
      </Text>
      <Text fontSize="xs" color="gray.400">{label}</Text>
    </Box>
  );
};

// ─── HeroChart ────────────────────────────────────────────────────────────────
const HeroChart = ({ resumen }) => {
  const [period, setPeriod]   = useState(PERIODS[1]);   // default 30D
  const [data, setData]       = useState([]);
  const [loading, setLoading] = useState(false);
  const [hovered, setHovered] = useState(null);

  const borderColor = useColorModeValue('gray.100', 'gray.700');

  // ── Load data according to selected period ────────────────────────────────
  React.useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      try {
        const now = new Date();
        let raw = [], labels = [];

        if (period.mode === 'annual') {
          // 1A: call ventas/anual/ — returns { labels: ['Ene','Feb',...], data: [...] }
          const res = await api.get('/api/dashboard/ventas/anual/', {
            params: { year: now.getFullYear() },
          });
          raw    = res.data.data   ?? [];
          labels = res.data.labels ?? [];
        } else if (period.mode === 'quarter') {
          // 3M: fetch 3 consecutive months and concatenate
          const months = [];
          for (let i = 2; i >= 0; i--) {
            const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
            months.push({ year: d.getFullYear(), month: d.getMonth() + 1 });
          }
          const results = await Promise.all(months.map(({ year, month }) =>
            api.get('/api/dashboard/ventas/mensual/', { params: { year, month } })
              .then(r => ({ data: r.data.data ?? [], labels: r.data.labels ?? [] }))
          ));
          results.forEach(({ data: d, labels: l }) => {
            raw.push(...d);
            labels.push(...l);
          });
        } else if (period.mode === 'weekly') {
          // 7D: use current month data sliced to last 7 non-zero entries
          const res = await api.get('/api/dashboard/ventas/mensual/', {
            params: { year: now.getFullYear(), month: now.getMonth() + 1 },
          });
          const fullData   = res.data.data   ?? [];
          const fullLabels = res.data.labels ?? [];
          // Slice to last 7 days of the current date
          const today = now.getDate();
          raw    = fullData.slice(Math.max(0, today - 7), today);
          labels = fullLabels.slice(Math.max(0, today - 7), today);
        } else {
          // 30D (monthly): full current month
          const res = await api.get('/api/dashboard/ventas/mensual/', {
            params: { year: now.getFullYear(), month: now.getMonth() + 1 },
          });
          raw    = res.data.data   ?? [];
          labels = res.data.labels ?? [];
        }

        if (!cancelled) {
          setData(raw.map((v, i) => ({ label: labels[i] ?? String(i + 1), value: v })));
        }
      } catch {
        if (!cancelled) setData([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [period]);

  // ── Compute trend from data: compare second half vs first half ────────────
  const { isPositive, totalFromData } = useMemo(() => {
    if (!data.length) return { isPositive: true, totalFromData: 0 };
    const mid  = Math.floor(data.length / 2);
    const first  = data.slice(0, mid).reduce((s, d) => s + d.value, 0);
    const second = data.slice(mid).reduce((s, d) => s + d.value, 0);
    return {
      isPositive: second >= first,
      totalFromData: data.reduce((s, d) => s + d.value, 0),
    };
  }, [data]);

  const lineColor = isPositive ? '#22c55e' : '#ef4444';
  const fillId    = isPositive ? 'fill-green' : 'fill-red';

  // Display value: hover shows point value, otherwise use resumen total
  const ventas       = resumen?.ventas ?? {};
  const resumenTotal = ventas.total ?? 0;
  const cantidad     = ventas.cantidad ?? 0;
  const displayValue = hovered !== null ? hovered : resumenTotal;

  return (
    <Box
      bg="white"
      borderRadius="xl"
      border="1px solid"
      borderColor={borderColor}
      p={6}
    >
      {/* ── Header — stacked on mobile to avoid compression ── */}
      <Flex
        direction={{ base: 'column', sm: 'row' }}
        justify="space-between"
        align={{ base: 'flex-start', sm: 'flex-start' }}
        gap={3}
        mb={1}
      >
        <Box>
          <Text
            fontSize="10px"
            fontWeight="semibold"
            color="gray.400"
            textTransform="uppercase"
            letterSpacing="wider"
            mb={1}
          >
            Ventas del mes
          </Text>
          <Text
            fontSize="3xl"
            fontWeight="bold"
            color={lineColor}
            fontVariantNumeric="tabular-nums"
            lineHeight="1"
            transition="color 0.3s"
          >
            S/ {Number(displayValue).toLocaleString('es-PE', { minimumFractionDigits: 2 })}
          </Text>
          <Text fontSize="xs" color="gray.400" mt={1}>
            {cantidad} transacciones este mes
          </Text>
        </Box>

        {/* Period pills — on their own row in mobile (F-005 fix) */}
        <HStack spacing={1} flexShrink={0}>
          {PERIODS.map(p => (
            <Button
              key={p.label}
              size="xs"
              variant={period.label === p.label ? 'solid' : 'ghost'}
              colorScheme={period.label === p.label ? 'blue' : 'gray'}
              borderRadius="full"
              fontWeight="medium"
              onClick={() => setPeriod(p)}
              px={3}
              minW="32px"
            >
              {p.label}
            </Button>
          ))}
        </HStack>
      </Flex>

      {/* ── Area chart ── */}
      <Box h="140px" mt={4}>
        {loading ? (
          <Skeleton h="100%" borderRadius="md" />
        ) : data.length === 0 ? (
          <Flex h="100%" align="center" justify="center">
            <Text fontSize="xs" color="gray.300">Sin datos para el período</Text>
          </Flex>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={data}
              margin={{ top: 4, right: 0, left: 0, bottom: 0 }}
              onMouseMove={(e) => {
                if (e?.activePayload?.[0]) setHovered(e.activePayload[0].value);
              }}
              onMouseLeave={() => setHovered(null)}
            >
              <defs>
                <linearGradient id="fill-green" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#22c55e" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="fill-red" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#ef4444" stopOpacity={0.12} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>

              <XAxis
                dataKey="label"
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 10, fill: '#9ca3af' }}
                interval="preserveStartEnd"
              />
              <Tooltip
                content={<CustomTooltip />}
                cursor={{ stroke: '#e5e7eb', strokeWidth: 1, strokeDasharray: '4 2' }}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke={lineColor}
                strokeWidth={2}
                fill={`url(#${fillId})`}
                dot={false}
                activeDot={{ r: 4, fill: lineColor, strokeWidth: 0 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </Box>
    </Box>
  );
};

export default HeroChart;
