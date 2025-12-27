'use client';

/**
 * StatusHero Component
 * ====================
 * Story 1A-5: StatusHero Component
 *
 * The largest and most prominent element on the dashboard.
 * Combines state, P&L, and symbol for instant comprehension (< 2 seconds).
 *
 * State Variants:
 * - MONITORING: Slate background, calm "Watching" state
 * - S1/Z1: Amber background, alert "Signal Detected" state
 * - POSITION_ACTIVE: Blue background with large P&L display
 * - ZE1: Green background, taking profit
 * - E1: Red background, stopping loss
 *
 * Typography:
 * - Hero Metric (P&L): 48-64px, Bold
 * - State Badge: 24px, Semibold
 * - Labels: 14px, Medium
 * - Values: 16px, Regular (monospace for numbers)
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  styled,
  alpha,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import {
  TrendingUp as ProfitIcon,
  TrendingDown as LossIcon,
  AccessTime as TimeIcon,
} from '@mui/icons-material';
import type { StateMachineState } from './StateBadge';

// ============================================================================
// TYPES
// ============================================================================

export interface StatusHeroProps {
  state: StateMachineState;
  symbol?: string;
  pnl?: number;
  pnlPercent?: number;
  entryPrice?: number;
  currentPrice?: number;
  sessionTime?: number; // seconds since session start
  positionTime?: number; // seconds since position opened
  signalType?: 'pump' | 'dump';
  indicatorHighlights?: { name: string; value: string }[];
  side?: 'LONG' | 'SHORT';
}

// ============================================================================
// STATE CONFIGURATION - Colors from UX Spec (Story 1A-5)
// ============================================================================

interface StateStyleConfig {
  background: string;
  backgroundHover: string;
  text: string;
  label: string;
  icon: string;
  description: string;
  pulsing: boolean;
}

const STATE_STYLES: Record<StateMachineState, StateStyleConfig> = {
  // Primary trading states
  MONITORING: {
    background: '#F8FAFC', // Slate-50
    backgroundHover: '#F1F5F9', // Slate-100
    text: '#334155', // Slate-700
    label: 'Watching',
    icon: '👀',
    description: 'Scanning for signals...',
    pulsing: false,
  },
  S1: {
    background: '#FFFBEB', // Amber-50
    backgroundHover: '#FEF3C7', // Amber-100
    text: '#78350F', // Amber-900
    label: 'Found!',
    icon: '🔥',
    description: 'Signal detected - evaluating entry',
    pulsing: true,
  },
  O1: {
    background: '#F9FAFB', // Gray-50
    backgroundHover: '#F3F4F6', // Gray-100
    text: '#374151', // Gray-700
    label: 'False Alarm',
    icon: '❌',
    description: 'Signal cancelled',
    pulsing: false,
  },
  Z1: {
    background: '#FFFBEB', // Amber-50
    backgroundHover: '#FEF3C7', // Amber-100
    text: '#78350F', // Amber-900
    label: 'Entering',
    icon: '🎯',
    description: 'Opening position...',
    pulsing: true,
  },
  POSITION_ACTIVE: {
    background: '#EFF6FF', // Blue-50
    backgroundHover: '#DBEAFE', // Blue-100
    text: '#1E3A8A', // Blue-900
    label: 'In Position',
    icon: '📈',
    description: 'Monitoring exit conditions',
    pulsing: false,
  },
  ZE1: {
    background: '#ECFDF5', // Green-50
    backgroundHover: '#D1FAE5', // Green-100
    text: '#064E3B', // Green-900
    label: 'Taking Profit',
    icon: '💰',
    description: 'Closing with profit',
    pulsing: false,
  },
  E1: {
    background: '#FEF2F2', // Red-50
    backgroundHover: '#FEE2E2', // Red-100
    text: '#7F1D1D', // Red-900
    label: 'Stopping Loss',
    icon: '🛑',
    description: 'Emergency exit',
    pulsing: false,
  },
  // Legacy states
  INACTIVE: {
    background: '#F9FAFB',
    backgroundHover: '#F3F4F6',
    text: '#6B7280',
    label: 'Inactive',
    icon: '⏸️',
    description: 'System not active',
    pulsing: false,
  },
  SIGNAL_DETECTED: {
    background: '#FFFBEB',
    backgroundHover: '#FEF3C7',
    text: '#78350F',
    label: 'Found!',
    icon: '🔥',
    description: 'Signal detected',
    pulsing: true,
  },
  EXITED: {
    background: '#ECFDF5',
    backgroundHover: '#D1FAE5',
    text: '#064E3B',
    label: 'Exited',
    icon: '✓',
    description: 'Position closed',
    pulsing: false,
  },
  ERROR: {
    background: '#FEF2F2',
    backgroundHover: '#FEE2E2',
    text: '#7F1D1D',
    label: 'Error',
    icon: '⚠️',
    description: 'Check logs',
    pulsing: false,
  },
};

// ============================================================================
// STYLED COMPONENTS
// ============================================================================

const HeroContainer = styled(Paper, {
  shouldForwardProp: (prop) => prop !== 'stateStyle' && prop !== 'pulsing',
})<{ stateStyle: StateStyleConfig; pulsing: boolean }>(({ theme, stateStyle, pulsing }) => ({
  position: 'relative', // For session timer absolute positioning
  padding: theme.spacing(4),
  borderRadius: theme.spacing(2),
  backgroundColor: stateStyle.background,
  color: stateStyle.text,
  transition: 'all 0.3s ease-in-out',
  boxShadow: `0 8px 32px ${alpha(stateStyle.text, 0.1)}`,
  border: `2px solid ${alpha(stateStyle.text, 0.1)}`,
  animation: pulsing ? 'heroPulse 2s ease-in-out infinite' : 'none',

  '&:hover': {
    backgroundColor: stateStyle.backgroundHover,
    boxShadow: `0 12px 40px ${alpha(stateStyle.text, 0.15)}`,
  },

  '@keyframes heroPulse': {
    '0%, 100%': {
      borderColor: alpha(stateStyle.text, 0.1),
    },
    '50%': {
      borderColor: alpha(stateStyle.text, 0.4),
    },
  },

  [theme.breakpoints.down('md')]: {
    padding: theme.spacing(3),
  },

  [theme.breakpoints.down('sm')]: {
    padding: theme.spacing(2),
  },
}));

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Format duration from seconds to human-readable string
 */
function formatDuration(seconds: number): string {
  if (seconds < 0) return '0s';

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  if (minutes > 0) {
    return `${minutes}m ${secs}s`;
  }
  return `${secs}s`;
}

/**
 * Format currency value
 */
function formatCurrency(value: number): string {
  const absValue = Math.abs(value);
  const sign = value >= 0 ? '+' : '-';

  if (absValue >= 1000000) {
    return `${sign}$${(absValue / 1000000).toFixed(2)}M`;
  }
  if (absValue >= 1000) {
    return `${sign}$${(absValue / 1000).toFixed(2)}K`;
  }
  return `${sign}$${absValue.toFixed(2)}`;
}

/**
 * Format percentage
 */
function formatPercent(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

/**
 * Format price
 */
function formatPrice(value: number): string {
  if (value >= 1000) {
    return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  return `$${value.toFixed(4)}`;
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const StatusHero: React.FC<StatusHeroProps> = ({
  state,
  symbol,
  pnl,
  pnlPercent,
  entryPrice,
  currentPrice,
  sessionTime,
  positionTime,
  signalType,
  indicatorHighlights,
  side,
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const isTablet = useMediaQuery(theme.breakpoints.down('md'));

  const [displayedSessionTime, setDisplayedSessionTime] = useState(sessionTime || 0);
  const [displayedPositionTime, setDisplayedPositionTime] = useState(positionTime || 0);

  // Get style configuration for current state
  const stateStyle = STATE_STYLES[state] || STATE_STYLES.MONITORING;

  // Determine if we're in a position state
  const isInPosition = state === 'POSITION_ACTIVE' || state === 'ZE1' || state === 'E1';

  // Determine P&L color
  const pnlColor = pnl !== undefined && pnl >= 0 ? '#10B981' : '#EF4444';

  // Update timers every second
  useEffect(() => {
    if (sessionTime !== undefined) {
      setDisplayedSessionTime(sessionTime);
    }
    if (positionTime !== undefined) {
      setDisplayedPositionTime(positionTime);
    }

    const interval = setInterval(() => {
      setDisplayedSessionTime((prev) => prev + 1);
      if (isInPosition) {
        setDisplayedPositionTime((prev) => prev + 1);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [sessionTime, positionTime, isInPosition]);

  // Dynamic font sizes based on viewport
  const heroFontSize = isMobile ? '2.5rem' : isTablet ? '3rem' : '3.5rem'; // 40-56px
  const stateFontSize = isMobile ? '1.25rem' : '1.5rem'; // 20-24px
  const labelFontSize = isMobile ? '0.75rem' : '0.875rem'; // 12-14px
  const valueFontSize = isMobile ? '0.875rem' : '1rem'; // 14-16px

  return (
    <HeroContainer
      elevation={0}
      stateStyle={stateStyle}
      pulsing={stateStyle.pulsing}
    >
      {/* State Header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 2,
          mb: isInPosition ? 3 : 2,
        }}
      >
        <Typography
          component="span"
          sx={{
            fontSize: stateFontSize,
            lineHeight: 1,
          }}
        >
          {stateStyle.icon}
        </Typography>
        <Typography
          variant="h4"
          component="h2"
          sx={{
            fontSize: stateFontSize,
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}
        >
          {stateStyle.label}
        </Typography>
        {symbol && (
          <Typography
            variant="body1"
            sx={{
              fontSize: valueFontSize,
              fontWeight: 500,
              opacity: 0.8,
              fontFamily: 'monospace',
            }}
          >
            {symbol}
          </Typography>
        )}
      </Box>

      {/* P&L Display (when in position) */}
      {isInPosition && pnl !== undefined && (
        <Box sx={{ textAlign: 'center', mb: 3 }}>
          <Typography
            variant="h1"
            sx={{
              fontSize: heroFontSize,
              fontWeight: 700,
              color: pnlColor,
              fontFamily: 'monospace',
              lineHeight: 1.2,
            }}
          >
            {formatCurrency(pnl)}
          </Typography>
          {pnlPercent !== undefined && (
            <Typography
              variant="h5"
              sx={{
                fontSize: isTablet ? '1.25rem' : '1.5rem',
                fontWeight: 600,
                color: pnlColor,
                opacity: 0.9,
              }}
            >
              {formatPercent(pnlPercent)}
            </Typography>
          )}
        </Box>
      )}

      {/* Signal Info (when signal detected) */}
      {(state === 'S1' || state === 'SIGNAL_DETECTED' || state === 'Z1') && signalType && (
        <Box sx={{ textAlign: 'center', mb: 2 }}>
          <Typography
            variant="h5"
            sx={{
              fontSize: isTablet ? '1.25rem' : '1.5rem',
              fontWeight: 600,
              textTransform: 'capitalize',
            }}
          >
            {signalType === 'pump' ? '📈 Pump Signal' : '📉 Dump Signal'}
          </Typography>
        </Box>
      )}

      {/* Description */}
      <Typography
        variant="body2"
        sx={{
          textAlign: 'center',
          fontSize: labelFontSize,
          opacity: 0.7,
          mb: isInPosition ? 3 : 1,
        }}
      >
        {stateStyle.description}
      </Typography>

      {/* Position Details (when in position) */}
      {isInPosition && (
        <Grid
          container
          spacing={2}
          justifyContent="center"
          sx={{
            borderTop: `1px solid ${alpha(stateStyle.text, 0.1)}`,
            pt: 2,
            mt: 1,
          }}
        >
          {side && (
            <Grid item>
              <Box sx={{ textAlign: 'center' }}>
                <Typography
                  variant="caption"
                  sx={{ fontSize: labelFontSize, opacity: 0.6, display: 'block' }}
                >
                  Side
                </Typography>
                <Typography
                  variant="body2"
                  sx={{
                    fontSize: valueFontSize,
                    fontWeight: 600,
                    color: side === 'LONG' ? '#10B981' : '#EF4444',
                  }}
                >
                  {side}
                </Typography>
              </Box>
            </Grid>
          )}

          {entryPrice !== undefined && (
            <Grid item>
              <Box sx={{ textAlign: 'center' }}>
                <Typography
                  variant="caption"
                  sx={{ fontSize: labelFontSize, opacity: 0.6, display: 'block' }}
                >
                  Entry
                </Typography>
                <Typography
                  variant="body2"
                  sx={{
                    fontSize: valueFontSize,
                    fontWeight: 500,
                    fontFamily: 'monospace',
                  }}
                >
                  {formatPrice(entryPrice)}
                </Typography>
              </Box>
            </Grid>
          )}

          {currentPrice !== undefined && (
            <Grid item>
              <Box sx={{ textAlign: 'center' }}>
                <Typography
                  variant="caption"
                  sx={{ fontSize: labelFontSize, opacity: 0.6, display: 'block' }}
                >
                  Current
                </Typography>
                <Typography
                  variant="body2"
                  sx={{
                    fontSize: valueFontSize,
                    fontWeight: 500,
                    fontFamily: 'monospace',
                  }}
                >
                  {formatPrice(currentPrice)}
                </Typography>
              </Box>
            </Grid>
          )}

          {displayedPositionTime > 0 && (
            <Grid item>
              <Box sx={{ textAlign: 'center' }}>
                <Typography
                  variant="caption"
                  sx={{ fontSize: labelFontSize, opacity: 0.6, display: 'block' }}
                >
                  Duration
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5 }}>
                  <TimeIcon sx={{ fontSize: '0.875rem', opacity: 0.6 }} />
                  <Typography
                    variant="body2"
                    sx={{
                      fontSize: valueFontSize,
                      fontWeight: 500,
                      fontFamily: 'monospace',
                    }}
                  >
                    {formatDuration(displayedPositionTime)}
                  </Typography>
                </Box>
              </Box>
            </Grid>
          )}
        </Grid>
      )}

      {/* Indicator Highlights (optional) */}
      {indicatorHighlights && indicatorHighlights.length > 0 && (
        <Grid
          container
          spacing={2}
          justifyContent="center"
          sx={{
            borderTop: `1px solid ${alpha(stateStyle.text, 0.1)}`,
            pt: 2,
            mt: 2,
          }}
        >
          {indicatorHighlights.slice(0, 3).map((indicator, index) => (
            <Grid item key={index}>
              <Box sx={{ textAlign: 'center' }}>
                <Typography
                  variant="caption"
                  sx={{ fontSize: labelFontSize, opacity: 0.6, display: 'block' }}
                >
                  {indicator.name}
                </Typography>
                <Typography
                  variant="body2"
                  sx={{
                    fontSize: valueFontSize,
                    fontWeight: 500,
                    fontFamily: 'monospace',
                  }}
                >
                  {indicator.value}
                </Typography>
              </Box>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Session Timer (subtle, bottom-right) */}
      {displayedSessionTime > 0 && (
        <Box
          sx={{
            position: 'absolute',
            bottom: 8,
            right: 16,
            display: 'flex',
            alignItems: 'center',
            gap: 0.5,
            opacity: 0.5,
          }}
        >
          <TimeIcon sx={{ fontSize: '0.75rem' }} />
          <Typography
            variant="caption"
            sx={{ fontSize: '0.75rem', fontFamily: 'monospace' }}
          >
            Session: {formatDuration(displayedSessionTime)}
          </Typography>
        </Box>
      )}
    </HeroContainer>
  );
};

export default StatusHero;
export { STATE_STYLES };
