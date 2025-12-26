/**
 * Error Toast Component
 * =====================
 * Displays transient error notifications using MUI Snackbar.
 * Integrates with UIStore for notification management.
 *
 * Story: 0-5-error-display-pattern
 * AC1: API errors display in toast/snackbar with error message
 * AC4: All errors include actionable recovery suggestion
 */

'use client';

import React from 'react';
import {
  Snackbar,
  Alert,
  AlertTitle,
  Button,
  IconButton,
  Stack,
  Box,
} from '@mui/material';
import {
  Close as CloseIcon,
  Refresh as RefreshIcon,
  Info as InfoIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  CheckCircle as SuccessIcon,
} from '@mui/icons-material';
import { useUIStore, useNotifications } from '@/stores/uiStore';

// Severity to auto-dismiss time mapping (in ms)
const SEVERITY_DISMISS_TIME: Record<string, number | null> = {
  success: 3000,
  info: 3000,
  warning: 5000,
  error: null, // Persist until dismissed
};

// Severity icons
const SEVERITY_ICONS: Record<string, React.ReactNode> = {
  success: <SuccessIcon />,
  info: <InfoIcon />,
  warning: <WarningIcon />,
  error: <ErrorIcon />,
};

interface NotificationWithActions {
  id: string;
  type: 'success' | 'info' | 'warning' | 'error';
  message: string;
  title?: string;
  recovery?: string;
  onRetry?: () => void;
  autoHide?: boolean;
  timestamp: number;
}

export const ErrorToast: React.FC = () => {
  const notifications = useNotifications() as NotificationWithActions[];
  const { removeNotification } = useUIStore();

  // Get the most recent notification
  const currentNotification = notifications[notifications.length - 1];

  if (!currentNotification) {
    return null;
  }

  const handleClose = (_event?: React.SyntheticEvent | Event, reason?: string) => {
    if (reason === 'clickaway') {
      return;
    }
    removeNotification(currentNotification.id);
  };

  const autoHideDuration = currentNotification.autoHide !== false
    ? SEVERITY_DISMISS_TIME[currentNotification.type]
    : null;

  return (
    <Snackbar
      open={true}
      autoHideDuration={autoHideDuration}
      onClose={handleClose}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      sx={{ maxWidth: 450 }}
    >
      <Alert
        severity={currentNotification.type}
        icon={SEVERITY_ICONS[currentNotification.type]}
        onClose={handleClose}
        sx={{
          width: '100%',
          alignItems: 'flex-start',
          '& .MuiAlert-message': { width: '100%' },
        }}
        action={
          <IconButton
            size="small"
            aria-label="close"
            color="inherit"
            onClick={handleClose}
          >
            <CloseIcon fontSize="small" />
          </IconButton>
        }
      >
        {currentNotification.title && (
          <AlertTitle>{currentNotification.title}</AlertTitle>
        )}

        <Box sx={{ mb: currentNotification.recovery || currentNotification.onRetry ? 1 : 0 }}>
          {currentNotification.message}
        </Box>

        {/* Recovery suggestion */}
        {currentNotification.recovery && (
          <Box sx={{ fontSize: '0.85rem', opacity: 0.9, mb: 1 }}>
            {currentNotification.recovery}
          </Box>
        )}

        {/* Action buttons */}
        {currentNotification.onRetry && (
          <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
            <Button
              size="small"
              color="inherit"
              startIcon={<RefreshIcon />}
              onClick={() => {
                currentNotification.onRetry?.();
                handleClose();
              }}
              sx={{ textTransform: 'none' }}
            >
              Retry
            </Button>
          </Stack>
        )}
      </Alert>
    </Snackbar>
  );
};

// Multiple toasts stacked (for showing all notifications)
export const ErrorToastStack: React.FC = () => {
  const notifications = useNotifications() as NotificationWithActions[];
  const { removeNotification } = useUIStore();

  return (
    <Box
      sx={{
        position: 'fixed',
        bottom: 24,
        right: 24,
        zIndex: 2000,
        display: 'flex',
        flexDirection: 'column-reverse',
        gap: 1,
        maxHeight: '80vh',
        overflow: 'hidden',
      }}
    >
      {notifications.slice(-5).map((notification) => (
        <Alert
          key={notification.id}
          severity={notification.type}
          onClose={() => removeNotification(notification.id)}
          sx={{
            minWidth: 300,
            maxWidth: 450,
            boxShadow: 3,
          }}
        >
          {notification.title && <AlertTitle>{notification.title}</AlertTitle>}
          {notification.message}
          {notification.recovery && (
            <Box sx={{ fontSize: '0.85rem', opacity: 0.9, mt: 0.5 }}>
              {notification.recovery}
            </Box>
          )}
        </Alert>
      ))}
    </Box>
  );
};

export default ErrorToast;
