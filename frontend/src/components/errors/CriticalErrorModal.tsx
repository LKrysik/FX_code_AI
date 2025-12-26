/**
 * Critical Error Modal Component
 * ==============================
 * Full-screen blocking modal for critical errors.
 * Cannot be dismissed without taking action.
 *
 * Story: 0-5-error-display-pattern
 * AC3: Critical errors (data loss risk) show full-screen modal
 * AC4: All errors include actionable recovery suggestion
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
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
  Divider,
  CircularProgress,
} from '@mui/material';
import {
  Error as ErrorIcon,
  Warning as WarningIcon,
  Security as SecurityIcon,
  Refresh as RefreshIcon,
  ExitToApp as ExitIcon,
  Phone as PhoneIcon,
} from '@mui/icons-material';
import { create } from 'zustand';

// Critical error types
export type CriticalErrorType =
  | 'position_at_risk'
  | 'data_corruption'
  | 'auth_expired'
  | 'trading_halted'
  | 'system_failure';

export interface CriticalError {
  type: CriticalErrorType;
  title: string;
  message: string;
  recovery: string;
  timestamp: Date;
  details?: string;
  actions: Array<{
    label: string;
    action: () => void | Promise<void>;
    variant: 'primary' | 'secondary';
  }>;
}

// Store for critical errors
interface CriticalErrorState {
  currentError: CriticalError | null;
  showCriticalError: (error: CriticalError) => void;
  dismissCriticalError: () => void;
}

export const useCriticalErrorStore = create<CriticalErrorState>((set) => ({
  currentError: null,
  showCriticalError: (error: CriticalError) => {
    // Log to console for debugging (AC5)
    console.error('[CRITICAL ERROR]', {
      type: error.type,
      title: error.title,
      message: error.message,
      timestamp: error.timestamp.toISOString(),
      details: error.details,
    });

    // Play alert sound if available
    try {
      const audio = new Audio('/sounds/critical-alert.mp3');
      audio.volume = 0.5;
      audio.play().catch(() => {/* Ignore if sound fails */});
    } catch {
      /* Ignore sound errors */
    }

    set({ currentError: error });
  },
  dismissCriticalError: () => set({ currentError: null }),
}));

// Error type configurations
const ERROR_CONFIGS: Record<CriticalErrorType, { icon: React.ReactNode; color: string }> = {
  position_at_risk: { icon: <SecurityIcon sx={{ fontSize: 48 }} />, color: '#f44336' },
  data_corruption: { icon: <ErrorIcon sx={{ fontSize: 48 }} />, color: '#f44336' },
  auth_expired: { icon: <ExitIcon sx={{ fontSize: 48 }} />, color: '#ff9800' },
  trading_halted: { icon: <WarningIcon sx={{ fontSize: 48 }} />, color: '#ff9800' },
  system_failure: { icon: <ErrorIcon sx={{ fontSize: 48 }} />, color: '#f44336' },
};

export const CriticalErrorModal: React.FC = () => {
  const { currentError, dismissCriticalError } = useCriticalErrorStore();
  const [isProcessing, setIsProcessing] = useState(false);

  // Prevent escape key from closing
  useEffect(() => {
    if (currentError) {
      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Escape') {
          e.preventDefault();
        }
      };
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }
  }, [currentError]);

  const handleAction = useCallback(async (action: () => void | Promise<void>) => {
    setIsProcessing(true);
    try {
      await action();
      dismissCriticalError();
    } catch (error) {
      console.error('Recovery action failed:', error);
    } finally {
      setIsProcessing(false);
    }
  }, [dismissCriticalError]);

  if (!currentError) {
    return null;
  }

  const config = ERROR_CONFIGS[currentError.type];

  return (
    <Dialog
      open={true}
      fullScreen
      disableEscapeKeyDown
      PaperProps={{
        sx: {
          backgroundColor: 'rgba(0, 0, 0, 0.95)',
        },
      }}
    >
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          p: 4,
        }}
      >
        {/* Error Icon */}
        <Box
          sx={{
            color: config.color,
            mb: 3,
            animation: 'pulse 2s infinite',
            '@keyframes pulse': {
              '0%, 100%': { opacity: 1 },
              '50%': { opacity: 0.5 },
            },
          }}
        >
          {config.icon}
        </Box>

        {/* Title */}
        <Typography
          variant="h3"
          sx={{
            color: config.color,
            fontWeight: 'bold',
            textAlign: 'center',
            mb: 2,
          }}
        >
          {currentError.title}
        </Typography>

        {/* Message */}
        <Typography
          variant="h6"
          sx={{
            color: 'white',
            textAlign: 'center',
            maxWidth: 600,
            mb: 3,
          }}
        >
          {currentError.message}
        </Typography>

        {/* Recovery Suggestion */}
        <Alert
          severity="info"
          sx={{
            maxWidth: 600,
            mb: 4,
            backgroundColor: 'rgba(33, 150, 243, 0.15)',
          }}
        >
          <AlertTitle>Recommended Action</AlertTitle>
          {currentError.recovery}
        </Alert>

        {/* Details (if available) */}
        {currentError.details && (
          <Box
            sx={{
              maxWidth: 600,
              mb: 4,
              p: 2,
              backgroundColor: 'rgba(255, 255, 255, 0.05)',
              borderRadius: 1,
            }}
          >
            <Typography variant="caption" sx={{ color: 'grey.500' }}>
              Technical Details:
            </Typography>
            <Typography variant="body2" sx={{ color: 'grey.400', fontFamily: 'monospace' }}>
              {currentError.details}
            </Typography>
          </Box>
        )}

        {/* Action Buttons */}
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', justifyContent: 'center' }}>
          {currentError.actions.map((action, index) => (
            <Button
              key={index}
              variant={action.variant === 'primary' ? 'contained' : 'outlined'}
              color={action.variant === 'primary' ? 'error' : 'inherit'}
              size="large"
              onClick={() => handleAction(action.action)}
              disabled={isProcessing}
              startIcon={isProcessing ? <CircularProgress size={20} /> : undefined}
              sx={{
                minWidth: 200,
                py: 1.5,
              }}
            >
              {action.label}
            </Button>
          ))}
        </Box>

        {/* Timestamp */}
        <Typography
          variant="caption"
          sx={{ color: 'grey.600', mt: 4 }}
        >
          Error occurred at: {currentError.timestamp.toLocaleString()}
        </Typography>

        {/* Emergency Contact */}
        <Box sx={{ mt: 3, display: 'flex', alignItems: 'center', gap: 1 }}>
          <PhoneIcon sx={{ color: 'grey.500', fontSize: 16 }} />
          <Typography variant="caption" sx={{ color: 'grey.500' }}>
            If this persists, contact system administrator
          </Typography>
        </Box>
      </Box>
    </Dialog>
  );
};

// Helper function to trigger critical errors
export const triggerCriticalError = (
  type: CriticalErrorType,
  message: string,
  recovery: string,
  actions: CriticalError['actions'],
  details?: string
) => {
  const titles: Record<CriticalErrorType, string> = {
    position_at_risk: 'Position At Risk',
    data_corruption: 'Data Corruption Detected',
    auth_expired: 'Authentication Expired',
    trading_halted: 'Trading Halted',
    system_failure: 'System Failure',
  };

  useCriticalErrorStore.getState().showCriticalError({
    type,
    title: titles[type],
    message,
    recovery,
    timestamp: new Date(),
    details,
    actions,
  });
};

export default CriticalErrorModal;
