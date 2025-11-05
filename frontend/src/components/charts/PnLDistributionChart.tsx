'use client';

/**
 * P&L Distribution Chart Component - TIER 2.1
 * ============================================
 * Displays profit/loss distribution statistics for paper trading sessions.
 *
 * Features:
 * - Bar chart showing average and largest wins/losses
 * - Color-coded bars (green for wins, red for losses)
 * - Tooltip with exact values
 * - Risk/reward ratio calculation
 * - Expectancy metric
 */

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts';
import { Box, Typography, Paper, Chip } from '@mui/material';
import { BarChart as BarChartIcon } from '@mui/icons-material';

interface PerformanceSnapshot {
  average_win: number;
  average_loss: number;
  largest_win: number;
  largest_loss: number;
  profit_factor: number;
  win_rate: number;
}

interface PnLDistributionChartProps {
  data: PerformanceSnapshot | null;
}

export default function PnLDistributionChart({ data }: PnLDistributionChartProps) {
  if (!data || (data.average_win === 0 && data.average_loss === 0)) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          No P&L data available yet. Distribution will appear after completing trades.
        </Typography>
      </Paper>
    );
  }

  // Prepare chart data
  const chartData = [
    {
      category: 'Avg Win',
      value: Math.abs(data.average_win),
      displayValue: `+$${Math.abs(data.average_win).toFixed(2)}`,
      type: 'win',
    },
    {
      category: 'Avg Loss',
      value: -Math.abs(data.average_loss),
      displayValue: `-$${Math.abs(data.average_loss).toFixed(2)}`,
      type: 'loss',
    },
    {
      category: 'Largest Win',
      value: Math.abs(data.largest_win),
      displayValue: `+$${Math.abs(data.largest_win).toFixed(2)}`,
      type: 'win',
    },
    {
      category: 'Largest Loss',
      value: -Math.abs(data.largest_loss),
      displayValue: `-$${Math.abs(data.largest_loss).toFixed(2)}`,
      type: 'loss',
    },
  ];

  const COLORS = {
    win: '#4caf50',
    loss: '#f44336',
  };

  // Calculate risk/reward ratio
  const riskRewardRatio = data.average_loss !== 0
    ? (data.average_win / Math.abs(data.average_loss)).toFixed(2)
    : 'N/A';

  // Calculate expectancy (average $ per trade)
  const expectancy = data.win_rate !== 0
    ? ((data.win_rate / 100) * data.average_win) - ((1 - data.win_rate / 100) * Math.abs(data.average_loss))
    : 0;

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <Paper sx={{ p: 1.5, bgcolor: 'background.paper', border: 1, borderColor: 'divider' }}>
          <Typography variant="body2" fontWeight="bold">
            {data.category}
          </Typography>
          <Typography
            variant="body2"
            color={data.type === 'win' ? 'success.main' : 'error.main'}
          >
            {data.displayValue}
          </Typography>
        </Paper>
      );
    }
    return null;
  };

  // Determine chart domain
  const maxAbsValue = Math.max(
    Math.abs(data.average_win),
    Math.abs(data.average_loss),
    Math.abs(data.largest_win),
    Math.abs(data.largest_loss)
  );
  const domain = [-maxAbsValue * 1.2, maxAbsValue * 1.2];

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <BarChartIcon sx={{ mr: 1, color: 'primary.main' }} />
          <Typography variant="h6">P&L Distribution</Typography>
        </Box>
        {expectancy !== 0 && (
          <Chip
            label={`Expectancy: ${expectancy >= 0 ? '+' : ''}$${expectancy.toFixed(2)}`}
            color={expectancy >= 0 ? 'success' : 'error'}
            size="small"
          />
        )}
      </Box>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart
          data={chartData}
          margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
          <XAxis
            dataKey="category"
            stroke="#666"
            style={{ fontSize: '12px' }}
          />
          <YAxis
            stroke="#666"
            style={{ fontSize: '12px' }}
            domain={domain}
            tickFormatter={(value) => `$${Math.abs(value).toFixed(0)}`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <ReferenceLine y={0} stroke="#999" strokeWidth={2} />
          <Bar
            dataKey="value"
            name="P&L Amount"
            label={{
              position: 'top',
              formatter: (value: number, entry: any) => entry.displayValue,
              fontSize: 11,
            }}
          >
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.type === 'win' ? COLORS.win : COLORS.loss}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Summary stats */}
      <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-around' }}>
        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            Risk/Reward Ratio
          </Typography>
          <Typography
            variant="body2"
            fontWeight="bold"
            color={parseFloat(riskRewardRatio.toString()) >= 1.5 ? 'success.main' : 'warning.main'}
          >
            {riskRewardRatio}
          </Typography>
        </Box>
        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            Profit Factor
          </Typography>
          <Typography
            variant="body2"
            fontWeight="bold"
            color={data.profit_factor >= 1.5 ? 'success.main' : data.profit_factor >= 1.0 ? 'warning.main' : 'error.main'}
          >
            {data.profit_factor.toFixed(2)}
          </Typography>
        </Box>
        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            Expectancy
          </Typography>
          <Typography
            variant="body2"
            fontWeight="bold"
            color={expectancy >= 0 ? 'success.main' : 'error.main'}
          >
            {expectancy >= 0 ? '+' : ''}${expectancy.toFixed(2)}
          </Typography>
        </Box>
      </Box>

      {/* Additional metrics */}
      <Box sx={{ mt: 2, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
        <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
          Trade Quality Analysis
        </Typography>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
          <Typography variant="body2">Average Win:</Typography>
          <Typography variant="body2" fontWeight="bold" color="success.main">
            +${data.average_win.toFixed(2)}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
          <Typography variant="body2">Average Loss:</Typography>
          <Typography variant="body2" fontWeight="bold" color="error.main">
            -${Math.abs(data.average_loss).toFixed(2)}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
          <Typography variant="body2">Best Trade:</Typography>
          <Typography variant="body2" fontWeight="bold" color="success.main">
            +${data.largest_win.toFixed(2)}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
          <Typography variant="body2">Worst Trade:</Typography>
          <Typography variant="body2" fontWeight="bold" color="error.main">
            -${Math.abs(data.largest_loss).toFixed(2)}
          </Typography>
        </Box>
      </Box>
    </Paper>
  );
}
