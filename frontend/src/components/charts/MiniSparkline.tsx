'use client';

/**
 * MiniSparkline Component (MS-01)
 * ================================
 *
 * Reusable SVG sparkline chart for inline display in tables.
 * Lightweight, no external dependencies, supports color-coding based on trend.
 *
 * Features:
 * - SVG-based for crisp rendering at any size
 * - Area fill with gradient
 * - Auto-scaling to data range
 * - Color-coded based on positive/negative trend
 * - Optional current value marker
 *
 * Related: docs/UI_BACKLOG.md - MS-01
 */

import React, { useMemo } from 'react';
import { Box, Tooltip, alpha, useTheme } from '@mui/material';

// ============================================================================
// Types
// ============================================================================

export interface MiniSparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: 'auto' | 'positive' | 'negative' | 'neutral' | string;
  showMarker?: boolean;
  showFill?: boolean;
  strokeWidth?: number;
  tooltip?: string | boolean;
}

// ============================================================================
// Component
// ============================================================================

export const MiniSparkline: React.FC<MiniSparklineProps> = ({
  data,
  width = 80,
  height = 24,
  color = 'auto',
  showMarker = true,
  showFill = true,
  strokeWidth = 1.5,
  tooltip = true,
}) => {
  const theme = useTheme();

  // Calculate trend and determine color
  const { pathD, fillPathD, strokeColor, fillColor, trend, changePercent } = useMemo(() => {
    if (data.length < 2) {
      return {
        pathD: '',
        fillPathD: '',
        strokeColor: theme.palette.grey[400],
        fillColor: theme.palette.grey[200],
        trend: 'neutral' as const,
        changePercent: 0,
      };
    }

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const padding = 2;

    // Calculate points
    const points = data.map((value, index) => {
      const x = padding + (index / (data.length - 1)) * (width - 2 * padding);
      const y = padding + (1 - (value - min) / range) * (height - 2 * padding);
      return { x, y };
    });

    // Create path
    const pathD = points.map((p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`)).join(' ');

    // Create filled path (for area chart)
    const firstPoint = points[0];
    const lastPoint = points[points.length - 1];
    const fillPathD = `${pathD} L ${lastPoint.x} ${height - padding} L ${firstPoint.x} ${height - padding} Z`;

    // Determine trend
    const firstValue = data[0];
    const lastValue = data[data.length - 1];
    const changePercent = ((lastValue - firstValue) / firstValue) * 100;

    let trendType: 'positive' | 'negative' | 'neutral';
    if (changePercent > 0.5) {
      trendType = 'positive';
    } else if (changePercent < -0.5) {
      trendType = 'negative';
    } else {
      trendType = 'neutral';
    }

    // Determine colors based on color prop
    let strokeColor: string;
    let fillColor: string;

    if (color === 'auto') {
      switch (trendType) {
        case 'positive':
          strokeColor = theme.palette.success.main;
          fillColor = alpha(theme.palette.success.main, 0.2);
          break;
        case 'negative':
          strokeColor = theme.palette.error.main;
          fillColor = alpha(theme.palette.error.main, 0.2);
          break;
        default:
          strokeColor = theme.palette.grey[500];
          fillColor = alpha(theme.palette.grey[500], 0.1);
      }
    } else if (color === 'positive') {
      strokeColor = theme.palette.success.main;
      fillColor = alpha(theme.palette.success.main, 0.2);
    } else if (color === 'negative') {
      strokeColor = theme.palette.error.main;
      fillColor = alpha(theme.palette.error.main, 0.2);
    } else if (color === 'neutral') {
      strokeColor = theme.palette.grey[500];
      fillColor = alpha(theme.palette.grey[500], 0.1);
    } else {
      strokeColor = color;
      fillColor = alpha(color, 0.2);
    }

    return { pathD, fillPathD, strokeColor, fillColor, trend: trendType, changePercent };
  }, [data, width, height, color, theme]);

  // Calculate marker position (last point)
  const markerPosition = useMemo(() => {
    if (data.length < 2) return null;

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const padding = 2;

    const lastIndex = data.length - 1;
    const x = padding + (lastIndex / (data.length - 1)) * (width - 2 * padding);
    const y = padding + (1 - (data[lastIndex] - min) / range) * (height - 2 * padding);

    return { x, y };
  }, [data, width, height]);

  // Generate tooltip text
  const tooltipText = useMemo(() => {
    if (!tooltip) return '';
    if (typeof tooltip === 'string') return tooltip;

    if (data.length < 2) return 'No data';

    const lastValue = data[data.length - 1];
    const sign = changePercent >= 0 ? '+' : '';
    return `${lastValue.toFixed(2)} (${sign}${changePercent.toFixed(1)}%)`;
  }, [tooltip, data, changePercent]);

  if (data.length < 2) {
    return (
      <Box
        sx={{
          width,
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'text.disabled',
          fontSize: '0.7rem',
        }}
      >
        -
      </Box>
    );
  }

  const sparklineContent = (
    <svg width={width} height={height} style={{ display: 'block' }}>
      {/* Gradient definition */}
      <defs>
        <linearGradient id={`sparkline-gradient-${strokeColor}`} x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor={fillColor} />
          <stop offset="100%" stopColor="transparent" />
        </linearGradient>
      </defs>

      {/* Fill area */}
      {showFill && (
        <path
          d={fillPathD}
          fill={`url(#sparkline-gradient-${strokeColor})`}
          opacity={0.5}
        />
      )}

      {/* Line */}
      <path
        d={pathD}
        fill="none"
        stroke={strokeColor}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Current value marker */}
      {showMarker && markerPosition && (
        <circle
          cx={markerPosition.x}
          cy={markerPosition.y}
          r={3}
          fill={strokeColor}
        />
      )}
    </svg>
  );

  if (tooltip) {
    return (
      <Tooltip title={tooltipText} arrow placement="top">
        <Box sx={{ display: 'inline-block', cursor: 'help' }}>
          {sparklineContent}
        </Box>
      </Tooltip>
    );
  }

  return sparklineContent;
};

// ============================================================================
// Utility: Generate mock data for preview
// ============================================================================

export function generateMockSparklineData(
  length: number = 20,
  trend: 'up' | 'down' | 'random' = 'random',
  volatility: number = 0.1
): number[] {
  const data: number[] = [];
  let value = 100;

  for (let i = 0; i < length; i++) {
    const trendBias = trend === 'up' ? 0.02 : trend === 'down' ? -0.02 : 0;
    const change = (Math.random() - 0.5) * 2 * volatility + trendBias;
    value = value * (1 + change);
    data.push(value);
  }

  return data;
}

export default MiniSparkline;
