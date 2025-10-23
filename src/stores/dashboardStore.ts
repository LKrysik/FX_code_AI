/**
 * Dashboard Store
 * ===============
 * Replaces 15+ useState hooks from the main dashboard component
 * Manages market data, signals, and dashboard-specific state
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { DashboardState, MarketData, ActiveSignal, IndicatorData } from './types';
import { apiService } from '@/services/api';
import { debugLog, errorLog } from '@/utils/config';

const initialState = {
  // Market Data
  marketData: [] as MarketData[],
  activeSignals: [] as ActiveSignal[],
  indicators: [] as IndicatorData[],

  // Loading States
  loading: true,
  marketDataLoading: false,
  signalsLoading: false,
  indicatorsLoading: false,

  // Error States
  error: null as string | null,
  marketDataError: null as string | null,
  signalsError: null as string | null,
  indicatorsError: null as string | null,
};

export const useDashboardStore = create<DashboardState>()(
  devtools(
    (set, get) => ({
      ...initialState,

      // Actions
      setMarketData: (data: MarketData[]) => {
        set({ marketData: data, marketDataLoading: false, marketDataError: null });
      },

      setActiveSignals: (signals: ActiveSignal[]) => {
        set({ activeSignals: signals, signalsLoading: false, signalsError: null });
      },

      addSignal: (signal: ActiveSignal) => {
        const currentSignals = get().activeSignals;
        // Keep only latest 10 signals to prevent memory bloat
        const updatedSignals = [signal, ...currentSignals.slice(0, 9)];
        set({ activeSignals: updatedSignals });
      },

      setIndicators: (indicators: IndicatorData[]) => {
        set({ indicators, indicatorsLoading: false, indicatorsError: null });
      },

      addIndicator: (indicator: IndicatorData) => {
        const currentIndicators = get().indicators;
        // Update existing indicator or add new one
        const existingIndex = currentIndicators.findIndex(
          ind => ind.symbol === indicator.symbol && ind.name === indicator.name
        );

        if (existingIndex >= 0) {
          // Update existing
          const updatedIndicators = [...currentIndicators];
          updatedIndicators[existingIndex] = { ...updatedIndicators[existingIndex], ...indicator };
          set({ indicators: updatedIndicators });
        } else {
          // Add new
          set({ indicators: [...currentIndicators, indicator] });
        }
      },

      updateIndicator: (symbol: string, indicatorName: string, updates: Partial<IndicatorData>) => {
        const currentIndicators = get().indicators;
        const updatedIndicators = currentIndicators.map(indicator =>
          indicator.symbol === symbol && indicator.name === indicatorName
            ? { ...indicator, ...updates, timestamp: new Date().toISOString() }
            : indicator
        );
        set({ indicators: updatedIndicators });
      },

      updateMarketData: (symbol: string, updates: Partial<MarketData>) => {
        const currentData = get().marketData;
        const updatedData = currentData.map(item =>
          item.symbol === symbol
            ? { ...item, ...updates, lastUpdate: new Date().toISOString() }
            : item
        );
        set({ marketData: updatedData });
      },

      setLoading: (loading: boolean) => {
        set({ loading });
      },

      setError: (error: string | null) => {
        set({ error });
      },

      // Async actions for API calls
      fetchMarketData: async () => {
        try {
          set({ marketDataLoading: true, marketDataError: null });
          const response = await apiService.getMarketData();
          if (response && response.data && response.data.market_data) {
            set({ marketData: response.data.market_data, marketDataLoading: false });
            debugLog('Market data fetched successfully');
            return response.data.market_data;
          } else {
            // Fallback to empty array if no data
            set({ marketData: [], marketDataLoading: false });
            return [];
          }
        } catch (error: any) {
          const errorMessage = error?.message || 'Failed to fetch market data';
          set({ marketDataError: errorMessage, marketDataLoading: false });
          errorLog('Failed to fetch market data', error);
          throw error;
        }
      },

      fetchIndicators: async () => {
        try {
          set({ indicatorsLoading: true, indicatorsError: null });
          const indicators = await apiService.getIndicators();
          if (indicators && indicators.data && indicators.data.indicators) {
            set({ indicators: indicators.data.indicators, indicatorsLoading: false });
            debugLog('Indicators fetched successfully');
            return indicators.data.indicators;
          } else {
            set({ indicators: [], indicatorsLoading: false });
            return [];
          }
        } catch (error: any) {
          const errorMessage = error?.message || 'Failed to fetch indicators';
          set({ indicatorsError: errorMessage, indicatorsLoading: false });
          errorLog('Failed to fetch indicators', error);
          throw error;
        }
      },

      fetchActiveSignals: async () => {
        try {
          set({ signalsLoading: true, signalsError: null });
          const sessionStatus = await apiService.getExecutionStatus();
          if (sessionStatus && sessionStatus.signals && sessionStatus.signals.length > 0) {
            // Transform session signals to ActiveSignal format
            const signals = sessionStatus.signals.map((signal: any, index: number) => ({
              id: signal.id || `signal_${index}`,
              symbol: signal.symbol || 'UNKNOWN',
              signalType: signal.type === 'pump_detection' ? 'pump' : 'dump',
              magnitude: signal.magnitude || signal.value || 0,
              confidence: signal.confidence || 50,
              timestamp: signal.timestamp || new Date().toISOString(),
              strategy: signal.strategy || 'unknown'
            }));
            set({ activeSignals: signals, signalsLoading: false });
            debugLog('Active signals fetched successfully');
            return signals;
          } else {
            set({ activeSignals: [], signalsLoading: false });
            return [];
          }
        } catch (error: any) {
          const errorMessage = error?.message || 'Failed to fetch active signals';
          set({ signalsError: errorMessage, signalsLoading: false });
          errorLog('Failed to fetch active signals', error);
          throw error;
        }
      },

      reset: () => {
        set(initialState);
      },
    }),
    {
      name: 'dashboard-store',
      enabled: process.env.NODE_ENV === 'development',
    }
  )
);

// Selectors for optimized re-renders
export const useMarketData = () => useDashboardStore(state => state.marketData);
export const useActiveSignals = () => useDashboardStore(state => state.activeSignals);
export const useIndicators = () => useDashboardStore(state => state.indicators);
export const useDashboardLoading = () => useDashboardStore(state => state.loading);
export const useDashboardError = () => useDashboardStore(state => state.error);

// Actions
export const useDashboardActions = () => useDashboardStore(state => ({
  // Sync actions
  setMarketData: state.setMarketData,
  setActiveSignals: state.setActiveSignals,
  setIndicators: state.setIndicators,
  addSignal: state.addSignal,
  addIndicator: state.addIndicator,
  updateIndicator: state.updateIndicator,
  updateMarketData: state.updateMarketData,
  setLoading: state.setLoading,
  setError: state.setError,
  reset: state.reset,
  // Async actions
  fetchMarketData: state.fetchMarketData,
  fetchIndicators: state.fetchIndicators,
  fetchActiveSignals: state.fetchActiveSignals,
}));