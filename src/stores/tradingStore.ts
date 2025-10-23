/**
 * Trading Store
 * =============
 * Manages trading-related state: wallet, performance, strategies, sessions
 * Replaces scattered trading state from multiple components
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { TradingState } from './types';
import { WalletBalance, TradingPerformance, Strategy } from '@/types/api';
import { apiService } from '@/services/api';
import { debugLog, errorLog } from '@/utils/config';

const initialState = {
  // Account Data
  walletBalance: null as WalletBalance | null,
  performance: null as TradingPerformance | null,
  strategies: [] as Strategy[],

  // Session Data
  currentSession: null as TradingState['currentSession'],

  // Loading States
  walletLoading: false,
  performanceLoading: false,
  strategiesLoading: false,

  // Error States
  walletError: null as string | null,
  performanceError: null as string | null,
  strategiesError: null as string | null,
};

export const useTradingStore = create<TradingState>()(
  devtools(
    (set, get) => ({
      ...initialState,

      // Actions
      setWalletBalance: (balance: WalletBalance | null) => {
        set({ walletBalance: balance, walletLoading: false, walletError: null });
      },

      setPerformance: (performance: TradingPerformance | null) => {
        set({ performance, performanceLoading: false, performanceError: null });
      },

      setStrategies: (strategies: Strategy[]) => {
        set({ strategies, strategiesLoading: false, strategiesError: null });
      },

      setCurrentSession: (session: TradingState['currentSession']) => {
        set({ currentSession: session });
      },

      updateSessionStatus: (status: string) => {
        const currentSession = get().currentSession;
        if (currentSession) {
          set({
            currentSession: {
              ...currentSession,
              status,
            },
          });
        }
      },

      setWalletLoading: (loading: boolean) => {
        set({ walletLoading: loading });
      },

      setPerformanceLoading: (loading: boolean) => {
        set({ performanceLoading: loading });
      },

      setStrategiesLoading: (loading: boolean) => {
        set({ strategiesLoading: loading });
      },

      setWalletError: (error: string | null) => {
        set({ walletError: error, walletLoading: false });
      },

      setPerformanceError: (error: string | null) => {
        set({ performanceError: error, performanceLoading: false });
      },

      setStrategiesError: (error: string | null) => {
        set({ strategiesError: error, strategiesLoading: false });
      },

      // Async actions for API calls
      fetchWalletBalance: async () => {
        try {
          set({ walletLoading: true, walletError: null });
          const balance = await apiService.getWalletBalance();
          set({ walletBalance: balance, walletLoading: false });
          debugLog('Wallet balance fetched successfully');
          return balance;
        } catch (error: any) {
          const errorMessage = error?.message || 'Failed to fetch wallet balance';
          set({ walletError: errorMessage, walletLoading: false });
          errorLog('Failed to fetch wallet balance', error);
          throw error;
        }
      },

      fetchTradingPerformance: async () => {
        try {
          set({ performanceLoading: true, performanceError: null });
          const performance = await apiService.getTradingPerformance();
          set({ performance, performanceLoading: false });
          debugLog('Trading performance fetched successfully');
          return performance;
        } catch (error: any) {
          const errorMessage = error?.message || 'Failed to fetch trading performance';
          set({ performanceError: errorMessage, performanceLoading: false });
          errorLog('Failed to fetch trading performance', error);
          throw error;
        }
      },

      fetchStrategies: async () => {
        try {
          set({ strategiesLoading: true, strategiesError: null });
          const strategies = await apiService.getStrategyStatus();
          set({ strategies, strategiesLoading: false });
          debugLog('Strategies fetched successfully');
          return strategies;
        } catch (error: any) {
          const errorMessage = error?.message || 'Failed to fetch strategies';
          set({ strategiesError: errorMessage, strategiesLoading: false });
          errorLog('Failed to fetch strategies', error);
          throw error;
        }
      },

      fetchExecutionStatus: async () => {
        try {
          const status = await apiService.getExecutionStatus();
          if (status && status.session_id) {
            set({
              currentSession: {
                sessionId: status.session_id,
                type: status.mode || 'unknown',
                status: status.status || 'unknown',
                symbols: status.symbols || [],
              }
            });
          } else {
            set({ currentSession: null });
          }
          debugLog('Execution status fetched successfully');
          return status;
        } catch (error: any) {
          errorLog('Failed to fetch execution status', error);
          throw error;
        }
      },

      startSession: async (sessionData: any) => {
        try {
          const response = await apiService.startSession(sessionData);
          debugLog('Session started successfully', response);
          // Refresh execution status after starting
          await get().fetchExecutionStatus();
          return response;
        } catch (error: any) {
          errorLog('Failed to start session', error);
          throw error;
        }
      },

      stopSession: async (sessionId?: string) => {
        try {
          await apiService.stopSession(sessionId);
          set({ currentSession: null });
          debugLog('Session stopped successfully');
        } catch (error: any) {
          errorLog('Failed to stop session', error);
          throw error;
        }
      },

      reset: () => {
        set(initialState);
      },
    }),
    {
      name: 'trading-store',
      enabled: process.env.NODE_ENV === 'development',
    }
  )
);

// Selectors for optimized re-renders
export const useWalletBalance = () => useTradingStore(state => state.walletBalance);
export const useTradingPerformance = () => useTradingStore(state => state.performance);
export const useStrategies = () => useTradingStore(state => state.strategies);
export const useCurrentSession = () => useTradingStore(state => state.currentSession);

// Loading states
export const useTradingLoadingStates = () => useTradingStore(state => ({
  walletLoading: state.walletLoading,
  performanceLoading: state.performanceLoading,
  strategiesLoading: state.strategiesLoading,
}));

// Error states
export const useTradingErrors = () => useTradingStore(state => ({
  walletError: state.walletError,
  performanceError: state.performanceError,
  strategiesError: state.strategiesError,
}));

// Actions
export const useTradingActions = () => useTradingStore(state => ({
  // Sync actions
  setWalletBalance: state.setWalletBalance,
  setPerformance: state.setPerformance,
  setStrategies: state.setStrategies,
  setCurrentSession: state.setCurrentSession,
  updateSessionStatus: state.updateSessionStatus,
  setWalletLoading: state.setWalletLoading,
  setPerformanceLoading: state.setPerformanceLoading,
  setStrategiesLoading: state.setStrategiesLoading,
  setWalletError: state.setWalletError,
  setPerformanceError: state.setPerformanceError,
  setStrategiesError: state.setStrategiesError,
  reset: state.reset,
  // Async actions
  fetchWalletBalance: state.fetchWalletBalance,
  fetchTradingPerformance: state.fetchTradingPerformance,
  fetchStrategies: state.fetchStrategies,
  fetchExecutionStatus: state.fetchExecutionStatus,
  startSession: state.startSession,
  stopSession: state.stopSession,
}));

// Computed selectors
export const useTotalPortfolioValue = () => {
  const balance = useTradingStore.getState().walletBalance;
  return balance?.total_usd_estimate || 0;
};

export const useActiveStrategiesCount = () => {
  const strategies = useTradingStore.getState().strategies;
  return strategies.filter(s => s.current_state === 'active').length;
};

export const useSessionStatus = () => {
  const session = useTradingStore.getState().currentSession;
  return session?.status || 'idle';
};

export const useIsTradingActive = () => {
  const session = useTradingStore.getState().currentSession;
  return session?.status === 'running' || session?.status === 'active';
};