'use client';

import React, { useState, useMemo, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Switch,
  FormControlLabel,
  Slider,
  Grid,
  Chip,
  Tooltip,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Collapse,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  TrendingUp as TrendingUpIcon,
  KeyboardArrowDown as ArrowDownIcon,
  KeyboardArrowUp as ArrowUpIcon,
  LocalFireDepartment as PumpIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
} from '@mui/icons-material';

// Interface for detected pump event
export interface PumpEvent {
  id: string;
  startIndex: number;
  endIndex: number;
  peakIndex: number;
  startTime: number;
  endTime: number;
  peakTime: number;
  startPrice: number;
  peakPrice: number;
  endPrice: number;
  magnitude: number;       // % change from start to peak
  duration: number;        // seconds from start to end
  pumpDuration: number;    // seconds from start to peak
  dumpDuration: number;    // seconds from peak to end
  velocity: number;        // magnitude / pumpDuration
  type: 'pump' | 'pump_dump' | 'dump';
}

// Interface for chart data point
interface ChartDataPoint {
  timestamp: number;
  price: number;
  index?: number;
  [key: string]: any;
}

// Detection parameters
interface DetectionParams {
  minMagnitude: number;      // minimum % change to be considered a pump (default 2%)
  minDuration: number;       // minimum duration in seconds (default 30s)
  maxDuration: number;       // maximum duration in seconds (default 3600s = 1h)
  lookbackWindow: number;    // window size for local min/max detection (default 10)
}

interface PumpHistoryMarkingProps {
  data: ChartDataPoint[];
  onPumpsDetected?: (pumps: PumpEvent[]) => void;
  showOnChart?: boolean;
}

// Default detection parameters
const defaultParams: DetectionParams = {
  minMagnitude: 2.0,     // 2% minimum pump magnitude
  minDuration: 30,       // 30 seconds minimum
  maxDuration: 3600,     // 1 hour maximum
  lookbackWindow: 10,    // 10 data points for local extrema
};

/**
 * DC-02: Pump History Marking Component
 * Detects and displays historical pump/dump events on price data
 */
export function PumpHistoryMarking({ data, onPumpsDetected, showOnChart = true }: PumpHistoryMarkingProps) {
  const [enabled, setEnabled] = useState(true);
  const [params, setParams] = useState<DetectionParams>(defaultParams);
  const [expandedPump, setExpandedPump] = useState<string | null>(null);

  /**
   * Detect pump events in the data
   * Algorithm:
   * 1. Find local minima (potential pump starts)
   * 2. Find local maxima after each minimum (potential pump peaks)
   * 3. Calculate magnitude and duration
   * 4. Filter by thresholds
   */
  const detectedPumps = useMemo(() => {
    if (!data || data.length < params.lookbackWindow * 2) {
      return [];
    }

    const pumps: PumpEvent[] = [];
    const prices = data.map(d => d.price);
    const timestamps = data.map(d => d.timestamp);

    // Helper: Check if index is local minimum
    const isLocalMin = (idx: number): boolean => {
      const start = Math.max(0, idx - params.lookbackWindow);
      const end = Math.min(prices.length - 1, idx + params.lookbackWindow);
      const localMin = Math.min(...prices.slice(start, end + 1));
      return prices[idx] === localMin;
    };

    // Helper: Check if index is local maximum
    const isLocalMax = (idx: number): boolean => {
      const start = Math.max(0, idx - params.lookbackWindow);
      const end = Math.min(prices.length - 1, idx + params.lookbackWindow);
      const localMax = Math.max(...prices.slice(start, end + 1));
      return prices[idx] === localMax;
    };

    // Find local minima as potential pump starts
    const localMinima: number[] = [];
    for (let i = params.lookbackWindow; i < prices.length - params.lookbackWindow; i++) {
      if (isLocalMin(i)) {
        localMinima.push(i);
      }
    }

    // For each local minimum, find the next local maximum
    for (const minIdx of localMinima) {
      // Look for local maximum after the minimum
      let maxIdx = -1;
      let maxPrice = prices[minIdx];

      // Search forward for local maximum within lookback window
      for (let j = minIdx + 1; j < Math.min(prices.length, minIdx + params.maxDuration); j++) {
        if (prices[j] > maxPrice) {
          maxPrice = prices[j];
          maxIdx = j;
        }
        // Check if this is a local maximum
        if (maxIdx !== -1 && isLocalMax(maxIdx)) {
          break;
        }
      }

      if (maxIdx === -1) continue;

      // Calculate pump magnitude
      const startPrice = prices[minIdx];
      const peakPrice = prices[maxIdx];
      const magnitude = ((peakPrice - startPrice) / startPrice) * 100;

      // Check if magnitude meets threshold
      if (magnitude < params.minMagnitude) continue;

      // Calculate duration
      const pumpDuration = timestamps[maxIdx] - timestamps[minIdx];

      // Check duration constraints
      if (pumpDuration < params.minDuration || pumpDuration > params.maxDuration) continue;

      // Find dump end (next local minimum after peak)
      let dumpEndIdx = maxIdx;
      let dumpEndPrice = peakPrice;

      for (let k = maxIdx + 1; k < Math.min(prices.length, maxIdx + params.maxDuration); k++) {
        if (prices[k] < dumpEndPrice) {
          dumpEndPrice = prices[k];
          dumpEndIdx = k;
        }
        if (isLocalMin(k)) {
          dumpEndIdx = k;
          dumpEndPrice = prices[k];
          break;
        }
      }

      const dumpDuration = timestamps[dumpEndIdx] - timestamps[maxIdx];
      const totalDuration = timestamps[dumpEndIdx] - timestamps[minIdx];

      // Determine pump type
      const dumpMagnitude = ((peakPrice - dumpEndPrice) / peakPrice) * 100;
      let type: PumpEvent['type'] = 'pump';
      if (dumpMagnitude > params.minMagnitude * 0.5) {
        type = 'pump_dump';
      }

      // Create pump event
      const pumpEvent: PumpEvent = {
        id: `pump_${minIdx}_${maxIdx}`,
        startIndex: minIdx,
        peakIndex: maxIdx,
        endIndex: dumpEndIdx,
        startTime: timestamps[minIdx],
        peakTime: timestamps[maxIdx],
        endTime: timestamps[dumpEndIdx],
        startPrice,
        peakPrice,
        endPrice: dumpEndPrice,
        magnitude,
        duration: totalDuration,
        pumpDuration,
        dumpDuration,
        velocity: magnitude / (pumpDuration / 60), // % per minute
        type,
      };

      pumps.push(pumpEvent);
    }

    // Remove overlapping pumps (keep the one with higher magnitude)
    const filteredPumps = pumps.filter((pump, idx) => {
      const overlapping = pumps.find((other, otherIdx) => {
        if (idx === otherIdx) return false;
        // Check if overlapping
        return (
          pump.startIndex < other.endIndex &&
          pump.endIndex > other.startIndex
        );
      });

      if (!overlapping) return true;
      return pump.magnitude >= overlapping.magnitude;
    });

    return filteredPumps;
  }, [data, params]);

  // Notify parent when pumps are detected
  React.useEffect(() => {
    if (onPumpsDetected && enabled) {
      onPumpsDetected(detectedPumps);
    }
  }, [detectedPumps, enabled, onPumpsDetected]);

  // Format timestamp to readable string
  const formatTime = useCallback((timestamp: number): string => {
    return new Date(timestamp * 1000).toLocaleString();
  }, []);

  // Format duration in human readable format
  const formatDuration = useCallback((seconds: number): string => {
    if (seconds < 60) return `${seconds.toFixed(0)}s`;
    if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
    return `${(seconds / 3600).toFixed(1)}h`;
  }, []);

  // Get color based on pump magnitude
  const getMagnitudeColor = useCallback((magnitude: number): 'success' | 'warning' | 'error' => {
    if (magnitude >= 10) return 'error';
    if (magnitude >= 5) return 'warning';
    return 'success';
  }, []);

  // Get icon based on pump type
  const getPumpTypeIcon = useCallback((type: PumpEvent['type']) => {
    switch (type) {
      case 'pump':
        return <TrendingUpIcon color="success" />;
      case 'pump_dump':
        return <PumpIcon color="error" />;
      case 'dump':
        return <TrendingUpIcon color="error" sx={{ transform: 'rotate(180deg)' }} />;
      default:
        return <TrendingUpIcon />;
    }
  }, []);

  return (
    <Accordion defaultExpanded>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <PumpIcon color="error" />
          <Typography variant="h6">
            Pump History Marking
          </Typography>
          <Chip
            label={`${detectedPumps.length} pumps detected`}
            color={detectedPumps.length > 0 ? 'primary' : 'default'}
            size="small"
          />
          <FormControlLabel
            control={
              <Switch
                checked={enabled}
                onChange={(e) => {
                  e.stopPropagation();
                  setEnabled(e.target.checked);
                }}
                onClick={(e) => e.stopPropagation()}
              />
            }
            label={enabled ? <VisibilityIcon /> : <VisibilityOffIcon />}
            onClick={(e) => e.stopPropagation()}
          />
        </Box>
      </AccordionSummary>
      <AccordionDetails>
        {/* Detection Parameters */}
        <Paper sx={{ p: 2, mb: 2 }}>
          <Typography variant="subtitle2" gutterBottom>Detection Parameters</Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} md={3}>
              <Typography variant="caption" color="text.secondary">
                Min Magnitude: {params.minMagnitude}%
              </Typography>
              <Slider
                value={params.minMagnitude}
                min={0.5}
                max={20}
                step={0.5}
                onChange={(_, value) => setParams(prev => ({ ...prev, minMagnitude: value as number }))}
                valueLabelDisplay="auto"
                valueLabelFormat={(v) => `${v}%`}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <Typography variant="caption" color="text.secondary">
                Min Duration: {formatDuration(params.minDuration)}
              </Typography>
              <Slider
                value={params.minDuration}
                min={5}
                max={300}
                step={5}
                onChange={(_, value) => setParams(prev => ({ ...prev, minDuration: value as number }))}
                valueLabelDisplay="auto"
                valueLabelFormat={(v) => formatDuration(v)}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <Typography variant="caption" color="text.secondary">
                Max Duration: {formatDuration(params.maxDuration)}
              </Typography>
              <Slider
                value={params.maxDuration}
                min={60}
                max={7200}
                step={60}
                onChange={(_, value) => setParams(prev => ({ ...prev, maxDuration: value as number }))}
                valueLabelDisplay="auto"
                valueLabelFormat={(v) => formatDuration(v)}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <Typography variant="caption" color="text.secondary">
                Lookback Window: {params.lookbackWindow} points
              </Typography>
              <Slider
                value={params.lookbackWindow}
                min={3}
                max={50}
                step={1}
                onChange={(_, value) => setParams(prev => ({ ...prev, lookbackWindow: value as number }))}
                valueLabelDisplay="auto"
              />
            </Grid>
          </Grid>
        </Paper>

        {/* Detected Pumps Summary */}
        {detectedPumps.length === 0 ? (
          <Alert severity="info">
            No pump events detected with current parameters. Try lowering the minimum magnitude threshold.
          </Alert>
        ) : (
          <>
            {/* Quick Stats */}
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={6} md={2}>
                <Paper sx={{ p: 1.5, textAlign: 'center' }}>
                  <Typography variant="h4" color="error.main">
                    {detectedPumps.length}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Total Pumps
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={6} md={2}>
                <Paper sx={{ p: 1.5, textAlign: 'center' }}>
                  <Typography variant="h4" color="success.main">
                    {Math.max(...detectedPumps.map(p => p.magnitude)).toFixed(1)}%
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Max Magnitude
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={6} md={2}>
                <Paper sx={{ p: 1.5, textAlign: 'center' }}>
                  <Typography variant="h4" color="warning.main">
                    {(detectedPumps.reduce((sum, p) => sum + p.magnitude, 0) / detectedPumps.length).toFixed(1)}%
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Avg Magnitude
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={6} md={2}>
                <Paper sx={{ p: 1.5, textAlign: 'center' }}>
                  <Typography variant="h4" color="info.main">
                    {formatDuration(detectedPumps.reduce((sum, p) => sum + p.pumpDuration, 0) / detectedPumps.length)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Avg Pump Time
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={6} md={2}>
                <Paper sx={{ p: 1.5, textAlign: 'center' }}>
                  <Typography variant="h4" color="primary.main">
                    {(detectedPumps.reduce((sum, p) => sum + p.velocity, 0) / detectedPumps.length).toFixed(2)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Avg Velocity (%/min)
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={6} md={2}>
                <Paper sx={{ p: 1.5, textAlign: 'center' }}>
                  <Typography variant="h4" color="secondary.main">
                    {detectedPumps.filter(p => p.type === 'pump_dump').length}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Pump & Dump
                  </Typography>
                </Paper>
              </Grid>
            </Grid>

            {/* Pumps Table */}
            <TableContainer component={Paper} sx={{ maxHeight: 400 }}>
              <Table stickyHeader size="small">
                <TableHead>
                  <TableRow>
                    <TableCell width={40}></TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Start Time</TableCell>
                    <TableCell align="right">Magnitude</TableCell>
                    <TableCell align="right">Pump Time</TableCell>
                    <TableCell align="right">Velocity</TableCell>
                    <TableCell align="right">Start Price</TableCell>
                    <TableCell align="right">Peak Price</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {detectedPumps.map((pump) => (
                    <React.Fragment key={pump.id}>
                      <TableRow
                        hover
                        sx={{ cursor: 'pointer' }}
                        onClick={() => setExpandedPump(expandedPump === pump.id ? null : pump.id)}
                      >
                        <TableCell>
                          <IconButton size="small">
                            {expandedPump === pump.id ? <ArrowUpIcon /> : <ArrowDownIcon />}
                          </IconButton>
                        </TableCell>
                        <TableCell>
                          <Tooltip title={pump.type.replace('_', ' & ')}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              {getPumpTypeIcon(pump.type)}
                              <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                                {pump.type.replace('_', ' ')}
                              </Typography>
                            </Box>
                          </Tooltip>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">
                            {formatTime(pump.startTime)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Chip
                            label={`+${pump.magnitude.toFixed(2)}%`}
                            color={getMagnitudeColor(pump.magnitude)}
                            size="small"
                          />
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2">
                            {formatDuration(pump.pumpDuration)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2" color="primary">
                            {pump.velocity.toFixed(2)} %/min
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                            ${pump.startPrice.toFixed(6)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2" sx={{ fontFamily: 'monospace' }} color="success.main">
                            ${pump.peakPrice.toFixed(6)}
                          </Typography>
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell sx={{ py: 0 }} colSpan={8}>
                          <Collapse in={expandedPump === pump.id} timeout="auto" unmountOnExit>
                            <Box sx={{ p: 2, bgcolor: 'action.hover' }}>
                              <Grid container spacing={2}>
                                <Grid item xs={12} md={4}>
                                  <Typography variant="subtitle2" gutterBottom>Timing Details</Typography>
                                  <Typography variant="body2">
                                    <strong>Start:</strong> {formatTime(pump.startTime)}
                                  </Typography>
                                  <Typography variant="body2">
                                    <strong>Peak:</strong> {formatTime(pump.peakTime)}
                                  </Typography>
                                  <Typography variant="body2">
                                    <strong>End:</strong> {formatTime(pump.endTime)}
                                  </Typography>
                                  <Typography variant="body2">
                                    <strong>Total Duration:</strong> {formatDuration(pump.duration)}
                                  </Typography>
                                </Grid>
                                <Grid item xs={12} md={4}>
                                  <Typography variant="subtitle2" gutterBottom>Price Details</Typography>
                                  <Typography variant="body2">
                                    <strong>Start Price:</strong> ${pump.startPrice.toFixed(6)}
                                  </Typography>
                                  <Typography variant="body2" color="success.main">
                                    <strong>Peak Price:</strong> ${pump.peakPrice.toFixed(6)}
                                  </Typography>
                                  <Typography variant="body2">
                                    <strong>End Price:</strong> ${pump.endPrice.toFixed(6)}
                                  </Typography>
                                  <Typography variant="body2" color="error.main">
                                    <strong>Dump:</strong> -{((pump.peakPrice - pump.endPrice) / pump.peakPrice * 100).toFixed(2)}%
                                  </Typography>
                                </Grid>
                                <Grid item xs={12} md={4}>
                                  <Typography variant="subtitle2" gutterBottom>Performance Metrics</Typography>
                                  <Typography variant="body2">
                                    <strong>Pump Duration:</strong> {formatDuration(pump.pumpDuration)}
                                  </Typography>
                                  <Typography variant="body2">
                                    <strong>Dump Duration:</strong> {formatDuration(pump.dumpDuration)}
                                  </Typography>
                                  <Typography variant="body2" color="primary">
                                    <strong>Velocity:</strong> {pump.velocity.toFixed(2)} %/min
                                  </Typography>
                                  <Typography variant="body2">
                                    <strong>Data Points:</strong> {pump.startIndex} → {pump.peakIndex} → {pump.endIndex}
                                  </Typography>
                                </Grid>
                              </Grid>
                            </Box>
                          </Collapse>
                        </TableCell>
                      </TableRow>
                    </React.Fragment>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            {/* Chart Markers Info */}
            {showOnChart && enabled && (
              <Alert severity="success" sx={{ mt: 2 }}>
                <Typography variant="body2">
                  <strong>{detectedPumps.length} pump zones</strong> are highlighted on the chart above.
                  Orange zones indicate pump events, red dots mark peak prices.
                </Typography>
              </Alert>
            )}
          </>
        )}
      </AccordionDetails>
    </Accordion>
  );
}

// Export helper to generate pump zone markers for chart
export const generatePumpMarkers = (pumps: PumpEvent[]): {
  zones: Array<{ start: number; end: number; color: string; label: string }>;
  points: Array<{ timestamp: number; price: number; color: string; label: string }>;
} => {
  const zones = pumps.map(pump => ({
    start: pump.startTime,
    end: pump.endTime,
    color: pump.type === 'pump_dump' ? 'rgba(255, 152, 0, 0.2)' : 'rgba(76, 175, 80, 0.2)',
    label: `${pump.magnitude.toFixed(1)}% ${pump.type.replace('_', ' ')}`,
  }));

  const points = pumps.map(pump => ({
    timestamp: pump.peakTime,
    price: pump.peakPrice,
    color: '#f44336',
    label: `Peak: $${pump.peakPrice.toFixed(6)} (+${pump.magnitude.toFixed(1)}%)`,
  }));

  return { zones, points };
};

export default PumpHistoryMarking;
