/**
 * Zustand Store Types
 * ===================
 * Type definitions for all store states
 * Ensures type safety across the application
 */

import { WalletBalance, TradingPerformance, Strategy } from '@/types/api';

// Market Data Types
export interface MarketData {
  symbol: string;
  price: number;
  priceChange24h: number;
  volume24h: number;
  pumpMagnitude: number;
  volumeSurge: number;
  confidenceScore: number;
  lastUpdate: string;
}

export interface ActiveSignal {
  id: string;
  symbol: string;
  signalType: 'pump' | 'dump';
  magnitude: number;
  confidence: number;
  timestamp: string;
  strategy: string;
}

export interface IndicatorData {
  name: string;
  value: number;
  symbol: string;
  timestamp: string;
  used_by_strategies: string[];
  indicator_type?: string;
  period?: number;
  metadata?: Record<string, any>;
}

// Dashboard State
export interface DashboardState {
  // Market Data
  marketData: MarketData[];
  activeSignals: ActiveSignal[];
  indicators: IndicatorData[];

  // Loading States
  loading: boolean;
  marketDataLoading: boolean;
  signalsLoading: boolean;
  indicatorsLoading: boolean;

  // Error States
  error: string | null;
  marketDataError: string | null;
  signalsError: string | null;
  indicatorsError: string | null;

  // Actions
  setMarketData: (data: MarketData[]) => void;
  setActiveSignals: (signals: ActiveSignal[]) => void;
  setIndicators: (indicators: IndicatorData[]) => void;
  addSignal: (signal: ActiveSignal) => void;
  addIndicator: (indicator: IndicatorData) => void;
  updateIndicator: (symbol: string, indicatorName: string, updates: Partial<IndicatorData>) => void;
  updateMarketData: (symbol: string, updates: Partial<MarketData>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;

  // Async Actions
  fetchMarketData: () => Promise<MarketData[]>;
  fetchIndicators: () => Promise<IndicatorData[]>;
  fetchActiveSignals: () => Promise<ActiveSignal[]>;
}

// WebSocket State
export interface WebSocketState {
  // Connection Status
  isConnected: boolean;
  connectionStatus: 'connected' | 'disconnected' | 'connecting' | 'error' | 'disabled';
  lastConnected: number | null;
  lastDisconnected: number | null;

  // Message Stats
  messagesReceived: number;
  messagesSent: number;
  lastMessageTime: number | null;

  // Error Tracking
  connectionErrors: number;
  lastError: string | null;

  // SEC-0-3: State Sync Tracking
  lastSyncTime: Date | null;
  syncStatus: 'idle' | 'syncing' | 'synced' | 'failed';

  // Actions
  setConnected: (connected: boolean) => void;
  setConnectionStatus: (status: WebSocketState['connectionStatus']) => void;
  incrementMessagesReceived: () => void;
  incrementMessagesSent: () => void;
  setLastError: (error: string | null) => void;
  resetStats: () => void;

  // SEC-0-3: State sync actions
  setLastSyncTime: (time: Date | null) => void;
  setSyncStatus: (status: 'idle' | 'syncing' | 'synced' | 'failed') => void;
}

// Trading State
export interface TradingState {
  // Account Data
  walletBalance: WalletBalance | null;
  performance: TradingPerformance | null;
  strategies: Strategy[];

  // Session Data
  currentSession: {
    sessionId: string | null;
    type: string | null;
    status: string | null;
    symbols: string[];
  } | null;

  // Loading States
  walletLoading: boolean;
  performanceLoading: boolean;
  strategiesLoading: boolean;

  // Error States
  walletError: string | null;
  performanceError: string | null;
  strategiesError: string | null;

  // Actions
  setWalletBalance: (balance: WalletBalance | null) => void;
  setPerformance: (performance: TradingPerformance | null) => void;
  setStrategies: (strategies: Strategy[]) => void;
  setCurrentSession: (session: TradingState['currentSession']) => void;
  updateSessionStatus: (status: string) => void;
  setWalletLoading: (loading: boolean) => void;
  setPerformanceLoading: (loading: boolean) => void;
  setStrategiesLoading: (loading: boolean) => void;
  setWalletError: (error: string | null) => void;
  setPerformanceError: (error: string | null) => void;
  setStrategiesError: (error: string | null) => void;
  fetchWalletBalance: () => Promise<WalletBalance | null>;
  fetchTradingPerformance: () => Promise<TradingPerformance | null>;
  fetchStrategies: () => Promise<Strategy[]>;
  fetchExecutionStatus: () => Promise<any>;
  startSession: (sessionData: any) => Promise<any>;
  stopSession: (sessionId?: string) => Promise<void>;
  reset: () => void;
}

// UI State
export interface UIState {
  // Global UI States
  sidebarOpen: boolean;
  theme: 'light' | 'dark';

  // Dialog/Modal States
  dialogs: {
    strategyBuilder: boolean;
    backtestConfig: boolean;
    riskManagement: boolean;
    emergencyStop: boolean;
  };

  // Notification States
  notifications: Array<{
    id: string;
    type: 'success' | 'error' | 'warning' | 'info';
    message: string;
    timestamp: number;
    autoHide?: boolean;
  }>;

  // Loading States
  globalLoading: boolean;
  loadingStates: Record<string, boolean>;

  // Actions
  setSidebarOpen: (open: boolean) => void;
  setTheme: (theme: UIState['theme']) => void;
  openDialog: (dialog: keyof UIState['dialogs']) => void;
  closeDialog: (dialog: keyof UIState['dialogs']) => void;
  addNotification: (notification: Omit<UIState['notifications'][0], 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
  setGlobalLoading: (loading: boolean) => void;
  setLoadingState: (key: string, loading: boolean) => void;
  reset: () => void;
}

// Combined Store Type
export interface AppStore extends DashboardState, WebSocketState, TradingState, UIState {}
