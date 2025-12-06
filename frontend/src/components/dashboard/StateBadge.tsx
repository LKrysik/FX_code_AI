'use client';

import React, { useState, useEffect } from 'react';
import {
  Chip,
  Tooltip,
  Box,
  styled,
  alpha
} from '@mui/material';

// ============================================================================
// TYPES
// ============================================================================

export type StateMachineState =
  | 'INACTIVE'
  | 'MONITORING'
  | 'SIGNAL_DETECTED'
  | 'POSITION_ACTIVE'
  | 'EXITED'
  | 'ERROR';

export interface StateBadgeProps {
  state: StateMachineState;
  since?: string; // ISO timestamp
  size?: 'small' | 'medium' | 'large';
  showDuration?: boolean;
}

// ============================================================================
// STATE CONFIGURATION
// ============================================================================

interface StateConfig {
  color: string;
  label: string;
  icon: string;
  description: string;
}

const STATE_CONFIG: Record<StateMachineState, StateConfig> = {
  INACTIVE: {
    color: '#9e9e9e',
    label: 'Inactive',
    icon: '⏸️',
    description: 'System is not actively monitoring markets'
  },
  MONITORING: {
    color: '#4caf50',
    label: 'Monitoring',
    icon: '👁️',
    description: 'Actively scanning markets for trading signals'
  },
  SIGNAL_DETECTED: {
    color: '#ff9800',
    label: 'Signal',
    icon: '⚡',
    description: 'Trading signal detected - evaluating entry conditions'
  },
  POSITION_ACTIVE: {
    color: '#f44336',
    label: 'In Position',
    icon: '📍',
    description: 'Active position open - monitoring exit conditions'
  },
  EXITED: {
    color: '#2196f3',
    label: 'Exited',
    icon: '✓',
    description: 'Position closed successfully'
  },
  ERROR: {
    color: '#d32f2f',
    label: 'Error',
    icon: '⚠️',
    description: 'System error detected - check logs'
  }
};

// ============================================================================
// STYLED COMPONENTS
// ============================================================================

const PulsingChip = styled(Chip, {
  shouldForwardProp: (prop) => prop !== 'pulsing' && prop !== 'stateColor'
})<{ pulsing?: boolean; stateColor?: string }>(({ theme, pulsing, stateColor }) => ({
  fontWeight: 600,
  animation: pulsing ? 'pulse 2s ease-in-out infinite' : 'none',

  '@keyframes pulse': {
    '0%, 100%': {
      boxShadow: `0 0 0 0 ${alpha(stateColor || theme.palette.primary.main, 0.7)}`
    },
    '50%': {
      boxShadow: `0 0 0 8px ${alpha(stateColor || theme.palette.primary.main, 0)}`
    }
  }
}));

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Calculate duration from ISO timestamp to now
 */
function calculateDuration(since: string): string {
  try {
    const start = new Date(since).getTime();
    const now = Date.now();
    const diffMs = now - start;

    if (diffMs < 0) return '0s';

    const seconds = Math.floor(diffMs / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days}d ${hours % 24}h`;
    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  } catch (error) {
    console.error('Error calculating duration:', error);
    return 'N/A';
  }
}

/**
 * Get chip size variant
 */
function getChipSize(size?: 'small' | 'medium' | 'large'): 'small' | 'medium' {
  // MUI Chip only supports 'small' and 'medium'
  if (size === 'small') return 'small';
  return 'medium';
}

/**
 * Get font size for large variant
 */
function getFontSize(size?: 'small' | 'medium' | 'large'): string {
  if (size === 'large') return '1.1rem';
  if (size === 'small') return '0.75rem';
  return '0.875rem';
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const StateBadge: React.FC<StateBadgeProps> = ({
  state,
  since,
  size = 'medium',
  showDuration = false
}) => {
  const [duration, setDuration] = useState<string>('');
  const config = STATE_CONFIG[state];

  // Update duration every second if showDuration is enabled
  useEffect(() => {
    if (!showDuration || !since) return;

    const updateDuration = () => {
      setDuration(calculateDuration(since));
    };

    // Initial update
    updateDuration();

    // Update every second
    const interval = setInterval(updateDuration, 1000);

    return () => clearInterval(interval);
  }, [since, showDuration]);

  // Determine if should pulse (SIGNAL_DETECTED state)
  const shouldPulse = state === 'SIGNAL_DETECTED';

  // Build label with duration
  const label = showDuration && duration
    ? `${config.icon} ${config.label} (${duration})`
    : `${config.icon} ${config.label}`;

  // Build tooltip content
  const tooltipContent = (
    <Box>
      <Box sx={{ fontWeight: 'bold', mb: 0.5 }}>
        {config.label}
      </Box>
      <Box sx={{ fontSize: '0.85em', opacity: 0.9 }}>
        {config.description}
      </Box>
      {since && (
        <Box sx={{ fontSize: '0.8em', opacity: 0.7, mt: 0.5 }}>
          Since: {new Date(since).toLocaleString()}
        </Box>
      )}
    </Box>
  );

  return (
    <Tooltip
      title={tooltipContent}
      arrow
      placement="top"
    >
      <PulsingChip
        label={label}
        size={getChipSize(size)}
        pulsing={shouldPulse}
        stateColor={config.color}
        sx={{
          backgroundColor: alpha(config.color, 0.15),
          color: config.color,
          borderColor: config.color,
          border: '1px solid',
          fontSize: getFontSize(size),
          '&:hover': {
            backgroundColor: alpha(config.color, 0.25)
          }
        }}
      />
    </Tooltip>
  );
};

export default StateBadge;
