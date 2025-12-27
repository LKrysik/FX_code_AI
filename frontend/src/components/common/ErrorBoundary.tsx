/**
 * Error Boundary Component
 * =======================
 * Comprehensive error boundary with financial safety features
 * Catches React errors and provides graceful degradation
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';
import {
  Box,
  Typography,
  Button,
  Alert,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
} from '@mui/material';
import { Logger } from '@/services/frontendLogService';
import {
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  BugReport as BugReportIcon,
  Security as SecurityIcon,
} from '@mui/icons-material';

interface Props {
  children: ReactNode;
  fallback?: ReactNode | ((props: { error: Error; resetError: () => void }) => ReactNode);
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  showDetails?: boolean;
  financial?: boolean; // Special handling for financial/trading errors
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorId: string | null;
  retryCount: number;
}

export class ErrorBoundary extends Component<Props, State> {
  private maxRetries = 3;
  private retryTimeouts: NodeJS.Timeout[] = [];

  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null,
      retryCount: 0,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      error,
      errorId: `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error details
    Logger.error('ErrorBoundary.componentDidCatch', { message: 'ErrorBoundary caught an error', error, errorInfo });

    // Update state with error info
    this.setState({
      errorInfo,
    });

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Log to external service (if available)
    this.logErrorToService(error, errorInfo);

    // Financial safety: Enter read-only mode for trading errors
    if (this.props.financial && this.isFinancialError(error)) {
      this.enterFinancialSafetyMode(error);
    }
  }

  componentWillUnmount() {
    // Clean up any pending retry timeouts
    this.retryTimeouts.forEach(timeout => clearTimeout(timeout));
  }

  private isFinancialError = (error: Error): boolean => {
    const financialKeywords = [
      'trading',
      'order',
      'position',
      'balance',
      'wallet',
      'transaction',
      'market',
      'price',
      'volume',
    ];

    const errorMessage = error.message.toLowerCase();
    return financialKeywords.some(keyword => errorMessage.includes(keyword));
  };

  private enterFinancialSafetyMode = (error: Error) => {
    // Emit custom event for financial safety mode
    const event = new CustomEvent('financialError', {
      detail: {
        error: error.message,
        timestamp: Date.now(),
        component: 'ErrorBoundary',
      },
    });
    window.dispatchEvent(event);

    // Log financial safety activation
    Logger.warn('ErrorBoundary.financialSafety', { message: 'FINANCIAL SAFETY MODE ACTIVATED due to error', errorMessage: error.message });
  };

  private logErrorToService = (error: Error, errorInfo: ErrorInfo) => {
    // In a real application, this would send to error reporting service
    const errorReport = {
      errorId: this.state.errorId,
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      financial: this.props.financial,
    };

    // For now, just log with structured format
    Logger.error('ErrorBoundary.logError', { logType: 'ERROR REPORT', errorMessage: errorReport.message, ...errorReport });

    // TODO: Send to error reporting service
    // errorReportingService.send(errorReport);
  };

  private handleRetry = () => {
    if (this.state.retryCount >= this.maxRetries) {
      Logger.warn('ErrorBoundary.handleRetry', { message: 'Max retry attempts reached' });
      return;
    }

    this.setState(prevState => ({
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: prevState.retryCount + 1,
    }));

    // Add exponential backoff for retries
    const delay = Math.min(1000 * Math.pow(2, this.state.retryCount), 10000);
    const timeout = setTimeout(() => {
      Logger.info('ErrorBoundary.retry', { message: `Retrying after error (attempt ${this.state.retryCount + 1})` });
    }, delay);

    this.retryTimeouts.push(timeout);
  };

  private handleReload = () => {
    // Clear any pending timeouts
    this.retryTimeouts.forEach(timeout => clearTimeout(timeout));
    this.retryTimeouts = [];

    // Reload the page
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        if (typeof this.props.fallback === 'function') {
          return this.props.fallback({
            error: this.state.error!,
            resetError: this.handleRetry,
          });
        }
        return this.props.fallback;
      }

      // Default error UI
      return (
        <Box sx={{ p: 3, maxWidth: 800, mx: 'auto' }}>
          <Alert
            severity={this.props.financial ? "error" : "warning"}
            icon={this.props.financial ? <SecurityIcon /> : <ErrorIcon />}
            sx={{ mb: 3 }}
          >
            <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 1 }}>
              {this.props.financial ? '🚨 Trading System Error' : 'Application Error'}
            </Typography>
            <Typography variant="body2">
              {this.props.financial
                ? 'A critical error occurred in the trading system. The application has entered read-only mode for safety.'
                : 'Something went wrong. Please try refreshing the page or contact support if the problem persists.'
              }
            </Typography>
          </Alert>

          <Paper sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <BugReportIcon color="error" sx={{ mr: 1 }} />
              <Typography variant="h6">
                Error Details
              </Typography>
              {this.state.errorId && (
                <Chip
                  label={`ID: ${this.state.errorId}`}
                  size="small"
                  sx={{ ml: 'auto' }}
                />
              )}
            </Box>

            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              {this.state.error?.message || 'An unexpected error occurred'}
            </Typography>

            <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
              <Button
                variant="contained"
                color="primary"
                startIcon={<RefreshIcon />}
                onClick={this.handleRetry}
                disabled={this.state.retryCount >= this.maxRetries}
              >
                Try Again {this.state.retryCount > 0 && `(${this.state.retryCount}/${this.maxRetries})`}
              </Button>

              <Button
                variant="outlined"
                startIcon={<RefreshIcon />}
                onClick={this.handleReload}
              >
                Reload Page
              </Button>
            </Box>

            {this.props.showDetails && this.state.error && (
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    Technical Details (for developers)
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Box sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                    <Typography variant="body2" sx={{ mb: 2, fontWeight: 'bold' }}>
                      Error: {this.state.error.name}
                    </Typography>
                    <Typography variant="body2" sx={{ mb: 2, whiteSpace: 'pre-wrap' }}>
                      {this.state.error.stack}
                    </Typography>
                    {this.state.errorInfo && (
                      <>
                        <Typography variant="body2" sx={{ mb: 1, fontWeight: 'bold' }}>
                          Component Stack:
                        </Typography>
                        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                          {this.state.errorInfo.componentStack}
                        </Typography>
                      </>
                    )}
                  </Box>
                </AccordionDetails>
              </Accordion>
            )}

            {this.props.financial && (
              <Alert severity="info" sx={{ mt: 2 }}>
                <Typography variant="body2">
                  <strong>Financial Safety:</strong> The system has automatically entered read-only mode.
                  No trading operations will be allowed until the error is resolved.
                </Typography>
              </Alert>
            )}
          </Paper>
        </Box>
      );
    }

    return this.props.children;
  }
}

// Higher-order component for easy usage
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<Props, 'children'>
) {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;

  return WrappedComponent;
}

// Hook for programmatic error handling
export const useErrorHandler = () => {
  return (error: Error, context?: string) => {
    Logger.error('ErrorBoundary.useErrorHandler', { message: `Error in ${context || 'unknown context'}`, error });

    // Emit custom event for error boundary
    const event = new CustomEvent('reactError', {
      detail: {
        error,
        context,
        timestamp: Date.now(),
      },
    });
    window.dispatchEvent(event);
  };
};