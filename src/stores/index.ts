/**
 * Zustand Store Index
 * ===================
 * Centralized state management to replace 15+ useState hooks
 * Organized into logical slices for better maintainability
 */

export { useDashboardStore, useDashboardActions } from './dashboardStore';
export { useWebSocketStore } from './websocketStore';
export { useTradingStore, useTradingActions } from './tradingStore';
export { useGraphStore, useGraphActions } from './graphStore';
export { useUIStore, useUIActions } from './uiStore';
export { useHealthStore } from './healthStore';
export { useAuthStore, useAuthHeaders, useHasPermission } from './authStore';

// Re-export types
export type { DashboardState, WebSocketState, TradingState, UIState, IndicatorData } from './types';
export type { User, AuthState } from './authStore';