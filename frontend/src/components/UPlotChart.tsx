'use client';

import React, { useRef, useEffect, useState } from 'react';
import uPlot from 'uplot';
import 'uplot/dist/uPlot.min.css';
import { Box } from '@mui/material';
import { Logger } from '@/services/frontendLogService';

// Type definitions
export interface UPlotSeries {
  label: string;
  stroke: string;
  width?: number;
  dash?: number[];
  scale?: string; // Which Y-axis to use (default: 'price', or 'volume', 'secondary')
  show?: boolean;
  spanGaps?: boolean;
  value?: (self: uPlot, rawValue: number) => string;
}

export interface UPlotDataPoint {
  timestamp: number;
  [key: string]: number | null | undefined;
}

export interface UPlotChartProps {
  data: UPlotDataPoint[];
  series: UPlotSeries[];
  height?: number;
  width?: number | string;
  priceRange?: [number, number];
  volumeRange?: [number, number];
  secondaryRange?: [number, number];
  onZoom?: (min: number, max: number) => void;
  showLegend?: boolean;
  showTooltip?: boolean;
  className?: string;
}

/**
 * High-performance uPlot chart wrapper component
 *
 * Features:
 * - Canvas-based rendering (10-100x faster than SVG)
 * - Handles millions of data points
 * - Multiple Y-axes support (price, volume, secondary indicators)
 * - Built-in zoom/pan
 * - Interactive tooltips
 * - Legend
 */
export const UPlotChart: React.FC<UPlotChartProps> = ({
  data,
  series,
  height = 600,
  width = '100%',
  priceRange,
  volumeRange,
  secondaryRange,
  onZoom,
  showLegend = true,
  showTooltip = true,
  className,
}) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const plotRef = useRef<uPlot | null>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height });

  // Transform data from object array to uPlot format: [timestamps, series1, series2, ...]
  const transformData = (): uPlot.AlignedData => {
    if (data.length === 0) {
      return [[], []];
    }

    // Extract timestamps (X-axis)
    const timestamps = data.map(d => d.timestamp);

    // Extract each series data
    const seriesData = series.map(s => {
      return data.map(d => {
        const value = d[s.label];
        return value !== null && value !== undefined ? value : null;
      });
    });

    return [timestamps, ...seriesData];
  };

  // Create uPlot options
  const createOptions = (w: number, h: number): uPlot.Options => {
    // Build scales object
    const scales: Record<string, uPlot.Scale> = {
      x: {
        time: true,
      },
      price: {
        auto: !priceRange,
        range: priceRange ? () => priceRange : undefined,
      },
    };

    // Add volume scale if any series uses it
    if (series.some(s => s.scale === 'volume')) {
      scales.volume = {
        auto: !volumeRange,
        range: volumeRange ? () => volumeRange : undefined,
        // side: 1, // Right side - removed, not in Scale type
      } as any;
    }

    // Add secondary scale if any series uses it
    if (series.some(s => s.scale === 'secondary')) {
      scales.secondary = {
        auto: !secondaryRange,
        range: secondaryRange ? () => secondaryRange : undefined,
        // side: 0, // Left side (or right if volume exists) - removed, not in Scale type
      } as any;
    }

    // Build axes
    const axes: uPlot.Axis[] = [
      {
        // X-axis (time)
        stroke: '#666',
        grid: {
          show: true,
          stroke: 'rgba(0,0,0,0.07)',
          width: 1,
        },
        ticks: {
          show: true,
          stroke: '#666',
        },
        values: (self, ticks) => {
          return ticks.map(t => {
            const date = new Date(t * 1000);
            return date.toLocaleTimeString();
          });
        },
      },
      {
        // Price Y-axis (left)
        scale: 'price',
        label: 'Price',
        labelSize: 30,
        labelGap: 10,
        size: 70,
        stroke: '#1976d2',
        grid: {
          show: true,
          stroke: 'rgba(0,0,0,0.07)',
          width: 1,
        },
        ticks: {
          show: true,
          stroke: '#666',
        },
        values: (self, ticks) => ticks.map(t => t.toFixed(6)),
      },
    ];

    // Add volume axis if needed
    if (series.some(s => s.scale === 'volume')) {
      axes.push({
        scale: 'volume',
        label: 'Volume',
        labelSize: 30,
        labelGap: 10,
        size: 70,
        // side: 1, // Removed - not in Axis type
        stroke: '#9c27b0',
        grid: {
          show: false,
        },
        ticks: {
          show: true,
          stroke: '#666',
        },
        values: (self, ticks) => ticks.map(t => t.toFixed(2)),
      });
    }

    // Add secondary axis if needed
    if (series.some(s => s.scale === 'secondary')) {
      axes.push({
        scale: 'secondary',
        label: 'Indicators',
        labelSize: 30,
        labelGap: 10,
        size: 70,
        // side: series.some(s => s.scale === 'volume') ? 1 : 0, // Removed - not in Axis type
        stroke: '#f44336',
        grid: {
          show: false,
        },
        ticks: {
          show: true,
          stroke: '#666',
        },
        values: (self, ticks) => ticks.map(t => t.toFixed(4)),
      });
    }

    // Build series configuration
    const uplotSeries: uPlot.Series[] = [
      {}, // First series is always empty (for X-axis)
      ...series.map(s => ({
        label: s.label,
        stroke: s.stroke,
        width: s.width || 2,
        dash: s.dash,
        scale: s.scale || 'price',
        show: s.show !== false,
        spanGaps: s.spanGaps !== false,
        value: s.value,
      })),
    ];

    // Plugin for zoom callback
    const plugins: uPlot.Plugin[] = [];

    if (onZoom) {
      plugins.push({
        hooks: {
          setScale: [
            (u, key) => {
              if (key === 'x') {
                const min = u.scales.x.min!;
                const max = u.scales.x.max!;
                onZoom(min, max);
              }
            },
          ],
        },
      });
    }

    return {
      width: w,
      height: h,
      scales,
      axes,
      series: uplotSeries,
      plugins,
      legend: {
        show: showLegend,
      },
      cursor: {
        show: showTooltip,
        drag: {
          x: true, // Enable zoom by dragging
          y: false,
        },
      },
    };
  };

  // Update dimensions on resize
  useEffect(() => {
    if (!chartRef.current) return;

    const updateDimensions = () => {
      if (chartRef.current) {
        const rect = chartRef.current.getBoundingClientRect();
        setDimensions({
          width: typeof width === 'number' ? width : rect.width,
          height,
        });
      }
    };

    updateDimensions();

    const resizeObserver = new ResizeObserver(updateDimensions);
    resizeObserver.observe(chartRef.current);

    return () => {
      resizeObserver.disconnect();
    };
  }, [width, height]);

  // Create and update uPlot instance
  useEffect(() => {
    if (!chartRef.current || dimensions.width === 0) return;

    const uplotData = transformData();

    // Create new instance if doesn't exist
    if (!plotRef.current) {
      const opts = createOptions(dimensions.width, dimensions.height);
      plotRef.current = new uPlot(opts, uplotData, chartRef.current);
      Logger.debug('UPlotChart.create', 'Chart created', { dataPoints: uplotData[0]?.length || 0 });
    } else {
      // Update existing instance
      plotRef.current.setData(uplotData);
      plotRef.current.setSize({
        width: dimensions.width,
        height: dimensions.height,
      });
      Logger.debug('UPlotChart.update', 'Chart updated', { dataPoints: uplotData[0]?.length || 0 });
    }

    // Cleanup on unmount
    return () => {
      if (plotRef.current) {
        plotRef.current.destroy();
        plotRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, series, dimensions, priceRange, volumeRange, secondaryRange]);

  return (
    <Box
      className={className}
      sx={{
        width: width,
        height: height,
        '& .u-legend': {
          fontSize: '12px',
          fontFamily: 'monospace',
        },
        '& .u-series': {
          cursor: 'pointer',
        },
      }}
    >
      <div ref={chartRef} style={{ width: '100%', height: '100%' }} />
    </Box>
  );
};

export default UPlotChart;
