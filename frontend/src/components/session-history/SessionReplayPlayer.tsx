/**
 * Session Replay Player Component (SH-08)
 * ========================================
 *
 * Step-by-step playback of historical trading sessions.
 * Allows trader to review past session execution in slow motion.
 *
 * Features:
 * - Play/Pause/Step controls
 * - Speed adjustment (0.5x, 1x, 2x, 4x)
 * - Timeline scrubber
 * - State transition highlights
 * - Current state badge
 * - Indicator values at current step
 *
 * Related: docs/UI_BACKLOG.md (SH-08)
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Slider,
  Chip,
  Stack,
  Tooltip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  CircularProgress,
  LinearProgress,
  Divider,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  SkipNext as StepIcon,
  SkipPrevious as StepBackIcon,
  FastForward as FastForwardIcon,
  FastRewind as RewindIcon,
  Stop as StopIcon,
  Replay as RestartIcon,
} from '@mui/icons-material';
import StateBadge, { StateMachineState } from '@/components/dashboard/StateBadge';

// ============================================================================
// Types
// ============================================================================

export interface ReplayDataPoint {
  timestamp: string;
  time: number; // Unix timestamp in seconds
  price: number;
  state?: string;
  transition?: {
    from_state: string;
    to_state: string;
    trigger: string;
  };
  indicators?: Record<string, number>;
  position?: {
    side: 'LONG' | 'SHORT' | null;
    entryPrice?: number;
    currentPnL?: number;
  };
}

export interface SessionReplayPlayerProps {
  sessionId: string;
  symbol: string;
  onDataPointChange?: (dataPoint: ReplayDataPoint, index: number) => void;
  onPlayStateChange?: (isPlaying: boolean) => void;
  height?: number;
}

// ============================================================================
// Component
// ============================================================================

export const SessionReplayPlayer: React.FC<SessionReplayPlayerProps> = ({
  sessionId,
  symbol,
  onDataPointChange,
  onPlayStateChange,
  height = 120,
}) => {
  // State
  const [dataPoints, setDataPoints] = useState<ReplayDataPoint[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Refs
  const playIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // ========================================
  // Data Loading
  // ========================================

  useEffect(() => {
    const loadReplayData = async () => {
      if (!sessionId) return;

      setLoading(true);
      setError(null);

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

        // Load OHLCV data and transitions for the session
        const [ohlcvResponse, transitionsResponse] = await Promise.all([
          fetch(`${apiUrl}/api/chart/ohlcv?session_id=${sessionId}&symbol=${symbol}&interval=1m&limit=1000`),
          fetch(`${apiUrl}/api/sessions/${sessionId}/transitions`),
        ]);

        let candles: any[] = [];
        let transitions: any[] = [];

        if (ohlcvResponse.ok) {
          const ohlcvResult = await ohlcvResponse.json();
          candles = ohlcvResult.data?.candles || ohlcvResult.candles || [];
        }

        if (transitionsResponse.ok) {
          const transitionsResult = await transitionsResponse.json();
          transitions = transitionsResult.data?.transitions || transitionsResult.transitions || [];
        }

        // Merge candles with transitions to create replay data points
        const mergedData: ReplayDataPoint[] = candles.map((candle: any) => {
          const timestamp = new Date(candle.time * 1000).toISOString();

          // Find transition at this time (if any)
          const transition = transitions.find((t: any) => {
            const tTime = Math.floor(new Date(t.timestamp).getTime() / 1000);
            return Math.abs(tTime - candle.time) < 60; // Within 1 minute
          });

          return {
            timestamp,
            time: candle.time,
            price: candle.close,
            state: transition?.to_state || undefined,
            transition: transition ? {
              from_state: transition.from_state,
              to_state: transition.to_state,
              trigger: transition.trigger,
            } : undefined,
            indicators: {
              PUMP_MAGNITUDE: Math.random() * 10, // Mock for now
              VELOCITY: Math.random() * 5,
            },
          };
        });

        // Sort by time
        mergedData.sort((a, b) => a.time - b.time);

        setDataPoints(mergedData);

        if (mergedData.length === 0) {
          setError('No replay data available for this session');
        }
      } catch (err) {
        console.error('Failed to load replay data:', err);
        setError('Failed to load replay data');
      } finally {
        setLoading(false);
      }
    };

    loadReplayData();
  }, [sessionId, symbol]);

  // ========================================
  // Playback Controls
  // ========================================

  const play = useCallback(() => {
    if (dataPoints.length === 0 || currentIndex >= dataPoints.length - 1) return;

    setIsPlaying(true);
    onPlayStateChange?.(true);
  }, [dataPoints.length, currentIndex, onPlayStateChange]);

  const pause = useCallback(() => {
    setIsPlaying(false);
    onPlayStateChange?.(false);

    if (playIntervalRef.current) {
      clearInterval(playIntervalRef.current);
      playIntervalRef.current = null;
    }
  }, [onPlayStateChange]);

  const stop = useCallback(() => {
    pause();
    setCurrentIndex(0);
  }, [pause]);

  const stepForward = useCallback(() => {
    if (currentIndex < dataPoints.length - 1) {
      setCurrentIndex((prev) => prev + 1);
    }
  }, [currentIndex, dataPoints.length]);

  const stepBackward = useCallback(() => {
    if (currentIndex > 0) {
      setCurrentIndex((prev) => prev - 1);
    }
  }, [currentIndex]);

  const restart = useCallback(() => {
    setCurrentIndex(0);
    setIsPlaying(false);
    onPlayStateChange?.(false);
  }, [onPlayStateChange]);

  // ========================================
  // Effects
  // ========================================

  // Playback loop
  useEffect(() => {
    if (isPlaying && dataPoints.length > 0) {
      const interval = 1000 / playbackSpeed; // Base: 1 second per data point

      playIntervalRef.current = setInterval(() => {
        setCurrentIndex((prev) => {
          if (prev >= dataPoints.length - 1) {
            pause();
            return prev;
          }
          return prev + 1;
        });
      }, interval);

      return () => {
        if (playIntervalRef.current) {
          clearInterval(playIntervalRef.current);
        }
      };
    }
  }, [isPlaying, playbackSpeed, dataPoints.length, pause]);

  // Notify parent of current data point change
  useEffect(() => {
    if (dataPoints[currentIndex]) {
      onDataPointChange?.(dataPoints[currentIndex], currentIndex);
    }
  }, [currentIndex, dataPoints, onDataPointChange]);

  // ========================================
  // Helpers
  // ========================================

  const formatTime = (timestamp: string): string => {
    try {
      return new Date(timestamp).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return 'N/A';
    }
  };

  const currentDataPoint = dataPoints[currentIndex];
  const progress = dataPoints.length > 0 ? (currentIndex / (dataPoints.length - 1)) * 100 : 0;

  // ========================================
  // Render
  // ========================================

  if (loading) {
    return (
      <Paper sx={{ p: 2, height }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
          <CircularProgress size={24} sx={{ mr: 2 }} />
          <Typography variant="body2" color="text.secondary">
            Loading replay data...
          </Typography>
        </Box>
      </Paper>
    );
  }

  if (error) {
    return (
      <Paper sx={{ p: 2, height }}>
        <Alert severity="info">{error}</Alert>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2, height }}>
      {/* Progress Bar */}
      <LinearProgress
        variant="determinate"
        value={progress}
        sx={{ mb: 2, height: 6, borderRadius: 1 }}
      />

      {/* Controls Row */}
      <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between">
        {/* Playback Controls */}
        <Stack direction="row" spacing={0.5} alignItems="center">
          <Tooltip title="Restart">
            <IconButton size="small" onClick={restart}>
              <RestartIcon fontSize="small" />
            </IconButton>
          </Tooltip>

          <Tooltip title="Step Back">
            <IconButton size="small" onClick={stepBackward} disabled={currentIndex === 0}>
              <StepBackIcon fontSize="small" />
            </IconButton>
          </Tooltip>

          {isPlaying ? (
            <Tooltip title="Pause">
              <IconButton size="small" onClick={pause} color="primary">
                <PauseIcon />
              </IconButton>
            </Tooltip>
          ) : (
            <Tooltip title="Play">
              <IconButton
                size="small"
                onClick={play}
                color="primary"
                disabled={currentIndex >= dataPoints.length - 1}
              >
                <PlayIcon />
              </IconButton>
            </Tooltip>
          )}

          <Tooltip title="Step Forward">
            <IconButton
              size="small"
              onClick={stepForward}
              disabled={currentIndex >= dataPoints.length - 1}
            >
              <StepIcon fontSize="small" />
            </IconButton>
          </Tooltip>

          <Tooltip title="Stop">
            <IconButton size="small" onClick={stop}>
              <StopIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Stack>

        {/* Current Position */}
        <Stack direction="row" spacing={2} alignItems="center">
          <Typography variant="caption" color="text.secondary">
            {currentIndex + 1} / {dataPoints.length}
          </Typography>

          {currentDataPoint && (
            <>
              <Chip
                label={formatTime(currentDataPoint.timestamp)}
                size="small"
                variant="outlined"
                sx={{ fontSize: '0.7rem' }}
              />

              <Typography variant="body2" fontWeight={500}>
                ${currentDataPoint.price.toFixed(2)}
              </Typography>

              {currentDataPoint.state && (
                <StateBadge state={currentDataPoint.state as StateMachineState} />
              )}

              {currentDataPoint.transition && (
                <Chip
                  label={currentDataPoint.transition.trigger}
                  size="small"
                  color="warning"
                  sx={{ fontSize: '0.65rem', animation: 'pulse 1s ease-in-out infinite' }}
                />
              )}
            </>
          )}
        </Stack>

        {/* Speed Control */}
        <Stack direction="row" spacing={1} alignItems="center">
          <Typography variant="caption" color="text.secondary">
            Speed:
          </Typography>
          <FormControl size="small" sx={{ minWidth: 80 }}>
            <Select
              value={playbackSpeed}
              onChange={(e) => setPlaybackSpeed(e.target.value as number)}
              sx={{ fontSize: '0.8rem', height: 28 }}
            >
              <MenuItem value={0.5}>0.5x</MenuItem>
              <MenuItem value={1}>1x</MenuItem>
              <MenuItem value={2}>2x</MenuItem>
              <MenuItem value={4}>4x</MenuItem>
              <MenuItem value={8}>8x</MenuItem>
            </Select>
          </FormControl>
        </Stack>
      </Stack>

      {/* Timeline Slider */}
      <Box sx={{ px: 1, mt: 1 }}>
        <Slider
          value={currentIndex}
          onChange={(_, value) => {
            pause();
            setCurrentIndex(value as number);
          }}
          min={0}
          max={Math.max(0, dataPoints.length - 1)}
          step={1}
          size="small"
          sx={{
            '& .MuiSlider-thumb': {
              width: 12,
              height: 12,
            },
          }}
        />
      </Box>

      {/* Indicator Values (if available) */}
      {currentDataPoint?.indicators && Object.keys(currentDataPoint.indicators).length > 0 && (
        <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
          {Object.entries(currentDataPoint.indicators).map(([key, value]) => (
            <Typography key={key} variant="caption" color="text.secondary">
              {key}: <strong>{typeof value === 'number' ? value.toFixed(2) : value}</strong>
            </Typography>
          ))}
        </Stack>
      )}
    </Paper>
  );
};

export default SessionReplayPlayer;
