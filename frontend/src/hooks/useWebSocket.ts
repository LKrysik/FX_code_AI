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

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';

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

export interface HeartbeatMetrics {
  lastPingSent: number;
  lastPongReceived: number;
  rttMs: number;
  avgRttMs: number;
  missedPongs: number;
  isHealthy: boolean;
}

export interface UseWebSocketReturn {
  isConnected: boolean;
  lastMessage: WebSocketMessage | null;
  connectionState: 'connecting' | 'connected' | 'disconnected' | 'error';
  reconnectAttempt: number;
  heartbeat: HeartbeatMetrics;
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
  const opts = useMemo(() => ({
    ...DEFAULT_OPTIONS,
    ...options
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [
    options.url,
    options.reconnect,
    options.reconnectInterval,
    options.reconnectDecay,
    options.reconnectAttempts,
    options.heartbeatInterval
  ]);

  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [reconnectAttempt, setReconnectAttempt] = useState(0);
  const [heartbeat, setHeartbeat] = useState<HeartbeatMetrics>({
    lastPingSent: 0,
    lastPongReceived: 0,
    rttMs: 0,
    avgRttMs: 0,
    missedPongs: 0,
    isHealthy: true
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const pongTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const messageQueueRef = useRef<any[]>([]);
  const shouldReconnectRef = useRef(true);
  const rttHistoryRef = useRef<number[]>([]);
  const lastPingSentRef = useRef<number>(0);

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
    if (pongTimeoutRef.current) {
      clearTimeout(pongTimeoutRef.current);
      pongTimeoutRef.current = null;
    }
  }, []);

  // Handle pong response - calculate RTT and update health
  const handlePong = useCallback((serverTime?: number) => {
    const now = Date.now();
    const rttMs = now - lastPingSentRef.current;

    // Update RTT history (keep last 10)
    rttHistoryRef.current.push(rttMs);
    if (rttHistoryRef.current.length > 10) {
      rttHistoryRef.current.shift();
    }

    // Calculate average RTT
    const avgRttMs = rttHistoryRef.current.reduce((a, b) => a + b, 0) / rttHistoryRef.current.length;

    // Clear pong timeout
    if (pongTimeoutRef.current) {
      clearTimeout(pongTimeoutRef.current);
      pongTimeoutRef.current = null;
    }

    setHeartbeat({
      lastPingSent: lastPingSentRef.current,
      lastPongReceived: now,
      rttMs,
      avgRttMs,
      missedPongs: 0,
      isHealthy: true
    });

    console.debug(`[useWebSocket] Pong received - RTT: ${rttMs}ms, Avg: ${avgRttMs.toFixed(1)}ms`);
  }, []);

  // Handle missed pong
  const handleMissedPong = useCallback(() => {
    setHeartbeat(prev => {
      const missedPongs = prev.missedPongs + 1;
      const isHealthy = missedPongs < 3;

      console.warn(`[useWebSocket] Missed pong #${missedPongs}${isHealthy ? '' : ' - connection unhealthy'}`);

      // If too many missed pongs, force reconnect
      if (missedPongs >= 3 && wsRef.current) {
        console.error('[useWebSocket] Too many missed pongs, forcing reconnect');
        wsRef.current.close();
      }

      return {
        ...prev,
        missedPongs,
        isHealthy
      };
    });
  }, []);

  // Start heartbeat to detect silent disconnects
  const startHeartbeat = useCallback(() => {
    clearTimers();
    rttHistoryRef.current = []; // Reset RTT history on new connection

    heartbeatIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        try {
          lastPingSentRef.current = Date.now();
          wsRef.current.send(JSON.stringify({
            type: 'heartbeat',  // Backend expects 'heartbeat', not 'ping'
            timestamp: new Date().toISOString(),
            client_time: lastPingSentRef.current
          }));

          setHeartbeat(prev => ({
            ...prev,
            lastPingSent: lastPingSentRef.current
          }));

          // Set pong timeout (expect response within 30 seconds)
          // BUG-005-2: Increased from 10s to 30s to handle normal network latency
          pongTimeoutRef.current = setTimeout(() => {
            handleMissedPong();
          }, 30000);

        } catch (error) {
          console.error('[useWebSocket] Heartbeat failed:', error);
          handleMissedPong();
        }
      }
    }, opts.heartbeatInterval);
  }, [opts.heartbeatInterval, clearTimers, handleMissedPong]);

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

          // Handle pong response (from server ping or our heartbeat)
          // Backend sends: {"type": "status", "status": "pong", "server_time": ...}
          if (message.type === 'pong' || (message.type === 'status' && (message as any).status === 'pong')) {
            handlePong((message as any).server_time);
            return; // Don't propagate internal heartbeat messages
          }

          // Handle server-initiated ping (respond with pong)
          if (message.type === 'ping') {
            wsRef.current?.send(JSON.stringify({
              type: 'pong',
              timestamp: new Date().toISOString(),
              client_time: Date.now(),
              server_time: (message.data as any)?.server_time
            }));
            return;
          }

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
  }, [opts, reconnectAttempt, startHeartbeat, processQueue, clearTimers, handlePong, options]);

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);  // Only run on mount/unmount

  return {
    isConnected,
    lastMessage,
    connectionState,
    reconnectAttempt,
    heartbeat,
    sendMessage,
    sendJsonMessage,
    close,
    reconnect
  };
}
