/**
 * useSocketSubscription Hook
 * ==========================
 * BUG-DV-031/032/033 FIX: Unified WebSocket subscription hook.
 *
 * Replaces the duplicate useWebSocket hook with a safe subscription to
 * the singleton wsService. Provides automatic cleanup on unmount to
 * prevent memory leaks.
 *
 * Usage:
 * ```tsx
 * useSocketSubscription((message) => {
 *   if (message.type === 'order_filled') {
 *     // Handle order fill
 *   }
 * }, 'MyComponent');
 * ```
 */

import { useEffect, useRef, useCallback } from 'react';
import { wsService, WSMessage } from '@/services/websocket';
import { useWebSocketStore } from '@/stores/websocketStore';

export type MessageHandler = (message: WSMessage) => void;

export interface UseSocketSubscriptionOptions {
  /**
   * Filter function to determine if message should be passed to handler.
   * If not provided, all messages are passed through.
   */
  filter?: (message: WSMessage) => boolean;

  /**
   * Whether to enable the subscription. Useful for conditional subscriptions.
   * Default: true
   */
  enabled?: boolean;
}

export interface UseSocketSubscriptionReturn {
  /** Whether the WebSocket is connected */
  isConnected: boolean;

  /** Current connection status */
  connectionStatus: string;

  /** Send a message through the WebSocket */
  sendMessage: (message: any) => void;

  /** Send a request and wait for response */
  sendRequest: (type: string, payload?: any, timeoutMs?: number) => Promise<any>;
}

/**
 * Subscribe to WebSocket messages with automatic cleanup.
 *
 * @param handler - Function to call when a message is received
 * @param componentName - Name of the component (for debugging memory leaks)
 * @param options - Optional configuration
 * @returns Object with connection state and send methods
 *
 * @example
 * ```tsx
 * // Basic usage
 * const { isConnected } = useSocketSubscription((msg) => {
 *   console.log('Received:', msg);
 * }, 'OrderHistory');
 *
 * // With filter
 * const { isConnected, sendMessage } = useSocketSubscription(
 *   (msg) => handleOrderUpdate(msg.data),
 *   'OrderHistory',
 *   { filter: (msg) => msg.type === 'order_filled' }
 * );
 * ```
 */
export function useSocketSubscription(
  handler: MessageHandler,
  componentName: string,
  options: UseSocketSubscriptionOptions = {}
): UseSocketSubscriptionReturn {
  const { filter, enabled = true } = options;

  // Use ref to always have latest handler without re-subscribing
  const handlerRef = useRef<MessageHandler>(handler);
  handlerRef.current = handler;

  const filterRef = useRef(filter);
  filterRef.current = filter;

  // Get connection state from the Zustand store
  const isConnected = useWebSocketStore((state) => state.isConnected);
  const connectionStatus = useWebSocketStore((state) => state.connectionStatus);

  // Memoized wrapper that uses refs
  const wrappedHandler = useCallback((message: WSMessage) => {
    // Apply filter if provided
    if (filterRef.current && !filterRef.current(message)) {
      return;
    }
    // Call the actual handler
    handlerRef.current(message);
  }, []);

  // Subscribe to wsService on mount, cleanup on unmount
  useEffect(() => {
    if (!enabled) {
      return;
    }

    // Subscribe to the singleton wsService
    const cleanup = wsService.addSessionUpdateListener(wrappedHandler, componentName);

    // Return cleanup function for unmount
    return cleanup;
  }, [componentName, wrappedHandler, enabled]);

  // Memoized send functions
  const sendMessage = useCallback((message: any) => {
    wsService.send(message);
  }, []);

  const sendRequest = useCallback(
    (type: string, payload?: any, timeoutMs?: number) => {
      return wsService.sendRequest(type, payload, timeoutMs);
    },
    []
  );

  return {
    isConnected,
    connectionStatus,
    sendMessage,
    sendRequest,
  };
}

/**
 * Hook for getting WebSocket connection state without subscribing to messages.
 * Use this when you only need connection status, not message handling.
 */
export function useWebSocketConnectionState() {
  const isConnected = useWebSocketStore((state) => state.isConnected);
  const connectionStatus = useWebSocketStore((state) => state.connectionStatus);
  const lastError = useWebSocketStore((state) => state.lastError);
  const reconnectAttempts = useWebSocketStore((state) => state.reconnectAttempts);

  return {
    isConnected,
    connectionStatus,
    lastError,
    reconnectAttempts,
  };
}

// Re-export WSMessage type for convenience
export type { WSMessage };
