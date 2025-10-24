/**
 * Unit Tests for Status Utilities
 * ===============================
 * Tests for all status utility functions to ensure consistent behavior.
 */

import {
  getOverallStatusColor,
  getOverallStatusIcon,
  getOverallStatusText,
  getWebSocketStatusColor,
  getWebSocketStatusIcon,
  getWebSocketStatusText,
  getBackendStatusColor,
  getBackendStatusText,
  getSessionStatusColor,
  getSessionStatusIcon,
  getSessionStatusText,
  getPerformanceStatusColor,
  getPerformanceStatusIcon,
  getMarketStatusColor,
  getMarketStatusText,
  getSignalStatusColor,
  getSignalStatusText,
  getCategoryStatusColor,
  convertSessionStatusToOverall,
  convertWebSocketStatusToOverall,
  convertBackendStatusToOverall,
  getHighestPriorityStatus,
  isValidStatus,
  hasStatusChanged,
  categorizeError,
  getErrorRecoveryStrategy,
  logUnifiedError,
  getStatusMessage,
  type OverallStatusType,
  type WebSocketStatusType,
  type SystemStatusType,
  type SessionStatusType,
  type SignalType,
  type CategoryType,
  type ErrorType
} from './statusUtils';

describe('Overall Status Utilities', () => {
  describe('getOverallStatusColor', () => {
    test('returns success for healthy status', () => {
      expect(getOverallStatusColor('healthy')).toBe('success');
    });

    test('returns warning for warning status', () => {
      expect(getOverallStatusColor('warning')).toBe('warning');
    });

    test('returns error for error status', () => {
      expect(getOverallStatusColor('error')).toBe('error');
    });
  });

  describe('getOverallStatusText', () => {
    test('returns correct text for healthy status', () => {
      expect(getOverallStatusText('healthy')).toBe('All Systems Operational');
    });

    test('returns correct text for warning status', () => {
      expect(getOverallStatusText('warning')).toBe('System Degraded');
    });

    test('returns correct text for error status', () => {
      expect(getOverallStatusText('error')).toBe('System Error');
    });
  });
});

describe('WebSocket Status Utilities', () => {
  describe('getWebSocketStatusColor', () => {
    test('returns success for connected status', () => {
      expect(getWebSocketStatusColor('connected')).toBe('success');
    });

    test('returns warning for connecting status', () => {
      expect(getWebSocketStatusColor('connecting')).toBe('warning');
    });

    test('returns warning for disconnected status', () => {
      expect(getWebSocketStatusColor('disconnected')).toBe('warning');
    });

    test('returns error for error status', () => {
      expect(getWebSocketStatusColor('error')).toBe('error');
    });
  });

  describe('getWebSocketStatusText', () => {
    test('returns correct text for connected status', () => {
      expect(getWebSocketStatusText('connected')).toBe('Connected');
    });

    test('returns correct text for connecting status', () => {
      expect(getWebSocketStatusText('connecting')).toBe('Connecting...');
    });

    test('returns correct text for disconnected status', () => {
      expect(getWebSocketStatusText('disconnected')).toBe('Disconnected');
    });

    test('returns correct text for error status', () => {
      expect(getWebSocketStatusText('error')).toBe('Connection Error');
    });
  });
});

describe('Backend Status Utilities', () => {
  describe('getBackendStatusColor', () => {
    test('returns success for healthy status', () => {
      expect(getBackendStatusColor('healthy')).toBe('success');
    });

    test('returns warning for degraded status', () => {
      expect(getBackendStatusColor('degraded')).toBe('warning');
    });

    test('returns error for unhealthy status', () => {
      expect(getBackendStatusColor('unhealthy')).toBe('error');
    });

    test('returns default for unknown status', () => {
      expect(getBackendStatusColor('unknown')).toBe('default');
    });
  });

  describe('getBackendStatusText', () => {
    test('returns correct text for healthy status', () => {
      expect(getBackendStatusText('healthy')).toBe('Healthy');
    });

    test('returns correct text for degraded status', () => {
      expect(getBackendStatusText('degraded')).toBe('Degraded');
    });

    test('returns correct text for unhealthy status', () => {
      expect(getBackendStatusText('unhealthy')).toBe('Unhealthy');
    });

    test('returns correct text for unknown status', () => {
      expect(getBackendStatusText('unknown')).toBe('Unknown');
    });
  });
});

describe('Session Status Utilities', () => {
  describe('getSessionStatusColor', () => {
    test('returns success for running status', () => {
      expect(getSessionStatusColor('running')).toBe('success');
    });

    test('returns success for active status', () => {
      expect(getSessionStatusColor('active')).toBe('success');
    });

    test('returns default for stopped status', () => {
      expect(getSessionStatusColor('stopped')).toBe('default');
    });

    test('returns default for completed status', () => {
      expect(getSessionStatusColor('completed')).toBe('default');
    });

    test('returns error for failed status', () => {
      expect(getSessionStatusColor('failed')).toBe('error');
    });

    test('returns error for error status', () => {
      expect(getSessionStatusColor('error')).toBe('error');
    });
  });

  describe('getSessionStatusText', () => {
    test('returns correct text for running status', () => {
      expect(getSessionStatusText('running')).toBe('Running');
    });

    test('returns correct text for active status', () => {
      expect(getSessionStatusText('active')).toBe('Running');
    });

    test('returns correct text for stopped status', () => {
      expect(getSessionStatusText('stopped')).toBe('Stopped');
    });

    test('returns correct text for completed status', () => {
      expect(getSessionStatusText('completed')).toBe('Completed');
    });

    test('returns correct text for failed status', () => {
      expect(getSessionStatusText('failed')).toBe('Failed');
    });

    test('returns correct text for error status', () => {
      expect(getSessionStatusText('error')).toBe('Error');
    });
  });
});

describe('Performance Status Utilities', () => {
  describe('getPerformanceStatusColor', () => {
    test('returns success for positive values', () => {
      expect(getPerformanceStatusColor(100)).toBe('success');
      expect(getPerformanceStatusColor(0.01)).toBe('success');
    });

    test('returns error for negative values', () => {
      expect(getPerformanceStatusColor(-100)).toBe('error');
      expect(getPerformanceStatusColor(-0.01)).toBe('error');
    });

    test('returns default for zero', () => {
      expect(getPerformanceStatusColor(0)).toBe('default');
    });

    test('respects custom threshold', () => {
      expect(getPerformanceStatusColor(50, 100)).toBe('error');
      expect(getPerformanceStatusColor(150, 100)).toBe('success');
    });
  });
});

describe('Market Status Utilities', () => {
  describe('getMarketStatusColor', () => {
    test('returns correct colors for magnitude', () => {
      expect(getMarketStatusColor(5, 'magnitude')).toBe('default');
      expect(getMarketStatusColor(10, 'magnitude')).toBe('warning');
      expect(getMarketStatusColor(20, 'magnitude')).toBe('error');
    });

    test('returns correct colors for surge', () => {
      expect(getMarketStatusColor(1, 'surge')).toBe('default');
      expect(getMarketStatusColor(4, 'surge')).toBe('warning');
      expect(getMarketStatusColor(6, 'surge')).toBe('error');
    });
  });

  describe('getMarketStatusText', () => {
    test('returns correct text for magnitude', () => {
      expect(getMarketStatusText(2, 'magnitude')).toBe('Low');
      expect(getMarketStatusText(5, 'magnitude')).toBe('Medium');
      expect(getMarketStatusText(10, 'magnitude')).toBe('High');
      expect(getMarketStatusText(20, 'magnitude')).toBe('Extreme');
    });

    test('returns correct text for surge', () => {
      expect(getMarketStatusText(1, 'surge')).toBe('Low');
      expect(getMarketStatusText(2, 'surge')).toBe('Medium');
      expect(getMarketStatusText(4, 'surge')).toBe('High');
      expect(getMarketStatusText(6, 'surge')).toBe('Extreme');
    });
  });
});

describe('Signal Status Utilities', () => {
  describe('getSignalStatusColor', () => {
    test('returns error for pump signals', () => {
      expect(getSignalStatusColor('pump')).toBe('error');
    });

    test('returns warning for dump signals', () => {
      expect(getSignalStatusColor('dump')).toBe('warning');
    });
  });

  describe('getSignalStatusText', () => {
    test('returns correct text for pump signals', () => {
      expect(getSignalStatusText('pump')).toBe('PUMP');
    });

    test('returns correct text for dump signals', () => {
      expect(getSignalStatusText('dump')).toBe('DUMP');
    });
  });
});

describe('Category Status Utilities', () => {
  describe('getCategoryStatusColor', () => {
    test('returns correct colors for different categories', () => {
      expect(getCategoryStatusColor('Fundamental')).toBe('default');
      expect(getCategoryStatusColor('Technical')).toBe('primary');
      expect(getCategoryStatusColor('Pump & Dump')).toBe('error');
      expect(getCategoryStatusColor('Risk')).toBe('warning');
      expect(getCategoryStatusColor('Unknown')).toBe('default');
    });
  });
});

describe('Status Conversion Utilities', () => {
  describe('convertSessionStatusToOverall', () => {
    test('converts running/active/completed to healthy', () => {
      expect(convertSessionStatusToOverall('running')).toBe('healthy');
      expect(convertSessionStatusToOverall('active')).toBe('healthy');
      expect(convertSessionStatusToOverall('completed')).toBe('healthy');
    });

    test('converts stopped to warning', () => {
      expect(convertSessionStatusToOverall('stopped')).toBe('warning');
    });

    test('converts failed/error to error', () => {
      expect(convertSessionStatusToOverall('failed')).toBe('error');
      expect(convertSessionStatusToOverall('error')).toBe('error');
    });
  });

  describe('convertWebSocketStatusToOverall', () => {
    test('converts connected to healthy', () => {
      expect(convertWebSocketStatusToOverall('connected')).toBe('healthy');
    });

    test('converts connecting/disconnected to warning', () => {
      expect(convertWebSocketStatusToOverall('connecting')).toBe('warning');
      expect(convertWebSocketStatusToOverall('disconnected')).toBe('warning');
    });

    test('converts error to error', () => {
      expect(convertWebSocketStatusToOverall('error')).toBe('error');
    });
  });

  describe('convertBackendStatusToOverall', () => {
    test('converts healthy to healthy', () => {
      expect(convertBackendStatusToOverall('healthy')).toBe('healthy');
    });

    test('converts degraded to warning', () => {
      expect(convertBackendStatusToOverall('degraded')).toBe('warning');
    });

    test('converts unhealthy/unknown to error', () => {
      expect(convertBackendStatusToOverall('unhealthy')).toBe('error');
      expect(convertBackendStatusToOverall('unknown')).toBe('error');
    });
  });
});

describe('Status Priority Utilities', () => {
  describe('getHighestPriorityStatus', () => {
    test('returns error when error is present', () => {
      expect(getHighestPriorityStatus(['healthy', 'warning', 'error'])).toBe('error');
      expect(getHighestPriorityStatus(['error', 'healthy'])).toBe('error');
    });

    test('returns warning when no error but warning present', () => {
      expect(getHighestPriorityStatus(['healthy', 'warning'])).toBe('warning');
    });

    test('returns healthy when only healthy statuses', () => {
      expect(getHighestPriorityStatus(['healthy', 'healthy'])).toBe('healthy');
    });
  });
});

describe('Status Validation Utilities', () => {
  describe('isValidStatus', () => {
    test('validates overall status correctly', () => {
      expect(isValidStatus('healthy', 'overall')).toBe(true);
      expect(isValidStatus('warning', 'overall')).toBe(true);
      expect(isValidStatus('error', 'overall')).toBe(true);
      expect(isValidStatus('invalid', 'overall')).toBe(false);
    });

    test('validates websocket status correctly', () => {
      expect(isValidStatus('connected', 'websocket')).toBe(true);
      expect(isValidStatus('connecting', 'websocket')).toBe(true);
      expect(isValidStatus('disconnected', 'websocket')).toBe(true);
      expect(isValidStatus('error', 'websocket')).toBe(true);
      expect(isValidStatus('invalid', 'websocket')).toBe(false);
    });

    test('validates backend status correctly', () => {
      expect(isValidStatus('healthy', 'backend')).toBe(true);
      expect(isValidStatus('degraded', 'backend')).toBe(true);
      expect(isValidStatus('unhealthy', 'backend')).toBe(true);
      expect(isValidStatus('unknown', 'backend')).toBe(true);
      expect(isValidStatus('invalid', 'backend')).toBe(false);
    });

    test('validates session status correctly', () => {
      expect(isValidStatus('running', 'session')).toBe(true);
      expect(isValidStatus('active', 'session')).toBe(true);
      expect(isValidStatus('stopped', 'session')).toBe(true);
      expect(isValidStatus('completed', 'session')).toBe(true);
      expect(isValidStatus('failed', 'session')).toBe(true);
      expect(isValidStatus('error', 'session')).toBe(true);
      expect(isValidStatus('invalid', 'session')).toBe(false);
    });
  });

  describe('hasStatusChanged', () => {
    test('detects status changes', () => {
      expect(hasStatusChanged('healthy', 'warning', 'overall')).toBe(true);
      expect(hasStatusChanged('healthy', 'healthy', 'overall')).toBe(false);
    });

    test('handles invalid statuses', () => {
      expect(hasStatusChanged('invalid', 'healthy', 'overall')).toBe(false);
      expect(hasStatusChanged('healthy', 'invalid', 'overall')).toBe(false);
    });

    test('normalizes session statuses', () => {
      expect(hasStatusChanged('running', 'active', 'session')).toBe(false);
      expect(hasStatusChanged('running', 'stopped', 'session')).toBe(true);
    });
  });
});

describe('Error Handling Utilities', () => {
  describe('categorizeError', () => {
    test('categorizes network errors', () => {
      const error = { message: 'Network error' };
      const result = categorizeError(error, 'test context');

      expect(result.type).toBe('network');
      expect(result.severity).toBe('high');
      expect(result.recoverable).toBe(true);
      expect(result.retryable).toBe(true);
      expect(result.context).toBe('test context');
    });

    test('categorizes timeout errors', () => {
      const error = { code: 'TIMEOUT' };
      const result = categorizeError(error);

      expect(result.type).toBe('timeout');
      expect(result.severity).toBe('medium');
    });

    test('categorizes authentication errors', () => {
      const error = { response: { status: 401 } };
      const result = categorizeError(error);

      expect(result.type).toBe('auth');
      expect(result.severity).toBe('critical');
      expect(result.recoverable).toBe(false);
      expect(result.retryable).toBe(false);
    });

    test('categorizes server errors', () => {
      const error = { response: { status: 500 } };
      const result = categorizeError(error);

      expect(result.type).toBe('server');
      expect(result.severity).toBe('high');
      expect(result.recoverable).toBe(true);
      expect(result.retryable).toBe(true);
    });

    test('categorizes client errors', () => {
      const error = { response: { status: 400 } };
      const result = categorizeError(error);

      expect(result.type).toBe('client');
      expect(result.severity).toBe('medium');
      expect(result.recoverable).toBe(false);
      expect(result.retryable).toBe(false);
    });

    test('categorizes WebSocket errors', () => {
      const error = { target: new WebSocket('ws://test') };
      const result = categorizeError(error);

      expect(result.type).toBe('network');
      expect(result.severity).toBe('high');
    });

    test('categorizes unknown errors', () => {
      const error = { message: 'Unknown error' };
      const result = categorizeError(error);

      expect(result.type).toBe('unknown');
      expect(result.severity).toBe('medium');
      expect(result.recoverable).toBe(true);
      expect(result.retryable).toBe(false);
    });
  });

  describe('getErrorRecoveryStrategy', () => {
    test('provides correct recovery strategy for network errors', () => {
      const error = { type: 'network' as ErrorType, severity: 'high' as any, message: '', timestamp: '', recoverable: true, retryable: true };
      const strategy = getErrorRecoveryStrategy(error);

      expect(strategy.shouldRetry).toBe(true);
      expect(strategy.retryDelay).toBe(2000);
      expect(strategy.maxRetries).toBe(3);
      expect(strategy.fallbackAction).toBe('Check network connection');
    });

    test('provides correct recovery strategy for timeout errors', () => {
      const error = { type: 'timeout' as ErrorType, severity: 'medium' as any, message: '', timestamp: '', recoverable: true, retryable: true };
      const strategy = getErrorRecoveryStrategy(error);

      expect(strategy.shouldRetry).toBe(true);
      expect(strategy.retryDelay).toBe(1000);
      expect(strategy.maxRetries).toBe(2);
      expect(strategy.fallbackAction).toBe('Try again later');
    });

    test('provides correct recovery strategy for auth errors', () => {
      const error = { type: 'auth' as ErrorType, severity: 'critical' as any, message: '', timestamp: '', recoverable: false, retryable: false };
      const strategy = getErrorRecoveryStrategy(error);

      expect(strategy.shouldRetry).toBe(false);
      expect(strategy.retryDelay).toBe(0);
      expect(strategy.maxRetries).toBe(0);
      expect(strategy.fallbackAction).toBe('Re-authenticate');
    });
  });
});

describe('Status Message Generation', () => {
  describe('getStatusMessage', () => {
    test('returns base message for healthy status', () => {
      expect(getStatusMessage('healthy')).toBe('All systems are operating normally.');
    });

    test('returns base message for warning status', () => {
      expect(getStatusMessage('warning')).toBe('Some systems may be experiencing issues.');
    });

    test('returns base message for error status', () => {
      expect(getStatusMessage('error')).toBe('Critical system errors detected.');
    });

    test('includes context when provided', () => {
      expect(getStatusMessage('healthy', 'Dashboard')).toBe('Dashboard: All systems are operating normally.');
    });
  });
});
