'use client';

/**
 * Equity Curve Chart Component - TIER 2.1
 * ========================================
 * Displays account balance over time during paper trading sessions.
 *
 * Features:
 * - Line chart showing current_balance progression
 * - Tooltip with timestamp, balance, P&L
 * - Initial balance reference line
 * - Profit/loss color coding
 * - Responsive design
 */

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceDot,
} from 'recharts';
import { Box, Typography, Paper } from '@mui/material';
import { TrendingUp as TrendingUpIcon } from '@mui/icons-material';

interface PerformanceSnapshot {
  timestamp: string;
  current_balance: number;
  total_pnl: number;
  total_return_pct: number;
}

interface TradeMarker {
  timestamp: string;
  side: 'BUY' | 'SELL';
  symbol: string;
  price: number;
  quantity: number;
  pnl?: number;
}

interface EquityCurveChartProps {
  data: PerformanceSnapshot[];
  initialBalance: number;
  trades?: TradeMarker[];
}

export default function EquityCurveChart({ data, initialBalance, trades = [] }: EquityCurveChartProps) {
  if (!data || data.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          No performance data available yet. Data will appear as the session progresses.
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
    balance: snapshot.current_balance,
    pnl: snapshot.total_pnl,
    returnPct: snapshot.total_return_pct,
  }));

  // Calculate min/max for Y-axis domain
  const balances = chartData.map((d) => d.balance);
  const minBalance = Math.min(...balances, initialBalance);
  const maxBalance = Math.max(...balances, initialBalance);
  const padding = (maxBalance - minBalance) * 0.1 || 100; // 10% padding or $100 minimum

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
            Balance: ${data.balance.toFixed(2)}
          </Typography>
          <Typography
            variant="body2"
            color={data.pnl >= 0 ? 'success.main' : 'error.main'}
          >
            P&L: {data.pnl >= 0 ? '+' : ''}${data.pnl.toFixed(2)} ({data.returnPct.toFixed(2)}%)
          </Typography>
        </Paper>
      );
    }
    return null;
  };

  // Determine line color based on final performance
  const finalBalance = chartData[chartData.length - 1]?.balance || initialBalance;
  const lineColor = finalBalance >= initialBalance ? '#4caf50' : '#f44336';

  // Map trades to chart data points - find closest balance for each trade timestamp
  const tradeMarkers = trades.map((trade) => {
    const tradeTime = new Date(trade.timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
    // Find the closest data point to this trade
    const matchingPoint = chartData.find((d) => d.timestamp === tradeTime);
    const balance = matchingPoint?.balance || initialBalance;
    return {
      ...trade,
      formattedTime: tradeTime,
      balance,
    };
  });

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <TrendingUpIcon sx={{ mr: 1, color: 'primary.main' }} />
        <Typography variant="h6">Equity Curve</Typography>
      </Box>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart
          data={chartData}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
          <XAxis
            dataKey="timestamp"
            stroke="#666"
            style={{ fontSize: '12px' }}
          />
          <YAxis
            stroke="#666"
            style={{ fontSize: '12px' }}
            domain={[minBalance - padding, maxBalance + padding]}
            tickFormatter={(value) => `$${value.toFixed(0)}`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />

          {/* Initial balance reference line */}
          <ReferenceLine
            y={initialBalance}
            stroke="#999"
            strokeDasharray="5 5"
            label={{
              value: `Initial: $${initialBalance.toFixed(0)}`,
              position: 'right',
              fill: '#666',
              fontSize: 12,
            }}
          />

          {/* Equity curve line */}
          <Line
            type="monotone"
            dataKey="balance"
            stroke={lineColor}
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
            name="Account Balance"
          />

          {/* Trade markers - BUY (green triangle up) and SELL (red triangle down) */}
          {tradeMarkers.map((trade, index) => (
            <ReferenceDot
              key={`trade-${index}`}
              x={trade.formattedTime}
              y={trade.balance}
              r={8}
              fill={trade.side === 'BUY' ? '#4caf50' : '#f44336'}
              stroke="#fff"
              strokeWidth={2}
              label={{
                value: trade.side === 'BUY' ? '▲' : '▼',
                position: 'top',
                fill: trade.side === 'BUY' ? '#4caf50' : '#f44336',
                fontSize: 14,
                fontWeight: 'bold',
              }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>

      {/* Summary stats */}
      <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-around' }}>
        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            Starting Balance
          </Typography>
          <Typography variant="body2" fontWeight="bold">
            ${initialBalance.toFixed(2)}
          </Typography>
        </Box>
        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            Current Balance
          </Typography>
          <Typography
            variant="body2"
            fontWeight="bold"
            color={finalBalance >= initialBalance ? 'success.main' : 'error.main'}
          >
            ${finalBalance.toFixed(2)}
          </Typography>
        </Box>
        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            Total Return
          </Typography>
          <Typography
            variant="body2"
            fontWeight="bold"
            color={finalBalance >= initialBalance ? 'success.main' : 'error.main'}
          >
            {finalBalance >= initialBalance ? '+' : ''}
            {((finalBalance - initialBalance) / initialBalance * 100).toFixed(2)}%
          </Typography>
        </Box>
      </Box>
    </Paper>
  );
}
