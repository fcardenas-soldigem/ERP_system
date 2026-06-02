import React, { useId } from 'react';
import { ResponsiveContainer, AreaChart, Area } from 'recharts';

/**
 * Mini sparkline — 30px tall, no axes, no grid, no tooltip.
 * Uses useId() for stable unique SVG gradient IDs (F-006 fix).
 *
 * Props:
 *   data   number[]  — array of values
 *   color  string    — stroke/fill color
 *   height number    — component height in px (default 30)
 */
const Sparkline = ({ data = [], color = '#22c55e', height = 30 }) => {
  // useId() returns a stable, unique ID per component instance — prevents
  // SVG gradient ID collision when multiple Sparklines share the same color.
  const uid = useId().replace(/:/g, '');
  const gradientId = `spark-${uid}`;

  if (!data.length) return null;

  const chartData = data.map((v, i) => ({ v, i }));
  const min = Math.min(...data);
  const max = Math.max(...data);
  // Prevent flat-line rendering when all values are identical
  const domain = min === max ? [min - 1, max + 1] : [min * 0.95, max * 1.05];

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={chartData} margin={{ top: 2, right: 0, left: 0, bottom: 2 }}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor={color} stopOpacity={0.2} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="v"
          stroke={color}
          strokeWidth={1.5}
          fill={`url(#${gradientId})`}
          dot={false}
          activeDot={false}
          isAnimationActive={false}
          domain={domain}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
};

export default Sparkline;
