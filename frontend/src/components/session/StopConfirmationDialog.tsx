/**
 * Stop Confirmation Dialog Component
 * ====================================
 * Story: 1b-8-emergency-stop-button
 *
 * Confirmation dialog for stopping a trading session.
 * Supports keyboard navigation: Enter to confirm, Esc to cancel.
 *
 * Acceptance Criteria:
 * - AC3: Pressing Esc key shows confirmation dialog: "Stop session? This cannot be undone."
 * - AC4: Confirm with Enter or cancel with Esc again
 */

'use client';

import React, { useEffect, useRef, useCallback } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Alert,
  AlertTitle,
  CircularProgress,
} from '@mui/material';
import {
  Warning as WarningIcon,
  Stop as StopIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { Logger } from '@/services/frontendLogService';

export interface StopConfirmationDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Callback when user confirms stop */
  onConfirm: () => void | Promise<void>;
  /** Callback when user cancels */
  onCancel: () => void;
  /** Whether the stop action is in progress */
  isLoading?: boolean;
  /** Session ID for display */
  sessionId?: string | null;
  /** Session type for display (backtest, paper, live) */
  sessionType?: string;
}

/**
 * Stop Confirmation Dialog
 *
 * Modal dialog that asks for confirmation before stopping a trading session.
 * Features:
 * - Keyboard shortcuts: Enter to confirm, Esc to cancel
 * - Visual warning about irreversibility
 * - Loading state during stop operation
 *
 * Usage:
 * ```tsx
 * <StopConfirmationDialog
 *   open={isOpen}
 *   onConfirm={handleConfirm}
 *   onCancel={handleCancel}
 *   sessionId="paper_20241231_123456"
 *   sessionType="paper"
 * />
 * ```
 */
export const StopConfirmationDialog: React.FC<StopConfirmationDialogProps> = ({
  open,
  onConfirm,
  onCancel,
  isLoading = false,
  sessionId,
  sessionType,
}) => {
  const confirmButtonRef = useRef<HTMLButtonElement>(null);

  // Focus management - focus confirm button when dialog opens
  useEffect(() => {
    if (open && confirmButtonRef.current) {
      // Small delay to ensure dialog is fully rendered
      const timeoutId = setTimeout(() => {
        confirmButtonRef.current?.focus();
      }, 50);
      return () => clearTimeout(timeoutId);
    }
  }, [open]);

  // Keyboard event handler for Enter and Esc
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (!open || isLoading) return;

    if (event.key === 'Enter') {
      event.preventDefault();
      event.stopPropagation();
      Logger.debug('StopConfirmationDialog.enter_pressed', {
        sessionId,
        message: 'User pressed Enter to confirm stop',
      });
      onConfirm();
    } else if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      Logger.debug('StopConfirmationDialog.escape_pressed', {
        sessionId,
        message: 'User pressed Esc to cancel stop',
      });
      onCancel();
    }
  }, [open, isLoading, onConfirm, onCancel, sessionId]);

  // Add/remove keyboard listener
  useEffect(() => {
    if (open) {
      window.addEventListener('keydown', handleKeyDown);
      return () => {
        window.removeEventListener('keydown', handleKeyDown);
      };
    }
  }, [open, handleKeyDown]);

  // Get session type display name
  const getSessionTypeDisplay = () => {
    switch (sessionType?.toLowerCase()) {
      case 'backtest':
        return 'Backtest';
      case 'paper':
        return 'Paper Trading';
      case 'live':
        return 'Live Trading';
      default:
        return 'Trading';
    }
  };

  return (
    <Dialog
      open={open}
      onClose={isLoading ? undefined : onCancel}
      aria-labelledby="stop-confirmation-dialog-title"
      aria-describedby="stop-confirmation-dialog-description"
      maxWidth="sm"
      fullWidth
      disableEscapeKeyDown={isLoading} // Prevent Esc when loading
      PaperProps={{
        sx: {
          borderTop: '4px solid',
          borderColor: 'warning.main',
        },
      }}
      data-testid="stop-confirmation-dialog"
    >
      <DialogTitle id="stop-confirmation-dialog-title">
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <WarningIcon color="warning" />
          <Typography variant="h6" component="span">
            Stop {getSessionTypeDisplay()} Session?
          </Typography>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Box id="stop-confirmation-dialog-description">
          <Typography variant="body1" sx={{ mb: 2 }}>
            This will immediately stop the current trading session.
            <strong> This action cannot be undone.</strong>
          </Typography>

          <Alert severity="warning" sx={{ mb: 2 }}>
            <AlertTitle>What will happen:</AlertTitle>
            <Box component="ul" sx={{ m: 0, pl: 2 }}>
              <li>All open positions will be closed at current prices</li>
              <li>Final P&L will be calculated</li>
              <li>Partial results will be preserved</li>
              <li>Session status will show "Stopped by user"</li>
            </Box>
          </Alert>

          {sessionId && (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{
                display: 'block',
                fontFamily: 'monospace',
                bgcolor: 'action.hover',
                p: 1,
                borderRadius: 1,
              }}
            >
              Session: {sessionId}
            </Typography>
          )}
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2, gap: 1 }}>
        <Button
          onClick={onCancel}
          disabled={isLoading}
          variant="outlined"
          color="inherit"
          startIcon={<CloseIcon />}
          data-testid="stop-dialog-cancel-button"
        >
          Cancel (Esc)
        </Button>
        <Button
          ref={confirmButtonRef}
          onClick={onConfirm}
          disabled={isLoading}
          variant="contained"
          color="error"
          startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : <StopIcon />}
          data-testid="stop-dialog-confirm-button"
        >
          {isLoading ? 'Stopping...' : 'Stop Session (Enter)'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default StopConfirmationDialog;
