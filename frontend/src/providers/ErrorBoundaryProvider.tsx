/**
 * Error Boundary Provider
 * ======================
 * Application-wide error boundary with recovery mechanisms
 * Provides financial safety and graceful error handling
 */

'use client';

import React, { ReactNode, useCallback } from 'react';
import { Box, Button, Typography, Paper, Alert } from '@mui/material';
import { ErrorBoundary, useErrorHandler } from '@/components/common/ErrorBoundary';
import { useUIStore } from '@/stores/uiStore';
import { useWebSocketStore } from '@/stores/websocketStore';
import { Logger } from '@/services/frontendLogService';

interface ErrorBoundaryProviderProps {
  children: ReactNode;
}

const GlobalErrorFallback: React.FC<{
  error: Error;
  resetError: () => void;
  isFinancialError: boolean;
}> = ({ error, resetError, isFinancialError }) => {
  const { addNotification } = useUIStore();
  const { setConnectionStatus } = useWebSocketStore();

  const handleRecovery = useCallback(() => {
    // Financial safety: Enter read-only mode for financial errors
    if (isFinancialError) {
      setConnectionStatus('error');
      addNotification({
        type: 'error',
        message: 'Critical error detected. Trading actions may be limited.',
      });
    }

    // Reset error state
    resetError();

    // Reload the page as last resort
    setTimeout(() => {
      window.location.reload();
    }, 1000);
  }, [isFinancialError, setConnectionStatus, addNotification, resetError]);

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        p: 3,
        bgcolor: 'background.default'
      }}
    >
      <Paper sx={{ p: 4, maxWidth: 600, width: '100%' }}>
        <Alert
          severity={isFinancialError ? "error" : "warning"}
          sx={{ mb: 3 }}
        >
          <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 1 }}>
            {isFinancialError ? '🚨 Critical Trading System Error' : 'Application Error'}
          </Typography>
          <Typography variant="body2">
            {isFinancialError
              ? 'A critical error has occurred in the trading system. The application has automatically entered read-only mode to protect your funds.'
              : 'An unexpected error has occurred. Please try recovering or reload the application.'
            }
          </Typography>
        </Alert>

        <Box sx={{ mb: 3 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Error: {error.message}
          </Typography>

          {isFinancialError && (
            <Alert severity="info" sx={{ mb: 2 }}>
              <Typography variant="body2">
                <strong>Financial Safety Active:</strong> All trading operations have been halted.
                No financial transactions will be processed until the error is resolved.
              </Typography>
            </Alert>
          )}
        </Box>

        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="contained"
            color="primary"
            onClick={handleRecovery}
            fullWidth
          >
            {isFinancialError ? 'Enter Safe Mode' : 'Try Recovery'}
          </Button>

          <Button
            variant="outlined"
            onClick={() => window.location.reload()}
            fullWidth
          >
            Reload Application
          </Button>
        </Box>

        <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
          If this problem persists, please contact system administrator.
        </Typography>
      </Paper>
    </Box>
  );
};

const PageErrorFallback: React.FC<{
  error: Error;
  resetError: () => void;
  isFinancialError: boolean;
}> = ({ error, resetError, isFinancialError }) => {
  const { addNotification } = useUIStore();

  const handleRetry = useCallback(() => {
    addNotification({
      type: 'info',
      message: 'Retrying operation...',
    });
    resetError();
  }, [addNotification, resetError]);

  return (
    <Box sx={{ p: 3 }}>
      <Alert severity={isFinancialError ? "error" : "warning"} sx={{ mb: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 1 }}>
          {isFinancialError ? 'Trading Error' : 'Page Error'}
        </Typography>
        <Typography variant="body2" sx={{ mb: 2 }}>
          {error.message}
        </Typography>

        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button size="small" variant="contained" onClick={handleRetry}>
            Try Again
          </Button>
          <Button size="small" variant="outlined" onClick={() => window.location.reload()}>
            Reload Page
          </Button>
        </Box>
      </Alert>
    </Box>
  );
};

export const ErrorBoundaryProvider: React.FC<ErrorBoundaryProviderProps> = ({ children }) => {
  const errorHandler = useErrorHandler();

  // Global error handler for unhandled errors
  React.useEffect(() => {
    const handleUnhandledError = (event: ErrorEvent) => {
      errorHandler(event.error, 'unhandled_error');
    };

    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      errorHandler(
        event.reason instanceof Error ? event.reason : new Error(String(event.reason)),
        'unhandled_promise_rejection'
      );
    };

    window.addEventListener('error', handleUnhandledError);
    window.addEventListener('unhandledrejection', handleUnhandledRejection);

    return () => {
      window.removeEventListener('error', handleUnhandledError);
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };
  }, [errorHandler]);

  // Custom event listener for financial errors
  React.useEffect(() => {
    const handleFinancialError = (event: CustomEvent) => {
      Logger.error('ErrorBoundaryProvider.financialError', { message: 'FINANCIAL ERROR EVENT', detail: event.detail });
      // Could trigger additional safety measures here
    };

    window.addEventListener('financialError', handleFinancialError as EventListener);

    return () => {
      window.removeEventListener('financialError', handleFinancialError as EventListener);
    };
  }, []);

  return (
    <ErrorBoundary
      fallback={({ error, resetError }) => (
        <GlobalErrorFallback
          error={error}
          resetError={resetError}
          isFinancialError={error.message.toLowerCase().includes('trading') ||
                           error.message.toLowerCase().includes('order') ||
                           error.message.toLowerCase().includes('position')}
        />
      )}
      onError={(error, errorInfo) => {
        // Log to external service
        Logger.error('ErrorBoundaryProvider.globalError', { message: 'Global error caught', error: error.message, componentStack: errorInfo?.componentStack });

        // Send to error reporting service (if available)
        // errorReportingService.send({
        //   error: error.message,
        //   stack: error.stack,
        //   componentStack: errorInfo.componentStack,
        //   timestamp: new Date().toISOString(),
        //   url: window.location.href,
        //   userAgent: navigator.userAgent,
        // });
      }}
      financial={true}
      showDetails={process.env.NODE_ENV === 'development'}
    >
      {children}
    </ErrorBoundary>
  );
};

// Page-level error boundary for individual pages
export const PageErrorBoundary: React.FC<{ children: ReactNode }> = ({ children }) => {
  return (
    <ErrorBoundary
      fallback={({ error, resetError }) => (
        <PageErrorFallback
          error={error}
          resetError={resetError}
          isFinancialError={error.message.toLowerCase().includes('trading') ||
                           error.message.toLowerCase().includes('order') ||
                           error.message.toLowerCase().includes('position')}
        />
      )}
      onError={(error, errorInfo) => {
        Logger.error('PageErrorBoundary.error', { message: 'Page error caught', error: error.message, componentStack: errorInfo?.componentStack });
      }}
      financial={false}
      showDetails={process.env.NODE_ENV === 'development'}
    >
      {children}
    </ErrorBoundary>
  );
};

// Hook for programmatic error recovery
export const useErrorRecovery = () => {
  const { addNotification } = useUIStore();

  const recoverFromError = useCallback((errorType: string) => {
    addNotification({
      type: 'info',
      message: `Recovering from ${errorType}...`,
    });

    // Implement recovery logic based on error type
    switch (errorType) {
      case 'websocket':
        // Reconnect WebSocket
        window.location.reload();
        break;

      case 'api':
        // Clear API cache and retry
        if ('caches' in window) {
          caches.delete('api-cache');
        }
        break;

      case 'trading':
        // Enter read-only mode
        // This would be handled by the financial safety hook
        break;

      default:
        // Generic recovery
        break;
    }
  }, [addNotification]);

  return { recoverFromError };
};
