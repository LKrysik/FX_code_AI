/**
 * Emergency Stop Button Component
 * ================================
 * Story: 1b-8-emergency-stop-button
 *
 * A prominent red STOP button that is always visible when a trading session is active.
 * Clicking the button opens a confirmation dialog before stopping the session.
 *
 * Acceptance Criteria:
 * - AC1: Prominent red "STOP" button is always visible when session is active
 * - AC2: Button is labeled clearly (text, not just icon)
 */

'use client';

import React, { useState } from 'react';
import { Button, CircularProgress, Tooltip, Box } from '@mui/material';
import { Stop as StopIcon } from '@mui/icons-material';
import { StopConfirmationDialog } from './StopConfirmationDialog';
import { useCurrentSession, useTradingActions } from '@/stores/tradingStore';
import { useUIActions } from '@/stores/uiStore';
import { Logger } from '@/services/frontendLogService';

export interface EmergencyStopButtonProps {
  /** Session ID to stop (optional - uses current session from store if not provided) */
  sessionId?: string | null;
  /** Custom callback when stop is triggered (optional - uses default store action if not provided) */
  onStop?: () => Promise<void>;
  /** Whether the button is disabled */
  disabled?: boolean;
  /** Size variant of the button */
  size?: 'small' | 'medium' | 'large';
  /** Show button only when session is active (default: true) */
  showOnlyWhenActive?: boolean;
  /** Position variant - fixed for always-visible placement */
  variant?: 'inline' | 'fixed';
}

/**
 * Emergency Stop Button
 *
 * Red stop button that opens a confirmation dialog before stopping the trading session.
 *
 * Usage:
 * ```tsx
 * // Basic usage (uses current session from store)
 * <EmergencyStopButton />
 *
 * // With custom session ID
 * <EmergencyStopButton sessionId="paper_20241231_123456" />
 *
 * // Fixed position (always visible at top-right)
 * <EmergencyStopButton variant="fixed" />
 * ```
 */
export const EmergencyStopButton: React.FC<EmergencyStopButtonProps> = ({
  sessionId: propSessionId,
  onStop: customOnStop,
  disabled = false,
  size = 'medium',
  showOnlyWhenActive = true,
  variant = 'inline',
}) => {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isStopping, setIsStopping] = useState(false);

  const currentSession = useCurrentSession();
  const { stopSession } = useTradingActions();
  const { addNotification } = useUIActions();

  // Use prop session ID or fall back to current session from store
  const sessionId = propSessionId ?? currentSession?.sessionId;
  const sessionStatus = currentSession?.status;

  // Determine if session is active
  const isSessionActive = sessionStatus === 'running' || sessionStatus === 'active';

  // Don't render if no active session and showOnlyWhenActive is true
  if (showOnlyWhenActive && !isSessionActive) {
    return null;
  }

  const handleOpenDialog = () => {
    Logger.info('EmergencyStopButton.dialog_opened', {
      sessionId,
      sessionStatus,
    });
    setIsDialogOpen(true);
  };

  const handleCloseDialog = () => {
    Logger.debug('EmergencyStopButton.dialog_closed', {
      sessionId,
    });
    setIsDialogOpen(false);
  };

  const handleConfirmStop = async () => {
    setIsStopping(true);
    const startTime = performance.now();

    Logger.warn('EmergencyStopButton.stop_confirmed', {
      sessionId,
      sessionStatus,
      message: 'User confirmed emergency stop',
    });

    try {
      if (customOnStop) {
        await customOnStop();
      } else {
        await stopSession(sessionId ?? undefined);
      }

      const duration = performance.now() - startTime;

      Logger.info('EmergencyStopButton.stop_success', {
        sessionId,
        durationMs: duration,
        message: 'Session stopped successfully',
      });

      addNotification({
        type: 'warning',
        message: 'Trading session stopped by user',
        autoHide: true,
      });

      // Close dialog on success
      setIsDialogOpen(false);

    } catch (error) {
      const duration = performance.now() - startTime;

      Logger.error('EmergencyStopButton.stop_failed', {
        sessionId,
        durationMs: duration,
        message: 'Failed to stop session',
      }, error instanceof Error ? error : undefined);

      addNotification({
        type: 'error',
        message: `Failed to stop session: ${error instanceof Error ? error.message : 'Unknown error'}`,
        autoHide: false,
      });
    } finally {
      setIsStopping(false);
    }
  };

  const buttonContent = (
    <Button
      variant="contained"
      color="error"
      size={size}
      disabled={disabled || isStopping || !isSessionActive}
      onClick={handleOpenDialog}
      startIcon={isStopping ? <CircularProgress size={20} color="inherit" /> : <StopIcon />}
      sx={{
        fontWeight: 'bold',
        minWidth: size === 'small' ? 80 : 100,
        // Pulse animation for visibility when active
        ...(isSessionActive && !isStopping && {
          animation: 'pulse-emergency 2s infinite',
          '@keyframes pulse-emergency': {
            '0%': { boxShadow: '0 0 0 0 rgba(211, 47, 47, 0.4)' },
            '70%': { boxShadow: '0 0 0 10px rgba(211, 47, 47, 0)' },
            '100%': { boxShadow: '0 0 0 0 rgba(211, 47, 47, 0)' },
          },
        }),
      }}
      aria-label="Emergency Stop - Stop trading session"
      data-testid="emergency-stop-button"
    >
      {isStopping ? 'STOPPING...' : 'STOP'}
    </Button>
  );

  // Fixed position wrapper for always-visible placement
  const wrappedButton = variant === 'fixed' ? (
    <Box
      sx={{
        position: 'fixed',
        top: 16,
        right: 16,
        zIndex: 1200, // Above most UI elements
      }}
    >
      <Tooltip title="Emergency Stop (Esc)" placement="left">
        {buttonContent}
      </Tooltip>
    </Box>
  ) : (
    <Tooltip title="Emergency Stop (Esc)">
      {buttonContent}
    </Tooltip>
  );

  return (
    <>
      {wrappedButton}

      <StopConfirmationDialog
        open={isDialogOpen}
        onConfirm={handleConfirmStop}
        onCancel={handleCloseDialog}
        isLoading={isStopping}
        sessionId={sessionId}
        sessionType={currentSession?.type ?? undefined}
      />
    </>
  );
};

export default EmergencyStopButton;
