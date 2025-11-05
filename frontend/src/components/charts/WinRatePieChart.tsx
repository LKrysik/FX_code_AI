'use client';

/**
 * Win Rate Pie Chart Component - TIER 2.1
 * ========================================
 * Displays win/loss distribution for paper trading sessions.
 *
 * Features:
 * - Pie chart showing winning vs losing trades
 * - Win rate percentage display
 * - Color-coded segments (green for wins, red for losses)
 * - Tooltip with trade counts
 * - Trade statistics summary
 */

import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Box, Typography, Paper } from '@mui/material';
import { PieChart as PieChartIcon } from '@mui/icons-material';

interface PerformanceSnapshot {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
}

interface WinRatePieChartProps {
  data: PerformanceSnapshot | null;
}

export default function WinRatePieChart({ data }: WinRatePieChartProps) {
  if (!data || data.total_trades === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          No trades yet. Win/Loss distribution will appear after executing trades.
        </Typography>
      </Paper>
    );
  }

  // Prepare chart data
  const chartData = [
    {
      name: 'Winning Trades',
      value: data.winning_trades,
      percentage: (data.winning_trades / data.total_trades) * 100,
    },
    {
      name: 'Losing Trades',
      value: data.losing_trades,
      percentage: (data.losing_trades / data.total_trades) * 100,
    },
  ];

  const COLORS = {
    winning: '#4caf50',
    losing: '#f44336',
  };

  // Custom label
  const renderCustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }: any) => {
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    if (percent < 0.05) return null; // Don't show label if slice is too small

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor={x > cx ? 'start' : 'end'}
        dominantBaseline="central"
        fontWeight="bold"
        fontSize="14"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <Paper sx={{ p: 1.5, bgcolor: 'background.paper', border: 1, borderColor: 'divider' }}>
          <Typography variant="body2" fontWeight="bold">
            {data.name}
          </Typography>
          <Typography variant="body2">
            Count: {data.value}
          </Typography>
          <Typography variant="body2">
            Percentage: {data.percentage.toFixed(1)}%
          </Typography>
        </Paper>
      );
    }
    return null;
  };

  // Determine win rate quality
  const getWinRateQuality = (winRate: number): { label: string; color: string } => {
    if (winRate >= 60) return { label: 'Excellent', color: '#4caf50' };
    if (winRate >= 50) return { label: 'Good', color: '#8bc34a' };
    if (winRate >= 40) return { label: 'Fair', color: '#ff9800' };
    return { label: 'Poor', color: '#f44336' };
  };

  const winRateQuality = getWinRateQuality(data.win_rate);

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <PieChartIcon sx={{ mr: 1, color: 'primary.main' }} />
        <Typography variant="h6">Win/Loss Distribution</Typography>
      </Box>

      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={renderCustomLabel}
            outerRadius={100}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={index === 0 ? COLORS.winning : COLORS.losing}
              />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>

      {/* Summary stats */}
      <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-around' }}>
        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            Total Trades
          </Typography>
          <Typography variant="body2" fontWeight="bold">
            {data.total_trades}
          </Typography>
        </Box>
        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            Win Rate
          </Typography>
          <Typography
            variant="body2"
            fontWeight="bold"
            sx={{ color: winRateQuality.color }}
          >
            {data.win_rate.toFixed(1)}%
          </Typography>
        </Box>
        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            Performance
          </Typography>
          <Typography
            variant="body2"
            fontWeight="bold"
            sx={{ color: winRateQuality.color }}
          >
            {winRateQuality.label}
          </Typography>
        </Box>
      </Box>

      {/* Additional metrics */}
      <Box sx={{ mt: 2, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="body2">Winning Trades:</Typography>
          <Typography variant="body2" fontWeight="bold" color="success.main">
            {data.winning_trades} ({((data.winning_trades / data.total_trades) * 100).toFixed(1)}%)
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
          <Typography variant="body2">Losing Trades:</Typography>
          <Typography variant="body2" fontWeight="bold" color="error.main">
            {data.losing_trades} ({((data.losing_trades / data.total_trades) * 100).toFixed(1)}%)
          </Typography>
        </Box>
      </Box>
    </Paper>
  );
}
