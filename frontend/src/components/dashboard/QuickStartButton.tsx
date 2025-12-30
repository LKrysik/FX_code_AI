'use client';

/**
 * QuickStartButton Component
 * ==========================
 * Story 1A-8: Quick Start Option (AC1, AC4)
 *
 * Prominent button for new traders to quickly load a demo strategy.
 * Removes friction by providing immediate signal visibility.
 *
 * Features:
 * - Loads pre-configured pump detection strategy
 * - Non-destructive (doesn't overwrite user strategies)
 * - Visual feedback during loading
 *
 * Placement: Dashboard empty state, next to "Start Session" flow
 */

import React from 'react';
import { Button, CircularProgress, Tooltip } from '@mui/material';
import { RocketLaunch as RocketIcon } from '@mui/icons-material';
import { getQuickStartStrategy, type QuickStartStrategy } from '@/constants/quickStartStrategy';

export interface QuickStartButtonProps {
  /** Callback when Quick Start is clicked, receives the template strategy */
  onQuickStart: (strategy: QuickStartStrategy) => void;
  /** Whether the button is visible (default: true) */
  visible?: boolean;
  /** Whether the button is in loading state */
  loading?: boolean;
  /** Whether the button is disabled */
  disabled?: boolean;
  /** Optional size variant */
  size?: 'small' | 'medium' | 'large';
}

/**
 * QuickStartButton - Load demo strategy with one click
 *
 * @example
 * ```tsx
 * <QuickStartButton
 *   onQuickStart={(strategy) => {
 *     // Load strategy and open session config
 *     setDemoStrategy(strategy);
 *     openSessionConfig();
 *   }}
 * />
 * ```
 */
const QuickStartButton: React.FC<QuickStartButtonProps> = ({
  onQuickStart,
  visible = true,
  loading = false,
  disabled = false,
  size = 'large',
}) => {
  if (!visible) {
    return null;
  }

  const handleClick = () => {
    if (loading || disabled) return;

    // Get fresh copy of template strategy
    const strategy = getQuickStartStrategy();
    onQuickStart(strategy);
  };

  return (
    <Tooltip
      title="Load a demo pump detection strategy and start immediately"
      placement="top"
    >
      <span>
        <Button
          variant="contained"
          color="primary"
          size={size}
          onClick={handleClick}
          disabled={loading || disabled}
          startIcon={
            loading ? (
              <CircularProgress size={20} color="inherit" />
            ) : (
              <RocketIcon />
            )
          }
          sx={{
            minWidth: 160,
            fontWeight: 600,
            py: size === 'large' ? 1.5 : 1,
            px: size === 'large' ? 4 : 3,
          }}
        >
          {loading ? 'Loading...' : '🚀 Quick Start'}
        </Button>
      </span>
    </Tooltip>
  );
};

export default QuickStartButton;
