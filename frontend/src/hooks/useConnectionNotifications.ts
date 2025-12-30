'use client';

/**
 * useConnectionNotifications Hook
 * ================================
 * BUG-008-3: Provides toast notifications for WebSocket connection events (AC5).
 *
 * Features:
 * - Toast notification on connection loss
 * - Toast notification on reconnection success
 * - Toast notification on permanent connection failure
 * - Integrates wsService.onNotification callback with uiStore
 *
 * Usage:
 * ```tsx
 * // In App layout or main component
 * function App() {
 *   useConnectionNotifications();
 *   return <YourApp />;
 * }
 * ```
 */

import { useEffect, useRef } from 'react';
import { wsService } from '@/services/websocket';
import { useUIStore } from '@/stores/uiStore';
import { useWebSocketStore } from '@/stores/websocketStore';
import { Logger } from '@/services/frontendLogService';

type ConnectionStatus = 'connected' | 'connecting' | 'reconnecting' | 'disconnected' | 'error' | 'disabled' | 'slow';

/**
 * Hook to bridge WebSocket connection events to UI notifications
 */
export function useConnectionNotifications() {
  const addNotification = useUIStore(state => state.addNotification);
  const connectionStatus = useWebSocketStore(state => state.connectionStatus);
  const reconnectAttempts = useWebSocketStore(state => state.reconnectAttempts);
  const maxReconnectAttempts = useWebSocketStore(state => state.maxReconnectAttempts);

  // Track previous status to detect transitions
  const previousStatusRef = useRef<ConnectionStatus>(connectionStatus);
  const hasNotifiedDisconnectRef = useRef(false);
  const hasNotifiedConnectRef = useRef(false);
  const hasNotifiedFinalAttemptRef = useRef(false);
  const previousReconnectAttemptsRef = useRef(reconnectAttempts);

  // Register wsService notification callback
  useEffect(() => {
    wsService.setCallbacks({
      onNotification: (notification) => {
        addNotification({
          type: notification.type,
          message: notification.message,
          autoHide: notification.autoHide,
        });
      },
    });
  }, [addNotification]);

  // Handle connection status transitions
  useEffect(() => {
    const previousStatus = previousStatusRef.current;
    previousStatusRef.current = connectionStatus;

    // Skip initial mount
    if (previousStatus === connectionStatus) {
      return;
    }

    Logger.debug('connection_notifications.status_change', {
      from: previousStatus,
      to: connectionStatus,
      reconnectAttempts,
    });

    // Connected: Show success if coming from a disconnected/error state
    if (connectionStatus === 'connected') {
      if (
        previousStatus === 'reconnecting' ||
        previousStatus === 'disconnected' ||
        previousStatus === 'error'
      ) {
        if (!hasNotifiedConnectRef.current) {
          addNotification({
            type: 'success',
            message: 'Connection restored',
            autoHide: true,
          });
          hasNotifiedConnectRef.current = true;
          hasNotifiedDisconnectRef.current = false;
        }
      }
      return;
    }

    // Disconnected: Show warning (only once per disconnect cycle)
    if (connectionStatus === 'disconnected' || connectionStatus === 'error') {
      if (!hasNotifiedDisconnectRef.current && previousStatus === 'connected') {
        addNotification({
          type: 'warning',
          message: 'Connection lost. Attempting to reconnect...',
          autoHide: false,
        });
        hasNotifiedDisconnectRef.current = true;
        hasNotifiedConnectRef.current = false;
      }
      return;
    }

    // Reconnecting: Show info about reconnect attempt
    if (connectionStatus === 'reconnecting') {
      // Only notify on first reconnect attempt
      if (reconnectAttempts === 1 && !hasNotifiedDisconnectRef.current) {
        addNotification({
          type: 'warning',
          message: 'Connection lost. Attempting to reconnect...',
          autoHide: false,
        });
        hasNotifiedDisconnectRef.current = true;
        hasNotifiedConnectRef.current = false;
      }
      // Note: Final attempt notification is handled in separate useEffect below
      return;
    }

    // Slow connection warning
    if (connectionStatus === 'slow') {
      addNotification({
        type: 'warning',
        message: 'Slow connection detected - server response delayed',
        autoHide: true,
      });
      return;
    }
  }, [connectionStatus, reconnectAttempts, maxReconnectAttempts, addNotification]);

  // Detect final reconnection attempt (fires when attempts change, not just status)
  useEffect(() => {
    const previousAttempts = previousReconnectAttemptsRef.current;
    previousReconnectAttemptsRef.current = reconnectAttempts;

    // Reset flag when connection is restored
    if (connectionStatus === 'connected') {
      hasNotifiedFinalAttemptRef.current = false;
      return;
    }

    // Notify on final attempt (only once)
    if (
      connectionStatus === 'reconnecting' &&
      reconnectAttempts === maxReconnectAttempts &&
      previousAttempts < maxReconnectAttempts &&
      !hasNotifiedFinalAttemptRef.current
    ) {
      addNotification({
        type: 'error',
        message: `Final reconnection attempt (${reconnectAttempts}/${maxReconnectAttempts})`,
        autoHide: false,
      });
      hasNotifiedFinalAttemptRef.current = true;
    }
  }, [reconnectAttempts, maxReconnectAttempts, connectionStatus, addNotification]);

  // Detect permanent failure (max reconnects reached)
  useEffect(() => {
    if (
      reconnectAttempts >= maxReconnectAttempts &&
      (connectionStatus === 'disconnected' || connectionStatus === 'error')
    ) {
      addNotification({
        type: 'error',
        message: 'Unable to connect to server. Please check your connection and refresh the page.',
        autoHide: false,
      });
    }
  }, [reconnectAttempts, maxReconnectAttempts, connectionStatus, addNotification]);
}

export default useConnectionNotifications;
