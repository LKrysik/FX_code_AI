/**
 * Safety Guards Utility
 * ====================
 * Comprehensive safety validation for financial operations
 * Prevents unsafe trading operations and data corruption
 */

import { useWebSocketStore } from '@/stores/websocketStore';
import { useUIStore } from '@/stores/uiStore';
import { useTradingStore } from '@/stores/tradingStore';
import { Logger } from '@/services/frontendLogService';

// Types for safety validation
export interface SafetyContext {
  operation: string;
  amount?: number;
  symbol?: string;
  userId?: string;
  sessionId?: string;
  timestamp: number;
}

export interface SafetyResult {
  safe: boolean;
  risk: 'low' | 'medium' | 'high' | 'critical';
  reasons: string[];
  recommendations: string[];
  blocked: boolean;
}

// Core safety validators
export class SafetyValidators {
  // Connection safety
  static validateConnection(): SafetyResult {
    const { isConnected, connectionStatus } = useWebSocketStore.getState();

    if (!isConnected) {
      return {
        safe: false,
        risk: 'critical',
        reasons: ['No WebSocket connection'],
        recommendations: ['Wait for connection to be restored', 'Check network connectivity'],
        blocked: true,
      };
    }

    if (connectionStatus === 'error') {
      return {
        safe: false,
        risk: 'high',
        reasons: ['WebSocket connection error'],
        recommendations: ['Reconnect WebSocket', 'Check server status'],
        blocked: true,
      };
    }

    return {
      safe: true,
      risk: 'low',
      reasons: [],
      recommendations: [],
      blocked: false,
    };
  }


  // Session safety
  static validateSession(): SafetyResult {
    const { currentSession } = useTradingStore.getState();

    if (!currentSession) {
      return {
        safe: false,
        risk: 'medium',
        reasons: ['No active trading session'],
        recommendations: ['Start a trading session first'],
        blocked: false, // Warning but not blocked
      };
    }

    const invalidStatuses = ['error', 'stopped', 'failed'];
    if (invalidStatuses.includes(currentSession.status || '')) {
      return {
        safe: false,
        risk: 'high',
        reasons: [`Session status: ${currentSession.status}`],
        recommendations: ['Restart session', 'Check session configuration'],
        blocked: true,
      };
    }

    return {
      safe: true,
      risk: 'low',
      reasons: [],
      recommendations: [],
      blocked: false,
    };
  }

  // Trading amount safety
  static validateTradingAmount(amount: number, context: SafetyContext): SafetyResult {
    const reasons: string[] = [];
    const recommendations: string[] = [];

    // Check for zero or negative amounts
    if (amount <= 0) {
      reasons.push('Invalid amount: must be positive');
      recommendations.push('Enter a valid positive amount');
    }

    // Check for unreasonably large amounts
    if (amount > 1000000) { // 1M USD equivalent
      reasons.push('Amount too large');
      recommendations.push('Consider splitting into smaller orders');
    }

    // Check for dust amounts
    if (amount < 0.01) {
      reasons.push('Amount too small (dust)');
      recommendations.push('Minimum order size is 0.01');
    }

    // Check for suspicious patterns (e.g., all 9s)
    const amountStr = amount.toString();
    if (amountStr.includes('99999') || amountStr.includes('88888')) {
      reasons.push('Suspicious amount pattern detected');
      recommendations.push('Use normal amount values');
    }

    const risk = reasons.length > 1 ? 'high' : reasons.length > 0 ? 'medium' : 'low';

    return {
      safe: reasons.length === 0,
      risk,
      reasons,
      recommendations,
      blocked: risk === 'high' || reasons.includes('Invalid amount'),
    };
  }

  // Symbol safety
  static validateSymbol(symbol: string): SafetyResult {
    const reasons: string[] = [];
    const recommendations: string[] = [];

    // Check format
    if (!/^[A-Z0-9]+_[A-Z0-9]+$/.test(symbol)) {
      reasons.push('Invalid symbol format');
      recommendations.push('Use format: BASE_QUOTE (e.g., BTC_USDT)');
    }

    // Check for suspicious symbols
    if (symbol.includes('TEST') || symbol.includes('FAKE')) {
      reasons.push('Test symbol detected');
      recommendations.push('Use real trading symbols only');
    }

    // Check length
    if (symbol.length > 20) {
      reasons.push('Symbol too long');
      recommendations.push('Check symbol format');
    }

    return {
      safe: reasons.length === 0,
      risk: reasons.length > 0 ? 'medium' : 'low',
      reasons,
      recommendations,
      blocked: reasons.includes('Invalid symbol format'),
    };
  }

  // Rate limiting safety
  static validateRateLimit(operation: string, context: SafetyContext): SafetyResult {
    // Simple rate limiting check (in real app, use proper rate limiter)
    const now = Date.now();
    const recentOperations = JSON.parse(
      localStorage.getItem(`rate_limit_${operation}`) || '[]'
    ).filter((timestamp: number) => now - timestamp < 60000); // Last minute

    // Allow max 10 operations per minute
    if (recentOperations.length >= 10) {
      return {
        safe: false,
        risk: 'high',
        reasons: ['Rate limit exceeded'],
        recommendations: ['Wait before making more requests', 'Reduce operation frequency'],
        blocked: true,
      };
    }

    // Update rate limit tracking
    recentOperations.push(now);
    localStorage.setItem(`rate_limit_${operation}`, JSON.stringify(recentOperations));

    return {
      safe: true,
      risk: 'low',
      reasons: [],
      recommendations: [],
      blocked: false,
    };
  }
}

// Main safety guard function
export function validateSafety(operation: string, context: SafetyContext): SafetyResult {
  const results: SafetyResult[] = [];

  // Always check connection
  results.push(SafetyValidators.validateConnection());

  // Check session for trading operations
  if (operation.includes('trade') || operation.includes('order')) {
    results.push(SafetyValidators.validateSession());
  }

  // Validate amount if provided
  if (context.amount !== undefined) {
    results.push(SafetyValidators.validateTradingAmount(context.amount, context));
  }

  // Validate symbol if provided
  if (context.symbol) {
    results.push(SafetyValidators.validateSymbol(context.symbol));
  }

  // Check rate limiting
  results.push(SafetyValidators.validateRateLimit(operation, context));

  // Combine results
  const blocked = results.some(r => r.blocked);
  const hasErrors = results.some(r => !r.safe);
  const allReasons = results.flatMap(r => r.reasons);
  const allRecommendations = results.flatMap(r => r.recommendations);

  // Determine overall risk level
  const riskLevels = results.map(r => r.risk);
  const riskPriority = { critical: 4, high: 3, medium: 2, low: 1 };
  const highestRisk = riskLevels.reduce((max, current) =>
    riskPriority[current] > riskPriority[max] ? current : max
  );

  return {
    safe: !blocked && !hasErrors,
    risk: highestRisk,
    reasons: allReasons,
    recommendations: allRecommendations,
    blocked,
  };
}

// Emergency stop function
export function emergencyStop(reason: string) {
  Logger.warn('safety.emergencyStop', 'EMERGENCY STOP ACTIVATED', { reason });

  // Update UI state
  const { addNotification } = useUIStore.getState();

  // Add emergency notification
  addNotification({
    type: 'error',
    message: `EMERGENCY STOP: ${reason}`,
  });

  // Log emergency event
  const emergencyEvent = new CustomEvent('emergencyStop', {
    detail: {
      reason,
      timestamp: Date.now(),
      userAgent: navigator.userAgent,
      url: window.location.href,
    },
  });
  window.dispatchEvent(emergencyEvent);
}

// Safety wrapper for async operations
export async function withSafetyGuard<T>(
  operation: () => Promise<T>,
  operationName: string,
  context: SafetyContext
): Promise<T | null> {
  // Validate safety first
  const safetyResult = validateSafety(operationName, context);

  if (safetyResult.blocked) {
    Logger.warn('safety.operationBlocked', `Operation blocked: ${operationName}`, { reasons: safetyResult.reasons });

    // Add notification
    const { addNotification } = useUIStore.getState();
    addNotification({
      type: 'error',
      message: `${operationName} blocked: ${safetyResult.reasons[0]}`,
    });

    return null;
  }

  if (!safetyResult.safe && safetyResult.risk === 'high') {
    Logger.warn('safety.operationWarning', `Operation warning: ${operationName}`, { reasons: safetyResult.reasons });

    // Add warning notification
    const { addNotification } = useUIStore.getState();
    addNotification({
      type: 'warning',
      message: `${operationName} warning: ${safetyResult.reasons[0]}`,
    });
  }

  try {
    Logger.info('safety.checkPassed', `Safety check passed: ${operationName}`);
    return await operation();
  } catch (error) {
    Logger.error('safety.operationFailed', `Operation failed: ${operationName}`, error);

    // Check if this is a critical financial error
    if (operationName.includes('trade') || operationName.includes('order')) {
      emergencyStop(`Operation failed: ${operationName}`);
    }

    throw error;
  }
}

// Hook for React components
export function useSafetyGuard() {
  return {
    validateSafety,
    withSafetyGuard,
    emergencyStop,
  };
}
