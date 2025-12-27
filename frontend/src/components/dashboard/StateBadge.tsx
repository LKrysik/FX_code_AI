'use client';

import React, { useState, useEffect } from 'react';
import {
  Chip,
  Tooltip,
  Box,
  styled,
  alpha
} from '@mui/material';

// Import centralized vocabulary (Story 1A-4: Human Vocabulary Labels - AC4)
import {
  StateMachineState,
  StateVocabulary,
  STATE_VOCABULARY,
  getStateVocabulary
} from '@/utils/stateVocabulary';

// Re-export type for consumers
export type { StateMachineState };

export interface StateBadgeProps {
  state: StateMachineState;
  since?: string; // ISO timestamp
  size?: 'small' | 'medium' | 'large' | 'hero';
  showDuration?: boolean;
}

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
function getChipSize(size?: 'small' | 'medium' | 'large' | 'hero'): 'small' | 'medium' {
  // MUI Chip only supports 'small' and 'medium'
  // Hero and large use 'medium' as base with custom styling
  if (size === 'small') return 'small';
  return 'medium';
}

/**
 * Get font size based on size variant
 * Story 1A-2 AC3: Hero size requires 48px (3rem) for prominent display
 */
function getFontSize(size?: 'small' | 'medium' | 'large' | 'hero'): string {
  if (size === 'hero') return '3rem';      // 48px - Hero element (AC3)
  if (size === 'large') return '1.5rem';   // 24px
  if (size === 'small') return '0.75rem';  // 12px
  return '0.875rem';                       // 14px - medium (default)
}

/**
 * Get padding based on size variant
 */
function getPadding(size?: 'small' | 'medium' | 'large' | 'hero'): string {
  if (size === 'hero') return '24px 48px';
  if (size === 'large') return '12px 24px';
  if (size === 'small') return '4px 8px';
  return '6px 12px';
}

/**
 * Get icon size based on size variant
 */
function getIconSize(size?: 'small' | 'medium' | 'large' | 'hero'): string {
  if (size === 'hero') return '2.5rem';    // 40px
  if (size === 'large') return '1.25rem';  // 20px
  if (size === 'small') return '0.875rem'; // 14px
  return '1rem';                           // 16px
}

// ============================================================================
// HERO BADGE STYLED COMPONENT (Story 1A-2 AC3)
// ============================================================================

const HeroBadge = styled(Box, {
  shouldForwardProp: (prop) => prop !== 'pulsing' && prop !== 'stateColor'
})<{ pulsing?: boolean; stateColor?: string }>(({ theme, pulsing, stateColor }) => ({
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '16px',
  borderRadius: '16px',
  fontWeight: 700,
  boxShadow: `0 8px 32px ${alpha(stateColor || theme.palette.primary.main, 0.3)}`,
  transition: 'all 0.3s ease-in-out',
  animation: pulsing ? 'heroPulse 2s ease-in-out infinite' : 'none',

  '@keyframes heroPulse': {
    '0%, 100%': {
      transform: 'scale(1)',
      boxShadow: `0 8px 32px ${alpha(stateColor || theme.palette.primary.main, 0.3)}`
    },
    '50%': {
      transform: 'scale(1.02)',
      boxShadow: `0 12px 48px ${alpha(stateColor || theme.palette.primary.main, 0.5)}`
    }
  }
}));

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
  // Use centralized vocabulary (Story 1A-4 AC4)
  const config = getStateVocabulary(state);

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

  // Determine if should pulse (S1 or SIGNAL_DETECTED - signal detected states)
  const shouldPulse = state === 'S1' || state === 'SIGNAL_DETECTED';

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

  // Hero size uses custom Box-based component for better layout control (AC3)
  if (size === 'hero') {
    return (
      <Tooltip
        title={tooltipContent}
        arrow
        placement="top"
      >
        <HeroBadge
          pulsing={shouldPulse}
          stateColor={config.color}
          sx={{
            backgroundColor: alpha(config.color, 0.15),
            color: config.color,
            border: `2px solid ${config.color}`,
            padding: getPadding(size),
            fontSize: getFontSize(size),
            '&:hover': {
              backgroundColor: alpha(config.color, 0.25),
              transform: 'scale(1.02)'
            }
          }}
        >
          <Box
            component="span"
            sx={{
              fontSize: getIconSize(size),
              lineHeight: 1
            }}
          >
            {config.icon}
          </Box>
          <Box component="span">
            {config.label}
            {showDuration && duration && (
              <Box
                component="span"
                sx={{
                  fontSize: '0.5em',
                  opacity: 0.8,
                  ml: 2
                }}
              >
                ({duration})
              </Box>
            )}
          </Box>
        </HeroBadge>
      </Tooltip>
    );
  }

  // Standard sizes use PulsingChip
  const label = showDuration && duration
    ? `${config.icon} ${config.label} (${duration})`
    : `${config.icon} ${config.label}`;

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
          padding: getPadding(size),
          fontSize: getFontSize(size),
          transition: 'all 0.3s ease-in-out',
          '&:hover': {
            backgroundColor: alpha(config.color, 0.25)
          }
        }}
      />
    </Tooltip>
  );
};

export default StateBadge;
