/**
 * Unified Status Utilities
 * =======================
 * Centralized status management utilities for consistent status display across the application.
 */

import React from 'react';
import { CircularProgress } from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Wifi as WifiIcon,
  WifiOff as WifiOffIcon,
  CloudOff as CloudOffIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Assessment as AssessmentIcon,
  TrendingUp as TrendingUpIcon,
} from '@mui/icons-material';

// Status Types
export type SystemStatusType = 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
export type WebSocketStatusType = 'connected' | 'disconnected' | 'connecting' | 'error';
export type OverallStatusType = 'healthy' | 'warning' | 'error';
export type SessionStatusType = 'running' | 'active' | 'stopped' | 'completed' | 'failed' | 'error';
export type SignalType = 'pump' | 'dump';
export type MarketStatusType = 'low' | 'medium' | 'high' | 'extreme';
export type CategoryType = 'Fundamental' | 'Technical' | 'Pump & Dump' | 'Risk' | 'Unknown';

// Overall Status Utilities
export const getOverallStatusColor = (status: OverallStatusType): 'success' | 'warning' | 'error' => {
  switch (status) {
    case 'healthy': return 'success';
    case 'warning': return 'warning';
    case 'error': return 'error';
  }
};

export const getOverallStatusIcon = (status: OverallStatusType): React.ReactElement => {
  switch (status) {
    case 'healthy': return <CheckCircleIcon fontSize="small" />;
    case 'warning': return <WarningIcon fontSize="small" />;
    case 'error': return <ErrorIcon fontSize="small" />;
  }
};

export const getOverallStatusText = (status: OverallStatusType): string => {
  switch (status) {
    case 'healthy': return 'All Systems Operational';
    case 'warning': return 'System Degraded';
    case 'error': return 'System Error';
  }
};

// WebSocket Status Utilities
export const getWebSocketStatusColor = (status: WebSocketStatusType): 'success' | 'warning' | 'error' | 'default' => {
  switch (status) {
    case 'connected': return 'success';
    case 'connecting': return 'warning';
    case 'disconnected': return 'warning';
    case 'error': return 'error';
  }
};

export const getWebSocketStatusIcon = (status: WebSocketStatusType): React.ReactElement => {
  switch (status) {
    case 'connected': return <WifiIcon fontSize="small" color="success" />;
    case 'connecting': return <CircularProgress size={16} color="warning" />;
    case 'disconnected': return <WifiOffIcon fontSize="small" color="warning" />;
    case 'error': return <CloudOffIcon fontSize="small" color="error" />;
  }
};

export const getWebSocketStatusText = (status: WebSocketStatusType): string => {
  switch (status) {
    case 'connected': return 'Connected';
    case 'connecting': return 'Connecting...';
    case 'disconnected': return 'Disconnected';
    case 'error': return 'Connection Error';
  }
};

// Backend Status Utilities
export const getBackendStatusColor = (status: SystemStatusType): 'success' | 'warning' | 'error' | 'default' => {
  switch (status) {
    case 'healthy': return 'success';
    case 'degraded': return 'warning';
    case 'unhealthy': return 'error';
    case 'unknown': return 'default';
  }
};

export const getBackendStatusText = (status: SystemStatusType): string => {
  switch (status) {
    case 'healthy': return 'Healthy';
    case 'degraded': return 'Degraded';
    case 'unhealthy': return 'Unhealthy';
    case 'unknown': return 'Unknown';
  }
};

// Session Status Utilities
export const getSessionStatusColor = (status: SessionStatusType): 'success' | 'warning' | 'error' | 'default' => {
  switch (status) {
    case 'running':
    case 'active':
      return 'success';
    case 'stopped':
    case 'completed':
      return 'default';
    case 'failed':
    case 'error':
      return 'error';
  }
};

export const getSessionStatusIcon = (status: SessionStatusType): React.ReactElement => {
  switch (status) {
    case 'running':
    case 'active':
      return <PlayIcon fontSize="small" />;
    case 'stopped':
    case 'completed':
      return <StopIcon fontSize="small" />;
    case 'failed':
    case 'error':
      return <ErrorIcon fontSize="small" />;
  }
};

export const getSessionStatusText = (status: SessionStatusType): string => {
  switch (status) {
    case 'running':
    case 'active':
      return 'Running';
    case 'stopped':
      return 'Stopped';
    case 'completed':
      return 'Completed';
    case 'failed':
      return 'Failed';
    case 'error':
      return 'Error';
  }
};

// Trading Performance Status
export const getPerformanceStatusColor = (value: number, threshold: number = 0): 'success' | 'error' | 'default' => {
  if (value > threshold) return 'success';
  if (value < 0) return 'error';
  return 'default';
};

export const getPerformanceStatusIcon = (value: number, threshold: number = 0): React.ReactElement => {
  if (value > threshold) return <TrendingUpIcon fontSize="small" color="success" />;
  if (value < 0) return <ErrorIcon fontSize="small" color="error" />;
  return <AssessmentIcon fontSize="small" />;
};

// Status Conversion Utilities
export const convertSessionStatusToOverall = (status: SessionStatusType): OverallStatusType => {
  switch (status) {
    case 'running':
    case 'active':
    case 'completed':
      return 'healthy';
    case 'stopped':
      return 'warning';
    case 'failed':
    case 'error':
      return 'error';
  }
};

export const convertWebSocketStatusToOverall = (status: WebSocketStatusType): OverallStatusType => {
  switch (status) {
    case 'connected':
      return 'healthy';
    case 'connecting':
    case 'disconnected':
      return 'warning';
    case 'error':
      return 'error';
  }
};

export const convertBackendStatusToOverall = (status: SystemStatusType): OverallStatusType => {
  switch (status) {
    case 'healthy':
      return 'healthy';
    case 'degraded':
      return 'warning';
    case 'unhealthy':
    case 'unknown':
      return 'error';
  }
};

// Status Priority (for combining multiple statuses)
export const getHighestPriorityStatus = (statuses: OverallStatusType[]): OverallStatusType => {
  if (statuses.includes('error')) return 'error';
  if (statuses.includes('warning')) return 'warning';
  return 'healthy';
};

// Status Validation
export const isValidStatus = (status: string, type: 'overall' | 'websocket' | 'backend' | 'session'): boolean => {
  const validStatuses = {
    overall: ['healthy', 'warning', 'error'],
    websocket: ['connected', 'disconnected', 'connecting', 'error'],
    backend: ['healthy', 'degraded', 'unhealthy', 'unknown'],
    session: ['running', 'active', 'stopped', 'completed', 'failed', 'error']
  };

  return validStatuses[type].includes(status);
};

// Status Change Detection
export const hasStatusChanged = (
  current: string,
  previous: string,
  type: 'overall' | 'websocket' | 'backend' | 'session' = 'overall'
): boolean => {
  if (!isValidStatus(current, type) || !isValidStatus(previous, type)) {
    return false;
  }

  // For session status, consider 'running' and 'active' as the same
  if (type === 'session') {
    const normalizeStatus = (status: string) =>
      status === 'running' || status === 'active' ? 'active' : status;
    return normalizeStatus(current) !== normalizeStatus(previous);
  }

  return current !== previous;
};

// Market Status Utilities (for pump magnitude, volume surge)
export const getMarketStatusColor = (value: number, type: 'magnitude' | 'surge'): 'default' | 'warning' | 'error' => {
  if (type === 'magnitude') {
    if (value > 15) return 'error';
    if (value > 8) return 'warning';
    return 'default';
  } else { // surge
    if (value > 5) return 'error';
    if (value > 3) return 'warning';
    return 'default';
  }
};

export const getMarketStatusText = (value: number, type: 'magnitude' | 'surge'): string => {
  if (type === 'magnitude') {
    if (value > 15) return 'Extreme';
    if (value > 8) return 'High';
    if (value > 3) return 'Medium';
    return 'Low';
  } else { // surge
    if (value > 5) return 'Extreme';
    if (value > 3) return 'High';
    if (value > 1.5) return 'Medium';
    return 'Low';
  }
};

// Signal Status Utilities
export const getSignalStatusColor = (signalType: SignalType): 'error' | 'warning' => {
  switch (signalType) {
    case 'pump': return 'error';
    case 'dump': return 'warning';
  }
};

export const getSignalStatusText = (signalType: SignalType): string => {
  switch (signalType) {
    case 'pump': return 'PUMP';
    case 'dump': return 'DUMP';
  }
};

// Category Status Utilities
export const getCategoryStatusColor = (category: CategoryType): 'default' | 'primary' | 'warning' | 'error' => {
  switch (category) {
    case 'Fundamental': return 'default';
    case 'Technical': return 'primary';
    case 'Pump & Dump': return 'error';
    case 'Risk': return 'warning';
    case 'Unknown': return 'default';
  }
};

// Error Handling Utilities
export type ErrorType = 'network' | 'timeout' | 'auth' | 'server' | 'client' | 'unknown';
export type ErrorSeverity = 'low' | 'medium' | 'high' | 'critical';

export interface UnifiedError {
  type: ErrorType;
  severity: ErrorSeverity;
  message: string;
  originalError?: any;
  context?: string;
  timestamp: string;
  recoverable: boolean;
  retryable: boolean;
}

export const categorizeError = (error: any, context?: string): UnifiedError => {
  const timestamp = new Date().toISOString();

  // Network errors
  if (!navigator.onLine || error.code === 'NETWORK_ERROR' || error.message?.includes('network')) {
    return {
      type: 'network',
      severity: 'high',
      message: 'Network connection error',
      originalError: error,
      context,
      timestamp,
      recoverable: true,
      retryable: true
    };
  }

  // Timeout errors
  if (error.code === 'TIMEOUT' || error.message?.includes('timeout')) {
    return {
      type: 'timeout',
      severity: 'medium',
      message: 'Request timed out',
      originalError: error,
      context,
      timestamp,
      recoverable: true,
      retryable: true
    };
  }

  // Authentication errors
  if (error.response?.status === 401 || error.response?.status === 403) {
    return {
      type: 'auth',
      severity: 'critical',
      message: 'Authentication failed',
      originalError: error,
      context,
      timestamp,
      recoverable: false,
      retryable: false
    };
  }

  // Server errors
  if (error.response?.status >= 500) {
    return {
      type: 'server',
      severity: 'high',
      message: 'Server error',
      originalError: error,
      context,
      timestamp,
      recoverable: true,
      retryable: true
    };
  }

  // Client errors
  if (error.response?.status >= 400 && error.response?.status < 500) {
    return {
      type: 'client',
      severity: 'medium',
      message: 'Client error',
      originalError: error,
      context,
      timestamp,
      recoverable: false,
      retryable: false
    };
  }

  // WebSocket specific errors
  if (error.target instanceof WebSocket) {
    return {
      type: 'network',
      severity: 'high',
      message: 'WebSocket connection error',
      originalError: error,
      context,
      timestamp,
      recoverable: true,
      retryable: true
    };
  }

  // Unknown errors
  return {
    type: 'unknown',
    severity: 'medium',
    message: error.message || 'Unknown error occurred',
    originalError: error,
    context,
    timestamp,
    recoverable: true,
    retryable: false
  };
};

export const getErrorRecoveryStrategy = (error: UnifiedError): {
  shouldRetry: boolean;
  retryDelay: number;
  maxRetries: number;
  fallbackAction?: string;
} => {
  switch (error.type) {
    case 'network':
      return {
        shouldRetry: true,
        retryDelay: 2000,
        maxRetries: 3,
        fallbackAction: 'Check network connection'
      };
    case 'timeout':
      return {
        shouldRetry: true,
        retryDelay: 1000,
        maxRetries: 2,
        fallbackAction: 'Try again later'
      };
    case 'server':
      return {
        shouldRetry: true,
        retryDelay: 5000,
        maxRetries: 2,
        fallbackAction: 'Contact support if issue persists'
      };
    case 'auth':
      return {
        shouldRetry: false,
        retryDelay: 0,
        maxRetries: 0,
        fallbackAction: 'Re-authenticate'
      };
    case 'client':
      return {
        shouldRetry: false,
        retryDelay: 0,
        maxRetries: 0,
        fallbackAction: 'Check input data'
      };
    default:
      return {
        shouldRetry: false,
        retryDelay: 0,
        maxRetries: 1,
        fallbackAction: 'Try again'
      };
  }
};

export const logUnifiedError = (error: UnifiedError): void => {
  const logMessage = `[${error.severity.toUpperCase()}] ${error.type}: ${error.message}`;
  const logData = {
    type: error.type,
    severity: error.severity,
    message: error.message,
    context: error.context,
    timestamp: error.timestamp,
    recoverable: error.recoverable,
    retryable: error.retryable,
    originalError: error.originalError?.message || error.originalError
  };

  switch (error.severity) {
    case 'critical':
      console.error(logMessage, logData);
      break;
    case 'high':
      console.error(logMessage, logData);
      break;
    case 'medium':
      console.warn(logMessage, logData);
      break;
    case 'low':
      console.info(logMessage, logData);
      break;
  }
};

// Status Message Generation
export const getStatusMessage = (
  status: OverallStatusType,
  context?: string
): string => {
  const baseMessages = {
    healthy: 'All systems are operating normally.',
    warning: 'Some systems may be experiencing issues.',
    error: 'Critical system errors detected.'
  };

  const message = baseMessages[status];

  if (context) {
    return `${context}: ${message}`;
  }

  return message;
};
