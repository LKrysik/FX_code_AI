'use client';

/**
 * Drawdown Chart Component - TIER 2.1
 * ====================================
 * Displays drawdown progression during paper trading sessions.
 *
 * Features:
 * - Area chart showing current_drawdown over time
 * - Max drawdown reference line
 * - Color-coded severity (green < 5%, yellow < 15%, red >= 15%)
 * - Tooltip with timestamp and drawdown values
 * - Risk level indicators
 */

import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { Box, Typography, Paper, Chip } from '@mui/material';
import { TrendingDown as TrendingDownIcon } from '@mui/icons-material';

interface PerformanceSnapshot {
  timestamp: string;
  current_drawdown: number;
  max_drawdown: number;
}

interface DrawdownChartProps {
  data: PerformanceSnapshot[];
}

export default function DrawdownChart({ data }: DrawdownChartProps) {
  if (!data || data.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          No drawdown data available yet. Data will appear as the session progresses.
        </Typography>
      </Paper>
    );
  }

  // Format data for chart
  const chartData = data.map((snapshot) => ({
    timestamp: new Date(snapshot.timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    }),
    currentDrawdown: Math.abs(snapshot.current_drawdown), // Show as positive for better visualization
    maxDrawdown: Math.abs(snapshot.max_drawdown),
  }));

  // Calculate max drawdown for the session
  const maxDrawdownValue = Math.max(...chartData.map((d) => d.maxDrawdown), 0);
  const currentDrawdownValue = chartData[chartData.length - 1]?.currentDrawdown || 0;

  // Determine severity level
  const getSeverityLevel = (drawdown: number): 'low' | 'medium' | 'high' => {
    if (drawdown < 5) return 'low';
    if (drawdown < 15) return 'medium';
    return 'high';
  };

  const getSeverityColor = (level: 'low' | 'medium' | 'high'): string => {
    switch (level) {
      case 'low':
        return '#4caf50';
      case 'medium':
        return '#ff9800';
      case 'high':
        return '#f44336';
    }
  };

  const severityLevel = getSeverityLevel(maxDrawdownValue);
  const severityColor = getSeverityColor(severityLevel);

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <Paper sx={{ p: 1.5, bgcolor: 'background.paper', border: 1, borderColor: 'divider' }}>
          <Typography variant="caption" color="text.secondary">
            {data.timestamp}
          </Typography>
          <Typography variant="body2" fontWeight="bold">
            Current Drawdown: {data.currentDrawdown.toFixed(2)}%
          </Typography>
          <Typography variant="body2" color="error.main">
            Max Drawdown: {data.maxDrawdown.toFixed(2)}%
          </Typography>
        </Paper>
      );
    }
    return null;
  };

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <TrendingDownIcon sx={{ mr: 1, color: 'error.main' }} />
          <Typography variant="h6">Drawdown Analysis</Typography>
        </Box>
        <Chip
          label={`Risk: ${severityLevel.toUpperCase()}`}
          color={severityLevel === 'low' ? 'success' : severityLevel === 'medium' ? 'warning' : 'error'}
          size="small"
        />
      </Box>

      <ResponsiveContainer width="100%" height={300}>
        <AreaChart
          data={chartData}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <defs>
            <linearGradient id="colorDrawdown" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={severityColor} stopOpacity={0.8} />
              <stop offset="95%" stopColor={severityColor} stopOpacity={0.1} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
          <XAxis
            dataKey="timestamp"
            stroke="#666"
            style={{ fontSize: '12px' }}
          />
          <YAxis
            stroke="#666"
            style={{ fontSize: '12px' }}
            tickFormatter={(value) => `${value.toFixed(0)}%`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />

          {/* Risk level reference lines */}
          <ReferenceLine
            y={5}
            stroke="#4caf50"
            strokeDasharray="5 5"
            label={{
              value: 'Low Risk (5%)',
              position: 'right',
              fill: '#4caf50',
              fontSize: 11,
            }}
          />
          <ReferenceLine
            y={15}
            stroke="#ff9800"
            strokeDasharray="5 5"
            label={{
              value: 'High Risk (15%)',
              position: 'right',
              fill: '#ff9800',
              fontSize: 11,
            }}
          />

          {/* Drawdown area */}
          <Area
            type="monotone"
            dataKey="currentDrawdown"
            stroke={severityColor}
            strokeWidth={2}
            fill="url(#colorDrawdown)"
            name="Current Drawdown (%)"
          />
        </AreaChart>
      </ResponsiveContainer>

      {/* Summary stats */}
      <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-around' }}>
        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            Current Drawdown
          </Typography>
          <Typography
            variant="body2"
            fontWeight="bold"
            color={currentDrawdownValue < 5 ? 'success.main' : currentDrawdownValue < 15 ? 'warning.main' : 'error.main'}
          >
            {currentDrawdownValue.toFixed(2)}%
          </Typography>
        </Box>
        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            Max Drawdown
          </Typography>
          <Typography
            variant="body2"
            fontWeight="bold"
            color={maxDrawdownValue < 5 ? 'success.main' : maxDrawdownValue < 15 ? 'warning.main' : 'error.main'}
          >
            {maxDrawdownValue.toFixed(2)}%
          </Typography>
        </Box>
        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            Risk Assessment
          </Typography>
          <Typography variant="body2" fontWeight="bold">
            {severityLevel === 'low' ? '✓ Acceptable' : severityLevel === 'medium' ? '⚠ Moderate' : '⛔ High'}
          </Typography>
        </Box>
      </Box>
    </Paper>
  );
}
