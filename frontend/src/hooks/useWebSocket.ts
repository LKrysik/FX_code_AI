/**
 * useWebSocket Hook - Agent 6
 * ===========================
 * Custom hook for WebSocket connection management with auto-reconnect and heartbeat.
 *
 * Features:
 * - Auto-connect on mount
 * - Auto-reconnect with exponential backoff (max 5 attempts)
 * - Heartbeat every 30s to detect silent disconnects
 * - Message queue for offline messages
 * - TypeScript-first design
 */

import { useState, useEffect, useRef, useCallback } from 'react';

export interface WebSocketMessage {
  type: string;
  stream?: string;
  data: any;
  timestamp?: string;
}

export interface UseWebSocketOptions {
  url?: string;
  reconnect?: boolean;
  reconnectInterval?: number;
  reconnectDecay?: number;
  reconnectAttempts?: number;
  heartbeatInterval?: number;
  onOpen?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (event: Event) => void;
  onMessage?: (message: WebSocketMessage) => void;
}

export interface UseWebSocketReturn {
  isConnected: boolean;
  lastMessage: WebSocketMessage | null;
  connectionState: 'connecting' | 'connected' | 'disconnected' | 'error';
  reconnectAttempt: number;
  sendMessage: (message: any) => void;
  sendJsonMessage: (data: any, type?: string) => void;
  close: () => void;
  reconnect: () => void;
}

const DEFAULT_OPTIONS: Required<Omit<UseWebSocketOptions, 'onOpen' | 'onClose' | 'onError' | 'onMessage'>> = {
  url: process.env.NEXT_PUBLIC_WS_URL || 'ws://127.0.0.1:8080/ws',
  reconnect: true,
  reconnectInterval: 1000,  // Start at 1 second
  reconnectDecay: 1.5,      // Exponential backoff multiplier
  reconnectAttempts: 5,     // Max 5 attempts before giving up
  heartbeatInterval: 30000  // 30 seconds
};

/**
 * WebSocket hook with auto-reconnect and heartbeat
 *
 * @example
 * ```tsx
 * const { isConnected, lastMessage, sendMessage } = useWebSocket({
 *   onMessage: (msg) => console.log('Received:', msg)
 * });
 *
 * // Send a message
 * sendMessage({ type: 'subscribe', stream: 'live_trading' });
 * ```
 */
export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const opts = { ...DEFAULT_OPTIONS, ...options };

  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [reconnectAttempt, setReconnectAttempt] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const messageQueueRef = useRef<any[]>([]);
  const shouldReconnectRef = useRef(true);

  // Clear all timers
  const clearTimers = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
  }, []);

  // Start heartbeat to detect silent disconnects
  const startHeartbeat = useCallback(() => {
    clearTimers();
    heartbeatIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        try {
          wsRef.current.send(JSON.stringify({ type: 'ping' }));
        } catch (error) {
          console.error('[useWebSocket] Heartbeat failed:', error);
        }
      }
    }, opts.heartbeatInterval);
  }, [opts.heartbeatInterval, clearTimers]);

  // Send message (raw)
  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      try {
        const payload = typeof message === 'string' ? message : JSON.stringify(message);
        wsRef.current.send(payload);
      } catch (error) {
        console.error('[useWebSocket] Failed to send message:', error);
        // Queue message for retry
        messageQueueRef.current.push(message);
      }
    } else {
      // Queue message if not connected
      messageQueueRef.current.push(message);
      console.warn('[useWebSocket] Message queued (not connected):', message);
    }
  }, []);

  // Send JSON message with type
  const sendJsonMessage = useCallback((data: any, type: string = 'message') => {
    sendMessage({
      type,
      data,
      timestamp: new Date().toISOString()
    });
  }, [sendMessage]);

  // Process queued messages after reconnect
  const processQueue = useCallback(() => {
    if (messageQueueRef.current.length > 0 && wsRef.current?.readyState === WebSocket.OPEN) {
      console.log(`[useWebSocket] Processing ${messageQueueRef.current.length} queued messages`);
      const queue = [...messageQueueRef.current];
      messageQueueRef.current = [];
      queue.forEach(msg => sendMessage(msg));
    }
  }, [sendMessage]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      console.log('[useWebSocket] Already connected or connecting');
      return;
    }

    clearTimers();
    setConnectionState('connecting');

    try {
      console.log(`[useWebSocket] Connecting to ${opts.url} (attempt ${reconnectAttempt + 1}/${opts.reconnectAttempts})`);
      const ws = new WebSocket(opts.url);

      ws.onopen = (event) => {
        console.log('[useWebSocket] Connected');
        setIsConnected(true);
        setConnectionState('connected');
        setReconnectAttempt(0);
        startHeartbeat();
        processQueue();
        options.onOpen?.(event);
      };

      ws.onclose = (event) => {
        console.log('[useWebSocket] Disconnected:', event.code, event.reason);
        setIsConnected(false);
        setConnectionState('disconnected');
        clearTimers();
        options.onClose?.(event);

        // Auto-reconnect if enabled and not manually closed
        if (shouldReconnectRef.current && opts.reconnect && reconnectAttempt < opts.reconnectAttempts) {
          const delay = Math.min(
            opts.reconnectInterval * Math.pow(opts.reconnectDecay, reconnectAttempt),
            30000  // Max 30 seconds
          );
          console.log(`[useWebSocket] Reconnecting in ${delay}ms...`);
          reconnectTimeoutRef.current = setTimeout(() => {
            setReconnectAttempt(prev => prev + 1);
            connect();
          }, delay);
        } else if (reconnectAttempt >= opts.reconnectAttempts) {
          console.error('[useWebSocket] Max reconnect attempts reached');
          setConnectionState('error');
        }
      };

      ws.onerror = (event) => {
        console.error('[useWebSocket] Error:', event);
        setConnectionState('error');
        options.onError?.(event);
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);
          options.onMessage?.(message);
        } catch (error) {
          console.error('[useWebSocket] Failed to parse message:', error, event.data);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('[useWebSocket] Connection error:', error);
      setConnectionState('error');
    }
  }, [opts, reconnectAttempt, startHeartbeat, processQueue, clearTimers, options]);

  // Close connection
  const close = useCallback(() => {
    shouldReconnectRef.current = false;
    clearTimers();
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
    setConnectionState('disconnected');
  }, [clearTimers]);

  // Manual reconnect
  const reconnect = useCallback(() => {
    shouldReconnectRef.current = true;
    setReconnectAttempt(0);
    close();
    setTimeout(connect, 100);
  }, [close, connect]);

  // Auto-connect on mount
  useEffect(() => {
    shouldReconnectRef.current = true;
    connect();

    return () => {
      shouldReconnectRef.current = false;
      clearTimers();
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);  // Only run on mount/unmount

  return {
    isConnected,
    lastMessage,
    connectionState,
    reconnectAttempt,
    sendMessage,
    sendJsonMessage,
    close,
    reconnect
  };
}
