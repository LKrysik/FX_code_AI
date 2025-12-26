/**
 * Error Banner Component
 * ======================
 * Persistent warning banner for connection issues.
 * Shows at top of page until issue is resolved.
 *
 * Story: 0-5-error-display-pattern
 * AC2: WebSocket disconnection shows visible banner
 * AC4: All errors include actionable recovery suggestion
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Alert,
  AlertTitle,
  Button,
  Box,
  LinearProgress,
  Collapse,
  IconButton,
  Typography,
} from '@mui/material';
import {
  WifiOff as WifiOffIcon,
  Refresh as RefreshIcon,
  Close as CloseIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { useWebSocketStore } from '@/stores/websocketStore';

interface ErrorBannerProps {
  onReconnect?: () => void;
}

export const WebSocketBanner: React.FC<ErrorBannerProps> = ({ onReconnect }) => {
  const { isConnected, connectionStatus, lastError } = useWebSocketStore();
  const [countdown, setCountdown] = useState(5);
  const [dismissed, setDismissed] = useState(false);
  const [autoReconnectAttempts, setAutoReconnectAttempts] = useState(0);

  // Reset dismissed state when connection changes
  useEffect(() => {
    if (isConnected) {
      setDismissed(false);
      setAutoReconnectAttempts(0);
    }
  }, [isConnected]);

  // Countdown for reconnection
  useEffect(() => {
    if (!isConnected && connectionStatus !== 'connecting' && !dismissed) {
      const timer = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            // Auto-reconnect attempt
            setAutoReconnectAttempts((a) => a + 1);
            onReconnect?.();
            return 5 + autoReconnectAttempts * 2; // Increase wait time with each attempt
          }
          return prev - 1;
        });
      }, 1000);

      return () => clearInterval(timer);
    }
  }, [isConnected, connectionStatus, dismissed, onReconnect, autoReconnectAttempts]);

  // Don't show if connected or dismissed
  if (isConnected || dismissed) {
    return null;
  }

  const isConnecting = connectionStatus === 'connecting';

  return (
    <Collapse in={!isConnected && !dismissed}>
      <Alert
        severity={connectionStatus === 'error' ? 'error' : 'warning'}
        icon={<WifiOffIcon />}
        sx={{
          borderRadius: 0,
          '& .MuiAlert-message': { width: '100%' },
        }}
        action={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Button
              color="inherit"
              size="small"
              startIcon={<RefreshIcon />}
              onClick={() => {
                setCountdown(5);
                onReconnect?.();
              }}
              disabled={isConnecting}
            >
              {isConnecting ? 'Connecting...' : 'Reconnect Now'}
            </Button>
            <IconButton
              size="small"
              color="inherit"
              onClick={() => setDismissed(true)}
              aria-label="dismiss"
            >
              <CloseIcon fontSize="small" />
            </IconButton>
          </Box>
        }
      >
        <AlertTitle>Connection Lost</AlertTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="body2">
            {isConnecting
              ? 'Attempting to reconnect...'
              : `Auto-reconnecting in ${countdown}s...`}
          </Typography>
          {lastError && (
            <Typography variant="caption" sx={{ opacity: 0.8 }}>
              ({lastError})
            </Typography>
          )}
        </Box>
        {isConnecting && <LinearProgress sx={{ mt: 1 }} />}
      </Alert>
    </Collapse>
  );
};

// Generic error banner for other persistent warnings
interface GenericBannerProps {
  severity: 'info' | 'warning' | 'error';
  title: string;
  message: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  dismissible?: boolean;
  onDismiss?: () => void;
}

export const GenericBanner: React.FC<GenericBannerProps> = ({
  severity,
  title,
  message,
  action,
  dismissible = true,
  onDismiss,
}) => {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) {
    return null;
  }

  return (
    <Alert
      severity={severity}
      icon={<WarningIcon />}
      sx={{
        borderRadius: 0,
        '& .MuiAlert-message': { width: '100%' },
      }}
      action={
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {action && (
            <Button color="inherit" size="small" onClick={action.onClick}>
              {action.label}
            </Button>
          )}
          {dismissible && (
            <IconButton
              size="small"
              color="inherit"
              onClick={() => {
                setDismissed(true);
                onDismiss?.();
              }}
              aria-label="dismiss"
            >
              <CloseIcon fontSize="small" />
            </IconButton>
          )}
        </Box>
      }
    >
      <AlertTitle>{title}</AlertTitle>
      {message}
    </Alert>
  );
};

export default WebSocketBanner;
