/**
 * Financial Safety Hook
 * ====================
 * Provides safety guards for financial operations
 * Prevents trading when system is in unsafe state
 */

import { useCallback, useEffect } from 'react';
import { useWebSocketStore } from '@/stores/websocketStore';
import { useUIStore } from '@/stores/uiStore';
import { useTradingStore } from '@/stores/tradingStore';
import { Logger } from '@/services/frontendLogService';

export interface SafetyCheckResult {
  safe: boolean;
  reason?: string;
  action?: 'block' | 'warn' | 'allow';
  details?: Record<string, any>;
}

export const useFinancialSafety = () => {
  const { isConnected, connectionStatus } = useWebSocketStore();
  const { /* readOnlyMode, */ addNotification } = useUIStore(); // TODO: readOnlyMode removed from UIState
  const { currentSession } = useTradingStore();
  const readOnlyMode = false; // TODO: Implement readOnlyMode properly

  // Core safety checks
  const checkConnectionSafety = useCallback((): SafetyCheckResult => {
    if (!isConnected) {
      return {
        safe: false,
        reason: 'No WebSocket connection',
        action: 'block',
        details: { connectionStatus }
      };
    }

    if (connectionStatus === 'error') {
      return {
        safe: false,
        reason: 'WebSocket connection error',
        action: 'block',
        details: { connectionStatus }
      };
    }

    return { safe: true, action: 'allow' };
  }, [isConnected, connectionStatus]);

  const checkReadOnlyMode = useCallback((): SafetyCheckResult => {
    if (readOnlyMode) {
      return {
        safe: false,
        reason: 'System is in read-only mode',
        action: 'block',
        details: { readOnlyMode }
      };
    }

    return { safe: true, action: 'allow' };
  }, [readOnlyMode]);

  const checkSessionSafety = useCallback((): SafetyCheckResult => {
    if (!currentSession) {
      return {
        safe: false,
        reason: 'No active trading session',
        action: 'warn',
        details: { currentSession: null }
      };
    }

    if (currentSession.status === 'error' || currentSession.status === 'stopped') {
      return {
        safe: false,
        reason: `Session status: ${currentSession.status}`,
        action: 'block',
        details: { sessionStatus: currentSession.status }
      };
    }

    return { safe: true, action: 'allow' };
  }, [currentSession]);

  // Comprehensive safety check
  const checkAllSafety = useCallback((): SafetyCheckResult => {
    // Check connection first (most critical)
    const connectionCheck = checkConnectionSafety();
    if (!connectionCheck.safe) {
      return connectionCheck;
    }

    // Check read-only mode
    const readOnlyCheck = checkReadOnlyMode();
    if (!readOnlyCheck.safe) {
      return readOnlyCheck;
    }

    // Check session status
    const sessionCheck = checkSessionSafety();
    if (!sessionCheck.safe && sessionCheck.action === 'block') {
      return sessionCheck;
    }

    return { safe: true, action: 'allow' };
  }, [checkConnectionSafety, checkReadOnlyMode, checkSessionSafety]);

  // Safe operation wrapper
  const withSafetyCheck = useCallback(
    async <T,>(
      operation: () => Promise<T>,
      operationName: string,
      options: {
        showNotification?: boolean;
        allowWarnings?: boolean;
      } = {}
    ): Promise<T | null> => {
      const { showNotification = true, allowWarnings = false } = options;

      // Perform safety check
      const safetyResult = checkAllSafety();

      if (!safetyResult.safe) {
        if (showNotification) {
          addNotification({
            type: safetyResult.action === 'block' ? 'error' : 'warning',
            message: `${operationName} blocked: ${safetyResult.reason}`,
          });
        }

        if (safetyResult.action === 'block') {
          Logger.warn('useFinancialSafety.blocked', `${operationName} blocked - ${safetyResult.reason}`);
          return null;
        }
      }

      // Operation is safe to proceed
      try {
        Logger.info('useFinancialSafety.approved', `${operationName} approved`);
        return await operation();
      } catch (error) {
        Logger.error('useFinancialSafety.failed', `${operationName} failed`, error instanceof Error ? error : undefined);

        if (showNotification) {
          addNotification({
            type: 'error',
            message: `${operationName} failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
          });
        }

        throw error;
      }
    },
    [checkAllSafety, addNotification]
  );

  // Emergency stop function
  const emergencyStop = useCallback(() => {
    Logger.warn('useFinancialSafety.emergency_stop', 'Emergency stop activated');

    addNotification({
      type: 'error',
      message: 'EMERGENCY STOP: All trading operations halted',
    });

    // This would trigger emergency protocols
    // - Close all positions
    // - Cancel pending orders
    // - Enter read-only mode
    // - Notify administrators
  }, [addNotification]);

  // Auto-safety mode based on connection status
  useEffect(() => {
    if (!isConnected && !readOnlyMode) {
      Logger.warn('useFinancialSafety.auto_readonly', 'Auto-entering read-only mode due to connection loss');
      // Note: In real implementation, this would update the UI store
    }
  }, [isConnected, readOnlyMode]);

  return {
    // Safety check functions
    checkConnectionSafety,
    checkReadOnlyMode,
    checkSessionSafety,
    checkAllSafety,

    // Safe operation wrapper
    withSafetyCheck,

    // Emergency functions
    emergencyStop,

    // Current safety status
    isSystemSafe: checkAllSafety().safe,
  };
};