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
      // ✅ EDGE CASE FIX: Added input validation to all setters
      setMarketData: (data: MarketData[]) => {
        // Validate input - fallback to empty array if invalid
        const validData = Array.isArray(data) ? data : [];
        set({ marketData: validData, marketDataLoading: false, marketDataError: null });
      },

      setActiveSignals: (signals: ActiveSignal[]) => {
        // Validate input - fallback to empty array if invalid
        const validSignals = Array.isArray(signals) ? signals : [];
        set({ activeSignals: validSignals, signalsLoading: false, signalsError: null });
      },

      addSignal: (signal: ActiveSignal) => {
        // Validate input - skip if null/undefined
        if (!signal) return;
        // [SIGNAL-FLOW] Debug logging for E2E verification (Story 0-2)
        console.log('[SIGNAL-FLOW] Signal added to store:', {
          signal_type: signal.signal_type,
          symbol: signal.symbol,
          timestamp: signal.timestamp,
          store_count: get().activeSignals.length + 1,
        });
        const currentSignals = get().activeSignals;
        // Keep only latest 10 signals to prevent memory bloat
        const updatedSignals = [signal, ...currentSignals.slice(0, 9)];
        set({ activeSignals: updatedSignals });
      },

      setIndicators: (indicators: IndicatorData[]) => {
        // Validate input - fallback to empty array if invalid
        const validIndicators = Array.isArray(indicators) ? indicators : [];
        set({ indicators: validIndicators, indicatorsLoading: false, indicatorsError: null });
      },

      addIndicator: (indicator: IndicatorData) => {
        // Validate input - skip if null/undefined
        if (!indicator) return;
        const currentIndicators = get().indicators;
        // Update existing indicator or add new one
        const existingIndex = currentIndicators.findIndex(
          ind => ind?.symbol === indicator?.symbol && ind?.name === indicator?.name
        );

        if (existingIndex >= 0) {
          // Update existing - merge new values into existing indicator
          const updatedIndicators = [...currentIndicators];
          updatedIndicators[existingIndex] = { ...updatedIndicators[existingIndex], ...indicator };
          set({ indicators: updatedIndicators });
        } else {
          // Add new
          set({ indicators: [...currentIndicators, indicator] });
        }
      },

      updateIndicator: (symbol: string, indicatorName: string, updates: Partial<IndicatorData>) => {
        // Validate inputs
        if (!symbol || !indicatorName) return;
        const currentIndicators = get().indicators;
        const updatedIndicators = currentIndicators.map(indicator =>
          indicator.symbol === symbol && indicator.name === indicatorName
            ? { ...indicator, ...(updates || {}), timestamp: new Date().toISOString() }
            : indicator
        );
        set({ indicators: updatedIndicators });
      },

      updateMarketData: (symbol: string, updates: Partial<MarketData>) => {
        // Validate inputs
        if (!symbol) return;
        const currentData = get().marketData;
        const updatedData = currentData.map(item =>
          item.symbol === symbol
            ? { ...item, ...(updates || {}), lastUpdate: new Date().toISOString() }
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

          // Type guard for market data validation
          const isValidMarketData = (item: any): boolean => {
            return (
              item &&
              typeof item.symbol === 'string' &&
              typeof item.price === 'number' &&
              typeof item.priceChange24h === 'number' &&
              typeof item.volume24h === 'number'
            );
          };

          // Validate response structure
          if (response && response.data && Array.isArray(response.data.market_data)) {
            const marketData = response.data.market_data;

            // Validate all items
            const validMarketData = marketData.filter(isValidMarketData);

            if (validMarketData.length !== marketData.length) {
              console.warn(`Filtered out ${marketData.length - validMarketData.length} invalid market data items`);
            }

            set({ marketData: validMarketData, marketDataLoading: false });
            debugLog('Market data fetched successfully', { count: validMarketData.length });
            return validMarketData;
          } else {
            console.warn('Invalid market data response structure:', response);
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

          // Type guard for indicator validation
          const isValidIndicator = (item: any): boolean => {
            return (
              item &&
              typeof item.name === 'string' &&
              typeof item.value === 'number' &&
              typeof item.symbol === 'string' &&
              typeof item.timestamp === 'string'
            );
          };

          // Validate response structure
          if (indicators && (indicators as any).data && Array.isArray((indicators as any).data.indicators)) {
            const indicatorData = (indicators as any).data.indicators;

            // Validate all items
            const validIndicators = indicatorData.filter(isValidIndicator);

            if (validIndicators.length !== indicatorData.length) {
              console.warn(`Filtered out ${indicatorData.length - validIndicators.length} invalid indicators`);
            }

            set({ indicators: validIndicators, indicatorsLoading: false });
            debugLog('Indicators fetched successfully', { count: validIndicators.length });
            return validIndicators;
          } else {
            console.warn('Invalid indicators response structure:', indicators);
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

          // Validate response structure
          if (sessionStatus && Array.isArray(sessionStatus.signals) && sessionStatus.signals.length > 0) {
            // Transform session signals to ActiveSignal format with null safety
            const signals = sessionStatus.signals
              .filter((signal: any) => signal && signal.symbol) // Filter out invalid signals
              .map((signal: any, index: number) => ({
                id: signal?.id || `signal_${index}`,
                symbol: signal?.symbol || 'UNKNOWN',
                // Handle signal type with explicit checks
                signalType: signal?.type === 'pump_detection'
                  ? 'pump'
                  : signal?.type === 'dump_detection'
                    ? 'dump'
                    : 'pump', // Default to 'pump' if type is unknown
                // Use nullish coalescing for numeric values to handle 0 correctly
                magnitude: signal?.magnitude ?? signal?.value ?? 0,
                confidence: signal?.confidence ?? 50,
                timestamp: signal?.timestamp || new Date().toISOString(),
                strategy: signal?.strategy || 'unknown'
              }));

            set({ activeSignals: signals, signalsLoading: false });
            debugLog('Active signals fetched successfully', { count: signals.length });
            return signals;
          } else {
            // Empty array or invalid structure
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