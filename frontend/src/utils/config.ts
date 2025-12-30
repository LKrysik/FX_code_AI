// Environment configuration utilities

import { Logger } from '@/services/frontendLogService';

export interface AppConfig {
  apiUrl: string;
  wsUrl: string;
  isProduction: boolean;
  isSecure: boolean;
  appName: string;
  appVersion: string;
  enableDebugMode: boolean;
  enableMockData: boolean;
  // BUG-008-2: Heartbeat configuration
  websocket: {
    heartbeatIntervalMs: number;
    heartbeatTimeoutMs: number;
    maxMissedPongs: number;
    slowConnectionThreshold: number;
  };
}

export const getAppConfig = (): AppConfig => {
  const isProduction = process.env.NODE_ENV === 'production';
  const isSecure = typeof window !== 'undefined' && window.location.protocol === 'https:';

  // API URL - must be set via environment variable in production
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

  // WebSocket URL - derive from API URL if not explicitly set
  // Appends /ws path for WebSocket endpoint
  let wsUrl = process.env.NEXT_PUBLIC_WS_URL;
  if (!wsUrl) {
    // Convert http(s) to ws(s) and append /ws path
    wsUrl = apiUrl.replace(/^http/, 'ws') + '/ws';
  }

  return {
    apiUrl,
    wsUrl,
    isProduction,
    isSecure,
    appName: process.env.NEXT_PUBLIC_APP_NAME || 'Crypto Trading Platform',
    appVersion: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
    enableDebugMode: process.env.NEXT_PUBLIC_ENABLE_DEBUG_MODE === 'true',
    enableMockData: process.env.NEXT_PUBLIC_ENABLE_MOCK_DATA === 'true', // Default to false - use real API data
    // BUG-008-2: Heartbeat configuration with externalized defaults
    websocket: {
      heartbeatIntervalMs: parseInt(process.env.NEXT_PUBLIC_WS_HEARTBEAT_INTERVAL_MS || '30000', 10),
      heartbeatTimeoutMs: parseInt(process.env.NEXT_PUBLIC_WS_HEARTBEAT_TIMEOUT_MS || '30000', 10),
      maxMissedPongs: parseInt(process.env.NEXT_PUBLIC_WS_MAX_MISSED_PONGS || '3', 10),
      slowConnectionThreshold: parseInt(process.env.NEXT_PUBLIC_WS_SLOW_CONNECTION_THRESHOLD || '2', 10),
    },
  };
};

export const config = getAppConfig();

// Utility functions for environment checks
export const isDevelopment = () => !config.isProduction;
export const isProduction = () => config.isProduction;
export const isSecureConnection = () => config.isSecure;
export const shouldUseMockData = () => config.enableMockData;
export const isDebugMode = () => config.enableDebugMode;

// Environment-specific logging
export const debugLog = (message: string, ...args: unknown[]) => {
  if (isDebugMode()) {
    // Combine all args into a data object
    const data: Record<string, unknown> = { message };
    args.forEach((arg, index) => {
      if (arg && typeof arg === 'object' && !Array.isArray(arg)) {
        Object.assign(data, arg);
      } else if (arg !== undefined) {
        data[`arg${index}`] = arg;
      }
    });
    Logger.debug('config.debug', data);
  }
};

export const errorLog = (message: string, error?: unknown) => {
  Logger.error('config.error', { message, error });
};