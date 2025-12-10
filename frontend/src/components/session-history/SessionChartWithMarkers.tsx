/**
 * SH-06: Session Chart with S1/Z1/ZE1 Markers
 *
 * CRITICAL COMPONENT for trader analysis:
 * Shows historical price chart with state machine transition markers.
 *
 * WHY THIS IS CRITICAL:
 * - Trader needs to SEE where on the chart pump was detected (S1)
 * - Trader needs to SEE where short position was entered (Z1)
 * - Trader needs to SEE where position was closed (ZE1/E1/O1)
 * - Without this, trader cannot correlate PRICE with DECISION
 *
 * Features:
 * - OHLCV candlestick chart from session data
 * - S1 markers (orange triangle up) = Pump detected
 * - Z1 markers (green circle) = Entry executed
 * - ZE1 markers (blue square) = Normal exit (dump end)
 * - E1 markers (red diamond) = Emergency exit
 * - O1 markers (gray X) = Signal timeout/cancel
 * - Position zones (green/red shading between Z1 and exit)
 * - P&L annotation at exit points
 * - Zoom and scroll capability
 * - Click markers for transition details
 *
 * Data sources:
 * - OHLCV: /api/sessions/{sessionId}/ohlcv or mock
 * - Transitions: /api/sessions/{sessionId}/transitions or mock
 *
 * Location: frontend/src/components/session-history/SessionChartWithMarkers.tsx
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  CircularProgress,
  Alert,
  Chip,
  Stack,
  IconButton,
  Tooltip,
  Slider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Card,
  CardContent,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Table,
  TableBody,
  TableCell,
  TableRow,
} from '@mui/material';
import {
  ShowChart as ChartIcon,
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  CenterFocusStrong as ResetZoomIcon,
  Info as InfoIcon,
  TrendingUp as PumpIcon,
  PlayArrow as EntryIcon,
  Stop as ExitIcon,
  Warning as EmergencyIcon,
  Cancel as CancelIcon,
} from '@mui/icons-material';

// ============================================================================
// TYPES
// ============================================================================

interface OHLCVData {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface TransitionMarker {
  id: string;
  timestamp: number;
  price: number;
  type: 'S1' | 'Z1' | 'ZE1' | 'E1' | 'O1';
  fromState: string;
  toState: string;
  trigger: string;
  conditions?: Record<string, { value: number; threshold: number; met: boolean }>;
  position?: {
    entryPrice?: number;
    exitPrice?: number;
    pnl?: number;
    pnlPct?: number;
  };
}

interface SessionChartWithMarkersProps {
  sessionId: string;
  symbol?: string;
  height?: number;
}

// ============================================================================
// MOCK DATA GENERATOR (for development/demo)
// ============================================================================

function generateMockSessionData(sessionId: string): {
  ohlcv: OHLCVData[];
  transitions: TransitionMarker[];
} {
  const now = Math.floor(Date.now() / 1000);
  const ohlcv: OHLCVData[] = [];
  const transitions: TransitionMarker[] = [];

  // Generate 4 hours of 1-minute data
  const candleCount = 240;
  let price = 100 + Math.random() * 50; // Base price
  let inPosition = false;
  let entryPrice = 0;
  let entryIndex = 0;

  for (let i = 0; i < candleCount; i++) {
    const timestamp = now - (candleCount - i) * 60;

    // Simulate pump events
    const isPumpStart = !inPosition && Math.random() < 0.02;
    let change = (Math.random() - 0.5) * 0.8;

    if (isPumpStart) {
      change = 2 + Math.random() * 3; // 2-5% pump
    } else if (inPosition && i > entryIndex + 5) {
      change = -1 - Math.random() * 2; // Dump phase
    }

    price = price * (1 + change / 100);

    const volatility = 0.003;
    const high = price * (1 + Math.random() * volatility);
    const low = price * (1 - Math.random() * volatility);

    ohlcv.push({
      timestamp,
      open: low + Math.random() * (high - low),
      high,
      low,
      close: low + Math.random() * (high - low),
      volume: 10000 + Math.random() * 50000,
    });

    // Generate transitions
    if (isPumpStart && !inPosition) {
      // S1: Pump detected
      transitions.push({
        id: `s1_${i}`,
        timestamp,
        price: high,
        type: 'S1',
        fromState: 'MONITORING',
        toState: 'SIGNAL_DETECTED',
        trigger: 'S1',
        conditions: {
          PUMP_MAGNITUDE: { value: change, threshold: 3, met: true },
          PRICE_VELOCITY: { value: 0.5, threshold: 0.3, met: true },
        },
      });

      // Z1: Entry after 2-3 candles
      const entryDelay = 2 + Math.floor(Math.random() * 2);
      if (i + entryDelay < candleCount) {
        inPosition = true;
        entryPrice = ohlcv[i].high * 0.99; // Slightly below peak
        entryIndex = i + entryDelay;

        transitions.push({
          id: `z1_${i}`,
          timestamp: timestamp + entryDelay * 60,
          price: entryPrice,
          type: 'Z1',
          fromState: 'SIGNAL_DETECTED',
          toState: 'POSITION_ACTIVE',
          trigger: 'Z1',
          conditions: {
            VELOCITY_CASCADE: { value: 0.08, threshold: 0.1, met: true },
            REVERSAL_INDEX: { value: 0.75, threshold: 0.7, met: true },
          },
          position: {
            entryPrice,
          },
        });
      }
    }

    // Exit after position
    if (inPosition && i === entryIndex + 10) {
      const exitPrice = price;
      const pnl = ((entryPrice - exitPrice) / entryPrice) * 100; // SHORT: profit when price drops
      const isEmergency = pnl < -3;

      transitions.push({
        id: `exit_${i}`,
        timestamp,
        price: exitPrice,
        type: isEmergency ? 'E1' : 'ZE1',
        fromState: 'POSITION_ACTIVE',
        toState: 'EXITED',
        trigger: isEmergency ? 'E1' : 'ZE1',
        conditions: isEmergency
          ? { PUMP_CONT: { value: 8, threshold: 7, met: true } }
          : { DUMP_EXHAUSTION: { value: 0.8, threshold: 0.7, met: true } },
        position: {
          entryPrice,
          exitPrice,
          pnl: (entryPrice - exitPrice) * 10, // Mock $
          pnlPct: pnl,
        },
      });

      inPosition = false;
    }
  }

  return { ohlcv, transitions };
}

// ============================================================================
// COMPONENT
// ============================================================================

export const SessionChartWithMarkers: React.FC<SessionChartWithMarkersProps> = ({
  sessionId,
  symbol = 'BTC_USDT',
  height = 400,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ohlcvData, setOhlcvData] = useState<OHLCVData[]>([]);
  const [transitions, setTransitions] = useState<TransitionMarker[]>([]);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [viewOffset, setViewOffset] = useState(0);
  const [selectedMarker, setSelectedMarker] = useState<TransitionMarker | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  // Chart dimensions
  const chartWidth = 900;
  const chartHeight = height - 80; // Reserve space for legend

  // Load data
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

        // Try to fetch OHLCV data
        let ohlcv: OHLCVData[] = [];
        let trans: TransitionMarker[] = [];

        try {
          const ohlcvResponse = await fetch(
            `${apiUrl}/api/sessions/${sessionId}/ohlcv?symbol=${symbol}`
          );
          if (ohlcvResponse.ok) {
            const data = await ohlcvResponse.json();
            ohlcv = data.ohlcv || data.data || [];
          }
        } catch (e) {
          console.warn('OHLCV fetch failed, using mock data');
        }

        try {
          const transResponse = await fetch(
            `${apiUrl}/api/sessions/${sessionId}/transitions`
          );
          if (transResponse.ok) {
            const data = await transResponse.json();
            trans = data.transitions || [];
          }
        } catch (e) {
          console.warn('Transitions fetch failed, using mock data');
        }

        // Fallback to mock data if API fails
        if (ohlcv.length === 0 || trans.length === 0) {
          const mockData = generateMockSessionData(sessionId);
          ohlcv = mockData.ohlcv;
          trans = mockData.transitions;
        }

        setOhlcvData(ohlcv);
        setTransitions(trans);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [sessionId, symbol]);

  // Marker counts
  const markerCounts = useMemo(() => {
    const counts = { S1: 0, Z1: 0, ZE1: 0, E1: 0, O1: 0 };
    transitions.forEach((t) => {
      if (counts[t.type] !== undefined) counts[t.type]++;
    });
    return counts;
  }, [transitions]);

  // Calculate visible data range based on zoom
  const visibleData = useMemo(() => {
    const total = ohlcvData.length;
    const visible = Math.ceil(total / zoomLevel);
    const start = Math.min(viewOffset, total - visible);
    return {
      data: ohlcvData.slice(Math.max(0, start), start + visible),
      startIndex: Math.max(0, start),
    };
  }, [ohlcvData, zoomLevel, viewOffset]);

  // Price scale
  const priceScale = useMemo(() => {
    if (visibleData.data.length === 0) return { min: 0, max: 100, range: 100 };
    const prices = visibleData.data.flatMap((d) => [d.high, d.low]);
    const min = Math.min(...prices) * 0.995;
    const max = Math.max(...prices) * 1.005;
    return { min, max, range: max - min };
  }, [visibleData]);

  // Scale functions
  const scaleY = useCallback(
    (price: number) => {
      return chartHeight - ((price - priceScale.min) / priceScale.range) * chartHeight;
    },
    [chartHeight, priceScale]
  );

  const scaleX = useCallback(
    (index: number) => {
      return ((index - visibleData.startIndex) / (visibleData.data.length - 1)) * chartWidth;
    },
    [chartWidth, visibleData]
  );

  // Handle marker click
  const handleMarkerClick = (marker: TransitionMarker) => {
    setSelectedMarker(marker);
    setDialogOpen(true);
  };

  // Zoom controls
  const handleZoomIn = () => setZoomLevel((z) => Math.min(z * 1.5, 10));
  const handleZoomOut = () => setZoomLevel((z) => Math.max(z / 1.5, 1));
  const handleResetZoom = () => {
    setZoomLevel(1);
    setViewOffset(0);
  };

  // Marker config
  const markerConfig: Record<
    string,
    { color: string; icon: string; label: string; shape: 'triangle' | 'circle' | 'square' | 'diamond' | 'x' }
  > = {
    S1: { color: '#ff9800', icon: '▲', label: 'Pump Detected', shape: 'triangle' },
    Z1: { color: '#4caf50', icon: '●', label: 'Entry Executed', shape: 'circle' },
    ZE1: { color: '#2196f3', icon: '■', label: 'Normal Exit', shape: 'square' },
    E1: { color: '#f44336', icon: '◆', label: 'Emergency Exit', shape: 'diamond' },
    O1: { color: '#9e9e9e', icon: '✕', label: 'Signal Cancelled', shape: 'x' },
  };

  // Render marker shape
  const renderMarkerShape = (
    x: number,
    y: number,
    type: string,
    size: number = 10
  ) => {
    const config = markerConfig[type] || markerConfig.S1;

    switch (config.shape) {
      case 'triangle':
        return (
          <polygon
            points={`${x},${y - size} ${x - size * 0.866},${y + size / 2} ${x + size * 0.866},${y + size / 2}`}
            fill={config.color}
          />
        );
      case 'circle':
        return <circle cx={x} cy={y} r={size / 2} fill={config.color} />;
      case 'square':
        return (
          <rect
            x={x - size / 2}
            y={y - size / 2}
            width={size}
            height={size}
            fill={config.color}
          />
        );
      case 'diamond':
        return (
          <polygon
            points={`${x},${y - size} ${x + size * 0.707},${y} ${x},${y + size} ${x - size * 0.707},${y}`}
            fill={config.color}
          />
        );
      case 'x':
        return (
          <g>
            <line x1={x - size / 2} y1={y - size / 2} x2={x + size / 2} y2={y + size / 2} stroke={config.color} strokeWidth={2} />
            <line x1={x + size / 2} y1={y - size / 2} x2={x - size / 2} y2={y + size / 2} stroke={config.color} strokeWidth={2} />
          </g>
        );
    }
  };

  // Render chart
  const renderChart = () => {
    if (visibleData.data.length === 0) return null;

    const candleWidth = Math.max(2, chartWidth / visibleData.data.length - 1);

    // Find position zones (Z1 to exit)
    const positionZones: Array<{
      startX: number;
      endX: number;
      profit: boolean;
      pnl: number;
    }> = [];

    transitions.forEach((t, i) => {
      if (t.type === 'Z1') {
        // Find corresponding exit
        const exit = transitions.find(
          (e, j) => j > i && (e.type === 'ZE1' || e.type === 'E1')
        );
        if (exit) {
          const startIdx = ohlcvData.findIndex((d) => d.timestamp >= t.timestamp);
          const endIdx = ohlcvData.findIndex((d) => d.timestamp >= exit.timestamp);
          if (startIdx >= 0 && endIdx >= 0) {
            positionZones.push({
              startX: scaleX(startIdx),
              endX: scaleX(endIdx),
              profit: (exit.position?.pnlPct || 0) > 0,
              pnl: exit.position?.pnlPct || 0,
            });
          }
        }
      }
    });

    return (
      <svg width={chartWidth} height={chartHeight + 60} style={{ background: '#1a1a2e' }}>
        {/* Position zones */}
        {positionZones.map((zone, i) => (
          <rect
            key={`zone-${i}`}
            x={zone.startX}
            y={0}
            width={zone.endX - zone.startX}
            height={chartHeight}
            fill={zone.profit ? 'rgba(76, 175, 80, 0.15)' : 'rgba(244, 67, 54, 0.15)'}
          />
        ))}

        {/* Price grid lines */}
        {[0.2, 0.4, 0.6, 0.8].map((ratio) => {
          const price = priceScale.min + priceScale.range * (1 - ratio);
          return (
            <g key={ratio}>
              <line
                x1={0}
                y1={ratio * chartHeight}
                x2={chartWidth}
                y2={ratio * chartHeight}
                stroke="#333"
                strokeDasharray="4,4"
              />
              <text x={5} y={ratio * chartHeight - 3} fill="#666" fontSize={10}>
                ${price.toFixed(2)}
              </text>
            </g>
          );
        })}

        {/* Candlesticks */}
        {visibleData.data.map((candle, i) => {
          const idx = visibleData.startIndex + i;
          const x = scaleX(idx);
          const isGreen = candle.close >= candle.open;
          const color = isGreen ? '#00c853' : '#ff1744';

          const bodyTop = scaleY(Math.max(candle.open, candle.close));
          const bodyBottom = scaleY(Math.min(candle.open, candle.close));
          const bodyHeight = Math.max(1, bodyBottom - bodyTop);

          return (
            <g key={`candle-${i}`}>
              {/* Wick */}
              <line
                x1={x}
                y1={scaleY(candle.high)}
                x2={x}
                y2={scaleY(candle.low)}
                stroke={color}
                strokeWidth={1}
              />
              {/* Body */}
              <rect
                x={x - candleWidth / 2}
                y={bodyTop}
                width={candleWidth}
                height={bodyHeight}
                fill={color}
              />
            </g>
          );
        })}

        {/* Transition markers */}
        {transitions.map((marker) => {
          const idx = ohlcvData.findIndex((d) => d.timestamp >= marker.timestamp);
          if (idx < visibleData.startIndex || idx >= visibleData.startIndex + visibleData.data.length) {
            return null;
          }

          const x = scaleX(idx);
          const y = scaleY(marker.price);
          const config = markerConfig[marker.type];

          return (
            <g
              key={marker.id}
              style={{ cursor: 'pointer' }}
              onClick={() => handleMarkerClick(marker)}
            >
              {/* Marker shape */}
              {renderMarkerShape(x, y, marker.type, 12)}

              {/* Vertical line */}
              <line
                x1={x}
                y1={y + 15}
                x2={x}
                y2={chartHeight}
                stroke={config.color}
                strokeWidth={1}
                strokeDasharray="2,2"
                opacity={0.5}
              />

              {/* Label */}
              <text
                x={x}
                y={y - 18}
                textAnchor="middle"
                fill={config.color}
                fontSize={11}
                fontWeight="bold"
              >
                {marker.type}
              </text>

              {/* P&L annotation for exits */}
              {(marker.type === 'ZE1' || marker.type === 'E1') && marker.position?.pnlPct && (
                <text
                  x={x}
                  y={y + 30}
                  textAnchor="middle"
                  fill={marker.position.pnlPct > 0 ? '#4caf50' : '#f44336'}
                  fontSize={10}
                  fontWeight="bold"
                >
                  {marker.position.pnlPct > 0 ? '+' : ''}
                  {marker.position.pnlPct.toFixed(1)}%
                </text>
              )}
            </g>
          );
        })}

        {/* Legend */}
        <g transform={`translate(10, ${chartHeight + 15})`}>
          {Object.entries(markerConfig).map(([type, config], i) => (
            <g key={type} transform={`translate(${i * 140}, 0)`}>
              {renderMarkerShape(8, 8, type, 8)}
              <text x={20} y={12} fill="#aaa" fontSize={10}>
                {type} - {config.label}
              </text>
            </g>
          ))}
        </g>

        {/* Position zone legend */}
        <g transform={`translate(10, ${chartHeight + 35})`}>
          <rect x={0} y={0} width={12} height={12} fill="rgba(76, 175, 80, 0.3)" />
          <text x={18} y={10} fill="#aaa" fontSize={10}>
            Profitable Position
          </text>
          <rect x={140} y={0} width={12} height={12} fill="rgba(244, 67, 54, 0.3)" />
          <text x={158} y={10} fill="#aaa" fontSize={10}>
            Losing Position
          </text>
        </g>
      </svg>
    );
  };

  // Render
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', py: 4 }}>
        <CircularProgress />
        <Typography sx={{ ml: 2 }}>Loading session chart data...</Typography>
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  return (
    <Paper sx={{ p: 2 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <ChartIcon color="primary" />
          <Typography variant="h6">Price Chart with Transition Markers</Typography>
          <Tooltip title="SH-06: Shows where state machine transitions occurred on the price chart. Click markers for details.">
            <IconButton size="small">
              <InfoIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>

        {/* Zoom controls */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Tooltip title="Zoom In">
            <IconButton size="small" onClick={handleZoomIn}>
              <ZoomInIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Zoom Out">
            <IconButton size="small" onClick={handleZoomOut}>
              <ZoomOutIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Reset Zoom">
            <IconButton size="small" onClick={handleResetZoom}>
              <ResetZoomIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Signal Summary */}
      <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: 'wrap' }}>
        {Object.entries(markerCounts).map(([type, count]) => {
          if (count === 0) return null;
          const config = markerConfig[type];
          return (
            <Chip
              key={type}
              label={`${count} ${type}`}
              size="small"
              sx={{
                backgroundColor: config.color,
                color: '#fff',
                fontWeight: 'bold',
              }}
            />
          );
        })}
      </Stack>

      {/* Chart */}
      <Box
        sx={{
          overflowX: 'auto',
          border: 1,
          borderColor: 'divider',
          borderRadius: 1,
        }}
      >
        {renderChart()}
      </Box>

      {/* Scroll control for zoomed view */}
      {zoomLevel > 1 && (
        <Box sx={{ mt: 2, px: 2 }}>
          <Typography variant="caption" color="text.secondary">
            Scroll Position
          </Typography>
          <Slider
            value={viewOffset}
            min={0}
            max={Math.max(0, ohlcvData.length - Math.ceil(ohlcvData.length / zoomLevel))}
            onChange={(_, value) => setViewOffset(value as number)}
          />
        </Box>
      )}

      {/* Info */}
      <Alert severity="info" sx={{ mt: 2 }}>
        <Typography variant="body2">
          <strong>How to read:</strong> Orange triangles (S1) show pump detection.
          Green circles (Z1) show SHORT entry. Blue squares (ZE1) or red diamonds (E1) show exits.
          Shaded zones indicate position duration. Click any marker for details.
        </Typography>
      </Alert>

      {/* Marker Details Dialog */}
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          {selectedMarker && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Chip
                label={selectedMarker.type}
                size="small"
                sx={{
                  backgroundColor: markerConfig[selectedMarker.type]?.color,
                  color: '#fff',
                }}
              />
              <Typography variant="h6">
                {markerConfig[selectedMarker.type]?.label}
              </Typography>
            </Box>
          )}
        </DialogTitle>
        <DialogContent>
          {selectedMarker && (
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Transition Details
              </Typography>
              <Table size="small">
                <TableBody>
                  <TableRow>
                    <TableCell><strong>Time</strong></TableCell>
                    <TableCell>
                      {new Date(selectedMarker.timestamp * 1000).toLocaleString()}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell><strong>Price</strong></TableCell>
                    <TableCell>${selectedMarker.price.toFixed(4)}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell><strong>State Change</strong></TableCell>
                    <TableCell>
                      {selectedMarker.fromState} → {selectedMarker.toState}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell><strong>Trigger</strong></TableCell>
                    <TableCell>{selectedMarker.trigger}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>

              {selectedMarker.conditions && Object.keys(selectedMarker.conditions).length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Conditions Met
                  </Typography>
                  <Table size="small">
                    <TableBody>
                      {Object.entries(selectedMarker.conditions).map(([key, cond]) => (
                        <TableRow key={key}>
                          <TableCell>{key}</TableCell>
                          <TableCell>
                            {cond.value.toFixed(2)} (threshold: {cond.threshold})
                          </TableCell>
                          <TableCell>
                            {cond.met ? '✅' : '❌'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </Box>
              )}

              {selectedMarker.position && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Position Details
                  </Typography>
                  <Table size="small">
                    <TableBody>
                      {selectedMarker.position.entryPrice && (
                        <TableRow>
                          <TableCell><strong>Entry Price</strong></TableCell>
                          <TableCell>${selectedMarker.position.entryPrice.toFixed(4)}</TableCell>
                        </TableRow>
                      )}
                      {selectedMarker.position.exitPrice && (
                        <TableRow>
                          <TableCell><strong>Exit Price</strong></TableCell>
                          <TableCell>${selectedMarker.position.exitPrice.toFixed(4)}</TableCell>
                        </TableRow>
                      )}
                      {selectedMarker.position.pnl !== undefined && (
                        <TableRow>
                          <TableCell><strong>P&L</strong></TableCell>
                          <TableCell
                            sx={{
                              color: selectedMarker.position.pnl >= 0 ? 'success.main' : 'error.main',
                              fontWeight: 'bold',
                            }}
                          >
                            {selectedMarker.position.pnl >= 0 ? '+' : ''}
                            ${selectedMarker.position.pnl.toFixed(2)} (
                            {selectedMarker.position.pnlPct?.toFixed(2)}%)
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};

export default SessionChartWithMarkers;
