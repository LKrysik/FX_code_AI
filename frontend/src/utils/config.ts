// Environment configuration utilities

export interface AppConfig {
  apiUrl: string;
  wsUrl: string;
  isProduction: boolean;
  isSecure: boolean;
  appName: string;
  appVersion: string;
  enableDebugMode: boolean;
  enableMockData: boolean;
}

export const getAppConfig = (): AppConfig => {
  const isProduction = process.env.NODE_ENV === 'production';
  const isSecure = typeof window !== 'undefined' && window.location.protocol === 'https:';

  return {
    apiUrl: process.env.NEXT_PUBLIC_API_URL || (isProduction || isSecure ? 'https://api.cryptotrading.com' : 'http://localhost:8080'),
    wsUrl: process.env.NEXT_PUBLIC_WS_URL || (isProduction || isSecure ? 'wss://api.cryptotrading.com/ws' : 'ws://localhost:8080'),
    isProduction,
    isSecure,
    appName: process.env.NEXT_PUBLIC_APP_NAME || 'Crypto Trading Platform',
    appVersion: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
    enableDebugMode: process.env.NEXT_PUBLIC_ENABLE_DEBUG_MODE === 'true',
    enableMockData: process.env.NEXT_PUBLIC_ENABLE_MOCK_DATA === 'true', // Default to false - use real API data
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
export const debugLog = (message: string, ...args: any[]) => {
  if (isDebugMode()) {
    console.log(`[DEBUG] ${message}`, ...args);
  }
};

export const errorLog = (message: string, error?: any) => {
  console.error(`[ERROR] ${message}`, error);
};