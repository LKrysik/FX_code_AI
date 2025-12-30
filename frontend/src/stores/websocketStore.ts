/**
 * WebSocket Store
 * ===============
 * Manages WebSocket connection state and statistics
 * Replaces scattered WebSocket state management
 */

import { create } from 'zustand';
import { devtools, subscribeWithSelector } from 'zustand/middleware';
import { WebSocketState } from './types';

const initialState = {
  // Connection Status
  isConnected: false,
  connectionStatus: 'disconnected' as const,
  lastConnected: null as number | null,
  lastDisconnected: null as number | null,

  // BUG-008-3: Reconnection tracking (AC2)
  reconnectAttempts: 0,
  maxReconnectAttempts: 5,
  nextRetryAt: null as number | null,

  // Message Stats
  messagesReceived: 0,
  messagesSent: 0,
  lastMessageTime: null as number | null,

  // Error Tracking
  connectionErrors: 0,
  lastError: null as string | null,

  // SEC-0-3: State Sync Tracking
  lastSyncTime: null as Date | null,
  syncStatus: 'idle' as 'idle' | 'syncing' | 'synced' | 'failed',
};

export const useWebSocketStore = create<WebSocketState>()(
  devtools(
    subscribeWithSelector(
      (set, get) => ({
        ...initialState,

        // Actions
        setConnected: (connected: boolean) => {
          const now = Date.now();
          const currentStatus = get().connectionStatus;
          // Don't set isConnected to true if WebSocket is disabled
          const shouldBeConnected = connected && currentStatus !== 'disabled';
          set({
            isConnected: shouldBeConnected,
            connectionStatus: shouldBeConnected ? 'connected' : (currentStatus === 'disabled' ? 'disabled' : 'disconnected'),
            lastConnected: shouldBeConnected ? now : get().lastConnected,
            lastDisconnected: shouldBeConnected ? get().lastDisconnected : now,
            lastError: shouldBeConnected ? null : get().lastError, // Clear error on successful connection
          });
        },

        setConnectionStatus: (status: WebSocketState['connectionStatus']) => {
          const now = Date.now();
          set({
            connectionStatus: status,
            lastConnected: status === 'connected' ? now : get().lastConnected,
            lastDisconnected: status === 'disconnected' ? now : get().lastDisconnected,
          });
        },

        incrementMessagesReceived: () => {
          set(state => ({
            messagesReceived: state.messagesReceived + 1,
            lastMessageTime: Date.now(),
          }));
        },

        incrementMessagesSent: () => {
          set(state => ({
            messagesSent: state.messagesSent + 1,
          }));
        },

        setLastError: (error: string | null) => {
          set(state => ({
            lastError: error,
            connectionErrors: error ? state.connectionErrors + 1 : state.connectionErrors,
          }));
        },

        resetStats: () => {
          set({
            messagesReceived: 0,
            messagesSent: 0,
            lastMessageTime: null,
            connectionErrors: 0,
            lastError: null,
          });
        },

        // BUG-008-3: Reconnection actions (AC2)
        setReconnectState: (attempts: number, maxAttempts: number, nextRetryAt: number | null) => {
          set({
            reconnectAttempts: attempts,
            maxReconnectAttempts: maxAttempts,
            nextRetryAt,
            connectionStatus: attempts > 0 ? 'reconnecting' : 'disconnected',
          });
        },

        resetReconnectState: () => {
          set({
            reconnectAttempts: 0,
            nextRetryAt: null,
          });
        },

        // SEC-0-3: State sync actions
        setLastSyncTime: (time: Date | null) => {
          set({
            lastSyncTime: time,
            syncStatus: time ? 'synced' : 'idle',
          });
        },

        setSyncStatus: (status: 'idle' | 'syncing' | 'synced' | 'failed') => {
          set({ syncStatus: status });
        },
      })
    ),
    {
      name: 'websocket-store',
      enabled: process.env.NODE_ENV === 'development',
    }
  )
);

// Selectors for optimized re-renders
export const useWebSocketConnection = () => useWebSocketStore(state => ({
  isConnected: state.isConnected,
  connectionStatus: state.connectionStatus,
  lastConnected: state.lastConnected,
  lastDisconnected: state.lastDisconnected,
  // BUG-008-3: Reconnection tracking (AC2)
  reconnectAttempts: state.reconnectAttempts,
  maxReconnectAttempts: state.maxReconnectAttempts,
  nextRetryAt: state.nextRetryAt,
}));

export const useWebSocketStats = () => useWebSocketStore(state => ({
  messagesReceived: state.messagesReceived,
  messagesSent: state.messagesSent,
  lastMessageTime: state.lastMessageTime,
  connectionErrors: state.connectionErrors,
}));

export const useWebSocketError = () => useWebSocketStore(state => state.lastError);

// Actions
export const useWebSocketActions = () => useWebSocketStore(state => ({
  setConnected: state.setConnected,
  setConnectionStatus: state.setConnectionStatus,
  incrementMessagesReceived: state.incrementMessagesReceived,
  incrementMessagesSent: state.incrementMessagesSent,
  setLastError: state.setLastError,
  resetStats: state.resetStats,
}));

// Computed selectors
export const useConnectionUptime = () => {
  const { lastConnected, lastDisconnected } = useWebSocketStore.getState();
  if (!lastConnected) return 0;

  const now = Date.now();
  const lastDisconnect = lastDisconnected || 0;

  if (lastConnected > lastDisconnect) {
    return now - lastConnected;
  }

  return 0;
};

export const useConnectionHealth = () => {
  const { connectionErrors, messagesReceived, isConnected } = useWebSocketStore.getState();

  if (!isConnected) return 'disconnected';

  // Simple health calculation based on error rate
  const errorRate = messagesReceived > 0 ? (connectionErrors / messagesReceived) * 100 : 0;

  if (errorRate > 10) return 'unhealthy';
  if (errorRate > 5) return 'warning';
  return 'healthy';
};